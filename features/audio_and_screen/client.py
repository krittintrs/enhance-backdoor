import socket
import cv2
import pyautogui
import mss
import numpy as np
import struct
import pyaudio
import sounddevice as sd
import threading
import queue
import time

# Constants
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
VIDEO_PORT = 9999
AUDIO_PORT = 6666
host_ip = '192.168.203.142'  # Replace with server IP address

def screen_stream(client_socket):
    w, h = pyautogui.size()
    monitor = {"top": 0, "left": 0, "width": w, "height": h}
    
    try:
        t0 = time.time()
        n_frames = 1
        with mss.mss() as sct:
            while True:
                screen = sct.grab(monitor)
                frame = np.array(screen)
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                message = struct.pack(">L", len(buffer)) + buffer.tobytes()
                try:
                    client_socket.sendall(message)
                except BrokenPipeError:
                    print("Broken pipe error, connection lost.")
                    break

                elapsed_time = time.time() - t0
                avg_fps = (n_frames / elapsed_time)
                print("Screen Average FPS: " + str(avg_fps))
                n_frames += 1
    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        client_socket.close()

def audio_stream(client_socket, mode):
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    
    speaker_queue = queue.Queue()
    
    if mode in (3, 4):
        def callback(indata, frames, time, status):
            if status:
                print(status)
            speaker_queue.put(indata.copy())
        sd.InputStream(callback=callback, channels=CHANNELS, samplerate=RATE, blocksize=CHUNK).start()

    try:
        print("Recording audio...")
        while True:
            try:
                mic_data = stream.read(CHUNK, exception_on_overflow=False) if mode in (2, 4) else b'\x00' * CHUNK * 2
                speaker_data = speaker_queue.get() if mode in (3, 4) else np.zeros(CHUNK, dtype=np.int16)
                mixed_data = np.frombuffer(mic_data, dtype=np.int16) + speaker_data.flatten()
                mixed_data = np.clip(mixed_data, -32768, 32767).astype(np.int16).tobytes()
                message = struct.pack(">L", len(mixed_data)) + mixed_data
                try:
                    client_socket.sendall(message)
                except BrokenPipeError:
                    print("Broken pipe error, connection lost.")
                    break
            except IOError as e:
                if e.errno == -9981:
                    print("Buffer overflowed. Skipping this chunk.")
                else:
                    raise
    except KeyboardInterrupt:
        print("Audio stream stopped by user.")
    finally:
        client_socket.close()
        stream.stop_stream()
        stream.close()
        p.terminate()

def main():

    print("Select mode:")
    print("1) Screen only")
    print("2) Screen + Mic")
    print("3) Screen + Speaker")
    print("4) Screen + Mic + Speaker")
    mode = int(input("Enter mode number: "))

    # Video streaming
    video_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    video_socket.connect((host_ip, VIDEO_PORT))
    video_thread = threading.Thread(target=screen_stream, args=(video_socket,))
    
    # Audio streaming
    audio_thread = None
    if mode != 1:
        audio_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        audio_socket.connect((host_ip, AUDIO_PORT))
        audio_thread = threading.Thread(target=audio_stream, args=(audio_socket, mode))
    
    # Start threads
    video_thread.start()
    if audio_thread:
        audio_thread.start()
    
    video_thread.join()
    if audio_thread:
        audio_thread.join()

if __name__ == "__main__":
    main()

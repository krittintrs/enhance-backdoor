import socket
import cv2
import pyautogui
import mss
import numpy as np
import struct
import pyaudio
import time
import threading

# Constants
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
AUDIO_RECORD_SECONDS = 20
VIDEO_PORT = 9999
AUDIO_PORT = 6666

# Screen capture
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

                # perf test
                elapsed_time = time.time() - t0
                avg_fps = (n_frames / elapsed_time)
                print("Screen Average FPS: " + str(avg_fps))
                n_frames += 1
    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        client_socket.close()

# Audio capture
def audio_stream(client_socket):
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    try:
        print("Recording audio...")
        while True:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                message = struct.pack(">L", len(data)) + data
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
    host_ip = '127.0.0.1'  # Replace with server IP address

    # Video streaming
    video_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    video_socket.connect((host_ip, VIDEO_PORT))
    video_thread = threading.Thread(target=screen_stream, args=(video_socket,))
    
    # Audio streaming
    audio_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    audio_socket.connect((host_ip, AUDIO_PORT))
    audio_thread = threading.Thread(target=audio_stream, args=(audio_socket,))
    
    # Start both threads
    video_thread.start()
    audio_thread.start()
    
    video_thread.join()
    audio_thread.join()

if __name__ == "__main__":
    main()

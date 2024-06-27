import socket
import cv2
import pyautogui
import mss
import numpy as np
import struct
import pyaudio
import threading
import time
import os
from dotenv import load_dotenv

reconnection_delay = 2

# Load environment variables from .env file
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
print(dotenv_path)
load_dotenv(dotenv_path)

# Set variables based on .env values
TARGET_IP = os.getenv("TARGET_IP", "127.0.0.1")
TARGET_PORT = int(os.getenv("TARGET_PORT", 5000))
VIDEO_PORT = int(os.getenv("VIDEO_PORT", 9000))
AUDIO_PORT = int(os.getenv("AUDIO_PORT", 6000))

# Use these variables in your code
print(f"Target IP: {TARGET_IP}")
print(f"Target Port: {TARGET_PORT}")
print(f"Video Port: {VIDEO_PORT}")
print(f"Audio Port: {AUDIO_PORT}")

# Constants
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

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
                mic_data = stream.read(CHUNK, exception_on_overflow=False)
                message = struct.pack(">L", len(mic_data)) + mic_data
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
    time.sleep(reconnection_delay)

    # Video streaming
    video_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    video_socket.connect((TARGET_IP, VIDEO_PORT))
    video_thread = threading.Thread(target=screen_stream, args=(video_socket,))
    
    # Audio streaming
    audio_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    audio_socket.connect((TARGET_IP, AUDIO_PORT))
    audio_thread = threading.Thread(target=audio_stream, args=(audio_socket,))
    
    # Start threads
    video_thread.start()
    audio_thread.start()
    
    video_thread.join()
    audio_thread.join()

if __name__ == "__main__":
    main()

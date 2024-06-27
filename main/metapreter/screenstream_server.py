import socket
import cv2
import numpy as np
import struct
import pyaudio
import threading
import queue
import os
from dotenv import load_dotenv

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

# Helper function to receive data
def receive_all(sock, count):
    buf = b''
    while count:
        newbuf = sock.recv(count)
        if not newbuf:
            return None
        buf += newbuf
        count -= len(newbuf)
    return buf

# Video receiving and displaying
def video_stream(server_socket, frame_queue):
    client_socket, addr = server_socket.accept()
    print('Video connection from:', addr)

    try:
        while True:
            message_size = receive_all(client_socket, struct.calcsize(">L"))
            if not message_size:
                break
            message_size = struct.unpack(">L", message_size)[0]
            frame_data = receive_all(client_socket, message_size)
            if not frame_data:
                break
                
            frame = np.frombuffer(frame_data, dtype=np.uint8)
            frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
            frame_queue.put(frame)
    finally:
        client_socket.close()

# Audio receiving and playing
def audio_stream(server_socket):
    client_socket, addr = server_socket.accept()
    print('Audio connection from:', addr)

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    output=True,
                    frames_per_buffer=CHUNK)

    try:
        while True:
            message_size = receive_all(client_socket, struct.calcsize(">L"))
            if not message_size:
                break
            message_size = struct.unpack(">L", message_size)[0]
            audio_data = receive_all(client_socket, message_size)
            if not audio_data:
                break
            stream.write(audio_data)
    finally:
        client_socket.close()
        stream.stop_stream()
        stream.close()
        p.terminate()

def main():

    # Video streaming
    video_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    video_server_socket.bind((TARGET_IP, VIDEO_PORT))
    video_server_socket.listen(5)
    print("Video server listening at:", (TARGET_IP, VIDEO_PORT))
    
    # Audio streaming
    audio_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    audio_server_socket.bind((TARGET_IP, AUDIO_PORT))
    audio_server_socket.listen(5)
    print("Audio server listening at:", (TARGET_IP, AUDIO_PORT))
    
    frame_queue = queue.Queue()

    video_thread = threading.Thread(target=video_stream, args=(video_server_socket, frame_queue))
    audio_thread = threading.Thread(target=audio_stream, args=(audio_server_socket,))
    
    video_thread.start()
    audio_thread.start()

    # Display frames from the queue in the main thread
    cv2.namedWindow('Received', cv2.WINDOW_NORMAL)
    try:
        while True:
            if not frame_queue.empty():
                frame = frame_queue.get()
                cv2.imshow('Received', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    finally:
        cv2.destroyAllWindows()

    video_thread.join()
    audio_thread.join()

if __name__ == "__main__":
    main()

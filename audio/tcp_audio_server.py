import socket
import pyaudio
import wave

# Server setup
host = '127.0.0.1'  # Listen on all available interfaces
port = 6789
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((host, port))
server_socket.listen(1)
print("Server listening on port:", port)

# Audio recording setup
chunk = 512
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
WAVE_OUTPUT_FILENAME = "received_output.wav"

p = pyaudio.PyAudio()
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=chunk)

print("Waiting for client connection...")
client_socket, addr = server_socket.accept()
print("Connection from:", addr)

frames = []

# Recording loop
while True:
    try:
        data = client_socket.recv(chunk)
        if not data:
            break
        frames.append(data)
    except:
        break

print("Recording finished, saving to file...")

# Save the recorded data as a WAV file
wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
wf.setnchannels(CHANNELS)
wf.setsampwidth(p.get_sample_size(FORMAT))
wf.setframerate(RATE)
wf.writeframes(b''.join(frames))
wf.close()

# Cleanup
client_socket.close()
server_socket.close()
stream.stop_stream()
stream.close()
p.terminate()

print("File saved as:", WAVE_OUTPUT_FILENAME)

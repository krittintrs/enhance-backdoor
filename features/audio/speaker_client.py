import socket
import sounddevice as sd
import threading
import queue
import struct
import time

# Constants
CHUNK = 1024
FORMAT = 'int16'
CHANNELS = 1
RATE = 44100
AUDIO_PORT = 6000
RECORD_SECONDS = 5  # Set the recording duration

def audio_stream(client_socket, duration):
    speaker_queue = queue.Queue()
    
    def callback(indata, frames, time, status):
        if status:
            print(status)
        speaker_queue.put(indata.copy())
    
    end_time = time.time() + duration
    
    with sd.InputStream(callback=callback, channels=CHANNELS, samplerate=RATE, blocksize=CHUNK):
        try:
            print("Recording audio...")
            while time.time() < end_time:
                speaker_data = speaker_queue.get()
                print(f"Speaker data size: {len(speaker_data)}")  # Debugging print
                message = struct.pack(">L", len(speaker_data)) + speaker_data.tobytes()
                try:
                    client_socket.sendall(message)
                except BrokenPipeError:
                    print("Broken pipe error, connection lost.")
                    break
        except KeyboardInterrupt:
            print("Audio stream stopped by user.")
        finally:
            client_socket.close()

def main():
    host_ip = '127.0.0.1'  # Replace with server IP address

    # Audio streaming
    audio_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    audio_socket.connect((host_ip, AUDIO_PORT))
    audio_thread = threading.Thread(target=audio_stream, args=(audio_socket, RECORD_SECONDS))
    
    # Start thread
    audio_thread.start()
    audio_thread.join()

if __name__ == "__main__":
    main()

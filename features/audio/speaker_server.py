import socket
import struct
import wave
import threading

# Constants
AUDIO_PORT = 6000
AUDIO_FILE = 'received_audio.wav'
RECORD_SECONDS = 5  # Set the recording duration

def receive_all(sock, count):
    buf = b''
    while count:
        newbuf = sock.recv(count)
        if not newbuf:
            return None
        buf += newbuf
        count -= len(newbuf)
    return buf

def audio_stream(client_socket, duration):
    wf = wave.open(AUDIO_FILE, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(2)  # Assuming 16-bit audio
    wf.setframerate(44100)
    
    try:
        while True:
            message_size = receive_all(client_socket, struct.calcsize(">L"))
            if not message_size:
                break
            message_size = struct.unpack(">L", message_size)[0]
            audio_data = receive_all(client_socket, message_size)
            if not audio_data:
                break
                
            print(f"Received audio data of size: {len(audio_data)} bytes")  # Debugging print
            wf.writeframes(audio_data)
    except Exception as e:
        print(f"Audio stream error: {e}")
    finally:
        wf.close()
        client_socket.close()
        print("Audio recording completed and saved.")

def main():
    host_ip = '127.0.0.1'  # Replace with your server IP address

    # Audio server setup
    audio_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    audio_server_socket.bind((host_ip, AUDIO_PORT))
    audio_server_socket.listen(5)
    print(f"Audio server listening at: {host_ip}:{AUDIO_PORT}")
    
    while True:
        audio_client_socket, _ = audio_server_socket.accept()
        audio_thread = threading.Thread(target=audio_stream, args=(audio_client_socket, RECORD_SECONDS))
        audio_thread.start()

if __name__ == "__main__":
    main()

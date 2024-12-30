import socket
import ctypes
import pyautogui
import time  # Importing time for timestamp-based filenames
from datetime import datetime

server_ip = '192.168.1.25'
client_port = 5001

# Connect to server's client socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((server_ip, client_port))

print("Connected to the server. Waiting for messages...")

# Define WinAPI functions for blocking/unblocking keyboard
user32 = ctypes.WinDLL('user32', use_last_error=True)

def block_keyboard():
    user32.BlockInput(True)
    ctypes.windll.user32.MessageBoxW(0, "Keyboard is now blocked.", "Blocked", 0x40 | 0x1)

def unblock_keyboard():
    user32.BlockInput(False)
    ctypes.windll.user32.MessageBoxW(0, "Keyboard is now unblocked.", "Unblocked", 0x40 | 0x1)

# Variable to keep track of screenshot count


try:
    while True:
        message = client_socket.recv(1024).decode()
        if not message:
            break
        
        print("Received from server:", message)
        
        if message == "HELLO":
            print("Hello from the server!")
        elif message == "BLOCK":
            block_keyboard()
        elif message == "UNBLOCK":
            unblock_keyboard()
        elif message == "SCREENSHOT":
            c = datetime.now()
            # Create a timestamp in sortable format: 'YYYY-MM-DD_HH-MM-SS'
            current_time = c.strftime('%Y-%m-%d_%H-%M-%S')
            print('Current Time is:', current_time)
            # Generate a new filename based on the timestamp
            screenshot_filename = f"PICTURE_{current_time}.png"

            screenshot = pyautogui.screenshot()
            screenshot.save(screenshot_filename)  # Save the screenshot with the dynamic filename
            
            with open(screenshot_filename, "rb") as f:
                screenshot_bytes = f.read()
            
            client_socket.sendall(b"PIC_START")
            client_socket.sendall(screenshot_bytes)
            client_socket.sendall(b"PIC_END")
            print(f"Screenshot saved as {screenshot_filename}")

except Exception as e:
    print(f"Error on client: {e}")

finally:
    # Clean up socket
    client_socket.close()

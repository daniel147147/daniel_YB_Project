import socket
import tkinter as tk
from tkinter import ttk, messagebox, Canvas
from PIL import Image, ImageTk
from io import BytesIO
import hashlib

class AdminClient:
    def __init__(self, admin_ip, admin_port):
        self.admin_ip = admin_ip
        self.admin_port = admin_port
        self.socket = None
        self.connected_clients = []

        self._setup_ui()

    def _connect_to_server(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.admin_ip, self.admin_port))
            self._log_history("Connected to server as admin.")
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect to server: {e}")

    def _setup_ui(self):
        self.root = tk.Tk()
        self.root.title("Admin Client GUI")
        self.root.geometry("800x600")

        # Frames for different sections
        command_frame = tk.Frame(self.root, bg="lightgray", width=200, height=150)
        command_frame.pack(side=tk.TOP, fill=tk.X)

        history_frame = tk.Frame(self.root, bg="white", width=200, height=150)
        history_frame.pack(side=tk.BOTTOM, fill=tk.X)

        client_list_frame = tk.Frame(self.root, bg="lightblue", width=200)
        client_list_frame.pack(side=tk.LEFT, fill=tk.Y)

        screenshot_frame = tk.Frame(self.root, bg="black")
        screenshot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Command Section
        connect_button = tk.Button(command_frame, text="Connect to Server", command=self._connect_to_server)
        connect_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.command_entry = tk.Entry(command_frame, font=("Arial", 12))
        self.command_entry.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        self.command_entry.bind("<Return>", lambda event: self._send_command())  # Bind Enter key to _send_command

        execute_button = tk.Button(command_frame, text="Execute", command=self._send_command)
        execute_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # Add "Request Last File" button
        last_file_button = tk.Button(command_frame, text="Request Last File", command=self._request_last_file)
        last_file_button.pack(side=tk.LEFT, padx=5, pady=5)

        # History Section
        self.history_text = tk.Text(history_frame, wrap=tk.WORD, bg="white", state="disabled", height=10)
        self.history_text.pack(fill=tk.BOTH, expand=True)

        # Client List Section
        tk.Label(client_list_frame, text="Connected Clients:", font=("Arial", 14)).pack(pady=5)
        self.client_listbox = tk.Listbox(client_list_frame, font=("Arial", 12))
        self.client_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        refresh_button = tk.Button(client_list_frame, text="Refresh", command=self._refresh_client_list)
        refresh_button.pack(pady=5)

        # Screenshot Section
        self.screenshot_canvas = Canvas(screenshot_frame, bg="black")
        self.screenshot_canvas.pack(fill=tk.BOTH, expand=True)

        self.root.mainloop()

    def _send_command(self):
        if not self.socket:
            messagebox.showwarning("Connection Error", "You must connect to the server first.")
            return

        command = self.command_entry.get().strip().upper()
        if not command:
            messagebox.showwarning("Input Error", "Please enter a command.")
            return

        try:
            if command == "CLIENTLIST":
                self._refresh_client_list()
            else: # including SCREENSHOT.
                self.socket.sendall(command.encode())
                response = self.socket.recv(1024).decode()
                self._log_history(f"Command: {command}\nResponse: {response}\n")
        except Exception as e:
            self._log_history(f"Error sending command: {e}\n")

    def _log_history(self, message):
        self.history_text.configure(state="normal")
        self.history_text.insert(tk.END, message + "\n")
        self.history_text.configure(state="disabled")
        self.history_text.see(tk.END)

    def _refresh_client_list(self):
        if not self.socket:
            self._log_history("Cannot refresh client list: Not connected to server.")
            return

        try:
            self.socket.sendall(b"CLIENTLIST")
            response = self.socket.recv(1024).decode()
            self.connected_clients = response.split(", ") if response else []
            self.client_listbox.delete(0, tk.END)
            for client in self.connected_clients:
                self.client_listbox.insert(tk.END, client)
            client_list = ", ".join(self.connected_clients)
            self._log_history(f"Connected Clients: {client_list}\n")
        
        except Exception as e:
            self._log_history(f"Error refreshing client list: {e}\n")

    def _receive_screenshot(self):
        if not self.socket:
            self._log_history("Cannot receive screenshot: Not connected to server.")
            return

        try:
            data = b""
            while True:
                chunk = self.socket.recv(4096)
                if b"SCREENSHOT_END" in chunk:
                    data += chunk.replace(b"SCREENSHOT_END", b"")
                    break
                data += chunk

            # Display the screenshot in the canvas
            image = Image.open(BytesIO(data))
            photo = ImageTk.PhotoImage(image)
            self.screenshot_canvas.create_image(0, 0, image=photo, anchor=tk.NW)
            self.screenshot_canvas.image = photo

            self._log_history("Screenshot received and displayed.")
        except Exception as e:
            self._log_history(f"Error receiving screenshot: {e}\n")

    def _request_last_file(self):
        print ("in request last file")
        if not self.socket:
            messagebox.showwarning("Connection Error", "You must connect to the server first.")
            return

        try:
            self.socket.sendall(b"LASTFILE")
            chunk = self.socket.recv(1024)
            data = chunk.replace(b"FILE_START", b"")
            
            while True:
                chunk = self.socket.recv(4096)
                if b"FILE_END" in chunk:
                    data += chunk.replace(b"FILE_END", b"")
                    break
                data += chunk

            checksum = hashlib.md5(data).hexdigest()
            print(f"Received file of size {len(data)} bytes with checksum {checksum}")

            # Validate if the received data is not empty
            if not data:
                self._log_history("Received empty data for the most recent file.")
                return

            # Attempt to open the image
            try:
                image = Image.open(BytesIO(data))
                canvas_width = self.screenshot_canvas.winfo_width()
                canvas_height = self.screenshot_canvas.winfo_height()
                image = image.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)

                photo = ImageTk.PhotoImage(image)
                self.screenshot_canvas.create_image(0, 0, image=photo, anchor=tk.NW)
                self.screenshot_canvas.image = photo
                self._log_history("Most recent file received and displayed.")
            except Exception as e:
                self._log_history(f"Error displaying the image: {e}")

        except Exception as e:
            self._log_history(f"Error receiving the most recent file: {e}")


if __name__ == "__main__":
    admin_ip = "192.168.1.25"
    admin_port = 5000

    AdminClient(admin_ip, admin_port)

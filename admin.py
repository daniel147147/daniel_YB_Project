# admin code

import socket
import tkinter as tk
from tkinter import ttk, messagebox, Canvas, simpledialog, filedialog
from PIL import ImageGrab
from PIL import Image, ImageTk, ImageOps
from io import BytesIO
import hashlib
import ssl
import os
import time
import threading
import queue
import sys

"""
AdminClient is the main class for the admin interface in the classroom management system.
It sets up the GUI, handles server communication via SSL, and manages connected clients. 
"""
    
class AdminClient:
    def __init__(self, admin_ip, admin_port, admin_test_port, client_msg_clientlist_port):
        self.admin_ip = admin_ip
        self.admin_port = admin_port
        self.admin_test_port = admin_test_port
        self.client_msg_clientlist_port = client_msg_clientlist_port

        # Socket variables for secure and plain connections
        self.socket = None
        self.test_socket = None
        self.msg_clientlist_socket = None

        # Client tracking
        self.connected_clients = []
        self.test_status = {}  # Tracks if client is currently taking a test
        self.selected_file_info = {}
        self.msg_mode = False
        self.shutdown = False

        # Build the user interface  
        self._setup_ui()

    """
    The function allows the display of an external file help.txt
    in the log history and display it on the canvas, that contains explanations all functions.
    """
    def _read_help(self):
        try:
            with open("help.txt", 'r') as help_file:
                content = help_file.read()
            return content
        except FileNotFoundError:
            return "Error: help.txt file not found."
        except Exception as e:
            return f"An error occurred while reading help.txt: {e}"


    def display_help(self):
        self.enable_screenshot_scroll(3500)  # Enables scrolling if necessary
        content = self._read_help()  # Read the help content from help.txt
        self.screenshot_canvas.delete("all")  # Clear previous content on the canvas
        self.screenshot_canvas.create_text(
            10, 10,
            text=content,
            font=("Arial", 20),
            fill="white",
            anchor="nw",
            width=580)  # <-- This is the important part! Set width to wrap text)



    def _connect_to_server(self):
        try:
            try:
                # sock is the admin sock before applying ecryption SSL -> self.socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.msg_clientlist_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False  # Disable hostname verification
                ssl_context.verify_mode = ssl.CERT_NONE  # Don't require a trusted CA
                
                # this is the main admin socket after encryption.
                self.socket = ssl_context.wrap_socket(sock, server_hostname=self.admin_ip)

                print ("admin requested connection, ", self.admin_port)
                self.socket.connect((self.admin_ip, self.admin_port))
                print ("admin was approved connection")
            except:
                print("cannot connect to server")
                messagebox.showwarning("connection Error", "cannot connect to server.")
                return
            try:
                self.test_socket.connect((self.admin_ip, self.admin_test_port))
                self._log_history("Connected to server as test admin.")
            except Exception as e:
                self._log_history(f"Failed to connect to test port: {e}")
            try:  
                self.msg_clientlist_socket.connect((self.admin_ip, self.client_msg_clientlist_port))
                self._log_history("Connected to server as msg \ clientlist admin.")
            except Exception as e:
                self._log_history(f"Failed to connect to msg/clientlist port: {e}")
                

            # Disable the button and change text
            self.connect_button.config(text="Connected", state=tk.DISABLED)

            # Start background listener after successful connection
            self._start_client_msg_clientlist_listener()

            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect to server: {e}")

    def on_close(self):
        """
        Triggered when the window is closed. Closes sockets and shuts down the GUI.
        """
        if messagebox.askokcancel("Quit", "Are you sure you want to quit?"):
            self.shutdown = True
            # Optional: clean socket resources
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
            if self.test_socket:
                try:
                    self.test_socket.close()
                except:
                    pass
            if self.msg_clientlist_socket:
                try:
                    self.msg_clientlist_socket.close()
                except:
                    pass

            print("Closing application. \n")
            self.root.destroy()

    def _setup_ui(self):
        """
        Sets up the Tkinter GUI layout and components for the admin client.
        Includes error handling to catch and report issues during UI creation.
        """
        # Initialize main window
        self.root = tk.Tk()
        self.root.title("Admin Client GUI")
        
        # Window size & resizing settings
        self.root.geometry("800x600")  # Default size
        self.root.minsize(888, 666)    # Minimum allowed size
        self.root.maxsize(888, 666)    # Maximum allowed size
        self.root.resizable(True, True)  # Allow resizing
        
        # Set background color
        self.root.config(bg="#f0f0f0")

        # Bind the close event to the on_close method
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

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
        self.connect_button = tk.Button(command_frame, text="Connect to Server", command=self._connect_to_server)
        self.connect_button.pack(side=tk.LEFT, padx=5, pady=5)

        execute_button = tk.Button(command_frame, text="Execute", command=self._get_command)
        execute_button.pack(side=tk.RIGHT, padx=5, pady=5)

        self.command_entry = tk.Entry(command_frame, font=("Arial", 12))
        self.command_entry.insert(0, "sending message to clients here")
        
        self.command_entry.config(state="disabled")
        self.command_entry.pack(side=tk.RIGHT, padx=5, pady=5, fill=tk.X, expand=True)
        self.command_entry.bind("<Return>", lambda event: self._get_command())

        # "Request Last File" button
        self.last_file_button = tk.Button(command_frame, text="Request Last File", command=self._request_last_file)
        self.last_file_button.pack(side=tk.LEFT, padx=5, pady=5)

        # History - split into two parts
        # History - split into two parts with equal width using grid
        history_frame.grid_rowconfigure(0, weight=1)
        history_frame.grid_columnconfigure(0, weight=1)
        history_frame.grid_columnconfigure(1, weight=1)

        # Left Frame
        left_history_frame = tk.Frame(history_frame, bg="white")
        left_history_frame.grid(row=0, column=0, sticky="nsew")

        left_title = tk.Label(left_history_frame, text="Command History", font=("Arial", 12, "bold"), bg="white")
        left_title.pack(side=tk.TOP, anchor="w", padx=5, pady=(5, 0))

        left_text_container = tk.Frame(left_history_frame, bg="white")
        left_text_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left Text + Scrollbar using grid
        self.history_text = tk.Text(left_text_container, wrap=tk.WORD, bg="white", state="disabled", height=8)
        self.history_text.grid(row=0, column=0, sticky="nsew")

        history_scrollbar = tk.Scrollbar(left_text_container, orient=tk.VERTICAL, command=self.history_text.yview)
        history_scrollbar.grid(row=0, column=1, sticky="ns")

        left_text_container.grid_rowconfigure(0, weight=1)
        left_text_container.grid_columnconfigure(0, weight=1)

        self.history_text.config(yscrollcommand=history_scrollbar.set)

        # Right Frame
        right_msg_frame = tk.Frame(history_frame, bg="white")
        right_msg_frame.grid(row=0, column=1, sticky="nsew")

        right_title = tk.Label(right_msg_frame, text="Messages from Clients", font=("Arial", 12, "bold"), bg="white")
        right_title.pack(side=tk.TOP, anchor="w", padx=5, pady=(5, 0))

        right_text_container = tk.Frame(right_msg_frame, bg="white")
        right_text_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Right Text + Scrollbar using grid
        self.client_msg_text = tk.Text(right_text_container, wrap=tk.WORD, bg="white", state="disabled", height=8)
        self.client_msg_text.grid(row=0, column=0, sticky="nsew")

        msg_scrollbar = tk.Scrollbar(right_text_container, orient=tk.VERTICAL, command=self.client_msg_text.yview)
        msg_scrollbar.grid(row=0, column=1, sticky="ns")

        right_text_container.grid_rowconfigure(0, weight=1)
        right_text_container.grid_columnconfigure(0, weight=1)

        self.client_msg_text.config(yscrollcommand=msg_scrollbar.set)


        # Client List Section (Moves text down)
        client_bottom_frame = tk.Frame(client_list_frame, bg="lightblue")
        client_bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 5))

        # Create a frame for buttons
        client_bottom_frame = tk.Frame(self.root)
        client_bottom_frame.pack(padx=10, pady=10)

        # Define buttons and their commands in the admin left side grid
        buttons = [
            ("Block", self.block_client),
            ("Unblock", self.unblock_client),
            ("Screenshot", self.screenshot),
            ("Help", self.help),
            ("GetGrades", self.GetGrades),
            ("SetGrade", self.Grade),
            ("SendFile", self.SendFile),
            ("Paint", self._open_paint),
            ("Test", self.Test),
            ("Test Status", lambda: self.show_test_status(refresh=True)),
            ("Msg", self.Msg),
            ("Remove Client", self.Remove_Client)
        ]

        # Place buttons in a grid
        for i, (text, command) in enumerate(buttons):
            btn = tk.Button(client_bottom_frame, text=text, command=command, width=12)
            btn.grid(row=i // 2, column=i % 2, padx=5, pady=5, sticky="nsew")

        # Configure grid to expand properly
        for i in range(2):  
            client_bottom_frame.columnconfigure(i, weight=1)
        for i in range(3):  
            client_bottom_frame.rowconfigure(i, weight=1)

        # The label
        tk.Label(client_bottom_frame, text="Connected Clients:", font=("Arial", 12)).grid(row=6, column=0, columnspan=2, pady=(10, 2))

        # Frame for Listbox & Scrollbar
        listbox_frame = tk.Frame(client_bottom_frame)
        listbox_frame.grid(row=7, column=0, columnspan=2, sticky="nsew", padx=5, pady=(5, 2))

        # Listbox with Scrollbar
        self.client_listbox = tk.Listbox(listbox_frame, font=("Arial", 11), height=9) 
        self.client_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.client_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.client_listbox.config(yscrollcommand=scrollbar.set)

        
        # Screenshot Section
        self.screenshot_canvas = tk.Canvas(screenshot_frame, bg="black")
        self.screenshot_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)


        self.root.mainloop()


    def enable_screenshot_scroll(self, width):
        """Enable scrollbar and mouse wheel scrolling on screenshot canvas."""
        try:
            self.screenshot_canvas.bind("<MouseWheel>", self._on_mousewheel)

            # Check if scrollbar exists, if not, create it
            if not hasattr(self, 'screenshot_scrollbar') or not self.screenshot_scrollbar.winfo_exists():
                self.screenshot_scrollbar = tk.Scrollbar(self.screenshot_canvas.master, orient=tk.VERTICAL, command=self.screenshot_canvas.yview)
                self.screenshot_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            else:
                if not self.screenshot_scrollbar.winfo_ismapped():
                    self.screenshot_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            self.screenshot_canvas.config(yscrollcommand=self.screenshot_scrollbar.set)
            self.screenshot_canvas.config(scrollregion=(0, 0, 1000, width))  # Set a big scrollable area
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def disable_screenshot_scroll(self):
        """Disable scrollbar and mouse wheel scrolling on screenshot canvas."""
        try:
            self.screenshot_canvas.unbind("<MouseWheel>")

            if hasattr(self, 'screenshot_scrollbar') and self.screenshot_scrollbar.winfo_exists():
                self.screenshot_scrollbar.pack_forget()

            self.screenshot_canvas.config(yscrollcommand=None)

            self.screenshot_canvas.yview_moveto(0)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")


    def _start_client_msg_clientlist_listener(self):
        print ("_start_client_msg_clientlist_listener")
        def listen_for_server_messages_clientlist():
            print("Inside listen_for_server_messages")
            try:
                while True:
                    print("trying to get message")
                    message = self.msg_clientlist_socket.recv(4096).decode() #.recv(4096).decode("utf-8")
                    print("got message")
                    if not message:
                        break

                    if message == "refresh client list, new client connected":
                        # reply for an auto refresh as sent by the server to the admin
                        print("refresh client list, new client connected")
                        self._refresh_client_list()
                        self._log_history("new client connected")
                    elif message == "refresh client list, admin connected":
                        # reply for an auto refresh as sent by the server to the admin
                        print("refresh client list, admin connected")
                        self._refresh_client_list()
                        self._log_history("admin connected")
                    elif message.startswith("msg"):
                        # accepting messages from client (through server) and display on right button side.
                        msg = message.split("msg") [1]
                        self._log_client_message(msg)
                    elif "has been disconnected" in message:
                        self._refresh_client_list()
                        print("refresh client list, a client_disconnected")
                        client_disconnected = message.split(" ")[1]
                        print("client_disconnected- ", client_disconnected)
                        self._log_history(f"{client_disconnected} has been disconnected")

            except Exception as e:
                print ("admin disconnected forcefully")
                self._log_history(f"Error in server message listener: {e}")
                if self.shutdown == False:
                    self.root.destroy()

        thread = threading.Thread(target=listen_for_server_messages_clientlist)
        thread.daemon = True
        thread.start()

    

    """
    paint on a last file defs:
    """

    # open the painter
    def _open_paint(self): 
        try:
            if not hasattr(self, "screenshot_canvas") or not hasattr(self.screenshot_canvas, "image"):
                messagebox.showwarning("Paint Error", "No image available to paint on.")
                return

            # Create a pop-up paint tool window
            self.paint_window = tk.Toplevel(self.root)
            self.paint_window.title("Paint Tool")
            self.paint_window.geometry("350x150")
            self.paint_window.configure(bg="#2C3E50")

            # UI elements
            tk.Label(self.paint_window, text="Color:", fg="white", bg="#2C3E50", font=("Arial", 12)).grid(row=0, column=0, padx=10, pady=10)
            self.color_var = tk.StringVar(value="red")
            colors = ["red", "blue", "green", "black", "yellow", "purple", "orange"]
            self.color_menu = ttk.Combobox(self.paint_window, textvariable=self.color_var, values=colors, state="readonly", width=10)
            self.color_menu.grid(row=0, column=1, padx=10, pady=10)

            tk.Label(self.paint_window, text="Brush Size:", fg="white", bg="#2C3E50", font=("Arial", 12)).grid(row=1, column=0, padx=10, pady=10)
            self.brush_size = tk.IntVar(value=3)
            self.brush_size_slider = ttk.Scale(self.paint_window, from_=1, to=20, variable=self.brush_size, orient=tk.HORIZONTAL, length=150)
            self.brush_size_slider.grid(row=1, column=1, padx=10, pady=10)

            button_frame = tk.Frame(self.paint_window, bg="#2C3E50")
            button_frame.grid(row=2, column=0, columnspan=2, pady=10)

            tk.Button(button_frame, text="Clear", command=self._clear_canvas, bg="#E74C3C", fg="white", font=("Arial", 10, "bold"), width=8).pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="Send file", command=self._send_paint, bg="#27AE60", fg="white", font=("Arial", 10, "bold"), width=8).pack(side=tk.LEFT, padx=5)

            self.screenshot_canvas.bind("<B1-Motion>", self._paint)

        except Exception as e:
            print(f"Error while opening paint tool: {e}")
            messagebox.showerror("Paint Tool Error", f"An unexpected error occurred: {e}")       


    # paint
    def _paint(self, event):
        try:
            x, y = event.x, event.y
            r = int(self.brush_size.get())
            color = self.color_var.get()
            self.screenshot_canvas.create_oval(x - r, y - r, x + r, y + r, fill=color, outline=color)
        except Exception as e:
            print(f"Error while painting: {e}")
            messagebox.showerror("Paint Error", f"An error occurred while painting: {e}")

    # clearing the canvas
    def _clear_canvas(self):
        self.screenshot_canvas.delete("all")

    # sending the updated painted image
    def _send_paint(self):
        try:
            
            file_path = "painted_image.png"

            self.paint_window.iconify()
            self.paint_window.destroy()
            time.sleep(0.1)
            # Get canvas position
            x = self.screenshot_canvas.winfo_rootx()
            y = self.screenshot_canvas.winfo_rooty()
            width = x + self.screenshot_canvas.winfo_width()
            height = y + self.screenshot_canvas.winfo_height()

            # Capture only the canvas area
            image = ImageGrab.grab(bbox=(x, y, width, height))

            # Save as PNG (optimized)
            image.save(file_path, "PNG", optimize=True, compress_level=9)

            # Send to client
            client_ip = self._choose_client()
            if self.test_status.get(client_ip, False):
                messagebox.showinfo("error", f"{client_ip} is currently taking a test - cannot send paint to him.")
                return
            elif client_ip:
                print(client_ip)
                print(type(client_ip))
                #self._send_image_to_server(file_path, client_ip)
                self._send_command("SENDFILE1 painted_image.png: "+client_ip)
                
        except Exception as e:
            print(f"Error while sending painted image: {e}")
            messagebox.showerror("Send Paint Error", f"An error occurred while sending the painted image: {e}")       
        
    # defs for different functions:
            
    def block_client(self):
        try:
            client_name = self._choose_client()
            print (client_name)
            if client_name:
                command = f"BLOCK: {client_name}"
                self._send_command(command)               
        except Exception as e:
            print(f"Error while blocking client: {e}")
            messagebox.showerror("Block Client Error", f"An error occurred while blocking the client: {e}")


    def unblock_client(self):
        try:
            client_name = self._choose_client()
            print(client_name)
            if client_name:
                command = f"UNBLOCK: {client_name}"
                self._send_command(command)
        except Exception as e:
            print(f"Error while unblocking client: {e}")
            messagebox.showerror("UnBlock Client Error", f"An error occurred while blocking the client: {e}")


    def screenshot(self):
        try:
            client_name = self._choose_client(allow_all=False)
            print(client_name)
            if client_name:
                # Disable the last file button
                self.last_file_button.config(state=tk.DISABLED)

                command = f"SCREENSHOT: {client_name}"
                self._send_command(command)
        except Exception as e:
            print(f"Error while taking screenshot: {e}")
            messagebox.showerror("Screenshot Error", f"An error occurred while taking the screenshot: {e}")


    def help(self):
        self._send_command("HELP")

    def GetGrades(self):
        self._send_command("GETGRADES")

    def Grade(self):
        try:
            client_name = self._choose_client(allow_all=False)
            if client_name:
                if self.test_status.get(client_name, False):
                    messagebox.showinfo("error", f"{client_name} is currently taking a test - cannot set grade for him.")
                    return
                root = tk.Tk()
                root.withdraw()  # Hide the root window
                
                grade = simpledialog.askinteger("Enter the grade", "Enter a grade between 0-100:", minvalue=0, maxvalue=100)
                
                if grade is not None:
                    self._send_command(f"GRADE {grade}: {client_name}")

                    
                else:
                    messagebox.showinfo("Info", "No grade entered.")
        except Exception as e:
            print(f"Error while setting grade: {e}")
            messagebox.showerror("Grade Error", f"An error occurred while setting the grade: {e}")


    def SendFile(self):
        try:
            client_name = self._choose_client()
            if self.test_status.get(client_name, False):
                messagebox.showinfo("error", f"{client_name} is currently taking a test - cannot send file to him.")
                return
            elif client_name:
                print("client_name ", client_name)
                # Open File Explorer to choose a file
                file_path = filedialog.askopenfilename(filetypes=[("Text and PNG files", "*.txt;*.png")])

                if file_path:
                    file_name = os.path.basename(file_path)
                    command = f"SENDFILE {file_name}: {client_name}"
                    self.selected_file_info[command] = (file_path, file_name)  # Save full path for later use
                    print(f"Selected file: {file_name}")
                    self._send_command(command)
        except Exception as e:
            print(f"Error while sending file: {e}")
            messagebox.showerror("Send File Error", f"An error occurred while sending the file: {e}")



    def Test(self):
        try:
            client_name = self._choose_client()
            if client_name:
                if client_name.lower() == "all":
                    for client in self.connected_clients:
                        client_check = client.split("(")[0].strip()
                        if self.test_status.get(client_check, False):
                            print (f"{client_check} in test")
                            messagebox.showinfo("error", f"{client_check} is currently taking a test - cannot set another test for him.")
                            return
                if self.test_status.get(client_name, False):
                    messagebox.showinfo("error", f"{client_name} is currently taking a test - cannot create a new test for him.")
                    return
                elif client_name:
                    while True:
                        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])

                        if not file_path:
                            return  # User cancelled

                        file_name = file_path.split("/")[-1]  # Get file name

                        if "TEST" in file_name.upper():
                            print(f"Selected file: {file_name}")
                            self._send_command(f"SENDFILE1 {file_name}: {client_name}")
                            break
                        else:
                            messagebox.showwarning("Invalid File", "Please select a .txt file that contains the word 'TEST' in its name.")
        except Exception as e:
            print(f"Error while assigning test: {e}")
            messagebox.showerror("Test Error", f"An error occurred while assigning the test: {e}")
    

    def show_test_status(self, refresh=False):
        try:
            if not hasattr(self, "screenshot_canvas"):
                return

            if refresh:
                print("refresh")
                self._refresh_client_list()
            self.disable_screenshot_scroll()

            self.screenshot_canvas.delete("all")
            y = 10
            self.screenshot_canvas.create_text(
                10, y, text="--- Test Status ---", font=("Arial", 28), fill="white", anchor="nw")
            y += 40

            for client, status in self.test_status.items():
                color = "green" if status else "red"
                status_text = "In Test" if status else "Not in Test"
                self.screenshot_canvas.create_text(
                    10, y, text=f"{client}: {status_text}", font=("Arial", 22), fill=color, anchor="nw")
                y += 35

            self.screenshot_canvas.create_text(
                10, y, text="---------------------", font=("Arial", 28), fill="white", anchor="nw")
        except Exception as e:
            print(f"Error while showing test status: {e}")
            messagebox.showerror("Test Status Error", f"An error occurred while showing the test status: {e}")


    def Msg(self):
        try:
            self.command_entry.config(state="normal")
            self.command_entry.delete(0, tk.END)
            self.msg_mode = True
            self.command_entry.focus_set()
        except Exception as e:
            print(f"Error while enabling message mode: {e}")
            messagebox.showerror("Message Mode Error", f"An error occurred while enabling message mode: {e}")
    

    def Remove_Client(self):
        try:
            client_name = self._choose_client(allow_all=False) 
            if self.test_status.get(client_name, False):
                messagebox.showinfo("error", f"{client_name} is currently taking a test - cannot remove him.")
                return
            print (client_name)
            if client_name:
                command = f"REMOVE: {client_name}"
                self._send_command(command)
        except Exception as e:
            print(f"Error while removing client: {e}")
            messagebox.showerror("Remove Client Error", f"An error occurred while removing the client: {e}")
    
             
    # choose client for functions
            
    def _choose_client(self, allow_all=True):
        try:
            if not self.connected_clients:
                self._refresh_client_list()
                if not self.connected_clients:
                    messagebox.showwarning("Client Selection", "No connected clients available.")
                    return None

            # Only add "ALL" if allowed
            client_options = ["ALL"] + self.connected_clients if allow_all else self.connected_clients

            client_selection = tk.Toplevel(self.root)
            client_selection.title("Select Client")
            client_selection.geometry("250x120")

            selected_client = tk.StringVar()
            user_confirmed = tk.BooleanVar(value=False)  # Track if user confirmed

            client_dropdown = ttk.Combobox(
                client_selection, textvariable=selected_client,
                values=client_options, state="readonly"
            )
            client_dropdown.pack(pady=10)
            client_dropdown.current(0)

            def confirm_selection():
                user_confirmed.set(True)
                client_selection.destroy()

            tk.Button(client_selection, text="Select", command=confirm_selection).pack(pady=5)

            client_selection.protocol("WM_DELETE_WINDOW", client_selection.destroy)  # Handle 'X' close
            client_selection.wait_window()

            if not user_confirmed.get():
                return None  # User closed the window with 'X'

            selected_client_name = selected_client.get()
            if selected_client_name and selected_client_name != "ALL":
                selected_client_name = selected_client_name.split("(")[0].strip()

            print(selected_client_name)
            return selected_client_name
        except Exception as e:
            print(f"Error while choosing client: {e}")
            messagebox.showerror("Choose Client Error", f"An error occurred while choosing the client: {e}")
            return None


        
    def handle_server_reply(self, command, client_name=None):
        # handling reply from server
        try:
            if client_name.lower() == "all":
                a = self.connected_clients
                print ("sendall in handle server reply")
            else:
                a= [client_name]
            for client in a:
                    print(f"Handling reply for client {client_name}\n")
                    try:
                        response = self.socket.recv(1024).decode()
                    except Exception as e:
                        print(f"Error getting response: {e}")
                        self._log_history(f"Error getting response: {e}")

                    
                    if response:                    
                        if response.startswith("SCREENSHOT SAVED AS"):
                            # Enable the last file button
                            self.last_file_button.config(state=tk.NORMAL)
                        elif "sent MSG you got a new grade" in response:
                            self._send_command("GETGRADES")
                            
                        self._log_history(f"Client {client_name} -> Command: {command}\nResponse: {response}\n")

                        if "is answering a test" in response:
                            c_name = response.split ("is") [0].strip()
                            self.test_status[c_name] = True
                            self.history_text.insert(tk.END, f"[INFO] Test status for {c_name}: Started\n")
                            print("self.test_status", self.test_status)
                            self.show_test_status()
                            # create a new socket on another port
                            print(f"{client_name} is answering a test... waiting up to 60 seconds for results")
                            threading.Thread(target=self.handle_test_answer, args=(), daemon=True).start()                        
                                          
        except Exception as e:
            print(f"Error getting reply from server: {e}")

            
    def handle_test_answer(self):
        # getting response from server of client's Test answers.
        try:
            second_response = self.test_socket.recv(1024).decode()
            if "TEST_ANSWER" in second_response:
                client_name = second_response.split(":")[1].strip()
                self.test_status[client_name] = False
                self.history_text.insert(tk.END, f"[INFO] Test status for {client_name}: Completed\n")
                print("self.test_status", self.test_status)
                self.show_test_status()
                self.history_text.insert(tk.END, f"[INFO] Test status for {client_name}: Completed\n")
                print(f"Received test answer from {client_name}: {second_response}")
                SetGrade= second_response.replace("TEST_ANSWER", "GRADE")
                self._send_command(f"{SetGrade}")
                self._log_history(f"Client {client_name} -> Test Answer: {second_response}\n")
        except Exception as e:
            print(f"Error handling test answer: {e}")

    def _get_command(self):
        # getting command from the command and sending it to client\s.
        try:
            if self.msg_mode:
                message = self.command_entry.get().strip()
                if not message:
                    messagebox.showwarning("Empty Message", "Please type a message before sending.")
                    return
                
                client_name = self._choose_client()
                if not client_name:
                    return  # User cancelled

                self._send_command(f"MSG {message}: {client_name}")
                self.command_entry.delete(0, tk.END)
                self.command_entry.config(state="disabled")
                self.msg_mode = False
            else:
                # Normal command behavior
                command = self.command_entry.get().strip()
                if command:
                    self._send_command(command)
                    self.command_entry.delete(0, tk.END)
        except Exception as e:
            print(f"Error in _get_command: {e}")
            self._log_history(f"Command entry error: {e}")
            
    def _send_command(self, command):
        #this def is sending commands to the server.
        
        try:
            # Ensure socket is open and connected
            if not self.socket or self.socket._closed:
                messagebox.showerror("Error", "No active connection. Please connect to the server.")
                return

            # Handle Help locally without sending to server
            elif command == "HELP":
                print ("in help, ", command)
                content = self._read_help()
                self.display_help()
                self._log_history(content)
                return

            # Request client list
            elif command == "CLIENTLIST":
                self._refresh_client_list()

            # Request grade list from server
            elif command == "GETGRADES":
                self.socket.sendall(command.encode())
                response = self.socket.recv(4096).decode()
                print(response)
                if response != "Database error occurred. Please try again later.":
                    response = "current grades:\n" + response
                # Estimate the height needed based on number of lines
                num_lines = response.count('\n') + 1
                print ("num_lines- ",num_lines)
                line_height = 30  # Approximate pixel height per line with font size 20
                total_height = num_lines * line_height + 200  # Some extra padding

                self.enable_screenshot_scroll(total_height)

                self.screenshot_canvas.delete("all")
                self.screenshot_canvas.create_text(10, 10, text=response, font=("Arial", 20), fill="white", anchor="nw")

            else:
                # Handle file transfer commands
                if "SENDFILE" in command:
                    if "SENDFILE1" in command: #handles sendfile from the same directory of the project
                        print ("command ", command)
                        file_name = command.split(':')[0].replace('SENDFILE1','').strip()
                        ip = command.split(':')[1] # need to also check for errors
                        with open(file_name, "rb") as f:
                            data = f.read()
                    else:   #handles sendfile from other directorys
                        print("command ", command)
                        file_info = self.selected_file_info.get(command)
                        if not file_info:
                            self._log_history("Error: File path info missing.")
                            return

                        file_path, file_name = file_info
                        ip = command.split(':')[1].strip()
                        with open(file_path, "rb") as f:
                            data = f.read()

                    checksum = hashlib.md5(data).hexdigest()
                    print(f"Sending file of size {len(data)} bytes with checksum {checksum}")

                    # Send file protocol commands
                    self.socket.sendall(command.encode())
                    self.socket.sendall(b"DATA_NAME") # fix: take the daniel.txt from the command
                    self.socket.sendall(file_name.encode())
                    self.socket.sendall(b"DATA_START")                   
                    self.socket.sendall(data)
                    self.socket.sendall(b"DATA_END")

                    print(f"Sent file {file_name} to server.")
                 
                    
                else: # including SCREENSHOT: supports BLOCK: ip, UNBLOCK: ip, MSG, GRADE, Remove, xxxx: IP
                      # add IMG xxxx: IP
                    print ("sending command - ",command.encode())
                    self.socket.sendall(command.encode())

                client_target = command.split(":")[1].strip()
 
                threading.Thread(target=self.handle_server_reply, args=(command, client_target), daemon=True).start()


                
        except Exception as e:
            self._log_history(f"Error sending command: {e}\n")
            

    def _log_history(self, message):
        # displays log history information in the bottom-left corner of the screen
        try:
            self.history_text.configure(state="normal")
            self.history_text.insert(tk.END, message + "\n")
            self.history_text.configure(state="disabled")
            self.history_text.see(tk.END)
        except Exception as e:
            if self.shutdown == False:
                print(f"Error logging history: {e}")
           

    def _log_client_message(self, message):
        # displays log messages from clients in the bottom-right corner of the screen
        try:
            self.client_msg_text.configure(state="normal")
            self.client_msg_text.insert(tk.END, message + "\n")
            self.client_msg_text.configure(state="disabled")
            self.client_msg_text.see(tk.END)
        except Exception as e:
            if self.shutdown == False:
                print(f"Error logging client's messages: {e}")

    def _refresh_client_list(self):
        # refrsh the client list by requasting from the server, and display it in a listbox at the left side

        if not self.socket:
            self._log_history("Cannot refresh client list: Not connected to server.")
            return

        try:

            # Send the CLIENTLIST request
            self.socket.sendall(b"CLIENTLIST")

            try:
                # Try to receive the response from the server
                response = self.socket.recv(1024).decode()
                print ("response of clientlist**",response,"&&")
                
                # Check if there are no clients connected
                if not response:
                    self._log_history("No clients connected to the server.")
                    self.client_listbox.delete(0, tk.END)
                    return

                self.client_listbox.delete(0, tk.END)
                self.connected_clients = response.split(", ") if response != "empty" else []

                # Remove clients from test_status if they're not in connected_clients
                for client in list(self.test_status.keys()):
                    if client not in [c.split("(")[0].strip() for c in self.connected_clients]:
                        del self.test_status[client]

                    
                if self.connected_clients == []:
                    self._log_history("No clients connected.")
                    return


                for client in self.connected_clients:
                    self.client_listbox.insert(tk.END, client)
                    c = client.split("(")[0].strip()
                    if c not in self.test_status:
                            self.test_status[c] = False

                client_list = ", ".join(self.connected_clients)
                self._log_history(f"Connected Clients: {client_list}\n")


            except:
                self._log_history("Error: No clients are connected.")

        except Exception as e:
            self._log_history(f"Error refreshing client list: {e}\n")




    def _request_last_file(self):
        # requasting last file for specific client from the server
        
        print ("in request last file")
        if not self.socket:
            messagebox.showwarning("Connection Error", "You must connect to the server first.")
            return

        try:
            self.disable_screenshot_scroll()
            client_name = self._choose_client(allow_all=False)
            if client_name:
                self.socket.sendall(f"LASTFILE - {client_name}".encode())
                chunk = self.socket.recv(1024)
                if chunk.decode().startswith("Error: No files found for client"):
                    print ("no last file from client - {client_name}")
                    self._log_history(f"no last file from client - {client_name}")
                    return
                elif "Error: No files found on server" not in chunk.decode():
                    # Start collecting file data
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
                        # Open and resize image for canvas
                        image = Image.open(BytesIO(data))
                        print ("before calc canvas_size")
                        canvas_width = self.screenshot_canvas.winfo_width()
                        canvas_height = self.screenshot_canvas.winfo_height()
                        image = image.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)

                        photo = ImageTk.PhotoImage(image)
                        self.screenshot_canvas.create_image(0, 0, image=photo, anchor=tk.NW)
                        self.screenshot_canvas.image = photo
                        self._log_history(f"Most recent file received and displayed from client- {client_name}.")
                    except Exception as e:
                        self._log_history(f"Error displaying the image: {e}")
                else:
                    print("there is no last file")
                    self._log_history(f"there is no last file")

        except Exception as e:
            self._log_history(f"Error receiving the most recent file: {e}")


    def _on_mousewheel(self, event):
        # This method allows the admin to scroll through the canvas display area
        self.screenshot_canvas.yview_scroll(int(-1*(event.delta/120)), "units")



if __name__ == "__main__":
    try:
        admin_ip = "192.168.1.26" 
        admin_port = 5000
        admin_test_port = 5002
        client_msg_clientlist_port = 5003
        AdminClient(admin_ip, admin_port, admin_test_port, client_msg_clientlist_port)
    except Exception as e:
        print(f"Fatal error starting AdminClient: {e}")

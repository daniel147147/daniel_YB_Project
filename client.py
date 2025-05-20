# client code

import socket
import ctypes 
import pyautogui
import time
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
import threading
import queue
from PIL import Image, ImageTk
import io
import ssl

class ClientApp:
    def __init__(self, master):
        self.root = root
        self.master = master
        self.master.title("Client Application")
        self.master.geometry("600x1200")
        self.master.config(bg="#f0f0f0")
        self.master.resizable(width=True, height=True)
        self.master.minsize(width=333, height=333) #width=666, height=666
        self.master.maxsize(width=400, height=400) #width=999, height=999
        
        self.connected = False
        self.shutdown = False
        self.name_accepted = True
        self.client_name = None
        self.timer_active = False  # Timer is initially inactive
        self.test_timer_id = None
        self.time_left = 60  # Default time for countdown
        self.create_name_screen()

    def create_name_screen(self):
        # name screen for entering client name
        try:
            self.name_frame = tk.Frame(self.master, bg="#f0f0f0")
            self.name_frame.pack(expand=True)

            tk.Label(self.name_frame, text="Enter your name:", font=("Arial", 14), bg="#f0f0f0").pack(pady=10)
            
            self.name_entry = tk.Entry(self.name_frame, font=("Arial", 14))
            self.name_entry.pack(pady=10)
            self.name_entry.bind("<KeyRelease>", self.validate_name)
            
            # Bind Enter key to self.name_entry
            self.name_entry.bind("<Return>", lambda event: self.submit_button.invoke())

            self.submit_button = tk.Button(self.name_frame, text="Submit", font=("Arial", 14), command=self.set_client_name, state=tk.DISABLED)
            self.submit_button.pack(pady=10)
        except Exception as e:
            messagebox.showerror("UI Error", f"Could not create name screen: {str(e)}")


    def validate_name(self, event):
        if self.name_entry.get().strip():
            self.submit_button.config(state=tk.NORMAL)
        else:
            self.submit_button.config(state=tk.DISABLED)
    def contains_hebrew(self, string):
        # function that check if the client name contains hebrew letters.
        for char in string:
            if '\u0590' <= char <= '\u05FF':  # Check if character is in the Hebrew Unicode range
                return True
        return False


    def set_client_name(self):
        # function that sets the client name and check for invalid names
        self.client_name = self.name_entry.get().strip()
        
        if "." in self.client_name :
            self.master.after(0, lambda: messagebox.showerror("Error", "You cannot set a name with dots"))
            self.name_frame.destroy()
            self.create_name_screen()
            return
        elif "(" in self.client_name :
            self.master.after(0, lambda: messagebox.showerror("Error", "You cannot set a name with '(' "))
            self.name_frame.destroy()
            self.create_name_screen()
            return
        elif "all" in self.client_name.lower():
            self.master.after(0, lambda: messagebox.showerror("Error", "You cannot set a name with the word- all"))
            self.name_frame.destroy()
            self.create_name_screen()
            return
        elif self.contains_hebrew(self.client_name.lower()):
            self.master.after(0, lambda: messagebox.showerror("Error", "You cannot set a name with Hebrew letters"))
            self.name_frame.destroy()
            self.create_name_screen()
            return
        self.name_frame.destroy()
        self.setup_ui()

    
    def setup_ui(self):
        # Adjust window limits
        self.master.minsize(width=666, height=999)
        self.master.maxsize(width=666, height=999)

        self.message_queue = queue.Queue()

        # Client Title Section
        self.top_frame = tk.Frame(self.master, bg="#f0f0f0")
        self.top_frame.pack(pady=10, padx=20, fill=tk.X)
        tk.Label(self.top_frame, text=f"Client: {self.client_name}", anchor="w", justify="left", bg="#f0f0f0", font=("Arial", 12), fg="black").pack(fill="both", expand=True)

        self.start_button = tk.Button(self.top_frame, text="Start Client", command=self.start_client, font=("Arial", 14), bg="#4CAF50", fg="white", relief="raised", bd=2)
        self.start_button.pack(pady=10)

        # Message Send Section
        self.send_frame = tk.Frame(self.master, bg="#f0f0f0")
        self.send_frame.pack(fill=tk.X, padx=20, pady=10)

        self.message_entry = tk.Entry(self.send_frame, font=("Arial", 16), bd=3, relief="sunken")
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=8)  # ipady makes it taller
        self.message_entry.bind("<Return>", self.send_message)

        self.send_button = tk.Button(self.send_frame, text="Send", font=("Arial", 14), bg="#4CAF50", fg="white",
                                     command=self.send_message, padx=15, pady=8)
        self.send_button.pack(side=tk.RIGHT)

        # Log Section
        self.log_frame = tk.Frame(self.master, bg="#f0f0f0", bd=2, relief="sunken")
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        tk.Label(self.log_frame, text="Log Messages", font=("Arial", 14), bg="#f0f0f0", anchor="w").pack(fill="x", padx=10)

        self.log_scrollbar = tk.Scrollbar(self.log_frame, orient="vertical")
        self.log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_display = tk.Text(self.log_frame, height=10, wrap=tk.WORD, font=("Arial", 12), bg="#e6e6e6", fg="black", padx=5, pady=5, state=tk.DISABLED)
        self.log_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.log_display.config(yscrollcommand=self.log_scrollbar.set)
        self.log_scrollbar.config(command=self.log_display.yview)

        # Message Display Section
        tk.Label(self.master, text="Messages", font=("Arial", 14), bg="#f0f0f0", anchor="w").pack(fill="x", padx=20, pady=5)

        # Create a frame for the message_display and scrollbar
        self.message_frame = tk.Frame(self.master)
        self.message_frame.pack(fill=tk.X, padx=20, pady=5)

        # Add Scrollbar for the message_display section
        self.message_scrollbar = tk.Scrollbar(self.message_frame, orient="vertical")
        self.message_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Create the message_display Text widget
        self.message_display = tk.Text(self.message_frame, height=5, wrap=tk.WORD, font=("Arial", 12), bg="white", fg="black", padx=5, pady=5, state=tk.DISABLED)
        self.message_display.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.message_display.config(yscrollcommand=self.message_scrollbar.set)
        self.message_scrollbar.config(command=self.message_display.yview)


        # File Display Section (Canvas)
        tk.Label(self.master, text="Received Files / Images", font=("Arial", 14), bg="#f0f0f0", anchor="w").pack(fill="x", padx=20, pady=5)

        self.canvas_frame = tk.Frame(self.master, bg="#f0f0f0")
        self.canvas_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.canvas_scrollbar = tk.Scrollbar(self.canvas_frame, orient="vertical")
        self.canvas_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas = tk.Canvas(self.canvas_frame, bg="white", yscrollcommand=self.canvas_scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas_scrollbar.config(command=self.canvas.yview)

        # Bind mouse wheel to canvas for scrolling
        self.canvas.bind_all("<MouseWheel>", self.on_mouse_wheel_canvas)
        # Download Button
        self.download_button = tk.Button(self.master, text="Download File", font=("Arial", 12),
                                         bg="#008CBA", fg="white", command=self.download_file)
        self.download_button.pack(pady=5)
        self.download_button.config(state=tk.DISABLED)  # Disabled until a file is received


        # Networking Setup
        self.server_ip = "192.168.1.26"
        self.client_port = 5001
        self.client_socket = None
        self.running = False
        self.user32 = ctypes.WinDLL('user32', use_last_error=True)
        self.master.after(100, self.process_queue)

    def send_message(self, event=None):
        # function to send messages to admin
        message = self.message_entry.get().strip()
        if self.running:
            if message:
                if self.contains_hebrew(message):
                    self.master.after(0, lambda: messagebox.showerror("Error", "You cannot send message with Hebrew letters"))
                    return
                self.message_display.config(state=tk.NORMAL)
                self.message_display.insert(tk.END, f"Me: {message}\n")
                self.message_display.config(state=tk.DISABLED)
                self.message_display.see(tk.END)

                self.client_socket.sendall(f"msg {self.client_name}: {message}".encode())
                self.message_entry.delete(0, tk.END)
            else:
                messagebox.showinfo("Empty Message", "Please type a message before sending.")
        else:
            messagebox.showinfo("Connection Error", "You must start the client first")

    def log_message(self, message):
        # log history messages
        self.message_queue.put(message)
    
    def widget_alive(self, widget):
        try:
            return widget.winfo_exists()
        except tk.TclError:
            return False

    def process_queue(self):
        try:
            if self.widget_alive(self.master):
                # Check if the log display widget exists and is still active
                if self.widget_alive(getattr(self, "log_display", None)):
                    # Drain the message queue
                    while not self.message_queue.empty():
                        message = self.message_queue.get_nowait()
                        self.log_display.config(state=tk.NORMAL)
                        self.log_display.insert(tk.END, message + "\n")
                        self.log_display.yview(tk.END)
                        self.log_display.config(state=tk.DISABLED)
                self.master.after(100, self.process_queue)
            else:
                print("Master window closed, stopping process_queue.")
        except Exception as e:
            print(f"Error in process_queue: {e}")



    def block_keyboard(self):
        # blocking mouse and keyboard
        self.user32.BlockInput(True)
        self.log_message("Keyboard is now blocked.")
        
    def unblock_keyboard(self):
        # unblocking mouse and keyboard
        self.user32.BlockInput(False)
        self.log_message("Keyboard is now unblocked.")

    def take_screenshot(self):
        try:
            # Generate a filename based on the current date and time
            current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            screenshot_filename = f"PICTURE_{current_time}.png"
            # Take a screenshot using pyautogui and save it locally
            screenshot = pyautogui.screenshot()
            screenshot.save(screenshot_filename)
            self.log_message(f"Screenshot saved as {screenshot_filename}")

            try:
                print ("sending screenshot to server")
                self.client_socket.sendall(b"PIC_START")

                # Open the screenshot file in binary mode and read it in chunks
                with open(screenshot_filename, "rb") as f: 
                    num = 0
                    while True:
                        num+=1
                        chunk = f.read(1024)
                        if not chunk:
                            break  # Stop when the file is fully read

                        self.client_socket.sendall(chunk)  # Send chunk
                        # print ("sent chunk ",num)
                
                self.client_socket.sendall(b"PIC_END")
                print("Screenshot sent successfully.")

            except Exception as e:
                self.log_message(f"Failed to send screenshot: {e}")
        except Exception as e:
            self.log_message(f"Error taking screenshot: {e}")

    def load_questions_from_content(self, content):
        # load questions from test
        try:
            # Step 1: Decode the content from bytes to a string, and split into lines
            lines = content.decode().splitlines()

            questions = []
            current_question = None
            # Step 2: Loop through each line to build question blocks
            for line in lines:
                line = line.strip()
                if line.startswith("Question"):
                    if current_question:
                        questions.append(current_question)
                    current_question = {"question": line, "options": [], "answer": None}
                elif line.startswith("Answer:"):
                    current_question["answer"] = int(line.split(":")[1].strip())
                elif line and current_question:
                    current_question["options"].append(line)
            # Step 3: After loop ends, save the last question if it exists
            if current_question:
                questions.append(current_question)

            return questions
        except Exception as e:
            self.log_message(f"Failed to load questions: {e}")
            return []  # Return an empty list on failure


    def check_answers(self, selected_answers, questions):
        # checking test answer
        try:
            print ("check_answers")
            score = 0
            for i, var in enumerate(selected_answers):
                if var.get () == questions[i]["answer"]:
                    score += 1
            # Calculate percentage grade
            s = int((score / len(questions)) * 100)
            # Send the score to the server
            self.client_socket.sendall(f"TEST_ANSWER {s}: {self.client_name}".encode())
            print ("sent")
            #self.client_socket.sendall(b"TEST_ANSWER 2")
            messagebox.showinfo("Results", f"You got {score}/{len(questions)} correct!")
        except Exception as e:
            self.log_message(f"Error checking answers: {e}")
            messagebox.showerror("Error", f"An error occurred while checking answers: {e}")

    def create_test_gui(self, filename):
        # creating the test
        try:
            # Step 1: Load questions from the received file content
            questions = self.load_questions_from_content(self.received_file_content)

            # Step 2: Setup canvas for test display
            self.canvas.delete("all")
            scrollable_frame = tk.Frame(self.canvas, bg="#ffffff")
            window_id = self.canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

            def update_scroll_region(event=None):
                self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
            scrollable_frame.bind("<Configure>", update_scroll_region)

            def on_canvas_resize(event):
                canvas_width = event.width
                self.canvas.itemconfig(window_id, width=canvas_width)

            self.canvas.bind("<Configure>", on_canvas_resize)

            # Step 3: Initialize selected answers and submit button
            selected_answers = []
            submit_button = None

            def check_all_answered(*args):
                # Check if all questions have been answered
                all_answered = all(var.get() != 0 for var in selected_answers)
                if all_answered:
                    submit_button.config(state=tk.NORMAL)

            # Step 4: Reset timer and start countdown
            self.timer_active = True
            self.time_left = 60

            # Countdown
            def countdown(time_left):
                if not self.timer_active:
                    return
                if time_left <= 0:
                    self.timer_active = False
                    self.submit_and_disable(submit_button, selected_answers, questions)
                    messagebox.showinfo("Time's up", "Your test has been submitted.")
                else:
                    timer_label.config(text=f"⏱ Time left: {time_left}s")
                    self.test_timer_id = self.canvas.after(1000, countdown, time_left - 1)

            # RED and BIG countdown timer
            timer_label = tk.Label(scrollable_frame, text=f"⏱ Time left: {self.time_left}s",
                                   font=("Arial", 20, "bold"), fg="red", bg="white")
            timer_label.pack(side="right", padx=20, pady=10)

            countdown(self.time_left)

            # Step 5: Loop through questions and display them
            for i, q in enumerate(questions):
                tk.Label(scrollable_frame, text=q["question"], font=("Arial", 16, "bold"),
                         bg="white", wraplength=700, justify="left", anchor="w", pady=5).pack(anchor="w", padx=10)

                var = tk.IntVar()
                var.trace_add("write", check_all_answered)
                selected_answers.append(var)

                for idx, option in enumerate(q["options"]):
                    tk.Radiobutton(scrollable_frame, text=option, variable=var, value=idx + 1,
                                   bg="white", anchor="w", justify="left", font=("Arial", 15)).pack(anchor="w", padx=20, pady=2)
            # Step 6: Submit button (disabled until all questions are answered)
            submit_button = tk.Button(scrollable_frame, text="Submit",
                                      command=lambda: self.submit_and_disable(submit_button, selected_answers, questions),
                                      bg="#28a745", activebackground="#218838", fg="white",
                                      font=("Arial", 14, "bold"), padx=10, pady=6,
                                      state=tk.DISABLED)
            submit_button.pack(pady=20)
        except Exception as e:
            self.log_message(f"Error creating test GUI: {e}")
            messagebox.showerror("Error", f"An error occurred while creating the test interface: {e}")



    def submit_and_disable(self, button, selected_answers, questions):
        try:
            self.timer_active = False  # Stop the timer immediately
            # Check answers and disable the submit button
            self.check_answers(selected_answers, questions)
            button.config(state=tk.DISABLED)
            # Clear the canvas after submission
            self.canvas.delete("all")
        except Exception as e:
            self.log_message(f"Error submitting answers: {e}")
            messagebox.showerror("Error", f"An error occurred while submitting the answers: {e}")


    def handle_message(self, message):
        # handle reccived messages from server
        try:
            # Handle block/unblock requests
            if message.startswith(b"BLOCK"):
                self.log_message("Received block request")
                self.block_keyboard()

            elif message.startswith(b"UNBLOCK"):
                self.unblock_keyboard()

            # Handle removal request - cleanup
            elif message.startswith(b"REMOVE"):
                self.cleanup(confirm=False)

            # message from admin
            elif message.startswith(b"MSG"):  
                msg = message.decode()[3:].strip()  # Remove "MSG" prefix and strip extra spaces
                self.log_message(f"Received message: {msg}")
                self.display_message(f"admin: {msg}")  # Display the message in the Text widget

            # Handle file data transfer (e.g., .txt files or png image data)
            elif message.startswith(b"DATA_NAME"):
                while b"DATA_END" not in message:
                    chunk = self.client_socket.recv(1024)
                    message += chunk
                message = message.replace(b'DATA_NAME', b'').replace(b'DATA_END', b'')
                msg = message.split(b'DATA_START')
                file_name = msg[0].strip().decode()
                content = msg[1].strip()

                self.log_message(f"Received data file: {file_name}")
                
                self.received_filename = file_name
                self.received_file_content = content  # Store content for downloading
                self.download_button.config(state=tk.NORMAL)  # Enable download button
                
                self.canvas.delete("all")
                if ".txt" in file_name.lower(): # Handle text file
                    if "test" in file_name.lower(): # Handle test file
                        print("answering a test")
                        self.client_socket.sendall(f"{self.client_name} is answering a test".encode())
                        self.download_button.config(state=tk.DISABLED)  # Disabled until finish test
                        self.create_test_gui(file_name)
                    else: # Regular text file
                        print ("regular file")
                        content = content.replace(b'\n', b'')
                        self.canvas.create_text(10, 10, text=content, font=("Arial", 14), fill="blue", anchor="nw")
                else: # Handle non-text files (png)
                    try:
                        image_data = io.BytesIO(content)
                        image = Image.open(image_data)
                        photo = ImageTk.PhotoImage(image)
                        self.canvas.image = photo  # Keep a reference to the image
                        self.canvas.create_image(10, 10, anchor="nw", image=photo)
                    except:
                        self.log_message("Error processing image")
                        
                self.canvas.config(scrollregion=self.canvas.bbox("all"))

            # Handle screenshot requests
            elif message.startswith(b"SCREENSHOT"):
                self.take_screenshot()
            else:
                self.log_message(f"Unknown command: {message}") # Log unknown message types
                
        except Exception as e:
            self.log_message(f"Error handling message: {e}")  # Log any errors that occur during message handling

    def download_file(self):
        # download txt or png files
        try:
            if hasattr(self, "received_filename") and hasattr(self, "received_file_content"):
                try:
                    # Attempt to save the file content to disk
                    with open(self.received_filename, "wb") as f:
                        f.write(self.received_file_content)
                    self.log_message(f"File downloaded: {self.received_filename}")
                except Exception as e:
                    self.log_message(f"Error saving file: {e}")
            else:
                # Handle the case where no file content is available
                self.log_message("No file to download.")
                
        except Exception as e:
            # Catch any exceptions during the file-saving process and log the error
            self.log_message(f"Error saving file: {e}")


    def display_message(self, msg):
        # displaying messages
        try:
            self.message_display.config(state=tk.NORMAL)
            self.message_display.insert(tk.END, msg + "\n")
            self.message_display.yview(tk.END)
            self.message_display.config(state=tk.DISABLED)
        except Exception as e:
            self.log_message(f"Error displaying message: {e}")  # Log any errors that occur

    def start_client(self):
        print ("starting client")
        self.start_button.config(state=tk.DISABLED) # Disable the start button
        if not self.running:
            self.running = True
            threading.Thread(target=self.run_client, daemon=True).start()
            

    def run_client(self):
        # this function is running the client, checking with the server if the name is already exists, and listening for messages
        while True and self.running:  # Keep retrying until we successfully connect
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False  # Disable hostname verification
                ssl_context.verify_mode = ssl.CERT_NONE  # Don't require a trusted CA

                self.client_socket = ssl_context.wrap_socket(sock, server_hostname=self.server_ip)
                try:
                    self.client_socket.connect((self.server_ip, self.client_port))
                    self.connected = True
                    self.log_message("Connected to the server. Waiting for messages...")
                except ConnectionRefusedError as e:
                    if self.connected == False:
                        self.running = False
                    # Handle the case where the connection is refused
                    print(f"Connection refused: {e}")
                    self.log_message("Connection refused. Server might not be running.")
                    self.start_button.config(state=tk.NORMAL)
                    return  # Exit the loop or retry if you want

                # Send client name to server
                name_message = f"{self.client_name}".encode()
                print ("sending client name to server ",name_message,"&&")
                self.client_socket.sendall(name_message)


                # Receive server response
                response = self.client_socket.recv(1024).decode().strip()
                print(f"[CLIENT] Server responded with: '{response}'")  # Debug log

                if response.lower() == "ok":
                    print(f"[CLIENT] Name '{self.client_name}' accepted! Proceeding to main chat...")
                    self.name_accepted = True
                else:
                    print(f"[CLIENT] Name '{self.client_name}' was rejected. Re-entering name selection...")
                    self.log_message("Error: Client name already in use. Restarting name entry...")

                    # Close socket before restarting
                    self.client_socket.close()
                    self.client_socket = None
                        
                    # Destroy all widgets inside master, but not master itself
                    for widget in self.master.winfo_children():
                        widget.destroy()

                    # Show error
                    self.master.after(0, lambda: messagebox.showerror("Error", "Client name already in use"))

                    # Go back to the name selection screen
                    self.create_name_screen()

                    #self.running = False
                    self.name_accepted = False
                    return

                # Handle messages normally after successful connection
                while self.running:
                    if self.shutdown:  # <-- Check if shutting down
                        break
                    print ("awaiting message from server")
                    message = self.client_socket.recv(1024)
                    if not message:
                        print ("server ended connection")
                        break
                    self.handle_message(message)


            except Exception as e:
                print ("error in client")
                self.log_message(f"Error on client: {e}")
                self.client_socket = None  # Ensure socket is reset on failure
            
            finally:
                if self.name_accepted == True:
                    if self.client_socket:  # Only clean up if a valid connection was made
                        if self.running:
                            self.cleanup(confirm=False) #confirm=True
                else:
                    print("name didnt accepted")
                    break


    def cleanup(self, confirm=True):
        # cleanning up the client and closing
        print("in cleanup")
        if confirm:
            if not messagebox.askokcancel("Quit", "Are you sure you want to exit?"):
                return
        try:
            msg = f"shutting down - {self.client_name}"
            print("msg- ", msg)              
            self.client_socket.sendall(msg.encode())
            print("Cleaning up before exit...")
            self.running = False
            self.shutdown = True  # <-- Set shutdown flag
            try:
                if self.client_socket:
                    #self.client_socket.close()
                    self.log_message("Disconnected from the server.")
            except Exception as e:
                print("Socket close error:", e)

            print("cleaned up successfully")

            #if confirm:
            self.root.destroy()
        except:
            print ("not connected to server, clean up")
            self.root.destroy()


    def on_mouse_wheel_canvas(self, event):
        # allow mouse wheel on canvas
        if event.delta > 0:
            self.canvas.yview_scroll(-1, "units")
        else:
            self.canvas.yview_scroll(1, "units")



if __name__ == "__main__":
    root = tk.Tk()
    app = ClientApp(root)


    def on_close():
        app.cleanup(confirm=True)  # shows messagebox on "X" button

        
    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()

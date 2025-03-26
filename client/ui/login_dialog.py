import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import sys
import os

# Add parent directory to path to import client module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from chat_client import ChatClient

class LoginDialog:
    def __init__(self, root, client):
        self.root = root
        self.client = client
        self.is_registered = False
        self.dialog = tk.Toplevel(root)
        self.dialog.title("Chat Login")
        self.dialog.geometry("350x300")
        self.dialog.resizable(False, False)
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_close)
        self.dialog.transient(root)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        self.create_widgets()
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        self.title_label = ttk.Label(main_frame, text="Login to Chat App", font=("Helvetica", 16, "bold"))
        self.title_label.pack(pady=(0, 20))
        
        # Error message
        self.error_var = tk.StringVar()
        self.error_label = ttk.Label(main_frame, textvariable=self.error_var, foreground="red", wraplength=300)
        self.error_label.pack(pady=(0, 10))
        self.error_label.pack_forget()  # Initially hidden
        
        # Form frame
        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill=tk.X, pady=10)
        
        # Username
        ttk.Label(form_frame, text="Username:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.username_var = tk.StringVar()
        self.username_entry = ttk.Entry(form_frame, textvariable=self.username_var, width=30)
        self.username_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Password
        ttk.Label(form_frame, text="Password:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(form_frame, textvariable=self.password_var, show="*", width=30)
        self.password_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Auth mode radio buttons
        auth_frame = ttk.Frame(main_frame)
        auth_frame.pack(fill=tk.X, pady=10)
        
        self.auth_mode = tk.StringVar(value="login")
        self.login_radio = ttk.Radiobutton(auth_frame, text="Login", variable=self.auth_mode, value="login", command=self.update_ui)
        self.login_radio.pack(side=tk.LEFT, padx=10)
        
        self.register_radio = ttk.Radiobutton(auth_frame, text="Register", variable=self.auth_mode, value="register", command=self.update_ui)
        self.register_radio.pack(side=tk.LEFT, padx=10)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        self.action_button = ttk.Button(button_frame, text="Login", command=self.on_action)
        self.action_button.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        self.quit_button = ttk.Button(button_frame, text="Quit", command=self.on_close)
        self.quit_button.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        self.username_entry.focus_set()
        
    def update_ui(self):
        auth_mode = self.auth_mode.get()
        if auth_mode == "login":
            self.action_button.config(text="Login")
            self.title_label.config(text="Login to Chat App")
        else:
            self.action_button.config(text="Register")
            self.title_label.config(text="Register for Chat App")
            
        self.error_var.set("")
        self.error_label.pack_forget()
        
    def on_action(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()
        
        if not username or not password:
            self.error_var.set("Username and password cannot be empty")
            self.error_label.pack(pady=(0, 10))
            return
            
        if self.auth_mode.get() == "login":
            self.on_login()
        else:
            self.on_register()
            
    def on_login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()
        
        success, message = self.client.login(username, password)
        
        if success:
            self.is_registered = True
            self.dialog.destroy()
        else:
            self.error_var.set(message)
            self.error_label.pack(pady=(0, 10))
            
    def on_register(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()
        
        success, message = self.client.register_user(username, password)
        
        if success:
            self.is_registered = True
            self.dialog.destroy()
        else:
            self.error_var.set(message)
            self.error_label.pack(pady=(0, 10))
            
    def on_close(self):
        if not self.is_registered:
            if messagebox.askokcancel("Quit", "Do you want to quit the application?", parent=self.dialog):
                self.root.quit()
        else:
            self.dialog.destroy()
            
    def get_result(self):
        return self.is_registered

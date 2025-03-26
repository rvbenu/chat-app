import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import sys
import os
from datetime import datetime

# Add parent directory to path to import client module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from chat_client import ChatClient
import chat_pb2

class ChatWidget(ttk.Frame):
    def __init__(self, parent, client, peer_username):
        super().__init__(parent)
        self.client = client
        self.peer_username = peer_username
        self.messages = {}  # message_id -> Message
        
        self.create_widgets()
        self.load_messages()
        
    def create_widgets(self):
        # Title label
        self.title_label = ttk.Label(
            self, 
            text=f"Conversation with {self.peer_username}", 
            font=("Helvetica", 12, "bold")
        )
        self.title_label.pack(pady=10)
        
        # Messages list with scrollbar
        messages_frame = ttk.Frame(self)
        messages_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.messages_listbox = tk.Listbox(
            messages_frame, 
            height=15, 
            width=50, 
            selectmode=tk.SINGLE
        )
        messages_scrollbar = ttk.Scrollbar(messages_frame, orient=tk.VERTICAL, command=self.messages_listbox.yview)
        self.messages_listbox.config(yscrollcommand=messages_scrollbar.set)
        
        self.messages_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        messages_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Message input
        input_frame = ttk.Frame(self)
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.message_var = tk.StringVar()
        self.message_entry = ttk.Entry(input_frame, textvariable=self.message_var, width=40)
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.message_entry.bind("<Return>", self.on_send)
        
        self.send_button = ttk.Button(input_frame, text="Send", command=self.on_send)
        self.send_button.pack(side=tk.RIGHT)
        
        # Delete button
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.delete_button = ttk.Button(
            button_frame, 
            text="Delete Selected Message", 
            command=self.on_delete,
            state=tk.DISABLED
        )
        self.delete_button.pack(pady=5)
        
        # Bind events
        self.messages_listbox.bind("<<ListboxSelect>>", self.on_message_select)
        
    def add_message(self, message):
        message_id = message.id
        self.messages[message_id] = message
        
        # Format the message for display
        timestamp = datetime.fromtimestamp(message.timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")
        if message.sender == self.client.get_username():
            display_text = f"[{timestamp}] You: {message.content}"
        else:
            display_text = f"[{timestamp}] {message.sender}: {message.content}"
            
        # Add to listbox
        self.messages_listbox.insert(tk.END, display_text)
        self.messages_listbox.itemconfig(tk.END, {"message_id": message_id})
        
        # Scroll to the bottom
        self.messages_listbox.see(tk.END)
        
    def remove_message(self, message_id):
        # Remove from dictionary
        if message_id in self.messages:
            del self.messages[message_id]
            
        # Find and remove from listbox
        for i in range(self.messages_listbox.size()):
            if self.messages_listbox.itemcget(i, "message_id") == message_id:
                self.messages_listbox.delete(i)
                break
                
    def load_messages(self, count=0):
        # Clear existing messages
        self.messages_listbox.delete(0, tk.END)
        self.messages.clear()
        
        # Get messages from the server
        messages = self.client.get_messages(self.peer_username, count)
        
        # Add to the widget
        for message in messages:
            self.add_message(message)
            
    def on_send(self, event=None):
        content = self.message_var.get().strip()
        if not content:
            return
            
        success, error_message = self.client.send_message(self.peer_username, content)
        
        if success:
            self.message_var.set("")  # Clear the input
            # The message will be added when we receive it from the server
        else:
            messagebox.showerror("Error", error_message)
            
    def on_delete(self):
        selected = self.messages_listbox.curselection()
        if not selected:
            return
            
        index = selected[0]
        message_id = self.messages_listbox.itemcget(index, "message_id")
        
        success, error_message = self.client.delete_message(message_id)
        
        if not success:
            messagebox.showerror("Error", error_message)
            
    def on_message_select(self, event):
        selected = self.messages_listbox.curselection()
        if not selected:
            self.delete_button.config(state=tk.DISABLED)
            return
            
        index = selected[0]
        message_id = self.messages_listbox.itemcget(index, "message_id")
        
        # Only allow deleting own messages
        if message_id in self.messages:
            message = self.messages[message_id]
            is_own_message = (message.sender == self.client.get_username())
            self.delete_button.config(state=tk.NORMAL if is_own_message else tk.DISABLED)

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import sys
import os

# Add parent directory to path to import client module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from chat_client import ChatClient
from ui.chat_widget import ChatWidget
import chat_pb2

class MainWindow:
    def __init__(self, root, client):
        self.root = root
        self.client = client
        self.chat_widgets = {}  # peer_username -> ChatWidget
        self.unread_counts = {}  # username -> count
        
        # Set up client event handlers
        self.client.on_message_received = self.on_message_received
        self.client.on_message_deleted = self.on_message_deleted
        self.client.on_user_online = self.on_user_online
        self.client.on_user_offline = self.on_user_offline
        self.client.on_disconnected = self.on_disconnected
        
        # Set up the main window
        self.root.title("Chat Application")
        self.root.geometry("800x600")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.create_widgets()
        self.client.connect()
        
    def create_widgets(self):
        # Main paned window
        self.paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel (contacts)
        self.left_panel = ttk.Frame(self.paned_window)
        self.paned_window.add(self.left_panel, weight=1)
        
        # Welcome message
        self.welcome_label = ttk.Label(
            self.left_panel, 
            text=f"Welcome, {self.client.get_username()}!",
            font=("Helvetica", 12, "bold")
        )
        self.welcome_label.pack(pady=10)
        
        # Contacts list with scrollbar
        contacts_frame = ttk.LabelFrame(self.left_panel, text="Contacts")
        contacts_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.contacts_listbox = tk.Listbox(contacts_frame, height=15, selectmode=tk.SINGLE)
        contacts_scrollbar = ttk.Scrollbar(contacts_frame, orient=tk.VERTICAL, command=self.contacts_listbox.yview)
        self.contacts_listbox.config(yscrollcommand=contacts_scrollbar.set)
        
        self.contacts_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        contacts_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # New contact controls
        add_contact_frame = ttk.Frame(self.left_panel)
        add_contact_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.new_contact_var = tk.StringVar()
        self.new_contact_entry = ttk.Entry(add_contact_frame, textvariable=self.new_contact_var)
        self.new_contact_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        self.add_contact_button = ttk.Button(add_contact_frame, text="Add Contact", command=self.on_add_contact)
        self.add_contact_button.pack(side=tk.RIGHT)
        
        # Unread messages controls
        unread_frame = ttk.Frame(self.left_panel)
        unread_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.unread_count_var = tk.IntVar(value=10)
        unread_count_spinner = ttk.Spinbox(
            unread_frame, 
            from_=1, 
            to=100, 
            width=5, 
            textvariable=self.unread_count_var
        )
        unread_count_spinner.pack(side=tk.LEFT, padx=(0, 5))
        
        self.unread_button = ttk.Button(
            unread_frame, 
            text="Load Unread Messages", 
            command=self.on_unread_messages
        )
        self.unread_button.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        # Logout and delete account buttons
        button_frame = ttk.Frame(self.left_panel)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.logout_button = ttk.Button(button_frame, text="Logout", command=self.on_logout)
        self.logout_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        self.delete_account_button = ttk.Button(
            button_frame, 
            text="Delete Account", 
            command=self.on_delete_account,
            style="Danger.TButton"
        )
        self.delete_account_button.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        # Right panel (chats)
        self.right_panel = ttk.Frame(self.paned_window)
        self.paned_window.add(self.right_panel, weight=3)
        
        # Welcome message or instructions
        self.chat_placeholder = ttk.Label(
            self.right_panel,
            text="Select a contact or add a new one to start chatting.",
            font=("Helvetica", 12),
            anchor=tk.CENTER
        )
        self.chat_placeholder.pack(expand=True)
        
        # Bind events
        self.contacts_listbox.bind("<<ListboxSelect>>", self.on_contact_select)
        
    def add_contact(self, username):
        if username == self.client.get_username():
            messagebox.showwarning("Invalid Contact", "You cannot add yourself as a contact.")
            return False
            
        # Check if already in the list
        for i in range(self.contacts_listbox.size()):
            if self.contacts_listbox.get(i) == username:
                self.contacts_listbox.selection_clear(0, tk.END)
                self.contacts_listbox.selection_set(i)
                self.contacts_listbox.see(i)
                self.on_contact_select()
                return False
                
        # Add to the list
        self.contacts_listbox.insert(tk.END, username)
        return True
        
    def show_chat_widget(self, peer_username):
        # Hide the placeholder
        self.chat_placeholder.pack_forget()
        
        # Clear any existing chat widgets
        for widget in self.chat_widgets.values():
            widget.pack_forget()
            
        # Get or create the chat widget for this peer
        if peer_username not in self.chat_widgets:
            self.chat_widgets[peer_username] = ChatWidget(self.right_panel, self.client, peer_username)
            
        # Show the chat widget
        self.chat_widgets[peer_username].pack(fill=tk.BOTH, expand=True)
        
    def on_add_contact(self):
        username = self.new_contact_var.get().strip()
        if not username:
            return
            
        added = self.add_contact(username)
        if added:
            self.new_contact_var.set("")  # Clear the input
            
            # Select the new contact
            index = self.contacts_listbox.size() - 1
            self.contacts_listbox.selection_clear(0, tk.END)
            self.contacts_listbox.selection_set(index)
            self.contacts_listbox.see(index)
            self.on_contact_select()
            
    def on_unread_messages(self):
        count = self.unread_count_var.get()
        messages = self.client.get_unread_messages(count)
        
        if not messages:
            messagebox.showinfo("No Messages", "You have no unread messages.")
            return
            
        # Group messages by sender
        messages_by_sender = {}
        for msg in messages:
            if msg.sender not in messages_by_sender:
                messages_by_sender[msg.sender] = []
            messages_by_sender[msg.sender].append(msg)
            
        # Add contacts and update chat widgets
        for sender, msgs in messages_by_sender.items():
            self.add_contact(sender)
            if sender in self.chat_widgets:
                for msg in msgs:
                    self.chat_widgets[sender].add_message(msg)
                    
        # Show a summary
        messagebox.showinfo(
            "Unread Messages", 
            f"Loaded {len(messages)} unread messages from {len(messages_by_sender)} contacts."
        )
            
    def on_contact_select(self, event=None):
        selected = self.contacts_listbox.curselection()
        if not selected:
            return
            
        index = selected[0]
        peer_username = self.contacts_listbox.get(index)
        
        self.show_chat_widget(peer_username)
        
    def on_logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            self.client.logout()
            self.root.destroy()
            
    def on_delete_account(self):
        if messagebox.askyesno(
            "Delete Account", 
            "Are you sure you want to delete your account? This action cannot be undone!",
            icon="warning"
        ):
            success, message = self.client.delete_account()
            if success:
                messagebox.showinfo("Account Deleted", "Your account has been deleted.")
                self.root.destroy()
            else:
                messagebox.showerror("Error", message)
                
    def on_close(self):
        if messagebox.askyesno("Quit", "Are you sure you want to quit?"):
            self.client.disconnect()
            self.root.destroy()
            
    # Client event handlers
    def on_message_received(self, message):
        peer_username = message.sender if message.recipient == self.client.get_username() else message.recipient
        
        # Add the contact if needed
        self.add_contact(peer_username)
        
        # Update the chat widget if it exists
        if peer_username in self.chat_widgets:
            self.chat_widgets[peer_username].add_message(message)
            
    def on_message_deleted(self, message_id):
        # Update all chat widgets
        for widget in self.chat_widgets.values():
            widget.remove_message(message_id)
            
    def on_user_online(self, username):
        # Could update the UI to show the user is online
        pass
        
    def on_user_offline(self, username):
        # Could update the UI to show the user is offline
        pass
        
    def on_disconnected(self):
        messagebox.showwarning("Disconnected", "You have been disconnected from the server.")

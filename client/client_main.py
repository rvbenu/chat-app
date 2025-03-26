import tkinter as tk
from tkinter import ttk
import logging
import argparse
import sys
import os

# Add parent directory to path to import generated grpc code
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from chat_client import ChatClient
from ui.login_dialog import LoginDialog
from ui.main_window import MainWindow

def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Chat Client")
    parser.add_argument(
        "--address", 
        default="localhost:50051",
        help="Server address to connect to (default: localhost:50051)"
    )
    
    args = parser.parse_args()
    
    # Create the client
    client = ChatClient(args.address)
    
    # Set up the main Tkinter window
    root = tk.Tk()
    root.title("Chat Application")
    root.withdraw()  # Hide the main window until login
    
    # Create a style
    style = ttk.Style()
    style.configure("Danger.TButton", foreground="red")
    
    # Show the login dialog
    login_dialog = LoginDialog(root, client)
    root.wait_window(login_dialog.dialog)
    
    if login_dialog.get_result():
        # Show the main window
        root.deiconify()
        main_window = MainWindow(root, client)
        root.mainloop()

if __name__ == "__main__":
    main()

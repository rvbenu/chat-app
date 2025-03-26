import logging
import threading
import grpc
import sys
import os
from typing import List, Optional, Callable, Dict

# Add parent directory to path to import generated grpc code
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import chat_pb2
import chat_pb2_grpc

class ChatClient:
    def __init__(self, server_address: str):
        self.server_address = server_address
        self.username = ""
        self.session_token = ""
        self.connected = False
        
        # Create a gRPC channel
        self.channel = grpc.insecure_channel(server_address)
        self.stub = chat_pb2_grpc.ChatServiceStub(self.channel)
        
        # Event handlers
        self.on_message_received: Optional[Callable[[chat_pb2.Message], None]] = None
        self.on_message_deleted: Optional[Callable[[str], None]] = None
        self.on_user_online: Optional[Callable[[str], None]] = None
        self.on_user_offline: Optional[Callable[[str], None]] = None
        self.on_disconnected: Optional[Callable[[], None]] = None
        
        # Thread for handling events
        self.event_thread = None
        self.running = False
    
    def register_user(self, username: str, password: str) -> tuple[bool, str]:
        """
        Register a new user.
        Returns: (success, error_message)
        """
        request = chat_pb2.RegisterRequest(
            username=username,
            password=password
        )
        
        try:
            response = self.stub.Register(request)
            
            if response.success:
                self.username = username
                self.session_token = response.session_token
                
            return response.success, response.message
        except grpc.RpcError as e:
            return False, f"RPC Error: {e.details()}"
    
    def login(self, username: str, password: str) -> tuple[bool, str]:
        """
        Authenticate a user.
        Returns: (success, error_message)
        """
        request = chat_pb2.LoginRequest(
            username=username,
            password=password
        )
        
        try:
            response = self.stub.Login(request)
            
            if response.success:
                self.username = username
                self.session_token = response.session_token
                
            return response.success, response.message
        except grpc.RpcError as e:
            return False, f"RPC Error: {e.details()}"
    
    def logout(self) -> bool:
        """
        Logout the current user.
        """
        if not self.session_token:
            return True  # Already logged out
            
        request = chat_pb2.DisconnectRequest(
            session_token=self.session_token
        )
        
        try:
            response = self.stub.Disconnect(request)
            
            # Clear session info regardless of the result
            self.session_token = ""
            self.username = ""
            
            return response.success
        except grpc.RpcError as e:
            logging.error(f"Logout error: {e}")
            return False
    
    def delete_account(self) -> tuple[bool, str]:
        """
        Delete the current user's account.
        Returns: (success, error_message)
        """
        if not self.session_token:
            return False, "Not logged in"
            
        request = chat_pb2.DeleteAccountRequest(
            session_token=self.session_token
        )
        
        try:
            response = self.stub.DeleteAccount(request)
            
            if response.success:
                # Clear session info
                self.session_token = ""
                self.username = ""
                
            return response.success, response.message
        except grpc.RpcError as e:
            return False, f"RPC Error: {e.details()}"
    
    def send_message(self, recipient: str, content: str) -> tuple[bool, str]:
        """
        Send a message to another user.
        Returns: (success, error_message)
        """
        if not self.session_token:
            return False, "Not logged in"
            
        request = chat_pb2.SendMessageRequest(
            session_token=self.session_token,
            recipient=recipient,
            content=content
        )
        
        try:
            response = self.stub.SendMessage(request)
            return response.success, response.message
        except grpc.RpcError as e:
            return False, f"RPC Error: {e.details()}"
    
    def get_messages(self, peer_username: str, last_n_messages: int = 0) -> List[chat_pb2.Message]:
        """
        Get messages between the current user and another user.
        """
        if not self.session_token:
            return []
            
        request = chat_pb2.GetMessagesRequest(
            session_token=self.session_token,
            peer_username=peer_username,
            last_n_messages=last_n_messages
        )
        
        try:
            response = self.stub.GetMessages(request)
            return list(response.messages)
        except grpc.RpcError as e:
            logging.error(f"Get messages error: {e}")
            return []
    
    def get_unread_messages(self, last_n_messages: int = 0) -> List[chat_pb2.Message]:
        """
        Get unread messages for the current user.
        """
        return self.get_messages("", last_n_messages)
    
    def delete_message(self, message_id: str) -> tuple[bool, str]:
        """
        Delete a message.
        Returns: (success, error_message)
        """
        if not self.session_token:
            return False, "Not logged in"
            
        request = chat_pb2.DeleteMessageRequest(
            session_token=self.session_token,
            message_id=message_id
        )
        
        try:
            response = self.stub.DeleteMessage(request)
            return response.success, response.message
        except grpc.RpcError as e:
            return False, f"RPC Error: {e.details()}"
    
    def is_connected(self) -> bool:
        """
        Check if the client is connected.
        """
        return self.connected
    
    def connect(self) -> bool:
        """
        Connect to the server to receive events.
        """
        if self.connected or not self.session_token:
            return False
            
        # Start event handling thread
        self.running = True
        self.event_thread = threading.Thread(target=self._event_loop)
        self.event_thread.daemon = True
        self.event_thread.start()
        
        return True
    
    def disconnect(self):
        """
        Disconnect from the server.
        """
        self.running = False
        
        if self.event_thread and self.event_thread.is_alive():
            self.event_thread.join(timeout=2.0)
            
        self.connected = False
        
        # Notify listener
        if self.on_disconnected:
            self.on_disconnected()
    
    def get_username(self) -> str:
        """
        Get the current username.
        """
        return self.username
    
    def _event_loop(self):
        """
        Event handling loop.
        """
        request = chat_pb2.ConnectRequest(
            session_token=self.session_token
        )
        
        try:
            self.connected = True
            
            # Start the event stream
            for event in self.stub.Connect(request):
                if not self.running:
                    break
                    
                # Handle the event based on its type
                if event.type == chat_pb2.ChatEvent.NEW_MESSAGE:
                    if self.on_message_received:
                        self.on_message_received(event.message)
                        
                elif event.type == chat_pb2.ChatEvent.MESSAGE_DELETED:
                    if self.on_message_deleted:
                        self.on_message_deleted(event.message_id)
                        
                elif event.type == chat_pb2.ChatEvent.USER_ONLINE:
                    if self.on_user_online:
                        self.on_user_online(event.username)
                        
                elif event.type == chat_pb2.ChatEvent.USER_OFFLINE:
                    if self.on_user_offline:
                        self.on_user_offline(event.username)
        except grpc.RpcError as e:
            logging.error(f"Event stream error: {e}")
        finally:
            self.connected = False
            
            # Notify listener of disconnection
            if self.on_disconnected:
                self.on_disconnected()

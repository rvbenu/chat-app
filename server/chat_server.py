import logging
import grpc
import threading
import time
import sys
import os
from concurrent import futures
from typing import Dict, Set

# Add parent directory to path to import generated grpc code
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import chat_pb2
import chat_pb2_grpc
import utils
from database import Database
from auth_service import AuthService

class ChatServicer(chat_pb2_grpc.ChatServiceServicer):
    """Implementation of the Chat service"""

    def __init__(self, db: Database, auth_service: AuthService):
        self.db = db
        self.auth_service = auth_service
        # Track connected clients: username -> List[client_stream]
        self.connected_clients = {}
        self.clients_lock = threading.Lock()

    def Register(self, request, context):
        """Register a new user."""
        success, error_message, token = self.auth_service.register_user(
            request.username, request.password
        )
        
        response = chat_pb2.AuthResponse(
            success=success,
            message="Registration successful" if success else error_message,
            session_token=token
        )
        
        return response

    def Login(self, request, context):
        """Authenticate a user."""
        success, error_message, token = self.auth_service.login(
            request.username, request.password
        )
        
        response = chat_pb2.AuthResponse(
            success=success,
            message="Login successful" if success else error_message,
            session_token=token
        )
        
        return response

    def DeleteAccount(self, request, context):
        """Delete a user account."""
        valid, username = self.auth_service.validate_session(request.session_token)
        if not valid:
            return chat_pb2.StatusResponse(
                success=False,
                message="Invalid session"
            )
        
        # Disconnect client
        self._disconnect_client(username)
        
        # Delete account
        success = self.auth_service.delete_account(request.session_token)
        
        return chat_pb2.StatusResponse(
            success=success,
            message="Account deleted successfully" if success else "Failed to delete account"
        )

    def SendMessage(self, request, context):
        """Send a message to another user."""
        valid, sender = self.auth_service.validate_session(request.session_token)
        if not valid:
            return chat_pb2.StatusResponse(
                success=False,
                message="Invalid session"
            )
        
        recipient = request.recipient
        
        # Validate recipient exists
        if not self.db.user_exists(recipient):
            return chat_pb2.StatusResponse(
                success=False,
                message="Recipient does not exist"
            )
        
        # Store message
        timestamp = utils.get_current_timestamp()
        message_id = self.db.store_message(sender, recipient, request.content, timestamp)
        
        if not message_id:
            return chat_pb2.StatusResponse(
                success=False,
                message="Failed to store message"
            )
        
        # Create message event
        message = chat_pb2.Message(
            id=message_id,
            sender=sender,
            recipient=recipient,
            content=request.content,
            timestamp=timestamp,
            read=False
        )
        
        event = chat_pb2.ChatEvent(
            type=chat_pb2.ChatEvent.NEW_MESSAGE,
            message=message
        )
        
        # Broadcast to recipient if connected (and to sender to update their view)
        self._broadcast_event(event, exclude_username="")  # Send to all connected users
        
        return chat_pb2.StatusResponse(
            success=True,
            message="Message sent"
        )

    def GetMessages(self, request, context):
        """Get messages between users."""
        valid, username = self.auth_service.validate_session(request.session_token)
        if not valid:
            context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid session")
        
        messages = []
        if not request.peer_username:
            # Get unread messages
            messages = self.db.get_unread_messages(username, request.last_n_messages)
        else:
            # Get conversation with a specific user
            messages = self.db.get_messages(username, request.peer_username, request.last_n_messages)
        
        # Mark all incoming messages as read
        for msg in messages:
            if msg.recipient == username and not msg.read:
                self.db.mark_message_as_read(msg.id)
        
        return chat_pb2.MessageList(messages=messages)

    def DeleteMessage(self, request, context):
        """Delete a message."""
        valid, username = self.auth_service.validate_session(request.session_token)
        if not valid:
            return chat_pb2.StatusResponse(
                success=False,
                message="Invalid session"
            )
        
        # Delete message
        success = self.db.delete_message(request.message_id)
        
        if success:
            # Notify clients about deleted message
            event = chat_pb2.ChatEvent(
                type=chat_pb2.ChatEvent.MESSAGE_DELETED,
                message_id=request.message_id
            )
            
            self._broadcast_event(event)
        
        return chat_pb2.StatusResponse(
            success=success,
            message="Message deleted" if success else "Failed to delete message"
        )

    def Connect(self, request, context):
        """Connect a client to receive events."""
        valid, username = self.auth_service.validate_session(request.session_token)
        if not valid:
            context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid session")
        
        # Register client
        with self.clients_lock:
            if username not in self.connected_clients:
                self.connected_clients[username] = []
            self.connected_clients[username].append(context)
        
        # Send user online event to other clients
        event = chat_pb2.ChatEvent(
            type=chat_pb2.ChatEvent.USER_ONLINE,
            username=username
        )
        self._broadcast_event(event, username)
        
        # Wait until the client disconnects
        try:
            # Keep the connection alive until the client disconnects
            while context.is_active():
                time.sleep(1)
        except Exception as e:
            logging.warning(f"Client connection error: {e}")
        finally:
            # Cleanup when the connection closes
            self._disconnect_client(username, context)
        
        return  # End of stream
        
    def Disconnect(self, request, context):
        """Disconnect a client."""
        valid, username = self.auth_service.validate_session(request.session_token)
        if not valid:
            return chat_pb2.StatusResponse(
                success=False,
                message="Invalid session"
            )
        
        self._disconnect_client(username)
        
        return chat_pb2.StatusResponse(
            success=True,
            message="Disconnected"
        )
        
    def _broadcast_event(self, event, exclude_username=None):
        """Broadcast an event to all connected clients except the excluded username."""
        with self.clients_lock:
            for username, contexts in self.connected_clients.items():
                if exclude_username and username == exclude_username:
                    continue
                    
                # Try to send to each context associated with this username
                for ctx in contexts[:]:  # Create a copy of the list to allow modification
                    try:
                        if ctx.is_active():
                            ctx.write(event)
                    except Exception as e:
                        logging.warning(f"Failed to broadcast to {username}: {e}")
                        contexts.remove(ctx)
    
    def _disconnect_client(self, username, specific_context=None):
        """Disconnect a client or a specific context for a client."""
        contexts_to_remove = []
        
        with self.clients_lock:
            if username in self.connected_clients:
                if specific_context:
                    # Remove specific context
                    if specific_context in self.connected_clients[username]:
                        self.connected_clients[username].remove(specific_context)
                        contexts_to_remove.append(specific_context)
                else:
                    # Remove all contexts for this username
                    contexts_to_remove = self.connected_clients[username]
                    del self.connected_clients[username]
        
        # Send offline notification if all connections for the user were closed
        if not specific_context or (username in self.connected_clients and not self.connected_clients[username]):
            event = chat_pb2.ChatEvent(
                type=chat_pb2.ChatEvent.USER_OFFLINE,
                username=username
            )
            self._broadcast_event(event, username)

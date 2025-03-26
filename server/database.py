import sqlite3
import logging
from typing import List, Optional, Tuple
import sys
import os

# Add parent directory to path to import generated grpc code
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import chat_pb2
import utils

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        
    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
            self.conn = None
            
    def init(self) -> bool:
        """Initialize database schema"""
        try:
            with self:
                cursor = self.conn.cursor()
                
                # Create users table
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
                ''')
                
                # Create sessions table
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    FOREIGN KEY (username) REFERENCES users(username)
                )
                ''')
                
                # Create messages table
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    sender TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    read INTEGER DEFAULT 0,
                    FOREIGN KEY (sender) REFERENCES users(username),
                    FOREIGN KEY (recipient) REFERENCES users(username)
                )
                ''')
                
                self.conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error(f"Database initialization error: {e}")
            return False
            
    def register_user(self, username: str, password_hash: str) -> bool:
        """Register a new user"""
        if self.user_exists(username):
            return False
            
        try:
            with self:
                cursor = self.conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                    (username, password_hash, utils.get_current_timestamp())
                )
                self.conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error(f"Failed to register user: {e}")
            return False
            
    def check_user_credentials(self, username: str, password_hash: str) -> bool:
        """Check if the user credentials are valid"""
        try:
            with self:
                cursor = self.conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM users WHERE username = ? AND password_hash = ?",
                    (username, password_hash)
                )
                return cursor.fetchone()[0] > 0
        except sqlite3.Error as e:
            logging.error(f"Failed to check user credentials: {e}")
            return False
            
    def delete_user(self, username: str) -> bool:
        """Delete a user and all associated data"""
        try:
            with self:
                # Delete all messages
                if not self.delete_all_user_messages(username):
                    return False
                    
                # Delete all sessions
                if not self.remove_all_user_sessions(username):
                    return False
                    
                # Delete user
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM users WHERE username = ?", (username,))
                self.conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error(f"Failed to delete user: {e}")
            return False
            
    def user_exists(self, username: str) -> bool:
        """Check if a user exists"""
        try:
            with self:
                cursor = self.conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (username,))
                return cursor.fetchone()[0] > 0
        except sqlite3.Error as e:
            logging.error(f"Failed to check if user exists: {e}")
            return False
            
    def store_session(self, username: str, token: str) -> bool:
        """Store a new session"""
        try:
            with self:
                cursor = self.conn.cursor()
                cursor.execute(
                    "INSERT INTO sessions (token, username, created_at) VALUES (?, ?, ?)",
                    (token, username, utils.get_current_timestamp())
                )
                self.conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error(f"Failed to store session: {e}")
            return False
            
    def validate_session(self, token: str) -> Optional[str]:
        """Validate a session token and return the username"""
        try:
            with self:
                cursor = self.conn.cursor()
                cursor.execute("SELECT username FROM sessions WHERE token = ?", (token,))
                row = cursor.fetchone()
                return row['username'] if row else None
        except sqlite3.Error as e:
            logging.error(f"Failed to validate session: {e}")
            return None
            
    def remove_session(self, token: str) -> bool:
        """Remove a session"""
        try:
            with self:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
                self.conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error(f"Failed to remove session: {e}")
            return False
            
    def remove_all_user_sessions(self, username: str) -> bool:
        """Remove all sessions for a user"""
        try:
            with self:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM sessions WHERE username = ?", (username,))
                self.conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error(f"Failed to remove all user sessions: {e}")
            return False
            
    def store_message(self, sender: str, recipient: str, content: str, timestamp: int) -> Optional[str]:
        """Store a new message and return its ID"""
        try:
            with self:
                message_id = utils.generate_uuid()
                cursor = self.conn.cursor()
                cursor.execute(
                    "INSERT INTO messages (id, sender, recipient, content, timestamp, read) VALUES (?, ?, ?, ?, ?, 0)",
                    (message_id, sender, recipient, content, timestamp)
                )
                self.conn.commit()
                return message_id
        except sqlite3.Error as e:
            logging.error(f"Failed to store message: {e}")
            return None
            
    def delete_message(self, message_id: str) -> bool:
        """Delete a message"""
        try:
            with self:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM messages WHERE id = ?", (message_id,))
                self.conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error(f"Failed to delete message: {e}")
            return False
            
    def delete_all_user_messages(self, username: str) -> bool:
        """Delete all messages for a user"""
        try:
            with self:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM messages WHERE sender = ? OR recipient = ?", (username, username))
                self.conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error(f"Failed to delete all user messages: {e}")
            return False
            
    def get_messages(self, user1: str, user2: str, limit: int = 0) -> List[chat_pb2.Message]:
        """Get messages between two users"""
        try:
            with self:
                cursor = self.conn.cursor()
                query = """
                SELECT id, sender, recipient, content, timestamp, read 
                FROM messages 
                WHERE (sender = ? AND recipient = ?) OR (sender = ? AND recipient = ?) 
                ORDER BY timestamp DESC
                """
                
                if limit > 0:
                    query += f" LIMIT {limit}"
                    
                cursor.execute(query, (user1, user2, user2, user1))
                rows = cursor.fetchall()
                
                messages = []
                for row in rows:
                    message = chat_pb2.Message()
                    message.id = row['id']
                    message.sender = row['sender']
                    message.recipient = row['recipient']
                    message.content = row['content']
                    message.timestamp = row['timestamp']
                    message.read = bool(row['read'])
                    messages.append(message)
                
                # Reverse to get chronological order
                messages.reverse()
                return messages
        except sqlite3.Error as e:
            logging.error(f"Failed to get messages: {e}")
            return []
            
    def get_unread_messages(self, recipient: str, limit: int = 0) -> List[chat_pb2.Message]:
        """Get unread messages for a user"""
        try:
            with self:
                cursor = self.conn.cursor()
                query = """
                SELECT id, sender, recipient, content, timestamp, read 
                FROM messages 
                WHERE recipient = ? AND read = 0 
                ORDER BY timestamp DESC
                """
                
                if limit > 0:
                    query += f" LIMIT {limit}"
                    
                cursor.execute(query, (recipient,))
                rows = cursor.fetchall()
                
                messages = []
                for row in rows:
                    message = chat_pb2.Message()
                    message.id = row['id']
                    message.sender = row['sender']
                    message.recipient = row['recipient']
                    message.content = row['content']
                    message.timestamp = row['timestamp']
                    message.read = False
                    messages.append(message)
                
                # Reverse to get chronological order
                messages.reverse()
                return messages
        except sqlite3.Error as e:
            logging.error(f"Failed to get unread messages: {e}")
            return []
            
    def mark_message_as_read(self, message_id: str) -> bool:
        """Mark a message as read"""
        try:
            with self:
                cursor = self.conn.cursor()
                cursor.execute("UPDATE messages SET read = 1 WHERE id = ?", (message_id,))
                self.conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error(f"Failed to mark message as read: {e}")
            return False

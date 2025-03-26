import logging
from typing import Tuple
from database import Database
import utils

class AuthService:
    def __init__(self, db: Database):
        self.db = db

    def register_user(self, username: str, password: str) -> Tuple[bool, str, str]:
        """
        Register a new user.
        Returns: (success, error_message, token)
        """
        # Input validation
        if not username or not password:
            return False, "Username and password cannot be empty", ""
            
        # Check if user already exists
        if self.db.user_exists(username):
            return False, "Username already exists", ""
            
        # Hash the password
        password_hash = utils.hash_password(password)
        
        # Register user in database
        if not self.db.register_user(username, password_hash):
            return False, "Failed to register user", ""
            
        # Generate a session token
        token = utils.generate_session_token()
        
        # Store session
        if not self.db.store_session(username, token):
            return False, "Failed to create session", ""
            
        return True, "", token

    def login(self, username: str, password: str) -> Tuple[bool, str, str]:
        """
        Authenticate a user.
        Returns: (success, error_message, token)
        """
        # Input validation
        if not username or not password:
            return False, "Username and password cannot be empty", ""
            
        # Hash the password
        password_hash = utils.hash_password(password)
        
        # Check credentials
        if not self.db.check_user_credentials(username, password_hash):
            return False, "Invalid username or password", ""
            
        # Generate a session token
        token = utils.generate_session_token()
        
        # Store session
        if not self.db.store_session(username, token):
            return False, "Failed to create session", ""
            
        return True, "", token

    def validate_session(self, token: str) -> Tuple[bool, str]:
        """
        Validate a session token.
        Returns: (valid, username)
        """
        username = self.db.validate_session(token)
        return username is not None, username or ""

    def logout(self, token: str) -> bool:
        """
        Logout a user by removing their session.
        """
        return self.db.remove_session(token)

    def delete_account(self, token: str) -> bool:
        """
        Delete a user account.
        """
        valid, username = self.validate_session(token)
        if not valid:
            return False
            
        return self.db.delete_user(username)

import time
import hashlib
import uuid
import random

def hash_password(password, salt=""):
    """
    Simple password hashing (dummy implementation for demonstration)
    """
    combined = salt + password
    return hashlib.sha256(combined.encode()).hexdigest()

def generate_session_token():
    """
    Generate a random session token
    """
    return uuid.uuid4().hex

def get_current_timestamp():
    """
    Get current timestamp in milliseconds
    """
    return int(time.time() * 1000)

def generate_uuid():
    """
    Generate a random UUID for message IDs
    """
    return str(uuid.uuid4())

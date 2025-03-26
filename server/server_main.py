import os
import sys
import logging
import argparse
import grpc
from concurrent import futures

# Add parent directory to path to import generated grpc code
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import chat_pb2
import chat_pb2_grpc
from database import Database
from auth_service import AuthService
from chat_server import ChatServicer

def run_server(address, db_path):
    # Initialize the database
    db = Database(db_path)
    if not db.init():
        logging.error("Failed to initialize database")
        return
    
    # Create the authentication service
    auth_service = AuthService(db)
    
    # Create the server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    # Add the service to the server
    chat_pb2_grpc.add_ChatServiceServicer_to_server(
        ChatServicer(db, auth_service), server
    )
    
    # Listen on the given address without any authentication mechanism
    server.add_insecure_port(address)
    server.start()
    
    logging.info(f"Server started, listening on {address}")
    
    # Keep the server running
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logging.info("Server shutting down...")
        server.stop(0)

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Chat Server")
    parser.add_argument(
        "--address", 
        default="localhost:50051",
        help="Address to listen on (default: localhost:50051)"
    )
    parser.add_argument(
        "--db", 
        default="chat.db",
        help="Path to SQLite database file (default: chat.db)"
    )
    
    args = parser.parse_args()
    
    run_server(args.address, args.db)

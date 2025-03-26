#!/bin/bash

# Script to run the chat server

# Check if Python is installed
if ! command -v python3 &> /dev/null
then
    echo "Python 3 is required but it's not installed. Please install Python 3 and try again."
    exit 1
fi

# Check if virtual environment exists
if [ -d "venv" ]; then
    # Activate virtual environment
    source venv/bin/activate
    echo "Activated virtual environment."
else
    echo "Virtual environment not found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Check if gRPC code has been generated
if [ ! -f "chat_pb2.py" ] || [ ! -f "chat_pb2_grpc.py" ]; then
    echo "Generating gRPC code..."
    python generate_proto.py
fi

# Run the server with provided arguments
echo "Starting chat server..."
python server/server_main.py "$@"

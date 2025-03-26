#!/usr/bin/env python3
import os
import subprocess
import sys

def main():
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Proto file path
    proto_path = os.path.join(script_dir, "proto", "chat.proto")
    
    # Check if the proto file exists
    if not os.path.exists(proto_path):
        print(f"Error: Proto file not found at {proto_path}")
        return 1
    
    # Output directory is the script directory
    output_dir = script_dir
    
    # Run protoc to generate gRPC code
    command = [
        "python", "-m", "grpc_tools.protoc",
        "-I", os.path.dirname(proto_path),
        f"--python_out={output_dir}",
        f"--grpc_python_out={output_dir}",
        proto_path
    ]
    
    print(f"Generating gRPC code from {proto_path}...")
    result = subprocess.run(command, check=False)
    
    if result.returncode != 0:
        print("Error: Failed to generate gRPC code")
        return 1
    
    print("Successfully generated gRPC code")
    print(f"Created: {os.path.join(output_dir, 'chat_pb2.py')}")
    print(f"Created: {os.path.join(output_dir, 'chat_pb2_grpc.py')}")
    return 0

if __name__ == "__main__":
    sys.exit(main())

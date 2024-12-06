import socket
import threading
import ssl
import time
from datetime import datetime
import os

# Cache dictionary to store responses
response_cache = {}
cache_lock = threading.Lock()

def get_from_cache(request):
    with cache_lock:
        if request in response_cache:
            entry = response_cache[request]
            # Check if the cache entry is still valid
            if entry["expires_at"] > time.time():
                return entry["response"]
            else:
                # Remove expired cache entry
                del response_cache[request]
    return None

# Define log file path
LOG_FILE = 'app.log'

# Initialize a list to store logs in memory (optional)
proxy_logs = []

# Ensure log file exists (create it if not)
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'w') as log_file:
        log_file.write('')  # Create an empty file

def log_message(message):
    """Log messages with a timestamp."""
    # Create a timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Format log entry
    log_entry = f'[{timestamp}] {message}'
    # Append log entry to in-memory log list
    proxy_logs.append(log_entry)
    
    # Open the log file in append mode, now we know it exists
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(log_entry + '\n')

# Function to add a response to the cache
def add_to_cache(request, response, timeout=30):
    with cache_lock:
        response_cache[request] = {
            "response": response,
            "expires_at": time.time() + timeout
        }

BLACKLIST = {'example.com'}
WHITELIST = set()

def is_blacklisted(hostname):
    """Check if the hostname is blacklisted."""
    return hostname in BLACKLIST

def is_whitelisted(hostname):
    """Check if the hostname is whitelisted."""
    return not WHITELIST or hostname in WHITELIST

def start_proxy_server(host, port):
    # Create a TCP socket for the proxy server
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Proxy server listening on {host}:{port}")
    log_message(f"Proxy server listening on {host}:{port}")

    while True:
        client_socket, client_address = server_socket.accept()
        print(f"Connection from {client_address}")
        log_message(f"Connection from {client_address}")
        
        # Create a new thread to handle the client connection
        client_thread = threading.Thread(target=handle_client, args=(client_socket,))
        client_thread.start()

def handle_client(client_socket):
    try:
        # Receive the message from the client
        request = client_socket.recv(1024).decode()
        print(f"Request received from client: {request}")
        log_message(f"Request received from client: {request}")
        
        # Use the cache function directly
        cached_response = get_from_cache(request)
        if cached_response:
            print("Serving response from cache.")
            log_message("Serving response from cache.")
            client_socket.send(cached_response)
            return
        
        # Check if the request looks like an HTTP request
        if request.startswith(("GET", "POST", "HEAD", "PUT", "DELETE", "CONNECT", "OPTIONS", "TRACE")):
            # Parse the HTTP request
            method, path, version, headers = parse_request(request)

            # Determine the target server and port (from the "Host" header)
            target_server, target_port = parse_host_header(headers)

            # Check blacklist and whitelist
            if is_blacklisted(target_server):
                print(f"Blocked blacklisted domain: {target_server}")
                log_message(f"Blocked blacklisted domain: {target_server}")
                client_socket.send(b"HTTP/1.1 403 Forbidden\r\n\r\n")
                return

            # Forward the HTTP request to the target server
            proxy_server(target_server, target_port, client_socket, request)

        else:
            # Treat it as a plain text message if it's not HTTP
            print(f"Non-HTTP request received: {request}")
            log_message(f"Non-HTTP request received: {request}")
            target_server = 'localhost'  # The plain text server's address
            target_port = 12000  # The plain text server's port

            # Forward the plain text to the plain text server
            forward_plain_text(target_server, target_port, client_socket, request)

    except Exception as e:
        print(f"Error handling client: {e}")
        log_message(f"Error handling client: {e}")
    finally:
        client_socket.close()

def forward_plain_text(target_server, target_port, client_socket, request):
    """Forward non-HTTP plain text to a server."""
    try:
        # Create a new socket to forward the message
        proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        proxy_socket.connect((target_server, target_port))

        # Send the plain text request to the target server
        proxy_socket.send(request.encode())

        # Receive the response from the target server
        response = proxy_socket.recv(4096)

        # Cache the plain text request and response
        add_to_cache(request, response)

        # Send the response back to the client
        client_socket.send(response)

    except Exception as e:
        print(f"Error in forwarding plain text: {e}")
        log_message(f"Error in forwarding plain text: {e}")
    finally:
        proxy_socket.close()

def parse_request(request):
    """Parse the HTTP request into method, path, version, and headers."""
    lines = request.split('\r\n')

    # Split the first line into method, path, and version
    try:
        method, path, version = lines[0].split(' ', 2)  # Split into exactly 3 parts
    except ValueError:
        raise ValueError("Malformed request line, unable to parse method, path, and version")

    # Remaining lines are headers
    headers = {}
    for line in lines[1:]:
        if line:
            try:
                key, value = line.split(': ', 1)  # Split only at the first occurrence of ": "
                headers[key] = value
            except ValueError:
                # If we can't split the line into a key-value pair, skip it
                continue
    
    return method, path, version, headers

def parse_host_header(headers):
    """Parse the 'Host' header to get the target server and port."""
    host_header = headers.get('Host')
    if not host_header:
        raise ValueError("Host header is missing")

    if ':' in host_header:
        target_server, target_port = host_header.split(':')
        target_port = int(target_port)
    else:
        target_server = host_header
        target_port = 80  # Default HTTP port
    
    return target_server, target_port

def proxy_server(target_server, target_port, client_socket, request):
    try:
        # Check if the request is HTTPS by inspecting the URL scheme
        if request.lower().startswith("https://"):
            # Securely connect using SSL
            proxy_socket = ssl.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
            target_port = 443  # Default HTTPS port
        else:
            proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        proxy_socket.connect((target_server, target_port))
        proxy_socket.send(request)

        full_response = b""
        while True:
            response = proxy_socket.recv(4096)
            if len(response) > 0:
                full_response += response
                client_socket.send(response)
            else:
                break

        add_to_cache(request, full_response)

    except Exception as e:
        print(f"Error in proxy server communication: {e}")
        log_message(f"Error in proxy server communication: {e}")
    finally:
        proxy_socket.close()
        client_socket.close()

if __name__ == "__main__":
    start_proxy_server('127.0.0.1', 8888)

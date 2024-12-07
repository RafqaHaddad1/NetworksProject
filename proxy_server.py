import threading
import ssl
import time
from datetime import datetime
import os
import select
import socket
# Cache dictionary to store responses
response_cache = {}
cache_lock = threading.Lock()

# Cache timeout (seconds)
CACHE_TIMEOUT = 30

# Blacklist and Whitelist
BLACKLIST = set()
WHITELIST = set()

# Log file path
LOG_FILE = 'app.log'

# Ensure log file exists
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'w') as log_file:
        log_file.write('')

def log_message(message):
    """Log messages with a timestamp."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f'[{timestamp}] {message}'
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(log_entry + '\n')

def get_from_cache(request):
    """Retrieve the cached response if valid."""
    with cache_lock:
        if request in response_cache:
            entry = response_cache[request]
            if entry["expires_at"] > time.time():  # Cache is valid
                return entry["response"]
            else:
                del response_cache[request]  # Remove expired entry
    return None

def add_to_cache(request, response, timeout=CACHE_TIMEOUT):
    """Cache the response."""
    with cache_lock:
        response_cache[request] = {
            "response": response,
            "expires_at": time.time() + timeout
        }

def is_blacklisted(hostname):
    """Check if hostname is blacklisted."""
    return hostname in BLACKLIST

def is_whitelisted(hostname):
    """Check if hostname is whitelisted."""
    return not WHITELIST or hostname in WHITELIST

def start_proxy_server():
    """Start the proxy server."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('127.0.0.1', 8888))
    server_socket.listen(5)
    
    log_message("Proxy server listening on 127.0.0.1:8888")
    
    while True:
        client_socket, _ = server_socket.accept()
        log_message(f"Connection from {client_socket.getpeername()}")
        handle_client(client_socket)

def handle_client(client_socket):
    """Handle the client request, forward it, and send back the response."""
    try:
        # Receive request from the client
        request = client_socket.recv(4096).decode('utf-8')
        if not request:
            return
        
        log_message(f"Received request from {client_socket.getpeername()}:\n{request}")
        
        # Check for cached response
        cached_response = get_from_cache(request)
        if cached_response:
            log_message(f"Cache hit for request from {client_socket.getpeername()}")
            client_socket.send(cached_response)
            return
        
        # Parse the request to get the target host and port
        target_host, target_port = parse_target_host(request)
        log_message(f"Parsed Host header: {target_host}")
        
        # Forward the request to the target server
        proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        proxy_socket.connect((target_host, target_port))
        
        # Log and forward the full request
        log_message(f"Forwarding HTTP request to {target_host}:{target_port}")
        log_message(f"Full HTTP request sent to {target_host}:\n{request}")
        proxy_socket.sendall(request.encode())

        # Receive and log the response from the target server
        full_response = b""
        while True:
            response = proxy_socket.recv(4096)
            if not response:
                break
            full_response += response
            client_socket.send(response)  # Send the response back to the client
            log_message(f"Received response chunk: {response[:1000]}...")  # Log the response chunk

        # Cache the response for future requests
        add_to_cache(request, full_response)

        # Split headers and body for logging
        response_parts = full_response.split(b'\r\n\r\n', 1)
        headers = response_parts[0]
        body = response_parts[1] if len(response_parts) > 1 else b""
        
        headers_decoded = headers.decode(errors='ignore')
        status_line = headers_decoded.splitlines()[0]
        log_message(f"Status Line: {status_line}")
        log_message(f"Headers:\n{headers_decoded}")
        
        try:
            body_decoded = body.decode(errors='ignore')
        except UnicodeDecodeError:
            body_decoded = "[Binary data that couldn't be decoded]"
        
        # Log response body, truncating if necessary
        log_message(f"Response Body:\n{body_decoded[:500]}... (truncated)")

    except Exception as e:
        log_message(f"Error: {e}")
    finally:
        client_socket.close()

def parse_target_host(request):
    """Parse the host from the request headers."""
    lines = request.splitlines()
    for line in lines:
        if line.startswith("Host:"):
            host = line.split(" ")[1].strip()
            if ':' in host:
                return host.split(":")[0], int(host.split(":")[1])
            else:
                return host, 80  # Default to port 80 for HTTP
    return None, None

def parse_connect_request(request):
    """Parse CONNECT request for HTTPS."""
    target = request.split(' ')[1]
    target_server, target_port = target.split(':')
    return target_server, int(target_port)

def handle_https_tunnel(client_socket, target_server, target_port):
    """Handle HTTPS tunneling (CONNECT method)."""
    log_message(f"Establishing HTTPS tunnel to {target_server}:{target_port}")
    client_socket.send(b"HTTP/1.1 200 Connection Established\r\n\r\n")
    
    # Set up SSL socket connection to target server
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.connect((target_server, target_port))
    
    sockets = [client_socket, proxy_socket]
    while True:
        ready_sockets, _, _ = select.select(sockets, [], [])
        for sock in ready_sockets:
            data = sock.recv(4096)
            if not data:
                return
            # Forward the data
            if sock is client_socket:
                proxy_socket.send(data)
            else:
                client_socket.send(data)

    proxy_socket.close()
    client_socket.close()

def proxy_http(target_server, target_port, client_socket, request):
    """Handle forwarding HTTP requests and responses."""
    try:
        log_message(f"Forwarding HTTP request to {target_server}:{target_port}")
        
        # Log the full HTTP request before sending it
        log_message(f"Full HTTP request sent to {target_server}:\n{request}")
        
        # Forward request to the target server
        proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        proxy_socket.connect((target_server, target_port))
        proxy_socket.send(request.encode())

        # Initialize variable to store the full response
        full_response = b""

        # Receive data from the target server
        while True:
            response = proxy_socket.recv(4096)
            if not response:
                break
            full_response += response
            client_socket.send(response)  # Send the response back to the client

        # Split response into header and body
        response_parts = full_response.split(b'\r\n\r\n', 1)
        headers = response_parts[0]
        body = response_parts[1] if len(response_parts) > 1 else b""

        # Decode headers to log them
        headers_decoded = headers.decode(errors='ignore')

        # Log the status line and headers
        status_line = headers_decoded.splitlines()[0]
        log_message(f"Status Line: {status_line}")
        log_message(f"Headers:\n{headers_decoded}")

        # Decode the body for logging (if possible)
        try:
            body_decoded = body.decode(errors='ignore')
        except UnicodeDecodeError:
            body_decoded = "[Binary data that couldn't be decoded]"

        # Log the response body (truncated for large responses)
        log_message(f"Response Body:\n{body_decoded[:500]}... (truncated)")

        # Cache the response for future requests
        add_to_cache(request, full_response)

    except Exception as e:
        log_message(f"Error forwarding HTTP request: {e}")
        client_socket.send(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
    finally:
        proxy_socket.close()

def parse_request(request):
    """Parse HTTP request details."""
    lines = request.split('\r\n')
    method, path, version = lines[0].split(' ', 2)
    headers = {}
    for line in lines[1:]:
        if ': ' in line:
            key, value = line.split(': ', 1)
            headers[key] = value
    return method, path, version, headers

def parse_host_header(headers):
    """Extract host and port from 'Host' header."""
    host_header = headers.get('Host')
    if not host_header:
        raise ValueError("Host header is missing")

    if ':' in host_header:
        target_server, target_port = host_header.split(':')
        target_port = int(target_port)
    else:
        target_server = host_header
        target_port = 80  # Default to port 80 for HTTP

    return target_server, target_port

if __name__ == "__main__":
    start_proxy_server()

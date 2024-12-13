import threading
import ssl
import time
from datetime import datetime
import os
import select
import socket
from flask import Flask, request, jsonify,render_template, send_from_directory
from flask_mysqldb import MySQL
from flask_cors import CORS 
import subprocess
from datetime import datetime, timedelta
import time

app = Flask(__name__,static_folder='AdminInterface')

# Configure MySQL connection
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'proxy_server'

mysql = MySQL(app)



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
    """Log messages with a timestamp and save to MySQL database."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f'[{timestamp}] {message}'

    # Log to file
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(log_entry + '\n')

    # Insert log entry into the database
    try:
        with app.app_context():  # Ensure database interaction happens within app context
            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO logs (timestamp, message) VALUES (%s, %s)", (timestamp, message))
            mysql.connection.commit()  # Commit the transaction
            cursor.close()  # Close the cursor
    except Exception as e:
        print(f"Error saving log to the database: {e}")

def get_from_cache(request):
    """Retrieve the cached response if valid."""
    
    with cache_lock:
        if request in response_cache:
            entry = response_cache[request]
            if entry["expires_at"] > time.time():  # Cache is valid
                log_message(f"Cache hit for request: {request[:100]}")
                return entry["response"]
            else:
                log_message(f"Cache expired for request: {request[:100]}")
                del response_cache[request]  # Remove expired entry
        log_message(f"Cache miss for request: {request[:100]}")
    return None

def add_to_cache(request, response, timeout=CACHE_TIMEOUT):
    """Cache the response in both in-memory and database."""
    log_message(f"Caching request: {request[:100]} with timeout: {timeout} seconds")

    # Calculate response size
    response_size = len(response)

    # In-memory cache
    with cache_lock:
        response_cache[request] = {
            "response": response,
            "expires_at": time.time() + timeout
        }

    try:
        with app.app_context():
            # Serialize the response (e.g., as JSON or compressed string)
            serialized_response = response  # You can use json.dumps() or other methods for serialization
            
            # Save to database cache
            cursor = mysql.connection.cursor()
            cursor.execute("""
                REPLACE INTO cache (url, size, expires)
                VALUES (%s, %s, %s)
            """, (request, response_size, time.time() + timeout))
            mysql.connection.commit()
            cursor.close()
            log_message(f"Request cached successfully in DB. Response size: {response_size} bytes")
    except Exception as e:
        log_message(f"Error saving to cache DB for {request[:100]}: {e}")

def is_blacklisted(hostname):
    """Check if hostname is blacklisted by querying the database."""
    try:
        with app.app_context():
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT url FROM blacklist WHERE url = %s", (hostname,))
            result = cursor.fetchone()
            cursor.close()
            return result is not None  # Return True if URL is found in the blacklist
    except Exception as e:
        log_message(f"Error checking blacklist for {hostname}: {e}")
        return False

def is_whitelisted(hostname):
    """Check if hostname is whitelisted by querying the database."""
    try:
        with app.app_context():
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT url FROM whitelist WHERE url = %s", (hostname,))
            result = cursor.fetchone()
            cursor.close()
            return result is not None  # Return True if URL is found in the whitelist
    except Exception as e:
        log_message(f"Error checking whitelist for {hostname}: {e}")
        return False

def start_proxy_server():
    """Start the proxy server."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('127.0.0.1', 8888))
    server_socket.listen(5)
    
    log_message("Proxy server listening on 127.0.0.1:8888")
    
    while True:
        client_socket, _ = server_socket.accept()
        log_message(f"Connection from {client_socket.getpeername()}")
        threading.Thread(target=handle_client, args=(client_socket,)).start()

def handle_client(client_socket):
    """Handle the client request, forward it, and send back the response."""
    try:
        # Receive request from the client
        request = client_socket.recv(4096).decode('utf-8')
        if not request:
            return

        log_message(f"Received request from {client_socket.getpeername()}:\n{request}")

        # Check if the request is a CONNECT method for HTTPS
        if request.startswith("CONNECT"):
            target_host, target_port = parse_connect_request(request)
            handle_https_tunnel(client_socket, target_host, target_port,request )
            return

        # Check for cached response for HTTP requests
        cached_response = get_from_cache(request)
        if cached_response:
            log_message(f"Cache hit for request from {client_socket.getpeername()}")
            client_socket.send(cached_response)
            return

        # Parse the request to get the target host and port for HTTP
        target_host, target_port = parse_target_host(request)
        log_message(f"Parsed Host header: {target_host}")
        #blacklist check 
        if is_blacklisted(target_host):
            log_message(f"Blocked blacklisted request to {target_host}")
            client_socket.send(b"HTTP/1.1 403 Forbidden\r\n\r\n")
            client_socket.close()
            return

        #Forward the request 
        proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        proxy_socket.connect((target_host, target_port))

        log_message(f"Forwarding HTTP request to {target_host}:{target_port}")
        log_message(f"Full HTTP request sent to {target_host}:\n{request}")
        proxy_socket.sendall(request.encode())

        #receive and send response
        full_response = b""
        while True:
            # recieve chunks of 4096 bytes
            response = proxy_socket.recv(4096)
            if not response:
                break
            full_response += response
            # Forward response
            client_socket.send(response)  # Send the response back to the client
            log_message(f"before proxy http")
            proxy_http(target_host, target_port, client_socket, request)
           
            log_message(f"Received response chunk: {response[:1000]}...")
        
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
        # Forward the request to the target server for HTTP
        log_message(f"before proxy http")
        
        log_message(f"Response Body:\n{body_decoded[:500]}... (truncated)")

    except Exception as e:
        log_message(f"Error: {e}")
    finally:
        client_socket.close()

def handle_https_tunnel(client_socket, target_host, target_port):
    """Handle HTTPS tunneling (CONNECT method)."""
    try:
        log_message(f"Establishing HTTPS tunnel to {target_host}:{target_port}")
        log_message(f"HTTP/1.1 200 Connection Established\r\n\r\n")
        client_socket.send(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        
        # Establish connection to the target server
        proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        proxy_socket.connect((target_host, target_port))

        # Forward data between the client and target server
        sockets = [client_socket, proxy_socket]
        while True:
            ready_sockets, _, _ = select.select(sockets, [], [])
            for sock in ready_sockets:
                data = sock.recv(4096)
                if not data:
                    return

                # Log the data being forwarded (size only)
                if sock is client_socket:
                    log_message(f"Forwarding {len(data)} bytes from client to {target_host}:{target_port}")
                    proxy_socket.sendall(data)
                else:
                    log_message(f"Forwarding {len(data)} bytes from {target_host}:{target_port} to client")
                    client_socket.sendall(data)
    except Exception as e:
        log_message(f"Error in HTTPS tunnel: {e}")
    finally:
        client_socket.close()
        proxy_socket.close()

def proxy_http(target_server, target_port, client_socket, request):
    """Handle forwarding HTTP requests and responses while caching progressively."""
    try:
        log_message(f"Forwarding HTTP request to {target_server}:{target_port}")
        
        # Log the full HTTP request before sending it
        log_message(f"Full HTTP request sent to {target_server}:\n{request}")
        
        # Forward request to the target server
        proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        proxy_socket.connect((target_server, target_port))
        proxy_socket.send(request.encode())

        # Initialize variable to store the full response for eventual caching/logging
        full_response = b""

        # Receive data from the target server
        while True:
            response_chunk = proxy_socket.recv(4096)
            if not response_chunk:
                break

            # Send the chunk to the client
            client_socket.send(response_chunk)

            # Append the chunk to the cumulative full response
            full_response += response_chunk

            # Cache the chunk progressively
            add_to_cache(request, full_response, CACHE_TIMEOUT)

            # Log each chunk's size and progress
            log_message(f"Forwarded and cached chunk of size {len(response_chunk)} bytes")

        # Split response into headers and body for logging purposes
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

    except Exception as e:
        log_message(f"Error forwarding HTTP request: {e}")
        client_socket.send(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
    finally:
        proxy_socket.close()

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
    target_host, target_port = target.split(':')
    return target_host, int(target_port)

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


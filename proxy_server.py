import socket
import threading
from urllib.parse import urlparse
from io import BytesIO

# Assuming cache is imported and contains methods `get_from_cache` and `add_to_cache`
import cache  

class HTTPRequest:
    """Helper class to parse raw HTTP request data."""
    def __init__(self, request_text):
        # Initialize a BytesIO object from the request text for easier parsing
        self.rfile = BytesIO(request_text)
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.headers = {}
        self.command = None
        self.path = None
        self._parse_request()

    def _parse_request(self):
        """Parses the raw HTTP request line and extracts method and path."""
        request_line = self.raw_requestline.decode('iso-8859-1').strip()
        parts = request_line.split()

        if len(parts) >= 2:
            self.command = parts[0]  # HTTP method (e.g., GET, POST)
            self.path = parts[1]     # Requested path or URL
        else:
            self.command = None
            self.path = None

        # Simulate headers (extend this to real HTTP header parsing as needed)
        self.headers = {
            "Host": "example.com"
        }


def parse_request(raw_request):
    """
    Parses raw HTTP request data to extract method, host, port, full URL, and headers.
    """
    try:
        # Parse raw HTTP request using HTTPRequest helper
        request = HTTPRequest(raw_request)
        
        # Extract the request method (e.g., GET, POST)
        method = request.command

        # Parse the full URL for detailed information
        parsed_url = urlparse(request.path)

        # Extract target server's address (host) and port
        host = parsed_url.hostname or request.headers.get('Host', '').split(':')[0]
        port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)

        # Full URL reconstruction
        full_url = f"{parsed_url.scheme}://{host}{parsed_url.path}" if parsed_url.scheme else request.path

        # Log the information for debugging
        print(f"Method: {method}")
        print(f"Host: {host}")
        print(f"Port: {port}")
        print(f"Full URL: {full_url}")

        # Prepare headers
        headers = dict(request.headers)
        headers['Host'] = f"{host}:{port}" if port not in [80, 443] else host

        return {
            "Method": method,
            "Host": host,
            "Port": port,
            "Full URL": full_url,
            "Headers": headers
        }
    except Exception as e:
        print(f"Error parsing request: {e}")
        return {
            "Error": str(e)
        }


def start_proxy_server(host, port):
    # Create a TCP socket for the proxy server
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Proxy server listening on {host}:{port}")

    while True:
        client_socket, client_address = server_socket.accept()
        print(f"Connection from {client_address}")
        
        # Create a new thread to handle the client connection
        client_thread = threading.Thread(target=handle_client, args=(client_socket,))
        client_thread.start()


def handle_client(client_socket):
    try:
        request = client_socket.recv(1024)
        print(f"Request received from client: {request.decode()}")
        
        parsed_request = parse_request(request)
        if 'Error' in parsed_request:
            print("Invalid request format")
            return

        cached_response = cache.get_from_cache(request)
        if cached_response:
            print("Serving response from cache.")
            client_socket.send(cached_response)
        else:
            # Forward the request to the actual server
            proxy_server(parsed_request['Host'], parsed_request['Port'], client_socket, request)
    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        client_socket.close()


def proxy_server(webserver, port, client_socket, request):
    try:
        proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        proxy_socket.connect((webserver, port))
        proxy_socket.send(request)

        full_response = b""

        # Receive the response from the server and forward it to the client
        while True:
            response = proxy_socket.recv(4096)
            if len(response) > 0:
                full_response += response
                client_socket.send(response)
            else:
                break

        # Cache the response for future use
        cache.add_to_cache(request, full_response)
    except Exception as e:
        print(f"Error in proxy server communication: {e}")
    finally:
        proxy_socket.close()
        client_socket.close()


if __name__ == "__main__":
    start_proxy_server('127.0.0.1', 8888)

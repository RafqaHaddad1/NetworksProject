import socket
import threading
import cache
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
       

        cached_response =  cache.get_from_cache(request)
        if cached_response:
            print("Serving response from cache.")
            client_socket.send(cached_response)
            return

        # Forward the request to the actual server
        proxy_server('localhost', 12000, client_socket, request)
    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        client_socket.close()


def proxy_server(webserver, port, client_socket, request):
    # Create a socket to connect to the server
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

            cache.add_to_cache(request, full_response)
    except Exception as e:
        print(f"Error in proxy server communication: {e}")
    finally:
        proxy_socket.close()
        client_socket.close()


if __name__ == "__main__":
    start_proxy_server('127.0.0.1', 8888)
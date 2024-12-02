from socket import *
import threading

def handle_client(client_socket, addr):
    try:
        while True:
            # Receive and print client messages
            request = client_socket.recv(1024).decode("utf-8")
            if not request:
                break  # Exit if the client closes the connection
            if request.lower() == "close":
                client_socket.send("Connection closed.".encode("utf-8"))
                break
            print(f"Received from {addr}: {request}")
            
            # Capitalize the sentence
            response = request.upper()

            # Send the modified sentence back to the client
            client_socket.send(response.encode("utf-8"))
            print(f"Sent to {addr}: {response}")
    except Exception as e:
        print(f"Error when handling client {addr}: {e}")
    finally:
        client_socket.close()
        print(f"Connection to client ({addr[0]}:{addr[1]}) closed")


def run_server():
    ServerPort = 12000

    # Create socket to listen for requests from the proxy
    serverSocket = socket(AF_INET, SOCK_STREAM)
    serverSocket.bind(('localhost', ServerPort))
    serverSocket.listen()

    print("The server is ready to receive")

    while True:
        # Accept connection from the proxy server
        client_socket, addr = serverSocket.accept()
        print(f"Connection from {addr}")
        
        # Start a new thread to handle the client
        thread = threading.Thread(target=handle_client, args=(client_socket, addr,))
        thread.start()


run_server()

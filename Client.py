from socket import *
import threading

# Create a global mutex lock for synchronizing access to shared resources
mutex = threading.Lock()

def run_client(client_id):
    proxy_host = "localhost"
    proxy_port = 8888

    # Create socket and connect to the proxy server
    clientSocket = socket(AF_INET, SOCK_STREAM)
    clientSocket.connect((proxy_host, proxy_port))

    try:
        while True:
            # Input sentence from the client
            sentence = input(f'Client {client_id} - Input lowercase sentence (or type "close" to exit): ')
            
            # If the user types "close", exit the loop and close the connection
            if sentence.lower() == "close":
                clientSocket.send(sentence.encode())
                mutex.acquire()  # Acquire lock before printing
                print(f"Client {client_id} - Closing connection...")
                mutex.release()  # Release lock after printing
                break

            # Acquire lock before sending the sentence and printing to avoid race conditions
            mutex.acquire()
            print(f"Client {client_id} - Sending sentence to proxy: {sentence}")
            mutex.release()

            # Send the sentence to the proxy
            clientSocket.send(sentence.encode())

            # Receive the modified sentence from the proxy
            modifiedSentence = clientSocket.recv(4096).decode()
            if not modifiedSentence:
                mutex.acquire()
                print(f"Client {client_id} - Connection closed by server.")
                mutex.release()
                break

            # Acquire lock before printing the received message
            mutex.acquire()
            print(f"Client {client_id} - From Proxy: {modifiedSentence}")
            mutex.release()
    except Exception as e:
        mutex.acquire()
        print(f"Client {client_id} - Error: {e}")
        mutex.release()
    finally:
        # Close the client socket
        clientSocket.close()

# Create multiple clients using threads
def create_clients(num_clients):
    threads = []
    for i in range(num_clients):
        thread = threading.Thread(target=run_client, args=(i+1,))
        threads.append(thread)
        thread.start()

    # Wait for all threads to finish
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    # Number of clients to run
    num_clients = 3  # Adjust this to run as many clients as you want
    create_clients(num_clients)

from socket import *

ServerPort = 12000

# Create socket to listen for requests from the proxy
serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(('localhost', ServerPort))
serverSocket.listen(1)

print("The server is ready to receive")

while True:
    # Accept connection from the proxy server
    connectionSocket, addr = serverSocket.accept()
    print(f"Connection from {addr}")

    # Receive the data sent by the proxy
    sentence = connectionSocket.recv(4096).decode()
    print(f"Received from proxy: {sentence}")

    # Capitalize the sentence
    capitalizedSentence = sentence.upper()

    # Send the modified sentence back to the proxy
    connectionSocket.send(capitalizedSentence.encode())
    print(f"Sent to proxy: {capitalizedSentence}")

    connectionSocket.close()

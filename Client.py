from socket import *

proxy_host = "localhost"
proxy_port = 8888

# Create socket and connect to the proxy server
clientSocket = socket(AF_INET, SOCK_STREAM)
clientSocket.connect((proxy_host, proxy_port))

# Input sentence from the client
sentence = input('Input lowercase sentence: ')
print(f"Sending sentence to proxy: {sentence}")

# Send the sentence to the proxy
clientSocket.send(sentence.encode())

# Receive the modified sentence from the proxy
modifiedSentence = clientSocket.recv(4096).decode()
print(f"From Proxy: {modifiedSentence}")

# Close the client socket
clientSocket.close()

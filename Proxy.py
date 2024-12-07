import http.server
import socketserver
import requests

# Target server URL
TARGET_SERVER = "http://example.com"  # Replace with your target server URL

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        # Forward GET request to the target server
        target_url = f"{TARGET_SERVER}{self.path}"
        try:
            response = requests.get(target_url)
            self.send_response(response.status_code)
            for key, value in response.headers.items():
                if key.lower() != "transfer-encoding":
                    self.send_header(key, value)
            self.end_headers()
            self.wfile.write(response.content)
        except requests.RequestException as e:
            self.send_error(502, f"Error: {e}")

    def do_POST(self):
        # Forward POST request to the target server
        target_url = f"{TARGET_SERVER}{self.path}"
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            response = requests.post(target_url, data=post_data, headers=self.headers)
            self.send_response(response.status_code)
            for key, value in response.headers.items():
                if key.lower() != "transfer-encoding":
                    self.send_header(key, value)
            self.end_headers()
            self.wfile.write(response.content)
        except requests.RequestException as e:
            self.send_error(502, f"Error: {e}")

# Define server settings
PORT = 8888

# Run the server
with socketserver.TCPServer(("", PORT), ProxyHandler) as httpd:
    print(f"Proxy server running on port {PORT}")
    httpd.serve_forever()

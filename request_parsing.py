
def parse_request(request):
    # Extract request method (GET, POST, etc.)
    method = request.method

    # Extract target server's address (host)
    host = request.host.split(':')[0]  # Stripping port if included in host

    # Extract target server's port (if provided)
    port = request.host.split(':')[1] if ':' in request.host else None

    # Extract the full URL
    full_url = request.url

    # Log the information for debugging (using print in Python)
    print(f"Method: {method}")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Full URL: {full_url}")

    # Modifying headers (e.g., setting the "Host" header)
    headers = dict(request.headers)
    if 'Host' not in headers:
        headers['Host'] = host

    # Remove client-specific headers if necessary (e.g., 'Authorization')
    if 'Authorization' in headers:
        del headers['Authorization']  # Remove 'Authorization' header for proxying

    return {
        "Method": method,
        "Host": host,
        "Port": port,
        "Full URL": full_url,
        "Headers": headers
    }

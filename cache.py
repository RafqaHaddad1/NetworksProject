import socket
import threading
import time

# Cache dictionary to store responses
cache = {}
cache_lock = threading.Lock()

def get_from_cache(request):
    with cache_lock:
        if request in cache:
            entry = cache[request]
            # Check if the cache entry is still valid
            if entry["expires_at"] > time.time():
                return entry["response"]
            else:
                # Remove expired cache entry
                del cache[request]
    return None

# Function to add a response to the cache
def add_to_cache(request, response, timeout=30):
    with cache_lock:
        cache[request] = {
            "response": response,
            "expires_at": time.time() + timeout
        }
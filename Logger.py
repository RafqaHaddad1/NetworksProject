import os
from datetime import datetime

# Define log file path
LOG_FILE = 'app.log'

# Initialize a list to store logs in memory (optional)
proxy_logs = []

# Ensure log file exists (create it if not)
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'w') as log_file:
        log_file.write('')  # Create an empty file

def log_message(message):
    """Log messages with a timestamp."""
    # Create a timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Format log entry
    log_entry = f'[{timestamp}] {message}'
    # Append log entry to in-memory log list
    proxy_logs.append(log_entry)
    
    # Open the log file in append mode, now we know it exists
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(log_entry + '\n')

# Example usage:
log_message('This is a test log entry.')
log_message('Another log entry for the file.')

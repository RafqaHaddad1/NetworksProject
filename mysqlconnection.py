from flask import Flask, request, jsonify,render_template, send_from_directory

import subprocess
from flask_mysqldb import MySQL
from flask_cors import CORS 
from datetime import datetime, timedelta
import time
app = Flask(__name__,static_folder='AdminInterface')

# Configure MySQL connection
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'proxy_server'

mysql = MySQL(app)




@app.route("/")
def home():
    return send_from_directory('AdminInterface', 'index.html')

@app.route('/AdminInterface/<filename>')
def serve_static_files(filename):
    return send_from_directory('AdminInterface', filename)



BLACKLIST = set()
WHITELIST = set()


@app.route('/add-to-blacklist', methods=['POST'])
def add_to_blacklist():
    if request.method == 'POST':
        url = request.form.get('url')
        print(f"URL received: {url}") 
        if url:
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO blacklist (url) VALUES (%s)", (url,))
            mysql.connection.commit()
            cur.close()
            return {'message': 'URL added to blacklist successfully'}, 200
        return {'message': 'URL is required'}, 400

@app.route('/add-to-whitelist', methods=['POST'])
def add_to_whitelist():
   if request.method == 'POST':
        url = request.form.get('url')
        print(f"URL received: {url}") 
        if url:
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO whitelist (url) VALUES (%s)", (url,))
            mysql.connection.commit()
            cur.close()
            return {'message': 'URL added to whitelist successfully'}, 200
        return {'message': 'URL is required'}, 400



@app.route('/get-whitelist', methods=['GET'])
def get_whitelist():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM whitelist")
    whitelist = cur.fetchall()
    cur.close()

    # Check if data was retrieved
    if not whitelist:
        return jsonify({"message": "No whitelist data found"}), 404

    # Return whitelist data as JSON
    return jsonify(whitelist)


@app.route('/get-blacklist', methods=['GET'])
def get_blacklist():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM blacklist")
    blacklist = cur.fetchall()
    cur.close()

    # Check if data was retrieved
    if not blacklist:
        return jsonify({"message": "No blacklist data found"}), 404

    # Return whitelist data as JSON
    return jsonify(blacklist)

@app.route('/remove-from-whitelist', methods=['POST'])
def remove_from_whitelist():
    data = request.get_json()  # Get the JSON data sent from the client-side
    url = data.get('url')  # Get the URL to remove
    
    if not url:
        return jsonify({"message": "No URL provided"}), 400
    
    # Create a cursor object
    cur = mysql.connection.cursor()

    # Execute the SQL query to delete the URL from the whitelist
    cur.execute("DELETE FROM whitelist WHERE url = %s", (url,))
    mysql.connection.commit()  # Commit the transaction to the database

    # Check if any row was affected (i.e., URL was deleted)
    if cur.rowcount > 0:
        return jsonify({"success": True, "message": "URL removed from whitelist"})
    else:
        return jsonify({"success": False, "message": "URL not found in whitelist"}), 404


@app.route('/remove-from-blacklist', methods=['POST'])
def remove_from_blacklist():
    data = request.get_json()  # Get the JSON data sent from the client-side
    url = data.get('url')  # Get the URL to remove
    
    if not url:
        return jsonify({"message": "No URL provided"}), 400
    
    # Create a cursor object
    cur = mysql.connection.cursor()

    # Execute the SQL query to delete the URL from the whitelist
    cur.execute("DELETE FROM blacklist WHERE url = %s", (url,))
    mysql.connection.commit()  # Commit the transaction to the database

    # Check if any row was affected (i.e., URL was deleted)
    if cur.rowcount > 0:
        return jsonify({"success": True, "message": "URL removed from blacklist"})
    else:
        return jsonify({"success": False, "message": "URL not found in blacklist"}), 404


def log_message(message):
    """Log messages with a timestamp and save to MySQL database."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f'[{timestamp}] {message}'
    
    # Insert log entry into the database
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO logs (timestamp, message) VALUES (%s, %s)", (timestamp, log_entry))
        mysql.connection.commit()
        cursor.close()
    except Exception as e:
        print(f"Error saving log to the database: {e}")


# API endpoint to fetch logs
@app.route('/api/logs', methods=['GET'])
def get_logs():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT timestamp, message FROM logs ORDER BY timestamp DESC")
    logs = cursor.fetchall()
    cursor.close()

    # Convert MySQL query results to JSON
    logs_list = [{'timestamp': log[0], 'message': log[1]} for log in logs]
    return jsonify(logs_list)


@app.route('/run_curl', methods=['POST'])
def run_curl():
    cmd = request.form.get('cmd')
    if cmd:
        try:
            # Run the curl command
            curl_command = f"curl -x http://127.0.0.1:8888 {cmd}"  # Adjust this to match your setup
            result = subprocess.check_output(curl_command, shell=True, stderr=subprocess.STDOUT)
            return jsonify({"result": result.decode('utf-8')})
        except subprocess.CalledProcessError as e:
            return jsonify({"result": f"Error: {e.output.decode('utf-8')}"})
    else:
        return jsonify({"result": "No URL provided."})
    
""""
@app.route('/run_curl', methods=['POST'])
def run_curl():
    cmd = request.form.get('cmd')
    if cmd:
        try:
            # Run the curl command
            curl_command = f"curl -v http://127.0.0.1:8888 {cmd}"  # Adjust this to match your setup
            result = subprocess.check_output(curl_command, shell=True, stderr=subprocess.STDOUT)
            return jsonify({"result": result.decode('utf-8')})
        except subprocess.CalledProcessError as e:
            return jsonify({"result": f"Error: {e.output.decode('utf-8')}"})
    else:
        return jsonify({"result": "No URL provided."})
"""""

@app.route('/api/cache', methods=['GET'])
def get_cache_entries():
    """Retrieve all cache entries from the database."""
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT url, size, expires FROM cache")
        cache_entries = cursor.fetchall()
        cursor.close()

        # Prepare the cache entries to be returned as JSON
        result = []
        for entry in cache_entries:
            url, size, expires = entry
            result.append({
                'url': url,
                'size': size,
                'expires': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expires))
            })

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
if __name__ == "__main__":
    app.run(debug=True)

function loadCacheEntries() {
    // Make AJAX request to the Flask API
    fetch('/api/cache')
        .then(response => response.json())
        .then(data => {
            const tableBody = document.querySelector('#cacheTable tbody');
            tableBody.innerHTML = '';  // Clear existing table rows

            // Loop through the cache entries and create table rows
            data.forEach(entry => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${entry.url}</td>
                    <td>${entry.size} bytes</td>
                    <td>${entry.expires}</td>
                `;
                tableBody.appendChild(row);
            });
            $("#cacheTable").DataTable();
        })
        .catch(error => {
            console.error('Error fetching cache entries:', error);
        });
}
function removeItem(listId, item) {
    // Determine the URL for the request based on the listId (whitelist or blacklist)
    let url = '';
    if (listId === 'whitelist') {
        url = '/remove-from-whitelist';
    } else if (listId === 'blacklist') {
        url = '/remove-from-blacklist';
    }

    // Send a POST request to Flask to remove the item from the correct list
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: item }) // Send the URL of the item to be removed
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // If the item is successfully removed, update the list
            const list = document.getElementById(listId);
            const listItem = Array.from(list.children).find(li => li.textContent.includes(item));
            if (listItem) {
                list.removeChild(listItem);  // Remove the list item from the DOM
            }
        } else {
            alert(data.message);  // If there was an error, show the message
        }
    })
    .catch(error => {
        console.error('Error removing item:', error);
        alert('Failed to remove the item');
    });
}
  // Fetch logs from the Flask API and display them in the table
    // Fetch logs from the Flask API and display them in the table
async function fetchLogs() {
    try {
        const response = await fetch('/api/logs'); // Wait for the fetch to complete
        const logs = await response.json(); // Wait for the response to be converted to JSON

        const logsTableBody = document.querySelector('#logsTable tbody');
        logsTableBody.innerHTML = ''; // Clear any existing logs

        logs.forEach(log => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${log.timestamp}</td>
                <td>${log.message}</td>
            `;
            logsTableBody.appendChild(row);
           
         });
         $("#logsTable").DataTable(); 
    } catch (error) {
        console.error('Error fetching logs:', error);
    }
}
document.addEventListener('DOMContentLoaded', function() {
    loadWhitelist();
    loadblacklist();
    fetchLogs();
    loadCacheEntries();
    // Navigation
    const navLinks = document.querySelectorAll('.sidebar a');
    const sections = document.querySelectorAll('main section');
    // Call the loadWhitelist function when the page loads
  
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetSection = this.getAttribute('data-section');
            
            navLinks.forEach(link => link.classList.remove('active'));
            this.classList.add('active');

            sections.forEach(section => section.classList.remove('active'));
            document.getElementById(targetSection).classList.add('active');
        });
    });
    document.getElementById('domainForm').onsubmit = function(event) {
        var url = document.getElementById('domainInput').value;
        if (!url) {
            alert('Please enter a domain');
            event.preventDefault(); // Prevent form submission if URL is empty
        }
    };
    function loadWhitelist() {
        fetch('/get-whitelist')
            .then(response => response.json()) // Parse the JSON response
            .then(data => {
                const whitelist = data.map(item => item[1]); // Extract the URL from the response (assuming it's at index 1)
                updateList('whitelist', whitelist); // Update the list using the updateList function
            })
            .catch(error => {
                console.error('Error fetching whitelist:', error);
            });
    }
    function updateList(listId, items) {
        const list = document.getElementById(listId);
        list.innerHTML = ''; // Clear existing list items
        items.forEach(item => {
            const li = document.createElement('li');
            li.innerHTML = `
                ${item}
                <button onclick="removeItem('${listId}', '${item}')">Remove</button>
            `;
            list.appendChild(li);
        });
    }
    function loadblacklist() {
        fetch('/get-blacklist')
            .then(response => response.json()) // Parse the JSON response
            .then(data => {
                const blacklist = data.map(item => item[1]); // Extract the URL from the response (assuming it's at index 1)
                updateList('blacklist', blacklist); // Update the list using the updateList function
            })
            .catch(error => {
                console.error('Error fetching blacklist:', error);
            });
    }
   
    function addToBlacklist(domain) {
        fetch('/add-to-blacklist', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: domain })
        })
        .then(response => response.json())
        .then(data => {
            if (data.message === 'URL added to blacklist successfully') {
                blacklist.push(domain);
                updateList('blacklist', blacklist);
            } else {
                alert('Failed to add to blacklist');
            }
        })
        .catch(error => console.error('Error:', error));
    }  
    // Function to send an AJAX request to add a domain to the whitelist
    function addToWhitelist(domain) {
        fetch('http://localhost:5000/add-to-whitelist', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: domain })
        })
        .then(response => response.json())
        .then(data => {
            if (data.message === 'URL added to whitelist successfully') {
                whitelist.push(domain);
                updateList('whitelist', whitelist);
            } else {
                alert('Failed to add to whitelist');
            }
        })
        .catch(error => console.error('Error:', error));
    }
    
    $('#run-curl').click(function(){
        var cmd = $('#cmd-input').val();
        
        if(cmd) {
            $.ajax({
                url: '/run_curl',
                type: 'POST',
                data: { cmd: cmd },
                success: function(response) {
                    $('#viewpage').text(response.result);
                },
                error: function(error) {
                    $('#viewpage').text("An error occurred.");
                }
            });
        } else {
            alert("Please enter a URL.");
        }
    });
});
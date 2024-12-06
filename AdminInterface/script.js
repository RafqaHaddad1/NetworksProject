document.addEventListener('DOMContentLoaded', function() {
    // Navigation
    const navLinks = document.querySelectorAll('.sidebar a');
    const sections = document.querySelectorAll('main section');

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

    // Logs
    const logsData = [
        { timestamp: '2023-06-01 10:00:00', level: 'INFO', message: 'Proxy server started' },
        { timestamp: '2023-06-01 10:01:23', level: 'WARN', message: 'High CPU usage detected' },
        { timestamp: '2023-06-01 10:02:45', level: 'ERROR', message: 'Failed to connect to upstream server' },
    ];

    const logsTableBody = document.querySelector('#logsTable tbody');
    logsData.forEach(log => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${log.timestamp}</td>
            <td>${log.level}</td>
            <td>${log.message}</td>
        `;
        logsTableBody.appendChild(row);
    });

    // Cache Entries
    const cacheData = [
        { url: 'https://example.com', size: '10KB', expires: '2023-06-02 10:00:00' },
        { url: 'https://example.org', size: '5KB', expires: '2023-06-02 11:00:00' },
        { url: 'https://example.net', size: '15KB', expires: '2023-06-02 12:00:00' },
    ];

    const cacheTableBody = document.querySelector('#cacheTable tbody');
    cacheData.forEach(entry => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${entry.url}</td>
            <td>${entry.size}</td>
            <td>${entry.expires}</td>
            <td><button onclick="deleteCache('${entry.url}')">Delete</button></td>
        `;
        cacheTableBody.appendChild(row);
    });

    // Blacklist and Whitelist
    let blacklist = ['example.com', 'badsite.com'];
    let whitelist = ['goodsite.com', 'allowed.com'];

    function updateList(listId, items) {
        const list = document.getElementById(listId);
        list.innerHTML = '';
        items.forEach(item => {
            const li = document.createElement('li');
            li.innerHTML = `
                ${item}
                <button onclick="removeItem('${listId}', '${item}')">Remove</button>
            `;
            list.appendChild(li);
        });
    }

    updateList('blacklist', blacklist);
    updateList('whitelist', whitelist);

    document.getElementById('addToBlacklist').addEventListener('click', function() {
        const domain = document.getElementById('domainInput').value;
        if (domain && !blacklist.includes(domain)) {
            blacklist.push(domain);
            updateList('blacklist', blacklist);
            document.getElementById('domainInput').value = '';
        }
    });

    document.getElementById('addToWhitelist').addEventListener('click', function() {
        const domain = document.getElementById('domainInput').value;
        if (domain && !whitelist.includes(domain)) {
            whitelist.push(domain);
            updateList('whitelist', whitelist);
            document.getElementById('domainInput').value = '';
        }
    });

    window.removeItem = function(listId, item) {
        if (listId === 'blacklist') {
            blacklist = blacklist.filter(i => i !== item);
            updateList('blacklist', blacklist);
        } else if (listId === 'whitelist') {
            whitelist = whitelist.filter(i => i !== item);
            updateList('whitelist', whitelist);
        }
    };

    window.deleteCache = function(url) {
        // In a real application, you would send a request to your server to delete the cache entry
        console.log(`Deleting cache entry for ${url}`);
        // For this example, we'll just remove it from the table
        const row = Array.from(cacheTableBody.querySelectorAll('tr')).find(row => row.cells[0].textContent === url);
        if (row) {
            row.remove();
        }
    };
});
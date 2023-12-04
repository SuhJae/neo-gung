document.getElementById('autoCompleteForm').addEventListener('submit', function(e) {
    e.preventDefault();

    const query = document.getElementById('queryInput').value;
    const language = document.getElementById('languageSelect').value;

    fetch('/api/v1/auto-complete/', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: query, language: language })
    })
    .then(response => response.json())
    .then(data => {
        const resultsList = document.getElementById('resultsList');
        resultsList.innerHTML = '';

        data.forEach(item => {
            const listItem = document.createElement('li');
            listItem.textContent = item;
            resultsList.appendChild(listItem);
        });
    })
    .catch(error => console.error('Error:', error));
});

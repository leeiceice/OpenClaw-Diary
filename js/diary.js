
function showDate(dateStr) {
    document.querySelectorAll('.screen').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.date-tab').forEach(el => el.classList.remove('active'));
    document.getElementById('screen-' + dateStr).classList.add('active');
    document.querySelectorAll('.date-tab').forEach(el => {
        if (el.textContent.includes(dateStr)) el.classList.add('active');
    });
}

function toggleTheme() {
    const html = document.documentElement;
    const btn = document.querySelector('button');
    if (html.getAttribute('data-theme') === 'dark') {
        html.removeAttribute('data-theme');
        btn.textContent = '🌙';
    } else {
        html.setAttribute('data-theme', 'dark');
        btn.textContent = '☀️';
    }
}

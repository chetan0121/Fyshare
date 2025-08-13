const themeToggle = document.getElementById('themeToggle');
const body = document.body;
const themeIcon = document.querySelector('.theme-icon');
const anim_duration = 400; //In ms, Match CSS transition time of theme-icon

// Check for saved theme preference
const savedTheme = localStorage.getItem('theme');
if (savedTheme === 'dark') {
    body.classList.add('dark-theme');
    themeIcon.textContent = '🌙';
} else {
    themeIcon.textContent = '☀️';
}

function updateThemeIcon() {
    const isDark = body.classList.contains('dark-theme');
    themeIcon.textContent = isDark ? '🌙' : '☀️';
}

function animateIcon() {
    themeIcon.classList.add('theme-animate');
    setTimeout(() => {
        themeIcon.classList.remove('theme-animate');
    }, anim_duration); 
}

themeToggle.addEventListener('click', () => {
    body.classList.toggle('dark-theme');
    animateIcon();
    setTimeout(updateThemeIcon, anim_duration/2);
    localStorage.setItem('theme', body.classList.contains('dark-theme') ? 'dark' : 'light');
});

// To go back using backspace
document.addEventListener('keydown', function(event) {
    if (event.key === 'Backspace') {
        // Avoid this triggering when typing in input or textarea
        const target = event.target;
        const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable;

        if (!isInput) {
            event.preventDefault(); // prevent default browser behavior
            window.history.back();  // go back to the previous page
        }
    }
});

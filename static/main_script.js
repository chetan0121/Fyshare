const themeToggle = document.getElementById('themeToggle');
const root = document.documentElement;
const themeIcon = document.querySelector('.theme-icon');

const anim_duration = 400; //In ms
document.documentElement.style.setProperty('--anim-duration', anim_duration+'ms');

updateTheme(root.classList.contains('dark-theme'));

// Change the UI theme if system theme changed
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', event => {
    updateTheme(event.matches);
});

function updateTheme(isDark){
    root.classList.toggle('dark-theme', isDark);
    sessionStorage.setItem('theme', isDark ? 'dark' : 'light');
    themeIcon.textContent = isDark ? '🌙' : '☀️';
}

function animateIcon() {
    themeIcon.classList.add('theme-animate');
    setTimeout(
        () => themeIcon.classList.remove('theme-animate'), anim_duration
    ); 
}

themeToggle.addEventListener('click', () => {
    root.classList.toggle('dark-theme');
    animateIcon();
    setTimeout(() => {
        const isDark = root.classList.contains('dark-theme');
        updateTheme(isDark);
    }, anim_duration/2);
});

// Go back(exit dir) using backspace
document.addEventListener('keydown', function(event) {
    if (event.key === 'Backspace') {
        const target = event.target;
        const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable;

        // Avoid this triggering when typing in input or textarea
        if (!isInput) {
            event.preventDefault(); // prevent default browser behavior
            window.history.back();  // go back to the previous page
        }
    }
});

// Handle UI for empty directories
const tbody = document.querySelector('.table-wrapper table tbody');
const emptyState = document.getElementById('empty-dir');
const parent_dir = document.getElementById('parent-dir') !== null ? 1 : 0;

const totalDir = tbody.querySelectorAll('.table-wrapper table tbody tr').length

// Check if no dir ()
if (totalDir <= parent_dir) {
    emptyState.hidden = false;
}

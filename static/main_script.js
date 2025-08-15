const themeToggle = document.getElementById('themeToggle');
const body = document.body;
const themeIcon = document.querySelector('.theme-icon');
const anim_duration = 400; //In ms, Match CSS animation duration of theme-icon

const savedTheme = sessionStorage.getItem('theme'); // Get theme preference if saved

if (savedTheme) {
    updateTheme(savedTheme === 'dark');
} else {
    updateTheme(window.matchMedia('(prefers-color-scheme: dark)').matches);
}

window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', event => {
    updateTheme(event.matches);
});

function updateTheme(isDark){
    body.classList.toggle('dark-theme', isDark);
    sessionStorage.setItem('theme', isDark ? 'dark' : 'light');
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
    setTimeout(() => {
        const isDark = body.classList.contains('dark-theme');
        updateTheme(isDark);
    }, anim_duration/2);
});


// Exit dir using backspace
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

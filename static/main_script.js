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

    // if (event.key === 'ArrowRight' && currentIndex < imageList.length-1) {
    //     loadImage(currentIndex + 1);
    // } else if (event.key === 'ArrowLeft' && currentIndex > 0) {
    //     loadImage(currentIndex - 1);
    // }
});


let scrollTimeout;
const scrollContainer = document.querySelector('.table-wrapper');
const path = window.location.pathname;

if (scrollContainer) {

    scrollContainer.addEventListener('scroll', () => {
        clearTimeout(scrollTimeout);
        scrollTimeout = setTimeout(() => {
            localStorage.setItem(`scrollPos_${path}`, scrollContainer.scrollTop);
        }, 150);
    });

    // Restore scroll position
    const savedPosition = localStorage.getItem(`scrollPos_${path}`);
    if (savedPosition !== null) {
        scrollContainer.scrollTop = parseInt(savedPosition, 10) || 0;
    }
}

// // Image navigation
// const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'];
// const LinkTags = document.querySelectorAll('.table-wrapper table tbody tr td a');
// const imageList = Array.from(LinkTags)
//   .map(a => a.href)
//   .filter(href => imageExtensions.some(ext => href.toLowerCase().endsWith(ext)));

// let currentIndex = 0;

// let viewer = document.getElementById('viewer');
// if (!viewer) {
//   viewer = document.createElement('img');
//   viewer.id = 'viewer';
//   viewer.style.maxWidth = '90vw';
//   viewer.style.maxHeight = '80vh';
//   viewer.style.display = 'block';
//   viewer.style.margin = '20px auto';
//   document.body.appendChild(viewer);
// }

// function loadImage(index) {
//   if (index < 0 || index >= imageList.length) return;

//   const tempImg = new Image();
//   tempImg.onload = () => {
//     viewer.src = tempImg.src;
//     if(index < imageList.length-1 && index > 0) currentIndex = index;
//   };
//   tempImg.onerror = () => {
//     console.warn('Skipping broken image:', imageList[index]);
//     const nextIndex = index > currentIndex ? index + 1 : index - 1;
//     loadImage(nextIndex);
//   };
//   tempImg.src = imageList[index];
// }

// document.addEventListener('keydown', (e) => {
//     if (e.key === 'ArrowRight' && currentIndex < imageList.length-1) {
//         loadImage(currentIndex + 1);
//     } else if (e.key === 'ArrowLeft' && currentIndex > 0) {
//         loadImage(currentIndex - 1);
//     }
// });

// // clicking anchor loads it into viewer
// LinkTags.forEach((a, i) => {
//   const index = imageList.indexOf(a.href);
//   if (index !== -1) {
//     a.addEventListener('click', (e) => {
//       e.preventDefault();
//       loadImage(index);
//     });
//   }
// });

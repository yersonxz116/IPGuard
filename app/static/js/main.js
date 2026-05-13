const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const heroVideo = document.getElementById('heroVideo');

if (heroVideo) {
    heroVideo.play().catch(() => {});
}

document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: reducedMotion ? 'auto' : 'smooth',
                block: 'start'
            });
        }
    });
});

const navbar = document.querySelector('.navbar');
let ticking = false;
if (navbar) {
    window.addEventListener('scroll', function() {
        if (!ticking) {
            requestAnimationFrame(() => {
                navbar.style.background = window.scrollY > 50
                    ? 'rgba(26, 26, 26, 0.98)'
                    : 'rgba(26, 26, 26, 0.95)';
                ticking = false;
            });
            ticking = true;
        }
    });
}

const mvCards = document.querySelectorAll('.mv-card');
if (mvCards.length) {
    const mvObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('mv-visible');
                mvObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.2 });
    mvCards.forEach(card => mvObserver.observe(card));
}

const objAnimElements = document.querySelectorAll('.obj-animate--left, .obj-animate--right');
if (objAnimElements.length) {
    const objObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('obj-visible');
                objObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.15 });
    objAnimElements.forEach(el => objObserver.observe(el));
}

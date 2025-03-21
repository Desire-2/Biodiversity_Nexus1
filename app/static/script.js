document.addEventListener("DOMContentLoaded", function () {
    const backToTop = document.querySelector('.back-to-top');

    window.addEventListener('scroll', () => {
        if (window.scrollY > 300) {
            backToTop.classList.add('show');
        } else {
            backToTop.classList.remove('show');
        }
    });
});

function scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

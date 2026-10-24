const duration = 25000; // 25 seconds of scrolling
const startTime = Date.now();
const totalHeight = document.body.scrollHeight - window.innerHeight;
const scrollStep = totalHeight / (duration / 16); // ~60fps

const timer = setInterval(() => {
    const elapsed = Date.now() - startTime;
    if (elapsed >= duration) {
        clearInterval(timer);
        // Hold at bottom for 3 seconds then navigate
        setTimeout(() => {
            window.location.href = '/dashboard';
        }, 3000);
        return;
    }
    window.scrollBy(0, scrollStep * (elapsed / 16));
}, 16);

console.log('Auto-scroll started for ' + duration + 'ms');
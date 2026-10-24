const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');

const CHROME_PATH = path.join(process.env.LOCALAPPDATA, '.cache', 'puppeteer', 'chrome', 'win64-155.0.8059.79', 'chrome-win64', 'chrome.exe');
const OUTPUT_DIR = path.join(__dirname, '..', 'demo-preparation', 'rebuild-demo-raw');

async function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function main() {
    if (!fs.existsSync(OUTPUT_DIR)) {
        fs.mkdirSync(OUTPUT_DIR, { recursive: true });
    }

    const browser = await puppeteer.launch({
        executablePath: CHROME_PATH,
        headless: 'new',
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--window-size=1920,1080',
            '--force-device-scale-factor=1',
            '--hide-scrollbars',
            '--mute-audio',
        ],
        defaultViewport: { width: 1920, height: 1080, deviceScaleFactor: 1 },
    });

    const page = await browser.newPage();

    // Configure page for screencasting
    await page.evaluateOnNewDocument(() => {
        // Hide scrollbars for cleaner recording
        const style = document.createElement('style');
        style.innerHTML = '::-webkit-scrollbar { display: none !important; }';
        document.head.appendChild(style);
    });

    try {
        console.log('=== Starting Interactive Walkthrough Recording ===');

        // Scene 1: Landing page (3 seconds)
        console.log('Scene 1: Landing page intro...');
        await page.goto('http://127.0.0.1:3000/', { waitUntil: 'networkidle0', timeout: 30000 });
        await delay(2000);

        // Click "Open CodeMemory" on landing page
        const openButton = await page.$('a[href="/dashboard"]');
        if (openButton) {
            await openButton.click();
        }
        await delay(2000);

        // Scene 2: Dashboard - show populated data (5 seconds)
        console.log('Scene 2: Dashboard populated...');
        await page.goto('http://127.0.0.1:3000/dashboard', { waitUntil: 'networkidle0', timeout: 30000 });
        await delay(3000);

        // Scroll to see activity
        await page.evaluate(() => window.scrollBy(0, 500));
        await delay(1000);

        // Scene 3: Navigate to Settings - Show sync state (4 seconds)
        console.log('Scene 3: Settings page...');
        await page.goto('http://127.0.0.1:3000/settings', { waitUntil: 'networkidle0', timeout: 30000 });
        await delay(3000);

        // Click on Account section
        const accountLink = await page.$('a[href="#account"], a[href="#data"]');
        if (accountLink) {
            await accountLink.click();
        }
        await delay(1000);

        // Scene 4: Problems page - search for a problem (5 seconds)
        console.log('Scene 4: Problems page...');
        await page.goto('http://127.0.0.1:3000/problems', { waitUntil: 'networkidle0', timeout: 30000 });
        await delay(2000);

        // Search for a problem
        const searchInput = await page.$('input[placeholder*="Search" i], input[type="search"]');
        if (searchInput) {
            await searchInput.type('two sum');
            await delay(2000);
        }

        // Scene 5: Open a problem detail (4 seconds)
        console.log('Scene 5: Problem detail...');
        await page.goto('http://127.0.0.1:3000/problems/two-sum', { waitUntil: 'networkidle0', timeout: 30000 });
        await delay(3000);

        // Scene 6: Analytics page (4 seconds)
        console.log('Scene 6: Analytics...');
        await page.goto('http://127.0.0.1:3000/analytics', { waitUntil: 'networkidle0', timeout: 30000 });
        await delay(3000);

        // Scene 7: Knowledge graph (4 seconds)
        console.log('Scene 7: Knowledge graph...');
        await page.goto('http://127.0.0.1:3000/knowledge', { waitUntil: 'networkidle0', timeout: 30000 });
        await delay(3000);

        // Scene 8: Revision queue (3 seconds)
        console.log('Scene 8: Revision queue...');
        await page.goto('http://127.0.0.1:3001/revision', { waitUntil: 'networkidle0', timeout: 30000 }).catch(() => {});
        await page.goto('http://127.0.0.1:3000/revision', { waitUntil: 'networkidle0', timeout: 30000 });
        await delay(3000);

        console.log('=== Recording complete ===');
    } catch (error) {
        console.error('Error:', error);
    } finally {
        await browser.close();
    }
}

main();

const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');

const CHROME_PATH = path.join(process.env.LOCALAPPDATA, '.cache', 'puppeteer', 'chrome', 'win64-155.0.8059.79', 'chrome-win64', 'chrome.exe');
const OUTPUT_DIR = path.join(__dirname, '..', 'demo-preparation', 'rebuild-demo-raw', 'screenshots');

async function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function captureScreenshots() {
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
        ],
        defaultViewport: null,
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });

    async function screenshot(name) {
        const filePath = path.join(OUTPUT_DIR, name);
        await page.screenshot({ path: filePath, fullPage: true });
        console.log(`Captured: ${name}`);
    }

    async function clickSelector(selector) {
        await page.waitForSelector(selector, { timeout: 10000 });
        await page.click(selector);
        await delay(500);
    }

    try {
        // Scene 1: Brief landing page intro
        console.log('Loading landing page...');
        await page.goto('http://127.0.0.1:3000/', { waitUntil: 'networkidle0', timeout: 30000 });
        await delay(1000);
        await screenshot('01-landing.png');
        await delay(500);

        // Click "Open CodeMemory" button to go to dashboard
        await clickSelector('a[href="/dashboard"]');
        await delay(2000);
        await screenshot('02-dashboard.png');
        await delay(500);

        // Scene 2: Navigate to connect page (Settings)
        console.log('Navigating to settings...');
        // First go to dashboard and then click settings link
        await page.goto('http://127.0.0.1:3000/settings', { waitUntil: 'networkidle0', timeout: 30000 });
        await delay(1000);
        await screenshot('03-settings-page.png');
        await delay(500);

        // Now let's go to the connect page and simulate the username connection
        // But first, let's disconnect (the credentials are already stored from our API call)
        console.log('Disconnecting LeetCode...');
        // Click "Disconnect" on the settings page
        await page.goto('http://127.0.0.1:3000/connect', { waitUntil: 'networkidle0', timeout: 30000 });
        await delay(2000);
        await screenshot('04-connect-page.png');
        await delay(500);

        // Scene 3: Show the settings page with credentials already stored (no typing shown)
        await page.goto('http://127.0.0.1:3000/settings', { waitUntil: 'networkidle0', timeout: 30000 });
        await delay(2000);
        await screenshot('05-settings-auth-stored.png');
        await delay(500);

        // Scene 4: Show dashboard with populated data
        await page.goto('http://127.0.0.1:3000/dashboard', { waitUntil: 'networkidle0', timeout: 30000 });
        await delay(2000);
        await screenshot('06-dashboard-populated.png');
        await delay(500);

        // Scene 5: Show problems page
        await page.goto('http://127.0.0.1:3000/problems', { waitUntil: 'networkidle0', timeout: 30000 });
        await delay(2000);
        await screenshot('07-problems-page.png');
        await delay(500);

        // Scene 6: Show a specific problem
        await page.goto('http://127.0.0.1:3000/problems/two-sum', { waitUntil: 'networkidle0', timeout: 30000 });
        await delay(2000);
        await screenshot('08-problem-detail.png');
        await delay(500);

        // Scene 7: Show analytics page
        await page.goto('http://127.0.0.1:3000/analytics', { waitUntil: 'networkidle0', timeout: 30000 });
        await delay(2000);
        await screenshot('09-analytics-page.png');
        await delay(500);

        // Scene 8: Show knowledge graph
        await page.goto('http://127.0.0.1:3000/knowledge', { waitUntil: 'networkidle0', timeout: 30000 });
        await delay(3000);
        await screenshot('10-knowledge-page.png');
        await delay(500);

        // Scene 9: Show revision queue
        await page.goto('http://127.0.0.1:3000/revision', { waitUntil: 'networkidle0', timeout: 30000 });
        await delay(2000);
        await screenshot('11-revision-page.png');
        await delay(500);

        // Scene 10: Show search
        await page.goto('http://127.0.0.1:3000/search', { waitUntil: 'networkidle0', timeout: 30000 });
        await delay(1000);
        // Type in search
        await page.type('input[placeholder*="search" i], input[type="search"]', 'two sum');
        await delay(2000);
        await screenshot('12-search-results.png');
        await delay(500);

        console.log('All screenshots captured successfully!');
    } catch (error) {
        console.error('Error during capture:', error);
    } finally {
        await browser.close();
    }
}

captureScreenshots();

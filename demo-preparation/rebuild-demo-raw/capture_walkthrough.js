const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const SCREENS_DIR = 'screens';

async function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function main() {
    if (!fs.existsSync(SCREENS_DIR)) {
        fs.mkdirSync(SCREENS_DIR, { recursive: true });
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
            '--disable-extensions',
        ],
        defaultViewport: { width: 1920, height: 1080, deviceScaleFactor: 1 },
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });

    await page.addStyleTag({
        content: `
            ::-webkit-scrollbar { display: none !important; }
            * { scrollbar-width: none !important; -ms-overflow-style: none !important; }
        `
    });

    await page.setDefaultNavigationTimeout(120000);

    async function screenshot(name) {
        const filePath = path.join(SCREENS_DIR, name);
        await page.screenshot({ path: filePath, fullPage: true });
        console.log(`Captured: ${name}`);
    }

    const timeline = [];

    try {
        console.log('=== CodeMemory End-to-End Demo Recording ===\n');

        // ============================================================
        // Scene 1: Landing Page (3s)
        // ============================================================
        console.log('Scene 1: Landing page...');
        timeline.push({ scene: 'intro', start: 0, end: 3 });
        await page.goto('http://127.0.0.1:3000/', { waitUntil: 'domcontentloaded' });
        await delay(2000);
        await screenshot('01-landing.png');

        // Click "Open CodeMemory"
        const openBtn = await page.$('a[href="/dashboard"]');
        if (openBtn) {
            await openBtn.click();
            timeline.push({ scene: 'intro', transition: 'click_open', time: 2.5 });
        }
        await delay(500);

        // ============================================================
        // Scene 2: LeetCode Connection (10s)
        // ============================================================
        console.log('Scene 2: Connect LeetCode page...');
        timeline.push({ scene: 'connect', start: 4 });
        
        await page.goto('http://127.0.0.1:3000/connect', { waitUntil: 'domcontentloaded' });
        await delay(1500);
        await screenshot('02-connect-empty.png');

        // Type username - show the interaction
        const usernameInput = await page.$('input[name="username"], input[id="leetcode-username"]');
        if (usernameInput) {
            // Focus first
            await page.hover('input[name="username"], input[id="leetcode-username"]');
            await delay(500);
            await screenshot('02a-connect-field-focus.png');
            
            await usernameInput.type('jaypatil1229', { delay: 100 });
            await delay(500);
            await screenshot('02b-username-typed.png');
        }
        timeline.push({ scene: 'connect', action: 'username_typed', time: 7 });

        // Click Connect button
        const connectBtn = await page.$('button[type="submit"]');
        if (connectBtn) {
            await page.hover('button[type="submit"]');
            await delay(300);
            await screenshot('02c-connect-button-hover.png');
            await connectBtn.click();
            console.log('  Clicked Connect button...');
            timeline.push({ scene: 'connect', action: 'click_connect', time: 8 });
        }

        // Show processing state (public sync starts)
        await delay(3000);
        await screenshot('02d-connect-processing.png');

        // Wait for sync to complete
        await delay(10000);
        await screenshot('02e-connect-success.png');
        timeline.push({ scene: 'connect', action: 'success', end: 22 });

        // ============================================================
        // Scene 3: Settings - Authenticated Sync (8s)
        // Credentials are ALREADY stored (via API, off-camera)
        // ============================================================
        console.log('Scene 3: Settings page...');
        timeline.push({ scene: 'settings', start: 23 });

        await page.goto('http://127.0.0.1:3000/settings', { waitUntil: 'domcontentloaded' });
        await delay(2000);
        await screenshot('03-settings-page.png');

        // Scroll to Account section to show credentials stored
        await page.evaluate(() => {
            // Find account section
            const headings = document.querySelectorAll('h3');
            for (const h of headings) {
                if (h.textContent && h.textContent.includes('Full history')) {
                    h.scrollIntoView({ behavior: 'auto', block: 'center' });
                    window.scrollBy(0, -150);
                    break;
                }
            }
        });
        await delay(1000);
        await screenshot('03b-settings-auth-section.png');

        // Highlight the credentials stored status
        await page.evaluate(() => {
            // Scroll to show "Credentials stored" status
            window.scrollBy(0, 200);
        });
        await delay(500);
        await screenshot('03c-settings-stored-status.png');

        // Show the "Sync full history" button area
        await page.evaluate(() => {
            const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Sync full history'));
            if (btn) {
                btn.scrollIntoView({ behavior: 'auto', block: 'center' });
                window.scrollBy(0, -50);
            }
        });
        await delay(500);
        await screenshot('03d-settings-sync-btn.png');
        timeline.push({ scene: 'settings', end: 31 });

        // ============================================================
        // Scene 4: Dashboard (5s) - Populated data
        // ============================================================
        console.log('Scene 4: Dashboard...');
        timeline.push({ scene: 'dashboard', start: 32 });
        await page.goto('http://127.0.0.1:3000/dashboard', { waitUntil: 'domcontentloaded' });
        await delay(2000);
        await screenshot('04-dashboard-populated.png');

        await page.evaluate(() => window.scrollBy(0, 600));
        await delay(1000);
        await screenshot('04b-dashboard-insights.png');
        timeline.push({ scene: 'dashboard', end: 37 });

        // ============================================================
        // Scene 5: Problems Page (5s)
        // ============================================================
        console.log('Scene 5: Problems page...');
        timeline.push({ scene: 'problems', start: 38 });
        await page.goto('http://127.0.0.1:3000/problems', { waitUntil: 'domcontentloaded' });
        await delay(2000);
        await screenshot('05-problems-list.png');

        const searchInput = await page.$('input[placeholder*="Search" i]');
        if (searchInput) {
            await searchInput.type('two', { delay: 150 });
            await delay(1500);
            await screenshot('05b-problems-filtered.png');
        }
        timeline.push({ scene: 'problems', end: 43 });

        // ============================================================
        // Scene 6: Problem Detail (5s)
        // ============================================================
        console.log('Scene 6: Problem detail...');
        timeline.push({ scene: 'problem', start: 44 });
        await page.goto('http://127.0.0.1:3000/problems?slug=two-sum', { waitUntil: 'domcontentloaded' });
        await delay(3000);
        await screenshot('06-problem-detail.png');

        await page.evaluate(() => window.scrollBy(0, 700));
        await delay(1000);
        await screenshot('06b-problem-submissions.png');
        timeline.push({ scene: 'problem', end: 49 });

        // ============================================================
        // Scene 7: Search (4s)
        // ============================================================
        console.log('Scene 7: Search...');
        timeline.push({ scene: 'search', start: 50 });
        await page.goto('http://127.0.0.1:3000/search', { waitUntil: 'domcontentloaded' });
        await delay(1000);

        const globalSearch = await page.$('input[placeholder*="search" i]');
        if (globalSearch) {
            await globalSearch.type('median', { delay: 150 });
            await delay(2000);
            await screenshot('07-search-results.png');
        }
        timeline.push({ scene: 'search', end: 54 });

        // ============================================================
        // Scene 8: Analytics (5s)
        // ============================================================
        console.log('Scene 8: Analytics...');
        timeline.push({ scene: 'analytics', start: 55 });
        await page.goto('http://127.0.0.1:3000/analytics', { waitUntil: 'domcontentloaded' });
        await delay(2000);
        await screenshot('08-analytics-charts.png');

        await page.evaluate(() => window.scrollBy(0, 500));
        await delay(1000);
        await screenshot('08b-analytics-insights.png');
        timeline.push({ scene: 'analytics', end: 60 });

        // ============================================================
        // Scene 9: Knowledge Graph (4s)
        // ============================================================
        console.log('Scene 9: Knowledge graph...');
        timeline.push({ scene: 'knowledge', start: 61 });
        await page.goto('http://127.0.0.1:3000/knowledge', { waitUntil: 'domcontentloaded' });
        await delay(3000);
        await screenshot('09-knowledge-graph.png');
        timeline.push({ scene: 'knowledge', end: 65 });

        // ============================================================
        // Scene 10: Revision Queue (4s)
        // ============================================================
        console.log('Scene 10: Revision queue...');
        timeline.push({ scene: 'revision', start: 66 });
        await page.goto('http://127.0.0.1:3000/revision', { waitUntil: 'domcontentloaded' });
        await delay(2000);
        await screenshot('10-revision-queue.png');
        timeline.push({ scene: 'revision', end: 70 });

        // ============================================================
        // Scene 11: Closing (4s)
        // ============================================================
        console.log('Scene 11: Closing...');
        timeline.push({ scene: 'closing', start: 71, end: 75 });
        await page.goto('http://127.0.0.1:3000/', { waitUntil: 'domcontentloaded' });
        await delay(2000);
        await screenshot('11-closing.png');

        console.log('\n=== All screenshots captured ===');
        fs.writeFileSync('timeline.json', JSON.stringify(timeline, null, 2));
        console.log('Timeline saved');
    } catch (error) {
        console.error('Error:', error);
    } finally {
        await browser.close();
    }
}

main();

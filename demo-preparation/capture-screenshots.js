const puppeteer = require('puppeteer-core');
const { spawn } = require('child_process');
const path = require('path');

const CHROME_PATH = path.join(require('os').homedir(), '.cache/puppeteer/chrome/win64-155.0.8059.79/chrome-win64/chrome.exe');

async function captureScreenshots() {
    const browser = await puppeteer.launch({
        executablePath: CHROME_PATH,
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--force-device-scale-factor=1']
    });
    
    const page = await browser.newPage();
    await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
    
    // Navigate to landing page
    console.log('Navigating to landing page...');
    await page.goto('http://127.0.0.1:3001', { waitUntil: 'networkidle0', timeout: 20000 });
    
    // Wait for page to render
    await page.waitForTimeout(3000);
    
    // Capture full page screenshot
    const fullPageHeight = await page.evaluate(() => document.body.scrollHeight);
    console.log('Full page height:', fullPageHeight);
    
    // Set viewport to full page height for full screenshot
    await page.setViewport({ width: 1920, height: fullPageHeight, deviceScaleFactor: 1 });
    await page.waitForTimeout(500);
    
    await page.screenshot({ 
        path: 'demo-preparation/recordings/landing-full.png',
        fullPage: true,
        type: 'png'
    });
    console.log('Saved landing-full.png');
    
    // Now capture key sections with scroll positions
    const sections = [
        { name: 'hero', scrollY: 0 },
        { name: 'product-premiere', scrollY: 300 },
        { name: 'memory-trace', scrollY: 600 },
        { name: 'solution-evolution', scrollY: 1200 },
        { name: 'analytics', scrollY: 1900 },
        { name: 'knowledge', scrollY: 2500 },
        { name: 'revision', scrollY: 3100 },
        { name: 'cta', scrollY: Math.max(0, fullPageHeight - 1080) },
    ];
    
    // Go back to normal viewport
    await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
    await page.waitForTimeout(500);
    
    for (const section of sections) {
        await page.evaluate((y) => window.scrollTo(0, y), section.scrollY);
        await page.waitForTimeout(300);
        await page.screenshot({
            path: `demo-preparation/recordings/section-${section.name}.png`,
            type: 'png'
        });
        console.log(`Saved section-${section.name}.png at scrollY=${section.scrollY}`);
    }
    
    await browser.close();
    console.log('Done!');
}

captureScreenshots().catch(console.error);
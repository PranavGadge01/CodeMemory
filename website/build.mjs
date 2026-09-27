import { mkdir, readFile, writeFile, cp } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = dirname(fileURLToPath(import.meta.url));
const release = JSON.parse(await readFile(join(root, '../release.json'), 'utf8'));
const out = join(root, 'out');
const localArtifacts = process.env.CODEMEMORY_RELEASE_DIR;
const available = Boolean(localArtifacts) || release.published;
const base = localArtifacts ? `/releases/v${release.version}` : `${release.repository}/releases/download/v${release.version}`;
const esc = (/** @type {string} */ text) => text.replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
const mark = '<svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true"><rect x=".75" y=".75" width="22.5" height="22.5" rx="6" fill="#141518" stroke="#33363b"/><g stroke="#ffa116" stroke-width="1.5" stroke-linecap="round"><path d="M6 5.5v13M6 7.6h6.4M6 12h9.2M6 16.4h4.2"/></g><g fill="#ffa116"><circle cx="12.4" cy="7.6" r="1.7"/><circle cx="15.2" cy="12" r="1.7"/><circle cx="10.2" cy="16.4" r="1.7"/></g></svg>';
const cta = '<a class="button primary" href="/download/">Download for Windows</a>';
function page(/** @type {string} */ title, /** @type {string} */ content, download = false) {
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#07080a"><meta name="description" content="Your coding history, remembered. Keep, search and revisit your LeetCode submissions in a local Windows workspace."><title>${title} · CodeMemory</title><link rel="icon" href="/assets/mark.svg"><link rel="stylesheet" href="/style.css"><link rel="preload" href="/assets/Geist-Regular.woff2" as="font" type="font/woff2" crossorigin></head><body><a class="skip" href="#main">Skip to content</a><header class="nav wrap"><a class="brand" href="/">${mark}CodeMemory</a><nav aria-label="Main navigation"><a href="/#memory">Explore</a><a href="/download/" ${download ? 'aria-current="page"' : ''}>Download</a><a href="${release.repository}">GitHub</a></nav></header>${content}<footer class="wrap"><a class="brand" href="/">${mark}CodeMemory</a><p>Your coding history, remembered.</p><a href="${release.repository}">Source & documentation</a></footer></body></html>`;
}
const home = page('Your coding history, remembered', `<main id="main">
  <section class="hero wrap">
    <div><p class="intro">A personal workspace for your LeetCode history</p><h1>Your coding history,<br>remembered.</h1><p class="lead">You remember the accepted solution.<br>Keep the thinking that got you there.</p><p class="hero-copy">Turn your LeetCode submissions into a searchable memory of attempts, lessons, and progress. On your own computer.</p><div class="actions">${cta}<a class="text-link" href="#memory">Explore CodeMemory</a></div><p class="fine">Windows 10/11 · Local storage · Optional full history sync</p></div>
    <figure class="trace"><figcaption>A submission is only the beginning.</figcaption><ol><li><span class="node"></span><h3>Your attempts</h3><p>Accepted solutions. Failed approaches. Available code.</p></li><li><span class="node"></span><h3>Your understanding</h3><p>Notes, mistakes, and the changes between submissions.</p></li><li><span class="node"></span><h3>Your next review</h3><p>A reason to revisit. A chance to solve it better.</p></li></ol><p class="trace-foot">History → understanding → recall</p></figure>
  </section>
  <section id="memory" class="memory wrap"><div class="section-heading"><h2>Keep more than<br>the green check.</h2><p>For the problems you solved once and the ideas you want to keep using.</p></div><div class="features">
    <article><h3>Follow the whole attempt</h3><p>Browse submissions by problem. Open status, language, runtime, memory, and code when LeetCode makes it available. Full history sync includes failed submissions.</p></article>
    <article><h3>See what changed</h3><p>Follow a problem’s submission evolution. Keep the reasoning, mistakes, and patterns that explain how your approach developed.</p></article>
    <article><h3>Find the idea again</h3><p>Search your imported history and notes. Memory search connects a question with relevant material from the active account.</p></article>
    <article><h3>Make revision deliberate</h3><p>Use an explainable priority queue based on difficulty, failures, recency, and topic weakness. Record a review and keep your own notes.</p></article>
    <article><h3>Read your progress</h3><p>Explore activity, topic coverage, language use, and difficulty trends derived from your actual submissions.</p></article>
    <article><h3>Keep accounts separate</h3><p>Switch LeetCode profiles without mixing private notes, review state, search results, or revision priorities.</p></article>
  </div></section>
  <section class="privacy"><div class="wrap privacy-grid"><h2>Your history belongs<br>on your computer.</h2><div><p class="lead">A local workspace.<br>A connection when you need it.</p><p>Imported data and preferences live on your Windows device. Sync connects to LeetCode. Optional authenticated sync stores credentials encrypted through the operating system’s credential vault.</p><p>Start with your public username. Add credentials only when you want full submission history and available code. Optional AI features may contact your configured provider.</p></div></div></section>
  <section class="start wrap"><h2>Pick up where<br>your last attempt left off.</h2><ol class="steps"><li><span>1</span>Install CodeMemory for Windows.</li><li><span>2</span>Connect your LeetCode username.</li><li><span>3</span>Sync recent history and open your workspace.</li></ol>${cta}</section>
</main>`);
const platforms = release.platforms.map((/** @type {{name: string, requirements: string, artifacts: {file: string, label: string, kind: string}[]}} */ platform) => `<section class="download-panel" aria-label="${esc(platform.name)} download"><div class="platform-icon" aria-hidden="true">⊞</div><h2>CodeMemory for ${esc(platform.name)}</h2><p>${esc(platform.requirements)}</p><p class="version">Version ${esc(release.version)}</p><div class="actions">${platform.artifacts.map((artifact, index) => available ? `<a class="button ${index === 0 ? 'primary' : 'secondary'}" href="${esc(base + '/' + artifact.file.replaceAll('{version}', release.version))}" download>${esc(artifact.label)}</a>` : `<button class="button ${index === 0 ? 'primary' : 'secondary'}" disabled>${esc(artifact.label)}</button>`).join('')}</div>${available ? '<p class="fine">Choose the standard installer, or MSI for managed installation.</p>' : '<p class="availability" role="status">The Windows release is being prepared. Downloads will appear here when the verified installers are published.</p>'}</section>`).join('');
const download = page('Download', `<main id="main" class="wrap download"><p class="intro">Your next coding session starts here</p><h1>A home for<br>your coding history.</h1><p class="lead">Install once. Keep learning from every attempt.</p>${platforms}<div class="download-notes"><section><h2>After installation</h2><p>Open CodeMemory, choose Get Started, and enter your LeetCode username. Public sync imports recent accepted submissions. Add credentials in Settings for full history and available code.</p></section><section><h2>Updating CodeMemory</h2><p>Close the app before running a newer installer. Your local history, notes, account settings, and encrypted credentials stay in your Windows user data folder.</p></section><section><h2>Other platforms</h2><p>Windows is the current desktop target. macOS and Linux installers are not available.</p></section><section><h2>Release information</h2><p><a href="${release.repository}/releases">View GitHub releases</a> for published assets and release notes. Internet access is needed for LeetCode sync and may be needed to install Microsoft WebView2.</p></section></div></main>`, true);
await mkdir(join(out, 'download'), { recursive: true });
await mkdir(join(out, 'assets'), { recursive: true });
await writeFile(join(out, 'index.html'), home);
await writeFile(join(out, 'download/index.html'), download);
await writeFile(join(out, '404.html'), page('Page not found', '<main id="main" class="wrap download"><h1>Page not found.</h1><p><a href="/">Return to CodeMemory</a></p></main>'));
await writeFile(join(out, 'assets/mark.svg'), mark.replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" '));
await cp(join(root, 'style.css'), join(out, 'style.css'));
for (const weight of ['Regular', 'SemiBold']) await cp(join(root, `node_modules/geist/dist/fonts/geist-sans/Geist-${weight}.woff2`), join(out, `assets/Geist-${weight}.woff2`));
await cp(join(root, 'node_modules/geist/LICENSE.txt'), join(out, 'assets/Geist-LICENSE.txt'));
if (localArtifacts) {
  for (const platform of release.platforms) for (const artifact of platform.artifacts) {
    const file = artifact.file.replaceAll('{version}', release.version);
    await mkdir(join(out, 'releases', `v${release.version}`), { recursive: true });
    await cp(join(localArtifacts, file), join(out, 'releases', `v${release.version}`, file));
  }
}
console.log(`Built / and /download into website/out. Version ${release.version}. Downloads ${available ? 'enabled' : 'await publication'}.`);

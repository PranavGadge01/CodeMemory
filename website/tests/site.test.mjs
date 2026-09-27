import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile, access } from 'node:fs/promises';
import { resolve } from 'node:path';

const ROUTES = [
  'index.html',
  'download/index.html',
  'about/index.html',
  'contact/index.html',
  'privacy/index.html',
  'terms/index.html',
  'changelog/index.html',
  '404.html',
];

// React splits interpolated text with comment markers; strip them so assertions
// can match the rendered copy exactly as a reader sees it.
const read = async (file) => (await readFile(`out/${file}`, 'utf8')).replaceAll('<!-- -->', '');

for (const route of ROUTES) {
  test(`${route} is standalone with valid internal links`, async () => {
    const html = await read(route);
    assert.match(html, /<h1/);
    assert.doesNotMatch(html, /127\.0\.0\.1:8000|localhost:8000|tauri:|testimonial/i);
    for (const [, href] of html.matchAll(/href="(\/[^"]*)"/g)) {
      if (href.startsWith('/_next/')) continue;
      const path = href.split('#')[0];
      if (!path || path === '/') continue;
      await access(resolve('out', '.' + (path.endsWith('/') ? `${path}index.html` : path)));
    }
  });
}

test('homepage keeps the recovered product presentation', async () => {
  const html = await read('index.html');
  for (const section of [
    'Product preview',
    'Your coding history,',
    'remembered',
    'Every attempt is preserved',
    'Solution evolution',
    'See how your thinking moved',
    'Progress you can measure',
    'Your problems, connected',
    'Revision queue',
    'Your code has a history. Make it useful.',
  ]) {
    assert.ok(html.includes(section), `homepage is missing: ${section}`);
  }
});

test('homepage links stay on the public site', async () => {
  const html = await read('index.html');
  for (const desktop of ['href="/connect', 'href="/auth/sign-in', 'href="/dashboard', 'href="/problems', 'href="/revision', 'href="/settings']) {
    assert.ok(!html.includes(desktop), `desktop route leaked into the website: ${desktop}`);
  }
  assert.ok(html.includes('href="/download/'), 'homepage has no download call to action');
});

test('download availability matches release configuration', async () => {
  const release = JSON.parse(await readFile('../release.json', 'utf8'));
  const html = await read('download/index.html');
  assert.ok(html.includes(`Version ${release.version}`));
  assert.ok(html.includes(`CodeMemory for ${release.platforms[0].name}`));
  if (!release.published && !process.env.CODEMEMORY_RELEASE_DIR) {
    assert.match(html, /disabled/);
    assert.ok(
      !html.includes('releases/download/'),
      'an unpublished release must not expose a download URL',
    );
    assert.match(html, /being prepared/);
  }
});

test('public CTAs use product wording and stay on the download page', async () => {
  const html = await read('index.html');
  for (const label of ['Download CodeMemory', 'Get CodeMemory', 'See how it works']) {
    assert.ok(html.includes(label), `homepage is missing CTA: ${label}`);
  }
  for (const stale of [
    'Connect LeetCode',
    'Open CodeMemory',
    'Browse problems',
    'Open queue',
    'Download for Windows',
  ]) {
    assert.ok(!html.includes(stale), `desktop-facing CTA leaked onto the site: ${stale}`);
  }
});

test('supporting pages use platform-neutral download wording', async () => {
  for (const route of ['about/index.html', 'changelog/index.html']) {
    const html = await read(route);
    assert.ok(html.includes('Download CodeMemory'), `${route} is missing the product CTA`);
    assert.ok(!html.includes('Download for Windows'), `${route} still advertises a Windows-only CTA`);
  }
});
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile, access } from 'node:fs/promises';
import { resolve } from 'node:path';

for (const route of ['index.html', 'download/index.html']) test(`${route} is standalone with valid internal links`, async () => {
  const html = await readFile(`out/${route}`, 'utf8');
  assert.match(html, /<h1>/);
  assert.doesNotMatch(html, /127\.0\.0\.1:8000|localhost:8000|tauri:|testimonial/i);
  for (const [, href] of html.matchAll(/href="(\/[^"]*)"/g)) {
    const path = href.split('#')[0];
    const file = path.endsWith('/') ? `${path}index.html` : path;
    await access(resolve('out', '.' + file));
  }
});
test('download availability matches release configuration', async () => {
  const release = JSON.parse(await readFile('../release.json', 'utf8'));
  const html = await readFile('out/download/index.html', 'utf8');
  assert.ok(html.includes(`Version ${release.version}`));
  if (!release.published && !process.env.CODEMEMORY_RELEASE_DIR) assert.match(html, /disabled>Download for Windows/);
});

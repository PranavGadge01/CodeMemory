// release.json is authoritative; --check fails without changing files.
import { readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const { version } = JSON.parse(await readFile(resolve(root, 'release.json'), 'utf8'));
if (!/^\d+\.\d+\.\d+$/.test(version)) throw new Error('Release version must be X.Y.Z');
const check = process.argv.includes('--check');
let changed = false;
for (const file of ['frontend/package.json', 'frontend/package-lock.json', 'frontend/src-tauri/tauri.conf.json', 'website/package.json', 'website/package-lock.json']) {
  const path = resolve(root, file);
  const text = await readFile(path, 'utf8');
  const value = JSON.parse(text);
  if (value.version === version && (!value.packages?.[''] || value.packages[''].version === version)) continue;
  changed = true;
  if (check) { console.error(`Version mismatch: ${file}`); continue; }
  value.version = version;
  if (value.packages?.['']) value.packages[''].version = version;
  await writeFile(path, JSON.stringify(value, null, 2) + '\n');
}
for (const [file, pattern, replacement] of [
  ['pyproject.toml', /^version = "[^"]+"/m, `version = "${version}"`],
  ['src/codememory/__init__.py', /__version__ = "[^"]+"/, `__version__ = "${version}"`],
  ['frontend/src-tauri/Cargo.toml', /^version = "[^"]+"/m, `version = "${version}"`],
  ['frontend/src-tauri/Cargo.lock', /(name = "app"\r?\n)version = "[^"]+"/, `$1version = "${version}"`],
]) {
  const path = resolve(root, file);
  const before = await readFile(path, 'utf8');
  const after = before.replace(pattern, replacement);
  if (before === after) continue;
  changed = true;
  if (check) console.error(`Version mismatch: ${file}`);
  else await writeFile(path, after);
}
if (check && changed) process.exitCode = 1;
else console.log(`Release versions consistent: ${version}`);

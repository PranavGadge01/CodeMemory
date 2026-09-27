import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { resolve, extname, sep } from 'node:path';

const root = resolve(process.argv[2] || 'out');
const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.json': 'application/json', '.png': 'image/png', '.exe': 'application/octet-stream', '.msi': 'application/octet-stream' };
createServer(async (request, response) => {
  try {
    const path = resolve(root, '.' + decodeURIComponent(new URL(request.url, 'http://localhost').pathname));
    if (path !== root && !path.startsWith(root + sep)) throw new Error('Invalid path');
    for (const candidate of [path, path + '.html', resolve(path, 'index.html')]) {
      try {
        if (!(await stat(candidate)).isFile()) continue;
        response.writeHead(200, { 'Content-Type': types[extname(candidate)] || 'application/octet-stream', 'Cache-Control': 'no-store' });
        response.end(await readFile(candidate));
        return;
      } catch { /* Try the static-export variant. */ }
    }
    response.writeHead(404).end('Page not found');
  } catch { response.writeHead(400).end('Invalid request'); }
}).listen(Number(process.argv[3] || 4173), '127.0.0.1', () => console.log(`Static site: http://127.0.0.1:${process.argv[3] || 4173}`));

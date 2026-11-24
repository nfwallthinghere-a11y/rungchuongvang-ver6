'use strict';
/*
 * Local dev server: serves the page and /api/* like Vercel does.
 * Without GAS_URL it starts a fake Apps Script that prints every row it would write.
 * Run: node tests/dev-server.js   -> http://localhost:5173
 */
const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const PORT = Number(process.env.PORT) || 5173;
const rows = [];

function startFakeGas() {
  return new Promise(ok => {
    const s = http.createServer((req, res) => {
      let b = ''; req.on('data', c => { b += c; });
      req.on('end', () => {
        const p = JSON.parse(b || '{}');
        res.setHeader('Content-Type', 'application/json');
        if (p.action === 'ping') return res.end('{"ok":true}');
        (p.rows || []).forEach(r => { rows.push({ sheet: p.sheet, r }); console.log('[sheet ' + p.sheet + ']', JSON.stringify(r)); });
        if (p.image) console.log('[drive] saved', p.image.name, p.image.b64.length, 'b64 chars');
        res.end(JSON.stringify({ ok: true, anh: !!p.image, n: (p.rows || []).length }));
      });
    });
    s.listen(0, () => ok('http://127.0.0.1:' + s.address().port + '/exec'));
  });
}

(async () => {
  if (!process.env.GAS_URL) {
    process.env.GAS_URL = await startFakeGas();
    process.env.GAS_SECRET = 'dev';
    console.log('Fake Apps Script at', process.env.GAS_URL);
  }
  http.createServer(async (req, res) => {
    const u = new URL(req.url, 'http://x');
    if (u.pathname === '/__rows') { res.setHeader('Content-Type', 'application/json'); return res.end(JSON.stringify(rows)); }
    const m = /^\/api\/([a-z]+)$/.exec(u.pathname);
    if (m && fs.existsSync(path.join(ROOT, 'api', m[1] + '.js'))) return require(path.join(ROOT, 'api', m[1] + '.js'))(req, res);
    const file = u.pathname === '/' ? 'rungchuongvang-index4.html' : u.pathname.slice(1);
    const fp = path.join(ROOT, file);
    if (!fp.startsWith(ROOT) || !fs.existsSync(fp) || fs.statSync(fp).isDirectory()) { res.statusCode = 404; return res.end('not found'); }
    res.setHeader('Content-Type', fp.endsWith('.html') ? 'text/html; charset=utf-8' : 'application/octet-stream');
    fs.createReadStream(fp).pipe(res);
  }).listen(PORT, () => console.log('Dev server http://localhost:' + PORT));
})();

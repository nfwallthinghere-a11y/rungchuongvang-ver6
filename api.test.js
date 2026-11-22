'use strict';
/*
 * API tests with a fake Apps Script server. No Google account needed.
 * Run: node tests/api.test.js
 */
const http = require('http');
const assert = require('assert');
const { Readable } = require('stream');

let received = [];
let gasMode = 'ok';
const gas = http.createServer((req, res) => {
  let body = '';
  req.on('data', c => { body += c; });
  req.on('end', () => {
    const p = JSON.parse(body || '{}');
    received.push(p);
    res.setHeader('Content-Type', 'application/json');
    if (gasMode === 'down') { res.statusCode = 500; return res.end('<html>error</html>'); }
    if (p.secret !== 'test-secret') return res.end(JSON.stringify({ ok: false, error: 'unauthorized' }));
    if (p.action === 'ping') return res.end(JSON.stringify({ ok: true }));
    res.end(JSON.stringify({ ok: true, anh: !!p.image, n: (p.rows || []).length }));
  });
});

function mockReq(method, body, headers) {
  const raw = body === undefined ? '' : (typeof body === 'string' ? body : JSON.stringify(body));
  const r = Readable.from(raw ? [Buffer.from(raw)] : []);
  r.method = method;
  r.headers = Object.assign({ 'x-forwarded-for': '1.2.3.' + Math.floor(Math.random() * 250), 'user-agent': 'test' }, headers || {});
  r.socket = { remoteAddress: '127.0.0.1' };
  return r;
}
function call(handler, method, body, headers) {
  return new Promise(resolve => {
    const res = {
      statusCode: 200, headers: {},
      setHeader(k, v) { this.headers[k.toLowerCase()] = v; },
      end(s) { let j = null; try { j = JSON.parse(s || 'null'); } catch (e) {} resolve({ status: this.statusCode, j, headers: this.headers }); },
    };
    handler(mockReq(method, body, headers), res);
  });
}

const tests = [];
const test = (name, fn) => tests.push({ name, fn });
const IMG = 'data:image/jpeg;base64,' + Buffer.from('fakejpeg').toString('base64');

test('health without config reports not configured', async () => {
  delete process.env.GAS_URL;
  const r = await call(require('../api/health'), 'GET');
  assert.strictEqual(r.j.sheets, false);
  assert.strictEqual(r.j.reason, 'chua_cau_hinh');
});

test('buff without config returns 503', async () => {
  delete process.env.GAS_URL;
  const r = await call(require('../api/buff'), 'POST', { phong: 'AB12', bid: 'babc12345', so: 50000 });
  assert.strictEqual(r.status, 503);
});

test('buff valid with image -> one Buff row, image forwarded, dedupe key', async () => {
  received = [];
  const r = await call(require('../api/buff'), 'POST',
    { phong: 'ab12', bid: 'babc12345', ten: 'Lan', so: 50000, nha: 'Minties', lk: 'https://share.timo.vn/VN/transaction/x1', anh: IMG });
  assert.strictEqual(r.status, 200, JSON.stringify(r.j));
  assert.strictEqual(r.j.anh, true);
  const p = received[0];
  assert.strictEqual(p.sheet, 'Buff');
  assert.strictEqual(p.secret, 'test-secret');
  assert.strictEqual(p.dedupeKey, 'buff:AB12:babc12345');
  assert.strictEqual(p.rows[0][1], 'AB12');
  assert.strictEqual(p.rows[0][5], 50000);
  assert.strictEqual(p.rows[0][8], 'Chờ duyệt');
  assert.strictEqual(p.imageCol, 7);
  assert.ok(p.image.b64.length > 0);
});

test('buff rejects bad inputs', async () => {
  const h = require('../api/buff');
  assert.strictEqual((await call(h, 'POST', { phong: 'AB1', bid: 'babc12345', so: 50000 })).status, 400);
  assert.strictEqual((await call(h, 'POST', { phong: 'AB12', bid: 'x', so: 50000 })).status, 400);
  assert.strictEqual((await call(h, 'POST', { phong: 'AB12', bid: 'babc12345', so: -5 })).status, 400);
  assert.strictEqual((await call(h, 'POST', { phong: 'AB12', bid: 'babc12345', so: 50000, lk: 'javascript:alert(1)' })).status, 400);
  assert.strictEqual((await call(h, 'POST', { phong: 'AB12', bid: 'babc12345', so: 50000, anh: 'data:text/html;base64,AAAA' })).status, 400);
  assert.strictEqual((await call(h, 'POST', '{not json')).status, 400);
  assert.strictEqual((await call(h, 'GET')).status, 405);
});

test('buff blocks formula injection in names', async () => {
  received = [];
  await call(require('../api/buff'), 'POST', { phong: 'AB12', bid: 'bformula1', ten: '=HYPERLINK("x")', so: 20000 });
  assert.ok(received[0].rows[0][3].startsWith("'="));
});

test('buff rate limit per IP', async () => {
  const h = require('../api/buff');
  let last;
  for (let i = 0; i < 10; i++) last = await call(h, 'POST', { phong: 'AB12', bid: 'brate' + i + 'xx', so: 20000 }, { 'x-forwarded-for': '9.9.9.9' });
  assert.strictEqual(last.status, 429);
});

test('log duyet/dudoan/hoaluc/ketqua map to the right tabs', async () => {
  const h = require('../api/log');
  const cases = [
    ['duyet', { bid: 'babc12345', ketQua: 'Duyệt', ten: 'Lan', nha: 'Minties', so: 50000, tongNha: 150000, luc: Date.now() }, 'Duyet', 9],
    ['dudoan', { vong: 1, kgId: 'dabc123456', ten: 'Lan', nha: 'Minties', luc: Date.now() }, 'DuDoan', 8],
    ['hoaluc', { nha: 'Minties', cong: 40, tong: 820 }, 'HoaLuc', 6],
    ['ketqua', { vong: 1, nha: 'Minties', soDuDoan: 120, soDung: 33 }, 'KetQua', 7],
  ];
  for (const [loai, row, sheet, width] of cases) {
    received = [];
    const r = await call(h, 'POST', { phong: 'AB12', loai, rows: [row] });
    assert.strictEqual(r.status, 200, loai + ' ' + JSON.stringify(r.j));
    assert.strictEqual(received[0].sheet, sheet);
    assert.strictEqual(received[0].rows[0].length, width);
    assert.strictEqual(received[0].rows[0][received[0].rows[0].length - 1] === 'Không' || sheet === 'Buff', true);
  }
});

test('log admin key marks rows verified', async () => {
  process.env.ADMIN_KEY = 'k-123';
  received = [];
  await call(require('../api/log'), 'POST', { phong: 'AB12', loai: 'hoaluc', rows: [{ nha: 'A', cong: 1, tong: 1 }] }, { 'x-rcv-key': 'k-123' });
  assert.strictEqual(received[0].rows[0][5], 'Có');
  received = [];
  await call(require('../api/log'), 'POST', { phong: 'AB12', loai: 'hoaluc', rows: [{ nha: 'A', cong: 1, tong: 1 }] }, { 'x-rcv-key': 'wrong' });
  assert.strictEqual(received[0].rows[0][5], 'Không');
  delete process.env.ADMIN_KEY;
});

test('log drops invalid rows and rejects bad batches', async () => {
  const h = require('../api/log');
  received = [];
  const r = await call(h, 'POST', { phong: 'AB12', loai: 'duyet', rows: [{ bid: 'b1', ketQua: 'Hack' }, { bid: 'babc', ketQua: 'Từ chối', so: 1 }] });
  assert.strictEqual(r.j.n, 1); assert.strictEqual(r.j.skipped, 1);
  assert.strictEqual((await call(h, 'POST', { phong: 'AB12', loai: 'xoa', rows: [{}] })).status, 400);
  assert.strictEqual((await call(h, 'POST', { phong: 'AB12', loai: 'hoaluc', rows: new Array(301).fill({ nha: 'A', cong: 1, tong: 1 }) })).status, 413);
});

test('Apps Script down -> 502, wrong secret -> error', async () => {
  gasMode = 'down';
  const r1 = await call(require('../api/log'), 'POST', { phong: 'AB12', loai: 'hoaluc', rows: [{ nha: 'A', cong: 1, tong: 1 }] });
  assert.strictEqual(r1.status, 502);
  gasMode = 'ok';
  process.env.GAS_SECRET = 'nope';
  const r2 = await call(require('../api/log'), 'POST', { phong: 'AB12', loai: 'hoaluc', rows: [{ nha: 'A', cong: 1, tong: 1 }] });
  assert.strictEqual(r2.status, 502); assert.strictEqual(r2.j.error, 'unauthorized');
  process.env.GAS_SECRET = 'test-secret';
});

(async () => {
  await new Promise(ok => gas.listen(0, ok));
  const url = 'http://127.0.0.1:' + gas.address().port + '/exec';
  process.env.GAS_SECRET = 'test-secret';
  let pass = 0, fail = 0;
  for (const t of tests) {
    if (!/without config/.test(t.name)) process.env.GAS_URL = url;
    try { await t.fn(); pass++; console.log('  ✓ ' + t.name); }
    catch (e) { fail++; console.log('  ✗ ' + t.name + '\n    ' + (e && e.message)); }
  }
  gas.close();
  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();

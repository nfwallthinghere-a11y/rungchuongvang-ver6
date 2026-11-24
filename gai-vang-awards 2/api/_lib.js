'use strict';
/*
 * Shared helpers for the Vercel serverless API.
 * Files starting with "_" inside /api are not exposed as routes.
 *
 * Env vars (set in Vercel > Project > Settings > Environment Variables):
 *   GAS_URL     Google Apps Script web-app URL (…/exec)            [required for logging]
 *   GAS_SECRET  Shared secret, must equal the SECRET script property [required for logging]
 *   ADMIN_KEY   Optional. When the MC enters the same key, MC log rows are marked verified.
 *   IP_SALT     Optional. Salt for hashing client IPs in the sheet.
 */
const crypto = require('crypto');

/* Sheet layouts. The Apps Script creates a tab with this header the first time. */
const SHEETS = {
  Buff:    ['Thời gian', 'Phòng', 'Mã GD', 'Người gửi', 'Nhà', 'Số tiền', 'Link biên lai',
            'Ảnh chuyển khoản', 'Trạng thái', 'IP (băm)', 'Trình duyệt'],
  Duyet:   ['Thời gian', 'Phòng', 'Mã GD', 'Kết quả', 'Người gửi', 'Nhà', 'Số tiền',
            'Tổng quỹ nhà sau duyệt', 'Xác thực MC'],
  DuDoan:  ['Thời gian', 'Phòng', 'Vòng', 'Mã khán giả', 'Tên', 'Nhà dự đoán', 'Lúc chọn', 'Xác thực MC'],
  HoaLuc:  ['Thời gian', 'Phòng', 'Nhà', 'Điểm cộng thêm', 'Tổng hỏa lực', 'Xác thực MC'],
  KetQua:  ['Thời gian', 'Phòng', 'Vòng', 'Nhà vô địch', 'Số lượt dự đoán', 'Số đoán đúng', 'Xác thực MC'],
};

/* ---------- best-effort rate limit (per warm instance) ---------- */
const buckets = new Map();
function rateLimit(key, max, windowMs) {
  const now = Date.now();
  let b = buckets.get(key);
  if (!b || now - b.start > windowMs) { b = { start: now, n: 0 }; buckets.set(key, b); }
  b.n++;
  if (buckets.size > 5000) {                       // keep memory bounded
    for (const [k, v] of buckets) if (now - v.start > windowMs) buckets.delete(k);
  }
  return b.n <= max;
}

function clientIp(req) {
  const xf = String(req.headers['x-forwarded-for'] || '').split(',')[0].trim();
  return xf || String(req.headers['x-real-ip'] || '') || (req.socket && req.socket.remoteAddress) || 'unknown';
}

function ipHash(ip) {
  return crypto.createHash('sha256').update((process.env.IP_SALT || 'rcv') + '|' + ip).digest('hex').slice(0, 12);
}

/* Plain text for a sheet cell: no control chars, bounded length, and no formula
   injection (a cell starting with = + - @ would run as a formula in Sheets). */
function cell(v, max) {
  let s = String(v == null ? '' : v).replace(/[\u0000-\u001f\u007f]/g, ' ').trim().slice(0, max || 200);
  if (/^[=+\-@\t]/.test(s)) s = "'" + s;
  return s;
}

function int(v, min, max) {
  const n = Math.round(Number(v));
  if (!Number.isFinite(n) || n < min || n > max) return null;
  return n;
}

const ROOM_RE = /^[0-9A-Z]{4}$/;

/* Vietnam local time as text, e.g. 2026-11-21 14:03:22 */
function nowVN() {
  const d = new Date(Date.now() + 7 * 3600 * 1000);
  return d.toISOString().replace('T', ' ').slice(0, 19);
}

function timeVN(ms) {
  const n = Number(ms);
  if (!Number.isFinite(n) || n <= 0) return '';
  return new Date(n + 7 * 3600 * 1000).toISOString().replace('T', ' ').slice(0, 19);
}

function isAdmin(req) {
  const key = process.env.ADMIN_KEY;
  const got = String(req.headers['x-rcv-key'] || '');
  if (!key || !got || got.length !== key.length) return false;
  return crypto.timingSafeEqual(Buffer.from(got), Buffer.from(key));
}

function cors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, x-rcv-key');
  res.setHeader('Cache-Control', 'no-store');
}

function send(res, status, obj) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.end(JSON.stringify(obj));
}

/* Read a JSON body whether or not the runtime already parsed it. */
async function readJson(req, maxBytes) {
  if (req.body && typeof req.body === 'object') return req.body;
  if (typeof req.body === 'string') return JSON.parse(req.body);
  const chunks = []; let size = 0;
  for await (const c of req) {
    size += c.length;
    if (size > maxBytes) throw Object.assign(new Error('too_large'), { status: 413 });
    chunks.push(c);
  }
  return JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}');
}

/* Forward to the Apps Script web app. Apps Script answers POST with a 302 to
   googleusercontent.com; fetch follows it with a GET, which is what it expects. */
async function callGas(payload, timeoutMs) {
  const url = process.env.GAS_URL, secret = process.env.GAS_SECRET;
  if (!url || !secret) return { ok: false, error: 'chua_cau_hinh', status: 503 };
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), timeoutMs || 25000);
  try {
    const r = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain;charset=utf-8' },
      body: JSON.stringify(Object.assign({}, payload, { secret })),
      redirect: 'follow',
      signal: ctl.signal,
    });
    const text = await r.text();
    let j = null; try { j = JSON.parse(text); } catch (e) { /* HTML error page */ }
    if (!j) return { ok: false, error: 'gas_bad_response', status: 502 };
    return j.ok ? Object.assign({ status: 200 }, j) : Object.assign({ status: 502 }, j);
  } catch (e) {
    return { ok: false, error: e.name === 'AbortError' ? 'gas_timeout' : 'gas_unreachable', status: 504 };
  } finally {
    clearTimeout(t);
  }
}

module.exports = { SHEETS, rateLimit, clientIp, ipHash, cell, int, ROOM_RE, nowVN, timeVN,
                   isAdmin, cors, send, readJson, callGas };

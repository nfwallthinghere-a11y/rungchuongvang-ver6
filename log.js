'use strict';
/*
 * POST /api/log — batched event log from the MC desk (the single writer of game state).
 * Body: { phong, loai, rows: [ {...}, ... ] }   (max 300 rows per call)
 *   loai = duyet | dudoan | hoaluc | ketqua
 * Header x-rcv-key (optional): equals ADMIN_KEY -> rows marked "Có" in "Xác thực MC".
 */
const L = require('./_lib');

const MAX_ROWS = 300;

/* map one client object to a sheet row; return null to skip an invalid row */
const MAP = {
  duyet: { sheet: 'Duyet', row: (r, ph, xt) => {
    const kq = r.ketQua === 'Duyệt' ? 'Duyệt' : r.ketQua === 'Từ chối' ? 'Từ chối' : null;
    if (!kq || !/^[A-Za-z0-9_-]{1,48}$/.test(String(r.bid || ''))) return null;
    return [L.timeVN(r.luc) || L.nowVN(), ph, String(r.bid), kq, L.cell(r.ten, 40), L.cell(r.nha, 40),
            L.int(r.so, -1000000000, 1000000000) || 0, L.int(r.tongNha, 0, 100000000000) || 0, xt];
  } },
  dudoan: { sheet: 'DuDoan', row: (r, ph, xt) => {
    const v = L.int(r.vong, 1, 1000);
    if (v === null || !r.nha) return null;
    return [L.nowVN(), ph, v, L.cell(r.kgId, 40), L.cell(r.ten, 40), L.cell(r.nha, 40), L.timeVN(r.luc), xt];
  } },
  hoaluc: { sheet: 'HoaLuc', row: (r, ph, xt) => {
    const cong = L.int(r.cong, 1, 10000000), tong = L.int(r.tong, 0, 1000000000);
    if (cong === null || tong === null || !r.nha) return null;
    return [L.nowVN(), ph, L.cell(r.nha, 40), cong, tong, xt];
  } },
  ketqua: { sheet: 'KetQua', row: (r, ph, xt) => {
    const v = L.int(r.vong, 1, 1000);
    if (v === null || !r.nha) return null;
    return [L.nowVN(), ph, v, L.cell(r.nha, 40), L.int(r.soDuDoan, 0, 10000000) || 0,
            L.int(r.soDung, 0, 10000000) || 0, xt];
  } },
};

module.exports = async (req, res) => {
  L.cors(res);
  if (req.method === 'OPTIONS') { res.statusCode = 204; return res.end(); }
  if (req.method !== 'POST') return L.send(res, 405, { ok: false, error: 'method' });

  const ip = L.clientIp(req);
  if (!L.rateLimit('log:' + ip, 60, 60000)) return L.send(res, 429, { ok: false, error: 'rate_limited' });

  let b;
  try { b = await L.readJson(req, 512 * 1024); }
  catch (e) { return L.send(res, e.status || 400, { ok: false, error: 'bad_json' }); }

  const phong = String(b.phong || '').toUpperCase();
  const m = MAP[b.loai];
  if (!L.ROOM_RE.test(phong)) return L.send(res, 400, { ok: false, error: 'phong' });
  if (!m) return L.send(res, 400, { ok: false, error: 'loai' });
  if (!Array.isArray(b.rows) || !b.rows.length) return L.send(res, 400, { ok: false, error: 'rows' });
  if (b.rows.length > MAX_ROWS) return L.send(res, 413, { ok: false, error: 'too_many_rows' });

  const xt = L.isAdmin(req) ? 'Có' : 'Không';
  const rows = b.rows.map(r => (r && typeof r === 'object') ? m.row(r, phong, xt) : null).filter(Boolean);
  if (!rows.length) return L.send(res, 400, { ok: false, error: 'no_valid_rows' });

  const r = await L.callGas({ action: 'append', sheet: m.sheet, header: L.SHEETS[m.sheet], rows }, 25000);
  if (!r.ok) return L.send(res, r.status || 502, { ok: false, error: r.error || 'gas_error' });
  return L.send(res, 200, { ok: true, n: rows.length, skipped: b.rows.length - rows.length });
};

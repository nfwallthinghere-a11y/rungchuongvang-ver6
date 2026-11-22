'use strict';
/*
 * POST /api/buff — an audience member reports a transfer (order info + optional screenshot).
 * Writes one row to the "Buff" tab and stores the screenshot in a private Drive folder.
 *
 * Body: { phong, bid, ten, so, nha, lk?, anh? }
 *   phong  4-char audience room code
 *   bid    client transaction id (same id the MC/moderation page sees) — used for idempotency
 *   so     amount in VND
 *   anh    optional "data:image/jpeg;base64,…" (client already compresses to ~190 KB)
 */
const L = require('./_lib');

const MAX_BODY = 1.5 * 1024 * 1024;
const MAX_IMG_B64 = 900 * 1024;

module.exports = async (req, res) => {
  L.cors(res);
  if (req.method === 'OPTIONS') { res.statusCode = 204; return res.end(); }
  if (req.method !== 'POST') return L.send(res, 405, { ok: false, error: 'method' });

  const ip = L.clientIp(req);
  if (!L.rateLimit('buff:' + ip, 8, 60000)) return L.send(res, 429, { ok: false, error: 'rate_limited' });

  let b;
  try { b = await L.readJson(req, MAX_BODY); }
  catch (e) { return L.send(res, e.status || 400, { ok: false, error: e.status === 413 ? 'too_large' : 'bad_json' }); }

  const phong = String(b.phong || '').toUpperCase();
  const bid = String(b.bid || '');
  const so = L.int(b.so, 1000, 1000000000);
  if (!L.ROOM_RE.test(phong)) return L.send(res, 400, { ok: false, error: 'phong' });
  if (!/^b[a-z0-9]{6,40}$/.test(bid)) return L.send(res, 400, { ok: false, error: 'bid' });
  if (so === null) return L.send(res, 400, { ok: false, error: 'so' });

  let lk = '';
  if (b.lk) {
    try {
      const u = new URL(String(b.lk).slice(0, 400));
      if (u.protocol !== 'https:' && u.protocol !== 'http:') throw new Error('proto');
      lk = u.href.slice(0, 300);
    } catch (e) { return L.send(res, 400, { ok: false, error: 'lk' }); }
  }

  let image = null;
  if (b.anh) {
    const m = /^data:image\/(jpeg|png|webp);base64,([A-Za-z0-9+/=]+)$/.exec(String(b.anh));
    if (!m) return L.send(res, 400, { ok: false, error: 'anh' });
    if (m[2].length > MAX_IMG_B64) return L.send(res, 413, { ok: false, error: 'anh_too_large' });
    image = { b64: m[2], mime: 'image/' + m[1], name: phong + '_' + bid + '.' + (m[1] === 'jpeg' ? 'jpg' : m[1]) };
  }

  const row = [
    L.nowVN(), phong, bid, L.cell(b.ten, 40) || 'Khán giả', L.cell(b.nha, 40), so, L.cell(lk, 300),
    '', 'Chờ duyệt', L.ipHash(ip), L.cell(req.headers['user-agent'], 160),
  ];

  const r = await L.callGas({
    action: 'append', sheet: 'Buff', header: L.SHEETS.Buff, rows: [row],
    dedupeKey: 'buff:' + phong + ':' + bid,
    image, imageCol: L.SHEETS.Buff.indexOf('Ảnh chuyển khoản'),
  }, 28000);

  if (!r.ok) return L.send(res, r.status || 502, { ok: false, error: r.error || 'gas_error' });
  return L.send(res, 200, { ok: true, dup: !!r.dup, anh: !!r.anh });
};

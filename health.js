'use strict';
/* GET /api/health — is the Google Sheets log wired up? Pings the Apps Script. */
const L = require('./_lib');

module.exports = async (req, res) => {
  L.cors(res);
  if (!L.rateLimit('health:' + L.clientIp(req), 10, 60000)) return L.send(res, 429, { ok: false, error: 'rate_limited' });
  const configured = !!(process.env.GAS_URL && process.env.GAS_SECRET);
  if (!configured) return L.send(res, 200, { ok: true, sheets: false, reason: 'chua_cau_hinh' });
  const r = await L.callGas({ action: 'ping' }, 15000);
  return L.send(res, 200, { ok: true, sheets: !!r.ok, reason: r.ok ? null : (r.error || 'gas_error'),
                            adminKey: !!process.env.ADMIN_KEY });
};

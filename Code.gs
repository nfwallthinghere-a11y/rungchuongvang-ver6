/**
 * Rung Chuông Vàng — Google Sheets logger (Google Apps Script web app).
 *
 * Setup (once):
 *  1. Create a Google Sheet. Extensions > Apps Script. Replace Code.gs with this file.
 *  2. Project Settings > Script properties: add SECRET = <a long random string>.
 *     Optional: FOLDER_ID = Drive folder id for transfer screenshots
 *     (if missing, a private folder "RCV - Ảnh chuyển khoản" is created on first upload).
 *  3. Deploy > New deployment > Web app. Execute as: Me. Who has access: Anyone.
 *     Copy the /exec URL.
 *  4. In Vercel: GAS_URL = that URL, GAS_SECRET = the same SECRET. Redeploy.
 *
 * Screenshots stay PRIVATE in your Drive (not shared). The sheet stores the file link,
 * which opens only for accounts that have access to the folder.
 */

function doPost(e) {
  try {
    var p = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    var props = PropertiesService.getScriptProperties();
    var secret = props.getProperty('SECRET');
    if (!secret || p.secret !== secret) return out_({ ok: false, error: 'unauthorized' });

    if (p.action === 'ping') return out_({ ok: true });
    if (p.action !== 'append') return out_({ ok: false, error: 'bad_action' });
    if (!/^[A-Za-z]{2,20}$/.test(String(p.sheet || ''))) return out_({ ok: false, error: 'bad_sheet' });
    if (!Array.isArray(p.header) || !Array.isArray(p.rows) || !p.rows.length) return out_({ ok: false, error: 'bad_rows' });

    var cache = CacheService.getScriptCache();
    if (p.dedupeKey) {
      if (cache.get(p.dedupeKey)) return out_({ ok: true, dup: true });
    }

    var width = p.header.length;
    var rows = p.rows.map(function (r) {
      var a = (r || []).slice(0, width);
      while (a.length < width) a.push('');
      return a;
    });

    /* screenshot -> private Drive file, link goes into the row */
    var anh = false;
    if (p.image && p.image.b64 && typeof p.imageCol === 'number') {
      var blob = Utilities.newBlob(Utilities.base64Decode(p.image.b64), p.image.mime || 'image/jpeg',
                                   String(p.image.name || 'anh.jpg').replace(/[^A-Za-z0-9_.-]/g, '_'));
      var file = folder_(props).createFile(blob);
      rows[0][p.imageCol] = file.getUrl();
      anh = true;
    }

    var lock = LockService.getScriptLock();
    lock.waitLock(25000);
    try {
      var sh = sheet_(p.sheet, p.header);
      sh.getRange(sh.getLastRow() + 1, 1, rows.length, width).setValues(rows);
      if (p.sheet === 'Duyet') markBuff_(rows);
    } finally {
      lock.releaseLock();
    }

    if (p.dedupeKey) cache.put(p.dedupeKey, '1', 21600);   // 6 h
    return out_({ ok: true, anh: anh, n: rows.length });
  } catch (err) {
    return out_({ ok: false, error: String(err && err.message || err).slice(0, 200) });
  }
}

function doGet() {
  return out_({ ok: true, service: 'rcv-logger' });
}

function out_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}

function sheet_(name, header) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(name);
  if (!sh) {
    sh = ss.insertSheet(name);
    sh.getRange(1, 1, 1, header.length).setValues([header]).setFontWeight('bold');
    sh.setFrozenRows(1);
  }
  return sh;
}

function folder_(props) {
  var id = props.getProperty('FOLDER_ID');
  if (id) { try { return DriveApp.getFolderById(id); } catch (e) { /* recreate below */ } }
  var f = DriveApp.createFolder('RCV - Ảnh chuyển khoản');
  props.setProperty('FOLDER_ID', f.getId());
  return f;
}

/* When the MC approves/rejects, update the "Trạng thái" cell of the matching Buff row. */
function markBuff_(rows) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName('Buff');
  if (!sh || sh.getLastRow() < 2) return;
  var head = sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0];
  var cBid = head.indexOf('Mã GD') + 1, cSt = head.indexOf('Trạng thái') + 1;
  if (cBid < 1 || cSt < 1) return;
  rows.forEach(function (r) {
    var bid = String(r[2] || ''), kq = String(r[3] || '');
    if (!bid) return;
    var hit = sh.getRange(2, cBid, sh.getLastRow() - 1, 1).createTextFinder(bid).matchEntireCell(true).findNext();
    if (hit) sh.getRange(hit.getRow(), cSt).setValue(kq + ' · ' + r[0]);
  });
}

/* Run once from the editor to create the Drive folder and grant permissions. */
function setup() {
  folder_(PropertiesService.getScriptProperties());
  sheet_('Buff', ['Thời gian', 'Phòng', 'Mã GD', 'Người gửi', 'Nhà', 'Số tiền', 'Link biên lai',
                  'Ảnh chuyển khoản', 'Trạng thái', 'IP (băm)', 'Trình duyệt']);
}

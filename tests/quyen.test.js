'use strict';
/* Rút đúng các hàm tính quyền từ trang ra rồi chạy thử — không cần trình duyệt. */
const fs = require('fs'), vm = require('vm');
const src = fs.readFileSync(require('path').join(__dirname,'..','rungchuongvang-index4.html'), 'utf8');
const js = (src.match(/<script[^>]*>([\s\S]*?)<\/script>/g) || []).map(x => x.replace(/<\/?script[^>]*>/g, '')).join('\n');
const can = ['const TRO = [', 'const MOC_DON_MAC_DINH', 'const MOC_TONG_MAC_DINH', 'const CAP_MOI_DON',
             'const CAP_THEO_TONG', 'const mucDon', 'const mucTong', 'const troTheoMa', 'const tienVN',
             'function soQuyen', 'function daMo', 'function daDung', 'function conDung',
             'function capQuyen', 'function mocKeTiep'];
/* lấy nguyên các khối cần thiết theo thứ tự xuất hiện */
let lay = '';
for (const k of can) {
  const i = js.indexOf(k);
  if (i < 0) { console.error('KHÔNG TÌM THẤY: ' + k); process.exit(1); }
  let j = i, sau = js.indexOf('\n', i);
  if (k.startsWith('function')) {
    let d = 0, bat = false;
    for (j = i; j < js.length; j++) { if (js[j] === '{') { d++; bat = true; } else if (js[j] === '}') { d--; if (bat && d === 0) { j++; break; } } }
  } else if (k.endsWith('[')) {
    j = js.indexOf('];', i) + 2;
  } else { j = sau; }
  lay += js.slice(i, j) + '\n';
}
const ctx = { CO_HOA_LUC: false, MOC_MAC_DINH: [1, 2, 3, 4], mocLuaI: () => 1e9, mocTien: () => 1e9, console };
vm.createContext(ctx);
vm.runInContext(lay, ctx);

let pass = 0, fail = 0;
const ok = (ten, dk, phu) => { if (dk) { pass++; console.log('  ✓ ' + ten); } else { fail++; console.log('  ✗ ' + ten + (phu !== undefined ? '   << ' + JSON.stringify(phu) : '')); } };
const nha = () => ({ ten: 'X', tien: 0, quyen: {}, tienChuKy: 0, mocDaCap: 0 });
const q = (d, m) => ctx.soQuyen(d, m);
const cap = (d, so) => ctx.capQuyen(d, so, null, null);   // dùng mốc mặc định 20k/30k · 150k/200k

console.log('MỖI ĐƠN DONATE');
let d = nha();
cap(d, 19000);
ok('19k: không được quyền nào', q(d,'chiadoi')===0 && q(d,'x2')===0, d.quyen);
d = nha(); cap(d, 20000);
ok('đúng 20k: được 1 quyền 50/50, chưa có nhân đôi', q(d,'chiadoi')===1 && q(d,'x2')===0, d.quyen);
d = nha(); cap(d, 29000);
ok('29k: chỉ 50/50', q(d,'chiadoi')===1 && q(d,'x2')===0, d.quyen);
d = nha(); cap(d, 30000);
ok('đúng 30k: được CẢ 50/50 lẫn nhân đôi', q(d,'chiadoi')===1 && q(d,'x2')===1, d.quyen);
d = nha(); cap(d, 50000);
ok('50k: được cả hai', q(d,'chiadoi')===1 && q(d,'x2')===1, d.quyen);
d = nha(); cap(d, 20000); cap(d, 20000); cap(d, 35000);
ok('nhiều đơn: quyền cộng dồn không giới hạn (50/50 ×3, nhân đôi ×1)',
   q(d,'chiadoi')===3 && q(d,'x2')===1, d.quyen);

console.log('\nMỐC THEO TỔNG (150k / 200k, đạt hết thì chạy lại)');
d = nha();
cap(d, 100000);
ok('tổng 100k: chưa có cướp quyền', q(d,'cuopquyen')===0, d);
cap(d, 50000);
ok('tổng 150k: được cướp quyền', q(d,'cuopquyen')===1, d.quyen);
ok('tổng 150k: chưa có người thân', q(d,'hoisinh')===0, d.quyen);
cap(d, 50000);
ok('tổng 200k: được người thân', q(d,'hoisinh')===1, d.quyen);
ok('đạt hết mốc -> tiến độ chu kỳ chạy lại từ 0', d.tienChuKy===0 && d.mocDaCap===0, d);
cap(d, 150000);
ok('chu kỳ mới: thêm 150k được cướp quyền lần 2', q(d,'cuopquyen')===2, d.quyen);

console.log('\nĐƠN LỚN MỘT LẦN');
d = nha(); cap(d, 500000);
ok('500k một lần: 50/50 ×1, nhân đôi ×1', q(d,'chiadoi')===1 && q(d,'x2')===1, d.quyen);
ok('500k một lần: cướp quyền ×2, người thân ×2', q(d,'cuopquyen')===2 && q(d,'hoisinh')===2, d.quyen);
ok('500k một lần: còn dư 100k tiến độ', d.tienChuKy===100000, d.tienChuKy);
d = nha(); cap(d, 2000000);
ok('2 triệu một lần: không treo, cấp 10 lần mỗi mốc tổng',
   q(d,'cuopquyen')===10 && q(d,'hoisinh')===10, d.quyen);

console.log('\nĐƠN ÂM (quản trò sửa sai)');
d = nha(); cap(d, 200000);
const giuCuop = q(d,'cuopquyen'), giuHs = q(d,'hoisinh');
cap(d, -50000);
ok('đơn âm: không cấp thêm quyền nào', q(d,'chiadoi')===1 && q(d,'x2')===1, d.quyen);
ok('đơn âm: không thu lại quyền đã cấp', q(d,'cuopquyen')===giuCuop && q(d,'hoisinh')===giuHs, d.quyen);
ok('đơn âm: tiến độ chu kỳ không âm', d.tienChuKy>=0, d.tienChuKy);

console.log('\nTHANH TIẾN ĐỘ');
d = nha(); cap(d, 60000);
let ke = ctx.mocKeTiep(d, null);
ok('mới 60k: mốc kế là cướp quyền, còn 90k', ke.ma==='cuopquyen' && ke.thieu===90000, ke);
cap(d, 90000);
ke = ctx.mocKeTiep(d, null);
ok('đủ 150k: mốc kế là người thân, còn 50k', ke.ma==='hoisinh' && ke.thieu===50000, ke);
cap(d, 50000);
ke = ctx.mocKeTiep(d, null);
ok('đạt hết: quay về mốc cướp quyền, còn đủ 150k', ke.ma==='cuopquyen' && ke.thieu===150000, ke);

console.log('\nCÁC HÀM CŨ VẪN HIỂU ĐÚNG');
d = nha(); cap(d, 30000);
ok('daMo = có ít nhất 1 quyền', ctx.daMo(d,0)===true && ctx.daMo(d,3)===false);
ok('daDung = hết quyền', ctx.daDung(d,'chiadoi')===false && ctx.daDung(d,'cuopquyen')===true);
ok('conDung = còn dùng được', ctx.conDung(d,0,null,'chiadoi')===true && ctx.conDung(d,3,null,'cuopquyen')===false);

console.log('\n' + pass + ' đạt, ' + fail + ' lỗi');
process.exit(fail ? 1 : 0);

# Rung Chuông Vàng

Game hỏi đáp nhiều đội, một file `rungchuongvang-index4.html`, đồng bộ realtime qua MQTT công cộng.
Backend nhỏ trên Vercel (`/api`) ghi log realtime ra **Google Sheets** qua một Google Apps Script.

## Tính năng mới

| Tính năng | Ai dùng | Ghi log vào tab |
|---|---|---|
| Lưu giao dịch buff: thông tin đơn + ảnh chuyển khoản (ảnh lưu Drive riêng) | Khán giả gửi | `Buff` |
| Kết quả kiểm duyệt (Duyệt / Từ chối, tổng quỹ nhà sau duyệt), tự cập nhật cột Trạng thái ở `Buff` | Bàn MC (nhận lệnh từ trang Duyệt) | `Duyet` |
| **Góp lửa** — *đang TẮT* (`CO_HOA_LUC = false`): ẩn thanh emoji, quyền trợ giúp chỉ mở theo donate. Đổi thành `true` để bật lại: mỗi lần chạm emoji = +1 hỏa lực, mở quyền theo mốc donate HOẶC mốc hỏa lực | Khán giả | `HoaLuc` (gộp mỗi 30 giây) |
| Màn khán giả: hàng dưới = Chat · **BXH BUFF LUCK** (xếp nhà theo tiền đã duyệt) · **BUFF LUCK** (chọn nhà + QR, bấm QR để phóng to) | Khán giả | — |
| **Dự đoán nhà vô địch**: MC mở → popup cho mọi khán giả; Mở chuông lần đầu tự khoá; MC công bố → ai đoán đúng thấy pháo hoa | Khán giả + MC | `DuDoan`, `KetQua` |

## Cấu trúc

```
rungchuongvang-index4.html   app (MC / đội / khán giả / trang duyệt)
api/_lib.js                  helper chung: validate, rate limit, chống formula injection, gọi Apps Script
api/buff.js                  POST /api/buff  — khán giả gửi đơn + ảnh
api/log.js                   POST /api/log   — MC gửi log theo lô (duyet | dudoan | hoaluc | ketqua)
api/health.js                GET  /api/health — kiểm tra đã nối Google Sheets chưa
gas/Code.gs                  Google Apps Script (dán vào Sheet)
tests/api.test.js            test API với Apps Script giả
tests/dev-server.js          chạy local như Vercel
vercel.json                  "/" -> file game
```

## Biến môi trường (Vercel > Settings > Environment Variables)

| Biến | Bắt buộc | Ý nghĩa |
|---|---|---|
| `GAS_URL` | có | URL `/exec` của Apps Script web app |
| `GAS_SECRET` | có | Trùng script property `SECRET` trong Apps Script |
| `ADMIN_KEY` | không | MC nhập cùng khoá ở mục Thiết lập → log đánh dấu "Xác thực MC" |
| `IP_SALT` | không | Muối để băm IP trong sheet |

Thiếu `GAS_URL`/`GAS_SECRET`: game vẫn chạy bình thường, API trả 503, log được giữ trên máy MC và tự gửi khi nối xong.

## Cài Google Sheets (một lần)

1. Tạo Google Sheet mới → **Tiện ích mở rộng › Apps Script** → dán `gas/Code.gs`.
2. **Cài đặt dự án › Thuộc tính tập lệnh**: thêm `SECRET` = chuỗi ngẫu nhiên dài.
3. **Triển khai › Bản triển khai mới › Ứng dụng web**: Thực thi với tư cách *Tôi*, Ai có quyền truy cập *Bất kỳ ai*. Cấp quyền khi Google hỏi. Chép URL `/exec`.
4. Vercel: đặt `GAS_URL`, `GAS_SECRET` → Redeploy. Mở `/api/health` phải thấy `"sheets":true`.

Ảnh chuyển khoản lưu ở thư mục Drive riêng tư "RCV - Ảnh chuyển khoản" của tài khoản cài script.

## Chạy local & test

```
node tests/api.test.js        # 10 test API
node tests/dev-server.js      # http://localhost:5173, in ra các dòng sẽ ghi vào sheet
```

## Luồng dữ liệu

- Khán giả → `/api/buff` (HTTPS) → Apps Script → tab `Buff` + ảnh vào Drive. Song song vẫn gửi qua MQTT cho bàn MC / trang duyệt như cũ.
- Cảm xúc khán giả mang theo `n` (id nhà) → **chỉ bàn MC cộng hỏa lực** (giới hạn 12 điểm/giây/máy), phát state tối đa 2 giây/lần.
- Dự đoán: mỗi khán giả giữ 1 tin retained `rcvang/<phòng>/dd/<id>` → chỉ bàn MC nghe → MC tải lại trang vẫn đủ.
- Bàn MC gom log, gửi `/api/log` theo lô 200 dòng mỗi 4 giây, lỗi thì thử lại, lưu hàng đợi vào localStorage.

## Rủi ro đã biết

- Broker MQTT công cộng: không cam kết capacity; ai có mã khán giả có thể gửi tin giả (hỏa lực giả với sid mới, dự đoán giả). Giới hạn hiện có chỉ chặn spam thông thường.
- `/api/buff` và `/api/log` công khai: có validate + rate limit theo IP (best effort, mỗi instance). Dùng `ADMIN_KEY` để phân biệt log thật của MC.
- Apps Script tài khoản thường: tối đa ~30 lượt chạy đồng thời. Log MC đã gom lô; buff gửi lẻ nhưng tần suất thấp.
- Hỏa lực và dự đoán lưu ở máy MC (localStorage). Đổi máy MC giữa trận sẽ mất phần chưa ghi Sheets.

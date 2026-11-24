# Rung Chuông Vàng

Game hỏi đáp nhiều đội, một file `rungchuongvang-index4.html`, đồng bộ realtime qua MQTT công cộng.
Backend nhỏ trên Vercel (`/api`) ghi log realtime ra **Google Sheets** qua một Google Apps Script.

## Deploy lên Vercel

1. Đẩy nguyên thư mục này lên một repo Git (hoặc kéo thả vào Vercel).
2. Vercel tự nhận: `/api/*.js` thành serverless function, `vercel.json` trỏ `/` về file game.
   **Không cần** build command, không cần `package.json`.
3. Đặt biến môi trường (bảng bên dưới) rồi **Redeploy**.
4. Mở `https://<tên-miền>/api/health` — phải thấy `"sheets":true`.

> **Phải chạy trang trên chính tên miền Vercel.** Trang gọi `/api/...` theo đường dẫn tương đối.
> Nếu copy file HTML lên Wix/Netlify thì `/api/buff` là 404: game vẫn chạy nhưng không ghi được sổ giao dịch.
> Muốn nhúng vào Wix thì dùng iframe trỏ tới URL Vercel, đừng tải file HTML lên Wix.

## Tính năng

| Tính năng | Ai dùng | Ghi log vào tab |
|---|---|---|
| Lưu giao dịch buff: thông tin đơn + ảnh chuyển khoản (ảnh lưu Drive riêng) | Khán giả gửi | `Buff` |
| Kết quả kiểm duyệt (Duyệt / Từ chối, tổng quỹ nhà sau duyệt), tự cập nhật cột Trạng thái ở `Buff` | Bàn MC (nhận lệnh từ trang Duyệt) | `Duyet` |
| **Góp lửa** — *đang TẮT* (`CO_HOA_LUC = false`): ẩn thanh emoji, quyền trợ giúp chỉ mở theo donate. Đổi thành `true` để bật lại | Khán giả | `HoaLuc` (gộp mỗi 30 giây) |
| Màn khán giả: Chat · **BXH BUFF LUCK** · **BUFF LUCK** (chọn nhà + QR, bấm QR để phóng to) | Khán giả | — |
| **Dự đoán nhà vô địch**: MC mở → popup cho mọi khán giả; mở chuông lần đầu tự khoá; MC công bố → ai đoán đúng thấy pháo hoa | Khán giả + MC | `DuDoan`, `KetQua` |
| **Link khán giả cố định** `#man` — không cần mã, tự vào phòng đang chơi | Khán giả | — |
| **Quản trò tắt/mở mic từng người** — từng đội và từng máy kiểm duyệt. "Khoá mic tất cả" áp cả cho đội vào sau | MC | — |
| **Top 5 BXH trên màn đội** — luôn hiện thêm hàng của chính đội mình | Đội | — |

## Link và phím tắt

| Thứ | Giá trị |
|---|---|
| Link khán giả cố định | `https://<tên-miền>/#man` — không mang mã phòng |
| Link khán giả có mã | `https://<tên-miền>/#man/<MÃ KG>` |
| Link đội | `https://<tên-miền>/#doi/<MÃ ĐỘI>` |
| Link trang duyệt | `https://<tên-miền>/#duyet/<MÃ KG>/<MÃ QUẢN TRỊ>` |
| Rung chuông (màn đội) | **Shift + R** |
| Bật/tắt mic (màn đội) | **M** |

**Link cố định hoạt động thế nào:** bàn quản trò giữ một tin MQTT "giữ lại" ở `rcvang/dangchoi`
ghi mã khán giả của phòng mình, đập lại 10 giây một lần. Ai mở `#man` sẽ đọc tin đó rồi vào thẳng.
Tin cũ quá 150 giây (quản trò đóng tab) thì trang báo và cho nhập mã tay.
Trong ô "Mã khán giả" ở bàn quản trò có checkbox **Dùng link khán giả cố định cho phòng này**
(mặc định bật) — **nhớ tắt ở phòng chạy thử**, nếu không link cố định sẽ theo phòng nào đập nhịp sau cùng.

## Cấu trúc

```
rungchuongvang-index4.html   app (MC / đội / khán giả / trang duyệt)
api/_lib.js                  helper chung: validate, rate limit, chống formula injection, gọi Apps Script
api/buff.js                  POST /api/buff  — khán giả gửi đơn + ảnh
api/log.js                   POST /api/log   — MC gửi log theo lô (duyet | dudoan | hoaluc | ketqua)
api/health.js                GET  /api/health — kiểm tra đã nối Google Sheets chưa
gas/Code.gs                  Google Apps Script (dán vào Sheet)
vercel.json                  "/" -> file game
tests/api.test.js            10 test API với Apps Script giả
tests/dev-server.js          chạy local như Vercel
tests/e2e-*.py               test giao diện bằng Playwright (xem bên dưới)
tests/stub.js, harness.html  broker MQTT giả chạy trong trang, cho các test e2e
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
node tests/api.test.js        # 10 test API, không cần tài khoản Google
node tests/dev-server.js      # http://localhost:5173, in ra các dòng sẽ ghi vào sheet

# test giao diện (cần python3 + playwright + google-chrome)
python3 tests/e2e-tongquat.py     # vòng chơi cơ bản, màn khán giả không bị tràn khung
python3 tests/e2e-mobile.py       # bố cục điện thoại, khung chat cố định
python3 tests/e2e-top5.py         # Top 5 trên màn đội
python3 tests/e2e-mic.py          # quản trò tắt/mở mic từng máy
python3 tests/e2e-link-codinh.py  # link khán giả cố định
python3 tests/e2e-phim-rung.py    # phím Shift + R
python3 tests/e2e-khoa-mic.py     # quản trò khoá mic đội thì đội NGỪNG gửi tiếng thật
python3 tests/e2e-khoa-mic-ba-tinh-huong.py   # khoá trước khi đội vào · đội tải lại trang
python3 tests/e2e-thongbao-va-dotre.py        # thông báo không chắn nút · ngân sách độ trễ tiếng
```

## Luồng dữ liệu

- Khán giả → `/api/buff` (HTTPS) → Apps Script → tab `Buff` + ảnh vào Drive. Song song vẫn gửi qua MQTT cho bàn MC / trang duyệt như cũ.
- Cảm xúc khán giả mang theo `n` (id nhà) → **chỉ bàn MC cộng hỏa lực** (giới hạn 12 điểm/giây/máy), phát state tối đa 2 giây/lần.
- Dự đoán: mỗi khán giả giữ 1 tin retained `rcvang/<phòng>/dd/<id>` → chỉ bàn MC nghe → MC tải lại trang vẫn đủ.
- Bàn MC gom log, gửi `/api/log` theo lô 200 dòng mỗi 4 giây, lỗi thì thử lại, lưu hàng đợi vào localStorage.
- Phòng thoại: mặc định tiếng đi **qua máy chủ** (µ-law 16 kHz trên MQTT, mã hoá AES-GCM). Kiểu ngang hàng (WebRTC) là tuỳ chọn, mạng 4G/công ty hay chặn.

## Rủi ro đã biết

- Broker MQTT công cộng: không cam kết capacity; ai có mã khán giả có thể gửi tin giả. Giới hạn hiện có chỉ chặn spam thông thường.
- `/api/buff` và `/api/log` công khai: có validate + rate limit theo IP, nhưng bộ đếm nằm trong RAM **từng instance serverless** nên Vercel chạy nhiều instance là vượt được. Dùng `ADMIN_KEY` để phân biệt log thật của MC.
- Apps Script tài khoản thường: tối đa ~30 lượt chạy đồng thời.
- Hỏa lực và dự đoán lưu ở máy MC (localStorage). **Đổi máy MC giữa trận sẽ mất phần chưa ghi Sheets** — nên dùng đúng một máy, một trình duyệt suốt đêm diễn.
- Mở hai bàn quản trò cùng lúc thì link khán giả cố định sẽ theo phòng đập nhịp sau cùng.
- **Tiếng đi qua bàn quản trò khi hai máy chủ MQTT đều có người.** Bàn quản trò làm cầu nối: mỗi gói tiếng của mỗi đội đi qua máy quản trò rồi phát lại sang máy chủ còn lại, nên máy quản trò nặng và ai ở máy chủ kia phải chịu thêm một chặng. Cách tránh: cho tất cả đội và quản trò dùng **cùng một máy chủ** bằng cách thêm `?may=0` vào link, ví dụ `https://<tên-miền>/?may=0#doi/<MÃ ĐỘI>`.

## Ngân sách độ trễ tiếng

Các hằng số ở đầu phần `taoTiengMayChu` quyết định nghe nhau trễ bao nhiêu. Hiện tại:

| Hằng số | Giá trị | Ý nghĩa |
|---|---|---|
| `AM_GOI_MS` | 160 | mỗi gói chứa bấy nhiêu ms tiếng — tăng thì đỡ tốn tin nhắn nhưng trễ thêm |
| `AM_DEM_MS` | 320 | đệm chống giật ban đầu |
| `AM_DEM_MIN` | 220 | không co dưới mức này — **phải nhỏ hơn** `AM_DEM_MS`, nếu không đệm chỉ tăng chứ không giảm |
| `AM_DEM_MAX` | 900 | mạng xấu thì đệm nở tới đây |
| `AM_TRE_MAX` | 1300 | hàng chờ dài quá mức này thì bỏ bớt để đuổi kịp thời gian thực |

Mạng tốt thì trễ khoảng `AM_GOI_MS + AM_DEM_MS` ≈ 0,5 giây. Nếu nghe bị giật (ngắt quãng)
thì tăng `AM_DEM_MS`; nếu nghe trễ quá thì giảm `AM_DEM_MS` và `AM_TRE_MAX`.

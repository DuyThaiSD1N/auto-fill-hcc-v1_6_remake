# Trợ lý nhân dân — Extension

Chrome MV3, **vanilla JS, KHÔNG framework, KHÔNG build step**. Sidebar trợ lý toàn trình
(giọng nói + chat) cắm cạnh phải trang cổng dịch vụ công, **đẩy trang sang trái** —
không che nội dung.

> Kế hoạch & docs từng bước: `../docs/00-tong-quan-toan-trinh.md`.
> Backend đi kèm: `../tro-ly-nguoi-dan-backend` (dev: `http://localhost:8010`).

## Cài & chạy

1. `chrome://extensions` → bật Developer mode → **Load unpacked** → chọn thư mục này.
2. Mở trang web bất kỳ → bong bóng robot góc phải-dưới → bấm mở sidebar.
3. Sau mỗi lần sửa code: bấm **Reload** ở chrome://extensions rồi F5 trang.

Đổi backend không sửa code (console của sidebar):
`chrome.storage.local.set({ tlnd_base_url: "https://<domain>" })`

## Cấu trúc

```
manifest.json            # MV3 — thứ tự content_scripts QUAN TRỌNG (fill-core trước engines)
background.js            # toggle sidebar, getTabId, offscreen ASR lifecycle, hàng đợi attach
content.js               # sidebar push-layout (Shadow DOM, 440px) + launcher + persist
content/
├── fill-core.js         # LÕI điền form: helpers + namespace __TLND__ + dispatcher "fillFields"
├── fill-legacy.js       # engine eForm moj (x-*)          — copy từ auto-fill-hcc-extension
├── fill-angular.js      # engine Angular (lienthong)       — copy
├── fill-bacninh.js      # engine Liferay Bắc Ninh          — copy
├── review.js  bbox-overlay.js/.css   # rà soát bbox        — copy
sidebar.html/.css/.js    # UI chat trong iframe (chip/card theo prototype)
services/                # render.js (markdown) + audio/asr/tts.js (voice — Bước 4)
api/config.js            # base URL + suy WS; override qua chrome.storage
offscreen.html/.js       # thu mic ngoài iframe (Bước 4)   — port từ bản A Bảo
permission.html/.js      # xin quyền mic 1 lần             — port
lib/imageToPdf.js  vendor/pdf-lib.min.js   # gộp ảnh → PDF khi đính kèm
```

## Trạng thái (theo bước docs/)

- [x] **Bước 2** — khung sidebar push-layout + launcher + engines nạp sẵn
- [x] **Bước 3** — hội thoại `POST /assistant/chat` server-driven (chips/cards/actions + journey)
- [x] **Bước 4** — voice: 🎤 push-to-talk (offscreen), 🔊 TTS đọc trả lời, 🎙️ rảnh tay (đọc xong tự nghe, barge-in, tự tắt sau 2 lượt im lặng)
- [x] **Bước 5** — gửi giấy tờ qua QR + 📷 Scan tại quầy (upload từ máy tính): phân loại realtime, tiến trình đồng bộ WS
- [x] **Bước 6a** — pipeline OCR+LLM chạy nền → bot tự điền form → rà soát → kế hoạch đính kèm
- [x] **Bước 6b** — `content/attach-core.js`: bot TỰ đính từng tệp vào thành phần hồ sơ (ví giấy tờ, menu-slot, thêm thành phần)
- [x] **Bước 7** — watcher: tự nhận vào-form (bỏ chip đăng nhập), tự nhận nộp-thành-công; sidebar TỰ MỞ LẠI xuyên origin (journey keep_open); `content/portal-dvc.js` tự chọn cơ quan + Nộp trực tuyến (cổng React mới)
- [x] **Bước 8** — hoàn thành: card SĐT nhận thông báo, 💾 lưu profile theo SĐT, 📁 "Lấy dữ liệu đã lưu" (không chụp lại), 🗑️ xoá dữ liệu 1 chạm
- [ ] Polish: card review bbox "Xem trên ảnh" + voice điền 1 ô thiếu (fill_target)

## Quy ước

- Mọi giao tiếp file content dùng namespace `window.__TLND__` (đã đổi từ `__HCC__`).
- Selector khớp **text/label fold dấu**, không dùng id/class dễ đổi.
- Không thêm dependency mới (vendor chỉ có pdf-lib).

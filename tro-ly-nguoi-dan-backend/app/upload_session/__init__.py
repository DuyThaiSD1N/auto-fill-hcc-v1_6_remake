"""Phiên tải giấy tờ qua QR — trang mobile + phân loại realtime + WS đồng bộ.

Triển khai ở Bước 5 (docs/05-upload-qr-session.md):
  router.py   — POST /upload-sessions, GET /m/{id}, POST .../files, GET trạng thái
  ws.py       — WS /ws/upload-sessions/{id} (sidebar + mobile cùng subscribe)
  classify.py — phân loại ảnh nhẹ (loại giấy tờ/mặt/người) — map theo THỨ TỰ mảng
  mobile/     — trang chụp ảnh trên điện thoại (HTML/JS vanilla)
"""

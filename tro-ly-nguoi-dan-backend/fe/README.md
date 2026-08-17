# HCC Trace — FE

UI theo dõi auto-fill (`/process`): đăng nhập bằng tài khoản phường, xem danh sách
+ chi tiết mỗi lần gọi (phường, thủ tục, **text OCR gộp** các file, **JSON LLM parse được**).

## Chạy dev

```bash
cd fe
npm install
npm run dev      # http://localhost:5173, proxy /api & /auth -> localhost:8000
```

Cần backend chạy ở `localhost:8000` (`uvicorn app.main:app --reload`).

Đăng nhập bằng tài khoản đã seed, ví dụ `hcctanphong` / `hcctanphong12`.

## Build production

```bash
npm run build    # ra dist/
```

Đặt `VITE_API_BASE` (file `.env`) trỏ tới backend nếu không chung domain.
Nhớ thêm origin của FE vào `FRONTEND_ORIGINS` trong `.env` của backend.

## Cấu trúc

- `src/api.ts` — gọi API + lưu token (localStorage) + tự refresh khi 401.
- `src/pages/Login.tsx` — đăng nhập (`/auth/login`).
- `src/pages/Traces.tsx` — danh sách + lọc (phường / thủ tục / khoảng ngày) + phân trang.
- `src/components/TraceDetailPanel.tsx` — chi tiết: OCR text + JSON output.

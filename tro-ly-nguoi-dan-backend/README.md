# Trợ lý người dân — Backend

Backend Python (FastAPI + MongoDB) của hệ **Trợ lý người dân toàn trình**: bot dẫn dắt
người dân làm thủ tục hành chính bằng giọng nói + chat ngay trên cổng dịch vụ công —
từ chọn thủ tục, đăng nhập VNeID, gửi giấy tờ qua QR điện thoại, OCR điền form,
đính kèm, đến nộp và nhận thông báo.

> Kế hoạch tổng & docs từng bước: `../docs/00-tong-quan-toan-trinh.md` (00→09).
> Nền copy từ `auto-fill-hcc-backend`, CHỈ giữ 5 thủ tục pilot (docs/01 §2.2).

## 5 thủ tục pilot

| key | Thủ tục |
|---|---|
| `khai-sinh-dang-ky` | Khai sinh liên thông (khai sinh + thường trú + BHYT <6 tuổi) — pilot toàn trình |
| `ket-hon` | Đăng ký kết hôn |
| `dang-ky-giam-ho` | Đăng ký giám hộ |
| `trich-luc-ks` | Cấp bản sao Trích lục hộ tịch / bản sao Giấy khai sinh |
| `xac-nhan-tinh-trang-hon-nhan` | Cấp Giấy xác nhận tình trạng hôn nhân |

## Cấu trúc

```
app/
├── main.py  config.py          # FastAPI, settings (.env)
├── procedures/registry.py      # danh mục 5 thủ tục (thêm thủ tục = sửa 3 chỗ ở đây)
├── pipelines/                  # _shared + 5 package process/attach (OCR + LLM)
├── process/  attachments/      # dispatch pipeline (API nội bộ/quản trị)
├── review/                     # bbox review (sources + image)
├── services/  traces/  auth/…  # LLM/OCR client, lưu vết, JWT (quản trị)
├── chat/                       # [Bước 3] não hội thoại — POST /api/v1/assistant/chat
├── voice/                      # [Bước 4] WS /ws/asr + /ws/tts proxy
├── upload_session/             # [Bước 5] phiên QR + trang mobile + WS đồng bộ
├── profiles/  notify/          # [Bước 8] profile người dân + thông báo tiến độ
```

Extension chỉ chạm mặt API "1 cửa" (docs/03 §2.3): `POST /assistant/chat` + WS voice
+ WS upload-session + danh mục tĩnh. `/process`, `/attachments/plan` là nội bộ.

## Chạy dev

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
docker compose up -d mongo          # Mongo riêng, host port 27027
./.venv/bin/uvicorn app.main:app --reload --port 8010
curl -s localhost:8010/api/v1/procedures | jq '.[].key'   # đủ 5 key
./.venv/bin/python -m pytest -q     # test 5 thủ tục + storage
```

`.env`: copy từ `.env.example`, điền key LLM/OCR (xem `app/config.py` — gồm cả
placeholder voice/upload cho các bước sau).

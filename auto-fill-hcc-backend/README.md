# Auto Fill HCC — Backend

Backend (Python FastAPI) cho extension Auto Fill HCC. Giữ kín prompt LLM, URL OCR/LLM,
mapping logic; cung cấp API có auth cho extension (client).

## Stack
- FastAPI + Uvicorn
- MongoDB (Motor async) — dùng chung cluster callbot
- JWT (python-jose) + bcrypt (passlib)
- httpx gọi OCR + LLM provider
- Docker / docker-compose

## Chạy local (không Docker)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # điền MONGO_URI, JWT secret, ...
uvicorn app.main:app --reload --port 8000
```

## Chạy bằng Docker
```bash
cp .env.example .env          # điền giá trị thật
docker compose up -d --build
docker compose logs -f app
```
Mongo dùng cluster ngoài qua `MONGO_URI`. Muốn Mongo local cho dev: bỏ comment service
`mongo` trong `docker-compose.yml` và trỏ `MONGO_URI=mongodb://mongo:27017`.

## Tạo user (không có self-register)
```bash
python -m scripts.seed_user --email admin@x.vn --password 'MatKhau123' --name 'Admin'
```

## API
| Endpoint | Mô tả |
|---|---|
| `POST /auth/login` | `{email,password}` → `{accessToken, refreshToken, user}` |
| `POST /auth/refresh` | `{refreshToken}` → cặp token mới (rotate) |
| `GET /auth/me` | verify token → info user |
| `GET /api/v1/procedures` | list thủ tục `{key,label,roles,useDangKyBy}` |
| `POST /api/v1/process` | files + procedure → `{fields, extracted, stats, errors}` |
| `GET /healthz` | health check |

Tất cả endpoint (trừ `/auth/login`, `/auth/refresh`, `/healthz`) cần header
`Authorization: Bearer <accessToken>`.

### `POST /api/v1/process`
```jsonc
{
  "procedure": "khai-sinh-dang-ky",
  "options": { "dangKyBy": "father" },
  "files": [
    { "name": "cccd.jpg", "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,...", "role": "father" },
    { "name": "gcs.pdf",  "type": "application/pdf", "dataUrl": "data:application/pdf;base64,...", "role": "birthProof" }
  ]
}
```
`fields[].value` là `str` hoặc `dict` (component `x-select-area` trả `{quocGia,tinh,diaChi}`).

## Cấu trúc
Xem `auto-fill-hcc-extension/docs/backend-migration-python-plan.md` (mục 3 & 7) để biết chi tiết
mapping JS → Python.

## Test
```bash
pytest -q
```
- Integration tests under `tests/integration/` mock OCR/LLM where possible.

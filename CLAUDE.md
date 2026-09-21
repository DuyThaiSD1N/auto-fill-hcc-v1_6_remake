# auto-fill-hcc

Monorepo 3 phần:

- `auto-fill-hcc-backend/` — FastAPI + các pipeline thủ tục hành chính, chạy bằng Docker.
- `auto-fill-hcc-extension/` — extension Chrome điền form, trỏ về `http://localhost:12005`.
- `tro-ly-nguoi-dan-extension-main/` — extension trợ lý người dân.

## BẮT BUỘC: sửa xong code backend là deploy Docker ngay

Mỗi khi sửa bất kỳ file nào trong `auto-fill-hcc-backend/` (trừ file test và tài liệu), sau khi
sửa xong phải tự chạy tuần tự, không cần hỏi lại:

```bash
cd auto-fill-hcc-backend
python -m pytest tests/unit tests/integration -q          # 1. test trước
docker compose -f compose.prod.yml up -d --build app batch-worker   # 2. build + restart
docker compose -f compose.prod.yml ps                     # 3. kiểm tra container đã Up
curl -s http://localhost:12005/healthz                     # 4. kiểm tra backend sống
```

Chỉ báo "xong" khi container đã `Up` và `/healthz` trả về OK. Nếu build hoặc healthz lỗi thì sửa
tiếp, không được bỏ qua bước này.

Chọn service để build theo chỗ đã sửa:

| Sửa ở | Lệnh build |
| --- | --- |
| `app/`, `scripts/`, `requirements.txt`, `Dockerfile` | `up -d --build app batch-worker` |
| `fe/` | `up -d --build fe` |
| `monitor-fe/` | `up -d --build monitor-fe` |

Sửa file trong hai thư mục extension thì KHÔNG cần đụng Docker.

## TUYỆT ĐỐI dùng compose.prod.yml

Luôn truyền `-f compose.prod.yml` cho mọi lệnh `docker compose`. Chạy `docker compose up` trơn sẽ
lấy `docker-compose.yml` mặc định, đá container app sang network `callbot-hcc-base_call_bot` và làm
web trace trả 502. Phần hướng dẫn Docker trong `auto-fill-hcc-backend/README.md` đã cũ, đừng làm theo.

## Cổng

| Dịch vụ | Cổng |
| --- | --- |
| Backend API | 12005 |
| Web quản lý (fe) | 12006 |
| Web Monitor (monitor-fe) | 12007 |
| Mongo | 12004 |

## Deploy sang server khác

Chỉ chạy khi người dùng yêu cầu rõ ràng, không tự động:

```bash
TARGET=user@server-dich ./scripts/deploy_to_server.sh
```

Script build image, `docker save` rồi `scp` sang đích. Sau đó phải vào server đích chạy
`cd /opt/autofill-hcc && ./server_up.sh` thì mới thực sự lên.

## Test

Chỉ chạy hai cây `tests/unit` và `tests/integration`. Cây `tests/handfree` lỗi collect sẵn, bỏ qua.
Baseline hiện tại có sẵn một số test đỏ không liên quan đến code mới; so số fail trước và sau khi
sửa thay vì cố đưa về 0.

## Lưu ý
Không bao giờ được phép tự ý dùng git để merge code hay đẩy lên github
# auto-fill-hcc

Monorepo 3 phần:

- `auto-fill-hcc-backend/` — FastAPI + các pipeline thủ tục hành chính, chạy bằng Docker.
- `auto-fill-hcc-extension/` — extension Chrome điền form, trỏ về `http://localhost:12005`.
- `tro-ly-nguoi-dan-extension-main/` — extension trợ lý người dân.

## BẮT BUỘC: sửa xong code backend là deploy Docker ngay

Mỗi khi sửa bất kỳ file nào trong `auto-fill-hcc-backend/` (trừ file test và tài liệu), sau khi
sửa xong phải tự chạy tuần tự, không cần hỏi lại. Khi người dùng nói "chạy code mới lên docker"
cũng làm đúng quy trình này (máy là Windows, lệnh dưới đây chạy được trong PowerShell):

```powershell
cd auto-fill-hcc-backend

# 1. Test riêng pipeline vừa sửa — bắt buộc pass hết
python -m pytest tests/unit/test_<ten_pipeline>.py -q -p no:cacheprovider

# 2. Test toàn bộ để so với baseline
python -m pytest tests/unit tests/integration -q --continue-on-collection-errors -p no:cacheprovider

# 3. Build + restart (chọn service theo bảng bên dưới)
docker compose -f compose.prod.yml up -d --build app batch-worker

# 4. Kiểm tra container đã Up
docker compose -f compose.prod.yml ps

# 5. Kiểm tra backend sống — phải trả về {"ok":true}
curl.exe -s http://localhost:12005/healthz
```

Ghi chú từng bước:

- Bước 1: nếu test của pipeline vừa sửa đỏ thì sửa tiếp, KHÔNG build Docker.
- Bước 2: bắt buộc có `--continue-on-collection-errors`. Ở máy local, 3 file
  `tests/unit/test_monitor_attach_flow.py`, `test_monitor_process_flow.py`,
  `test_trace_document_content_access.py` lỗi collect do protobuf local cũ (thiếu
  `runtime_version`). Thiếu cờ này thì pytest dừng ngay, không chạy test nào. Đây là lỗi môi
  trường, không phải lỗi code, và không ảnh hưởng image Docker.
- Bước 2: so số fail với baseline ở mục "Test". Số fail tăng, hoặc có test fail thuộc pipeline vừa
  sửa, thì phải xem lại trước khi build.
- Bước 5: trong PowerShell phải gõ `curl.exe`. `curl` trơn là alias của `Invoke-WebRequest`.

Chỉ báo "xong" khi container đã `Up` và `/healthz` trả về `{"ok":true}`. Nếu build hoặc healthz
lỗi thì sửa tiếp, không được bỏ qua bước này. Khi báo cáo cho người dùng, ghi rõ: kết quả test của
pipeline vừa sửa, số pass/fail toàn bộ so với baseline, trạng thái container, kết quả healthz.

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

Baseline ngày 2026-10-02, sau commit "thay BE mới" (máy local, có `--continue-on-collection-errors`):
`101 failed, 2144 passed, 23 skipped, 4 errors` (lỗi collect thứ 4 là
`tests/unit/test_submit_click_khong_dem_doi.py`). Các test đỏ nằm ở khai tử, trích lục, xác nhận TTHN,
thay đổi hộ tịch, khuyết tật, xét tuyển viên chức, mai táng. Nếu sửa xong mà số test đỏ giảm hẳn
hoặc tăng lên, cập nhật lại dòng này.

## Lưu ý
Không bao giờ được phép tự ý dùng git để merge code hay đẩy lên github
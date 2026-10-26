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

# 2. Test toàn bộ để so với baseline (cần plugin win_socketpair + UTF-8, xem ghi chú bước 2)
$env:PYTHONUTF8="1"; $env:PYTHONPATH="<thu-muc-chua-win_socketpair.py>"
python -m pytest tests/unit tests/integration -q --continue-on-collection-errors -p no:cacheprovider -p win_socketpair --tb=native

# 3. Build + restart (chọn service theo bảng bên dưới)
docker compose -f compose.prod.yml up -d --build --remove-orphans app

# 4. Kiểm tra container đã Up
docker compose -f compose.prod.yml ps

# 5. Kiểm tra backend sống — phải trả về {"ok":true,...}
curl.exe -s http://localhost:12005/healthz
```

Ghi chú từng bước:

- Bước 1: nếu test của pipeline vừa sửa đỏ thì sửa tiếp, KHÔNG build Docker.
- Bước 2: bắt buộc có `--continue-on-collection-errors` (máy local thiếu `mongomock` → 3 file lỗi collect;
  thiếu cờ này pytest dừng ngay).
- Bước 2: từ bản BE 2026-10-12, `tests/conftest.py` chặn mọi `socket.connect` trừ `AF_UNIX` — Windows
  không có `AF_UNIX`, asyncio lại tạo socketpair qua 127.0.0.1 → chạy trơn ra ~440 errors và pytest có thể
  INTERNALERROR (`AST constructor recursion depth mismatch`, tránh bằng `--tb=native`). KHÔNG sửa
  conftest (bản BE dán đè lại). Tạo file `win_socketpair.py` trong scratchpad, trỏ `PYTHONPATH` tới đó:
  ```python
  import socket
  _connect_goc = socket.socket.connect
  if not hasattr(socket, "AF_UNIX"):
      socket.AF_UNIX = -1  # conftest vẫn chặn kết nối mạng thật
  _pair_goc = socket.socketpair
  def _pair(*a, **k):
      cur = socket.socket.connect
      socket.socket.connect = _connect_goc
      try:
          return _pair_goc(*a, **k)
      finally:
          socket.socket.connect = cur
  socket.socketpair = _pair
  ```
  `PYTHONUTF8=1` để test chạy node (vd `test_mobile_send_queue.py`) không vỡ vì cp1252.
- Bước 2: so số fail với baseline ở mục "Test". Số fail tăng, hoặc có test fail thuộc pipeline vừa
  sửa, thì phải xem lại trước khi build.
- Bước 5: trong PowerShell phải gõ `curl.exe`. `curl` trơn là alias của `Invoke-WebRequest`.

Chỉ báo "xong" khi container đã `Up` và `/healthz` trả về `{"ok":true}`. Nếu build hoặc healthz
lỗi thì sửa tiếp, không được bỏ qua bước này. Khi báo cáo cho người dùng, ghi rõ: kết quả test của
pipeline vừa sửa, số pass/fail toàn bộ so với baseline, trạng thái container, kết quả healthz.

Chọn service để build theo chỗ đã sửa:

| Sửa ở | Lệnh build |
| --- | --- |
| `app/`, `scripts/`, `requirements.txt`, `Dockerfile` | `up -d --build --remove-orphans app` |
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

Baseline ngày 2026-10-26, sau commit "update BE" e85b0b7 + khôi phục 4 file BE của a850f92 (máy local, plugin
win_socketpair, có PYTHONUTF8=1): `11 failed, 3050 passed, 40 skipped, 5 errors` (gồm test Monitor trả ảnh chụp form
thêm cùng ngày). 11 đỏ y hệt bản 2026-10-21; lỗi collect thứ 5 là `tests/unit/test_form_snapshots.py` (file mới của
bản BE, cũng thiếu `mongomock`).

Baseline ngày 2026-10-26, sau commit "thêm thủ tục" 467a57f (máy local, plugin win_socketpair, có PYTHONUTF8=1):
`11 failed, 3020 passed, 39 skipped, 4 errors`. 11 đỏ y hệt bản 2026-10-21; lỗi collect thứ 4 là
`tests/unit/test_archive_worker.py` (có từ BE 2676438, cũng thiếu `mongomock`).

Baseline ngày 2026-10-26, sau commit "thêm thủ tục" 467a57f (cùng điều kiện như dưới): `11 failed, 3020 passed, 39 skipped,
4 errors`. 11 đỏ y như bản 2026-10-21; error thứ 4 là `tests/unit/test_archive_worker.py`, cũng thiếu `mongomock`.

Baseline ngày 2026-10-21, sau commit "update lại bE" 5792794 (máy local, plugin win_socketpair, có PYTHONUTF8=1):
`11 failed, 2914 passed, 39 skipped, 3 errors`. Đúng 15 đỏ môi trường của bản 2026-10-12 trừ 4 `test_mobile_send_queue`
(pass nhờ UTF-8); 3 errors vẫn là thiếu `mongomock`.

Baseline ngày 2026-10-12, sau commit "thay BE mới" 8b35314 (máy local, plugin win_socketpair, chưa đặt
PYTHONUTF8): `15 failed, 2400 passed, 38 skipped, 3 errors`. Cả 15 đỏ là môi trường, chạy trong image Docker đều pass:
4 `test_heic_to_jpeg` (local thiếu `pillow-heif`), 4 `test_mobile_send_queue` (cp1252; có `PYTHONUTF8=1` thì pass),
7 test v2 trả 422 ở `test_v2_process` / `test_monitor_*_flow` (local fastapi 0.111 / python-multipart 0.0.9, requirements
ghi 0.115.6 / 0.0.20). 3 errors là collect thiếu `mongomock`. Bản BE này bỏ service `batch-worker`
(và `scripts/run_batch_worker.py`) khỏi compose.prod.yml.

Baseline cũ ngày 2026-10-09, sau commit "update BE mới" e9a9dda (máy local, có `--continue-on-collection-errors`):
`111 failed, 2328 passed, 34 skipped, 6 errors`. So với bản 2026-10-07 (`108 failed, 2286 passed`) thêm 3 đỏ đến từ
chính bản BE dán vào, trong đó `test_dieu_chinh_huu_tri_registry` còn đợi tên cũ "Thực hiện, điều chỉnh, thôi hưởng
trợ cấp hưu trí xã hội" sau khi BE đổi label. Bản 2026-10-07:
`108 failed, 2286 passed, 34 skipped, 6 errors`. Lỗi collect thứ 4 là `tests/unit/test_submit_click_khong_dem_doi.py`,
thứ 5 và 6 là `tests/unit/test_auth_refresh_grace.py`, `tests/unit/test_upload_session_sliding_expiry.py` (máy local
thiếu `mongomock`). Bản 2026-10-05 trước đó: `107 failed, 2204 passed, 30 skipped, 5 errors`. So với bản trước (103 failed):
6 test registry cũ đỏ vì `khai-sinh-dang-ky-thuong`, `khai-tu`, `trich-luc-ks`, `thay-doi-cai-chinh-ho-tich` đã
chuyển sang pipeline Cổng DVC quốc gia mới (`*_dvc_moi`, `khai_tu_dvcqg`); 2 test `chuyen_muc_dich_su_dung_dat_lam_dong`
hết đỏ vì file test bị xoá. Các test đỏ nằm ở khai tử, trích lục, xác nhận TTHN,
thay đổi hộ tịch, khuyết tật, xét tuyển viên chức, mai táng. Nếu sửa xong mà số test đỏ giảm hẳn
hoặc tăng lên, cập nhật lại dòng này.

## Lưu ý
Không bao giờ được phép tự ý dùng git để merge code hay đẩy lên github
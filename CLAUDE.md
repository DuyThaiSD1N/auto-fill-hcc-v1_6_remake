# auto-fill-hcc

Monorepo 4 phần:

- `auto-fill-hcc-backend/` — FastAPI + các pipeline thủ tục hành chính, chạy bằng Docker.
- `auto-fill-hcc-extension/` — extension Chrome điền form, trỏ về `http://localhost:12005`.
- `tro-ly-nguoi-dan-extension-main/` — extension trợ lý người dân.
- `auto-test-hcc/` — web Agent tự sửa + dịch vụ agent, tách riêng khỏi backend (xem mục Web Agent tự sửa).

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

Sửa file trong hai thư mục extension thì KHÔNG cần đụng Docker. Sửa `auto-test-hcc/` thì không build backend (xem mục Web Agent tự sửa).

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
| Web Agent tự sửa (test-fe) | 12008 |
| Dịch vụ agent (chạy trên host, chỉ nghe 127.0.0.1) | 12009 |
| Mongo | 12004 |

## Deploy sang server khác

Chỉ chạy khi người dùng yêu cầu rõ ràng, không tự động:

```bash
TARGET=user@server-dich ./scripts/deploy_to_server.sh
```

Script build image, `docker save` rồi `scp` sang đích. Sau đó phải vào server đích chạy
`cd /opt/autofill-hcc && ./server_up.sh` thì mới thực sự lên.

## Web Agent tự sửa (auto-test-hcc, cổng 12008)

Tách riêng khỏi backend theo yêu cầu người dùng, mã nằm ở `auto-test-hcc/`, ĐỪNG đưa lại vào `monitor-fe`. Compose riêng, nối vào
mạng `autofill_hcc_net`, nên `docker compose` của phần này dùng `-f auto-test-hcc/compose.yml` chứ không phải `compose.prod.yml`.
Người sửa code đọc `auto-test-hcc/README.md`, đội tester đọc `auto-test-hcc/KE-HOACH.md`, team F19 cài máy mới theo `auto-test-hcc/HUONG-DAN-F19.md`.

- Chỉ super_admin. Nhận mã req + mô tả lỗi; hội đồng agent họp, trọng tài quyết định; lỗi OCR thì bỏ qua và báo cáo; lỗi code thì sửa
  BE hoặc extension, chạy test, rồi DỪNG CHỜ NGƯỜI DUYỆT patch trên web (đồng ý / làm lại theo góp ý / dừng); có đồng ý mới build và
  chạy lại 5 lần để chấm. Không thêm cờ bỏ qua bước duyệt. Bản sửa đạt nằm trong thư mục làm việc, chưa commit. Hết vòng mà
  chưa đạt (Cần người xem) thì để lại code của vòng trượt gần nhất cho người xem, không build, có nút hoàn tác.
- Giấy tờ chỉ lấy từ req nội bộ trong Mongo local. Mỗi lần chạy phải OCR mới: dịch vụ tự xoá cache OCR của đúng các tệp trong req rồi
  kiểm lại `trace_steps.ocr[].cache`, không cần cờ trong BE.
- Chạy trên cổng thật: người dùng chỉ đăng nhập VNeID, bot tự vào thủ tục qua panel như Auto Fill, tự xác nhận, tải lại trang và điền
  5 lần, chấm trên giá trị đọc từ form. Bot KHÔNG được nộp hồ sơ: không gỡ lớp chặn nộp trong `agents/browser.py`, không thêm cờ tắt.
- Tab "Thêm thủ tục mới" (`agents/devjob.py`) đã gỡ ngày 2026-11-09 theo yêu cầu người dùng; web chỉ còn job sửa lỗi một ca.

## Thêm thủ tục mới

### Tên folder pipeline theo key trong ke_khai_links.json

Mỗi khi làm pipeline cho thủ tục mới, key thủ tục trong `app/procedures/registry.py` phải TRÙNG `key` đã khai ở
`app/procedures/data/ke_khai_links.json`, và tên folder pipeline là đúng key đó đổi `-` thành `_`. Ví dụ link
`hoa-giai-tranh-chap-dat-dai` → folder `app/pipelines/hoa_giai_tranh_chap_dat_dai/`, test
`tests/unit/test_hoa_giai_tranh_chap_dat_dai.py`. Thủ tục chưa có link thì thêm link vào `ke_khai_links.json`
trước, chốt key ở đó rồi mới đặt tên folder. Không tự đặt tên folder khác key (kiểu viết tắt, đổi thứ tự chữ).

### Thủ tục mới có đính kèm thì luôn hỗ trợ tách file

Theo yêu cầu người dùng (12/11/2026): mọi thủ tục mới có bước đính kèm phải chạy được cả khi extension BẬT
cài đặt "Tách giấy tờ", không cần người dùng nhắc. Cụ thể:

1. Entry trong `app/procedures/registry.py` khai `"supportsSplitDocuments": True` (thiếu cờ thì planner luôn cắt
   trang dù người dùng tắt cài đặt). Thủ tục đưa lên trợ lý thì entry trong `procedure_registry.py` cũng khai cờ này.
2. Pipeline có `attach/planner.py` điều phối theo `options.splitDocuments is True` (chỉ boolean True mới tách; client
   cũ / tắt tách đính nguyên tệp) giữa `attach/dinh_kem_tach/` và `attach/dinh_kem_khong_tach/`.
3. Chế độ tách: LLM chia giấy theo trang trong MỘT lượt, mỗi giấy một mục có `sourceSegments`, không sót trang,
   ghép hai mặt CCCD; OCR / LLM lỗi thì quay về chế độ không tách. Dùng lại hàm chia trang của một thủ tục cùng cổng
   (vd `khai_sinh_dvc_moi/attach/dinh_kem_tach/planner.py` cho Cổng DVC quốc gia mới), chỉ viết riêng prompt và
   bảng dòng.
4. Test của pipeline có ca tách đúng dòng + không sót trang, ca tắt tách đính nguyên tệp, ca tách lỗi quay về
   không tách. Mẫu: `tests/unit/test_khai_sinh_nuoc_ngoai.py` (2.000528).

### Làm thủ tục mới thì đưa lên cả trợ lý người dân (tro-ly-nguoi-dan)

Không cần người dùng nhắc: làm xong pipeline lõi (Auto Fill) thì đưa luôn thủ tục đó lên trợ lý, cùng key. Chép theo
một thủ tục ĐÃ chạy trên trợ lý ở cùng cổng, cùng cấp cơ quan (vd cổng NN&MT cấp xã → `ho-tro-co-so-san-xuat-thiet-hai-
dich-benh-dong-vat`; iGate tỉnh → bản Khánh Hòa/Tuyên Quang). Các chỗ phải khai (đều trong `auto-fill-hcc-backend/`):

1. `app/channels/handfree/procedure_registry.py`: entry cùng key với lõi (`detect`, `label`, `shortLabel`,
   `subtitle`, `icon`, `keKhaiUrl` = url trong ke_khai_links, cờ chọn cơ quan, `wizard`, `bxdFlow` nếu là cổng iGate
   các bộ, `requiredDocs`, `uploadHint`). Thủ tục riêng của tỉnh thì thêm `provinceOnly`. Cùng file thêm một dòng vào
   `_HOAN_THIEN_THEO_TINH` (tỉnh nào bảng theo dõi thủ tục ghi "Hoàn thiện phần mềm"; chưa có trong bảng thì hỏi
   người dùng): vắng dòng thì tài khoản 11 tỉnh theo dõi không thấy thủ tục, test
   `test_service_list_frequent_province.py` đỏ. Bảng chép từ file Excel theo dõi ngày 10/11/2026.
2. `app/channels/handfree/chat/procedure_picker/prompt.py`: câu người dân hay nói để agent chọn đúng thủ tục, kèm
   chú thích phân biệt với thủ tục dễ nhầm.
3. `app/channels/handfree/chat/script_mong.py`: tên tiếng Mông, ghi "BẢN NHÁP chờ anh Dư soát".
4. Cổng iGate các bộ (bxdFlow): thêm `app/pipelines/<folder>/handfree/__init__.py` + `field_review.py`
   (`PROCEDURE_KEYS`, `REQUIRED = ()`, `NO_ASK`) — ngoại lệ được phép của quy tắc không thêm file mới.
5. Test: `tests/handfree/unit/test_flow_profiles.py` (số đếm + dòng ghi chú, khối kiểm khuôn cấp cơ quan), các danh
   sách key ở `test_field_review.py`, `test_bxd.py`, `test_mae_agency_cap_xa.py`… theo khuôn đã chép; thêm một test
   trợ lý vào file test của pipeline. Chạy riêng từng file test handfree đã sửa (cả cây `tests/handfree` có lỗi
   collect sẵn).

Extension trợ lý (`tro-ly-nguoi-dan-extension-main/`) chỉ phải sửa khi thủ tục nằm trên cổng/host trợ lý chưa chạy:
thêm host vào `maeHost` (content.js) và `HOSTS` (content/bxd/portal.js, field-review-formio.js), kèm cờ capability
riêng. Chỉ đẩy lên thai_dev khi người dùng yêu cầu.

## Test

Chỉ chạy hai cây `tests/unit` và `tests/integration`. Cây `tests/handfree` lỗi collect sẵn, bỏ qua.
Baseline hiện tại có sẵn một số test đỏ không liên quan đến code mới; so số fail trước và sau khi
sửa thay vì cố đưa về 0.

Baseline ngày 2026-11-05, sau khi kéo BE thai_dev 8a15b386 (máy local, plugin win_socketpair, có PYTHONUTF8=1):
`13 failed, 3866 passed, 40 skipped, 6 errors`. Vẫn đúng 13 đỏ môi trường (4 heic + 9 v2 422); lỗi collect thứ 6 là
`tests/unit/test_bug_reports.py` (mới kéo về), cũng thiếu `mongomock` (image Docker cũng không có mongomock).

Baseline ngày 2026-11-02, sau khi đổi Thành phố Quảng Ninh (máy local, plugin win_socketpair, có PYTHONUTF8=1):
`13 failed, 3535 passed, 40 skipped, 5 errors`. Chỉ còn đỏ môi trường (4 heic + 9 v2 422); 2 đỏ `test_dang_ky_hanh_nghe.py`
attach của bản 2026-11-01 đã hết.

Baseline ngày 2026-11-01, sau commit kéo BE thai_dev 2cd2bfe (máy local, plugin win_socketpair, có PYTHONUTF8=1):
`15 failed, 3393 passed, 40 skipped, 5 errors`. Vẫn 4 heic; v2 422 thành 9 (BE kéo về thêm 2 test v2 sha256/409 — cùng lỗi
môi trường fastapi/python-multipart); thêm 2 đỏ `tests/integration/test_dang_ky_hanh_nghe.py` attach (đến từ bản BE kéo về,
planner không import gì của code mới).

Baseline ngày 2026-10-28, sau commit "update code mới" 4e6bce2 (máy local, plugin win_socketpair, có PYTHONUTF8=1):
`11 failed, 3103 passed, 40 skipped, 5 errors`. Lại đúng 11 đỏ môi trường (4 heic + 7 v2 422);
`test_registry_uses_ho_tro_mai_tang_process_pipeline` đã hết đỏ. Bản dán 4e6bce2 đưa 3 test của commit 11e46e3 về bản cũ
(mai táng hưu trí, procedure_picker, assistant_flow) nên đã khôi phục lại; `test_khuyet_tat_compact_agent` chỉnh để nhận
cảnh báo `SECTION_III_WARNING` khi đọc ảnh Mục III lỗi.

Baseline ngày 2026-10-27, sau commit "update code" 60b7f96 (máy local, plugin win_socketpair, có PYTHONUTF8=1):
`12 failed, 3082 passed, 40 skipped, 5 errors`. Thêm 1 đỏ so với 2026-10-25:
`test_registry_uses_ho_tro_mai_tang_process_pipeline` (BE 3e6e220 thêm mã "(1.001731)" vào label mai táng, test còn tên cũ);
lỗi collect thứ 5 là `tests/unit/test_form_snapshots.py`, cũng thiếu `mongomock`.

Baseline ngày 2026-10-25, sau commit "thêm thủ tục" 467a57f (máy local, plugin win_socketpair, có PYTHONUTF8=1):
`11 failed, 3013 passed, 39 skipped, 4 errors` (3013 gồm 2 test freshOcr thêm cùng ngày). Vẫn 11 đỏ môi trường như bản 2026-10-21; lỗi collect thứ 4 là
`tests/unit/test_archive_worker.py` (thêm ở commit 2676438) cũng thiếu `mongomock`.

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
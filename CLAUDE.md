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
- Req của trolysoao (người dùng chốt lại 17/11/2026): Agent tự sửa CHẠY TRÊN MÁY LOCAL, chỉ đọc req của server `nlp@<ip-trolysoao>`
  qua SSH (khoá bị giới hạn: đường hầm tới Mongo 12004 + `deploy/read-uploads.sh`, tài khoản Mongo `autotest_ro` role read), xem
  mục A của `auto-test-hcc/HUONG-DAN-SERVER.md`. Backend thử vẫn là Docker local 12005. KHÔNG chạy `deploy_to_server.sh` cho việc
  này: script đó đẩy BE local đè lên production.
- Cách B, cài cả hệ thống lên server (chưa dùng, giữ để sau): req lấy từ Mongo + uploads PRODUCTION
  qua tài khoản chỉ đọc; bản sửa build và chạy lại trên backend THỬ `auto-test-hcc/deploy/compose.server.yml` (127.0.0.1:12015, Mongo
  riêng 12014), không bao giờ build `compose.prod.yml` trên server (`config.server_problems()` chặn); bản sửa đạt commit lên nhánh
  `agent/<mã ca>` của repo `dev-f19/test-auto-test-and-fix` (`agents/publish.py`), không đẩy lên main; cửa sổ bot xem qua noVNC
  `/vnc/` có vé super_admin. Máy local không đặt biến `AUTOTEST_*` thì chạy như cũ.

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
   `_HOAN_THIEN_THEO_TINH` (tỉnh nào bảng theo dõi thủ tục ghi "Hoàn thiện phần mềm"): vắng dòng thì tài khoản 11 tỉnh
   theo dõi không thấy thủ tục, test `test_service_list_frequent_province.py` đỏ (nhớ cộng số đếm từng tỉnh trong
   test đó). Bảng chép từ file Excel theo dõi ngày 10/11/2026.

   **Mặc định toàn quốc** (người dùng chốt 16/11/2026): người dùng không nói gì về tỉnh / phạm vi áp dụng thì thủ tục
   mở cho TOÀN QUỐC — không khai `provinceOnly`, dòng `_HOAN_THIEN_THEO_TINH` ghi `_TAT_CA`, không cần hỏi lại. Chỉ
   giới hạn tỉnh khi người dùng nói rõ, hoặc thủ tục là bản riêng của một tỉnh (key / label / link mang tên tỉnh, cổng
   tỉnh, mã thủ tục địa phương).
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

Baseline ngày 2026-11-25, sau khi thêm pipeline 1.012796 đính chính GCN đã cấp lần đầu có sai sót Khánh Hòa
(`dinh_chinh_gcn_cap_lan_dau_sai_sot_khanh_hoa`, máy local, plugin win_socketpair, có PYTHONUTF8=1):
`23 failed, 6428 passed, 42 skipped, 13 errors`. Vẫn đúng 23 đỏ như dòng dưới.

Baseline ngày 2026-11-25, sau khi thêm pipeline 1.115591 tổ chức kinh tế nhận chuyển nhượng QSDĐ Lai Châu
(`to_chuc_kinh_te_nhan_chuyen_nhuong_qsdd_du_an_lai_chau`, máy local, plugin win_socketpair, có PYTHONUTF8=1):
`23 failed, 6397 passed, 42 skipped, 13 errors`. Vẫn đúng 23 đỏ như dòng dưới.

Baseline ngày 2026-11-25, sau khi khôi phục form cũ eForm Bộ Tư pháp xác nhận TTHN 1.004873
(`xac-nhan-tinh-trang-hon-nhan-eform` → pipeline cũ `xac_nhan_tthn`, máy local, plugin win_socketpair, có PYTHONUTF8=1):
`23 failed, 6365 passed, 42 skipped, 13 errors`; khôi phục thêm form cũ trích lục 2.000635 (`trich-luc-ks-eform` → pipeline
cũ `trich_luc`) cùng ngày: `23 failed, 6368 passed, 42 skipped, 13 errors`. Vẫn đúng 23 đỏ như dòng dưới.

Baseline ngày 2026-11-25, sau khi thêm pipeline 1.115692 cấp GCN phần diện tích còn lại Lào Cai
(`dang_ky_cap_gcn_phan_dien_tich_con_lai_du_dieu_kien_lao_cai`, máy local, plugin win_socketpair, có PYTHONUTF8=1):
`23 failed, 6346 passed, 42 skipped, 13 errors`. Vẫn đúng 23 đỏ như dòng dưới; `test_cap_moi_gphn_chuyen_tiep_attach.py::
test_giay_co_chu_llm_tra_other_van_canh_bao_vao_dong_don` thỉnh thoảng đỏ khi chạy cả cây (chạy riêng pass) — chập chờn.

Baseline ngày 2026-11-25, sau khi thêm pipeline 1.115683 gia hạn phương án sử dụng đất kết hợp Lào Cai
(`gia_han_phuong_an_su_dung_dat_ket_hop_da_muc_dich_lao_cai`, máy local, plugin win_socketpair, có PYTHONUTF8=1):
`23 failed, 6313 passed, 42 skipped, 13 errors`. Vẫn đúng 23 đỏ như dòng dưới.

Baseline ngày 2026-11-25, sau khi thêm pipeline 1.115684 giao đất ở Lào Cai cấp xã (`giao_dat_o_khong_dau_gia_lao_cai`,
máy local, plugin win_socketpair, có PYTHONUTF8=1): `23 failed, 6285 passed, 42 skipped, 13 errors`; thêm chế độ "Lấy người nộp theo tờ khai" cùng ngày: `23 failed, 6292 passed, 42 skipped, 13 errors`. Vẫn đúng 23 đỏ như dòng dưới.

Baseline ngày 2026-11-25, sau khi thêm link 1.115684 giao đất ở Lào Cai cấp xã (máy local, plugin win_socketpair, có
PYTHONUTF8=1): `23 failed, 6264 passed, 42 skipped, 13 errors`. 17 đỏ như dòng dưới + 6 đỏ
`tests/unit/test_dashboard_xuat_danh_gia.py` (đến từ commit 9aae1f9b8: `strftime` có chữ tiếng Việt vỡ locale Windows ở
`app/dashboard/export.py`, cùng loại đỏ dashboard cũ).

Baseline ngày 2026-11-24, sau khi thêm 3.000333 cấp Phiếu lý lịch tư pháp Công an cấp tỉnh (máy local, plugin
win_socketpair, có PYTHONUTF8=1): `17 failed, 6249 passed, 42 skipped, 13 errors`. Vẫn đúng 17 đỏ và 13 lỗi collect như dòng dưới.

Baseline ngày 2026-11-24, sau khi thêm khối nhận kết quả (cboRECEIVER_TYPE) cho trang tạm trú (máy local, plugin
win_socketpair, có PYTHONUTF8=1): `17 failed, 6233 passed, 42 skipped, 13 errors`. Vẫn đúng 17 đỏ và 13 lỗi collect như dòng dưới.

Baseline ngày 2026-11-24, sau khi thêm 1.115148 tính lại tiền sử dụng đất Khánh Hòa (máy local, plugin win_socketpair, có
PYTHONUTF8=1): `17 failed, 6223 passed, 42 skipped, 13 errors`. Vẫn đúng 17 đỏ và 13 lỗi collect như dòng dưới.

Baseline ngày 2026-11-24, sau khi thêm đính kèm cho 1.010041 xác nhận thông tin về cư trú (máy local, plugin win_socketpair,
có PYTHONUTF8=1): `17 failed, 6230 passed, 42 skipped, 13 errors`. Vẫn đúng 17 đỏ và 13 lỗi collect như dòng dưới.

Baseline ngày 2026-11-24, sau khi thêm 1.013061 cấp phép thi công công trình trên đường bộ đang khai thác (máy local, plugin
win_socketpair, có PYTHONUTF8=1): `17 failed, 6194 passed, 42 skipped, 13 errors` (gồm test khối "Thông tin chi tiết" thêm cùng ngày). Vẫn đúng 17 đỏ và 13 lỗi collect như dòng dưới.

Baseline ngày 2026-11-24, sau khi thêm 1.115462 xác nhận tiếp tục sử dụng đất nông nghiệp Bắc Ninh (máy local, plugin
win_socketpair, có PYTHONUTF8=1): `17 failed, 6177 passed, 42 skipped, 13 errors`. Vẫn đúng 17 đỏ và 13 lỗi collect như dòng dưới.

Baseline ngày 2026-11-24, sau khi thêm 1.001766 khai tử có yếu tố nước ngoài (máy local, plugin win_socketpair, có
PYTHONUTF8=1): `17 failed, 6145 passed, 42 skipped, 13 errors`. Vẫn đúng 17 đỏ của bản 2026-11-20; lỗi collect thứ 13 là
`tests/unit/test_submit_quota_theo_ke_hoach.py` (đến từ commit d98443ea5), cũng thiếu `mongomock`.

Baseline ngày 2026-11-24, sau khi thêm 1.001766 khai tử có yếu tố nước ngoài + 1.000419 khai tử lưu động (máy local,
plugin win_socketpair, có PYTHONUTF8=1): `17 failed, 6161 passed, 42 skipped, 13 errors`. Vẫn đúng 17 đỏ của bản 2026-11-18;
lỗi collect thứ 13 là `tests/unit/test_submit_quota_theo_ke_hoach.py` (đến từ commit d98443ea5), cũng thiếu `mongomock`.

Baseline ngày 2026-11-20, sau khi thêm 1.001445 trình báo mất hộ chiếu cấp tỉnh (máy local, plugin win_socketpair, có
PYTHONUTF8=1): `17 failed, 5810 passed, 41 skipped, 12 errors` (gồm 3 test chặn tài khoản khác người thêm cùng ngày). Vẫn
đúng 17 đỏ của bản 2026-11-18; lỗi collect thứ 12 là
`tests/unit/test_role_bo_cong_an.py` (đến từ commit a753a9b4), cũng thiếu `mongomock`.

Baseline ngày 2026-11-18, sau khi kéo BE thai_dev d3a90fb6 (máy local, plugin win_socketpair, có PYTHONUTF8=1):
`17 failed, 5611 passed, 41 skipped, 11 errors`. 16 đỏ môi trường cũ + 1 đỏ
`tests/unit/test_khai_sinh_lien_thong_tach_trang.py::test_moc_trang_chi_nhan_moc_cua_dich_vu_ocr_o_moi_planner_tach` (glob trả
`\` trên Windows nên import module hỏng; chạy lại logic với `/` thì cả 46 planner tách đều đạt); lỗi collect thứ 11 là
`tests/unit/test_bien_ban_lam_viec.py`, thiếu `mongomock`.

Baseline ngày 2026-11-17, sau khi chuyển GPXD 1.013225 nhà ở riêng lẻ sang dòng 1/2/4 (máy local, plugin win_socketpair,
có PYTHONUTF8=1): `16 failed, 5369 passed, 41 skipped, 10 errors`. Vẫn đúng 16 đỏ môi trường của bản 2026-11-13; lỗi collect
thứ 10 là `tests/unit/test_partner_api_thong_ke.py` (đến từ commit 00926724), cũng thiếu `mongomock`.

Baseline ngày 2026-11-13, sau khi kéo BE thai_dev dab5931e1 (máy local, plugin win_socketpair, có PYTHONUTF8=1):
`16 failed, 4982 passed, 41 skipped, 9 errors`. Như bản 2026-11-12 cộng 1 đỏ
`tests/unit/test_dashboard_danh_muc_thu_tuc.py::test_xuat_excel_dung_dong_dang_loc_va_trong_pham_vi` (cùng lỗi `strftime` locale
Windows) và 2 lỗi collect thiếu `mongomock`: `tests/unit/test_second_pass.py`, `tests/unit/test_bao_cao_hang_ngay.py` (cài
`mongomock` tạm bằng `pip install --target <scratchpad>` rồi thêm vào PYTHONPATH thì hai file này pass; `test_bug_reports.py`
khi đó còn 7 đỏ 422 / 206 do fastapi + python-multipart local cũ).

Baseline ngày 2026-11-12, sau khi kéo BE thai_dev 0d6416f8 (máy local, plugin win_socketpair, có PYTHONUTF8=1):
`15 failed, 4672 passed, 41 skipped, 7 errors`. 13 đỏ môi trường như cũ (4 heic + 9 v2 422) + 2 đỏ
`tests/unit/test_dashboard_chon_nhieu_don_vi.py` (main thêm: `strftime` có chữ tiếng Việt vỡ locale trên Windows, trong Docker
chạy đúng); lỗi collect thứ 7 là `tests/unit/test_dossier_idle_va_cu_bam_trung.py`, cũng thiếu `mongomock`.

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
# Checklist chiều T3 20/10/2026 — Đợt 1, ngày 2 (thủ tục đã có, nhiều người dùng)

Mục tiêu chiều nay: **59 → 65 thủ tục** (+6) trên trợ lý.
Đổi so với [ke-hoach-100-thu-tuc-tro-ly.md](ke-hoach-100-thu-tuc-tro-ly.md): chọn theo lượt dùng thật, không theo thứ tự đợt.

Hiện tại: 12005 đang chạy bản **59 thủ tục** (thêm `khai-sinh-ket-hop-nhan-cha-me-con`, `dang-ky-nuoi-con-nuoi-trong-nuoc`, đã test lại xong), `/healthz` ok.
Code đang sửa chưa commit (`procedure_registry.py`, `flow.py`, `router.py`, mapper khai sinh kết hợp / nhận cha mẹ con, planner nuôi con nuôi…).

## Cách chọn

- Chỉ lấy thủ tục **đã có pipeline + entry** trong `app/procedures/registry.py` (extension Auto Fill đang chạy) nhưng **chưa có trong trợ lý**.
- Xếp theo `process_requests` trong Mongo local (27/07 → 20/10/2026): số lượt điền / số tài khoản khác nhau đã dùng.
  Ưu tiên thủ tục nhiều tài khoản cùng dùng; dùng 1 tài khoản thường chỉ là người test.
- Mongo local phần lớn là dữ liệu test, số liệu server thật (10.1.10.21) sẽ chính xác hơn.

Mỗi thủ tục bên trợ lý cần: entry trong `app/channels/handfree/procedure_registry.py`, gợi ý chọn thủ tục
(`procedure_picker/prompt.py`), tên tiếng Mông (`script_mong.py`).

## Tư pháp: đã hết thủ tục có pipeline

Cả 33 thủ tục Tư pháp có pipeline đều đã vào trợ lý. Còn 6 thủ tục Tư pháp **chưa có pipeline** (chưa ai dùng),
muốn làm phải đăng ký key mới trỏ vào pipeline anh em — để sau, xem phần cuối.

## Thủ tục còn phải làm chiều nay

### 1. `cap-cap-lai-phu-hieu-xe-kinh-doanh-van-tai` — Cấp, cấp lại phù hiệu xe ô tô kinh doanh vận tải (mã 2.002288) — 59 lượt / 3 tài khoản
Cổng DVC Bộ Xây dựng `dvc.moc.gov.vn` (Form.io `fillFormStandard` + attach `attp-row`), cùng cổng với liên vận Việt – Lào.
Pipeline: `cap_lai_phu_hieu_xe_oto`. URL SPA không mang mã → nhận theo cụm tên.
- [ ] Entry trong `procedure_registry.py`: chép khung từ `cap-giay-phep-lien-van-viet-lao` (cùng cổng, `flowProfile: "xay-dung"`).
- [ ] Gợi ý chọn thủ tục + tên tiếng Mông. Test pass, deploy 12005.
- [ ] Card hiện, nhận đúng trang.
- [ ] Chạy thử: điền đơn vị kinh doanh vận tải → thêm xe qua panel "Thêm phương tiện" → đính kèm → dừng trước nút Nộp.

### 2. `thanh-lap-cong-ty-tnhh-hai-thanh-vien` — Thành lập công ty TNHH hai thành viên trở lên — 56 lượt / 4 tài khoản
Cổng ĐKKD qua mạng `dangkyquamang.dkkd.gov.vn` (khác cổng hộ kinh doanh), wizard 3 bước. Pipeline: `thanh_lap_tnhh2`.
Trợ lý chưa có thủ tục nào trên cổng này → làm cùng #3. URL chỉ mang handle phiên → nhận diện theo domain + loại hình tick ở bước 2 (`LLC2`).
- [ ] Entry trong `procedure_registry.py`.
- [ ] Gợi ý chọn thủ tục + tên tiếng Mông. Test pass, deploy 12005.
- [ ] Card hiện, nhận đúng trang (phân biệt với công ty cổ phần cùng domain).
- [ ] Chạy thử: đi hết 3 bước wizard → đính kèm → dừng trước nút Nộp.

### 3. `thanh-lap-cong-ty-co-phan` — Thành lập công ty cổ phần — 19 lượt / 3 tài khoản
Cùng cổng, cùng wizard với #2, chỉ khác loại hình. Pipeline: `thanh_lap_ctcp`.
- [ ] Entry trong `procedure_registry.py`: chép từ #2, đổi loại hình.
- [ ] Gợi ý chọn thủ tục + tên tiếng Mông. Test pass, deploy 12005.
- [ ] Card hiện, nhận đúng trang.
- [ ] Chạy thử: đi hết 3 bước wizard → đính kèm → dừng trước nút Nộp.

### 4. `cap-the-huong-dan-vien-du-lich-noi-dia` — Cấp thẻ hướng dẫn viên du lịch nội địa (mã 1.004623) — 17 lượt / 3 tài khoản
Cổng Bộ VHTTDL (Angular Material `liz-*`, engine `fill-liz.js`), nộp về Sở VHTTDL. Form và bảng thành phần hồ sơ chung một trang.
Pipeline: `cap_the_hdv_noi_dia`. Trợ lý chưa có thủ tục nào trên cổng này.
- [ ] Entry trong `procedure_registry.py`; ghi lại trợ lý có gọi được engine `fill-liz.js` không.
- [ ] Gợi ý chọn thủ tục + tên tiếng Mông. Test pass, deploy 12005.
- [ ] Card hiện, nhận đúng trang.
- [ ] Chạy thử: điền → đính kèm (cùng trang) → dừng trước nút Nộp.

### 5. `dinh-chinh-gcn-da-cap-bac-ninh` — [Bắc Ninh] Đính chính GCN đã cấp (mã mới 1.115476) — 14 lượt / 2 tài khoản
Cổng `dichvucong.bacninh.gov.vn` (Liferay + select2, engine `fill-bacninh.js`). Pipeline: `dinh_chinh_gcn_da_cap_bac_ninh`.
Trợ lý đã chạy cổng này qua `dang-ky-bien-phap-bao-dam-bac-ninh`.
- [ ] Entry trong `procedure_registry.py`: chép khung từ `dang-ky-bien-phap-bao-dam-bac-ninh`, `detect` theo mã mới 1.115476 (cổng không còn phát 1.012790).
- [ ] Gợi ý chọn thủ tục + tên tiếng Mông. Test pass, deploy 12005.
- [ ] Card hiện, nhận đúng trang.
- [ ] Chạy thử: điền đơn Mẫu 18 + người nhận kết quả → đính kèm 4 nhóm → dừng trước nút Nộp.

### 6. `cap-doi-gcn-bac-ninh` — [Bắc Ninh] Cấp đổi GCN (mã mới 1.115464) — 9 lượt / 3 tài khoản
Cùng cổng, cùng đơn Mẫu 18 với #5. Pipeline: `cap_doi_gcn_bac_ninh`. Test lõi: `test_cap_doi_gcn_bac_ninh_attach.py`, `test_cap_doi_gcn_bac_ninh_nhan.py`.
- [ ] Entry trong `procedure_registry.py`: chép từ #5, `detect` theo mã mới 1.115464.
- [ ] Gợi ý chọn thủ tục + tên tiếng Mông. Test pass, deploy 12005.
- [ ] Card hiện, nhận đúng trang.
- [ ] Chạy thử: điền đơn Mẫu 18 + người nhận kết quả → đính kèm → dừng trước nút Nộp.

### Dự phòng (làm nếu xong sớm, theo thứ tự)

| Thủ tục | Lượt / TK | Cổng |
|---|---|---|
| `cap-lai-dieu-chinh-gcn-du-dieu-kien-kinh-doanh-duoc-so-y-te` (1.014104) | 13 / 2 | Bộ Y tế, Form.io, chọn Sở Y tế |
| `gia-han-chung-chi-hanh-nghe-thu-y` (2.001064) + `cap-lai-chung-chi-hanh-nghe-thu-y` (1.005319) | 12 / 2 + 23 / 1 | Form.io, chọn Sở NN&MT; cùng họ form, làm chung |
| `dang-ky-hanh-nghe` (1.012275) | 10 / 2 | Bộ Y tế, chọn Sở Y tế |
| `thong-bao-phat-trien-nguon-dien-mat-troi-mai-nha` (1.115377) | 10 / 2 | Một cửa Bộ Công Thương, Form.io |
| `cap-lai-the-huong-dan-vien-du-lich-da-nang` (1.004614) | 8 / 2 | Cùng cổng `liz-*` với #4 |

## Chạy thử còn nợ (đã có entry, chưa chạy trên cổng)

- [ ] `ho-tro-mai-tang-1116910`: nhận đúng trang, không nhầm sang 1.001731 (tên trùng nguyên văn) → chạy thử.
- [ ] 10 thủ tục có entry từ 19/10: `chung-thuc-di-chuc`, `cap-ban-sao-so-goc`, `bau-to-truong-to-hoa-giai`, `khai-tu-lien-thong` (còn đính kèm + 3 ô mai táng phí), `yeu-cau-tro-giup-phap-ly`, `xac-nhan-thong-tin-ho-tich`, `tam-ngung-kinh-doanh`, `cap-lai-cap-doi-gcn-ho-kinh-doanh`, `doi-cap-lai-giay-xac-nhan-khuyet-tat`, `thuc-hien-tro-cap-xa-hoi-nhan-cham-soc-nuoi-duong-hang-thang`.

## Mở đường cổng Đà Nẵng (chưa tính vào số đếm)

### `cap-doi-gcn-da-nang` — Cấp đổi GCN (Đà Nẵng)
Pipeline: `cap_doi_gcn_da_nang`. Test lõi: `test_cap_doi_gcn_da_nang_mapper.py`, `test_cap_doi_gcn_da_nang_attach.py`.
- [ ] Đăng nhập tài khoản test Hải Châu hoặc Liên Chiểu.
- [ ] Ghi lại: trợ lý vào được trang kê khai chưa, engine điền nào nhận form (`standard`?), bước đính kèm có chạy không.
- [ ] Ghi danh sách vấn đề cổng Đà Nẵng để xử lý trước Đợt 3 (27/10).

## Cuối buổi: test + deploy (một lần cho cả 6 thủ tục)

- [ ] Import registry không lỗi, đủ 65 thủ tục: `_validate_profile_dispatch()` chạy lúc import và báo ngay nếu thiếu pipeline.
- [ ] Test lõi: `python -m pytest tests/unit/test_cap_doi_gcn_bac_ninh_attach.py tests/unit/test_cap_doi_gcn_bac_ninh_nhan.py tests/unit/test_nhan_cha_me_con_mapper.py -q -p no:cacheprovider -p win_socketpair --tb=native`
- [ ] Test toàn bộ `tests/unit` + `tests/integration` (plugin `win_socketpair` + `PYTHONUTF8=1`): số fail không vượt baseline 15.
- [ ] `docker compose -f compose.prod.yml up -d --build --remove-orphans app`
- [ ] Container `Up`, `curl.exe -s http://localhost:12005/healthz` trả `{"ok":true}`.
- [ ] Stack toàn trình (cổng 12015) cũng chạy bản mới, nếu trợ lý đang trỏ vào đó.

## Kết quả cuối buổi

| Thủ tục | Lượt / TK | Entry | Nhận trang | Chạy thử | Ghi chú |
|---|---|---|---|---|---|
| cap-cap-lai-phu-hieu-xe-kinh-doanh-van-tai | 59 / 3 | ☐ | ☐ | ☐ | Cổng Bộ Xây dựng |
| thanh-lap-cong-ty-tnhh-hai-thanh-vien | 56 / 4 | ☐ | ☐ | ☐ | Cổng ĐKKD, mới với trợ lý |
| thanh-lap-cong-ty-co-phan | 19 / 3 | ☐ | ☐ | ☐ | Cổng ĐKKD |
| cap-the-huong-dan-vien-du-lich-noi-dia | 17 / 3 | ☐ | ☐ | ☐ | Cổng VHTTDL, mới với trợ lý |
| dinh-chinh-gcn-da-cap-bac-ninh | 14 / 2 | ☐ | ☐ | ☐ | Bắc Ninh |
| cap-doi-gcn-bac-ninh | 9 / 3 | ☐ | ☐ | ☐ | Bắc Ninh |
| cap-doi-gcn-da-nang (mở đường) | — | — | ☐ | ☐ | |

**Tổng chiều nay: 2 (khai sinh kết hợp, nuôi con nuôi) + ___ / 6 → lũy kế ___ / 100**

## Lùi xuống sau

- Tư pháp chưa có pipeline (chưa ai dùng, đăng ký key mới trỏ vào pipeline anh em):
  `cap-ban-sao-chung-thuc-tu-ban-chinh-hop-dong-giao-dich` (2.000942, anh em `cap_ban_sao_so_goc`),
  `cong-nhan-hoa-giai-vien` (1.002211, anh em `bau_to_truong_to_hoa_giai`),
  `khai-sinh-ket-hop-nhan-cha-me-con-nuoc-ngoai` (1.001695), `khai-tu-nuoc-ngoai` (1.001766),
  `thay-doi-cai-chinh-ho-tich-nuoc-ngoai` (2.000748), `ghi-so-ho-tich-ket-hon-nuoc-ngoai` (2.002189).
- Bảo trợ xã hội / người có công còn lại: `mai-tang-dan-cong-hoa-tuyen`, `cap-lai-to-quoc-ghi-cong`,
  `cap-bo-sung-cap-lai-giay-chung-nhan-nguoi-co-cong`, `bo-sung-than-nhan-liet-si`,
  `ho-tro-chi-phi-van-chuyen-nguoi-tu-vong-den-co-so-hoa-tang` (Đà Nẵng).

Thủ tục nào chiều nay chưa xong thì dồn sang T4 21/10.

> Dùng dữ liệu bịa khi chạy thử. Không nộp hồ sơ thật.

# Checklist sáng T3 20/10/2026 — Đợt 1, ngày 2 (ưu tiên Bộ Tư pháp)

Mục tiêu sáng nay: **54 → 61 thủ tục** (+7, toàn bộ là thủ tục Bộ Tư pháp).
Đổi so với [ke-hoach-100-thu-tuc-tro-ly.md](ke-hoach-100-thu-tuc-tro-ly.md): đẩy nhóm Tư pháp lên trước, nhóm bảo trợ xã hội / người có công lùi xuống chiều.

Trợ lý hiện đã có 28 thủ tục Tư pháp. Còn lại chia hai nhóm:
- **Nhóm A** (3): đã có pipeline + entry trong `app/procedures/registry.py`, chỉ thiếu entry bên trợ lý.
- **Nhóm B** (4): chưa có pipeline nhưng có thủ tục anh em cùng cổng đã chạy. Đăng ký key mới trỏ vào pipeline anh em
  (như `chung_thuc_chu_ky` đang phục vụ cả `chung-thuc-chu-ky` lẫn `chung-thuc-chu-ky-nguoi-dich-ctv`), không tạo pipeline mới.

Mỗi thủ tục bên trợ lý cần: entry trong `app/channels/handfree/procedure_registry.py`, gợi ý chọn thủ tục
(`procedure_picker/prompt.py`), tên tiếng Mông (`script_mong.py`).

## Đầu giờ

- [ ] Docker Desktop đã chạy lại (container 12005 `Up`). Kiểm bản đang chạy có đủ 54 thủ tục (commit "đẩy bản mới" f7bd021), chưa đủ thì deploy lại.

## Nhóm A — có pipeline, chỉ thêm entry trợ lý

### 1. `khai-sinh-ket-hop-nhan-cha-me-con` — Đăng ký khai sinh kết hợp nhận cha, mẹ, con (mã 1.000689)
Tạm bỏ qua hôm 19/10, nay đưa lại (22 lượt / 5 tài khoản trên Mongo local — dùng nhiều nhất trong nhóm Tư pháp còn thiếu).
Pipeline có sẵn, `detect.urlIncludes` `maThuTuc=1.000689`. Test lõi: `test_nhan_cha_me_con_mapper.py`.
- [ ] Entry trong `procedure_registry.py`: chép khung từ `dang-ky-nhan-cha-me-con` (`mode: "agent"`, `flowProfile: "tu-phap"`).
- [ ] Gợi ý chọn thủ tục + tên tiếng Mông. Không nhầm với `khai-sinh-dang-ky-thuong` và `dang-ky-nhan-cha-me-con`.
- [ ] Test pass, deploy 12005.
- [ ] Card hiện, nhận đúng trang.
- [ ] Chạy thử: chọn cơ quan → điền → đính kèm → dừng trước nút Nộp.
- [ ] Kiểm khối trẻ / người nhận cha-mẹ-con / người được nhận không bị tráo.

### 2. `dang-ky-nuoi-con-nuoi-trong-nuoc` — Đăng ký việc nuôi con nuôi trong nước (mã 2.001263)
Tạm bỏ qua hôm 19/10, nay đưa lại. Cổng DVCQG, tờ khai eForm hộ tịch "NCNV5" (`tokhaidientu.moj.gov.vn`). Pipeline: `dang_ky_nuoi_con_nuoi_trong_nuoc`. Chưa có file test riêng.
- [ ] Entry trong `procedure_registry.py`, `flowProfile: "tu-phap"`.
- [ ] Gợi ý chọn thủ tục + tên tiếng Mông. Test pass, deploy 12005.
- [ ] Card hiện, nhận đúng trang.
- [ ] Chạy thử: chọn cơ quan → điền eForm NCNV5 → đính kèm → dừng trước nút Nộp.
- [ ] Kiểm người nhận nuôi / trẻ được nhận nuôi / cha mẹ đẻ không bị tráo khối.

### 3. `cap-chung-chi-hanh-nghe-luat-su-mien-dao-tao-tap-su` — Cấp Chứng chỉ hành nghề luật sư (miễn đào tạo, miễn tập sự) (mã 1.000688)
Nộp tại Sở Tư pháp (`selectSo`). Wizard tư pháp DVCQG, bước Kê khai là eForm "Văn bản đề nghị…".
Pipeline: `cap_chung_chi_hanh_nghe_luat_su_mien_dao_tao_tap_su`. Test lõi: `test_cap_chung_chi_hanh_nghe_luat_su_mien_dao_tao_tap_su.py`.
- [x] Entry trong `procedure_registry.py`: chép khung từ `yeu-cau-tro-giup-phap-ly` (cùng kiểu chọn cơ quan cấp Sở: `agencyProvinceOnly` + `agencySoFirst` + `infoModalFields`), `flowProfile: "tu-phap"`.
- [x] Gợi ý chọn thủ tục + tên tiếng Mông. Test pass, deploy 12005.
- [x] Card hiện, nhận đúng trang.
- [x] Chạy thử: chọn Sở Tư pháp → điền eForm → đính kèm → dừng trước nút Nộp.

## Nhóm B — dùng lại pipeline anh em

Mỗi thủ tục: thêm key vào `app/procedures/registry.py` (detect + label + map process/attach sang pipeline anh em),
rồi thêm entry trợ lý như nhóm A. Chỉ sửa mapper của pipeline anh em khi form khác thật sự.

### 4. `chung-thuc-chu-ky-nguoi-dich-khong-ctv` — Chứng thực chữ ký người dịch không phải cộng tác viên (mã 2.001008)
Anh em: `chung-thuc-chu-ky-nguoi-dich-ctv` (attach, pipeline `chung_thuc_chu_ky`).
- [x] Đăng ký key trong `app/procedures/registry.py`, trỏ vào planner của bản CTV (`chung_thuc_chu_ky_nguoi_dich_ctv`), không dùng `chung_thuc_chu_ky`. Bản CTV vốn đã chạy planner này.
- [x] Entry trợ lý (`mode: "attach"`), chép từ `chung-thuc-chu-ky-nguoi-dich-ctv`. `requiredDocs` CHƯA thêm ô bằng cấp: planner xếp tệp theo thứ tự (tệp đầu vào dòng 1), không biết tệp thuộc ô nào; bằng cấp + giấy tùy thân người dịch ghi là xuất trình tại quầy.
- [x] Gợi ý chọn thủ tục + tên tiếng Mông (bản nháp). Không nhầm với bản cộng tác viên.
- [x] Test pass, deploy 12005.
- [x] Card hiện, nhận đúng trang. Chạy thử: chọn cơ quan → đính kèm → dừng trước nút Nộp.

### 5. `cap-ban-sao-chung-thuc-tu-ban-chinh-hop-dong-giao-dich` — Cấp bản sao có chứng thực từ bản chính hợp đồng, giao dịch đã chứng thực (mã 2.000942)
Anh em: `cap-ban-sao-so-goc`, `chung-thuc-giao-dich-tai-san` (đều attach).
- [ ] Đăng ký key trong `app/procedures/registry.py` trỏ vào pipeline `cap_ban_sao_so_goc`.
- [ ] Entry trợ lý (`mode: "attach"`), chép từ `cap-ban-sao-so-goc`.
- [ ] Gợi ý chọn thủ tục + tên tiếng Mông. Không nhầm với `cap-ban-sao-so-goc`, `chung-thuc-ban-sao`.
- [ ] Test pass, deploy 12005.
- [ ] Card hiện, nhận đúng trang. Chạy thử: chọn cơ quan → đính kèm → dừng trước nút Nộp.

### 6. `cong-nhan-hoa-giai-vien` — Công nhận hòa giải viên cấp xã (mã 1.002211)
Anh em: `bau-to-truong-to-hoa-giai` (attach, cùng bộ mẫu biên bản / đề nghị công nhận hòa giải viên).
- [ ] Đăng ký key trong `app/procedures/registry.py` trỏ vào `bau_to_truong_to_hoa_giai`.
- [ ] Entry trợ lý (`mode: "attach"`), chép từ `bau-to-truong-to-hoa-giai`, đổi `requiredDocs` (biên bản bầu hòa giải viên, danh sách đề nghị công nhận Mẫu 06).
- [ ] Gợi ý chọn thủ tục + tên tiếng Mông. Không nhầm với bầu tổ trưởng.
- [ ] Test pass, deploy 12005.
- [ ] Card hiện, nhận đúng trang. Chạy thử: chọn cơ quan → đính kèm → dừng trước nút Nộp.

### 7. `dang-ky-cham-dut-giam-ho` — Đăng ký chấm dứt giám hộ (mã 1.004845)
Anh em: `dang-ky-giam-ho` (agent, `flowProfile: "tu-phap"`, pipeline `dang_ky_giam_ho`).
- [x] Đăng ký key trong `app/procedures/registry.py` trỏ vào `dang_ky_giam_ho`; kiểm eForm chấm dứt giám hộ có thêm ô lý do chấm dứt → bổ sung vào mapper sẵn có nếu thiếu.
- [x] Entry trợ lý, chép từ `dang-ky-giam-ho`.
- [x] Gợi ý chọn thủ tục + tên tiếng Mông. Không nhầm với đăng ký giám hộ.
- [x] Test pass (`dang_ky_giam_ho`), deploy 12005.
- [ ] Card hiện, nhận đúng trang. Chạy thử: chọn cơ quan → điền → đính kèm → dừng trước nút Nộp.
- [ ] Kiểm người giám hộ / người được giám hộ không bị tráo khối.

## Mở đường cổng Đà Nẵng (chưa tính vào số đếm)

### `cap-doi-gcn-da-nang` — Cấp đổi GCN (Đà Nẵng)
Pipeline: `cap_doi_gcn_da_nang`. Test lõi: `test_cap_doi_gcn_da_nang_mapper.py`, `test_cap_doi_gcn_da_nang_attach.py`.
- [ ] Đăng nhập tài khoản test Hải Châu hoặc Liên Chiểu.
- [ ] Ghi lại: trợ lý vào được trang kê khai chưa, engine điền nào nhận form (`standard`?), bước đính kèm có chạy không.
- [ ] Ghi danh sách vấn đề cổng Đà Nẵng để xử lý trước Đợt 3 (27/10).

## Cuối buổi: test + deploy (một lần cho cả 7 thủ tục)

- [ ] Import registry không lỗi, đủ 61 thủ tục: `_validate_profile_dispatch()` chạy lúc import và báo ngay nếu thiếu pipeline.
- [ ] Test lõi: `python -m pytest tests/unit/test_cap_chung_chi_hanh_nghe_luat_su_mien_dao_tao_tap_su.py tests/unit/test_nhan_cha_me_con_mapper.py -q -p no:cacheprovider -p win_socketpair --tb=native`, cộng test của pipeline anh em nếu có sửa mapper.
- [ ] Test toàn bộ `tests/unit` + `tests/integration` (plugin `win_socketpair` + `PYTHONUTF8=1`): số fail không vượt baseline 15.
- [ ] `docker compose -f compose.prod.yml up -d --build --remove-orphans app`
- [ ] Container `Up`, `curl.exe -s http://localhost:12005/healthz` trả `{"ok":true}`.
- [ ] Stack toàn trình (cổng 12015) cũng chạy bản mới, nếu trợ lý đang trỏ vào đó.

## Kết quả cuối buổi

| Thủ tục | Nhóm | Entry | Nhận trang | Chạy thử | Ghi chú |
|---|---|---|---|---|---|
| khai-sinh-ket-hop-nhan-cha-me-con | A | ☐ | ☐ | ☐ | Bỏ qua 19/10, đưa lại |
| dang-ky-nuoi-con-nuoi-trong-nuoc | A | ☐ | ☐ | ☐ | Bỏ qua 19/10, đưa lại |
| cap-chung-chi-hanh-nghe-luat-su-mien-dao-tao-tap-su | A | ☑ | ☑ | ☑ | Chọn Sở Tư pháp |
| chung-thuc-chu-ky-nguoi-dich-khong-ctv | B | ☑ | ☑ | ☑ | Dùng planner bản CTV |
| cap-ban-sao-chung-thuc-tu-ban-chinh-hop-dong-giao-dich | B | ☐ | ☐ | ☐ | Dùng `cap_ban_sao_so_goc` |
| cong-nhan-hoa-giai-vien | B | ☐ | ☐ | ☐ | Dùng `bau_to_truong_to_hoa_giai` |
| dang-ky-cham-dut-giam-ho | B | ☐ | ☐ | ☐ | Dùng `dang_ky_giam_ho` |
| cap-doi-gcn-da-nang (mở đường) | — | — | ☐ | ☐ | |

**Tổng sáng nay: ___ / 7 → lũy kế ___ / 100**

Chiều 20/10:
- Tư pháp có yếu tố nước ngoài (chưa có pipeline, cần xem cổng trước): `khai-sinh-ket-hop-nhan-cha-me-con-nuoc-ngoai` (1.001695), `khai-tu-nuoc-ngoai` (1.001766), `thay-doi-cai-chinh-ho-tich-nuoc-ngoai` (2.000748), `ghi-so-ho-tich-ket-hon-nuoc-ngoai` (2.002189). Anh em gần nhất: `ket-hon-nuoc-ngoai`, `khai-tu`, `thay-doi-cai-chinh-ho-tich`.
- Bảo trợ xã hội / người có công lùi từ sáng: `ho-tro-mai-tang-1116910`, `mai-tang-dan-cong-hoa-tuyen`, `cap-lai-to-quoc-ghi-cong`, `cap-bo-sung-cap-lai-giay-chung-nhan-nguoi-co-cong`, `bo-sung-than-nhan-liet-si`, `ho-tro-chi-phi-van-chuyen-nguoi-tu-vong-den-co-so-hoa-tang` (Đà Nẵng).
- Chạy thử trên cổng 10 thủ tục đã có entry từ 19/10: `chung-thuc-di-chuc`, `cap-ban-sao-so-goc`, `bau-to-truong-to-hoa-giai`, `khai-tu-lien-thong`, `yeu-cau-tro-giup-phap-ly`, `xac-nhan-thong-tin-ho-tich`, `tam-ngung-kinh-doanh`, `cap-lai-cap-doi-gcn-ho-kinh-doanh`, `doi-cap-lai-giay-xac-nhan-khuyet-tat`, `thuc-hien-tro-cap-xa-hoi-nhan-cham-soc-nuoi-duong-hang-thang`.

> Dùng dữ liệu bịa khi chạy thử. Không nộp hồ sơ thật.

# Checklist chiều T2 19/10/2026 — Đợt 1, ngày 1

Mục tiêu chiều nay: **49 → 55 thủ tục** (+6), và **mở đường cổng Đà Nẵng**.
Theo [ke-hoach-100-thu-tuc-tro-ly.md](ke-hoach-100-thu-tuc-tro-ly.md), mục 3, Đợt 1 (kéo #8, #9 và #10–12 lên).

Cả 6 thủ tục đã có pipeline + entry trong `app/procedures/registry.py` (extension Auto Fill), chỉ thiếu entry bên trợ lý
(`app/channels/handfree/procedure_registry.py`), gợi ý chọn thủ tục (`procedure_picker/prompt.py`) và tên tiếng Mông (`script_mong.py`).

## Thủ tục phải xong chiều nay

### 1. `xac-nhan-thong-tin-ho-tich` — Xác nhận thông tin hộ tịch (mã 2.002516)
Profile `tu-phap`. Pipeline: `xac_nhan_thong_tin_ho_tich`. Test lõi: `test_xac_nhan_thong_tin_ho_tich.py`.
- [ ] Entry trong `procedure_registry.py`, đặt `flowProfile: "tu-phap"`, `detect.urlIncludes` theo `maThuTuc=2.002516`.
- [ ] Gợi ý chọn thủ tục + tên tiếng Mông. Test pass, deploy 12005.
- [ ] Card hiện, nhận đúng trang.
- [ ] Chạy thử: chọn cơ quan → điền → đính kèm → dừng trước nút Nộp.
- [ ] Kiểm hai bộ ô: trang cổng Form.io (`data[...]`) và eForm hộ tịch (`x-*`) trong iframe đều được điền, không bộ nào bị bỏ.

### 2. `tam-ngung-kinh-doanh` — Tạm ngừng kinh doanh hộ kinh doanh
Cùng engine HKD với `dang-ky-thay-doi-noi-dung-ho-kinh-doanh`, `cham-dut-hoat-dong-ho-kinh-doanh`. Pipeline: `tam_ngung_kinh_doanh`.
- [ ] Entry trong `procedure_registry.py`: chép khung từ `cham-dut-hoat-dong-ho-kinh-doanh`, đổi `detect`, label, các bước (`tam-ngung-hoat-dong`, `nguoi-nop-ho-so`), `requiredDocs`.
- [ ] Gợi ý chọn thủ tục + tên tiếng Mông. Test pass, deploy 12005.
- [ ] Card hiện, nhận đúng trang.
- [ ] Chạy thử: điền thời gian tạm ngừng + người nộp → đính kèm → dừng trước nút Nộp.

### 3. `cap-lai-cap-doi-gcn-ho-kinh-doanh` — Cấp lại / cấp đổi GCN đăng ký hộ kinh doanh
Cùng engine HKD. Pipeline: `cap_lai_cap_doi_gcn_ho_kinh_doanh`. Test lõi: `test_cap_lai_cap_doi_gcn_ho_kinh_doanh.py`.
- [ ] Entry trong `procedure_registry.py`: chép khung từ `cham-dut-hoat-dong-ho-kinh-doanh`, các bước `thong-tin-de-nghi-cap-lai`, `nguoi-nop-ho-so`.
- [ ] Gợi ý chọn thủ tục + tên tiếng Mông. Test pass, deploy 12005.
- [ ] Card hiện, nhận đúng trang.
- [ ] Chạy thử: điền thông tin đề nghị cấp lại + người nộp → đính kèm → dừng trước nút Nộp.

### 4. `doi-cap-lai-giay-xac-nhan-khuyet-tat` — Đổi, cấp lại Giấy xác nhận khuyết tật (mã 1.001653)
Nhóm bảo trợ xã hội. Pipeline: `doi_cap_lai_giay_xac_nhan_khuyet_tat`. Test lõi: `test_khuyet_tat_nguoi_nop.py`, `test_khuyet_tat_vision.py`.
- [ ] Entry trong `procedure_registry.py`, `detect.urlIncludes` theo `maThuTuc=1.001653`.
- [ ] Gợi ý chọn thủ tục + tên tiếng Mông. Test pass, deploy 12005.
- [ ] Card hiện, nhận đúng trang.
- [ ] Chạy thử: chọn cơ quan → điền → đính kèm → dừng trước nút Nộp.
- [ ] Kiểm người khuyết tật / người nộp hồ sơ không bị tráo khối.

### 5. `thuc-hien-tro-cap-xa-hoi-nhan-cham-soc-nuoi-duong-hang-thang` — Trợ cấp xã hội + nhận chăm sóc, nuôi dưỡng (mã 1.116909, NĐ 335)
Cổng Bộ Y tế `dichvucongbyt.moh.gov.vn`, Form.io (`fillFormStandard`) + bảng thành phần hồ sơ 2 dòng. Pipeline: `tcxh_nd335`.
URL SPA không mang mã → nhận theo cụm tên, cần `textPriority` để thắng rule chung của cổng.
- [ ] Entry trong `procedure_registry.py`: chép khung từ `tro-cap-xa-hoi-hang-thang`, đổi `detect` (cụm tên riêng, không đụng thủ tục cũ 1.001776).
- [ ] Gợi ý chọn thủ tục + tên tiếng Mông. Test pass, deploy 12005.
- [ ] Card hiện, nhận đúng trang (không nhầm sang `tro-cap-xa-hoi-hang-thang`).
- [ ] Chạy thử: điền → đính kèm 2 dòng → dừng trước nút Nộp.

### 6. `ho-tro-mai-tang-1116910` — [Ninh Bình] Hỗ trợ chi phí mai táng cho đối tượng bảo trợ xã hội (mã 1.116910)
Pipeline: `ho_tro_mai_tang`. Test lõi: `test_ho_tro_mai_tang_mapper.py`.
- [ ] Entry trong `procedure_registry.py`, `detect.urlIncludes` theo `maThuTuc=1.116910` + UUID `01a0f66e-63a3-749a-a9d8-2dcbeda6af79`.
- [ ] Gợi ý chọn thủ tục + tên tiếng Mông. Test pass, deploy 12005.
- [ ] Card hiện, nhận đúng trang.
- [ ] Chạy thử: chọn cơ quan → điền → đính kèm → dừng trước nút Nộp.
- [ ] Kiểm người chết / người lo mai táng không bị tráo khối.

## Tạm bỏ qua (đổi kế hoạch 19/10)

- `khai-sinh-ket-hop-nhan-cha-me-con` (1.000689)
- `dang-ky-nuoi-con-nuoi-trong-nuoc` (2.001263)

Chuyển xuống danh sách dự bị, làm lại khi có thời gian.

## Mở đường cổng Đà Nẵng (chưa tính vào số đếm)

### `cap-doi-gcn-da-nang` — Cấp đổi GCN (Đà Nẵng)
Pipeline: `cap_doi_gcn_da_nang`. Test lõi: `test_cap_doi_gcn_da_nang_mapper.py`, `test_cap_doi_gcn_da_nang_attach.py`.
- [ ] Đăng nhập tài khoản test Hải Châu hoặc Liên Chiểu.
- [ ] Ghi lại: trợ lý vào được trang kê khai chưa, engine điền nào nhận form (`standard`?), bước đính kèm có chạy không.
- [ ] Ghi danh sách vấn đề cổng Đà Nẵng để xử lý trước Đợt 3 (27/10).

## Cuối ngày: test + deploy (một lần cho cả 6 thủ tục)

- [ ] Import registry không lỗi, đủ 55 thủ tục: `_validate_profile_dispatch()` chạy lúc import và báo ngay nếu thiếu pipeline.
- [ ] Test lõi: `python -m pytest tests/unit/test_xac_nhan_thong_tin_ho_tich.py tests/unit/test_cap_lai_cap_doi_gcn_ho_kinh_doanh.py tests/unit/test_khuyet_tat_nguoi_nop.py tests/unit/test_khuyet_tat_vision.py tests/unit/test_ho_tro_mai_tang_mapper.py -q -p no:cacheprovider -p win_socketpair --tb=native`
- [ ] Test toàn bộ `tests/unit` + `tests/integration` (plugin `win_socketpair` + `PYTHONUTF8=1`): số fail không vượt baseline 15.
- [ ] `docker compose -f compose.prod.yml up -d --build --remove-orphans app`
- [ ] Container `Up`, `curl.exe -s http://localhost:12005/healthz` trả `{"ok":true}`.
- [ ] Stack toàn trình (cổng 12015) cũng chạy bản mới, nếu trợ lý đang trỏ vào đó.

## Kết quả cuối ngày

| Thủ tục | Entry | Nhận trang | Chạy thử | Ghi chú |
|---|---|---|---|---|
| xac-nhan-thong-tin-ho-tich | ☐ | ☐ | ☐ | |
| tam-ngung-kinh-doanh | ☐ | ☐ | ☐ | |
| cap-lai-cap-doi-gcn-ho-kinh-doanh | ☐ | ☐ | ☐ | |
| doi-cap-lai-giay-xac-nhan-khuyet-tat | ☐ | ☐ | ☐ | |
| thuc-hien-tro-cap-xa-hoi-nhan-cham-soc-nuoi-duong-hang-thang | ☐ | ☐ | ☐ | |
| ho-tro-mai-tang-1116910 | ☐ | ☐ | ☐ | |
| cap-doi-gcn-da-nang (mở đường) | — | ☐ | ☐ | |

**Tổng hôm nay: ___ / 6 → lũy kế ___ / 100**

Còn lại của Đợt 1 cho T3 20/10: bảo trợ xã hội / người có công #13–20 (`mai-tang-dan-cong-hoa-tuyen`, `ho-tro-chi-phi-van-chuyen-nguoi-tu-vong-den-co-so-hoa-tang`, `cap-lai-to-quoc-ghi-cong`, …), và chạy thử trên cổng 5 thủ tục có entry từ sáng (`chung-thuc-di-chuc`, `cap-ban-sao-so-goc`, `bau-to-truong-to-hoa-giai`, `khai-tu-lien-thong`, `yeu-cau-tro-giup-phap-ly`). Thủ tục nào hôm nay chưa xong thì dồn sang ngày mai.

> Dùng dữ liệu bịa khi chạy thử. Không nộp hồ sơ thật.

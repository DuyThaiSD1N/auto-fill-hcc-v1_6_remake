# Checklist T2 19/10/2026 — Đợt 1, ngày 1

Mục tiêu hôm nay: **44 → 50 thủ tục** (+6), và **mở đường cổng Đà Nẵng**.
Theo [ke-hoach-100-thu-tuc-tro-ly.md](ke-hoach-100-thu-tuc-tro-ly.md), mục 3, Đợt 1.

## Thủ tục phải xong hôm nay

### 1. `chung-thuc-di-chuc` — Chứng thực di chúc (mã 2.001019)
Chế độ attach. Pipeline: `chung_thuc_di_chuc.attach.planner`.
- [x] Entry trong `procedure_registry.py`: chép từ entry `chung-thuc-chu-ky`, đổi `detect`, label, `requiredDocs`, `uploadHint`.
- [x] Test backend pass, đã deploy 12005 (registry 45 thủ tục, có bộ phân loại tệp, gợi ý chọn thủ tục, tên tiếng Mông).
- [ ] Card hiện trên trợ lý, nhận đúng trang thủ tục.
- [ ] Chạy thử hồ sơ mẫu: chọn cơ quan → đính kèm → dừng trước nút Nộp.

### 2. `cap-ban-sao-so-goc` — Cấp bản sao từ sổ gốc (mã 2.000908)
Chế độ attach. Pipeline: `cap_ban_sao_so_goc.attach`.
- [x] Entry trong `procedure_registry.py` (registry 46 thủ tục, dùng bộ phân loại chung, gợi ý chọn thủ tục, tên tiếng Mông). Test pass, đã deploy 12005.
- [ ] Card hiện, nhận đúng trang.
- [ ] Chạy thử: chọn cơ quan → đính kèm → dừng trước nút Nộp.

### 3. `bau-to-truong-to-hoa-giai` — Bầu tổ trưởng tổ hòa giải (mã 2.000950)
Chế độ attach. Pipeline: `bau_to_truong_to_hoa_giai.attach.planner`.
- [x] Entry trong `procedure_registry.py` (registry 47 thủ tục, dùng bộ phân loại chung hỏi LLM theo tên ô, gợi ý chọn thủ tục, tên tiếng Mông). Test pass, đã deploy 12005.
- [ ] Card hiện, nhận đúng trang.
- [ ] Chạy thử: chọn cơ quan → đính kèm → dừng trước nút Nộp.

### 4. `khai-tu-lien-thong` — Liên thông khai tử, xóa thường trú, trợ cấp mai táng (mã 1.006714)
Cổng liên thông Angular (`lienthong.dichvucong.gov.vn/#/ke-khai/1.006714`), cùng cổng với `khai-sinh-dang-ky`.
Pipeline: `khai_tu_lien_thong`. Test lõi: `test_khai_tu_lien_thong.py`. Kéo từ ngày 20/10 lên, thay 1.000689.
- [x] Entry trong `procedure_registry.py`: chép khung từ `khai-sinh-dang-ky` (`mode: "agent"`, `hasAttachmentStep`, `agencyFillPlan` nếu cần), `detect.urlIncludes` theo link 1.006714. Chưa có `agencyFillPlan` (chọn cơ quan bằng tay). Có gợi ý chọn thủ tục + tên tiếng Mông. Test pass, đã deploy 12005.
- [x] Card hiện, nhận đúng trang (req_19aba7fa2d10: chọn đúng thủ tục, báo "Đã vào trang kê khai").
- [ ] Chạy thử: chọn cơ quan → điền form Angular → đính kèm → dừng trước nút Nộp.
  - req_19aba7fa2d10: chọn cơ quan bằng tay ✓, điền **23/26 ô** ✓. Đính kèm **chưa chạy**: hội thoại dừng ở `waiting_attachment_page`, không có req đính kèm nào.
- [ ] Kiểm người chết / người đi khai không bị tráo khối; khối xóa thường trú và mai táng phí có dữ liệu.
  - Không tráo ✓: khối người được khai tử lấy đúng CCCD người chết (khớp giấy báo tử), không lấy CCCD người đi khai.
  - Xóa thường trú ✓: họ tên + giấy tờ chủ hộ chép từ khối người yêu cầu, có quan hệ.
  - Mai táng phí ✗: 3 ô không tìm thấy trên trang (`CanhanIsNyc`, `NnmtpQqMaQuocgia`, `NccQqMaQuocgia`). Có thể khối này chỉ hiện sau khi cán bộ chọn chế độ mai táng. Trợ lý đang báo nguyên tên kỹ thuật 3 ô này cho người dân.

### 5. `yeu-cau-tro-giup-phap-ly` — Yêu cầu trợ giúp pháp lý (mã 2.000829)
Qua Cổng DVC (`019d2bfd-8e3d-737e-8aca-295dd1f2ea9f`), `needsAgencySelect` + `selectSo` (chọn Sở Tư pháp).
Pipeline: `yeu_cau_tro_giup_phap_ly`. Test lõi: `test_yeu_cau_tro_giup_phap_ly.py`. Thay 2.001263.
- [x] Entry trong `procedure_registry.py`: nhận diện theo UUID / mã 2.000829 + cụm "Thủ tục yêu cầu trợ giúp pháp lý".
- [ ] Card hiện, nhận đúng trang.
- [ ] Chạy thử: chọn Sở Tư pháp → điền → đính kèm → dừng trước nút Nộp.
- [ ] Ghi lại cổng đích sau bước chọn cơ quan dùng engine điền nào (chưa từng chạy trên trợ lý).

### 6. `xac-nhan-thong-tin-ho-tich` — Xác nhận thông tin hộ tịch (mã 2.002516)
Profile `tu-phap`. Pipeline: `xac_nhan_thong_tin_ho_tich`. Test lõi: `test_xac_nhan_thong_tin_ho_tich.py`.
Kéo từ ngày 20/10 lên để đủ 50.
- [ ] Entry trong `procedure_registry.py`, đặt `flowProfile: "tu-phap"`.
- [ ] Card hiện, nhận đúng trang.
- [ ] Chạy thử: chọn cơ quan → điền → đính kèm → dừng trước nút Nộp.
- [ ] Kiểm hai bộ ô: trang cổng Form.io (`data[...]`) và eForm hộ tịch (`x-*`) trong iframe đều được điền, không bộ nào bị bỏ.

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

- [ ] Import registry không lỗi: `_validate_profile_dispatch()` chạy lúc import và báo ngay nếu thiếu pipeline.
- [ ] Test lõi: `python -m pytest tests/unit/test_khai_tu_lien_thong.py tests/unit/test_yeu_cau_tro_giup_phap_ly.py tests/unit/test_xac_nhan_thong_tin_ho_tich.py -q -p no:cacheprovider`
- [ ] Test toàn bộ `tests/unit` + `tests/integration` (plugin `win_socketpair` + `PYTHONUTF8=1`): số fail không vượt baseline 15.
- [ ] `docker compose -f compose.prod.yml up -d --build --remove-orphans app`
- [ ] Container `Up`, `curl.exe -s http://localhost:12005/healthz` trả `{"ok":true}`.
- [ ] Stack toàn trình (cổng 12015) cũng chạy bản mới, nếu trợ lý đang trỏ vào đó.

## Kết quả cuối ngày

| Thủ tục | Entry | Nhận trang | Chạy thử | Ghi chú |
|---|---|---|---|---|
| chung-thuc-di-chuc | ☑ | ☐ | ☐ | Backend test pass + deploy 12005; chờ chạy thử trên cổng |
| cap-ban-sao-so-goc | ☑ | ☐ | ☐ | Backend test pass + deploy 12005; chờ chạy thử trên cổng |
| bau-to-truong-to-hoa-giai | ☑ | ☐ | ☐ | Backend test pass + deploy 12005; chờ chạy thử trên cổng |
| khai-tu-lien-thong | ☑ | ☑ | ☐ | Thay 1.000689. Điền 23/26 (3 ô mai táng phí không thấy trên trang); chưa chạy đính kèm |
| yeu-cau-tro-giup-phap-ly | ☐ | ☐ | ☐ | Thay 2.001263 |
| xac-nhan-thong-tin-ho-tich | ☐ | ☐ | ☐ | |
| cap-doi-gcn-da-nang (mở đường) | — | ☐ | ☐ | |

**Tổng hôm nay: ___ / 6 → lũy kế ___ / 100**

Còn lại của Đợt 1 cho T3 20/10: `tam-ngung-kinh-doanh`, `cap-lai-cap-doi-gcn-ho-kinh-doanh`, cộng thêm thủ tục bảo trợ xã hội / người có công kéo lên từ 21/10 cho đủ nhịp. Thủ tục nào hôm nay chưa xong thì dồn sang ngày mai.

> Dùng dữ liệu bịa khi chạy thử. Không nộp hồ sơ thật.

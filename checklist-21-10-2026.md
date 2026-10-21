# Checklist sáng T4 21/10/2026 — Đợt 1, ngày 3

Mục tiêu sáng nay: **57 → 64 thủ tục** trên trợ lý (khôi phục 2 + thêm 5 mới). Đạt luôn mốc 64 của T5 22/10 trong
[ke-hoach-100-thu-tuc-tro-ly.md](ke-hoach-100-thu-tuc-tro-ly.md).

## Hiện trạng lúc 09:40

- Trợ lý (`app/channels/handfree/procedure_registry.py`) còn **57 thủ tục**, không phải 59 như cuối buổi hôm qua.
- Lý do: bản BE dán vào lúc 08:50 (commit `a63ba04 update BE mới`) đã gỡ hết phần sửa hôm qua cho
  `khai-sinh-ket-hop-nhan-cha-me-con` và `dang-ky-nuoi-con-nuoi-trong-nuoc`. Bị gỡ ở: entry trong `procedure_registry.py`
  (93 dòng), `chat/flow.py` (203 dòng), `chat/router.py`, `procedure_picker/prompt.py`, `script_mong.py`,
  mapper `nhan_cha_me_con` / `khai_sinh_ket_hop_nhan_cmc` và test đi kèm. Pipeline lõi của hai thủ tục vẫn còn.
- Bản dán đó cũng bỏ thủ tục lõi `dang-ky-bien-dong-thoa-thuan-bac-ninh` (1.115470) khỏi `app/procedures/registry.py`,
  nên lõi còn 221 thủ tục.
- Cả 6 thủ tục trong checklist chiều 20/10 đều **chưa vào trợ lý**.
- Kiểm tra lại 12005 đang chạy bản nào: nếu đã build sau `a63ba04` thì người dùng đang chỉ thấy 57 card.

## Tổng hợp theo bộ (lõi 221 thủ tục có entry, trợ lý 57)

Phân bộ theo cơ cấu sau sắp xếp 2025: người có công, hưu trí xã hội về Nội vụ; bảo trợ xã hội về Y tế;
giáo dục nghề nghiệp về GD&ĐT; đăng ký kinh doanh, đầu tư về Tài chính; xuất bản, trò chơi điện tử về VHTTDL.

| Bộ | Lõi | Trợ lý | Còn | Đã có trên trợ lý | Còn lại (lượt / số tài khoản cao nhất) |
|---|---:|---:|---:|---|---|
| Tư pháp | 42 | 32 | 10 | Hộ tịch 17, chứng thực 9, bản sao sổ gốc, tổ hòa giải, trợ giúp pháp lý, CCHN luật sư, biện pháp bảo đảm Bắc Ninh 2 | **Khai sinh kết hợp nhận CMC 36/6** và **nuôi con nuôi 11/3** (bị gỡ sáng nay); 8 biện pháp bảo đảm Đà Nẵng / Lào Cai / Quảng Ninh (cổng chưa mở) |
| Nông nghiệp & Môi trường | 87 | 1 | 86 | Giấy phép khai thác thủy sản | Đất đai Bắc Ninh 9 (đính chính GCN 14/2, cấp đổi 9/3, tách hợp thửa 9/1, đăng ký lần đầu 6/1), Lào Cai ~32, Đà Nẵng ~15, Quảng Ninh ~13, Ninh Bình 6, Quảng Ngãi 6, Lâm Đồng 4, Lai Châu 3; thú y 2 (gia hạn 12/2, cấp lại 23/1); tàu cá 3; ATTP nông lâm thủy sản; dịch bệnh động vật |
| Xây dựng | 25 | 7 | 18 | GPXD mới / điều chỉnh / sửa chữa nhà ở, thông tin quy hoạch, lòng đường vỉa hè, nhà ở xã hội, liên vận Việt – Lào | **Phù hiệu xe 59/3**, chặt hạ cây xanh 6/2, xác nhận diện tích nhà ở 5/1, gia hạn GPXD 3/1, xe tập lái 3/1; còn lại 0 lượt: sửa chữa GPXD công trình, đấu nối tạm, GCNKNCM, lưu hành xe Lào, thẩm định BCNCKT, nước sạch 2, số nhà Đà Nẵng 2, phương tiện thủy 2, môi giới BĐS, NOXH Bắc Ninh |
| Y tế | 21 | 6 | 15 | Khuyết tật 2, mai táng BTXH 1.116910, trợ cấp xã hội 2, ATTP dịch vụ ăn uống | **Dược Sở Y tế 13/2**, **đăng ký hành nghề 10/2**, GPHN chuyển tiếp 2 (9/1, 3/1), GPHĐ KCB 3/2, tiêm chủng 4/1, mai táng 1.001731 4/1, CCHN dược, hỏa táng 3 (Bắc Ninh, Quảng Ngãi, vận chuyển), người cao tuổi Bắc Ninh, cấp lại ATTP |
| Nội vụ | 21 | 5 | 16 | Hưu trí xã hội 2, thờ cúng liệt sĩ, NCC từ trần, di chuyển hồ sơ ưu đãi | GCN người có công 5/1, kháng chiến 2/1, Tổ quốc ghi công, thân nhân liệt sĩ, thăm viếng mộ, sửa thông tin NCC, mai táng dân công; công chức / viên chức 5 và hội 3 (không phải người dân); nội quy lao động 4/1 |
| Tài chính | 10 | 5 | 5 | Hộ kinh doanh 5 | Công ty TNHH 2 TV 56/4, cổ phần 19/3 (cổng ĐKKD mới với trợ lý); chủ trương đầu tư Lào Cai 3 |
| Văn hóa, TT&DL | 7 | 0 | 7 | — | HDV nội địa 17/3, HDV Đà Nẵng 3 (8/2, 8/1, 2/1), băng-rôn 22/1 (cần `fill-liz.js`), trò chơi điện tử, xuất bản |
| Công Thương | 4 | 0 | 4 | — | Điện mặt trời mái nhà 10/2, khuyến mại 2, ATTP công thương |
| Giáo dục & ĐT | 3 | 1 | 2 | Bản sao văn bằng từ sổ gốc | Miễn giảm học phí GDNN 5/1, hỗ trợ học tập Bắc Ninh |
| Tiện ích | 1 | 0 | 1 | — | `dien-thong-tin-tai-khoan-bac-ninh` (không phải TTHC) |

Lượt / tài khoản lấy từ `process_requests` Mongo local (đến sáng 21/10), phần lớn là dữ liệu test.

## Kế hoạch sáng nay

Thứ tự ưu tiên: (1) khôi phục cái đã mất, (2) cổng trợ lý đã chạy được, (3) nhiều tài khoản dùng.
Phù hiệu xe, công ty, HDV du lịch dời sang chiều vì cần engine hoặc cổng mới (`dom-editgrid`, ĐKKD, `fill-liz.js`).

### 09:45–10:20 · Tư pháp: khôi phục 2 thủ tục bị gỡ (57 → 59)

- [ ] Hỏi người dán bản BE: bỏ `dang-ky-bien-dong-thoa-thuan-bac-ninh` và phần mapper nhận cha mẹ con là cố ý hay sót?
- [ ] Lấy lại phần đã gỡ ở 5 file handfree (`procedure_registry.py`, `flow.py`, `router.py`, `procedure_picker/prompt.py`,
      `script_mong.py`). So bản `af8d854` với hiện tại bằng `git show af8d854:<file>` ra file tạm, chép tay từng đoạn.
      Không dùng `git stash`, không checkout cả file (bản mới có sửa khác cần giữ), không để lại gì trong index.
- [ ] Mapper `nhan_cha_me_con` / `khai_sinh_ket_hop_nhan_cmc` + test: chỉ lấy lại nếu người dán xác nhận là sót.
- [ ] `python -m pytest tests/unit/test_nhan_cha_me_con_mapper.py tests/handfree/unit/test_flow_profiles.py -q -p no:cacheprovider`
- [ ] Card hiện, nhận đúng trang (1.000689; nuôi con nuôi theo cụm tên).

### 10:20–11:10 · Nông nghiệp & MT: cụm đất đai Bắc Ninh (59 → 63)

Cổng `dichvucong.bacninh.gov.vn` (Liferay eForm, `fill-bacninh.js`) trợ lý đã chạy qua `dang-ky-bien-phap-bao-dam-bac-ninh`.
Chép khung entry đó: `provinceOnly: ["bacninh"]`, `agencySoFirst`, `samePageAttach`. Key trùng lõi, process/attach tự nối.

| # | Key | Mã trên URL | Lượt / TK |
|---|---|---|---|
| 1 | `dinh-chinh-gcn-da-cap-bac-ninh` | 1.115436, 1.115476 | 14 / 2 |
| 2 | `cap-doi-gcn-bac-ninh` | 1.115464 | 9 / 3 |
| 3 | `tach-hop-thua-dat-bac-ninh` | 1.115458 | 9 / 1 |
| 4 | `dang-ky-dat-dai-lan-dau-bac-ninh` | 1.115443 | 6 / 1 |

Mỗi thủ tục:
- [ ] Entry trong `procedure_registry.py` (`detect` theo mã ở bảng), `requiredDocs` + `uploadHint` lấy từ entry lõi.
- [ ] Gợi ý chọn thủ tục (`procedure_picker/prompt.py`) + tên tiếng Mông (`script_mong.py`).
- [ ] Card chỉ hiện với tài khoản Bắc Ninh (`hiephoabn`), nhận đúng trang.

Test lõi: `test_cap_doi_gcn_bac_ninh_attach.py`, `test_cap_doi_gcn_bac_ninh_nhan.py`.

### 11:10–11:30 · Xây dựng: chặt hạ cây xanh (63 → 64)

- [ ] `cap-giay-phep-chat-ha-cay-xanh` (6 / 2): cổng `dvc.moc.gov.vn`, chép khung từ `cap-giay-phep-lien-van-viet-lao`
      (`flowProfile: "xay-dung"`), nhận theo cụm tên "cấp giấy phép chặt hạ, dịch chuyển cây xanh".
- [ ] Gợi ý chọn thủ tục + tên tiếng Mông. Card hiện, nhận đúng trang.

### 11:30–12:00 · Test + deploy một lần cho cả 7

- [ ] Import registry không lỗi, đủ 64 thủ tục (`_validate_profile_dispatch()` báo ngay nếu thiếu pipeline).
- [ ] Test toàn bộ `tests/unit` + `tests/integration` (plugin `win_socketpair` + `PYTHONUTF8=1`): số fail không vượt baseline 15.
- [ ] `docker compose -f compose.prod.yml up -d --build --remove-orphans app`
- [ ] Container `Up`, `curl.exe -s http://localhost:12005/healthz` trả `{"ok":true}`.
- [ ] Stack toàn trình (12015) cũng lên bản mới nếu trợ lý đang trỏ vào đó.

### Dự phòng nếu xong sớm (theo thứ tự)

| Bộ | Thủ tục | Lượt / TK | Ghi chú |
|---|---|---|---|
| Y tế | `cap-lai-dieu-chinh-gcn-du-dieu-kien-kinh-doanh-duoc-so-y-te` | 13 / 2 | DVCQG Form.io, chọn Sở Y tế; trợ lý đã chạy ATTP Y tế |
| Y tế | `dang-ky-hanh-nghe` (1.012275) | 10 / 2 | Chọn Sở Y tế |
| Nội vụ | `cap-bo-sung-cap-lai-giay-chung-nhan-nguoi-co-cong` | 5 / 1 | Cùng nhóm với thờ cúng liệt sĩ, NCC từ trần |
| Nội vụ | `giai-quyet-che-do-khang-chien` | 2 / 1 | Cùng nhóm người có công |

## Dồn sang chiều

- Chạy thử trên cổng (dừng trước nút Nộp, dữ liệu bịa) cho 7 thủ tục sáng nay.
- Từ checklist 20/10: phù hiệu xe (cần `dom-editgrid`), công ty TNHH 2 TV + cổ phần (cổng ĐKKD), HDV nội địa (`fill-liz.js`).
- Chạy thử còn nợ: `ho-tro-mai-tang-1116910` và 10 thủ tục có entry từ 19/10.
- Mở đường cổng Đà Nẵng bằng `cap-doi-gcn-da-nang` trước Đợt 3 (27/10).

## Kết quả cuối buổi

| Bộ | Thủ tục | Entry | Nhận trang | Chạy thử | Ghi chú |
|---|---|---|---|---|---|
| Tư pháp | khai-sinh-ket-hop-nhan-cha-me-con | ☐ | ☐ | ☐ | Khôi phục |
| Tư pháp | dang-ky-nuoi-con-nuoi-trong-nuoc | ☐ | ☐ | ☐ | Khôi phục |
| NN&MT | dinh-chinh-gcn-da-cap-bac-ninh | ☐ | ☐ | ☐ | |
| NN&MT | cap-doi-gcn-bac-ninh | ☐ | ☐ | ☐ | |
| NN&MT | tach-hop-thua-dat-bac-ninh | ☐ | ☐ | ☐ | |
| NN&MT | dang-ky-dat-dai-lan-dau-bac-ninh | ☐ | ☐ | ☐ | |
| Xây dựng | cap-giay-phep-chat-ha-cay-xanh | ☐ | ☐ | ☐ | |

**Tổng sáng nay: ___ / 7 → lũy kế ___ / 100**

> Dùng dữ liệu bịa khi chạy thử. Không nộp hồ sơ thật.

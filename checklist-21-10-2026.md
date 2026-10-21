# Checklist sáng T4 21/10/2026 — Đợt 1, ngày 3

Mục tiêu sáng nay: **59 → 66 thủ tục** trên trợ lý (+7). Vượt mốc 64 của T5 22/10 trong
[ke-hoach-100-thu-tuc-tro-ly.md](ke-hoach-100-thu-tuc-tro-ly.md).

## Hiện trạng lúc 09:55

- Bản BE `5792794 update lại bE` đã có lại `khai-sinh-ket-hop-nhan-cha-me-con`, `dang-ky-nuoi-con-nuoi-trong-nuoc`
  (trợ lý) và `dang-ky-bien-dong-thoa-thuan-bac-ninh` (lõi). Trợ lý **59**, lõi **222**.
- 12005 đã chạy bản này: test toàn bộ `11 failed, 2914 passed, 39 skipped, 3 errors` (11 đỏ đều do môi trường),
  container `Up`, `/healthz` ok.
- Stack toàn trình 12015 vẫn chạy image `:dev-toan-trinh` cũ.
- Cả 6 thủ tục trong checklist chiều 20/10 đều **chưa vào trợ lý**.

## Tổng hợp theo bộ (lõi 222, trợ lý 59)

Phân bộ theo cơ cấu sau sắp xếp 2025: người có công, hưu trí xã hội về Nội vụ; bảo trợ xã hội về Y tế;
giáo dục nghề nghiệp về GD&ĐT; đăng ký kinh doanh, đầu tư về Tài chính; xuất bản, trò chơi điện tử về VHTTDL.

| Bộ | Lõi | Trợ lý | Còn | Đã có trên trợ lý | Còn lại (lượt / số tài khoản) |
|---|---:|---:|---:|---|---|
| Tư pháp | 42 | 34 | 8 | Hộ tịch 19 (có khai sinh kết hợp nhận CMC, nuôi con nuôi), chứng thực 9, bản sao sổ gốc, tổ hòa giải, trợ giúp pháp lý, CCHN luật sư, biện pháp bảo đảm Bắc Ninh 2 | 8 biện pháp bảo đảm Đà Nẵng / Lào Cai / Quảng Ninh (cổng chưa mở) |
| Nông nghiệp & Môi trường | 88 | 1 | 87 | Giấy phép khai thác thủy sản | Đất đai Bắc Ninh 10 (đính chính GCN 14/2, cấp đổi 9/3, tách hợp thửa 9/1, đăng ký lần đầu 6/1, thu hồi GCN 5/1…), Lào Cai ~32, Đà Nẵng ~15, Quảng Ninh ~13, Ninh Bình 6, Quảng Ngãi 6, Lâm Đồng 4, Lai Châu 3; thú y 2 (gia hạn 12/2, cấp lại 23/1); tàu cá 3; ATTP nông lâm thủy sản; dịch bệnh động vật |
| Xây dựng | 25 | 7 | 18 | GPXD mới / điều chỉnh / sửa chữa nhà ở, thông tin quy hoạch, lòng đường vỉa hè, nhà ở xã hội, liên vận Việt – Lào | **Phù hiệu xe 59/3**, chặt hạ cây xanh 6/2, xác nhận diện tích nhà ở 5/1, gia hạn GPXD 3/1, xe tập lái 3/1; 0 lượt: sửa chữa GPXD công trình, đấu nối tạm, GCNKNCM, lưu hành xe Lào, thẩm định BCNCKT, nước sạch 2, số nhà Đà Nẵng 2, phương tiện thủy 2, môi giới BĐS, NOXH Bắc Ninh |
| Y tế | 21 | 6 | 15 | Khuyết tật 2, mai táng BTXH 1.116910, trợ cấp xã hội 2, ATTP dịch vụ ăn uống | **Dược Sở Y tế 13/2**, **đăng ký hành nghề 10/2**, GPHN chuyển tiếp 2 (9/1, 3/1), GPHĐ KCB 3/2, tiêm chủng 4/1, mai táng 1.001731 4/1, CCHN dược, hỏa táng 3, người cao tuổi Bắc Ninh, cấp lại ATTP |
| Nội vụ | 21 | 5 | 16 | Hưu trí xã hội 2, thờ cúng liệt sĩ, NCC từ trần, di chuyển hồ sơ ưu đãi | GCN người có công 5/1, kháng chiến 2/1, Tổ quốc ghi công, thân nhân liệt sĩ, thăm viếng mộ, sửa thông tin NCC, mai táng dân công; công chức / viên chức 5 và hội 3 (không phải người dân); nội quy lao động 4/1 |
| Tài chính | 10 | 5 | 5 | Hộ kinh doanh 5 | Công ty TNHH 2 TV 56/4, cổ phần 19/3 (cổng ĐKKD mới với trợ lý); chủ trương đầu tư Lào Cai 3 |
| Văn hóa, TT&DL | 7 | 0 | 7 | — | HDV nội địa 17/3, HDV Đà Nẵng 3 (8/2, 8/1, 2/1), băng-rôn 22/1 (cần `fill-liz.js`), trò chơi điện tử, xuất bản |
| Công Thương | 4 | 0 | 4 | — | Điện mặt trời mái nhà 10/2, khuyến mại 2, ATTP công thương |
| Giáo dục & ĐT | 3 | 1 | 2 | Bản sao văn bằng từ sổ gốc | Miễn giảm học phí GDNN 5/1, hỗ trợ học tập Bắc Ninh |
| Tiện ích | 1 | 0 | 1 | — | `dien-thong-tin-tai-khoan-bac-ninh` (không phải TTHC) |

Lượt / tài khoản lấy từ `process_requests` Mongo local (đến sáng 21/10), phần lớn là dữ liệu test.

## Kế hoạch sáng nay

Thứ tự ưu tiên: (1) cổng trợ lý đã chạy được, (2) nhiều tài khoản dùng.
Phù hiệu xe, công ty, HDV du lịch dời sang chiều vì cần engine hoặc cổng mới (`dom-editgrid`, ĐKKD, `fill-liz.js`).

Mỗi thủ tục cần: entry trong `app/channels/handfree/procedure_registry.py`, gợi ý chọn thủ tục
(`procedure_picker/prompt.py`), tên tiếng Mông (`script_mong.py`). Không tạo file mới.

### 10:00–11:00 · Nông nghiệp & MT: cụm đất đai Bắc Ninh (59 → 63)

Cổng `dichvucong.bacninh.gov.vn` (Liferay eForm, `fill-bacninh.js`) trợ lý đã chạy qua `dang-ky-bien-phap-bao-dam-bac-ninh`.
Chép khung entry đó: `provinceOnly: ["bacninh"]`, `agencySoFirst`, `samePageAttach`. Key trùng lõi, process/attach tự nối.

| # | Key | Mã trên URL | Lượt / TK |
|---|---|---|---|
| 1 | `dinh-chinh-gcn-da-cap-bac-ninh` | 1.115436, 1.115476 | 14 / 2 |
| 2 | `cap-doi-gcn-bac-ninh` | 1.115464 | 9 / 3 |
| 3 | `tach-hop-thua-dat-bac-ninh` | 1.115458 | 9 / 1 |
| 4 | `dang-ky-dat-dai-lan-dau-bac-ninh` | 1.115443 | 6 / 1 |

Mỗi thủ tục:
- [ ] Entry (`detect` theo mã ở bảng), `requiredDocs` + `uploadHint` lấy từ entry lõi.
- [ ] Gợi ý chọn thủ tục + tên tiếng Mông.
- [ ] Card chỉ hiện với tài khoản Bắc Ninh (`hiephoabn`), nhận đúng trang.

Test lõi: `test_cap_doi_gcn_bac_ninh_attach.py`, `test_cap_doi_gcn_bac_ninh_nhan.py`.

### 11:00–11:20 · Xây dựng: chặt hạ cây xanh (63 → 64)

- [ ] `cap-giay-phep-chat-ha-cay-xanh` (6 / 2): cổng `dvc.moc.gov.vn`, chép khung từ `cap-giay-phep-lien-van-viet-lao`
      (`flowProfile: "xay-dung"`), nhận theo cụm tên "cấp giấy phép chặt hạ, dịch chuyển cây xanh".
- [ ] Gợi ý chọn thủ tục + tên tiếng Mông. Card hiện, nhận đúng trang.

### 11:20–11:40 · Y tế: dược + đăng ký hành nghề (64 → 66)

Cổng DVCQG Form.io, chọn Sở Y tế. Trợ lý đã chạy ATTP dịch vụ ăn uống (Y tế) trên cùng nền.
- [ ] `cap-lai-dieu-chinh-gcn-du-dieu-kien-kinh-doanh-duoc-so-y-te` (13 / 2): nhận theo cụm tên
      "cấp lại, điều chỉnh giấy chứng nhận đủ điều kiện kinh doanh dược".
- [ ] `dang-ky-hanh-nghe` (10 / 2): nhận theo `maThuTuc=1.012275`.
- [ ] Gợi ý chọn thủ tục + tên tiếng Mông. Card hiện, nhận đúng trang.

### 11:40–12:00 · Test + deploy một lần cho cả 7

- [ ] Import registry không lỗi, đủ 66 thủ tục (`_validate_profile_dispatch()` báo ngay nếu thiếu pipeline).
- [ ] Test toàn bộ `tests/unit` + `tests/integration` (plugin `win_socketpair` + `PYTHONUTF8=1`):
      không vượt mốc sáng nay `11 failed, 3 errors`.
- [ ] `docker compose -f compose.prod.yml up -d --build --remove-orphans app`
- [ ] Container `Up`, `curl.exe -s http://localhost:12005/healthz` trả `{"ok":true}`.
- [ ] Stack toàn trình (12015) lên bản mới nếu trợ lý đang trỏ vào đó.

### Dự phòng nếu xong sớm (theo thứ tự)

| Bộ | Thủ tục | Lượt / TK | Ghi chú |
|---|---|---|---|
| Nội vụ | `cap-bo-sung-cap-lai-giay-chung-nhan-nguoi-co-cong` | 5 / 1 | Cùng nhóm với thờ cúng liệt sĩ, NCC từ trần |
| Nội vụ | `giai-quyet-che-do-khang-chien` | 2 / 1 | Cùng nhóm người có công |
| NN&MT | `thu-hoi-gcn-cap-sai-bac-ninh` (1.115447) | 5 / 1 | Cùng cụm Bắc Ninh |
| Y tế | `dieu-chinh-giay-phep-hanh-nghe-chuyen-tiep` | 9 / 1 | Cùng nhóm hành nghề |

## Dồn sang chiều

- Chạy thử trên cổng (dừng trước nút Nộp, dữ liệu bịa) cho 7 thủ tục sáng nay.
- Từ checklist 20/10: phù hiệu xe (cần `dom-editgrid`), công ty TNHH 2 TV + cổ phần (cổng ĐKKD), HDV nội địa (`fill-liz.js`).
- Chạy thử còn nợ: `ho-tro-mai-tang-1116910` và 10 thủ tục có entry từ 19/10.
- Mở đường cổng Đà Nẵng bằng `cap-doi-gcn-da-nang` trước Đợt 3 (27/10).

## Kết quả cuối buổi

| Bộ | Thủ tục | Entry | Nhận trang | Chạy thử | Ghi chú |
|---|---|---|---|---|---|
| NN&MT | dinh-chinh-gcn-da-cap-bac-ninh | ☐ | ☐ | ☐ | |
| NN&MT | cap-doi-gcn-bac-ninh | ☐ | ☐ | ☐ | |
| NN&MT | tach-hop-thua-dat-bac-ninh | ☐ | ☐ | ☐ | |
| NN&MT | dang-ky-dat-dai-lan-dau-bac-ninh | ☐ | ☐ | ☐ | |
| Xây dựng | cap-giay-phep-chat-ha-cay-xanh | ☐ | ☐ | ☐ | |
| Y tế | cap-lai-dieu-chinh-gcn-du-dieu-kien-kinh-doanh-duoc-so-y-te | ☐ | ☐ | ☐ | |
| Y tế | dang-ky-hanh-nghe | ☐ | ☐ | ☐ | |

**Tổng sáng nay: ___ / 7 → lũy kế ___ / 100**

> Dùng dữ liệu bịa khi chạy thử. Không nộp hồ sơ thật.

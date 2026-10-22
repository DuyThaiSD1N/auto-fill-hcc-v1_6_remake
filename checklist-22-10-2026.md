# Checklist sáng T5 22/10/2026 — Đợt 1 ngày cuối / mở Đợt 2

Mục tiêu sáng nay: **69 → 78 thủ tục** trên trợ lý (+9). Mốc Đợt 1 (64) đã vượt từ chiều 21/10; sáng nay
gần chạm mốc Đợt 2 (79, hạn T2 26/10) trong [ke-hoach-100-thu-tuc-tro-ly.md](ke-hoach-100-thu-tuc-tro-ly.md).

## Hiện trạng đầu giờ

- Chiều 21/10 (commit `5cb6871`) đã thêm **10 thủ tục đất đai Bắc Ninh**: đính chính GCN, cấp đổi GCN, tách hợp thửa,
  đăng ký lần đầu, thu hồi GCN cấp sai, đính chính sai sót, giao/thuê/chuyển mục đích, biến động (chung, thỏa thuận,
  chuyển nhượng). Trợ lý **69**, lõi **222**, còn **153**.
- 3 thủ tục còn lại của checklist sáng 21/10 **chưa vào trợ lý**: chặt hạ cây xanh, dược Sở Y tế, đăng ký hành nghề.
- Container `app` 12005 build lúc 17:09 21/10: **đã có** 10 thủ tục Bắc Ninh, **chưa có** commit `19dbfd4`
  (`ke_khai_links.py`, `router.py`, 17:25). `/healthz` ok.
- Stack toàn trình 12015 vẫn chạy image `:dev-toan-trinh` từ 17/10.
- Bảng kết quả cuối buổi 21/10 chưa điền: 10 thủ tục Bắc Ninh mới có entry, **chưa chạy thử trên cổng**.

## Kế hoạch sáng nay

Ưu tiên như hôm qua: (1) cổng trợ lý đã chạy được, (2) nhiều lượt / tài khoản. Lượt / TK lấy từ `process_requests`
Mongo local sáng 22/10.

Mỗi thủ tục cần: entry trong `app/channels/handfree/procedure_registry.py`, gợi ý chọn thủ tục
(`procedure_picker/prompt.py`), tên tiếng Mông (`script_mong.py`). Không tạo file mới.

### 09:30–10:30 · Y tế: cổng `dichvucongbyt.moh.gov.vn` (69 → 73)

Chép khung từ `cap-giay-chung-nhan-co-so-du-dieu-kien-an-toan-thuc-pham` (cùng cổng, Form.io, chọn Sở Y tế).
`detect` gồm `urlScope` + `maThuTuc=` + id form.

| # | Key | Lượt / TK | Nhận trang |
|---|---|---|---|
| 1 | `cap-lai-dieu-chinh-gcn-du-dieu-kien-kinh-doanh-duoc-so-y-te` | 13 / 2 | cụm tên "cấp lại, điều chỉnh giấy chứng nhận đủ điều kiện kinh doanh dược" |
| 2 | `dang-ky-hanh-nghe` | 10 / 2 | `maThuTuc=1.012275` |
| 3 | `dieu-chinh-giay-phep-hanh-nghe-chuyen-tiep` | 9 / 1 | cụm tên "điều chỉnh giấy phép hành nghề" |
| 4 | `cap-moi-giay-phep-hanh-nghe-chuyen-tiep` | 7 / 2 | cụm tên "cấp mới giấy phép hành nghề" |

- [ ] Entry, `requiredDocs` + `uploadHint` lấy từ entry lõi.
- [ ] #3 và #4 cùng chữ "giấy phép hành nghề … chuyển tiếp": kiểm `detect` không nhận nhầm nhau.
- [ ] Gợi ý chọn thủ tục + tên tiếng Mông. Card hiện, nhận đúng trang.

Test lõi: `test_cap_moi_gphn_chuyen_tiep_attach.py` (vừa sửa planner chiều 21/10).

### 10:30–11:10 · Xây dựng: cổng `dvc.moc.gov.vn` (73 → 76)

Chép khung từ `cap-giay-phep-lien-van-viet-lao` (`flowProfile: "xay-dung"`).

| # | Key | Lượt / TK | Nhận trang |
|---|---|---|---|
| 5 | `cap-giay-phep-chat-ha-cay-xanh` | 6 / 2 | "cấp giấy phép chặt hạ, dịch chuyển cây xanh" |
| 6 | `chap-thuan-dau-noi-tam` | 0 | "chấp thuận vị trí đấu nối tạm" |
| 7 | `cap-gcnkncm-cccm` | 0 | "cấp, cấp lại, chuyển đổi giấy chứng nhận khả năng chuyên môn" |

- [ ] Entry + gợi ý chọn thủ tục + tên tiếng Mông. Card hiện, nhận đúng trang.

### 11:10–11:40 · Nội vụ – người có công: cổng `dichvucongbnv.moha.gov.vn` (76 → 78)

Chép khung từ `uu-dai-ncc-tu-tran` / `tro-cap-tho-cung-liet-si` (`urlScope` + `MaTTHC=`).

| # | Key | Lượt / TK | Ghi chú |
|---|---|---|---|
| 8 | `cap-bo-sung-cap-lai-giay-chung-nhan-nguoi-co-cong` | 5 / 1 | Có lượt mới nhất 17/10 |
| 9 | `giai-quyet-che-do-khang-chien` | 2 / 1 | `detect` lõi theo `apply-online/…`: kiểm URL thật trên cổng Bộ Nội vụ trước khi viết |

- [ ] Entry + gợi ý chọn thủ tục + tên tiếng Mông. Card hiện, nhận đúng trang.

### 11:40–12:00 · Test + deploy một lần cho cả 9

- [ ] Import registry không lỗi, đủ 78 thủ tục (`_validate_profile_dispatch()` báo ngay nếu thiếu pipeline).
- [ ] Test toàn bộ `tests/unit` + `tests/integration` (plugin `win_socketpair` + `PYTHONUTF8=1`):
      không vượt baseline `11 failed, 3 errors`.
- [ ] `docker compose -f compose.prod.yml up -d --build --remove-orphans app` (lên luôn cả `19dbfd4` đang nợ).
- [ ] Container `Up`, `curl.exe -s http://localhost:12005/healthz` trả `{"ok":true}`.
- [ ] Stack toàn trình (12015) lên bản mới nếu trợ lý đang trỏ vào đó.

### Dự phòng nếu xong sớm (theo thứ tự)

| Bộ | Thủ tục | Lượt / TK | Ghi chú |
|---|---|---|---|
| Xây dựng | `gia-han-luu-hanh-phuong-tien-lao` | 0 | Cùng nhóm liên vận Việt – Lào |
| Y tế | `ho-tro-chi-phi-hoa-tang-bac-ninh` | 0 | Cổng Bắc Ninh, test bằng `hiephoabn` |
| Y tế | `ho-tro-nguoi-cao-tuoi-bac-ninh` | 0 | Bắc Ninh, chế độ attach |
| Nội vụ | `bo-sung-than-nhan-liet-si` (`maThuTuc=1.010825`) | 0 | Cùng nhóm người có công |

## Không đưa vào sáng nay (lượt cao nhưng kẹt engine / cổng)

| Thủ tục | Lượt / TK | Lý do |
|---|---|---|
| Phù hiệu xe | 59 / 3 | Cần `dom-editgrid` |
| Công ty TNHH 2 TV, cổ phần | 56 / 4, 19 / 3 | Cổng ĐKKD chưa mở với trợ lý |
| Tính tiền SDĐ Quảng Ngãi | 30 / 1 | Cần `add-document-dialog` |
| CCHN thú y cấp lại / gia hạn | 23 / 1, 12 / 2 | Gia hạn cần `add-document-dialog` |
| Băng-rôn, HDV nội địa | 22 / 1, 17 / 3 | Cần `fill-liz.js` |
| Điện mặt trời mái nhà | 10 / 2 | Cần `add-document-dialog` |

## Dồn sang chiều

- Chạy thử trên cổng (dừng trước nút Nộp, dữ liệu bịa) cho 9 thủ tục sáng nay.
- Chạy thử còn nợ: 10 thủ tục đất đai Bắc Ninh (21/10), `ho-tro-mai-tang-1116910`, 10 thủ tục có entry từ 19/10.
- Mở đường cổng Đà Nẵng bằng `cap-doi-gcn-da-nang` trước Đợt 3 (27/10).

## Kết quả cuối buổi

| Bộ | Thủ tục | Entry | Nhận trang | Chạy thử | Ghi chú |
|---|---|---|---|---|---|
| Y tế | cap-lai-dieu-chinh-gcn-du-dieu-kien-kinh-doanh-duoc-so-y-te | ☐ | ☐ | ☐ | |
| Y tế | dang-ky-hanh-nghe | ☐ | ☐ | ☐ | |
| Y tế | dieu-chinh-giay-phep-hanh-nghe-chuyen-tiep | ☐ | ☐ | ☐ | |
| Y tế | cap-moi-giay-phep-hanh-nghe-chuyen-tiep | ☐ | ☐ | ☐ | |
| Xây dựng | cap-giay-phep-chat-ha-cay-xanh | ☐ | ☐ | ☐ | |
| Xây dựng | chap-thuan-dau-noi-tam | ☐ | ☐ | ☐ | |
| Xây dựng | cap-gcnkncm-cccm | ☐ | ☐ | ☐ | |
| Nội vụ | cap-bo-sung-cap-lai-giay-chung-nhan-nguoi-co-cong | ☐ | ☐ | ☐ | |
| Nội vụ | giai-quyet-che-do-khang-chien | ☐ | ☐ | ☐ | |

**Tổng sáng nay: ___ / 9 → lũy kế ___ / 100**

> Dùng dữ liệu bịa khi chạy thử. Không nộp hồ sơ thật.

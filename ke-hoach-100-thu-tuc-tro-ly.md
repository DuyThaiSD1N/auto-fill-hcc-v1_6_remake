# Kế hoạch đưa Trợ lý nhân dân lên 100 thủ tục — hạn 31/10/2026

## 1. Hiện trạng

- Trợ lý nhân dân (kênh handfree) đang có **44 thủ tục**, nên cần thêm **56**.
- Thời gian từ T2 19/10 tới T6 30/10 là **10 ngày làm việc**, tức trung bình 5–6 thủ tục mỗi ngày.
- Registry lõi của Auto Fill (`app/procedures/registry.py`) có **219 thủ tục**. Có **175** đã có pipeline nhưng trợ lý chưa mở.
- Thêm một thủ tục **không cần viết pipeline mới**. Chỉ cần một entry trong `app/channels/handfree/procedure_registry.py`:
  - cách nhận diện trang (`detect`), nhãn (`label` / `shortLabel` / `subtitle` / `icon`), link kê khai (`keKhaiUrl`);
  - `needsAgencySelect`, `wizard` (các bước) hoặc `flowProfile`;
  - checklist giấy tờ (`requiredDocs`) và `uploadHint`.

  Phần xử lý và đính kèm dùng lại từ lõi.
- Việc tốn thời gian thật là **chạy thử trên cổng**. Vì vậy thủ tục được chấm "dễ" khi đạt cả hai tiêu chí:
  1. Thủ tục nằm trên cổng mà trợ lý đã chạy được.
  2. Pipeline không đòi engine mà extension trợ lý chưa có.

## 2. Loại khỏi tháng này

| Nhóm | Số lượng | Lý do |
|---|---|---|
| Lào Cai (đất đai, đầu tư) | ~32 | Bảng đính kèm chia nhánh (`sectionHeader`), extension trợ lý chưa có engine này |
| Cần nút "Thêm giấy tờ" của cổng MAE: gia hạn GPXD, xóa tàu cá, gia hạn CCHN thú y, ATTP nông lâm thủy sản, nội quy lao động, điện mặt trời mái nhà, tính tiền SDĐ Quảng Ngãi | 8 | Extension trợ lý chưa có engine `add-document-dialog` |
| Đăng ký tàu cá, phù hiệu xe | 3 | Cần `dom-click` / `dom-editgrid`, extension trợ lý chưa có |
| Thông báo băng-rôn quảng cáo (Bộ VHTTDL) | 1 | Extension trợ lý chưa có `fill-liz.js` |
| Thành lập công ty, chủ trương đầu tư, khuyến mại, hội | — | Không phải thủ tục cho người dân |
| Cổng Quảng Ninh, Quảng Ngãi, Ninh Bình, Lâm Đồng, Lai Châu | — | Chưa từng chạy trên trợ lý, mỗi cổng phải mở đường riêng |

## 3. Lộ trình

| Đợt | Thời gian | Thêm | Lũy kế |
|---|---|---|---|
| 1 | T2 19/10 → T5 22/10 | 20 | 64 |
| 2 | T6 23/10 → T2 26/10 | 15 | 79 |
| 3 | T3 27/10 → T5 29/10 | 21 | 100 |
| Chốt | T6 30/10 | Hồi quy toàn bộ + deploy | 100 |
| Dự phòng | T7 31/10 | — | — |

### Đợt 1 — chỉ cấu hình, cổng đã chạy (+20)

**Tư pháp + hộ kinh doanh (9)**

| # | Key | Vì sao dễ |
|---|---|---|
| 1 | `chung-thuc-di-chuc` | Chế độ attach, giống chứng thực |
| 2 | `cap-ban-sao-so-goc` | Chế độ attach |
| 3 | `bau-to-truong-to-hoa-giai` | Chế độ attach |
| 4 | `khai-sinh-ket-hop-nhan-cha-me-con` | Profile `tu-phap` |
| 5 | `dang-ky-nuoi-con-nuoi-trong-nuoc` | Profile `tu-phap` |
| 6 | `xac-nhan-thong-tin-ho-tich` | Profile `tu-phap`; kiểm việc tách hai bộ ô Form.io + eForm |
| 7 | `khai-tu-lien-thong` | Cùng cổng liên thông Angular với khai sinh |
| 8 | `tam-ngung-kinh-doanh` | Cùng engine HKD với thay đổi / chấm dứt hộ kinh doanh |
| 9 | `cap-lai-cap-doi-gcn-ho-kinh-doanh` | Cùng engine HKD |

**Bảo trợ xã hội / người có công (11).** Cùng nhóm cổng với trợ cấp xã hội, mai táng, thờ cúng liệt sĩ, ưu đãi người có công từ trần.

| # | Key |
|---|---|
| 10 | `doi-cap-lai-giay-xac-nhan-khuyet-tat` |
| 11 | `thuc-hien-tro-cap-xa-hoi-nhan-cham-soc-nuoi-duong-hang-thang` |
| 12 | `ho-tro-mai-tang-1116910` |
| 13 | `mai-tang-dan-cong-hoa-tuyen` |
| 14 | `ho-tro-chi-phi-van-chuyen-nguoi-tu-vong-den-co-so-hoa-tang` |
| 15 | `cap-lai-to-quoc-ghi-cong` |
| 16 | `cap-bo-sung-cap-lai-giay-chung-nhan-nguoi-co-cong` |
| 17 | `bo-sung-than-nhan-liet-si` |
| 18 | `tham-vieng-mo-liet-si` |
| 19 | `giai-quyet-che-do-khang-chien` |
| 20 | `sua-doi-thong-tin-ho-so-nguoi-co-cong` |

> Cũng trong T2 19/10: chạy thử `cap-doi-gcn-da-nang` để mở đường cho cổng Đà Nẵng, phát hiện vấn đề sớm cho Đợt 3.

### Đợt 2 — anh em cùng cổng (+15)

**Bộ Xây dựng, profile `xay-dung` (5)**

| # | Key | Ghi chú |
|---|---|---|
| 21 | `sua-chua-cai-tao-gpxd-cong-trinh` | Cùng pipeline `cap_giay_phep_xay_dung` |
| 22 | `cap-giay-phep-chat-ha-cay-xanh` | |
| 23 | `chap-thuan-dau-noi-tam` | |
| 24 | `cap-gcnkncm-cccm` | |
| 25 | `gia-han-luu-hanh-phuong-tien-lao` | Cùng nhóm với liên vận Việt – Lào |

**Bắc Ninh (10).** Cổng và engine Liferay đã chạy với biện pháp bảo đảm.

| # | Key |
|---|---|
| 26 | `cap-doi-gcn-bac-ninh` |
| 27 | `dinh-chinh-gcn-da-cap-bac-ninh` |
| 28 | `dinh-chinh-sai-sot-bac-ninh` |
| 29 | `dang-ky-dat-dai-lan-dau-bac-ninh` |
| 30 | `dang-ky-bien-dong-dat-dai-bac-ninh` |
| 31 | `tach-hop-thua-dat-bac-ninh` |
| 32 | `ho-tro-chi-phi-hoa-tang-bac-ninh` |
| 33 | `ho-tro-nguoi-cao-tuoi-bac-ninh` |
| 34 | `cap-hoc-tap-bac-ninh` |
| 35 | `dang-ky-nha-o-xa-hoi-bac-ninh` |

### Đợt 3 — cổng Đà Nẵng + dân sinh (+21)

**Đà Nẵng (10).** Có sẵn tài khoản test Hải Châu và Liên Chiểu.

| # | Key |
|---|---|
| 36 | `cap-doi-gcn-da-nang` (đã mở đường ở Đợt 1) |
| 37 | `dinh-chinh-gcn-da-cap-da-nang` |
| 38 | `tach-hop-thua-dat-da-nang` |
| 39 | `dang-ky-bien-dong-dat-dai-da-nang` |
| 40 | `chuyen-muc-dich-su-dung-dat-da-nang` |
| 41 | `cap-gcn-so-nha-da-nang` |
| 42 | `xac-nhan-ho-so-so-nha-da-nang` |
| 43 | `xoa-dang-ky-bien-phap-bao-dam-da-nang` |
| 44 | `dang-ky-bien-phap-bao-dam-qsdd` |
| 45 | `xac-dinh-lai-dien-tich-dat-o-gcn-truoc-2004` |

**Thẻ hướng dẫn viên du lịch (4)**

| # | Key |
|---|---|
| 46 | `cap-the-huong-dan-vien-du-lich-noi-dia` |
| 47 | `cap-the-huong-dan-vien-du-lich-tai-diem-da-nang` |
| 48 | `cap-doi-the-huong-dan-vien-du-lich-da-nang` |
| 49 | `cap-lai-the-huong-dan-vien-du-lich-da-nang` |

**Dân sinh (5) + Y tế (2)**

| # | Key |
|---|---|
| 50 | `dang-ky-lap-dat-su-dung-nuoc-sach` |
| 51 | `chuyen-doi-ten-hop-dong-nuoc-sach` |
| 52 | `xac-nhan-dieu-kien-dien-tich-nha-o-dang-ky-thuong-tru` |
| 53 | `mien-giam-hoc-phi-gdnn-dai-hoc-tu-thuc` |
| 54 | `yeu-cau-tro-giup-phap-ly` |
| 55 | `dang-ky-hanh-nghe` |
| 56 | `cap-lai-giay-phep-hanh-nghe-truoc-2024` |

### Danh sách dự bị

Lấy thay khi một thủ tục trong lộ trình bị kẹt.

- Y tế: `cap-moi-giay-phep-hanh-nghe-chuyen-tiep`, `dieu-chinh-giay-phep-hanh-nghe-chuyen-tiep`, `cap-chung-chi-hanh-nghe-duoc`, `cap-lai-chung-chi-hanh-nghe-thu-y`
- Đà Nẵng: `dang-ky-dat-dai-lan-dau-da-nang`, `dang-ky-thay-doi-bien-phap-bao-dam-qsdd`
- Bắc Ninh: `giao-thue-chuyen-muc-dich-dat-bac-ninh`, `thu-hoi-gcn-cap-sai-bac-ninh`

## 4. Thế nào là "xong" cho một thủ tục

1. Có entry trong `procedure_registry.py`. Không tạo file mới.
2. Card hiện ra trên trợ lý, trợ lý nhận đúng trang thủ tục.
3. Chạy thử một hồ sơ mẫu bằng **dữ liệu bịa**: chọn cơ quan → điền form → đính kèm → **dừng trước nút Nộp**.
4. Pytest pass, rồi deploy Docker. Gom mỗi nhóm một lần deploy để khỏi build quá nhiều lần.

## 5. Mốc kiểm tra

| Ngày | Phải đạt |
|---|---|
| T5 22/10 | 64 thủ tục; cổng Đà Nẵng đã mở đường |
| T2 26/10 | 79 thủ tục. Nếu chưa đạt thì lấy danh sách dự bị thay cho nhóm Đà Nẵng |
| T5 29/10 | 100 thủ tục |
| T6 30/10 | Hồi quy xong, deploy bản chốt |

## 6. Rủi ro

- Kế hoạch được phân loại từ code: engine nào có, cổng nào đã có thủ tục chạy, pipeline đòi gì. **Chưa chạy thử thủ tục nào trên cổng thật.** Cổng Đà Nẵng và nhóm Y tế hành nghề có thể còn bất ngờ.
- Chạy thử trên cổng DVCQG cần tài khoản VNeID đăng nhập được. Đây là điểm nghẽn lớn nhất nếu chỉ một người có tài khoản.
- Đợt 3 dày nhất (21 thủ tục). Theo dõi mốc 26/10 để kịp đổi sang danh sách dự bị.

# Kế hoạch đưa Trợ lý nhân dân lên 100 thủ tục — hạn 31/10/2026

## 1. Hiện trạng

- Trợ lý nhân dân (kênh handfree) đang có **44 thủ tục**, nên cần thêm **56**.
  _Cập nhật 22/10 15:00: **71 thủ tục**, còn thiếu 29._
  _Cập nhật 23/10 11:00: **75 thủ tục**, còn thiếu 25. Danh sách ở mục 7._
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

## 7. Thủ tục đã lên trợ lý — 75 (cập nhật T6 23/10 11:00, chưa commit, trên `aedb955`)

Lấy từ `app/channels/handfree/procedure_registry.py` và xếp theo nhóm. Trong file, thứ tự không theo nhóm: 4 thủ tục hộ
kinh doanh nằm sau nhóm Xây dựng. Container `app` 12005 (build 10:23 23/10) đếm đủ 75. "Có entry" chưa có nghĩa là
đã chạy thử trên cổng: xem phần nợ chạy thử trong checklist từng ngày.

So với bản 22/10 (71) thêm 4 thủ tục: `dieu-chinh-giay-phep-hanh-nghe-chuyen-tiep` (commit `53ea8cd`, 22/10) và 3 thủ
tục Bắc Ninh (23/10, chưa commit). `cap-hoc-tap-bac-ninh` (1.014581) bỏ qua.

**Hộ tịch (19)**

| # | Key | Tên (rút gọn từ shortLabel) |
|---|---|---|
| 1 | `khai-sinh-dang-ky` | Liên thông đăng ký khai sinh |
| 2 | `khai-sinh-dang-ky-thuong` | Đăng ký Khai sinh |
| 3 | `ket-hon` | Đăng ký Kết hôn |
| 4 | `dang-ky-giam-ho` | Đăng ký Giám hộ |
| 5 | `dang-ky-cham-dut-giam-ho` | Chấm dứt Giám hộ |
| 6 | `trich-luc-ks` | Bản sao Trích lục hộ tịch |
| 7 | `ket-hon-nuoc-ngoai` | Kết hôn có yếu tố nước ngoài |
| 8 | `dang-ky-lai-ket-hon` | Đăng ký lại Kết hôn |
| 9 | `khai-sinh-dang-ky-lai` | Đăng ký lại Khai sinh |
| 10 | `khai-sinh-da-co-ho-so` | Khai sinh (đã có giấy tờ cá nhân) |
| 11 | `khai-tu` | Đăng ký Khai tử |
| 12 | `khai-tu-lien-thong` | Liên thông đăng ký khai tử |
| 13 | `khai-tu-dang-ky-lai` | Đăng ký lại Khai tử |
| 14 | `dang-ky-nhan-cha-me-con` | Nhận Cha, Mẹ, Con |
| 15 | `khai-sinh-ket-hop-nhan-cha-me-con` | Khai sinh kết hợp nhận Cha, Mẹ, Con |
| 16 | `dang-ky-nuoi-con-nuoi-trong-nuoc` | Nuôi con nuôi trong nước |
| 17 | `thay-doi-cai-chinh-ho-tich` | Cải chính hộ tịch |
| 18 | `xac-nhan-tinh-trang-hon-nhan` | Xác nhận tình trạng hôn nhân |
| 19 | `xac-nhan-thong-tin-ho-tich` | Xác nhận thông tin hộ tịch |

**Chứng thực và tư pháp khác (13)**

| # | Key | Tên (rút gọn từ shortLabel) |
|---|---|---|
| 20 | `chung-thuc-ban-sao` | Chứng thực bản sao |
| 21 | `chung-thuc-giao-dich-tai-san` | Chứng thực giao dịch tài sản |
| 22 | `chung-thuc-phan-chia-di-san` | Chứng thực văn bản phân chia di sản |
| 23 | `chung-thuc-tu-choi-nhan-di-san` | Chứng thực văn bản từ chối nhận di sản |
| 24 | `chung-thuc-di-chuc` | Chứng thực di chúc |
| 25 | `chung-thuc-sua-doi-bo-sung-huy-bo-giao-dich` | Chứng thực sửa đổi, bổ sung, hủy bỏ giao dịch |
| 26 | `chung-thuc-chu-ky-nguoi-dich-ctv` | Chứng thực chữ ký người dịch (CTV) |
| 27 | `chung-thuc-chu-ky-nguoi-dich-khong-ctv` | Chứng thực chữ ký người dịch (không CTV) |
| 28 | `chung-thuc-chu-ky` | Chứng thực chữ ký |
| 29 | `cap-ban-sao-so-goc` | Cấp bản sao từ sổ gốc |
| 30 | `bau-to-truong-to-hoa-giai` | Bầu tổ trưởng tổ hòa giải |
| 31 | `yeu-cau-tro-giup-phap-ly` | Yêu cầu trợ giúp pháp lý |
| 32 | `cap-chung-chi-hanh-nghe-luat-su-mien-dao-tao-tap-su` | Chứng chỉ hành nghề luật sư (miễn tập sự) |

**Hộ kinh doanh (5)**

| # | Key | Tên (rút gọn từ shortLabel) |
|---|---|---|
| 33 | `dang-ky-kinh-doanh` | Đăng ký thành lập hộ kinh doanh |
| 34 | `dang-ky-thay-doi-noi-dung-ho-kinh-doanh` | Thay đổi nội dung hộ kinh doanh |
| 35 | `cham-dut-hoat-dong-ho-kinh-doanh` | Chấm dứt hộ kinh doanh |
| 36 | `tam-ngung-kinh-doanh` | Tạm ngừng hộ kinh doanh |
| 37 | `cap-lai-cap-doi-gcn-ho-kinh-doanh` | Cấp lại GCN hộ kinh doanh |

**Bảo trợ xã hội / người có công (10)**

| # | Key | Tên (rút gọn từ shortLabel) |
|---|---|---|
| 38 | `dieu-chinh-huu-tri-xa-hoi` | Trợ cấp hưu trí xã hội — thực hiện |
| 39 | `di-chuyen-ho-so-nguoi-huong-tro-cap` | Di chuyển hồ sơ người hưởng trợ cấp ưu đãi |
| 40 | `tro-cap-tho-cung-liet-si` | Trợ cấp thờ cúng liệt sĩ |
| 41 | `uu-dai-ncc-tu-tran` | Trợ cấp khi người có công từ trần |
| 42 | `xac-dinh-muc-do-khuyet-tat` | Xác định mức độ khuyết tật |
| 43 | `doi-cap-lai-giay-xac-nhan-khuyet-tat` | Đổi, cấp lại Giấy xác nhận khuyết tật |
| 44 | `ho-tro-mai-tang-1116910` | Mai táng — đối tượng bảo trợ xã hội |
| 45 | `ho-tro-mai-tang-huu-tri-xa-hoi` | Mai táng — người hưởng hưu trí xã hội |
| 46 | `tro-cap-xa-hoi-hang-thang` | Trợ cấp xã hội hàng tháng |
| 47 | `thuc-hien-tro-cap-xa-hoi-nhan-cham-soc-nuoi-duong-hang-thang` | Trợ cấp XH và nhận chăm sóc, nuôi dưỡng (NĐ 335) |

**Xây dựng (7)**

| # | Key | Tên (rút gọn từ shortLabel) |
|---|---|---|
| 48 | `cho-thue-thue-mua-nha-o-xa-hoi` | Thuê / thuê mua nhà ở xã hội |
| 49 | `cap-giay-phep-xay-dung-moi-nha-o-rieng-le` | Cấp phép xây dựng mới |
| 50 | `dieu-chinh-giay-phep-xay-dung` | Điều chỉnh giấy phép xây dựng |
| 51 | `sua-chua-cai-tao-gpxd-nha-o-rieng-le` | Cấp phép sửa chữa, cải tạo |
| 52 | `cung-cap-thong-tin-quy-hoach` | Cung cấp thông tin quy hoạch |
| 53 | `cap-phep-long-duong-via-he` | Sử dụng tạm thời lòng đường, vỉa hè |
| 54 | `cap-giay-phep-lien-van-viet-lao` | Giấy phép liên vận Việt Nam - Lào |

**Y tế (4)**

| # | Key | Tên (rút gọn từ shortLabel) | Ghi chú |
|---|---|---|---|
| 55 | `cap-giay-chung-nhan-co-so-du-dieu-kien-an-toan-thuc-pham` | GCN cơ sở đủ điều kiện ATTP (dịch vụ ăn uống) | |
| 56 | `cap-lai-dieu-chinh-gcn-du-dieu-kien-kinh-doanh-duoc-so-y-te` | Cấp lại, điều chỉnh GCN đủ điều kiện kinh doanh dược | Mới 22/10 |
| 57 | `dang-ky-hanh-nghe` | Đăng ký người hành nghề khám bệnh, chữa bệnh | Mới 22/10 |
| 58 | `dieu-chinh-giay-phep-hanh-nghe-chuyen-tiep` | Điều chỉnh GPHN khám bệnh, chữa bệnh (giai đoạn chuyển tiếp) | Mới 22/10, Sở Y tế |

**Đất đai Bắc Ninh (12)**

| # | Key | Tên (rút gọn từ shortLabel) |
|---|---|---|
| 59 | `dang-ky-bien-phap-bao-dam-bac-ninh` | Đăng ký biện pháp bảo đảm bằng QSDĐ |
| 60 | `xoa-dang-ky-bien-phap-bao-dam-bac-ninh` | Xóa đăng ký biện pháp bảo đảm bằng QSDĐ |
| 61 | `dinh-chinh-gcn-da-cap-bac-ninh` | Đính chính giấy chứng nhận đã cấp |
| 62 | `dang-ky-bien-dong-thoa-thuan-bac-ninh` | Đăng ký biến động theo thỏa thuận (hộ gia đình, vợ chồng, tranh chấp, thế chấp) |
| 63 | `dang-ky-bien-dong-dat-dai-bac-ninh` | Đăng ký biến động (chuyển đổi, chuyển nhượng, thừa kế, tặng cho, góp vốn) |
| 64 | `tach-hop-thua-dat-bac-ninh` | Tách thửa đất hoặc hợp thửa đất |
| 65 | `cap-doi-gcn-bac-ninh` | Cấp đổi GCN quyền sử dụng đất |
| 66 | `dang-ky-dat-dai-lan-dau-bac-ninh` | Đăng ký đất đai, cấp GCN lần đầu |
| 67 | `thu-hoi-gcn-cap-sai-bac-ninh` | Thu hồi GCN cấp lần đầu sai quy định và cấp lại |
| 68 | `dinh-chinh-sai-sot-bac-ninh` | Đính chính GCN cấp lần đầu có sai sót |
| 69 | `giao-thue-chuyen-muc-dich-dat-bac-ninh` | Giao đất, cho thuê đất, chuyển mục đích |
| 70 | `dang-ky-bien-dong-chuyen-nhuong-bac-ninh` | Đăng ký biến động (chuyển nhượng, thừa kế, tặng cho, góp vốn; cho thuê, cho thuê lại) |

**Bắc Ninh — xã hội, nhà ở (3)**

| # | Key | Mã | Tên (rút gọn từ shortLabel) | Ghi chú |
|---|---|---|---|---|
| 71 | `ho-tro-nguoi-cao-tuoi-bac-ninh` | 1.014589 | Hỗ trợ người cao tuổi 70–dưới 75 tuổi; đảng viên huy hiệu 40 năm tuổi đảng | Mới 23/10, chỉ đính kèm |
| 72 | `ho-tro-chi-phi-hoa-tang-bac-ninh` | 1.014582 | Hỗ trợ chi phí hỏa táng (cả điện táng) | Mới 23/10, điền đơn + đính kèm |
| 73 | `dang-ky-nha-o-xa-hoi-bac-ninh` | 1.014632 | Đăng ký mua, thuê mua, thuê nhà ở xã hội | Mới 23/10, điền Mẫu 02 + đính kèm |

**Khác (2)**

| # | Key | Tên (rút gọn từ shortLabel) |
|---|---|---|
| 74 | `cap-giay-phep-khai-thac-thuy-san` | Giấy phép khai thác thủy sản |
| 75 | `cap-ban-sao-van-bang-so-goc` | Cấp bản sao văn bằng, chứng chỉ từ sổ gốc |

3 entry Bắc Ninh (#61, #64, #68) không có `shortLabel`, card hiện `label` (đều đã ngắn).

Hai tính năng mới 23/10 áp cho nhiều thủ tục. Cả hai chỉ chạy khi extension trợ lý khai cờ, từ bản 1.13.3:

- **Khối "người được ủy quyền" cổng Bắc Ninh** (`bacNinhAuthorizedPerson`, cờ `supportsBacNinhAuthorizedPerson`):
  #59, #60, #62, #63, #72, #73. Chỉ điền khi công dân chọn đối tượng có ủy quyền.
- **Bước "Hình thức nhận kết quả" cổng Bộ Y tế** (cờ `supportsIgateResultStep`): gắn tự động cho 11 thủ tục có `urlScope`
  `dichvucongbyt.moh.gov.vn`, gồm #38, #42–#47 và #55–#58. Trợ lý chọn cách nhận kết quả. Ô cam đoan và Mã xác nhận do
  công dân tự làm.

Kế hoạch 23/10 chiều (75 → 77): `cap-moi-giay-phep-hanh-nghe-chuyen-tiep`, `cap-giay-phep-chat-ha-cay-xanh`. Chi tiết
ở [checklist-23-10-2026.md](checklist-23-10-2026.md).

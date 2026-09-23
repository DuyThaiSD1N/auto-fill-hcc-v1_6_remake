"""[Lào Cai] Sử dụng đất kết hợp đa mục đích (cấp xã) — mã 1.115682.

Người sử dụng đất đang có Giấy chứng nhận cho một mục đích CHÍNH (hồ sơ mẫu: đất trồng cây hàng năm
khác) nay đề nghị UBND cấp xã cho phép dùng KẾT HỢP một phần thửa vào mục đích khác (thương mại,
dịch vụ…) theo Điều 218 Luật Đất đai 2024 và Điều 99 Nghị định 102/2024/NĐ-CP.

⚑ KHÔNG PHẢI CHUYỂN MỤC ĐÍCH SỬ DỤNG ĐẤT: mục đích chính của thửa GIỮ NGUYÊN trên Giấy chứng nhận,
chỉ bổ sung chức năng kết hợp có thời hạn, hết thời hạn phải tháo dỡ và hoàn nguyên. Vì vậy hồ sơ
KHÔNG có đơn xin chuyển mục đích, KHÔNG có trích đo địa chính, KHÔNG có hợp đồng chuyển nhượng —
nhầm sang `chuyen_md_sd_dat_phuong_xa_lao_cai` là nhầm cả bộ giấy tờ phải nộp.

Bộ hồ sơ theo Đơn Mẫu số 13 mục 6 và ảnh ánh xạ đính kèm của hồ sơ mẫu (ông Nguyễn Đức Nhân, thửa
428 tờ bản đồ 264, TDP Cầu Mây 1, phường Sa Pa, tỉnh Lào Cai):
  1. Văn bản đề nghị sử dụng đất kết hợp đa mục đích theo Mẫu số 13;
  2. Phương án sử dụng đất kết hợp (tập thuyết minh + bản đồ + bản vẽ, gộp chung MỘT tệp);
  3. Giấy chứng nhận đã cấp hoặc giấy tờ về quyền sử dụng đất;
  4. Bản sao Căn cước công dân của chủ hộ (Đơn Mẫu 13 mục 6 có kê nhưng hồ sơ mẫu CHƯA có tệp).

⚑ MÀN HÌNH ĐÍNH KÈM KHÔNG CÓ BẢNG "THÀNH PHẦN HỒ SƠ". Khối "Biểu mẫu giấy tờ" của bước này ghi đúng
một dòng "(Hồ sơ không yêu cầu giấy tờ kèm theo)" — toàn bộ giấy tờ phải tự thêm ở danh sách "Giấy
tờ khác". Đây là khác biệt lớn nhất so với 1.115685/1.115693 (bảng phẳng, khớp theo `slotIndex`):
planner của thủ tục này KHÔNG phát `fixed-slot` nào.

Cùng cổng `dichvucong.laocai.gov.vn`, cùng eForm iGate legacy (bộ ô `CongDan_*` / `ChuHoSo_*`) với
1.115650/1.115678/1.115681/1.115685/1.115693/1.115694 → dùng lại engine `dom-*` của extension,
không phải sửa FE.
"""

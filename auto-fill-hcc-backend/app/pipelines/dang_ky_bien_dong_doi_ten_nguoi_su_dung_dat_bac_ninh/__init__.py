"""Pipeline "[Tỉnh Bắc Ninh] Đăng ký biến động đối với trường hợp đổi tên hoặc thay đổi thông tin về người sử dụng đất…"
(mã TTHC 1.115460, link kê khai tích Sở).

Cổng dichvucong.bacninh.gov.vn (Liferay + select2, engine content/fill-bacninh.js), trang nộp 4 tab cùng trang. Theo bản
crawl DOM ngày 21/11/2026:

1. ĐƠN (purpose "registration_form"): Đơn đăng ký biến động Mẫu số 18, khớp ô theo CLASS eform-element-<Key> — CÙNG bộ
   khoá với cap_lai_giay_chung_nhan_do_bi_mat_bac_ninh (1.115465). Số vào sổ / số phát hành GCN đã cấp ghép vào
   "II. Nội dung biến động" theo hướng dẫn (3) của Mẫu 18.
2. ỦY QUYỀN (purpose "authorized_person"): khối doiTuongKhac* = chủ hồ sơ (người đứng Đơn / bên ủy quyền).
3. ĐÍNH KÈM: 7 thành phần TP-H05.* + "File đính kèm khác"; hỗ trợ tách giấy theo trang (attach/planner.py).
"""

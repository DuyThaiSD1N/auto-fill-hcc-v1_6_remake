"""Pipeline "[Tỉnh Bắc Ninh] Đăng ký biến động đối với trường hợp đổi tên hoặc thay đổi thông tin về người sử dụng đất…"
(mã TTHC 1.115460, link kê khai tích Sở).

Cổng dichvucong.bacninh.gov.vn (Liferay + select2, engine content/fill-bacninh.js), trang nộp 4 tab cùng trang. Theo bản
crawl DOM ngày 21/11/2026 + file mapping Excel và ảnh ánh xạ đính kèm ngày 25/11/2026 (eform 2867):

1. ĐƠN (purpose "registration_form"): Đơn đăng ký biến động (giấy Mẫu 18 hoặc Mẫu 24, tối đa hai người đứng đơn), khớp
   ô theo CLASS eform-element-<Key> — CÙNG bộ khoá với cap_lai_giay_chung_nhan_do_bi_mat_bac_ninh (1.115465); nơi /
   ngày khai khớp NAME element_77275/77276. Mục IV (2) và mục V lấy từ Văn bản cam kết thành viên hộ khi Đơn trống.
2. ỦY QUYỀN (purpose "authorized_person"): khối doiTuongKhac* = chủ hồ sơ (người đứng Đơn / bên ủy quyền); từ 60 tuổi
   → loại "Người cao tuổi".
3. ĐÍNH KÈM: 7 thành phần TP-H05.* + "File đính kèm khác"; Văn bản cam kết đính chung 000049 + 000051, CCCD vào 000049
   Bản sao; hỗ trợ tách giấy theo trang (attach/planner.py).
"""

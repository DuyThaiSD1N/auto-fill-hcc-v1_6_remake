"""Pipeline "[Tỉnh Bắc Ninh] Xác nhận tiếp tục sử dụng đất nông nghiệp" (mã TTHC 1.115462, link kê khai tích Sở).

Cổng dichvucong.bacninh.gov.vn (Liferay + select2, engine content/fill-bacninh.js), trang nộp 4 tab cùng trang
(thuTucHanhChinhId 3836, eformId 2869). Theo file mapping Excel + ảnh ánh xạ đính kèm của người dùng ngày 24/11/2026:

1. ĐƠN (purpose "registration_form"): Đơn xin xác nhận lại thời hạn sử dụng đất nông nghiệp Mẫu 09, kèm phần
   "II. Xác nhận của UBND cấp xã". Ô eform KHÔNG có class ngữ nghĩa trong mapping → khớp NAME ``element_773xx``
   (cố định trong eform 2869). Đơn có nhiều thửa thì 3 ô thửa / tờ / diện tích ghi danh sách cùng thứ tự.
2. ỦY QUYỀN (purpose "authorized_person"): khối doiTuongKhac* = chủ hồ sơ = BÊN ỦY QUYỀN của Giấy ủy quyền (người
   sử dụng đất đứng Đơn). Chủ hồ sơ từ đủ 60 tuổi → loại "Người cao tuổi" (``authorizedSubject``), còn lại loại mặc
   định "Cá nhân khác là Công dân Việt Nam".
3. ĐÍNH KÈM: TP-H05.000053 (Đơn Mẫu 09 + trang xác nhận UBND xã, không tách), TP-H05.000040 (GCN, bìa + trang chứng
   nhận), Giấy ủy quyền + lời chứng chứng thực / CCCD / giấy khác → "File đính kèm khác". Hỗ trợ tách giấy theo trang.
"""

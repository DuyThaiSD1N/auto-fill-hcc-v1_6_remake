"""Pipeline "[Tỉnh Bắc Ninh] Cấp lại Giấy chứng nhận do bị mất" (mã TTHC 1.115465).

Cổng dichvucong.bacninh.gov.vn (Liferay + select2, engine content/fill-bacninh.js), trang nộp 4 tab cùng trang.
Thân đơn = Đơn đăng ký biến động Mẫu số 18, khớp ô theo CLASS eform-element-<Key> (cùng bộ khoá với
dinh_chinh_gcn_da_cap_bac_ninh). Khối "Thông tin trong trường hợp được ủy quyền" (doiTuongKhac*) = chủ hồ sơ, đọc ở
lượt purpose="authorized_person" (khuôn dinh_chinh_sai_sot_bac_ninh).

Riêng thủ tục này: GCN đã MẤT nên hồ sơ không có bản gốc GCN; số vào sổ / số phát hành của GCN bị mất lấy từ Đơn
trình báo mất hoặc Bản cam kết rồi ghép vào "II. Nội dung biến động" theo hướng dẫn (3) của Mẫu 18. Đính kèm: Đơn Mẫu
18 (thường scan chung cả bộ) → TP-H05.000026; dòng GCN TP-H05.000040 chỉ nhận bản GCN nếu thật sự có; mảnh trích đo →
TP-H05.000045; giấy lẻ còn lại → "File đính kèm khác".
"""

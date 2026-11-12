"""Thủ tục "[Tỉnh Bắc Ninh] Đăng ký thay đổi biện pháp bảo đảm bằng QSDĐ, tài sản gắn liền với đất" (1.011442).

Cổng dichvucong.bacninh.gov.vn (Liferay + select2, engine fill-bacninh.js), trang nộp 4 tab cùng trang, eForm Phiếu yêu
cầu Mẫu số 02a (eformId 1556, mã DVC 1.011442.02). Theo mapping DOM ngày 12/11/2026 (Mapping_Don_dang_ky.xlsx,
Mapping_Nguoi_uy_quyen.xlsx + ảnh ánh xạ đính kèm):

1. ĐƠN (purpose "registration_form"): ô eForm khớp class eform-element-<Key>; radio/checkbox tick theo nhãn.
2. ỦY QUYỀN (purpose "authorized_person"): khối doiTuongKhac* = bên ủy quyền (thường là ngân hàng cấp Giấy giới
   thiệu → loại "Doanh nghiệp"; cá nhân/tổ chức thì đổi loại theo ``authorizedSubject``).
3. ĐÍNH KÈM: 12 thành phần theo mã KQ003703…KQ003714 + "File đính kèm khác"; hỗ trợ tách giấy theo trang.
"""

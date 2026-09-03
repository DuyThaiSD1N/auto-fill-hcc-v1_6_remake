"""Thủ tục "[Bắc Ninh] Đăng ký mua, thuê mua, thuê nhà ở xã hội, vay vốn để hộ gia đình, cá nhân tự
xây dựng hoặc cải tạo, sửa chữa nhà ở" trên cổng DVC tỉnh Bắc Ninh (Liferay eForm 2836).

Cấu trúc y như [[ho_tro_chi_phi_hoa_tang_bac_ninh]]: 3 phần trên cổng —
1. ĐƠN đăng ký (eForm Giấy xác nhận về điều kiện nhà ở, Mẫu số 02) — điền các ô element_762xx theo NAME
   để không nhầm giữa người kê khai (mục 2-5) và vợ/chồng (mục 6, trùng class CapNgay/Tai/CCCD).
2. KHỐI NGƯỜI ĐƯỢC ỦY QUYỀN — chỉ khi nộp thay & có Văn bản ủy quyền; điền doiTuongKhac* (fill-bacninh.js
   fillAuthorizedPersonBacNinh). Mapper phân nhánh theo options["purpose"].
3. ĐÍNH KÈM — thành phần G17-KQ005445 "Giấy tờ chứng minh điều kiện về nhà ở": Mẫu 02 → Bản chính,
   CCCD + Giấy chứng nhận kết hôn → Bản sao; giấy tờ chứng minh đối tượng (mục 8) → ô bổ sung.
"""

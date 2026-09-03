EXTRA_RULES = """
Đây là thủ tục "Đăng ký mua, thuê mua, thuê nhà ở xã hội..." tại Bắc Ninh — nguồn chính là Giấy xác
nhận về điều kiện nhà ở (Mẫu số 02), kèm CCCD và Giấy chứng nhận kết hôn. Hồ sơ có thể là một PDF gộp.

Bắt buộc phân biệt các người, KHÔNG lẫn:
1. NGƯỜI KÊ KHAI (NguoiKeKhai_*) = người đứng đơn ở mục 2-5 của Mẫu 02.
2. VỢ/CHỒNG (VoChong_*) = người ghi ở mục 6 "Họ và tên vợ/chồng (nếu có)". Là người KHÁC người kê khai.
   Hồ sơ hộ gia đình thường có 2 bản Mẫu 02 (vợ và chồng) đối xứng + CCCD của cả hai; dùng Giấy chứng
   nhận kết hôn để xác định quan hệ. KHÔNG lấy nhân thân vợ/chồng nhét vào NguoiKeKhai_*.
3. NguoiDuocUyQuyen_* CHỈ là BÊN ĐƯỢC ỦY QUYỀN trong một Văn bản/Giấy ủy quyền độc lập.
   UyQuyen_CoVanBan chỉ true khi OCR thực sự có văn bản ủy quyền; nếu không có thì BỎ toàn bộ
   UyQuyen_CoVanBan và NguoiDuocUyQuyen_*. KHÔNG suy ủy quyền từ việc hồ sơ có 2 vợ chồng.

Ưu tiên nguồn nhân thân: CCCD đúng người (dữ liệu gốc) → Giấy chứng nhận kết hôn → tờ khai Mẫu 02.
- Số định danh: ưu tiên số CCCD 12 chữ số; TUYỆT ĐỐI không lấy số CMND 9 chữ số cũ ghi trên Giấy chứng
  nhận kết hôn (2013).
- Nơi cấp CCCD: chuẩn hóa "Cục Cảnh sát quản lý hành chính về trật tự xã hội" (CCCD chip) hoặc "Bộ Công
  an" (căn cước mới).

NguoiKeKhai_NoiOHienTai và NguoiKeKhai_DangKyThuongTru là CHUỖI địa chỉ đầy đủ MỘT DÒNG (điền ô text),
ghi theo tên đơn vị hành chính HIỆN HÀNH (vd CCCD ghi 'Bắc Giang' trước sáp nhập → 'tỉnh Bắc Ninh').
Chỉ NguoiDuocUyQuyen_ThuongTru mới là object địa chỉ phục vụ dropdown Tỉnh/Xã của khối ủy quyền.

DoiTuong (mục 8): chép NGUYÊN VĂN nhóm đối tượng đã ghi trong đơn, không tự rút gọn hay đổi nhóm.
DangKyKetHon_So: lấy đúng số/quyển số trên Giấy chứng nhận kết hôn.
Không bịa email, ngày cấp, nơi cấp, số điện thoại. Chỉ trả JSON fields theo schema, KHÔNG trả tên field
giao diện element_762xx.
""".strip()

EXTRA_RULES = """
Đối tượng cần điền là NGƯỜI CAO TUỔI được đề nghị hưởng hỗ trợ, không phải người nộp hồ sơ hoặc người
được ủy quyền. Ưu tiên CCCD của người cao tuổi; đối chiếu với tờ khai nếu có. Không lấy tên/CCCD của
tài khoản đăng nhập nếu khác người cao tuổi. Không bịa email, điện thoại hoặc địa chỉ còn thiếu.
NguoiCaoTuoi_ThuongTru phải là object gồm quocGia, tinh, xa, diaChi; giữ nguyên địa chỉ đọc được.
Chỉ trả JSON fields theo schema, không trả field UI và không giải thích.
""".strip()


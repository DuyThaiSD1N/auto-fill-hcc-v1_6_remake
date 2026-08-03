"""Facts nguồn cho hồ sơ thay đổi nội dung đăng ký hộ kinh doanh.

LLM chỉ đọc dữ kiện hiện tại và nội dung đề nghị. Quyết định trang nào phải sửa,
có đổi tên hay không và mã ngành nào phải xóa thuộc về mapper tất định.
"""

FIELDS: list[dict] = [
    {"name": "HoKinhDoanh_MaSo", "desc": "Mã số hộ kinh doanh/mã số thuế, ưu tiên trên Thông báo thay đổi."},
    {"name": "HoKinhDoanh_MaDangKy", "desc": "Mã số đăng ký hộ kinh doanh nếu đọc được."},
    {"name": "HoKinhDoanh_MaNoiBo", "desc": "Mã số nội bộ trong hệ thống nếu tài liệu có ghi."},
    {"name": "HienTai_Ten", "desc": "Tên hiện tại trên Giấy chứng nhận đăng ký hộ kinh doanh."},
    {"name": "DeNghi_Ten", "desc": "Tên mới CHỈ khi Thông báo ghi rõ đề nghị thay đổi tên hộ kinh doanh."},
    {"name": "HienTai_TruSo", "desc": "Địa chỉ trụ sở hiện tại trên GCN, object {quocGia,tinh,xa,diaChi}."},
    {"name": "DeNghi_TruSo", "desc": "Địa chỉ trụ sở mới CHỈ khi Thông báo ghi thay đổi trụ sở, object {quocGia,tinh,xa,diaChi}."},
    {"name": "DeNghi_KhongKinhDoanhTaiTruSo", "desc": "Boolean, chỉ trả true khi ô Không kinh doanh tại trụ sở được đánh dấu trong mục thay đổi trụ sở."},
    {"name": "DeNghi_TruSo_DienThoai", "desc": "Điện thoại trụ sở mới nếu thuộc nội dung thay đổi."},
    {"name": "DeNghi_TruSo_Email", "desc": "Email trụ sở mới nếu thuộc nội dung thay đổi."},
    {"name": "DeNghi_TruSo_Fax", "desc": "Fax trụ sở mới nếu thuộc nội dung thay đổi."},
    {"name": "DeNghi_TruSo_Website", "desc": "Website trụ sở mới nếu thuộc nội dung thay đổi."},
    {"name": "HienTai_NganhNghe", "desc": "Mọi ngành hiện có trên GCN, array {ma,ten,chinh}."},
    {"name": "DeNghi_NganhNgheBoSung", "desc": "CHỈ các ngành đề nghị bổ sung, array {ma,ten,chinh}; giữ dòng có tên dù mã trống."},
    {"name": "DeNghi_NganhNgheBaiBo", "desc": "CHỈ các ngành đề nghị bỏ, array {ma,ten}; ưu tiên mã 4 chữ số ghi trên Thông báo."},
    {"name": "HienTai_ChuHo", "desc": "Chủ hộ hiện tại trên GCN, object {hoTen,ngaySinh,gioiTinh,soDinhDanh,diaChi,dienThoai,email,fax,website}."},
    {"name": "DeNghi_ChuHo", "desc": "Chủ hộ mới CHỈ khi mục thay đổi chủ hộ được kê khai, cùng cấu trúc HienTai_ChuHo."},
    {"name": "DeNghi_ChuHo_LoaiThayDoi", "desc": "Loại đăng ký thay đổi chủ hộ đúng theo nội dung Thông báo nếu đọc được."},
    {"name": "DeNghi_ChuHo_LyDo", "desc": "Lý do thay đổi chủ hộ nếu Thông báo có ghi rõ; không tự đoán."},
    {"name": "HienTai_Von", "desc": "Vốn hiện tại trên GCN, số tiền đồng."},
    {"name": "DeNghi_Von", "desc": "Vốn mới CHỈ khi Thông báo ghi thay đổi vốn, số tiền đồng."},
    {"name": "DeNghi_Von_HinhThuc", "desc": "Hình thức tăng hoặc giảm vốn đúng theo Thông báo."},
    {"name": "DeNghi_Von_ThoiDiem", "desc": "Thời điểm tăng/giảm vốn, dd/mm/yyyy nếu có."},
    {"name": "DeNghi_Thue", "desc": "Thông tin thuế mới CHỈ khi thuộc nội dung thay đổi, object {diaChiNhanThongBao,dienThoai,fax,email,ngayBatDau,soLaoDong,phuongPhapTinh}."},
    {"name": "NguoiNop", "desc": "Người ký/nộp theo Thông báo hoặc ủy quyền, object {hoTen,ngaySinh,gioiTinh,soDinhDanh,diaChi}."},
    {"name": "Cccd_DanhSach", "desc": "Mọi CCCD/căn cước vật lý trong hồ sơ, array {hoTen,ngaySinh,gioiTinh,soDinhDanh,ngayCap,noiCap,diaChi}. Không tự gán vai trò."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "raw" for name in ALLOWED}

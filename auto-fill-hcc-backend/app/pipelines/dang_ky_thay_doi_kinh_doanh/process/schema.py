"""Facts nguồn cho hồ sơ thay đổi nội dung đăng ký hộ kinh doanh.

LLM chỉ đọc dữ kiện hiện tại và nội dung đề nghị. Quyết định trang nào phải sửa,
có đổi tên hay không và mã ngành nào phải xóa thuộc về mapper tất định.
"""

FIELDS: list[dict] = [
    {"name": "HoKinhDoanh_MaSo", "desc": (
        "Mã số hộ kinh doanh. "
        "CHỈ lấy khi có nhãn rõ ràng 'Mã số hộ kinh doanh', 'MST', 'Số đăng ký' trên Thông báo thay đổi hoặc GCN đăng ký HKD. "
        "TUYỆT ĐỐI KHÔNG lấy số định danh/CCCD/CMND của bất kỳ cá nhân nào (dù xuất hiện dưới bất kỳ nhãn nào). "
        "Nếu không tìm thấy nhãn rõ ràng → để trống."
    )},
    {"name": "HoKinhDoanh_MaDangKy", "desc": (
        "Mã số đăng ký hộ kinh doanh nếu đọc được (khác HoKinhDoanh_MaSo). "
        "TUYỆT ĐỐI KHÔNG lấy số CCCD/CMND."
    )},
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
    {
        "name": "HasMultipleCCCD",
        "desc": (
            "Boolean: true nếu hồ sơ có 2+ CCCD với số định danh khác nhau, false nếu chỉ có 1 CCCD. "
            "Dùng để xác định người nộp có phải chủ hộ hay không."
        ),
    },
    {
        "name": "UyQuyen_CoGiayUyQuyen",
        "desc": (
            "Boolean: true nếu hồ sơ có giấy ủy quyền văn bản riêng, false nếu chỉ có 2 CCCD. "
            "CHỈ điền khi HasMultipleCCCD=true VÀ CCCD thứ 2 KHÁC chủ hộ."
        ),
    },
    {
        "name": "UyQuyen_NguoiUyQuyen_HoTen",
        "desc": (
            "Họ tên người ủy quyền (= CHỦ HỘ KINH DOANH). "
            "CHỈ điền khi HasMultipleCCCD=true VÀ có người nộp thay."
        ),
    },
    {
        "name": "UyQuyen_NguoiUyQuyen_SoDinhDanh",
        "desc": (
            "Số CCCD người ủy quyền (= số CCCD CHỦ HỘ). "
            "CHỈ điền khi HasMultipleCCCD=true VÀ có người nộp thay."
        ),
    },
    {
        "name": "UyQuyen_NguoiDuocUyQuyen_HoTen",
        "desc": (
            "Họ tên người được ủy quyền (= NGƯỜI ĐI NỘP HỒ SƠ THAY). "
            "Đọc từ CCCD của người nộp thay. CHỈ điền khi HasMultipleCCCD=true VÀ CCCD thứ 2 KHÁC chủ hộ."
        ),
    },
    {
        "name": "UyQuyen_NguoiDuocUyQuyen_SoDinhDanh",
        "desc": (
            "Số CCCD người được ủy quyền. "
            "CHỈ điền khi HasMultipleCCCD=true VÀ CCCD thứ 2 KHÁC chủ hộ."
        ),
    },
    {
        "name": "UyQuyen_NguoiDuocUyQuyen_GioiTinh",
        "desc": (
            "Giới tính người được ủy quyền: 'Nam' hoặc 'Nữ'. "
            "CHỈ điền khi HasMultipleCCCD=true VÀ CCCD thứ 2 KHÁC chủ hộ."
        ),
    },
    {
        "name": "UyQuyen_NguoiDuocUyQuyen_NgaySinh",
        "desc": (
            "Ngày sinh người được ủy quyền, dd/mm/yyyy. "
            "CHỈ điền khi HasMultipleCCCD=true VÀ CCCD thứ 2 KHÁC chủ hộ."
        ),
    },
    {
        "name": "UyQuyen_NguoiDuocUyQuyen_DiaChi",
        "desc": (
            "Địa chỉ người được ủy quyền, object {quocGia,tinh,xa,diaChi}. "
            "Đọc từ 'Nơi thường trú' trên CCCD của người nộp thay. "
            "CHỈ điền khi HasMultipleCCCD=true VÀ CCCD thứ 2 KHÁC chủ hộ."
        ),
    },
    {
        "name": "UyQuyen_NguoiDuocUyQuyen_DienThoai",
        "desc": "Số điện thoại bên được ủy quyền nếu Giấy ủy quyền có ghi.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "raw" for name in ALLOWED}

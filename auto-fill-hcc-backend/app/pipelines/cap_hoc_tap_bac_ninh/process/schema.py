"""Schema trích xuất nhân thân HỌC SINH/SINH VIÊN (chủ hồ sơ) cho khối "được ủy quyền" Bắc Ninh 1.014581.

Thủ tục "Chính sách hỗ trợ chi phí học tập cho HSSV" trên cổng Bắc Ninh KHÔNG có eForm kê khai
(toàn bộ Mẫu 01 nằm trên giấy, scan đính kèm). Việc điền duy nhất là khối `doiTuongKhac*` — cổng gọi
là "Thông tin trong trường hợp được ủy quyền", nhưng NGƯỜI điền vào đó CHÍNH LÀ HỌC SINH/SINH VIÊN
(chủ hồ sơ), vì HSSV thường chưa có định danh mức 2/VNeID nên cha/mẹ dùng tài khoản của mình nộp thay
(cổng tự điền người nộp từ VNeID). Vì vậy schema chỉ mô tả 1 người: HSSV.
"""

FIELDS: list[dict] = [
    {
        "name": "HocSinh_HoTen",
        "desc": (
            "Họ và tên HỌC SINH/SINH VIÊN (người đứng đơn Mẫu 01 'ĐƠN ĐỀ NGHỊ HỖ TRỢ CHI PHÍ HỌC TẬP', "
            "người trên Bằng tốt nghiệp THCS/THPT, người được xác nhận đang học ở Mẫu 02, và là "
            "'con tôi/cháu tôi' trong Đơn xin xác nhận ủy quyền). VIẾT IN HOA. TUYỆT ĐỐI không lấy tên "
            "người nộp thay (cha/mẹ/người giám hộ = 'Tên tôi là'/'tôi' trong Đơn ủy quyền) hay cán bộ ký Lời chứng."
        ),
    },
    {
        "name": "HocSinh_GioiTinh",
        "desc": "Giới tính HSSV, chỉ trả 'Nam' hoặc 'Nữ' khi giấy tờ ghi rõ (CCCD/Bằng tốt nghiệp/Mẫu 01).",
    },
    {
        "name": "HocSinh_SoDinhDanh",
        "desc": (
            "Số định danh cá nhân/số thẻ CCCD của HSSV, chỉ giữ 12 chữ số. Nguồn chuẩn: thẻ CCCD có họ tên "
            "trùng HSSV; đối chiếu Mẫu 01 ('Số Thẻ CCCD') và Đơn ủy quyền ('Số CCCD' của con). KHÔNG lấy "
            "số CCCD của người nộp thay."
        ),
    },
    {
        "name": "HocSinh_NgayCap",
        "desc": "Ngày cấp CCCD của HSSV, dd/mm/yyyy; lấy ở mặt sau thẻ CCCD của HSSV, không lấy ngày cấp CCCD người nộp thay.",
    },
    {
        "name": "HocSinh_NoiCap",
        "desc": (
            "Nơi cấp CCCD của HSSV — dòng cơ quan ký ở mặt sau CCCD (thường 'Cục Cảnh sát quản lý hành chính "
            "về trật tự xã hội'). Ghi đầy đủ theo CCCD."
        ),
    },
    {
        "name": "HocSinh_NgaySinh",
        "desc": "Ngày sinh HSSV, dd/mm/yyyy; nguồn chuẩn CCCD, đối chiếu Bằng tốt nghiệp và Mẫu 01.",
    },
    {
        "name": "HocSinh_Email",
        "desc": "Email HSSV nếu hồ sơ ghi rõ; đa số hồ sơ không có → bỏ trống, TUYỆT ĐỐI không bịa.",
    },
    {
        "name": "HocSinh_SoDienThoai",
        "desc": "Số điện thoại liên hệ ghi trong Mẫu 01 (đơn đề nghị); chỉ giữ chữ số.",
    },
    {
        "name": "HocSinh_ThuongTru",
        "desc": (
            "Nơi thường trú HSSV dạng object {quocGia,tinh,xa,diaChi}. Ưu tiên địa chỉ trên Mẫu 01/Đơn ủy "
            "quyền (dùng ĐỊA GIỚI MỚI sau sáp nhập, ví dụ 'Phường Bắc Giang, tỉnh Bắc Ninh'); KHÔNG dùng "
            "địa danh cũ trên CCCD (ví dụ 'Thọ Xương, TP. Bắc Giang, Bắc Giang'). diaChi là phần chi tiết "
            "nhất (số nhà, ngõ, tổ dân phố)."
        ),
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["HocSinh_NgaySinh"] = "x-date"
COMPACT_COMP_BY_NAME["HocSinh_NgayCap"] = "x-date"
COMPACT_COMP_BY_NAME["HocSinh_ThuongTru"] = "x-select-area"

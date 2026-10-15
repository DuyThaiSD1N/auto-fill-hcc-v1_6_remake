"""Bổ sung ô còn trống trên tờ khai đăng ký kết hôn sau khi điền (chat/field_review)."""

PROCEDURE_KEYS = ("ket-hon",)

# Theo chấm đỏ của eForm sau "Xem trước". Mỗi bên: họ tên, dân tộc, loại giấy tờ, khối nơi cư trú trong nước,
# tình trạng hôn nhân.
REQUIRED = (
    "HoTenBenNu", "DanTocBenNu", "LoaiGiayToDinhDanh_BenNu", "NoiCuTru_BenNu_TrongNuoc",
    "LoaiTinhTrangHonNhan_BenNu",
    "HoTenBenNam", "DanTocBenNam", "LoaiGiayToDinhDanh_BenNam", "NoiCuTru_BenNam_TrongNuoc",
    "LoaiTinhTrangHonNhan_BenNam",
)

# Yêu cầu chung của hai bên nhưng nằm dưới tiêu đề "II. Thông tin bên nam" → hỏi không kèm tên phần.
# ThongTin = ô "Số lượng bản sao", cổng chỉ dựng sau khi chọn "Có" ở ô Đề nghị cấp bản sao.
NO_SECTION = ("loaiDangKy", "CapBanSao", "ThongTin")

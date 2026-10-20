"""Bổ sung ô còn trống trên tờ khai đăng ký kết hôn có yếu tố nước ngoài sau khi điền (chat/field_review).

Cùng eForm với đăng ký kết hôn (chỉ không có ô số nhà / tổ dân phố của nơi cư trú) → cùng bộ ô bắt buộc.
"""

PROCEDURE_KEYS = ("ket-hon-nuoc-ngoai",)

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

# Ô "Đề nghị cấp bản sao" (Có/Không) và ô số lượng cổng chỉ dựng sau khi chọn Có: công dân nói "có, ba bản" hoặc chỉ
# "ba bản" thì chọn Có rồi điền luôn số lượng, không hỏi lại.
COPY_QUANTITY = ("CapBanSao", "ThongTin")

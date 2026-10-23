"""Bổ sung ô còn trống trên tờ khai đăng ký khai sinh cho người đã có hồ sơ, giấy tờ cá nhân (chat/field_review)."""

PROCEDURE_KEYS = ("khai-sinh-da-co-ho-so",)

# Theo chấm "Trường này không được bỏ trống" của eForm: nơi cư trú người yêu cầu, loại đăng ký, loại khai sinh và các ô
# chính của người được khai sinh (họ tên, ngày sinh, giới tính, quốc tịch, nơi sinh, quê quán).
REQUIRED = (
    "nycNoiCuTru", "LoaiDangKy", "nksLoaiKhaiSinh", "HoTenKS", "NgaySinhChon", "GioiTinhKS", "QuocTichKS",
    "nksNoiSinh", "nksQueQuan",
)

# SoLuong = ô "(27) Đề nghị cấp bản sao" (nhập số bản): yêu cầu chung nhưng nằm ngay sau khối "IV. Thông tin về người
# cha" (tờ khai không có phần V) → hỏi không kèm tên phần. Tờ khai này không có cặp Có/Không + ô số lượng.
NO_SECTION = ("SoLuong",)

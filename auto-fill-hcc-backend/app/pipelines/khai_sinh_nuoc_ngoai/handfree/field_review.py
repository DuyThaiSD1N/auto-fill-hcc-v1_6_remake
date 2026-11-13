"""Bổ sung ô còn trống trên eForm khai sinh có yếu tố nước ngoài (cổng Bộ Tư pháp, mẫu 2093 — chat/field_review)."""

PROCEDURE_KEYS = ("khai-sinh-nuoc-ngoai",)

# Theo chấm "Trường này không được bỏ trống" của eForm khai sinh: nơi cư trú người yêu cầu, loại đăng ký, loại khai
# sinh và các ô chính của người được khai sinh. Quốc tịch con theo thỏa thuận của cha mẹ nên mapper hay để trống.
REQUIRED = (
    "nycNoiCuTru", "LoaiDangKy", "nksLoaiKhaiSinh", "HoTenKS", "NgaySinhChon", "GioiTinhKS", "QuocTichKS",
    "nksNoiSinh", "nksQueQuan",
)

# SoLuong = ô số bản của "(27) Đề nghị cấp bản sao", nằm ngay sau khối "IV. Thông tin về người cha" → hỏi không kèm
# tên phần.
NO_SECTION = ("SoLuong",)

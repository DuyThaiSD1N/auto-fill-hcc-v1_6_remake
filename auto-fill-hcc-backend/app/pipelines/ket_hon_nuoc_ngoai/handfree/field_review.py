"""Bổ sung ô còn trống trên tờ khai đăng ký kết hôn có yếu tố nước ngoài sau khi điền (chat/field_review).

Cùng eForm với đăng ký kết hôn (chỉ không có ô số nhà / tổ dân phố của nơi cư trú) → cùng bộ ô bắt buộc.
"""

PROCEDURE_KEYS = ("ket-hon-nuoc-ngoai",)

# Theo chấm đỏ của eForm sau "Xem trước", thêm số định danh + số giấy tờ. Mỗi bên: họ tên, dân tộc, số định danh, loại
# giấy tờ, số giấy tờ, ô chọn nơi cư trú (Trong nước / Khác), khối nơi cư trú trong nước, tình trạng hôn nhân, số lần
# kết hôn (cổng không đánh sao nhưng tờ khai thiếu thì vô nghĩa). Khối trong nước chỉ hiện sau khi tích "Trong nước"
# — thiếu ô chọn thì lúc chưa tích không còn ô bắt buộc nào ở dòng nơi cư trú, ô bị tô cam rồi cổng chặn Xem trước.
REQUIRED = (
    "HoTenBenNu", "DanTocBenNu", "SoDinhDanh_BenNu", "LoaiGiayToDinhDanh_BenNu", "SoGiayToDinhDanh_BenNu",
    "NoiCuTru_BenNu", "NoiCuTru_BenNu_TrongNuoc", "LoaiTinhTrangHonNhan_BenNu", "SoLanKetHon_BenNu",
    "HoTenBenNam", "DanTocBenNam", "SoDinhDanh_BenNam", "LoaiGiayToDinhDanh_BenNam", "SoGiayToDinhDanh_BenNam",
    "NoiCuTru_BenNam", "NoiCuTru_BenNam_TrongNuoc", "LoaiTinhTrangHonNhan_BenNam", "SoLanKetHon_BenNam",
    # Ô con của khối chi tiết tình trạng hôn nhân (khối 5: từ ngày / đến ngày; khối 6: mô tả; ly hôn; góa): cổng không
    # đánh sao nhưng tờ khai thiếu thì vô nghĩa. Extension chỉ đếm ô đang hiện → chỉ bắt buộc khi chọn đúng tình trạng.
    *(name for side in ("BenNu", "BenNam")
      for name in (f"TuNgay_{side}", f"DenNgay_{side}", f"NhapMoTaTinhTrangHonNhan_{side}", f"{side}_SoBanAn",
                   f"{side}_NgayQD", f"{side}_CoQuanCap", f"{side}_SoBanAn1", f"{side}_NgayQD1", f"{side}_CoQuanCap1")),
)

# Yêu cầu chung của hai bên nhưng nằm dưới tiêu đề "II. Thông tin bên nam" → hỏi không kèm tên phần.
# ThongTin = ô "Số lượng bản sao", cổng chỉ dựng sau khi chọn "Có" ở ô Đề nghị cấp bản sao.
NO_SECTION = ("loaiDangKy", "CapBanSao", "ThongTin")

# Ô "Đề nghị cấp bản sao" (Có/Không) và ô số lượng cổng chỉ dựng sau khi chọn Có: công dân nói "có, ba bản" hoặc chỉ
# "ba bản" thì chọn Có rồi điền luôn số lượng, không hỏi lại.
COPY_QUANTITY = ("CapBanSao", "ThongTin")

# Vòng bổ sung bản 2: agent điều phối + agent chuyên môn (sửa ô bất kỳ, sửa nhiều ô một câu).
FIELD_REVIEW_V2 = True

# Vòng bổ sung bản 2: cách người dân gọi hai bên trên tờ khai (agent điều phối dùng để tìm đúng phần khi công dân sửa ô).
VOCABULARY = """- "chồng", "chú rể", "anh ấy", "bên trai", "nhà trai" = phần thông tin bên nam.
- "vợ", "cô dâu", "chị ấy", "bên gái", "nhà gái" = phần thông tin bên nữ.
- "người yêu cầu", "người đi nộp" = phần thông tin người yêu cầu (nếu tờ khai có)."""


# Khối chi tiết tình trạng hôn nhân (dựng sau khi chọn tình trạng): các ô con là input thường không có thẻ x-* riêng
# (BenNu_SoBanAn, BenNu_NgayQD, BenNu_CoQuanCap…) → khai khối lồng để extension tách từng ô, không thì cả khối thành
# MỘT ô và chỉ hỏi được ô đầu (số bản án).
_MARRIAGE_BLOCKS = {"BenNu": "vo", "BenNam": "chong"}
NESTED = tuple(
    name
    for side, spouse in _MARRIAGE_BLOCKS.items()
    for name in (f"{spouse}TinhTrangHonNhan5", f"{spouse}TinhTrangHonNhan6", f"TTHN_DaChet_{side}",
                 f"TTHN_LyHon_{side}")
)
# Extension chưa có cờ supportsFieldReviewNested vẫn bổ sung được (khối thành một ô như trước) — không tắt cả vòng hỏi.
NESTED_OPTIONAL = True

# Vòng bổ sung bản 2: cụm ô hỏi liền nhau; công dân nói luôn nhiều ô cùng cụm thì điền cả. Cụm Hôn nhân gồm cả ô con
# của các khối trên (tên ô con: thời hạn TuNgay/DenNgay, mô tả, số / ngày / cơ quan của bản án, giấy chứng tử).
GROUPS = tuple(
    group
    for side, spouse in _MARRIAGE_BLOCKS.items()
    for group in (
        ("Nhân thân", (f"HoTen{side}", f"NgaySinh{side}", f"DanToc{side}", f"DanToc{side}Khac", f"QuocTich{side}")),
        ("Giấy tờ tùy thân", (f"SoDinhDanh_{side}", f"LoaiGiayToDinhDanh_{side}", f"TenGiayTo_{side}",
                              f"SoGiayToDinhDanh_{side}", f"NgayCapDD_{side}", f"NoiCapDD_{side}")),
        ("Nơi cư trú", (f"LoaiCuTru_{side}", f"NoiCuTru_{side}", f"NoiCuTru_{side}_TrongNuoc",
                        f"NoiCuTru_{side}_NuocNgoai")),
        ("Hôn nhân", (f"SoLanKetHon_{side}", f"LoaiTinhTrangHonNhan_{side}", f"TuNgay_{side}", f"DenNgay_{side}",
                      f"NhapMoTaTinhTrangHonNhan_{side}", f"{side}_SoBanAn1", f"{side}_CoQuanCap1", f"{side}_NgayQD1",
                      f"{side}_SoBanAn", f"{side}_NgayQD", f"{side}_CoQuanCap")),
    )
)

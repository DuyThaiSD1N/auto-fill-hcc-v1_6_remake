"""Bổ sung ô còn trống trên Đơn đề nghị đăng ký hành nghề luật sư với tư cách cá nhân sau khi điền (chat/field_review)."""

PROCEDURE_KEYS = ("dang-ky-hanh-nghe-luat-su-voi-tu-cach-ca-nhan",)

# Ô bắt buộc theo Mẫu TP-LS-05-sđ: Kính gửi, nhân thân + giấy tờ tùy thân (1)–(3), nơi thường trú (4) và nơi ở hiện
# tại (5) đủ 3 ô, Thẻ luật sư số + ngày cấp + Đoàn Luật sư, tên/địa chỉ tổ chức ký HĐLĐ, nơi lập đơn, ngày lập và họ tên
# người ký. Điện thoại / fax / email của luật sư và của tổ chức, website không bắt buộc. Ô cổng chấm đỏ khi bấm Xem
# trước vẫn được extension gộp thêm vào danh sách.
REQUIRED = (
    "KinhGuiC",
    "HoVaTenC", "GioiTinhC", "NgaySinhC",
    "LoaiGiayToDinhDanhC", "SoDinhDanhC", "NgayCapDDC", "NoiCapDDC",
    "TT_TinhThanhC", "TT_PhuongXaC", "TT_SoNhaToDanPhoC",
    "NO_TinhThanhC", "NO_PhuongXaC", "NO_SoNhaToDanPhoC",
    "TheLuatSuSoC", "NgayCapTheC", "ThanhVienDoanC",
    "CoQuan_HopDongC",
    "NoiLapC", "Ngay", "Thang", "Nam", "ChuKyNguoiDeNghiC",
)

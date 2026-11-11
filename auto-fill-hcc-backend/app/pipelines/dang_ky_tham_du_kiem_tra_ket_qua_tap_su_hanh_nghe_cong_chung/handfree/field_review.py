"""Bổ sung ô còn trống trên Giấy đăng ký tham dự kiểm tra kết quả tập sự công chứng sau khi điền (chat/field_review)."""

PROCEDURE_KEYS = ("dang-ky-tham-du-kiem-tra-ket-qua-tap-su-hanh-nghe-cong-chung",)

# Mọi dòng của Mẫu TP-TSCC-10 đều phải khai: nhân thân, nơi ở hiện tại, điện thoại, giấy tờ tùy thân, nơi/ngày tập sự,
# công chứng viên hướng dẫn, quyết định công nhận, các kỳ đã tham dự ("Chưa" nếu chưa), nơi làm giấy. Kỳ kiểm tra và
# Email không bắt buộc (mẫu để trống được). Ô cổng chấm đỏ khi bấm Xem trước vẫn được extension gộp thêm vào danh sách.
REQUIRED = (
    "KinhGui",
    "HoVaTenC", "GioiTinhC", "NgaySinhC",
    "LoaiGiayToDinhDanhC", "SoDinhDanhC", "NgayCapDDC", "NoiCapDDC",
    "NO_TinhThanhC", "NO_PhuongXaC", "NO_SoNhaToDanPhoC", "SoDienThoai",
    "ToChucTapSu", "CongChungVienHuongDan", "NgayBatDauTapSu", "NgayKetThucTapSu",
    "SoQuyetDinhCongNhan", "NgayQuyetDinhCongNhan", "SoTuPhapCongNhan",
    "DaTungThamDuKyKiemTra", "LamTai",
)

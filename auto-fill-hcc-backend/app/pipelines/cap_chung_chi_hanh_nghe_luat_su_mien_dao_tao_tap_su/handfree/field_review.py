"""Bổ sung ô còn trống trên văn bản đề nghị cấp chứng chỉ hành nghề luật sư sau khi điền (chat/field_review)."""

PROCEDURE_KEYS = ("cap-chung-chi-hanh-nghe-luat-su-mien-dao-tao-tap-su",)

# Người đề nghị: nhân thân, nơi thường trú và nơi ở hiện tại (tỉnh, xã, chi tiết), điện thoại, giấy tờ tùy thân; nội
# dung hồ sơ của trường hợp MIỄN tập sự: lý do miễn, khen thưởng/kỷ luật (không có thì ghi "không" theo hướng dẫn
# trên mẫu), truy cứu trách nhiệm hình sự; Kính gửi và nơi làm đơn. Ba ô kết quả kiểm tra tập sự và ô đề nghị cấp lại
# chỉ dành cho trường hợp khác → không bắt buộc. Bảng quá trình hoạt động (x-table) vòng hỏi chưa đọc được.
# Ô cổng chấm đỏ khi bấm Xem trước vẫn được extension gộp thêm vào danh sách bắt buộc.
REQUIRED = (
    "KinhGui",
    "HoVaTenC", "GioiTinhC", "NgaySinhC", "QuocTichC",
    "TT_TinhThanhC", "TT_PhuongXaC", "TT_NoiThuongTruC",
    "NO_TinhThanhC", "NO_PhuongXaC", "TT_NoiOHienTaiC",
    "SoDienThoai", "LoaiGiayToDinhDanhC", "SoDinhDanhC", "NgayCapDDC", "NoiCapDDC",
    "HoSo_LyDoMien", "HoSo_KhenThuong", "HoSo_TruyCuuTrachNhiem",
    "LamTai",
)

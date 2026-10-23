"""Bổ sung ô còn trống trên tờ khai đăng ký chấm dứt giám hộ sau khi điền (chat/field_review).

Cùng pipeline với đăng ký giám hộ nhưng eForm 1912 đặt tên ô khác (C = người yêu cầu, M = người giám hộ, Cha = người
được giám hộ) → cấu hình riêng."""

PROCEDURE_KEYS = ("dang-ky-cham-dut-giam-ho",)

# Người giám hộ (II) và người được giám hộ (III): họ tên, ngày sinh, giới tính, quốc tịch, nơi cư trú (tỉnh + xã) như
# tờ khai đăng ký giám hộ; lý do chấm dứt là nội dung chính của yêu cầu. Người yêu cầu (I) cổng điền sẵn từ tài khoản.
# Ô cổng chấm đỏ khi bấm Xem trước vẫn được extension gộp thêm vào danh sách bắt buộc.
REQUIRED = (
    "HoVaTenM", "NgaySinhM", "GioiTinhM", "QuocTichM", "TT_TinhThanhM", "TT_PhuongXaM",
    "HoVaTenCha", "NgaySinhCha", "GioiTinhCha", "QuocTichCha", "TT_TinhThanhCha", "TT_PhuongXaCha",
    "LyDoChamDuQH",
)

# (21) đăng ký giám hộ đã cấp, (22) lý do, (23) đề nghị cấp bản sao: yêu cầu chung của hồ sơ nhưng nằm dưới tiêu đề
# "III. Thông tin về người được giám hộ" → hỏi không kèm tên phần. ThongTin = ô "Số lượng bản sao", cổng chỉ dựng sau
# khi chọn "Có".
NO_SECTION = ("SoDKTai", "NgayDKTai", "CoQuanDk", "LyDoChamDuQH", "CapBanSao", "ThongTin")

# Công dân nói "có, ba bản" hoặc chỉ "ba bản" thì chọn Có rồi điền luôn số lượng, không hỏi lại.
COPY_QUANTITY = ("CapBanSao", "ThongTin")

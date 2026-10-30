"""Bổ sung ô còn trống trên trang nộp hồ sơ 4 tab cổng Bắc Ninh (tab khối người ủy quyền / tab Nhập đơn đăng ký). Tên
ô = khoá class eform-element-<Khoá> của ô đơn / phần đuôi id doiTuongKhac* của khối ủy quyền."""

PROCEDURE_KEYS = ("dang-ky-bien-dong-chuyen-nhuong-bac-ninh",)

# Cổng không đánh dấu ô bắt buộc trên đơn → mọi ô trống là không bắt buộc.
REQUIRED = ()

# "Kính gửi" do cổng tự ghi theo cơ quan tiếp nhận đã chọn ở tab đầu.
NO_ASK = ("KinhGui",)

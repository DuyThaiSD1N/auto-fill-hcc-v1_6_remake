"""Bổ sung ô còn trống trên trang nộp hồ sơ 4 tab cổng Bắc Ninh (tab khối người ủy quyền / tab Nhập đơn đăng ký). Tên
ô = khoá class eform-element-<Khoá> của ô đơn / phần đuôi id doiTuongKhac* của khối ủy quyền."""

PROCEDURE_KEYS = ("dinh-chinh-gcn-da-cap-bac-ninh", "dinh-chinh-gcn-da-cap-1115476-bac-ninh")

# Cổng không đánh dấu ô bắt buộc trên đơn → mọi ô trống là không bắt buộc.
REQUIRED = ()

# "Kính gửi" do cổng tự ghi theo cơ quan tiếp nhận đã chọn ở tab đầu.
NO_ASK = ("KinhGui",)

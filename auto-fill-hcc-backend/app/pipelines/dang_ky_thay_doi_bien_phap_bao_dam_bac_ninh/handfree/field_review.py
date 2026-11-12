"""Bổ sung ô còn trống ở tab "Chọn cơ quan tiếp nhận" (khối người ủy quyền) và "Nhập đơn đăng ký" (eForm Mẫu 02a) của
cổng Bắc Ninh 1.011442. Tên ô = khoá class eform-element-<Khoá> của ô đơn / phần đuôi id doiTuongKhac* của khối ủy quyền."""

PROCEDURE_KEYS = ("dang-ky-thay-doi-bien-phap-bao-dam-bac-ninh",)

# Cổng không đánh dấu ô bắt buộc trên eForm (chỉ có câu báo lỗi khi lưu) → mọi ô trống là không bắt buộc.
REQUIRED = ()

# "Kính gửi" do cổng tự ghi theo cơ quan tiếp nhận ở tab đầu. "Số: (nếu có)" là ô số nguyên — số hợp đồng có chữ / "/"
# gõ vào thành dãy số sai, số đầy đủ đã nằm ở "Tên văn bản". Ô ghi rõ cách nhận chỉ dùng khi nhận qua bưu chính.
NO_ASK = ("KinhGui", "SoNeuCo", "CachThucNhanKetQuaDangKy2")

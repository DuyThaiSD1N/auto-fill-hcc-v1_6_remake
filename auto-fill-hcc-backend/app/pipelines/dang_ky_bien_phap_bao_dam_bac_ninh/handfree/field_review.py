"""Bổ sung ô còn trống ở tab "Chọn cơ quan tiếp nhận" (khối người ủy quyền) và "Nhập đơn đăng ký" (eForm Mẫu 01a) của
cổng Bắc Ninh. Tên ô = khoá class eform-element-<Khoá> của ô đơn / phần đuôi id doiTuongKhac* của khối ủy quyền."""

PROCEDURE_KEYS = ("dang-ky-bien-phap-bao-dam-bac-ninh",)

# Cổng không đánh dấu ô bắt buộc (mọi ô chỉ có câu "Không được để trống" khi lưu) → mọi ô trống là không bắt buộc.
REQUIRED = ()

# "Kính gửi" do cổng tự ghi theo cơ quan tiếp nhận đã chọn ở tab đầu. "3. Bên bảo đảm" / "(iii) Giấy chứng nhận…" là ô
# tiêu đề mang đúng giá trị của ô ngay dưới (mapper ghi cả hai) → chỉ hỏi ô dưới, rồi ghi kèm (MIRROR).
NO_ASK = ("KinhGui", "3BenBaoDam9", "IiiGiayChungNhanDoiVoiQuyenSuDungDat")

# "ô trả lời=ô ghi kèm": công dân trả lời ô trái thì extension ghi cùng giá trị vào ô phải nếu ô đó đang trống.
MIRROR = (
    "31HoVaTenDayDuDoiVoiCaNhan10tenDayDuDoiVoiToChuc11=3BenBaoDam9",
    "TenGiayChungNhan=IiiGiayChungNhanDoiVoiQuyenSuDungDat",
)

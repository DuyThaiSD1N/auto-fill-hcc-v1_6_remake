"""Bổ sung ô còn trống trên trang nộp hồ sơ 4 tab cổng Bắc Ninh 1.115462 (tab khối người ủy quyền / tab Nhập đơn đăng
ký). Tên ô = name element_<id> của ô đơn (eform 2869) / phần đuôi id doiTuongKhac* của khối ủy quyền."""

PROCEDURE_KEYS = ("xac-nhan-tiep-tuc-su-dung-dat-nong-nghiep-bac-ninh",)

# Cổng không đánh dấu ô bắt buộc trên đơn → mọi ô trống là không bắt buộc.
REQUIRED = ()

# "Kính gửi" khớp cơ quan tiếp nhận chọn ở tab đầu; phần II do UBND cấp xã xác nhận (nơi / ngày / nội dung xác nhận).
# Mapping chỉ ghi name element_<id>; extension trợ lý đặt tên ô theo class eform-element-<Khoá> nếu có, không thì theo
# name → khai cả "KinhGui" như các thủ tục Bắc Ninh khác.
NO_ASK = ("KinhGui", "element_77323", "element_77344", "element_77346", "element_77347")

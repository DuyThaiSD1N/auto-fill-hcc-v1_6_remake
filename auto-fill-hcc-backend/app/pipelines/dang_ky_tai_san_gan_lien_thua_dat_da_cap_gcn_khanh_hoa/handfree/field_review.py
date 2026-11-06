"""Bổ sung ô còn trống trên tờ khai đăng ký tài sản gắn liền với thửa đất đã cấp GCN — cổng iGate Khánh Hòa (Form.io ba
khối người nộp / chủ hồ sơ / thửa đất, cùng một form cho cả 4 trường hợp giải quyết)."""

PROCEDURE_KEYS = ("dang-ky-tai-san-gan-lien-thua-dat-da-cap-gcn-khanh-hoa",)

# Cổng đánh dấu ô bắt buộc trên component (class "required") và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó nên không khai thêm tên ô.
REQUIRED = ()

# "Nội dung yêu cầu giải quyết" là nguyên văn Đơn do trợ lý chép; khối "Thông tin tổ chức" chỉ hiện khi chủ hồ sơ là tổ
# chức; các ô ẩn của cổng (district*, LaQuyTrinhCapTinh, nvtcDate, is2Cap) không phải câu hỏi cho người dân.
NO_ASK = (
    "noidungyeucaugiaiquyet", "noidungyeucaugiaiquyet1", "district", "district1", "district2", "LaQuyTrinhCapTinh",
    "nvtcDate", "is2Cap", "soChungNhanDKKD", "soQDThanhLap", "ngayCap", "maSoThue",
)

"""Bổ sung ô còn trống trên tờ khai giao đất, cho thuê đất, chuyển mục đích sử dụng đất, gia hạn — cổng iGate Tuyên
Quang (Form.io, hai form theo quy trình).

Trợ lý chạy key gốc cho cả quy trình thường lẫn quy trình VBDLIS, nên một cấu hình phủ tên ô của cả hai form.
"""

PROCEDURE_KEYS = ("giao-thue-chuyen-muc-dich-dat-giao-rung-gia-han-tuyen-quang",)

# Cổng đánh dấu ô bắt buộc trên component / nhãn và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng các dấu
# đó nên không khai thêm tên ô.
REQUIRED = ()

# Ô tự do hoặc không áp dụng cho hồ sơ cá nhân tự nộp: tên hồ sơ, ghi chú (ghép từ Đơn), cơ quan/tổ chức, số đăng ký
# kinh doanh, khối "Thông tin người ủy quyền (nếu có)" của form 1, số bộ hồ sơ cổng để sẵn và ô ghi chú đồng bộ của
# form VBDLIS.
NO_ASK = (
    "textField", "tenHoSo", "fullname1", "agency1", "Hovaten", "Sogiaytotuythan", "sodienthoai", "diachi",
    "note", "ProcedureDossierQuantity", "ghiChu",
)

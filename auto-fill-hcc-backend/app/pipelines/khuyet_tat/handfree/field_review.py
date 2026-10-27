"""Bổ sung ô còn trống trên tờ khai xác định, xác định lại mức độ khuyết tật (Form.io, cổng Bộ Y tế dichvucongbyt.moh.gov.vn)."""

PROCEDURE_KEYS = ("xac-dinh-muc-do-khuyet-tat",)

# Cổng đánh dấu ô bắt buộc trên nhãn (label.field-required) và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó nên không khai thêm tên ô.
REQUIRED = ()

# "Ghi chú" của chủ hồ sơ là ô tự do. Bảng dạng khuyết tật (khuyetTatRadio*, mỗi nhóm khuyết tật một khối) và bảng mức độ
# thực hiện hoạt động (mucDoRadio*): hàng chục ô Có/Không mà câu hỏi nằm ở chữ bên cạnh, không gắn vào ô — hỏi bằng giọng
# không đọc được câu hỏi; mapper điền từ đơn, cán bộ soát trên trang.
NO_ASK = (
    "ghiChu", "khuyetTatRadio", *(f"khuyetTatRadio{i}" for i in range(1, 8)),
    *(f"mucDoRadio{i}" for i in range(1, 11)),
)

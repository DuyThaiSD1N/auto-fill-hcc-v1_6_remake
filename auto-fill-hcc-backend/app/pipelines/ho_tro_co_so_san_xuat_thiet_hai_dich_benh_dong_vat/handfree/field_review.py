"""Bổ sung ô còn trống trên tờ khai hỗ trợ cơ sở sản xuất bị thiệt hại do dịch bệnh động vật (Form.io, cổng NN&MT dichvucongnnmt.mae.gov.vn)."""

PROCEDURE_KEYS = ("ho-tro-co-so-san-xuat-thiet-hai-dich-benh-dong-vat",)

# Cổng đánh dấu ô bắt buộc trên nhãn (label.field-required) / class "required" và báo lỗi dưới ô sau khi bấm Tiếp tục —
# extension đọc thẳng các dấu đó (cả form người nộp lẫn eForm thủ tục) nên không khai thêm tên ô.
REQUIRED = ()

# "Ghi chú" do trợ lý tóm tắt từ biên bản tiêu hủy, không phải thông tin công dân trả lời.
NO_ASK = ("ghiChu",)

"""Bổ sung ô còn trống trên tờ khai đăng ký đất đai lần đầu — cổng iGate Tuyên Quang (Form.io, ba form theo quy trình).

Trợ lý chạy key gốc cho cả ba quy trình ("5 bước", iLis, VBDLIS), nên một cấu hình phủ tên ô của cả ba form.
"""

PROCEDURE_KEYS = ("dang-ky-dat-dai-lan-dau-tuyen-quang",)

# Cổng đánh dấu ô bắt buộc trên component / nhãn và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng các dấu
# đó nên không khai thêm tên ô.
REQUIRED = ()

# Ô tự do hoặc không áp dụng cho hồ sơ cá nhân tự nộp: ghi chú, tên hồ sơ, cơ quan/tổ chức, số đăng ký kinh doanh, khối
# "Thông tin người ủy quyền (nếu có)" của form 5 bước, khối "Thông tin chi tiết" (giấy phép) của form iLis — cấp lần
# đầu chưa có Giấy chứng nhận — và số bộ hồ sơ cổng để sẵn của form VBDLIS.
NO_ASK = (
    "textField", "tenHoSo", "fullname1", "agency1", "Hovaten", "Sogiaytotuythan", "sodienthoai", "diachi",
    "organization", "ghiChu", "licenseCode", "licenseDate", "licensingPlace", "licensingAgency", "effectiveDate",
    "expirationDate", "note", "ProcedureDossierQuantity",
)

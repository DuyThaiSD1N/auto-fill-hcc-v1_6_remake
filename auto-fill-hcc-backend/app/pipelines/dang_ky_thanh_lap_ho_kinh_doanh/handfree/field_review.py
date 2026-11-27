"""Bổ sung ô còn trống trên form SurveyJS đăng ký thành lập hộ kinh doanh (dichvucong.gov.vn/nop-ho-so).

Ô bắt buộc lấy theo chính cổng (isRequired / dấu "*" ở nhãn). Khối người nộp cổng khoá theo tài khoản nên không hỏi;
tỉnh / phường trụ sở cổng khoá theo cơ quan đã chọn; giới tính người được ủy quyền cổng khoá (không nhập được).
"""

PROCEDURE_KEYS = ("dang-ky-thanh-lap-ho-kinh-doanh",)

REQUIRED = ()

NO_ASK = ("tinhThanhTruSo", "phuongXaTruSo", "citizenGioiTinh_NYQ")

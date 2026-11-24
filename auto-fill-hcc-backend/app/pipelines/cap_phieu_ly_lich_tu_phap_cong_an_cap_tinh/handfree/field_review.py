"""Bổ sung ô còn trống trên form SurveyJS cấp Phiếu lý lịch tư pháp (dichvucong.gov.vn/nop-ho-so).

Ô bắt buộc lấy theo chính cổng (isRequired / dấu "*" ở nhãn). Khối người nộp cổng khoá theo tài khoản nên không hỏi;
khối "Nơi ở hiện nay" cổng khoá (disabled) nên cũng không hỏi.
"""

PROCEDURE_KEYS = ("cap-phieu-ly-lich-tu-phap-cong-an-cap-tinh",)

REQUIRED = ()

# Nơi ở hiện nay (Cá nhân: citizenField34–36, Khai hộ: citizenField37–39) — cổng khoá, chưa rõ điều kiện mở.
NO_ASK = ("citizenField34", "citizenField35", "citizenField36", "citizenField37", "citizenField38", "citizenField39")

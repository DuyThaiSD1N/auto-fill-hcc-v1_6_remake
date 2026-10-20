"""Bổ sung ô còn trống trên form SurveyJS cấp Giấy xác nhận tình trạng hôn nhân (dichvucong.gov.vn/nop-ho-so).

Ô bắt buộc lấy theo chính cổng (isRequired / dấu "*" ở nhãn) nên không khai thêm. Ô đọc theo các câu đang hiện
trên trang: chọn tình trạng hôn nhân, mục đích, loại / nơi cư trú xong thì các ô chi tiết tương ứng hiện ra và
được hỏi tiếp ở lượt sau.
"""

PROCEDURE_KEYS = ("xac-nhan-tinh-trang-hon-nhan",)

REQUIRED = ()

# Kính gửi (engine dựng theo xã của tài khoản quầy) và khối "Địa điểm, ngày lập tờ khai" (Tại, Ngày, Tháng,
# Năm) — không phải thông tin của công dân.
NO_ASK = ("citizenField27", "citizenField29", "citizenField78", "citizenField71", "citizenField72")

# Số lượng bản sao: cổng / engine để sẵn 0 trước khi có ai hỏi → còn 0 thì vẫn tô đỏ và hỏi.
ZERO_IS_EMPTY = ("citizenField70",)

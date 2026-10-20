"""Bổ sung ô còn trống trên form SurveyJS cấp bản sao trích lục hộ tịch (dichvucong.gov.vn/nop-ho-so).

Ô bắt buộc lấy theo chính cổng (isRequired / dấu "*" ở nhãn). Khối người nộp cổng khóa theo tài khoản nên không hỏi;
Quan hệ = "Bản thân" thì cổng tự chép khối người được cấp. Chọn nơi cư trú "Trong nước" xong thì ô Quốc gia / Tỉnh /
Xã / Địa chỉ hiện ra và được hỏi tiếp ở lượt sau.
"""

PROCEDURE_KEYS = ("trich-luc-ks",)

REQUIRED = ()

# Kính gửi / Tại (engine dựng theo cơ quan đã chọn hoặc tài khoản quầy) và Ngày / Tháng / Năm lập tờ khai (cổng tự điền).
NO_ASK = ("citizenField27", "citizenField37", "citizenField50", "citizenField52", "citizenField53")

# Ngày sinh người được cấp là Ô CHỮ (nhãn "dd/mm/yyyy"), không phải ô lịch: hỏi như ô ngày, nhận cả tháng-năm hoặc
# chỉ năm, ghi vào cổng dạng chữ.
TEXT_DATES = ("citizenNDK_NgaySinh",)

# Cùng ba ô tra cứu CSDL dân cư như khai tử: điền xong chờ cổng tra rồi mới tìm ô trống kế tiếp, kẻo hỏi đúng
# giới tính / dân tộc cổng sắp tự đổ.
LOOKUP = ("citizenNDK_HoVaTen", "citizenNDK_SoDinhDanh", "citizenNDK_NgaySinh")

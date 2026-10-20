"""Bổ sung ô còn trống trên form SurveyJS đăng ký khai tử (dichvucong.gov.vn/nop-ho-so).

Ô bắt buộc lấy theo chính cổng (isRequired / dấu "*" ở nhãn). Ô đọc theo các câu đang hiện: chọn nơi chết, loại /
nơi cư trú cuối cùng xong thì ô Tỉnh / Xã / Địa chỉ tương ứng hiện ra và được hỏi tiếp ở lượt sau.
"""

PROCEDURE_KEYS = ("khai-tu",)

REQUIRED = ()

# Kính gửi (engine dựng theo xã của tài khoản quầy) và khối "Địa điểm, ngày lập tờ khai" (Tại, Ngày, Tháng, Năm).
NO_ASK = ("citizenField27", "citizenField29", "citizenField28", "citizenField31", "citizenField32")

# Số lượng bản sao: cổng / engine để sẵn 0 → còn 0 thì vẫn tô đỏ và hỏi.
ZERO_IS_EMPTY = ("citizenSoluongbansaonguoiyeucaudenghi",)

# Ngày sinh / ngày chết của người được khai tử là Ô CHỮ cổng kiểm regex dd/mm/yyyy | mm/yyyy | yyyy: hỏi như ô ngày
# (nhận cả tháng-năm hoặc chỉ năm — người mất lâu thường không nhớ đủ ngày), ghi vào cổng dạng chữ.
TEXT_DATES = ("citizenNDK_NgaySinh", "citizenField56")

# Ba ô tra cứu CSDL dân cư: điền xong cổng tự đổ giới tính, dân tộc, quốc tịch, giấy tờ → chờ cổng tra rồi mới
# tìm ô trống kế tiếp.
LOOKUP = ("citizenNDK_HoVaTen", "citizenNDK_SoDinhDanh", "citizenNDK_NgaySinh")

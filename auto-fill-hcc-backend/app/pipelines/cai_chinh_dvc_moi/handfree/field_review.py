"""Bổ sung ô còn trống trên form SurveyJS thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc
(dichvucong.gov.vn/nop-ho-so).

Ô bắt buộc lấy theo chính cổng (isRequired / dấu "*" ở nhãn). Khối người nộp cổng khóa theo tài khoản nên không hỏi;
Quan hệ = "Bản thân" thì cổng tự chép khối người có nội dung thay đổi. Số lượng bản sao nhãn ghi "điền 0 nếu không
cần" nên câu trả lời "không cần" là 0, không phải bỏ qua.
"""

PROCEDURE_KEYS = ("thay-doi-cai-chinh-ho-tich",)

REQUIRED = ()

# Kính gửi / Tại (engine dựng theo cơ quan đã chọn hoặc tài khoản quầy) và Ngày / Tháng / Năm lập tờ khai (cổng tự điền).
NO_ASK = ("citizenField27", "citizenField29", "citizenField28", "citizenField31", "citizenField32")

# Ngày sinh người có nội dung thay đổi là Ô CHỮ dd/mm/yyyy (không phải ô lịch): hỏi như ô ngày, nhận cả tháng-năm
# hoặc chỉ năm, ghi vào cổng dạng chữ.
TEXT_DATES = ("citizenNDK_NgaySinh",)

# Bộ ba họ tên + số định danh + ngày sinh người có nội dung thay đổi: điền xong chờ cổng tra CSDL dân cư rồi mới
# tìm ô trống kế tiếp, kẻo hỏi đúng giới tính / dân tộc cổng sắp tự đổ.
LOOKUP = ("citizenNDKHoTen", "citizenNDKSodinhdanh", "citizenNDK_NgaySinh")

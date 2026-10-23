"""Bổ sung ô còn trống trên tờ khai liên thông khai sinh (form Angular của lienthong.dichvucong.gov.vn)."""

PROCEDURE_KEYS = ("khai-sinh-dang-ky",)

# Cổng tự đánh dấu ô bắt buộc ngay từ đầu (dấu * của mat-form-field, class "required" của ng-select) và tô vàng ô
# còn trống sau khi bấm "Chuyển bước tiếp theo" — extension đọc thẳng các dấu đó nên không khai thêm tên ô.
REQUIRED = ()

# Chọn nguồn dữ liệu chứng sinh (nhập tay / lấy từ CSDL Bảo hiểm) là thao tác của cán bộ, không phải thông tin hồ sơ.
NO_ASK = ("IsChungSinhBhxh",)

# Ô "Đề nghị cấp bản sao" (Có/Không) và ô số lượng hiện ra sau khi chọn Có: nói "có, ba bản" là điền cả hai.
COPY_QUANTITY = ("CapBanSao", "BanSaoSoLuong")

"""Bổ sung ô còn trống trên tờ khai liên thông khai tử (form Angular của lienthong.dichvucong.gov.vn)."""

PROCEDURE_KEYS = ("khai-tu-lien-thong",)

# Cổng tự đánh dấu ô bắt buộc ngay từ đầu (dấu * của mat-form-field) — extension đọc thẳng nên không khai thêm tên ô.
# Khối mai táng phí đổi theo đối tượng chọn ở bước 1 (BHXH: BhxhNhantrocap*; bảo trợ xã hội: Canhan*, Nnmtp*…):
# extension đọc ô đang hiện nên không liệt kê theo đối tượng.
REQUIRED = ()

# Chọn nguồn dữ liệu báo tử (nhập tay / lấy từ CSDL Bảo hiểm) là thao tác của cán bộ, không phải thông tin hồ sơ.
NO_ASK = ("IsChungTuBhxh",)

# Ô "Đề nghị cấp bản sao" (Có/Không) và ô số lượng hiện ra sau khi chọn Có: nói "có, ba bản" là điền cả hai.
COPY_QUANTITY = ("CapBanSao", "BanSaoSoluong")

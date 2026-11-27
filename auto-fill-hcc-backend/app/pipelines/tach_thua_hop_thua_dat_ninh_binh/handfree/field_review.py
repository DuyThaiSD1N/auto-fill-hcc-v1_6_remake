"""Bổ sung ô còn trống trên tờ khai tách thửa hoặc hợp thửa đất (1.012784) — cổng iGate Ninh Bình, quy trình "Phi địa
giới" (Form.io ba khối người nộp / địa chỉ thửa đất / người nhận kết quả)."""

PROCEDURE_KEYS = ("tach-thua-hop-thua-dat-ninh-binh",)

# Cổng đánh dấu ô bắt buộc trên component (class "required") và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó nên không khai thêm tên ô.
REQUIRED = ()

# Khối tổ chức (organization/taxCode/province1/village1/address1) chỉ điền khi người sử dụng đất là tổ chức; "Tư cách người
# nộp hồ sơ" trợ lý tự ghi theo ủy quyền; Tỉnh/TP thửa đất (province2) cổng khoá; "Hình thức nộp hồ sơ" cổng chọn sẵn.
NO_ASK = ("organization", "taxCode", "province1", "village1", "address1", "TuCachNguoiNopHoSo", "province2",
          "hinhThucNopHs")

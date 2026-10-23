"""Bổ sung ô còn trống trên đơn yêu cầu trợ giúp pháp lý sau khi điền (chat/field_review)."""

PROCEDURE_KEYS = ("yeu-cau-tro-giup-phap-ly",)

# Nhân thân người được trợ giúp (mục I) + nội dung yêu cầu (mục III) — phần cơ quan trợ giúp cần để thụ lý. Ô cổng
# chấm đỏ khi bấm Xem trước vẫn được extension gộp thêm vào danh sách bắt buộc.
REQUIRED = (
    "NguoiDuocTGPL_HoVaTen", "NguoiDuocTGPL_NgaySinh", "NguoiDuocTGPL_GioiTinh", "NguoiDuocTGPL_SoDinhDanh",
    "NguoiDuocTGPL_DiaChi", "NguoiDuocTGPL_TinhThanh", "NguoiDuocTGPL_PhuongXa", "NguoiDuocTGPL_DienDoiTuong",
    "VuViec_TomTatYeuCau", "VuViec_HinhThucTGPL",
)

# Phần đầu/cuối đơn (tổ chức nhận đơn, nơi và ngày làm đơn, người ký) — nằm sau tiêu đề mục III nhưng không thuộc
# nội dung vụ việc → hỏi không kèm tên phần.
NO_SECTION = ("KinhGui", "ToChucTGPL_ToChucTiepNhan", "LamTai", "Ngay", "Thang", "Nam", "KyTen")

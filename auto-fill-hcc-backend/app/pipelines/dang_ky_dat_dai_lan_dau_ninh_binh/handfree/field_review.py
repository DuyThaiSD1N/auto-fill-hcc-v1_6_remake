"""Bổ sung ô còn trống trên tờ khai đăng ký đất đai, cấp GCN lần đầu (1.013978) — cổng iGate Ninh Bình (Form.io ba khối
người nộp / chủ hồ sơ / khối nhận kết quả, dùng chung cho cả 6 thủ tục đất đai Ninh Bình trên trợ lý)."""

PROCEDURE_KEYS = ("dang-ky-dat-dai-lan-dau-ninh-binh",)

# Cổng đánh dấu ô bắt buộc trên component (class "required") và báo lỗi dưới ô sau khi bấm Tiếp tục — extension đọc thẳng
# các dấu đó nên không khai thêm tên ô.
REQUIRED = ()

# "Nội dung yêu cầu giải quyết" là nguyên văn Đơn do trợ lý chép; "Ghi chú" là câu trợ lý ghi cho cán bộ; "Cơ quan/Tổ
# chức" chỉ điền khi chủ hồ sơ là tổ chức; "Loại liên thông" / "Hình thức nộp hồ sơ" cổng chọn sẵn. KHÔNG thêm district:
# trên form Ninh Bình đó là ô Phường/Xã của người nộp (mapper ghi xã vào data[district]).
NO_ASK = ("noidungyeucaugiaiquyet", "note", "organization", "loaiVanBan", "hinhThucNopHs")

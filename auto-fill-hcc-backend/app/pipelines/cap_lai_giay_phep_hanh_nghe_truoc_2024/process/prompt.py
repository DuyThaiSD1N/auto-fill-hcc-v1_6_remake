"""Prompt rules đặc thù cho "Cấp lại giấy phép hành nghề đối với trường hợp được cấp trước ngày 01/01/2024..."
(Form.io — cổng Bộ Y tế)."""

EXTRA_RULES = """Thủ tục: Cấp lại giấy phép hành nghề khám bệnh, chữa bệnh cho người đã được cấp chứng chỉ / giấy
phép hành nghề TRƯỚC ngày 01/01/2024 (hồ sơ nộp từ 01/01/2024 đến thời điểm kiểm tra đánh giá năng lực
hành nghề). Đầu vào thường gồm: CCCD của người hành nghề, Đơn đề nghị (Mẫu 08 Phụ lục I NĐ 96/2023),
chứng chỉ / giấy phép hành nghề ĐÃ ĐƯỢC CẤP (bản cũ), ảnh chân dung; CÓ THỂ có thêm CCCD của người nộp thay.

HAI vai — tách RIÊNG, KHÔNG lẫn:
- NGƯỜI HÀNH NGHỀ (NguoiHanhNghe_*) = CHỦ HỒ SƠ = người đề nghị cấp lại. Đây là người CHÍNH: người đứng
  tên trên Đơn Mẫu 08 và trên chứng chỉ / giấy phép hành nghề cũ. Trích nhân thân người này vào
  NguoiHanhNghe_*.
- NGƯỜI NỘP (NguoiNop_*) = người đứng nộp hồ sơ trên cổng (tài khoản đăng nhập). ĐA SỐ tự nộp → CHÍNH
  LÀ người hành nghề → BỎ TRỐNG NguoiNop_*. Chỉ khi có người khác NỘP THAY và hồ sơ có CCCD RIÊNG của
  người nộp thì mới trích NguoiNop_* TỪ CCCD đó. Xem khối <nguoi_nop_context> ở cuối (nếu có) để biết
  tài khoản nộp là ai và CCCD nào là của người nộp.

⚠ KHÔNG lấy CCCD của người nộp thay làm NguoiHanhNghe_* — giấy phép cấp lại cho NGƯỜI HÀNH NGHỀ (người
trên Đơn Mẫu 08 / chứng chỉ hành nghề cũ), KHÔNG phải người nộp hộ. Chỉ có 1 người trong hồ sơ (CCCD trùng
số định danh với Đơn / chứng chỉ hành nghề) → tự nộp, BỎ TRỐNG NguoiNop_*.

NGUỒN DỮ LIỆU (NguoiHanhNghe_*):
- Họ tên / ngày sinh / số định danh: CCCD, Đơn Mẫu 08, chứng chỉ / giấy phép hành nghề cũ (dòng "Thẻ Căn
  cước công dân số"). Giới tính chỉ có trên CCCD.
- SỐ ĐỊNH DANH: có cả số 12 chữ số (CCCD/căn cước) lẫn số 9 chữ số (CMND) → LUÔN chọn số 12 chữ số.
  Ngày cấp và nơi cấp phải đi CÙNG số định danh đã chọn (cùng một giấy, cùng một dòng), không ghép ngày cấp
  của số này với nơi cấp của số khác.
- ThuongTru: chứng chỉ hành nghề cũ và CCCD hay ghi địa giới CŨ (trước sáp nhập); Đơn Mẫu 08 làm gần đây
  thường ghi địa giới MỚI → ưu tiên Đơn. Tách object {quocGia,tinh,xa,diaChi}; diaChi CHỈ chi tiết (số
  nhà/đường/tổ/thôn), KHÔNG kèm phường/xã/huyện/tỉnh.
- DienThoai: lấy số DI ĐỘNG trên Đơn; KHÔNG lấy số bàn. Email: chỉ Đơn có.
- Chữ ký, tên người ký/đóng dấu trên chứng chỉ hành nghề (Giám đốc Sở Y tế…) và trên CCCD (Cục trưởng…)
  KHÔNG phải người hành nghề cũng không phải người nộp.

LƯU Ý: nội dung chuyên môn (văn bằng, chức danh, phạm vi hoạt động chuyên môn, số chứng chỉ cũ, lý do cấp
lại…) KHÔNG có trường nhập online → KHÔNG cần trích, chỉ nộp qua file đính kèm.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""

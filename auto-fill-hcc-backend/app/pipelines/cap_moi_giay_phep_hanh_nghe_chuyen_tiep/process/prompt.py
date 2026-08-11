"""Prompt rules đặc thù cho "Cấp mới giấy phép hành nghề trong giai đoạn chuyển tiếp..." (Form.io —
cổng Bộ Y tế)."""

EXTRA_RULES = """Thủ tục: Cấp mới giấy phép hành nghề khám bệnh, chữa bệnh trong giai đoạn chuyển tiếp
(hồ sơ nộp từ 01/01/2024 đến thời điểm kiểm tra đánh giá năng lực hành nghề) cho các chức danh bác sỹ,
y sỹ, điều dưỡng, hộ sinh, kỹ thuật y, dinh dưỡng lâm sàng, cấp cứu viên ngoại viện, tâm lý lâm sàng.
Đầu vào gồm: CCCD của người hành nghề, Đơn đề nghị cấp GPHN (Mẫu 08 PL I NĐ 96/2023), Sơ yếu lý lịch
tự thuật của người hành nghề (Mẫu 09 PL I), và CÓ THỂ có thêm CCCD của người nộp thay.

HAI vai — tách RIÊNG, KHÔNG lẫn:
- NGƯỜI HÀNH NGHỀ (NguoiHanhNghe_*) = CHỦ HỒ SƠ = người đề nghị cấp giấy phép. Đây là người CHÍNH. Đơn
  Mẫu 08, Sơ yếu lý lịch Mẫu 09 LUÔN là của người này (kê khai chuyên môn, chức danh đề nghị cấp, quá
  trình đào tạo/công tác). Trích toàn bộ nhân thân của người này vào các field NguoiHanhNghe_*.
- NGƯỜI NỘP (NguoiNop_*) = người đứng nộp hồ sơ trên cổng (tài khoản đăng nhập). ĐA SỐ tự nộp → CHÍNH
  LÀ người hành nghề → BỎ TRỐNG NguoiNop_*. Chỉ khi có người khác NỘP THAY và hồ sơ có CCCD RIÊNG của
  người nộp thì mới trích NguoiNop_* TỪ CCCD đó. Xem khối <nguoi_nop_context> ở cuối (nếu có) để biết
  tài khoản nộp là ai và CCCD nào là của người nộp.

⚠ KHÔNG lấy CCCD của người nộp thay làm NguoiHanhNghe_* — giấy phép cấp cho NGƯỜI HÀNH NGHỀ (người trong
Đơn Mẫu 08 / Sơ yếu lý lịch Mẫu 09), KHÔNG phải người nộp hộ. Nếu chỉ có 1 người trong hồ sơ (CCCD trùng
số định danh với Đơn/Mẫu 09) → tự nộp, BỎ TRỐNG NguoiNop_*.

NGUỒN DỮ LIỆU (NguoiHanhNghe_*):
- Họ tên / ngày sinh / giới tính / số định danh / ngày cấp: ưu tiên CCCD người hành nghề; bổ sung từ Đơn
  Mẫu 08 và Sơ yếu lý lịch Mẫu 09.
- SỐ ĐỊNH DANH: có cả số 12 chữ số (CCCD/căn cước) lẫn số 9 chữ số (CMND) → LUÔN chọn số 12 chữ số.
- Nơi cấp: CCCD gắn chip không in nhãn "Nơi cấp" riêng → lấy ở Mẫu 08/09. Chuẩn hóa tên cơ quan cấp
  (Cục Cảnh sát QLHC về TTXH / Bộ Công an).
- ThuongTru: tách object {quocGia,tinh,xa,diaChi}; ưu tiên tên địa giới MỚI (sau sáp nhập) nếu giấy tờ
  ghi; diaChi CHỈ chi tiết (số nhà/đường/tổ/thôn), KHÔNG kèm phường/xã/huyện/tỉnh.
- DienThoai: lấy số DI ĐỘNG; KHÔNG lấy số nhà riêng/bàn. Email: chỉ Mẫu 08 có.

LƯU Ý: các nội dung nghiệp vụ của Mẫu 08 (văn bằng chuyên môn, chức danh đề nghị cấp, phạm vi hành nghề,
cơ sở KCB...) và nội dung chuyên môn của Mẫu 09 (nguyên quán, dân tộc, trình độ, quá trình đào tạo/công
tác...) KHÔNG có trường nhập online → KHÔNG cần trích, chỉ nộp qua file đính kèm.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""

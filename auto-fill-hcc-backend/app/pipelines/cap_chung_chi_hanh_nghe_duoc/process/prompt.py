"""Prompt rules đặc thù cho "Cấp Chứng chỉ hành nghề dược ... theo hình thức xét hồ sơ" (Form.io —
cổng Bộ Y tế)."""

EXTRA_RULES = """Thủ tục: Cấp Chứng chỉ hành nghề dược (CCHN dược) theo hình thức xét hồ sơ, gồm cả trường
hợp cấp lại cho người bị THU HỒI CCHN dược theo Điều 28 Luật Dược. Đầu vào gồm: CCCD của người đề nghị,
Đơn đề nghị cấp CCHN dược (Mẫu số 02), Phiếu lý lịch tư pháp, Văn bằng chuyên môn (bằng tốt nghiệp), Giấy
chứng nhận đủ sức khỏe hành nghề dược, Giấy xác nhận thời gian thực hành (Mẫu 03), và CÓ THỂ có thêm CCCD
của người nộp thay.

HAI vai — tách RIÊNG, KHÔNG lẫn:
- NGƯỜI ĐỀ NGHỊ (NguoiDeNghi_*) = CHỦ HỒ SƠ = dược sĩ đề nghị cấp CCHN dược. Đây là người CHÍNH. Đơn Mẫu
  02, Phiếu lý lịch tư pháp, văn bằng, giấy khám sức khỏe, giấy xác nhận thực hành LUÔN là của người này.
  Trích toàn bộ nhân thân của người này vào các field NguoiDeNghi_*.
- NGƯỜI NỘP (NguoiNop_*) = người đứng nộp hồ sơ trên cổng (tài khoản đăng nhập). ĐA SỐ tự nộp → CHÍNH LÀ
  người đề nghị → BỎ TRỐNG NguoiNop_*. Chỉ khi có người khác NỘP THAY và hồ sơ có CCCD RIÊNG của người
  nộp thì mới trích NguoiNop_* TỪ CCCD đó. Xem khối <nguoi_nop_context> ở cuối (nếu có).

⚠ KHÔNG lấy CCCD của người nộp thay làm NguoiDeNghi_* — chứng chỉ cấp cho NGƯỜI ĐỀ NGHỊ (người trong Đơn
Mẫu 02 / Phiếu lý lịch tư pháp), KHÔNG phải người nộp hộ. Chỉ 1 người trong hồ sơ (CCCD trùng số định danh
với Đơn Mẫu 02) → tự nộp, BỎ TRỐNG NguoiNop_*.

NGUỒN DỮ LIỆU (NguoiDeNghi_*):
- Họ tên: Đơn Mẫu 02 mục 1 / CCCD. Ngày sinh: mục 2 / CCCD. Số định danh + ngày/nơi cấp: mục 5 / CCCD.
  Điện thoại + email: mục 6. Nơi thường trú: mục 3 (Nơi đăng ký hộ khẩu thường trú) / CCCD.
- Giới tính: Đơn Mẫu 02 KHÔNG có → lấy từ CCCD / Phiếu lý lịch tư pháp.
- SỐ ĐỊNH DANH: có cả số 12 chữ số (CCCD/căn cước) lẫn số 9 chữ số (CMND) → LUÔN chọn số 12 chữ số.
- Nơi cấp: CCCD gắn chip không in nhãn "Nơi cấp" riêng → lấy ở Đơn Mẫu 02 mục 5 / Phiếu LLTP. Chuẩn hóa
  tên cơ quan cấp (Cục Cảnh sát QLHC về TTXH / Bộ Công an).
- ThuongTru: ưu tiên tên địa giới MỚI (sau sáp nhập) ghi ở Đơn Mẫu 02 (CCCD cũ có thể ghi tên tỉnh/xã CŨ
  — vd CCCD ghi "tỉnh Quảng Nam" nhưng Đơn 2026 ghi "TP Đà Nẵng" thì lấy theo Đơn). tách object
  {quocGia,tinh,xa,diaChi}; diaChi CHỈ chi tiết (số nhà/đường/thôn/tổ), KHÔNG kèm phường/xã/huyện/tỉnh.
- DienThoai: số DI ĐỘNG; KHÔNG lấy số bàn. Email: chỉ khi Đơn có.

LƯU Ý: nội dung nghiệp vụ (văn bằng chuyên môn, phạm vi hoạt động chuyên môn, thời gian thực hành, kết
luận sức khỏe, án tích LLTP...) KHÔNG có trường nhập online → KHÔNG cần trích, chỉ nộp qua file đính kèm.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""

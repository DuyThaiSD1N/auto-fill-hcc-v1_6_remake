"""Prompt rules đặc thù cho "Cung cấp thông tin quy hoạch đô thị và nông thôn" (Form.io)."""

EXTRA_RULES = """Thủ tục: Cung cấp thông tin quy hoạch đô thị và nông thôn. Người dân/tổ chức nộp
Đơn (Văn bản) đề nghị cung cấp thông tin quy hoạch cho một thửa đất/lô đất cụ thể.
Đầu vào thường gồm: CCCD người nộp, Đơn đề nghị cung cấp thông tin quy hoạch, và Giấy chứng nhận QSDĐ
(sổ đỏ) của thửa đất cần tra cứu.

FORM CHỈ THU THÔNG TIN NGƯỜI NỘP HỒ SƠ:
- Chỉ trích thông tin về NGƯỜI NỘP (NguoiNop_*). KHÔNG trích thông tin thửa đất (thửa số, tờ bản đồ,
  diện tích, mục đích, số GCN...) — form không có ô cho các thông tin này (nộp qua bản scan).
- KHÔNG nhầm người sử dụng đất trên Giấy chứng nhận với người nộp, TRỪ KHI họ là cùng một người
  (tự nộp). Xem <nguoi_nop_context> nếu có.

NGUỒN DỮ LIỆU NGƯỜI NỘP:
- Họ tên/ngày sinh/giới tính/số định danh: ưu tiên CCCD; Đơn đề nghị bổ sung nếu CCCD thiếu.
- BẮT BUỘC cố đọc NguoiNop_NgayCapCccd/NguoiNop_NoiCapCccd từ mặt sau CCCD. Nếu OCR thấy "CỤC TRƯỞNG
  CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → NguoiNop_NoiCapCccd = "Cục Cảnh sát quản lý hành
  chính về trật tự xã hội". Thẻ CĂN CƯỚC mới (tiêu đề "CĂN CƯỚC"/"IDENTITY CARD", ghi "BỘ CÔNG AN") →
  "Bộ Công an".
- NguoiNop_DienThoai/NguoiNop_Email: lấy từ Đơn đề nghị (CCCD/GCN không có).

ĐỊA CHỈ (NguoiNop_ThuongTru):
- object {quocGia,tinh,xa,diaChi}: tinh = "Tỉnh/Thành phố …", xa = phường/xã, diaChi = tổ dân phố/thôn/
  số nhà/đường. Địa giới đã sáp nhập → ƯU TIÊN tên phường/xã MỚI (hiện hành). Nếu CCCD ghi tên CŨ
  (vd 'Xã Ngũ Thái') mà Đơn đề nghị ghi tên MỚI (vd 'Phường Song Liễu') → lấy theo ĐƠN (mới nhất).

NGƯỜI NỘP THAY / ĐẠI DIỆN:
- Nếu có khối <nguoi_nop_context result="co_giay_to"> ở cuối prompt: người nộp là tài khoản đăng nhập
  (tên+CCCD), giấy tờ tùy thân ở tài liệu đã chỉ. Trích NguoiNop_* CỦA CHÍNH NGƯỜI NÀY từ đúng tài liệu
  đó, KHÔNG lấy thông tin người sử dụng đất trên GCN/Đơn nếu người đó khác người nộp.
- Nếu <nguoi_nop_context result="khong_co_giay_to">: hồ sơ KHÔNG có CCCD của người nộp → để TRỐNG toàn
  bộ NguoiNop_* (form đã tự điền từ VNeID, không đè).
- Không có <nguoi_nop_context> (tự nộp thông thường) → trích NguoiNop_* từ CCCD/Đơn của người đứng đơn.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""

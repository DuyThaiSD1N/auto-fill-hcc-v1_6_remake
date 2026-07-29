"""Prompt rules đặc thù cho "Cấp GCN đủ điều kiện điểm trò chơi điện tử công cộng"."""

EXTRA_RULES = """Thủ tục: Cấp Giấy chứng nhận đủ điều kiện hoạt động điểm cung cấp dịch vụ trò chơi
điện tử công cộng (chủ điểm là CÁ NHÂN). Đầu vào gồm: CCCD chủ điểm, Đơn đề nghị (Mẫu số 51a),
và Giấy phép kinh doanh (Giấy chứng nhận đăng ký hộ kinh doanh).

MỘT NGƯỜI DUY NHẤT: chủ điểm là cá nhân → người nộp = người được giải quyết = chủ hộ kinh doanh
(người đại diện pháp luật) là CÙNG một người (Nguoi_*). KHÔNG tách thành nhiều người.

NGUỒN DỮ LIỆU NGƯỜI (Nguoi_*):
- Họ tên/ngày sinh/số định danh/ngày cấp: ưu tiên CCCD; Đơn 51a bổ sung nếu CCCD thiếu.
- Nguoi_NoiCapCccd: ƯU TIÊN "Nơi cấp" ghi trên Đơn 51a (vd "Bắc Ninh"); nếu Đơn không ghi thì chuẩn hóa
  từ mặt sau CCCD ("CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản
  lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới → "Bộ Công an").
- Nguoi_DienThoai: từ Đơn 51a hoặc Giấy phép kinh doanh (CCCD không có).
- Nguoi_ThuongTru: object {tinh,xa,diaChi}. ƯU TIÊN tên phường/xã MỚI (sau sáp nhập) trong Đơn 51a /
  Giấy phép kinh doanh; CCCD 2021 ghi tên CŨ (vd 'Ngũ Thái, Thuận Thành') thì BỎ, lấy tên mới.

NGUỒN DỮ LIỆU HỘ KINH DOANH (HoKD_*) — CHỈ từ Giấy phép kinh doanh:
- HoKD_MaSo = mã số hộ kinh doanh (= mã số thuế).
- HoKD_CoQuanCap = cơ quan cấp GCN đăng ký hộ kinh doanh.
- HoKD_NgayDangKyLanDau = ngày 'Đăng ký lần đầu'.
- HoKD_TenTiengViet = tên hộ kinh doanh viết bằng tiếng Việt.
- HoKD_TruSo = địa chỉ trụ sở/địa điểm kinh doanh, object {tinh,xa,diaChi} — CÓ THỂ KHÁC nơi thường trú.
- Hộ kinh doanh KHÔNG có tên nước ngoài / tên viết tắt / fax / website → không trả các thông tin đó.

KHÔNG trả field UI (mat-label, section, id). KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field.
Số máy tính / tên điểm ("Village game") / số đăng ký kinh doanh điểm trong Đơn 51a KHÔNG có ô ở màn này
→ bỏ qua."""

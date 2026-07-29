"""Prompt rules đặc thù cho "Xét tuyển Viên chức (NĐ 85/2023) (Lai Châu)" (eForm Lai Châu)."""

EXTRA_RULES = """Thủ tục: Xét tuyển Viên chức theo Nghị định số 85/2023/NĐ-CP (Lai Châu). Đầu vào gồm:
CCCD của người dự tuyển và Phiếu đăng ký dự tuyển theo Mẫu số 01.

FORM CHỈ THU THÔNG TIN NGƯỜI DỰ TUYỂN (người nộp hồ sơ):
- Chỉ trích thông tin về NGƯỜI DỰ TUYỂN (Nguoi_*). KHÔNG trích thông tin chi tiết dự tuyển (đào tạo,
  gia đình, quá trình công tác, nguyện vọng vị trí, đơn vị) — các nội dung này nằm trong Phiếu Mẫu 01
  đính kèm, không có ô trên e-form.

NGUỒN DỮ LIỆU:
- Họ tên/ngày sinh/giới tính/số định danh/ngày cấp: ưu tiên CCCD; Phiếu Mẫu 01 bổ sung nếu CCCD thiếu.
- BẮT BUỘC cố đọc Nguoi_NgayCap/Nguoi_NoiCap từ mặt sau CCCD. "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH
  CHÍNH VỀ TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới → "Bộ Công an".
- Nguoi_DanToc/Nguoi_DiDong/Nguoi_Email: lấy từ Phiếu Mẫu 01.

ĐỊA CHỈ (Nguoi_ThuongTru):
- Lấy theo NƠI THƯỜNG TRÚ / hộ khẩu (CCCD hoặc Phiếu), KHÔNG lấy quê quán (quê quán có thể khác tỉnh).
- object {tinh,xa,diaChi}: tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/đường/tổ/thôn/xóm.
  Địa giới đã sáp nhập → ưu tiên tên phường/xã MỚI (hiện hành) nếu giấy tờ có ghi.

KHÔNG trả field UI dạng CongDan_.... KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""

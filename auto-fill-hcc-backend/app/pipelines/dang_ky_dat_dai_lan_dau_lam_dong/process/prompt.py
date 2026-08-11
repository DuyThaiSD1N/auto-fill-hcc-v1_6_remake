"""Prompt rules đặc thù cho [Lâm Đồng] đăng ký đất đai cấp GCN lần đầu (Form.io)."""

EXTRA_RULES = """Thủ tục: Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận LẦN ĐẦU cho
hộ gia đình, cá nhân, cộng đồng dân cư, người gốc Việt Nam định cư ở nước ngoài.
Đầu vào thường gồm: CCCD chủ hộ, Đơn đăng ký đất đai (Mẫu 15/ĐK), Sơ đồ ranh giới sử dụng đất, Trích
lục bản đồ địa chính, các giấy tờ nguồn gốc đất, và có thể có Giấy ủy quyền.

NGUỒN DỮ LIỆU:
- Nguoi_* là CHỦ HỒ SƠ = người sử dụng đất đứng đơn đăng ký. Lấy từ CCCD / mục người sử dụng đất của Đơn
  đăng ký đất đai.
- BẮT BUỘC cố đọc Nguoi_NgayCapCccd/Nguoi_NoiCapCccd từ mặt sau CCCD. Nếu OCR thấy "CỤC TRƯỞNG CỤC CẢNH SÁT
  QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → Nguoi_NoiCapCccd = "Cục Cảnh sát quản lý hành chính về trật tự xã
  hội". Thẻ CĂN CƯỚC mới (tiêu đề "CĂN CƯỚC"/"IDENTITY CARD", ghi "BỘ CÔNG AN") → "Bộ Công an".
- KHỚP NGƯỜI THEO SỐ ĐỊNH DANH, KHÔNG theo tên. Nơi cấp/ngày cấp có thể nằm trong GIẤY TỜ KHÁC (đơn xác
  nhận, ủy quyền, thông báo thuế...) ở dạng "CCCD số <X> ... do <nơi> cấp". Nếu <X> TRÙNG số định danh của
  một vai (chủ hồ sơ/đại diện) thì thông tin đó LÀ của vai đó — DÙ tên viết hơi khác do OCR/viết tắt (vd
  "Huỳnh Phương" và "Huỳnh Thanh Phương" cùng số 068074004719 là MỘT người). Chuẩn hóa viết tắt: "cục CS
  ... về TTXH" / "cục CSQLHC về TTXH" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội".
- CẤM BỊA nơi cấp: nếu KHÔNG tài liệu nào ghi nơi cấp cho số định danh đó → ĐỂ TRỐNG *_NoiCapCccd. TUYỆT
  ĐỐI KHÔNG suy đoán, KHÔNG lấy ví dụ "Bộ Công an"/"Cục Cảnh sát..." trong quy tắc này làm giá trị mặc định.

NGƯỜI NỘP THAY / ĐẠI DIỆN (DaiDien_*):
- DaiDien_* = NGƯỜI NỘP HỒ SƠ khi người này KHÁC chủ hồ sơ (người đứng đơn đăng ký). Nhận biết qua:
  (a) khối <nguoi_nop_context> ở cuối prompt (nếu có) — báo rõ mỏ neo người nộp (tên+CCCD tài khoản) và
      CCCD tương ứng trong hồ sơ; hoặc (b) Giấy ủy quyền / Đơn ghi rõ người đại diện.
- Khi <nguoi_nop_context result="co_giay_to"> và người nộp KHÁC người đứng đơn: BẮT BUỘC trích DaiDien_*
  (họ tên, ngày sinh, giới tính, số định danh, ngày/nơi cấp, nơi thường trú) từ đúng CCCD của người nộp;
  Nguoi_* vẫn là người đứng đơn đăng ký.
- Ngày cấp + nơi cấp CCCD người đại diện: từ mặt sau CCCD của họ, hoặc dòng "Căn cước công dân số … cấp
  ngày <ngày> tại <nơi>" trong Giấy ủy quyền.
- TỰ NỘP (người nộp TRÙNG người đứng đơn, hoặc không có mỏ neo/không có giấy tờ người nộp) → để TRỐNG
  toàn bộ DaiDien_*.

ĐỊA CHỈ:
- Nguoi_ThuongTru (nơi ở chủ hộ, từ CCCD/Đơn) và ThuaDat_DiaChi (vị trí THỬA ĐẤT đăng ký, từ Đơn đăng ký
  đất đai / Sơ đồ ranh giới / Trích lục bản đồ) là HAI địa chỉ KHÁC nhau — đừng gán trùng.
- Tách object {tinh,xa,diaChi}: tinh = "Tỉnh …", xa = phường/xã, diaChi = số nhà/đường/thôn/xóm. Địa giới
  đã sáp nhập → ưu tiên tên phường/xã MỚI (hiện hành) nếu giấy tờ có ghi.
- ThuaDat_So / ThuaDat_ToBanDo: thửa đất số / tờ bản đồ số, từ Đơn/sơ đồ/trích lục.

Thủ tục ĐĂNG KÝ LẦN ĐẦU nên CHƯA có Giấy chứng nhận — KHÔNG cần và KHÔNG được bịa số/ngày cấp GCN.
Không trả field UI dạng data[...]. Không bịa thông tin còn thiếu."""

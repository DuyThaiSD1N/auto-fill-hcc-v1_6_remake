"""Prompt rules đặc thù cho "Cấp lại, điều chỉnh GCN đủ điều kiện kinh doanh dược (Sở Y tế)" (Form.io —
cổng Bộ Y tế)."""

EXTRA_RULES = """Thủ tục: Cấp lại, điều chỉnh Giấy chứng nhận đủ điều kiện kinh doanh dược (GCN đủ ĐKKD dược) do
Sở Y tế cấp cho nhà thuốc / quầy thuốc / cơ sở bán buôn. Đầu vào (có thể là MỘT PDF gộp nhiều giấy tờ):
- Đơn đề nghị điều chỉnh GCN đủ ĐKKD dược (Mẫu số 12) HOẶC Đơn đề nghị cấp lại (Mẫu số 11): Tên cơ sở, Số
  điện thoại liên hệ, Địa chỉ kinh doanh, Người phụ trách chuyên môn, Số CCHN dược, Nội dung xin điều chỉnh,
  người ký "NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT".
- Giấy chứng nhận đăng ký hộ kinh doanh (mục 6 "Thông tin về chủ hộ kinh doanh": họ tên, giới tính, sinh
  ngày, số định danh cá nhân, nơi thường trú, nơi ở hiện tại) hoặc Giấy chứng nhận đăng ký doanh nghiệp.
- Giấy chứng nhận đạt GPP, GCN đủ ĐKKD dược cũ, Chứng chỉ hành nghề dược (nếu có).
- CCCD của chủ cơ sở và/hoặc CCCD của người nộp thay.

HAI vai — tách RIÊNG, KHÔNG lẫn:
- CHỦ HỒ SƠ (ChuHoSo_*) = chủ hộ kinh doanh / người đại diện theo pháp luật của cơ sở (thường cũng là người
  phụ trách chuyên môn về dược). Đây là người CHÍNH.
- NGƯỜI NỘP (NguoiNop_*) = tài khoản đăng nhập cổng. Chỉ trích khi khối <nguoi_nop_context> báo hồ sơ CÓ
  CCCD của người đó; nếu người nộp chính là chủ hồ sơ hoặc không có CCCD → BỎ TRỐNG NguoiNop_*.

NGUỒN ChuHoSo_* (ưu tiên theo thứ tự): CCCD của chủ cơ sở → Đơn đề nghị → GCN đăng ký hộ kinh doanh mục 6
→ GCN GPP.
- HoTen: BỎ tiền tố trình độ ("DSĐH.", "DS.", "Dược sĩ đại học"...). Vd "DSĐH. Trần Thị Bích" → "TRẦN THỊ
  BÍCH" / "Trần Thị Bích".
- SoDinhDanh: CCCD, hoặc GCN ĐKHKD "Số định danh cá nhân" của chủ hộ. KHÔNG lấy "Mã số hộ kinh doanh",
  "Mã số doanh nghiệp", số CCHN dược hay số GPP.
- NgayCap/NoiCap: CHỈ lấy trên thẻ CCCD. Đơn có dòng "Số CCHN Dược ... Nơi cấp: Sở Y tế ... Năm cấp ..." —
  đó là của CHỨNG CHỈ HÀNH NGHỀ, TUYỆT ĐỐI KHÔNG dùng cho NgayCap/NoiCap. Hồ sơ không có CCCD → bỏ trống.
- ThuongTru: nơi thường trú CÁ NHÂN của chủ hồ sơ (CCCD / GCN ĐKHKD mục 6 "Nơi thường trú"). KHÔNG lấy "Trụ
  sở", "Địa chỉ kinh doanh", "Địa điểm kinh doanh" của cơ sở. CCCD cũ ghi địa giới CŨ (quận/phường trước sáp
  nhập) thì ưu tiên địa giới MỚI ghi ở GCN ĐKHKD. tách {quocGia,tinh,xa,diaChi}; diaChi CHỈ số nhà/đường/tổ.
- DienThoai: Đơn "Số điện thoại liên hệ" hoặc GCN ĐKHKD "Điện thoại"; bỏ dấu chấm/khoảng trắng.

NoiDungDeNghi: Đơn Mẫu 12 → chép NGUYÊN VĂN phần "Nội dung xin điều chỉnh" (giữ dấu "+" đầu dòng nếu có, nối
các dòng bằng "; "). Đơn Mẫu 11 → chép "Lý do đề nghị cấp lại".

LƯU Ý: Tên cơ sở, loại hình, phạm vi kinh doanh, số CCHN, vốn, ngành nghề... KHÔNG có ô nhập online → KHÔNG
trích.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""

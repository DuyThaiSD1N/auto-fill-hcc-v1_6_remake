"""Prompt rules đặc thù cho "Cấp GCN đủ điều kiện kinh doanh dược (Sở Y tế)" (Form.io — cổng Bộ Y tế)."""

EXTRA_RULES = """Thủ tục: Cấp Giấy chứng nhận đủ điều kiện kinh doanh dược (GCN đủ ĐKKD dược) LẦN ĐẦU do Sở Y tế cấp cho
cơ sở bán buôn / nhà thuốc / quầy thuốc. Đầu vào (có thể là MỘT PDF gộp nhiều giấy tờ):
- Danh mục hồ sơ (bảng kê giấy tờ + "Bảng dữ liệu dùng chung") — chỉ để tham khảo, ưu tiên giấy gốc.
- Đơn đề nghị cấp GCN đủ ĐKKD dược (Mẫu số 10): Tên cơ sở, Địa chỉ trụ sở chính, Địa chỉ địa điểm kinh doanh, Số
  điện thoại liên hệ (bàn – Di động), Người chịu trách nhiệm chuyên môn, Số CCHN, Loại hình, Phạm vi kinh doanh,
  người ký "NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT".
- Giấy chứng nhận đăng ký doanh nghiệp (Tên công ty, Mã số doanh nghiệp, Địa chỉ trụ sở chính, Điện thoại, Fax, Email,
  mục "Người đại diện theo pháp luật": Họ và tên, Giới tính, Sinh ngày, Số giấy tờ pháp lý, Ngày cấp, Nơi cấp, Địa
  chỉ thường trú) hoặc GCN đăng ký hộ kinh doanh.
- Tài liệu kỹ thuật GDP/GPP, Tài liệu thuyết minh an ninh (Mẫu số 11), Chứng chỉ hành nghề dược (của người chịu
  trách nhiệm chuyên môn — KHÁC người đại diện).
- CCCD của người đại diện và/hoặc CCCD của người nộp thay.

HAI vai — tách RIÊNG, KHÔNG lẫn:
- CHỦ HỒ SƠ (ChuHoSo_*) = NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT của cơ sở (Giám đốc / chủ hộ kinh doanh). KHÔNG phải người
  chịu trách nhiệm chuyên môn đứng tên trên Chứng chỉ hành nghề dược (trừ khi đó cũng là người đại diện).
- NGƯỜI NỘP (NguoiNop_*) = tài khoản đăng nhập cổng. Chỉ trích khi khối <nguoi_nop_context> báo hồ sơ CÓ CCCD của
  người đó; nếu người nộp chính là chủ hồ sơ hoặc không có CCCD → BỎ TRỐNG NguoiNop_*.

NGUỒN ChuHoSo_* (ưu tiên theo thứ tự): CCCD của người đại diện → GCN đăng ký doanh nghiệp mục "Người đại diện theo
pháp luật" → Đơn → Mẫu 11 → Tài liệu kỹ thuật.
- SoDinhDanh: CCCD, hoặc GCN đăng ký doanh nghiệp "Số giấy tờ pháp lý của cá nhân" của người đại diện. KHÔNG lấy Mã
  số doanh nghiệp, số CCHN dược, số định danh của người chịu trách nhiệm chuyên môn.
- NgayCap/NoiCap: thẻ CCCD, hoặc GCN đăng ký doanh nghiệp "Ngày cấp"/"Nơi cấp" giấy tờ pháp lý của người đại diện.
  Đơn có dòng "Số CCHN Dược ... Nơi cấp: Sở Y tế ... Năm cấp ..." — đó là của CHỨNG CHỈ HÀNH NGHỀ, TUYỆT ĐỐI KHÔNG
  dùng.
- ThuongTru: nơi thường trú CÁ NHÂN của người đại diện (CCCD / GCN đăng ký doanh nghiệp "Địa chỉ thường trú"). KHÔNG
  lấy "Địa chỉ trụ sở chính", "Địa điểm kinh doanh" của cơ sở. CCCD cũ ghi địa giới CŨ (quận/huyện trước sáp nhập)
  mà GCN đăng ký doanh nghiệp ghi địa giới MỚI → ưu tiên địa giới MỚI. chiTietDuoiXa CHỈ số nhà/ngõ/đường/thôn.
- DienThoai: số DI ĐỘNG (09x/03x/05x/07x/08x, 10 số). Đơn ghi "024 3000 0000 – Di động: 0912 000 111" → lấy
  "0912000111". KHÔNG lấy số máy bàn.

CoSo_*: chỉ dùng soạn ô Ghi chú — Tên cơ sở, Mã số doanh nghiệp, Loại hình, Địa điểm kinh doanh chép nguyên văn.

LƯU Ý: Phạm vi kinh doanh, vốn, nhân sự, trang thiết bị, SOP... KHÔNG có ô nhập online → KHÔNG trích.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""

"""Luật prompt riêng cho thủ tục 1.013066 — Đăng ký xe lần đầu toàn trình đối với xe nhập khẩu."""

EXTRA_RULES = """Hồ sơ đăng ký xe (xe nhập khẩu), có thể gồm: thẻ căn cước của chủ xe; Giấy chứng nhận thu hồi đăng ký, biển số xe (GCN thu hồi); Hợp đồng mua bán xe có lời chứng công chứng (HĐMB); Dữ liệu điện tử về lệ phí trước bạ hoặc Thông báo nộp lệ phí trước bạ (LPTB); Hóa đơn bán xe; Tờ khai hàng hóa nhập khẩu (hải quan); Giấy khai đăng ký xe; có khi kèm trang thông tin hồ sơ ghi hình thức nhận kết quả. Mỗi field có tiền tố theo giấy (Cccd_, GcnThuHoi_, Hdmb_, Lptb_, HoaDon_, ToKhaiHq_, ToKhai_, HoSo_): CHỈ đọc field từ đúng giấy đó, giấy nào không có trong hồ sơ thì bỏ hết field của nó. Hợp đồng mua bán KHÔNG phải hóa đơn: không trả HoaDon_* từ hợp đồng.

CHỦ XE = người đứng tên đăng ký xe (chủ xe MỚI: bên mua trong HĐMB, mục "Sang tên cho chủ xe mới" trên GCN thu hồi, người nộp lệ phí trước bạ, người mua trên hóa đơn):
- Cccd_* chỉ đọc từ thẻ căn cước/CCCD của chủ xe. Không lấy thẻ của bên bán hay người được ủy quyền.
- Thẻ căn cước mẫu mới: ngày cấp ở dòng "Ngày, tháng, năm cấp / Date of issue"; nơi cấp là dòng "BỘ CÔNG AN" in cuối mặt sau dù không có nhãn.
- GCN thu hồi: "Chủ xe" + "Địa chỉ" ngay dưới là chủ xe CŨ (GcnThuHoi_ChuXe, GcnThuHoi_DiaChiChuXe); mục "Sang tên cho chủ xe mới" mới là chủ xe mới (GcnThuHoi_ChuMoi*). "Công an xã ..." ở đầu giấy là nơi thu hồi, không phải địa chỉ ai.
- HĐMB: bên bán (bên A) có thể nhiều người và có người được ủy quyền ký thay — Hdmb_BenBan* lấy người ĐẦU TIÊN của bên A. Email / số điện thoại của văn phòng công chứng ở đầu hợp đồng KHÔNG phải của chủ xe.

ĐẶC ĐIỂM XE:
- Xe_* là đặc điểm theo giấy đăng ký: lấy theo GCN thu hồi trước, rồi Giấy khai, HĐMB, Tờ khai hải quan, Hóa đơn. Lptb_* (nhãn hiệu, số loại, dung tích…) đọc RIÊNG từ giấy lệ phí trước bạ, chép đúng như giấy đó in (kể cả khi khác GCN thu hồi, vd số loại có thêm mã trong ngoặc, dung tích lệch 1 đơn vị).
- Ô ghi chấm chấm "……" là để trống → bỏ field, không ghi chữ "Trống". Số khung/số máy chép đúng từng ký tự, không thêm khoảng trắng; bản cà số khung/số máy dán trên giấy KHÔNG đọc.
- "Màu biển" (màu nền biển số) KHÔNG phải màu sơn.

LỆ PHÍ TRƯỚC BẠ / GIÁ TIỀN:
- Lptb_NgayNop là dòng "Ngày nộp"; Lptb_NgayThongBao là ngày ban hành Thông báo. Ô ngày để "__/__/__" → bỏ field.
- Số tiền chép đúng chữ số như in, không đổi đơn vị. HoaDon_So giữ đủ số 0 đầu.

Không bịa thông tin thiếu; không chắc thì bỏ field. Không trả field UI như CongDan__fs*."""

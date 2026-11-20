"""Luật prompt riêng cho thủ tục 2.000076 — Đăng ký sang tên, di chuyển xe thực hiện tại Công an cấp tỉnh."""

EXTRA_RULES = """Hồ sơ đăng ký sang tên / di chuyển xe, có thể gồm: thẻ căn cước của chủ xe; Giấy chứng nhận thu hồi đăng ký, biển số xe (GCN thu hồi); Hợp đồng mua bán / tặng cho xe có lời chứng công chứng (HĐMB); Dữ liệu điện tử về lệ phí trước bạ hoặc Thông báo nộp lệ phí trước bạ (LPTB); Giấy khai đăng ký xe; giấy ủy quyền làm thủ tục đăng ký xe kèm thẻ căn cước người được ủy quyền; giấy phép kinh doanh vận tải; giấy xác nhận trúng đấu giá biển số; có khi kèm trang thông tin hồ sơ ghi hình thức nhận kết quả. Mỗi field có tiền tố theo giấy (Cccd_, GcnThuHoi_, Hdmb_, Lptb_, Xe_, ToKhai_, UyQuyen_, CccdNduq_, GpKdvt_, DauGia_, HoSo_): CHỈ đọc field từ đúng giấy đó, giấy nào không có trong hồ sơ thì bỏ hết field của nó.

CHỦ XE = người đứng tên đăng ký xe: khi sang tên là chủ xe MỚI (bên mua trong HĐMB, mục "Sang tên cho chủ xe mới" trên GCN thu hồi, người nộp lệ phí trước bạ); khi di chuyển nguyên chủ là chính "Chủ xe" trên GCN thu hồi.
- Cccd_* chỉ đọc từ thẻ căn cước/CCCD của chủ xe. Thẻ của người được chủ xe ủy quyền làm thủ tục → CccdNduq_*. Thẻ của bên bán → bỏ.
- Thẻ căn cước mẫu mới: ngày cấp ở dòng "Ngày, tháng, năm cấp / Date of issue"; nơi cấp là dòng "BỘ CÔNG AN" in cuối mặt sau dù không có nhãn.
- GCN thu hồi: "Chủ xe" + dòng "Địa chỉ", "Số điện thoại", "Mã định danh", "Ngày cấp" ngay dưới là của chủ xe CŨ (GcnThuHoi_ChuXe*); mục "Sang tên cho chủ xe mới" mới là chủ xe mới (GcnThuHoi_ChuMoi*). "Công an xã ..." ở đầu giấy là nơi thu hồi; "Mã hồ sơ trực tuyến" của GCN thu hồi KHÔNG phải mã hồ sơ lệ phí trước bạ.
- HĐMB: bên bán (bên A) có thể nhiều người và có người được bên bán ủy quyền ký thay — người đó KHÔNG phải người làm thủ tục đăng ký xe, không trả UyQuyen_* / CccdNduq_* từ hợp đồng mua bán. Email / số điện thoại của văn phòng công chứng ở đầu hợp đồng KHÔNG phải của chủ xe.
- UyQuyen_* chỉ đọc từ giấy/hợp đồng ủy quyền mà bên ủy quyền là CHỦ XE (giao cho người khác làm thủ tục đăng ký xe).

ĐẶC ĐIỂM XE (Xe_*): lấy theo GCN thu hồi trước, rồi HĐMB, rồi Giấy khai. Số khung/số máy chép đúng từng ký tự, không thêm khoảng trắng; bản cà số khung/số máy dán trên giấy KHÔNG đọc. "Màu biển" (màu nền biển số) KHÔNG phải màu sơn. Lptb_* (biển số, số máy, số khung) đọc RIÊNG từ giấy lệ phí trước bạ.

Ô ghi chấm chấm "……" hoặc "__/__/__" là để trống → bỏ field. Số điện thoại chép đúng chữ số như in (kể cả dãy toàn số 0). Không bịa thông tin thiếu; không chắc thì bỏ field. Không trả field UI như CongDan__fs*."""

"""Prompt rules đặc thù cho "Cấp giấy phép chặt hạ, dịch chuyển cây xanh" (cổng DVC Bộ Xây dựng)."""

EXTRA_RULES = """Thủ tục: Cấp giấy phép chặt hạ, dịch chuyển cây xanh. Đầu vào gồm: Đơn đề nghị cấp giấy
phép chặt hạ/dịch chuyển cây xanh (Mẫu số 01, Phụ lục I) có BẢNG KÊ CÂY XANH, CCCD của chủ hồ sơ (người
đề nghị), có thể có Giấy chứng nhận QSDĐ; có thể có CCCD của người nộp thay.

HAI vai — tách RIÊNG:
- CHỦ HỒ SƠ (ChuHoSo_*, ToKhai_*) = người/tổ chức ĐỀ NGHỊ cấp phép, đứng tên Đơn Mẫu 01. Đây là chủ thể
  chính, trích đầy đủ (tên, số định danh, địa chỉ, điện thoại) + nội dung đơn (kính gửi, lý do, bảng cây).
- NGƯỜI NỘP (NguoiNop_*) = tài khoản nộp trên cổng. Trích NguoiNop_* khi hồ sơ CÓ CCCD của người nộp
  (kể cả khi người nộp CHÍNH LÀ chủ hồ sơ — cùng một người). ⚠ BẮT BUỘC: CCCD LUÔN in ngày sinh ("Ngày
  sinh / Date of birth") và giới tính ("Giới tính / Sex") → khi có CCCD người nộp thì PHẢI điền
  NguoiNop_NgaySinh (dd/mm/yyyy) và NguoiNop_GioiTinh ("Nam"/"Nữ"), TUYỆT ĐỐI không bỏ sót.

⚠ CHỦ HỒ SƠ có thể CÁ NHÂN hoặc TỔ CHỨC:
- TỔ CHỨC: ChuHoSo_LoaiChuThe='Tổ chức'; ChuHoSo_Ten=tên tổ chức.
- CÁ NHÂN: ChuHoSo_LoaiChuThe='Cá nhân'; ChuHoSo_Ten=họ tên.

⚠ ChuHoSo_NguoiDaiDien + ChuHoSo_ChucVu: 2 mục này BẮT BUỘC trên form và Đơn Mẫu 01 thường có SẴN 2 dòng
'Người đại diện của tổ chức' + 'Chức vụ' — LẤY nguyên văn nếu đơn CÓ ghi, KỂ CẢ khi chủ hồ sơ là cá nhân
(người đứng đại diện/nộp thay). CHỈ bỏ trống khi đơn thực sự để trống 2 mục này.

BẢNG KÊ CÂY XANH (BangKeCay) — MẢNG, mỗi cây 1 phần tử {loaiCay, viTri, chieuCao, duongKinh, moTa}. Trích
ĐÚNG số dòng có trong bảng kê của Đơn Mẫu 01, GIỮ NGUYÊN đơn vị (m, cm). moTa = mô tả tình trạng cây
(mục, nghiêng, khô, sâu bệnh...). Nếu bảng có nhiều cây → trả nhiều phần tử.

ĐỊA CHỈ chủ hồ sơ (ChuHoSo_DiaChi): MỘT chuỗi đầy đủ (số nhà, đường, phường, tỉnh) — cổng chỉ có 1 ô địa
chỉ cho chủ hồ sơ (khác Phần I người nộp tách tỉnh/xã).

ĐIỆN THOẠI/FAX: Đơn Mẫu 01 mục 'Điện thoại' và 'Fax' thường trên cùng một dòng. Trích ChuHoSo_DienThoai =
số điện thoại, ChuHoSo_Fax = số Fax (chỉ chữ số, bỏ ngoặc). Nếu số điện thoại bị thiếu/cắt cụt (không đủ
10 số) mà Fax là số hợp lệ → cứ điền cả Fax vào ChuHoSo_Fax để hệ thống dùng làm dự phòng.

⚠ DẤU CHẤM CHỖ TRỐNG: trên mẫu giấy, các ô để trống hiện dưới dạng dòng dấu chấm ("......." hoặc nhiều
dòng chấm). ĐÓ LÀ Ô TRỐNG — BỎ QUA, để field RỖNG (không có), TUYỆT ĐỐI KHÔNG lấy chuỗi dấu chấm làm giá
trị. Ở cuối câu có dữ liệu cũng cắt bỏ dấu chấm điền thừa

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""

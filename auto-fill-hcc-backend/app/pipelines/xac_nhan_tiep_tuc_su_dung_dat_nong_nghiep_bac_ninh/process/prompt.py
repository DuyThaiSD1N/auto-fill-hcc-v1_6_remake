"""Quy tắc compact prompt cho "[Bắc Ninh] Xác nhận tiếp tục sử dụng đất nông nghiệp" (1.115462)."""

EXTRA_RULES = """Đầu vào thường gồm: Đơn xin xác nhận (lại) thời hạn sử dụng đất nông nghiệp (Mẫu số 09) — trang 1 là
đơn, trang 2 là "II- XÁC NHẬN CỦA ỦY BAN NHÂN DÂN CẤP XÃ"; Giấy chứng nhận quyền sử dụng đất đã cấp (bìa + trang chứng
nhận, có thể viết tay, mẫu cũ); Giấy ủy quyền kèm lời chứng chứng thực (nếu nộp thay); có thể có CCCD.

NGUỒN DỮ LIỆU:
- Mọi field Don_* CHỈ lấy từ Đơn Mẫu 09, đúng mục của field. Mục trống hoặc chỉ có dấu chấm "…." → BỎ field.
- Don_NoiKhai / Don_NgayKhai: dòng "<địa danh>, ngày … tháng … năm …" ở ĐẦU Đơn (không phải ngày ở phần xác nhận).
- Don_DiaChiLienHe: CHUỖI một dòng, chép nguyên văn mục 2 (gồm cả "điện thoại: …"). KHÔNG trả object.
- Thửa đất: Đơn có thể liệt kê NHIỀU dòng "Thửa đất số … Tờ bản đồ số … Diện tích (m2) …". Lấy ĐỦ mọi dòng, giữ ĐÚNG
  thứ tự; Don_ThuaSo / Don_ToBanDo / Don_DienTich mỗi field là MỘT chuỗi ngăn bằng ", ", phần tử thứ i của ba field là
  cùng một thửa. Đơn không có thì lấy theo bảng liệt kê của Giấy chứng nhận.
- Gcn_SoPhatHanh / Gcn_SoVaoSo / Gcn_NgayCap: mục 3.8 của Đơn; Đơn không ghi thì đọc ở Giấy chứng nhận (số in ở bìa,
  dòng "Vào sổ cấp giấy chứng nhận … Số", ngày ký). Chép đúng ký tự.
- Mục 4: phần chữ trước "đến ngày" → Don_NoiDungDeNghi; số ngày / tháng / năm viết tay sau "đến ngày", "tháng", "năm"
  → Don_DenNgay / Don_DenThang / Don_DenNam. Chỗ chỉ có dấu chấm → bỏ field đó.
- Xn_NoiDung: chép đủ các đoạn nội dung xác nhận của UBND cấp xã (nối đoạn bằng "\\n"); Xn_NgayXacNhan là ngày ký phần
  xác nhận. Trang xác nhận trống → bỏ.
- ChuHoSo_SoDinhDanh: số CCCD của người sử dụng đất = BÊN ỦY QUYỀN (mục I của Giấy ủy quyền / dòng 1 của lời chứng).
  TUYỆT ĐỐI KHÔNG lấy số của BÊN ĐƯỢC ỦY QUYỀN.

KHÔNG trả field UI ("element_...", "nhanTaiNha..."); chỉ trả field nguồn trong schema. Không bịa; không có thì bỏ.

Ví dụ output ĐÚNG (dữ liệu bịa):
```json
{"fields":{"Don_NoiKhai":"Đông Phong","Don_NgayKhai":"05/03/2026","Don_KinhGui":"Văn phòng đăng ký đất đai liên phường, xã Yên Phong","Don_NguoiSuDungDat":"Lê Văn An","Don_GioiTinh":"Nam","Don_DiaChiLienHe":"Thôn Đông, xã Đông Phong, tỉnh Bắc Ninh, điện thoại: 0912.345.678","Don_DienThoai":"0912345678","Don_ThuaSo":"12, 45","Don_ToBanDo":"III, IV","Don_DienTich":"240, 360","Don_MucDich":"Canh tác","Don_ThoiHan":"tháng 10/2013","Don_TaiSan":"Không","Don_DiaDiem":"Thôn Đông, xã Đông Phong, tỉnh Bắc Ninh","Gcn_SoPhatHanh":"M 123456","Gcn_SoVaoSo":"00123 QSDĐ/100 QĐCT","Gcn_NgayCap":"15/06/1999","Don_DenThang":"10","Don_DenNam":"2063","Xn_NoiDung":"Các thửa đất nêu trên hiện sử dụng vào mục đích canh tác, sử dụng ổn định, không tranh chấp.","Xn_NgayXacNhan":"06/03/2026","ChuHoSo_SoDinhDanh":"027060001234"}}
```"""

# purpose="authorized_person": chỉ nhân thân MỘT người = chủ hồ sơ (bên ủy quyền) → khối doiTuongKhac*.
RULES_UYQUYEN = """Trích NHÂN THÂN của CHỦ HỒ SƠ (người sử dụng đất đứng Đơn Mẫu 09) để điền khối "Thông tin trong
trường hợp được ủy quyền" — tài khoản đang nộp là người ĐƯỢC ủy quyền (nộp thay), cổng hỏi thông tin người đã ủy quyền
cho họ. Đầu vào: Giấy ủy quyền ("I. BÊN ỦY QUYỀN" / "II. BÊN ĐƯỢC ỦY QUYỀN") kèm lời chứng chứng thực, Đơn Mẫu 09, Giấy
chứng nhận; có thể có CCCD.

CHỌN ĐÚNG NGƯỜI:
- Có Giấy ủy quyền: LẤY "I. BÊN ỦY QUYỀN" (bên A). ⚠ TUYỆT ĐỐI KHÔNG lấy "II. BÊN ĐƯỢC ỦY QUYỀN" (bên B, người đi nộp
  thay) — người đó KHÔNG lên field nào. Lời chứng chứng thực liệt kê cả hai người: chỉ lấy dòng của bên ủy quyền.
- Không có giấy ủy quyền: lấy người ở mục "1. Người sử dụng đất" của Đơn và CCCD của chính người đó.

Họ tên viết hoa chữ đầu, không kèm "Ông/Bà". Số CCCD chỉ chữ số. Ngày dd/mm/yyyy ("Năm sinh: 25/02/1959" ghi đủ ngày
→ ChuHoSo_NgaySinh "25/02/1959").
ChuHoSo_NoiCap: Giấy ủy quyền ghi tắt "Cục cảnh sát" → trả "Cục Cảnh sát quản lý hành chính về trật tự xã hội".
ChuHoSo_ThuongTru là OBJECT {quocGia,tinh,xa,chiTietDuoiXa} theo "Hộ khẩu thường trú" / nơi thường trú của bên ủy quyền
(vd "Thôn Đông, Xã Đông Phong, Tỉnh Bắc Ninh" → tinh "Bắc Ninh", xa "Xã Đông Phong", chiTietDuoiXa "Thôn Đông").
ChuHoSo_DienThoai: Giấy ủy quyền để trống "……" thì lấy số điện thoại ở mục 2 của Đơn.
ChuHoSo_GioiTinh: CCCD, hoặc danh xưng "ông"/"bà" đứng trước tên người sử dụng đất ở Đơn / Giấy chứng nhận.

⚠ KHÔNG BỊA: chỉ trích field giấy tờ ghi RÕ; không có/không chắc → bỏ field.
KHÔNG trả field UI ("doiTuongKhac...", "element_..."); chỉ trả field nguồn trong schema."""

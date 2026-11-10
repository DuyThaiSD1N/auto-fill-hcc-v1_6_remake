"""Quy tắc compact prompt cho "[Bắc Ninh] Cấp lại Giấy chứng nhận do bị mất"."""

EXTRA_RULES = """Đầu vào thường là MỘT tệp scan chung gồm: Đơn đăng ký biến động đất đai (Mẫu số 18, chữ viết tay),
Đơn trình báo về việc mất giấy chứng nhận, Bản cam kết, giấy xác nhận tình trạng hôn nhân, CCCD của người đứng đơn.
Giấy chứng nhận đã MẤT nên thường không có bản GCN.

NGUỒN DỮ LIỆU:
- Cccd_HoTen/Cccd_SoDinhDanh: lấy từ CCCD nếu có; không có CCCD thì lấy từ Đơn (dòng "- Tên", "- Giấy tờ nhân
  thân/pháp nhân"). Số CCCD viết tay có dấu chấm ("0011.020.12345") → chỉ giữ chữ số.
- Cccd_NgayCap/Cccd_NoiCap CHỈ có khi upload CCCD (mặt sau) hoặc giấy tờ ghi rõ "cấp ngày …". Nơi cấp: "CỤC TRƯỞNG CỤC
  CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC
  mới ghi "BỘ CÔNG AN" → "Bộ Công an".

- QUAN TRỌNG — Don_DiaChi là NGOẠI LỆ của quy tắc địa chỉ chung (quy tắc 5): KHÔNG trả object. Don_DiaChi PHẢI là
  CHUỖI MỘT DÒNG, chép NGUYÊN VĂN dòng "- Địa chỉ" ở mục I của Đơn Mẫu 18 (đúng như người dân viết, kể cả địa giới
  cũ), GIỮ ĐỦ thôn/tổ dân phố + phường/xã + tỉnh. KHÔNG lấy địa chỉ từ CCCD hay Đơn trình báo cho field này.

- Don_KinhGui lấy từ dòng "Kính gửi:" đầu Đơn Mẫu 18; bỏ ký hiệu chú thích "(1)". Bỏ field nếu đơn không ghi.
- Don_NoiDungBienDong CHỈ lấy từ mục "II. Nội dung biến động" của Đơn Mẫu 18, NGUYÊN VĂN, GIỮ từng dòng gạch đầu dòng
  (nối các dòng bằng "\\n"). Với thủ tục này thường có "- Cấp lại giấy chứng nhận do bị mất", có thể kèm dòng khác
  (vd thay đổi địa chỉ). Mục trống → BỎ field.
- Gcn_SoVaoSo / Gcn_SoPhatHanh: thông tin GIẤY CHỨNG NHẬN BỊ MẤT, đọc ở Đơn, Đơn trình báo mất hoặc Bản cam kết
  ("có số vào sổ CS…", "Số phát hành CĐ …"). Chép đúng ký tự, không suy luận. Không ghi → bỏ.
- Don_DienThoai lấy từ Đơn (dòng "Điện thoại liên hệ"); chỉ chữ số.
- Don_GiayTo2/Don_GiayTo3: CHỈ lấy dòng "(2) …" / "(3) …" ở mục IV của Đơn. Dòng trống/chỉ có dấu chấm → BỎ, KHÔNG
  tự liệt kê các giấy tờ khác trong tệp. KHÔNG lấy dòng in sẵn "(1) Giấy chứng nhận đã cấp".
- Don_MaSoThue/Don_Email/Don_MienGiam/Don_ThanhVienHo/Don_TranhChap/Don_RanhGioi: CHỈ chép khi Đơn GHI RÕ nội dung ở
  đúng dòng đó. Dòng trống hoặc chỉ có dấu chấm "...." → BỎ field, không suy luận (Bản cam kết "không thế chấp, cầm
  cố…" KHÔNG phải tình trạng tranh chấp).

KHÔNG trả field UI dạng "- Tên", "nhanTaiNha...", element_...; chỉ trả field nguồn trong schema. Không bịa thông tin
còn thiếu; ô/tài liệu không có thì bỏ field.

Ví dụ output ĐÚNG (Don_DiaChi là chuỗi có phường/xã; Don_NoiDungBienDong giữ xuống dòng):
```json
{"fields":{"Cccd_HoTen":"Nguyễn Văn An","Cccd_SoDinhDanh":"027090001234","Cccd_NgayCap":"10/05/2022","Cccd_NoiCap":"Cục Cảnh sát quản lý hành chính về trật tự xã hội","Don_KinhGui":"Chi nhánh Văn phòng đăng ký đất đai liên phường, xã Từ Sơn","Don_DiaChi":"Thôn Đông, phường Tân Hồng, tỉnh Bắc Ninh","Don_DienThoai":"0912345678","Don_NoiDungBienDong":"- Cấp lại giấy chứng nhận do bị mất","Gcn_SoVaoSo":"CS01234/T05/Q02","Gcn_SoPhatHanh":"CĐ 123456"}}
```"""

# purpose="authorized_person": chỉ nhân thân MỘT người = chủ hồ sơ (bên ủy quyền) → khối doiTuongKhac*.
RULES_UYQUYEN = """Trích NHÂN THÂN của CHỦ HỒ SƠ (người sử dụng đất bị mất Giấy chứng nhận, người đứng Đơn Mẫu 18) để
điền khối "Thông tin trong trường hợp được ủy quyền" — tài khoản đang nộp là người ĐƯỢC ủy quyền (nộp thay), cổng
hỏi thông tin người đã ủy quyền cho họ. Đầu vào: Đơn đăng ký biến động (Mẫu số 18), CCCD, Đơn trình báo mất, Bản cam
kết, giấy xác nhận tình trạng hôn nhân; có thể có Giấy/Văn bản ủy quyền.

CHỌN ĐÚNG NGƯỜI:
- Có Giấy ủy quyền ("BÊN ỦY QUYỀN (bên A)" / "BÊN ĐƯỢC ỦY QUYỀN (bên B)"): LẤY BÊN ỦY QUYỀN (bên A).
- ⚠ TUYỆT ĐỐI KHÔNG lấy bên ĐƯỢC ủy quyền (bên B, người đi nộp thay) — người đó KHÔNG lên field nào.
- Không có giấy ủy quyền: lấy người đứng Đơn Mẫu 18 (dòng "- Tên") và CCCD của chính người đó.
- Tên chủ GCN cũ (người đã chuyển nhượng cho chủ hồ sơ) ghi trong Đơn trình báo/Bản cam kết KHÔNG phải chủ hồ sơ.

Họ tên viết hoa chữ đầu, không kèm "Ông/Bà". Số CCCD chỉ chữ số. Ngày dd/mm/yyyy.
ChuHoSo_ThuongTru là OBJECT {quocGia,tinh,xa,chiTietDuoiXa} theo TÊN HÀNH CHÍNH HIỆN HÀNH. Giấy tờ ghi địa giới cũ kèm
"(nay thuộc phường Y, tỉnh Z)" / "(nay là …)" thì lấy tỉnh/phường "nay"; chiTietDuoiXa = thôn/tổ dân phố/khu dân cư
cũ còn ghi (vd "Thôn X - huyện cũ (nay thuộc phường Y, tỉnh Bắc Ninh)" → tinh "Bắc Ninh", xa "Phường Y",
chiTietDuoiXa "Thôn X").
ChuHoSo_GioiTinh chỉ điền khi giấy tờ ghi rõ giới tính hoặc danh xưng riêng "Ông"/"Bà"; dòng in sẵn "Ông, bà:" → BỎ.

⚠ KHÔNG BỊA: chỉ trích field giấy tờ ghi RÕ; không có/không chắc → bỏ field.
KHÔNG trả field UI ("doiTuongKhac...", "element_..."); chỉ trả field nguồn trong schema."""

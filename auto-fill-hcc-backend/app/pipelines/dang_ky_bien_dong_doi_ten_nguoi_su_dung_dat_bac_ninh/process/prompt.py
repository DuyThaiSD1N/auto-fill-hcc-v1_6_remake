"""Quy tắc compact prompt cho "[Bắc Ninh] Đăng ký biến động do đổi tên / thay đổi thông tin người sử dụng đất"."""

EXTRA_RULES = """Đầu vào là một hoặc nhiều tệp scan gồm: Đơn đăng ký biến động đất đai (Mẫu số 18 hoặc Mẫu số 24, có thể
viết tay), Giấy chứng nhận quyền sử dụng đất đã cấp (có thể là bản sao chứng thực, kèm trang bổ sung), CCCD, giấy tờ
chứng minh việc thay đổi thông tin (giấy xác nhận thông tin về cư trú, giấy xác nhận số CMND cũ, quyết định cho phép thay
đổi họ tên, trích lục thay đổi hộ tịch…), Văn bản cam kết của các thành viên hộ gia đình có chung quyền sử dụng đất
(kèm lời chứng thực chữ ký), có thể kèm văn bản ủy quyền, mảnh trích đo bản đồ địa chính.

HAI KIỂU ĐƠN:
- Mẫu số 18: mục "I." có dòng "- Tên", "- Giấy tờ nhân thân/pháp nhân", "- Địa chỉ", "- Mã số thuế", "- Điện thoại liên
  hệ", "Hộp thư điện tử"; "II. Nội dung biến động"; "III. … miễn, giảm"; "IV. Giấy tờ nộp kèm"; "V. Cam kết".
- Mẫu số 24: "1. Người sử dụng đất…" chia "1.1. Tên Ông: …" và "1.2. Tên Bà: …" (mỗi người có Giấy tờ nhân thân, Địa
  chỉ thường trú, Điện thoại, Hộp thư); "2. Nội dung biến động"; "3. Giấy tờ liên quan … gồm có: (1) Giấy chứng nhận đã
  cấp; (2) …". Mẫu 24 KHÔNG có mục miễn giảm và mục V.
- Người THỨ NHẤT (dòng "- Tên" đầu / mục 1.1) → Cccd_*, Don_DanhXung, Don_DiaChi, Don_DienThoai, Don_Email. Người THỨ
  HAI (mục 1.2 / dòng "- Tên" thứ hai) → Don2_*. Đơn chỉ một người → KHÔNG trả Don2_*. KHÔNG đổi chỗ hai người, KHÔNG
  gán số điện thoại / giấy tờ của người này cho người kia (mục 1.1 để trống điện thoại thì Don_DienThoai bỏ).

THÔNG TIN CŨ VÀ MỚI: thủ tục này đăng ký THAY ĐỔI thông tin. Giấy chứng nhận in thông tin CŨ (tên cũ, số CMND 9 số cũ,
địa chỉ cũ, "Hộ ông …"). Các field Cccd_* / Don_* là thông tin HIỆN TẠI của người đứng đơn — lấy từ CCCD và Đơn, KHÔNG
lấy từ phần người sử dụng đất in trên Giấy chứng nhận.

NGUỒN DỮ LIỆU:
- Cccd_HoTen/Cccd_SoDinhDanh: lấy từ CCCD của người thứ nhất nếu có; không có CCCD thì lấy từ Đơn. Số CCCD viết tay có
  dấu chấm ("0011.020.12345") → chỉ giữ chữ số.
- Cccd_NgayCap/Cccd_NoiCap: mặt sau CCCD, hoặc Văn bản cam kết / lời chứng thực ghi "Căn cước công dân số … do … cấp
  ngày …" cho ĐÚNG người thứ nhất. Nơi cấp: "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" / "Cục cảnh
  sát Quản lý hành chính về trật tự xã hội" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi
  "BỘ CÔNG AN" → "Bộ Công an".

- QUAN TRỌNG — Don_DiaChi / Don2_DiaChi là NGOẠI LỆ của quy tắc địa chỉ chung (quy tắc 5): KHÔNG trả object. PHẢI là
  CHUỖI MỘT DÒNG, chép NGUYÊN VĂN dòng "- Địa chỉ" / "- Địa chỉ thường trú" của đúng người đó trên Đơn (kể cả địa giới
  cũ), GIỮ ĐỦ thôn/tổ dân phố + phường/xã + tỉnh. KHÔNG lấy địa chỉ từ CCCD hay Giấy chứng nhận cho field này.

- Don_KinhGui lấy từ dòng "Kính gửi:" đầu Đơn; bỏ ký hiệu chú thích "(1)". Bỏ field nếu đơn không ghi.
- Don_NoiDungBienDong CHỈ lấy từ mục "Nội dung biến động" của Đơn, NGUYÊN VĂN (kể cả rất ngắn, vd "Thay đổi Hộ"), GIỮ
  từng dòng gạch đầu dòng (nối các dòng bằng "\\n"), bỏ dấu chấm giữ chỗ. Mục trống → BỎ field, KHÔNG tự đặt câu, KHÔNG
  ghép thêm số Giấy chứng nhận.
- Don_DienThoai lấy từ Đơn (dòng "Điện thoại liên hệ"); chỉ chữ số. Số viết tay đọc kỹ đủ 10 chữ số.
- Don_GiayTo2/Don_GiayTo3: CHỈ lấy dòng "(2) …" / "(3) …" ở mục giấy tờ nộp kèm của Đơn. Dòng trống/chỉ có dấu chấm →
  BỎ, KHÔNG tự liệt kê các giấy tờ khác trong tệp. KHÔNG lấy dòng in sẵn "(1) Giấy chứng nhận đã cấp".
- Don_MaSoThue/Don_Email/Don_MienGiam/Don_ThanhVienHo/Don_TranhChap/Don_RanhGioi: CHỈ chép khi Đơn GHI RÕ nội dung ở
  đúng dòng đó. Dòng trống hoặc chỉ có dấu chấm "...." → BỎ field, không suy luận.
- Don_NoiKhai / Don_NgayKhai: dòng "<địa danh>, ngày … tháng … năm …" ngay trên chữ "Người viết đơn" (số viết tay, vd
  "ngày 9 tháng 10 năm 2026" → "09/10/2026"). Địa danh chỉ có dấu chấm → bỏ Don_NoiKhai. KHÔNG lấy ngày của lời chứng
  thực, Giấy chứng nhận hay văn bản cam kết.

VĂN BẢN CAM KẾT CỦA CÁC THÀNH VIÊN HỘ GIA ĐÌNH (chỉ khi hồ sơ có văn bản này; không có → bỏ mọi Vbck_*):
- Vbck_TieuDe: tiêu đề + phụ đề viết thường thành một cụm, vd "Văn bản cam kết của các thành viên hộ gia đình có chung
  quyền sử dụng đất".
- Vbck_ChungThuc: từ trang "LỜI CHỨNG CHỨNG THỰC" / lời công chứng, vd "chứng thực chữ ký, điểm chỉ ngày 05/03/2026 tại
  Văn phòng Công chứng X, tỉnh Y".
- Vbck_ThanhVien: MẢNG đủ mọi thành viên "1. Ông …", "2. Bà …", … ở đầu văn bản, đúng thứ tự, mỗi người
  {"danhXung","hoTen","ngaySinh","soDinhDanh","thuongTru"} — thuongTru là CHUỖI nguyên văn sau "Địa chỉ thường trú tại".
- Vbck_TranhChap: câu cam kết không tranh chấp, nguyên văn bỏ gạch đầu dòng.

KHÔNG trả field UI dạng "- Tên", "nhanTaiNha...", element_...; chỉ trả field nguồn trong schema. Không bịa thông tin
còn thiếu; ô/tài liệu không có thì bỏ field.

Ví dụ output ĐÚNG (Đơn Mẫu 24 hai người; Don_DiaChi là chuỗi có phường/xã; dữ liệu ví dụ là bịa):
```json
{"fields":{"Cccd_HoTen":"NGUYỄN VĂN AN","Don_DanhXung":"Ông","Cccd_SoDinhDanh":"027070001234","Cccd_NgayCap":"10/05/2021","Cccd_NoiCap":"Cục Cảnh sát quản lý hành chính về trật tự xã hội","Don_KinhGui":"Chi nhánh Văn phòng đăng ký đất đai liên phường Tân Hồng","Don_DiaChi":"Thôn Đông, phường Tân Hồng, tỉnh Bắc Ninh","Don2_DanhXung":"Bà","Don2_HoTen":"TRẦN THỊ BÌNH","Don2_SoGiayTo":"027172005678","Don2_DiaChi":"Thôn Đông, phường Tân Hồng, tỉnh Bắc Ninh","Don2_DienThoai":"0912345678","Don_NoiDungBienDong":"Thay đổi Hộ","Don_NgayKhai":"05/03/2026","Vbck_TieuDe":"Văn bản cam kết của các thành viên hộ gia đình có chung quyền sử dụng đất","Vbck_ChungThuc":"chứng thực chữ ký, điểm chỉ ngày 05/03/2026 tại Văn phòng Công chứng X, tỉnh Bắc Ninh","Vbck_ThanhVien":[{"danhXung":"Ông","hoTen":"Nguyễn Văn An","ngaySinh":"01/02/1970","soDinhDanh":"027070001234","thuongTru":"Thôn Đông, phường Tân Hồng, tỉnh Bắc Ninh"},{"danhXung":"Bà","hoTen":"Trần Thị Bình","ngaySinh":"03/04/1972","soDinhDanh":"027172005678","thuongTru":"Thôn Đông, phường Tân Hồng, tỉnh Bắc Ninh"}],"Vbck_TranhChap":"Không có bất cứ tranh chấp khiếu nại, khiếu kiện gì"}}
```"""

# purpose="authorized_person": chỉ nhân thân MỘT người = chủ hồ sơ (bên ủy quyền) → khối doiTuongKhac*.
RULES_UYQUYEN = """Trích NHÂN THÂN của CHỦ HỒ SƠ (người sử dụng đất đứng Đơn) để điền khối "Thông tin trong trường hợp
được ủy quyền" — tài khoản đang nộp là người ĐƯỢC ủy quyền (nộp thay), cổng hỏi thông tin người đã ủy quyền cho họ. Đầu
vào: Đơn đăng ký biến động (Mẫu số 18 / Mẫu số 24), CCCD, Giấy chứng nhận, giấy tờ chứng minh thay đổi thông tin, Văn bản
cam kết của các thành viên hộ gia đình; có thể có Giấy/Văn bản ủy quyền.

CHỌN ĐÚNG NGƯỜI:
- Có Giấy ủy quyền ("BÊN ỦY QUYỀN (bên A)" / "BÊN ĐƯỢC ỦY QUYỀN (bên B)"): LẤY BÊN ỦY QUYỀN (bên A) — nhiều người thì
  người đứng đầu.
- ⚠ TUYỆT ĐỐI KHÔNG lấy bên ĐƯỢC ủy quyền (bên B, người đi nộp thay) — người đó KHÔNG lên field nào.
- Không có giấy ủy quyền: lấy người THỨ NHẤT đứng Đơn (dòng "- Tên" đầu tiên Mẫu 18 / "1.1. Tên Ông/Bà" Mẫu 24) và CCCD
  của chính người đó. Ngày sinh / ngày cấp / nơi cấp CCCD có thể lấy ở Văn bản cam kết hoặc lời chứng thực ghi rõ cho
  ĐÚNG người đó (khớp họ tên + số CCCD).
- Thông tin HIỆN TẠI: số CCCD mới / tên mới theo CCCD và Đơn; số CMND cũ, tên cũ in trên Giấy chứng nhận KHÔNG dùng.

Họ tên viết hoa chữ đầu, không kèm "Ông/Bà". Số CCCD chỉ chữ số. Ngày dd/mm/yyyy.
ChuHoSo_ThuongTru là OBJECT {quocGia,tinh,xa,chiTietDuoiXa} theo TÊN HÀNH CHÍNH HIỆN HÀNH. Giấy tờ ghi địa giới cũ kèm
"(nay thuộc phường Y, tỉnh Z)" / "(nay là …)" thì lấy tỉnh/phường "nay"; chiTietDuoiXa = thôn/tổ dân phố/khu dân cư
cũ còn ghi (vd "Thôn X - huyện cũ (nay thuộc phường Y, tỉnh Bắc Ninh)" → tinh "Bắc Ninh", xa "Phường Y",
chiTietDuoiXa "Thôn X"). Đơn ghi địa giới mới, CCCD / Giấy chứng nhận ghi địa giới cũ → theo Đơn.
ChuHoSo_GioiTinh chỉ điền khi giấy tờ ghi rõ giới tính hoặc danh xưng riêng "Ông"/"Bà" ("1.1. Tên Ông:" → "Nam"); dòng in
sẵn "Ông, bà:" → BỎ.

⚠ KHÔNG BỊA: chỉ trích field giấy tờ ghi RÕ; không có/không chắc → bỏ field.
KHÔNG trả field UI ("doiTuongKhac...", "element_..."); chỉ trả field nguồn trong schema."""

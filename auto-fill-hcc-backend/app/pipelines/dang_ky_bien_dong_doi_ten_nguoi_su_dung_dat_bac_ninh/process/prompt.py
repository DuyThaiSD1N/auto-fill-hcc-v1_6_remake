"""Quy tắc compact prompt cho "[Bắc Ninh] Đăng ký biến động do đổi tên / thay đổi thông tin người sử dụng đất"."""

EXTRA_RULES = """Đầu vào thường là MỘT tệp scan chung gồm: Đơn đăng ký biến động đất đai (Mẫu số 18, có thể viết tay),
Giấy chứng nhận quyền sử dụng đất đã cấp, CCCD của người đứng đơn, giấy tờ chứng minh việc thay đổi thông tin (giấy xác
nhận thông tin về cư trú, giấy xác nhận số CMND cũ, quyết định cho phép thay đổi họ tên, trích lục thay đổi hộ tịch…),
có thể kèm văn bản ủy quyền, mảnh trích đo bản đồ địa chính.

THÔNG TIN CŨ VÀ MỚI: thủ tục này đăng ký THAY ĐỔI thông tin. Giấy chứng nhận in thông tin CŨ (tên cũ, số CMND 9 số cũ,
địa chỉ cũ). Các field Cccd_* / Don_* là thông tin HIỆN TẠI của người đứng đơn — lấy từ CCCD và Đơn, KHÔNG lấy từ phần
người sử dụng đất in trên Giấy chứng nhận.

NGUỒN DỮ LIỆU:
- Cccd_HoTen/Cccd_SoDinhDanh: lấy từ CCCD nếu có; không có CCCD thì lấy từ Đơn (dòng "- Tên", "- Giấy tờ nhân
  thân/pháp nhân"). Số CCCD viết tay có dấu chấm ("0011.020.12345") → chỉ giữ chữ số.
- Cccd_NgayCap/Cccd_NoiCap CHỈ có khi upload CCCD (mặt sau) hoặc giấy tờ ghi rõ "cấp ngày …". Nơi cấp: "CỤC TRƯỞNG CỤC
  CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC
  mới ghi "BỘ CÔNG AN" → "Bộ Công an".

- QUAN TRỌNG — Don_DiaChi là NGOẠI LỆ của quy tắc địa chỉ chung (quy tắc 5): KHÔNG trả object. Don_DiaChi PHẢI là
  CHUỖI MỘT DÒNG, chép NGUYÊN VĂN dòng "- Địa chỉ" ở mục I của Đơn Mẫu 18 (đúng như người dân viết, kể cả địa giới
  cũ), GIỮ ĐỦ thôn/tổ dân phố + phường/xã + tỉnh. KHÔNG lấy địa chỉ từ CCCD hay Giấy chứng nhận cho field này.

- Don_KinhGui lấy từ dòng "Kính gửi:" đầu Đơn Mẫu 18; bỏ ký hiệu chú thích "(1)". Bỏ field nếu đơn không ghi.
- Don_NoiDungBienDong CHỈ lấy từ mục "II. Nội dung biến động" của Đơn Mẫu 18, NGUYÊN VĂN, GIỮ từng dòng gạch đầu dòng
  (nối các dòng bằng "\\n"). Với thủ tục này thường là "- Thay đổi số CMND … thành số CCCD …", "- Đổi tên từ … thành …",
  "- Thay đổi địa chỉ …", "- Thay đổi số hiệu thửa đất …", "- Giảm diện tích do sạt lở tự nhiên …". Mục trống → BỎ field.
- Gcn_SoVaoSo / Gcn_SoPhatHanh: thông tin GIẤY CHỨNG NHẬN ĐÃ CẤP, đọc ở chính Giấy chứng nhận (dòng "Số vào sổ cấp
  GCN", số seri in ở trang 1 dạng "CĐ 123456") hoặc ở Đơn. Chép đúng ký tự, không suy luận. Không có → bỏ.
- Don_DienThoai lấy từ Đơn (dòng "Điện thoại liên hệ"); chỉ chữ số.
- Don_GiayTo2/Don_GiayTo3: CHỈ lấy dòng "(2) …" / "(3) …" ở mục IV của Đơn. Dòng trống/chỉ có dấu chấm → BỎ, KHÔNG
  tự liệt kê các giấy tờ khác trong tệp. KHÔNG lấy dòng in sẵn "(1) Giấy chứng nhận đã cấp".
- Don_MaSoThue/Don_Email/Don_MienGiam/Don_ThanhVienHo/Don_TranhChap/Don_RanhGioi: CHỈ chép khi Đơn GHI RÕ nội dung ở
  đúng dòng đó. Dòng trống hoặc chỉ có dấu chấm "...." → BỎ field, không suy luận.

KHÔNG trả field UI dạng "- Tên", "nhanTaiNha...", element_...; chỉ trả field nguồn trong schema. Không bịa thông tin
còn thiếu; ô/tài liệu không có thì bỏ field.

Ví dụ output ĐÚNG (Don_DiaChi là chuỗi có phường/xã; Don_NoiDungBienDong giữ xuống dòng):
```json
{"fields":{"Cccd_HoTen":"Nguyễn Văn An","Cccd_SoDinhDanh":"027090001234","Cccd_NgayCap":"10/05/2022","Cccd_NoiCap":"Cục Cảnh sát quản lý hành chính về trật tự xã hội","Don_KinhGui":"Văn phòng đăng ký đất đai tỉnh Bắc Ninh","Don_DiaChi":"Thôn Đông, phường Tân Hồng, tỉnh Bắc Ninh","Don_DienThoai":"0912345678","Don_NoiDungBienDong":"- Thay đổi số CMND 125123456 thành số CCCD 027090001234","Gcn_SoVaoSo":"CS01234/T05/Q02","Gcn_SoPhatHanh":"CĐ 123456"}}
```"""

# purpose="authorized_person": chỉ nhân thân MỘT người = chủ hồ sơ (bên ủy quyền) → khối doiTuongKhac*.
RULES_UYQUYEN = """Trích NHÂN THÂN của CHỦ HỒ SƠ (người sử dụng đất đứng Đơn Mẫu 18) để điền khối "Thông tin trong
trường hợp được ủy quyền" — tài khoản đang nộp là người ĐƯỢC ủy quyền (nộp thay), cổng hỏi thông tin người đã ủy quyền
cho họ. Đầu vào: Đơn đăng ký biến động (Mẫu số 18), CCCD, Giấy chứng nhận, giấy tờ chứng minh thay đổi thông tin; có thể
có Giấy/Văn bản ủy quyền.

CHỌN ĐÚNG NGƯỜI:
- Có Giấy ủy quyền ("BÊN ỦY QUYỀN (bên A)" / "BÊN ĐƯỢC ỦY QUYỀN (bên B)"): LẤY BÊN ỦY QUYỀN (bên A).
- ⚠ TUYỆT ĐỐI KHÔNG lấy bên ĐƯỢC ủy quyền (bên B, người đi nộp thay) — người đó KHÔNG lên field nào.
- Không có giấy ủy quyền: lấy người đứng Đơn Mẫu 18 (dòng "- Tên") và CCCD của chính người đó.
- Thông tin HIỆN TẠI: số CCCD mới / tên mới theo CCCD và Đơn; số CMND cũ, tên cũ in trên Giấy chứng nhận KHÔNG dùng.

Họ tên viết hoa chữ đầu, không kèm "Ông/Bà". Số CCCD chỉ chữ số. Ngày dd/mm/yyyy.
ChuHoSo_ThuongTru là OBJECT {quocGia,tinh,xa,chiTietDuoiXa} theo TÊN HÀNH CHÍNH HIỆN HÀNH. Giấy tờ ghi địa giới cũ kèm
"(nay thuộc phường Y, tỉnh Z)" / "(nay là …)" thì lấy tỉnh/phường "nay"; chiTietDuoiXa = thôn/tổ dân phố/khu dân cư
cũ còn ghi (vd "Thôn X - huyện cũ (nay thuộc phường Y, tỉnh Bắc Ninh)" → tinh "Bắc Ninh", xa "Phường Y",
chiTietDuoiXa "Thôn X").
ChuHoSo_GioiTinh chỉ điền khi giấy tờ ghi rõ giới tính hoặc danh xưng riêng "Ông"/"Bà"; dòng in sẵn "Ông, bà:" → BỎ.

⚠ KHÔNG BỊA: chỉ trích field giấy tờ ghi RÕ; không có/không chắc → bỏ field.
KHÔNG trả field UI ("doiTuongKhac...", "element_..."); chỉ trả field nguồn trong schema."""

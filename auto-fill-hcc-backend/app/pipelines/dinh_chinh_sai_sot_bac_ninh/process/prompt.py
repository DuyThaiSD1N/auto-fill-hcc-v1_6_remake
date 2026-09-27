"""Quy tắc compact prompt cho "[Bắc Ninh] Đính chính GCN đã cấp lần đầu có sai sót"."""

EXTRA_RULES = """Đầu vào thường gồm: CCCD/CMND của người nộp hồ sơ (người đứng đơn),
Đơn đăng ký biến động đất đai (Mẫu số 18), và có thể có Giấy chứng nhận QSDĐ (bản gốc).

NGUỒN DỮ LIỆU:
- Cccd_HoTen/Cccd_SoDinhDanh: lấy từ CCCD nếu có; nếu không có CCCD thì lấy từ Đơn (dòng "a) Tên"/
  "- Tên" và dòng "CCCD số"/"Căn cước số"). Cccd_HoTen CHỈ là họ tên (viết hoa chữ đầu), không kèm
  "Ông/Bà", năm sinh hay phần trong ngoặc.
- Cccd_NgayCap/Cccd_NoiCap CHỈ có khi upload CCCD (mặt sau). Không có CCCD thì BỎ 2 field này.
  Nơi cấp: "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản lý
  hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → "Bộ Công an".

- QUAN TRỌNG — Don_DiaChi là NGOẠI LỆ của quy tắc địa chỉ chung (quy tắc 5): KHÔNG trả object.
  Don_DiaChi PHẢI là CHUỖI (string) MỘT DÒNG, chép NGUYÊN VĂN dòng "c) Địa chỉ"/"- Địa chỉ" của Đơn
  Mẫu 18, GIỮ ĐỦ tổ dân phố/thôn + phường/xã + tỉnh. Ví dụ đọc được "- Địa chỉ: TDP X, phường Y –
  tỉnh Bắc Ninh." → trả Don_DiaChi = "TDP X, phường Y, tỉnh Bắc Ninh".
  TUYỆT ĐỐI KHÔNG bỏ phường/xã ra khỏi Don_DiaChi.

- Don_KinhGui lấy từ dòng "Kính gửi:" đầu Đơn (vd "UBND phường Song Liễu, tỉnh Bắc Ninh"); bỏ ký
  hiệu chú thích "(1)" ở cuối. Bỏ field nếu đơn không ghi.
- Don_Ten/Don_GiayToNhanThan: chép NGUYÊN VĂN dòng "Tên"/"Giấy tờ nhân thân" của Đơn (giữ cả năm sinh,
  tư cách đại diện trong ngoặc). Dòng trống/chỉ "...." → bỏ.
- Don_NoiDungBienDong CHỈ lấy từ mục "2."/"II. Nội dung biến động" của Đơn Mẫu số 18, NGUYÊN VĂN. Nếu
  không có Đơn hoặc mục này trống thì BỎ field.
- Don_DienThoai lấy từ Đơn (mục d) nếu có; chỉ chữ số.
- Don_GiayTo2/Don_GiayTo3: giấy tờ nộp kèm thứ 2 và thứ 3 trong danh sách giấy tờ liên quan của Đơn,
  THEO THỨ TỰ DÒNG, bất kể đơn đánh số (2)(3) hay (4)(5). Còn dòng nữa thì ghép vào Don_GiayTo3, ngăn "; ".
  KHÔNG lấy dòng "(1) Giấy chứng nhận đã cấp …" (dòng in sẵn của mẫu).
- Don_MaSoThue/Don_Email/Don_MienGiam/Don_ThanhVienHo/Don_TranhChap/Don_RanhGioi: CHỈ chép khi Đơn GHI
  RÕ nội dung ở đúng dòng đó. Dòng trống hoặc chỉ có dấu chấm "...." → BỎ field, không suy luận.

KHÔNG trả field UI dạng "a) Tên", "b) Giấy tờ...", "nhanTaiNha...", element_...; chỉ trả field nguồn trong schema.
Không bịa thông tin còn thiếu; ô/tài liệu không có thì bỏ field.

Ví dụ output ĐÚNG (chú ý Don_DiaChi là chuỗi có phường/xã):
```json
{"fields":{"Cccd_HoTen":"Nguyễn Văn A","Cccd_SoDinhDanh":"001090001234","Don_KinhGui":"UBND xã Y, tỉnh Bắc Ninh","Don_Ten":"Ông NGUYỄN VĂN A, sinh năm 1980 (là người đại diện hộ gia đình)","Don_GiayToNhanThan":"Căn cước số 001090001234","Don_DiaChi":"Thôn X, xã Y, tỉnh Bắc Ninh","Don_NoiDungBienDong":"Đính chính mục đích sử dụng đất","Don_GiayTo2":"CCCD bản photo","Don_GiayTo3":"Sơ đồ thửa đất","Don_TranhChap":"Không có tranh chấp"}}
```"""

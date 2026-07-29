"""Quy tắc compact prompt cho "[Bắc Ninh] Đính chính giấy chứng nhận đã cấp"."""

EXTRA_RULES = """Đầu vào thường gồm: CCCD/CMND của người nộp hồ sơ (người sử dụng đất đứng đơn),
Đơn đăng ký biến động đất đai (Mẫu số 18), và Bản gốc Giấy chứng nhận QSDĐ đã cấp.

NGUỒN DỮ LIỆU:
- Cccd_HoTen/Cccd_SoDinhDanh: lấy từ CCCD nếu có; nếu không có CCCD thì lấy từ Đơn (mục a) Tên và
  dòng "CCCD số: ..."). Ghi họ tên như trên Giấy chứng nhận đã cấp.
- Cccd_NgayCap/Cccd_NoiCap CHỈ có khi upload CCCD (mặt sau). Không có CCCD thì BỎ 2 field này.
  Nơi cấp: "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản lý
  hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → "Bộ Công an".

- QUAN TRỌNG — Don_DiaChi là NGOẠI LỆ của quy tắc địa chỉ chung (quy tắc 5): KHÔNG trả object.
  Don_DiaChi PHẢI là CHUỖI (string) MỘT DÒNG, chép NGUYÊN VĂN dòng "c) Địa chỉ" của Đơn Mẫu 18,
  GIỮ ĐỦ tổ dân phố/thôn + phường/xã + tỉnh. Ví dụ "c) Địa chỉ: Bản Nậm Dòn, xã Nậm Hàng, tỉnh Lai
  Châu" → Don_DiaChi = "Bản Nậm Dòn, xã Nậm Hàng, tỉnh Lai Châu". TUYỆT ĐỐI KHÔNG bỏ phường/xã.

- Don_KinhGui lấy từ dòng "Kính gửi:" đầu Đơn (vd "Chi nhánh Văn phòng ĐKĐĐ ..."); bỏ ký hiệu chú
  thích "(1)" ở cuối. Bỏ field nếu đơn không ghi.
- Don_NoiDungBienDong CHỈ lấy từ mục 2 "Nội dung biến động" của Đơn Mẫu số 18, NGUYÊN VĂN — với thủ
  tục này thường là đính chính thông tin trên GCN (vd "Đính chính diện tích/số thửa/họ tên..."). Nếu
  mục này trống thì BỎ field.
- Don_DienThoai lấy từ Đơn (mục d) nếu có; chỉ chữ số.
- Don_GiayTo2/Don_GiayTo3: lấy từ mục 3 Đơn "(2) ..." và "(3) ...". Bỏ nếu trống. KHÔNG lấy dòng
  "(1) Giấy chứng nhận đã cấp" (dòng in sẵn của mẫu).

KHÔNG trả field UI dạng "a) Tên", "b) Giấy tờ...", "nhanTaiNha...", element_...; chỉ trả field nguồn
trong schema. Không bịa thông tin còn thiếu; ô/tài liệu không có thì bỏ field.

Ví dụ output ĐÚNG (chú ý Don_DiaChi là chuỗi có phường/xã):
```json
{"fields":{"Cccd_HoTen":"Nguyễn Văn A","Cccd_SoDinhDanh":"035090001234","Cccd_NgayCap":"03/06/2022","Cccd_NoiCap":"Cục Cảnh sát quản lý hành chính về trật tự xã hội","Don_KinhGui":"Chi nhánh Văn phòng đăng ký đất đai liên xã Yên Phong","Don_DiaChi":"Thôn ..., xã ..., tỉnh Bắc Ninh","Don_DienThoai":"0912345678","Don_NoiDungBienDong":"Đính chính thông tin trên Giấy chứng nhận đã cấp"}}
```"""

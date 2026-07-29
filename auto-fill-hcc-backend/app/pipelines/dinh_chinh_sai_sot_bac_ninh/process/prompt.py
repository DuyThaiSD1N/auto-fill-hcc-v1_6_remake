"""Quy tắc compact prompt cho "[Bắc Ninh] Đính chính GCN đã cấp lần đầu có sai sót"."""

EXTRA_RULES = """Đầu vào thường gồm: CCCD/CMND của người nộp hồ sơ (người đứng đơn),
Đơn đăng ký biến động đất đai (Mẫu số 18), và có thể có Giấy chứng nhận QSDĐ (bản gốc).

NGUỒN DỮ LIỆU:
- Cccd_HoTen/Cccd_SoDinhDanh: lấy từ CCCD nếu có; nếu không có CCCD thì lấy từ Đơn (mục a) Tên và
  dòng "CCCD số: ..." trong phần người có quyền lợi liên quan).
- Cccd_NgayCap/Cccd_NoiCap CHỈ có khi upload CCCD (mặt sau). Không có CCCD thì BỎ 2 field này.
  Nơi cấp: "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản lý
  hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → "Bộ Công an".

- QUAN TRỌNG — Don_DiaChi là NGOẠI LỆ của quy tắc địa chỉ chung (quy tắc 5): KHÔNG trả object.
  Don_DiaChi PHẢI là CHUỖI (string) MỘT DÒNG, chép NGUYÊN VĂN dòng "c) Địa chỉ" của Đơn Mẫu 18,
  GIỮ ĐỦ tổ dân phố/thôn + phường/xã + tỉnh. Ví dụ đọc được "c) Địa chỉ: TDP Bùi Xá, phường Song
  Liễu – tỉnh Bắc Ninh." → trả Don_DiaChi = "TDP Bùi Xá, phường Song Liễu, tỉnh Bắc Ninh".
  TUYỆT ĐỐI KHÔNG bỏ phường/xã ra khỏi Don_DiaChi.

- Don_KinhGui lấy từ dòng "Kính gửi:" đầu Đơn (vd "UBND phường Song Liễu, tỉnh Bắc Ninh"); bỏ ký
  hiệu chú thích "(1)" ở cuối. Bỏ field nếu đơn không ghi.
- Don_NoiDungBienDong CHỈ lấy từ mục 2 "Nội dung biến động" của Đơn Mẫu số 18, NGUYÊN VĂN. Nếu
  không có Đơn hoặc mục này trống thì BỎ field.
- Don_DienThoai lấy từ Đơn (mục d) nếu có; chỉ chữ số.
- Don_GiayTo2/Don_GiayTo3: lấy từ mục 3 Đơn "(2) ..." và "(3) ..." (vd "(2) CCCD"). Bỏ nếu trống.
  KHÔNG lấy dòng "(1) Giấy chứng nhận đã cấp" (dòng in sẵn của mẫu).

KHÔNG trả field UI dạng "a) Tên", "b) Giấy tờ...", element_...; chỉ trả field nguồn trong schema.
Không bịa thông tin còn thiếu; ô/tài liệu không có thì bỏ field.

Ví dụ output ĐÚNG (chú ý Don_DiaChi là chuỗi có phường/xã):
```json
{"fields":{"Cccd_HoTen":"Nguyễn Tiến Định","Cccd_SoDinhDanh":"027066000695","Don_DiaChi":"TDP Bùi Xá, phường Song Liễu, tỉnh Bắc Ninh","Don_DienThoai":"0947874091","Don_NoiDungBienDong":"Đính chính mục đích sử dụng đất","Don_GiayTo2":"CCCD"}}
```"""

"""Quy tắc compact prompt cho "[Bắc Ninh] Thu hồi GCN cấp sai & cấp lại"."""

EXTRA_RULES = """Đầu vào gồm: CCCD chủ hồ sơ (người kiến nghị), Giấy chứng nhận QSDĐ (sổ đỏ) đang
xin thu hồi, và Biên bản họp gia đình (đóng vai trò văn bản kiến nghị thu hồi). Có thể có hợp đồng
ủy quyền — chỉ trích thông tin CHỦ HỒ SƠ (người sử dụng đất), KHÔNG lấy người được ủy quyền.

QUAN TRỌNG VỀ DẤU TIẾNG VIỆT: GCN/sổ đỏ scan CŨ thường OCR SAI DẤU tên người (vd "Nguyễn Kim Anh"
thay vì "Nguyễn Kim Ánh", "Huyền" thay vì "Huệ"). Khi một tên xuất hiện ở nhiều nguồn, ƯU TIÊN nguồn
có DẤU CHUẨN theo thứ tự: CCCD > Biên bản họp gia đình > GCN. KHÔNG chép tên từ GCN cũ nếu sai dấu.

NGUỒN & CÁCH LẤY:
- Cccd_HoTen: họ tên chủ hồ sơ, ưu tiên CCCD rồi Biên bản họp gia đình (dấu chuẩn); KHÔNG lấy từ GCN cũ.
- Cccd_SoDinhDanh/NgayCap/NoiCap từ CCCD chủ hồ sơ (hoặc dòng "CCCD số …" trên đơn/biên bản/ủy quyền).
- TenChuSuDungDat: tên chủ sử dụng đất cho ô "a) Tên", dạng "Hộ ông …"/"Hộ bà …". ƯU TIÊN lấy từ Biên
  bản họp gia đình — cụm "chủ sử dụng đất, hộ ông/bà: <tên>" (vd "Hộ ông Nguyễn Kim Ánh") — hoặc CCCD;
  KHÔNG lấy tên từ GCN cũ nếu sai dấu. Chỉ giữ "Hộ ông/bà" nếu tài liệu nêu rõ, không thì trả họ tên chuẩn.
- Don_KinhGui: cơ quan nhận đơn — dòng "Kính gửi:" hoặc cụm "đề nghị UBND phường … thu hồi" trong biên bản.
- QUAN TRỌNG — NGOẠI LỆ quy tắc địa chỉ chung (quy tắc 5): Don_DiaChi PHẢI là CHUỖI (string) một dòng,
  giữ ĐỦ tổ dân phố/thôn + phường/xã + tỉnh. KHÔNG trả object, KHÔNG bỏ phường/xã.

KHÔNG trả field UI ("element_...", "a) Tên", "nhanTaiNha..."); chỉ trả field nguồn trong schema.
Không bịa; thiếu thì bỏ field.

Ví dụ output ĐÚNG:
```json
{"fields":{"Cccd_HoTen":"Nguyễn Kim Ánh","Cccd_SoDinhDanh":"027070010408","TenChuSuDungDat":"Hộ ông Nguyễn Kim Ánh","Don_KinhGui":"UBND phường Song Liễu","Don_DiaChi":"Tổ dân phố Tứ Cờ, phường Song Liễu, tỉnh Bắc Ninh"}}
```"""

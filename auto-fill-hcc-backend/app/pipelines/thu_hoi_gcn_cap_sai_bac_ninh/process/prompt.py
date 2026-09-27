"""Quy tắc compact prompt cho "[Bắc Ninh] Thu hồi GCN cấp sai & cấp lại"."""

EXTRA_RULES = """Đầu vào gồm: CCCD chủ hồ sơ (người kiến nghị), Giấy chứng nhận QSDĐ (sổ đỏ) đang
xin thu hồi, và Biên bản họp gia đình (đóng vai trò văn bản kiến nghị thu hồi). Có thể có hợp đồng
ủy quyền — chỉ trích thông tin CHỦ HỒ SƠ (người sử dụng đất), KHÔNG lấy người được ủy quyền.

QUAN TRỌNG VỀ DẤU TIẾNG VIỆT: GCN/sổ đỏ scan CŨ thường OCR SAI DẤU tên người (vd "Nguyễn Văn Anh"
thay vì "Nguyễn Văn Ánh"). Khi một tên xuất hiện ở nhiều nguồn, ƯU TIÊN nguồn có DẤU CHUẨN theo thứ
tự: CCCD > Biên bản họp gia đình > GCN. KHÔNG chép tên từ GCN cũ nếu sai dấu.

NGUỒN & CÁCH LẤY:
- Cccd_HoTen: họ tên chủ hồ sơ, ưu tiên CCCD rồi Biên bản họp gia đình (dấu chuẩn); KHÔNG lấy từ GCN cũ.
- Cccd_SoDinhDanh/NgayCap/NoiCap từ CCCD chủ hồ sơ (hoặc dòng "CCCD số …" trên đơn/biên bản/ủy quyền).
- TenChuSuDungDat: tên chủ sử dụng đất cho ô "a) Họ và tên", dạng "Hộ ông …"/"Hộ bà …". ƯU TIÊN lấy từ
  Biên bản họp gia đình — cụm "chủ sử dụng đất, hộ ông/bà: <tên>" — hoặc CCCD; KHÔNG lấy tên từ GCN cũ
  nếu sai dấu. Chỉ giữ "Hộ ông/bà" nếu tài liệu nêu rõ, không thì trả họ tên chuẩn.
- Don_KinhGui: cơ quan nhận đơn — dòng "Kính gửi:" hoặc cụm "đề nghị UBND phường … thu hồi" trong biên bản.
- QUAN TRỌNG — NGOẠI LỆ quy tắc địa chỉ chung (quy tắc 5): Don_DiaChi và Dat_DiaChi PHẢI là CHUỖI
  (string) một dòng, giữ ĐỦ tổ dân phố/thôn + phường/xã + tỉnh. KHÔNG trả object, KHÔNG bỏ phường/xã.

THÔNG TIN THỬA ĐẤT (Dat_*, Gcn_SoPhatHanh):
- ƯU TIÊN văn bản kiến nghị/Biên bản họp gia đình (văn bản đánh máy, thường chép lại "thông tin thửa đất:
  Số sổ …, thửa đất số …, tờ bản đồ số …, diện tích …, mục đích sử dụng …, thời hạn sử dụng …"). Chỉ khi
  văn bản kiến nghị KHÔNG ghi mới lấy từ bảng trên GCN (GCN scan cũ hay OCR sai số).
- Dat_DiaChi: nếu ghi cả địa danh cũ và "(Nay là …)" thì lấy địa danh MỚI sau "Nay là".
- Dat_SuDungChung/Dat_SuDungRieng/Dat_TuThoiDiem/Dat_NguonGoc: CHỈ trả khi tài liệu ghi rõ; không suy luận.
- Gcn_SoPhatHanh: số seri GCN (vd "K 708004" ở dòng "Số sổ …" hoặc "Số K…"), KHÔNG phải số vào sổ.
- Don_VanBanKienNghi: tên loại văn bản kiến nghị theo tiêu đề tài liệu (vd "Biên bản họp gia đình").

KHÔNG trả field UI ("element_...", "a) Họ và tên", "nhanTaiNha..."); chỉ trả field nguồn trong schema.
Không bịa; thiếu thì bỏ field.

Ví dụ output ĐÚNG:
```json
{"fields":{"Cccd_HoTen":"Nguyễn Văn A","Cccd_SoDinhDanh":"001090001234","TenChuSuDungDat":"Hộ ông Nguyễn Văn A","Don_KinhGui":"UBND phường X","Don_DiaChi":"Tổ dân phố Y, phường X, tỉnh Bắc Ninh","Dat_ThuaSo":"120","Dat_ToBanDo":"5","Dat_DiaChi":"Tổ dân phố Y, phường X, tỉnh Bắc Ninh","Dat_DienTich":"150,0 m²","Dat_MucDich":"Đất ở","Dat_ThoiHan":"Lâu dài","Gcn_SoPhatHanh":"AB 123456","Don_VanBanKienNghi":"Biên bản họp gia đình"}}
```"""

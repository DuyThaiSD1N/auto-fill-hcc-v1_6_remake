"""Quy tắc compact prompt cho "Cấp trích lục hoặc sao hồ sơ người có công với cách mạng" (1.010828)."""

EXTRA_RULES = """<critical_rules>
1. NGƯỜI LÀM ĐƠN (người có công hoặc thân nhân đề nghị cấp trích lục/sao hồ sơ) là chủ hồ sơ. Đơn đề nghị và CCCD
   của người này gộp thông tin, không tách thành nhiều người.
2. Đơn đề nghị chỉ trả Don_*. CCCD của người làm đơn (cùng họ tên/số định danh với Đơn) chỉ trả Person1_*. CCCD của
   người KHÁC KHÔNG BAO GIỜ vào Person1_*.
   NguoiNop_* chỉ trích khi khối <nguoi_nop_context> ở cuối chỉ ra giấy tờ của NGƯỜI NỘP (người đăng nhập, nộp
   thay) và người đó KHÁC người làm đơn; khi đó lấy NguoiNop_* từ CHÍNH giấy tờ ấy. Không có khối đó, khối báo
   không trả NguoiNop_*, hoặc người nộp chính là người làm đơn → bỏ trống NguoiNop_*.
3. Người có công gốc (liệt sĩ, thương binh…) chỉ được nêu tên trong nội dung đơn — KHÔNG lấy làm người làm đơn.
4. Không trả field UI dạng data[...]; chỉ trả field nguồn trong schema. Ô trống/không đọc chắc thì bỏ field, không
   bịa, không đoán chữ số.
</critical_rules>

<document_classification>
1. Đơn đề nghị: có "ĐƠN ĐỀ NGHỊ" + "Người làm đơn"; có thể là đơn cấp trích lục/sao hồ sơ người có công hoặc đơn
   "Di chuyển hồ sơ …" (Mẫu số 27) — đều là Đơn.
2. CCCD: "CĂN CƯỚC"/"CĂN CƯỚC CÔNG DÂN"/"Identity Card"/"Số định danh cá nhân", có vùng MRZ "IDVNM…".
</document_classification>

<don_rules>
1. Don_TieuDe chép NGUYÊN VĂN tiêu đề đơn = chữ "ĐƠN ĐỀ NGHỊ" + 1-2 dòng ngay dưới (gồm phần viết tay điền vào
   chỗ trống), vd "ĐƠN ĐỀ NGHỊ Di chuyển hồ sơ trợ cấp một lần", "ĐƠN ĐỀ NGHỊ cấp trích lục hồ sơ người có công".
   KHÔNG lấy câu "Tôi đề nghị …" trong thân đơn.
2. Ngày cấp và nơi cấp lấy từ dòng "Ngày cấp", "Nơi cấp" của Đơn; nơi cấp chép nguyên văn.
3. Don_NoiThuongTru là object {quocGia,tinh,xa,chiTietDuoiXa}: chiTietDuoiXa chỉ số nhà/đường/thôn/tổ, KHÔNG lặp
   xã/tỉnh; đơn không ghi tỉnh thì để tinh rỗng. Không lấy "Quê quán" vào nơi thường trú.
</don_rules>

<cccd_rules>
1. Person1_NoiCuTru lấy dòng "Nơi cư trú"/"Nơi thường trú" (mặt sau thẻ), KHÔNG lấy "Nơi đăng ký khai sinh"/
   "Quê quán". Thẻ ghi "12 Đường Mẫu, Mẫu Hòa, Khánh Hòa" → {"tinh":"Khánh Hòa","xa":"Mẫu Hòa","chiTietDuoiXa":
   "12 Đường Mẫu"}.
2. Person1_NoiCap: thẻ "CĂN CƯỚC" mẫu mới in "BỘ CÔNG AN" → "Bộ Công an"; thẻ CCCD gắn chip in "CỤC TRƯỞNG CỤC
   CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội".
3. Person1_NgayCap là "Ngày, tháng, năm cấp / Date of issue"; KHÔNG lấy ngày sinh hay ngày hết hạn.
</cccd_rules>

<output_examples>
Đúng:
{"fields":{"Don_TieuDe":"ĐƠN ĐỀ NGHỊ cấp trích lục hồ sơ người có công","Don_HoTen":"Trần Văn Mẫu","Don_DienThoai":"0912000111","Person1_HoTen":"TRẦN VĂN MẪU","Person1_SoDinhDanh":"001064000111","Person1_NoiCap":"Bộ Công an","Person1_NoiCuTru":{"quocGia":"Việt Nam","tinh":"Tỉnh Mẫu","xa":"Phường Mẫu","chiTietDuoiXa":"12 Đường Mẫu"}}}

Sai:
{"fields":{"data[fullname]":"TRẦN VĂN MẪU","Person1_NoiCuTru":{"tinh":"Tỉnh Mẫu","xa":"Phường Mẫu","chiTietDuoiXa":"12 Đường Mẫu, Phường Mẫu, Tỉnh Mẫu"}}}
Lý do sai: trả field UI data[...]; chiTietDuoiXa lặp phường/tỉnh.
</output_examples>"""

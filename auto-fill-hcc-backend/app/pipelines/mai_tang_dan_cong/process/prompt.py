"""Procedure-specific compact prompt rules cho mai táng phí dân công hỏa tuyến."""

EXTRA_RULES = """Thủ tục: Giải quyết chế độ mai táng phí đối với dân công hỏa tuyến (QĐ 49/2015/QĐ-TTg).
Đầu vào: Bản khai của thân nhân (Mẫu 02-MTP), thẻ CCCD của người đứng khai, có thể có thẻ CCCD của người
nộp thay, Biên bản đồng thuận (Mẫu 80A), Trích lục khai tử, Quyết định trợ cấp một lần. Hồ sơ có thể là
PDF gộp nhiều giấy tờ.

TRÍCH HAI VAI (bạn KHÔNG quyết định ai là người nộp trên cổng — mapper sẽ xác minh bằng tài khoản UI):

1) CHỦ HỒ SƠ (ChuHoSo_*) = người ĐỨNG KHAI nhận trợ cấp, ghi ở MỤC 1 "Phần khai về thân nhân (người
   đứng khai nhận trợ cấp)" của Bản khai Mẫu 02-MTP. Lấy: HoTen, NgaySinh, SoDinhDanh, NgayCap, NoiCap,
   ThuongTru, DienThoai, QuanHeNguoiTuTran — ĐÚNG TỪ MỤC 1; bổ sung GioiTinh từ thẻ CCCD của chính họ.

2) NGƯỜI NỘP (NguoiNop_*) = NHÂN THÂN LẤY TỪ THẺ CCCD CỦA NGƯỜI KHÁC người đứng khai. QUY TẮC RÕ RÀNG:
   - Nếu hồ sơ có MỘT thẻ CCCD mà HỌ TÊN và SỐ ĐỊNH DANH KHÁC người đứng khai ở mục 1 → BẮT BUỘC trích
     TRỌN nhân thân người đó vào NguoiNop_* (HoTen, NgaySinh, GioiTinh, SoDinhDanh, NgayCap, NoiCap,
     ThuongTru). Đây là người NỘP THAY. TUYỆT ĐỐI KHÔNG bỏ sót thẻ CCCD thứ hai này.
   - CHỈ bỏ trống NguoiNop_* khi TẤT CẢ thẻ CCCD trong hồ sơ đều là của chính người đứng khai (tự nộp).
   - NguoiNop_* lấy TỪ CHÍNH thẻ CCCD đó; KHÔNG lấy từ mục 1 Bản khai, KHÔNG trộn với ChuHoSo_*.

⚠ MỖI vai lấy nhân thân TỪ ĐÚNG MỘT nguồn/thẻ, KHÔNG trộn dữ liệu (không lấy ngày sinh/nơi thường trú của
người này gán cho người kia). NgayCap/NoiCap ở mặt sau đúng thẻ của cùng người.

⚠ LOẠI TRỪ, KHÔNG lấy làm ChuHoSo_/NguoiNop_:
- NGƯỜI TỪ TRẦN (mục 2 Bản khai / Trích lục khai tử / Quyết định trợ cấp — người đã mất): họ tên người
  chết, ngày chết, nguyên quán, số trích lục, số quyết định.
- Cán bộ ký (Chủ tịch/Phó Chủ tịch UBND, người ký trích lục), và các tên trong BẢNG Biên bản 80A (đó là
  tên trong văn bản, KHÔNG phải thẻ CCCD vật lý). NguoiNop_* chỉ lấy từ ẢNH/MẶT THẺ CCCD thật.

CCCD: NgayCap ở mặt sau gần nhãn "Ngày, tháng, năm / Date, month, year". NoiCap chuẩn hóa "Cục Cảnh sát
quản lý hành chính về trật tự xã hội" / "Bộ Công an".

ĐỊA CHỈ (ThuongTru) object {"quocGia":"Việt Nam","tinh":"<tỉnh/thành>","xa":"<xã/phường/thị trấn>",
"diaChi":"<chi tiết trước xã>"}; bỏ cấp huyện/quận nếu có ở giữa.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa; thiếu thì bỏ field.

<output_contract>
Ví dụ đúng (người đứng khai NGUYỄN VĂN A + thẻ CCCD người nộp thay TRẦN VĂN B):
{"fields":{"ChuHoSo_HoTen":"NGUYỄN VĂN A","ChuHoSo_SoDinhDanh":"012345678901","ChuHoSo_NgaySinh":"01/01/1970","ChuHoSo_DienThoai":"0900000000","ChuHoSo_QuanHeNguoiTuTran":"Con đẻ","ChuHoSo_ThuongTru":{"quocGia":"Việt Nam","tinh":"Bắc Ninh","xa":"Hiệp Hòa","diaChi":"Thôn số 1"},"NguoiNop_HoTen":"TRẦN VĂN B","NguoiNop_SoDinhDanh":"098765432109","NguoiNop_GioiTinh":"Nam","NguoiNop_NgaySinh":"02/02/1990","NguoiNop_NgayCap":"02/07/2021","NguoiNop_ThuongTru":{"quocGia":"Việt Nam","tinh":"Nghệ An","xa":"Quỳ Hợp","diaChi":"Xóm Long Thành"}}}
Ví dụ sai: {"fields":{"data[fullname]":"...","ChuHoSo_HoTen":"<tên người từ trần>"}} — sai vì trả field UI và lấy người từ trần.
</output_contract>"""

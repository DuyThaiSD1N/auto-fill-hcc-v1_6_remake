"""Quy tắc compact prompt cho thủ tục "Thăm viếng mộ liệt sĩ"."""

EXTRA_RULES = """<critical_rules>
1. "GIẤY GIỚI THIỆU THĂM VIẾNG MỘ LIỆT SĨ" (Mẫu 42) hoặc "Đơn đề nghị thăm viếng mộ liệt sĩ" (Mẫu 31)
   là NGUỒN CHÍNH cho ToKhai_*, ToKhai_NguoiCungDi và tên liệt sĩ.
2. CCCD/CMND chỉ dùng để trả Person1_*. Bằng "Tổ quốc ghi công" và trích lục hồ sơ liệt sĩ/giấy xác nhận
   nơi hy sinh (Mẫu 44) dùng cho LietSi_* (quê quán, cơ quan/cấp bậc, ngày/nơi hy sinh, số bằng).
3. Không trả field UI dạng data[...]; chỉ trả field nguồn trong schema.
4. Không bịa. Ô/bảng trống thì bỏ field hoặc trả mảng rỗng.
</critical_rules>

<document_classification>
1. Nhận diện Giấy giới thiệu qua cụm: "GIẤY GIỚI THIỆU THĂM VIẾNG MỘ LIỆT SĨ", "trân trọng giới thiệu",
   "Ông (bà)", "thăm viếng phần mộ liệt sĩ", "Mối quan hệ với liệt sĩ".
2. Nhận diện CCCD qua "CĂN CƯỚC CÔNG DÂN"/"Citizen Identity Card"/"Số / No.".
3. Bằng TQGC/trích lục hồ sơ liệt sĩ là nguồn thông tin liệt sĩ. Tên file chỉ là tín hiệu phụ, OCR là nguồn chính.
</document_classification>

<nguoi_khai>
1. ToKhai_HoTen lấy dòng "Ông (bà)"; ToKhai_QuanHeVoiLietSi lấy dòng "Mối quan hệ với liệt sĩ" (vd "Cháu ruột").
2. ToKhai_SoDinhDanh, ToKhai_NgayCap, ToKhai_NoiCap lấy dòng "CCCD/CMND số ... Ngày cấp ... Nơi cấp ...".
3. ToKhai_NoiThuongTru là object {quocGia,tinh,xa,diaChi} từ dòng "thường trú tại". quocGia mặc định "Việt Nam";
   tinh giữ đủ "Tỉnh ..."/"Thành phố ..."; xa giữ đủ "Xã ..."/"Phường ..."; diaChi chỉ giữ thôn/tổ/số nhà/đường.
4. ToKhai_LoaiGiayTo mặc định "CCCD" nếu giấy tờ là căn cước công dân.
</nguoi_khai>

<liet_si>
1. LietSi_HoTen là tên liệt sĩ được thăm viếng (trong cụm "thăm viếng phần mộ liệt sĩ <Tên>").
2. LietSi_QueQuan, LietSi_CoQuanDonVi, LietSi_CapBac, LietSi_NgayHySinh, LietSi_NoiHySinh, LietSi_SoBang
   lấy từ Bằng TQGC/trích lục hồ sơ liệt sĩ; Giấy giới thiệu thường KHÔNG có các thông tin này. Bỏ field nào không có nguồn.
</liet_si>

<nguoi_cung_di>
1. ToKhai_NguoiCungDi là mảng những người cùng đi thăm viếng (ngoài người khai). Mỗi item:
   hoTen, ngaySinh, soGiayTo (số CCCD/CMND), ngayCap, noiCap, moiQuanHe (quan hệ với liệt sĩ).
2. KHÔNG đưa chính người khai (người được giới thiệu ở mục đầu) vào danh sách này.
3. Không được chỉ lấy người đầu nếu có nhiều người. Giữ đúng thứ tự. Bảng trống thì bỏ field.
</nguoi_cung_di>

<cccd>
1. Person1_NgayCap lấy ở mặt sau CCCD, KHÔNG lấy ngày sinh/ngày hết hạn.
2. Person1_NoiCuTru là object {quocGia,tinh,xa,diaChi}.
</cccd>

<output_examples>
Đúng:
{"fields":{"ToKhai_HoTen":"Nguyễn Văn P","ToKhai_QuanHeVoiLietSi":"Cháu ruột","ToKhai_NoiThuongTru":{"quocGia":"Việt Nam","tinh":"Tỉnh Bắc Ninh","xa":"Phường Song Liễu","diaChi":""},"LietSi_HoTen":"Nguyễn Văn M","ToKhai_NguoiCungDi":[{"hoTen":"Nguyễn Văn B","ngaySinh":"03/02/1967","soGiayTo":"027067010265","ngayCap":"09/05/2021","moiQuanHe":"Em trai liệt sĩ"}]}}

Sai:
{"fields":{"data[fullname1]":"Nguyễn Văn M","qheLSi":"Cháu ruột"}}
Lý do sai: trả field UI data[...] thay vì field nguồn ToKhai_*/LietSi_*.
</output_examples>"""

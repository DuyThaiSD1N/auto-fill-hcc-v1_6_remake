"""Quy tắc compact prompt cho thủ tục "Hưởng trợ cấp khi người có công đang hưởng trợ cấp ưu đãi từ trần"."""

EXTRA_RULES = """<critical_rules>
1. "BẢN KHAI để giải quyết chế độ ưu đãi khi người có công từ trần" (Mẫu số 12) là NGUỒN CHÍNH.
   PHÂN BIỆT RÕ HAI NGƯỜI:
   - ToKhai_* = NGƯỜI KHAI/người nhận trợ cấp một lần (CÒN SỐNG, đứng ra kê khai — Mục 3 bản khai).
   - TuTran_* = NGƯỜI CÓ CÔNG ĐÃ TỪ TRẦN (đã mất — Mục 1 bản khai). Đây là hai người KHÁC nhau.
2. CCCD/CMND là của NGƯỜI KHAI → trả Person1_* (không phải của người từ trần). Trích lục khai tử là của
   NGƯỜI TỪ TRẦN → dùng cho TuTran_NgayTuTran, TuTran_SoGiayBaoTu, TuTran_NgayCapBaoTu, TuTran_NoiCapBaoTu.
3. Không trả field UI dạng data[...]; chỉ trả field nguồn trong schema.
4. Không bịa. Ô/bảng trống thì bỏ field hoặc trả mảng rỗng.
</critical_rules>

<document_classification>
1. Nhận diện Bản khai Mẫu 12 qua cụm: "BẢN KHAI", "người có công từ trần", "Từ trần ngày",
   "người nhận mai táng phí", "người nhận trợ cấp một lần".
2. Nhận diện CCCD qua "CĂN CƯỚC CÔNG DÂN"/"Citizen Identity Card"/"Số / No." (của người khai).
3. Trích lục khai tử: "TRÍCH LỤC KHAI TỬ"/"Giấy chứng tử" (của người từ trần). Tên file chỉ là tín hiệu phụ.
</document_classification>

<nguoi_khai>
1. ToKhai_HoTen, ToKhai_NgaySinh, ToKhai_GioiTinh, ToKhai_SoDinhDanh, ToKhai_NgayCap, ToKhai_NoiCap,
   ToKhai_DienThoai từ Mục 3 bản khai + CCCD người khai.
2. ToKhai_MoiQuanHeVoiTuTran là quan hệ của người khai với người có công từ trần (vd "Con đẻ").
3. ToKhai_LoaiGiayTo mặc định "Căn cước công dân" nếu là CCCD.
4. Quê quán/Nơi thường trú người khai là object {quocGia,tinh,xa,diaChi}.
</nguoi_khai>

<nguoi_tu_tran>
1. TuTran_HoTen, TuTran_NgaySinh, TuTran_GioiTinh, TuTran_QueQuan, TuTran_NoiThuongTru, TuTran_DoiTuong
   lấy từ Mục 1 bản khai (thông tin người có công từ trần).
2. TuTran_DoiTuong ghi rõ diện người có công (vd "Vợ liệt sĩ (Nguyễn Văn Giá)").
3. TuTran_NgayTuTran, TuTran_SoGiayBaoTu, TuTran_NgayCapBaoTu, TuTran_NoiCapBaoTu ưu tiên lấy từ
   TRÍCH LỤC KHAI TỬ. TuTran_SoQDHuongTroCap/NgayQD/NoiCapQD/TiLeTonThuong thường trống trên tờ khai → bỏ.
4. TuTran_MucTroCap là số tiền (vd "2.789.000"); TuTran_TroCapDaNhanDenHet là tháng (vd "Tháng 04/2026").
5. Quê quán/Nơi thường trú người từ trần là object {quocGia,tinh,xa,diaChi}.
</nguoi_tu_tran>

<mai_tang>
1. BẮT BUỘC: nếu Mục 2 - a) Cá nhân có ghi HỌ VÀ TÊN thì PHẢI trích đầy đủ nhóm MaiTang_* (MaiTang_HoTen,
   MaiTang_NgaySinh, MaiTang_GioiTinh, MaiTang_SoDinhDanh, MaiTang_NgayCap, MaiTang_NoiCap,
   MaiTang_LoaiGiayTo, MaiTang_QueQuan, MaiTang_NoiThuongTru, MaiTang_DienThoai, MaiTang_MoiQuanHe).
2. VẪN PHẢI trích MaiTang_* NGAY CẢ KHI:
   - Người ở Mục 2a TRÙNG với người khai/Mục 3 (vd cùng là một người) — KHÔNG được bỏ qua vì trùng.
   - Có câu ghi chú như "Đã ... nhận kinh phí mai táng phí bên bảo hiểm xã hội" — ghi chú này KHÔNG làm
     Mục 2a trống; miễn a) Cá nhân có họ tên thì vẫn trích.
   MaiTang_* và ToKhai_* (Mục 3) là HAI nhóm ĐỘC LẬP, phải trả CẢ HAI dù giá trị giống nhau.
3. Chỉ bỏ MaiTang_* khi Mục 2a thực sự KHÔNG có họ tên (trống) hoặc hồ sơ chọn "b) Tổ chức".
</mai_tang>

<than_nhan>
1. ToKhai_ThanNhan là mảng thân nhân (Mục 4a/biên bản họp GĐ): hoTen, namSinh, noiThuongTru, quanHe,
   ngheNghiep, hoanCanh. namSinh chỉ NĂM. Giữ đúng thứ tự, bỏ item trống.
2. ToKhai_ConNCC là mảng con NCC từ 18 tuổi đi học/khuyết tật (Mục 4b) — thường trống, bỏ nếu không có.
</than_nhan>

<cccd>
1. Person1_* là của NGƯỜI KHAI (còn sống). Person1_NgayCap lấy ở mặt sau CCCD.
2. Person1_NoiCuTru là object {quocGia,tinh,xa,diaChi}.
</cccd>

<output_examples>
Đúng (chú ý: Mục 2a và Mục 3 cùng là một người nhưng VẪN trả cả MaiTang_* lẫn ToKhai_*):
{"fields":{"ToKhai_HoTen":"Nguyễn Thị T","ToKhai_MoiQuanHeVoiTuTran":"Con đẻ","MaiTang_HoTen":"Nguyễn Thị T","MaiTang_SoDinhDanh":"027...","MaiTang_MoiQuanHe":"Con đẻ","TuTran_HoTen":"Nguyễn Thị C","TuTran_DoiTuong":"Vợ liệt sĩ (Nguyễn Văn G)","TuTran_NgayTuTran":"20/04/2026","TuTran_SoGiayBaoTu":"576/2026/TLKT-BS","ToKhai_ThanNhan":[{"hoTen":"Nguyễn Thị T","namSinh":"1961","quanHe":"Con đẻ"}]}}

Sai:
{"fields":{"ToKhai_HoTen":"Nguyễn Thị C","TuTran_HoTen":"Nguyễn Thị T"}}
Lý do sai: đảo ngược — ToKhai là người khai còn sống, TuTran là người có công đã mất.
</output_examples>"""

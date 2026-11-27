"""Quy tắc trích xuất cho "Giải quyết chế độ mai táng phí đối với cựu chiến binh" (2.002307)."""

EXTRA_RULES = """<critical_rules>
1. Ba người KHÁC nhau, không trộn dữ liệu:
   - ChuHoSo_* = CÁ NHÂN NHẬN TRỢ CẤP MAI TÁNG (còn sống) ở Mục 2a "Cá nhân hoặc tổ chức nhận trợ cấp mai táng" của
     Bản khai Mẫu số 01 Thông tư 21/2026/TT-BNV.
   - CCB_* = CỰU CHIẾN BINH ĐÃ CHẾT ở Mục 1 Bản khai, trên trích lục khai tử / giấy chứng tử và giấy xác nhận cựu chiến
     binh.
   - NguoiNop_* = người nộp theo nguoi_nop_context.
2. Không đưa cán bộ ký (Chủ tịch UBND, người ký trích lục, người chứng thực, Chỉ huy trưởng Ban CHQS, Chủ tịch Hội cựu
   chiến binh) vào bất kỳ vai nào.
3. Không bịa; ô trống / "Không áp dụng" thì bỏ field. Không trả field UI data[...].
</critical_rules>

<nguoi_nhan_tro_cap>
1. Họ tên, ngày sinh, giới tính, số định danh: ưu tiên thẻ CCCD ĐÚNG người (khớp họ tên hoặc số với Mục 2a), rồi Mục 2a.
2. Ngày cấp, nơi cấp: mặt sau CCCD đúng người; không có CCCD mà trích lục khai tử ghi "Họ, chữ đệm, tên người đi khai
   tử" TRÙNG người nhận trợ cấp → lấy số / ngày cấp / cơ quan cấp ở dòng "Giấy tờ tùy thân" ngay dưới tên đó.
3. Quê quán, nơi thường trú CHỈ lấy từ CCCD của người nhận trợ cấp (Bản khai không ghi). Không có CCCD → bỏ, KHÔNG lấy
   địa chỉ của cựu chiến binh.
4. Số điện thoại lấy Mục 2a Bản khai. ChuHoSo_QuanHe ngắn gọn ("Cháu nội"), bỏ phần giải thích.
5. Mục 2b ghi "Không áp dụng" / để trống → không trả ToChucNhan_Ten.
</nguoi_nhan_tro_cap>

<nguoi_nop>
1. result="owner_match": người nộp chính là người nhận trợ cấp → chỉ trả ChuHoSo_*, không lặp NguoiNop_*.
2. result="co_giay_to": trích NguoiNop_* TỪ ĐÚNG thẻ CCCD trong cccd_nguoi_nop.
3. result="khong_giay_to" hoặc không có nguoi_nop_context: bỏ toàn bộ NguoiNop_*.
</nguoi_nop>

<cuu_chien_binh>
1. Họ tên, ngày sinh: Mục 1 Bản khai → trích lục khai tử → giấy xác nhận. Giới tính: trích lục → giấy xác nhận.
2. CCB_NgayChet ưu tiên trích lục khai tử ("Đã chết vào lúc … ngày … tháng … năm …"), chỉ lấy ngày.
3. CCB_SoGiayChungTu là SỐ ở góc trái trích lục / giấy chứng tử (vd "152/TLKT"); KHÔNG lấy "Số chứng thực", "Quyển số",
   số giấy báo tử của cơ sở y tế. CCB_NgayCapGiayChungTu là ngày ký trích lục (dòng "<địa danh>, ngày … tháng … năm …"
   góc phải), KHÔNG lấy ngày chứng thực bản sao trong khung lời chứng.
4. CCB_QueQuan lấy "Quê quán" trên giấy xác nhận cựu chiến binh, giữ địa danh CŨ kèm huyen (vd "xã A, huyện B, tỉnh C
   (nay là xã D, tỉnh E)" → tinh "C", huyen "B", xa "Xã A"). CCB_NoiThuongTru lấy "Nơi cư trú cuối cùng" trên trích lục.
5. Số hiệu quân nhân, số thẻ hội viên, quyết định phục viên KHÔNG phải sổ trợ cấp — không trả vào field nào.
</cuu_chien_binh>

<dia_chi>
Mọi địa chỉ trả object {quocGia,tinh,huyen,xa,chiTietDuoiXa}: địa chỉ cũ ba cấp giữ cụm quận/huyện ở khoá "huyen" (không
đưa vào xa, không đưa vào chiTietDuoiXa); địa chỉ mới hai cấp thì bỏ huyen. Số định danh, số điện thoại chỉ giữ chữ số;
ngày dd/mm/yyyy.
</dia_chi>

<output_contract>
Ví dụ đúng (dữ liệu giả):
{"fields":{"ChuHoSo_HoTen":"TRẦN VĂN B","ChuHoSo_SoDinhDanh":"001200000001","ChuHoSo_GioiTinh":"Nam",
"ChuHoSo_DienThoai":"0900000000","ChuHoSo_QuanHe":"Con đẻ","CCB_HoTen":"TRẦN VĂN A","CCB_NgaySinh":"01/01/1950",
"CCB_GioiTinh":"Nam","CCB_NgayChet":"02/02/2026","CCB_LoaiGiayChungTu":"Trích lục khai tử","CCB_SoGiayChungTu":"10/TLKT",
"CCB_NgayCapGiayChungTu":"05/02/2026","CCB_NoiCapGiayChungTu":"Ủy ban nhân dân xã X, tỉnh Y",
"CCB_QueQuan":{"quocGia":"Việt Nam","tinh":"Tỉnh C","huyen":"Huyện B","xa":"Xã A","chiTietDuoiXa":""},
"CCB_DoiTuong":"Cựu chiến binh (kháng chiến chống Mỹ, nhập ngũ 1970, phục viên 1975)"}}
Sai: {"fields":{"ChuHoSo_HoTen":"TRẦN VĂN A"}} — đó là cựu chiến binh đã chết, không phải người nhận trợ cấp.
</output_contract>"""

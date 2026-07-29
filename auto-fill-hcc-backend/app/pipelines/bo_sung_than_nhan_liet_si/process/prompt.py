"""Quy tắc compact prompt cho thủ tục "Bổ sung tình hình thân nhân trong hồ sơ liệt sĩ"."""

EXTRA_RULES = """<critical_rules>
1. "ĐƠN ĐỀ NGHỊ Sửa đổi, bổ sung thông tin trong hồ sơ liệt sĩ" (Mẫu số 26/06) là NGUỒN CHÍNH cho
   ToKhai_*, ToKhai_ThanNhan và tên liệt sĩ.
2. CCCD/CMND chỉ dùng để trả Person1_* (bổ sung số định danh, ngày/nơi cấp, nơi cư trú). Hồ sơ liệt sĩ gốc
   và Bằng Tổ quốc ghi công dùng cho LietSi_* (quê quán, cơ quan/cấp bậc khi hy sinh, số bằng/QĐ).
3. Không trả field UI dạng data[...]; chỉ trả field nguồn trong schema.
4. Không bịa. Ô/bảng trống thì bỏ field hoặc trả mảng rỗng.
</critical_rules>

<document_classification>
1. Nhận diện Đơn Mẫu 26 qua cụm: "ĐƠN ĐỀ NGHỊ", "Sửa đổi, bổ sung thông tin trong hồ sơ liệt sĩ",
   "Thuộc diện người có công", "đề nghị sửa đổi, bổ sung".
2. Nhận diện CCCD qua "CĂN CƯỚC CÔNG DÂN"/"Citizen Identity Card"/"Số / No.".
3. Công văn UBND (".../CV-UBND", "Kính gửi: Sở Nội vụ") là giấy đính kèm; chỉ dùng đối chiếu, không tạo field mới.
   Tên file chỉ là tín hiệu phụ, OCR là nguồn chính.
</document_classification>

<nguoi_khai>
1. ToKhai_HoTen, ToKhai_NgaySinh, ToKhai_GioiTinh, ToKhai_SoDinhDanh, ToKhai_NgayCap, ToKhai_NoiCap,
   ToKhai_DienThoai lấy ở phần thông tin người khai đầu đơn.
2. ToKhai_QuanHeVoiLietSi lấy từ dòng "Thuộc diện người có công" (vd "Con đẻ liệt sĩ (Nguyễn Văn Giá)"
   → trả "Con đẻ").
3. Quê quán và Nơi thường trú là object {quocGia,tinh,xa,diaChi}. quocGia mặc định "Việt Nam";
   tinh giữ đủ "Tỉnh ..."/"Thành phố ..."; xa giữ đủ "Xã ..."/"Phường ..."/"Thị trấn ...";
   diaChi chỉ giữ thôn/tổ dân phố/số nhà/đường, KHÔNG lặp xã/huyện/tỉnh.
</nguoi_khai>

<liet_si>
1. LietSi_HoTen là tên liệt sĩ có hồ sơ được đề nghị sửa đổi (vd "hồ sơ liệt sĩ Nguyễn Văn Giá").
2. LietSi_QueQuan, LietSi_NgayHySinh, LietSi_CoQuanDonVi, LietSi_CapBac lấy từ hồ sơ liệt sĩ gốc;
   LietSi_SoBang, LietSi_SoQuyetDinh, LietSi_NgayQuyetDinh lấy từ Bằng Tổ quốc ghi công. Bỏ field nào không có nguồn.
</liet_si>

<than_nhan>
1. ToKhai_ThanNhan là mảng mọi thành viên trong danh sách "Đề nghị sửa đổi, bổ sung ... gồm các thành viên sau".
   Mỗi thành viên có: hoTen, ngaySinh, moiQuanHe (và soGiayTo/noiThuongTru/hoanCanh nếu có).
2. QUAN TRỌNG: ngaySinh LẤY từ dòng "Thông tin ĐỀ NGHỊ sửa đổi, bổ sung: ... sinh ngày dd/mm/yyyy" —
   ĐÂY là thông tin muốn cập nhật. TUYỆT ĐỐI KHÔNG lấy dòng "Thông tin đang ghi trong hồ sơ: ... sinh năm ..."
   (đó là thông tin CŨ đang sai).
3. moiQuanHe lấy từ ghi chú trong ngoặc sau tên (vd "(vợ liệt sĩ ...)" → "Vợ"; "(con đẻ liệt sĩ ...)" → "Con đẻ").
4. soGiayTo (số CCCD/CMND hoặc số Giấy khai sinh) lấy từ bản sao chứng minh quan hệ nếu có; không bịa.
5. Không được chỉ lấy thành viên đầu nếu đơn có nhiều người. Giữ đúng thứ tự.
</than_nhan>

<cccd>
1. Person1_NgayCap lấy ở mặt sau CCCD, KHÔNG lấy ngày sinh/ngày hết hạn.
2. Person1_NoiCuTru là object {quocGia,tinh,xa,diaChi}.
</cccd>

<output_examples>
Đúng:
{"fields":{"ToKhai_HoTen":"Trần Thị B","ToKhai_QuanHeVoiLietSi":"Con đẻ","LietSi_HoTen":"Trần Văn A","ToKhai_ThanNhan":[{"hoTen":"Lê Thị C","ngaySinh":"01/01/1937","moiQuanHe":"Vợ"},{"hoTen":"Trần Thị B","ngaySinh":"29/05/1961","moiQuanHe":"Con đẻ"}]}}

Sai:
{"fields":{"ToKhai_ThanNhan":[{"hoTen":"Lê Thị C","ngaySinh":"1938"}]}}
Lý do sai: lấy năm sinh ở dòng "đang ghi trong hồ sơ" (cũ) thay vì ngày ở dòng "đề nghị sửa đổi, bổ sung".
</output_examples>"""

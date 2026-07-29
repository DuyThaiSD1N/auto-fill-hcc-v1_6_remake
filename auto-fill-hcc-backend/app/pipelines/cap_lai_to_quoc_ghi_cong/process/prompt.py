"""Quy tắc compact prompt cho thủ tục "Cấp lại Bằng Tổ quốc ghi công"."""

EXTRA_RULES = """<critical_rules>
1. Tờ khai "ĐƠN ĐỀ NGHỊ Cấp đổi/cấp lại Bằng Tổ quốc ghi công" (Mẫu số 16) là NGUỒN CHÍNH cho toàn bộ
   ToKhai_*, LietSi_*, ToKhai_ThanNhan.
2. CCCD/CMND chỉ dùng để trả Person1_* (bổ sung/đối chiếu số định danh, ngày cấp, nơi cấp, nơi cư trú).
   Không thay thế ToKhai_* nếu tờ khai đã có thông tin.
3. Không trả field UI dạng data[...]; chỉ trả field nguồn trong schema.
4. Không bịa. Ô/bảng trống trong tờ khai thì bỏ field hoặc trả mảng rỗng.
</critical_rules>

<document_classification>
1. Nhận diện tờ khai Mẫu 16 qua cụm: "ĐƠN ĐỀ NGHỊ", "Cấp đổi/cấp lại", "Tổ quốc ghi công",
   "Thông tin người đề nghị", "Thông tin về liệt sĩ", "Mẫu số 16".
2. Nhận diện CCCD qua "CĂN CƯỚC CÔNG DÂN"/"Citizen Identity Card"/"Số / No.".
3. "DANH SÁCH ĐỀ NGHỊ CẤP LẠI BẰNG..." và Công văn của UBND chỉ là giấy đính kèm; chỉ dùng Danh sách để
   ĐỐI CHIẾU tên/nguyên quán liệt sĩ, không tạo field mới. Tên file chỉ là tín hiệu phụ, OCR là nguồn chính.
</document_classification>

<nguoi_de_nghi>
1. ToKhai_HoTen, ToKhai_NgaySinh, ToKhai_GioiTinh, ToKhai_SoDinhDanh, ToKhai_NgayCap, ToKhai_NoiCap,
   ToKhai_DienThoai, ToKhai_MoiQuanHeVoiLietSi, ToKhai_DeNghiCap, ToKhai_LyDoCap lấy từ mục 1.
2. ToKhai_DeNghiCap chỉ trả "Cấp đổi" hoặc "Cấp lại" theo đúng chữ khoanh/ghi trong tờ khai.
3. Quê quán và Nơi thường trú là object {quocGia,tinh,xa,diaChi}. quocGia mặc định "Việt Nam";
   tinh giữ đủ "Tỉnh ..."/"Thành phố ..."; xa giữ đủ "Xã ..."/"Phường ..."/"Thị trấn ...";
   diaChi chỉ giữ thôn/tổ dân phố/số nhà/đường, KHÔNG lặp lại xã/huyện/tỉnh.
4. Với địa chỉ nhiều phần: tỉnh/thành phố là đơn vị hành chính cấp tỉnh ở CUỐI chuỗi; xã/phường/thị trấn
   là cấp xã ngay trước tỉnh hoặc phần có tiền tố "xã/phường/thị trấn/TT"; phần còn lại mới vào diaChi.
5. Nếu địa chỉ chỉ có 2 phần và phần đầu là xã/phường/thị trấn, đặt phần đầu vào xa, phần sau vào tinh,
   để diaChi rỗng.
</nguoi_de_nghi>

<liet_si>
1. LietSi_HoTen, LietSi_NgaySinh, LietSi_GioiTinh, LietSi_QueQuan lấy từ mục 2.
2. LietSi_NgayHySinh, LietSi_CapBac, LietSi_SoBang, LietSi_SoQuyetDinh, LietSi_NgayQuyetDinh,
   LietSi_DonViCapBang lấy từ mục 2; ô nào trống thì bỏ field đó, không suy đoán.
3. Tên liệt sĩ CHUẨN theo tờ khai Mẫu 16 (mục 2, và dòng "đề nghị cấp ... đối với liệt sĩ" ở mục 1).
   Danh sách đề nghị và Công văn chỉ là giấy phụ; nếu cách viết tên ở đó khác tờ khai (vd một chữ cái
   đầu khác) thì VẪN TRẢ THEO TỜ KHAI, tuyệt đối không đổi tên liệt sĩ theo danh sách/công văn.
</liet_si>

<than_nhan>
1. ToKhai_ThanNhan là mảng mọi dòng trong bảng mục 3 "Thông tin về thân nhân liệt sĩ";
   mỗi item có đúng key: hoTen, ngaySinh, moiQuanHe.
2. Không được chỉ lấy dòng đầu nếu OCR có nhiều dòng thân nhân. Bảng trống thì bỏ field.
</than_nhan>

<cccd>
1. Person1_NgayCap lấy ở mặt sau CCCD, KHÔNG lấy ngày sinh hay ngày hết hạn.
2. Person1_NoiCuTru là object {quocGia,tinh,xa,diaChi}.
</cccd>

<output_examples>
Đúng:
{"fields":{"ToKhai_HoTen":"Trần Văn A","ToKhai_MoiQuanHeVoiLietSi":"em ruột","ToKhai_DeNghiCap":"Cấp lại","ToKhai_LyDoCap":"rách nát","ToKhai_NoiThuongTru":{"quocGia":"Việt Nam","tinh":"Tỉnh Bắc Ninh","xa":"Phường Song Liễu","diaChi":"TDP Đoàn Hạ"},"LietSi_HoTen":"Trần Văn B","LietSi_NgaySinh":"không nhớ","ToKhai_ThanNhan":[{"hoTen":"Trần Văn C","ngaySinh":"không nhớ","moiQuanHe":"Bố đẻ"}]}}

Sai:
{"fields":{"data[fullname]":"Trần Văn A","denghiCap":"Cấp lại"}}
Lý do sai: trả field UI data[...] thay vì field nguồn ToKhai_*.
</output_examples>"""

"""Quy tắc compact prompt cho thủ tục "Giải quyết chế độ trợ cấp thờ cúng liệt sĩ"."""

EXTRA_RULES = """<critical_rules>
1. "ĐƠN ĐỀ NGHỊ ... trợ cấp thờ cúng liệt sĩ" (Mẫu số 18) là NGUỒN CHÍNH cho ToKhai_*, ToKhai_ThanNhan,
   tên liệt sĩ (ToKhai_LietSiThoCung).
2. CCCD/CMND chỉ dùng để trả Person1_*. Bằng "Tổ quốc ghi công" dùng cho LietSi_* (quê quán liệt sĩ,
   số bằng, quyết định số, ngày cấp bằng). Trích lục khai tử dùng cho năm mất của thân nhân.
3. Không trả field UI dạng data[...]; chỉ trả field nguồn trong schema.
4. Không bịa. Ô/bảng trống thì bỏ field hoặc trả mảng rỗng.
</critical_rules>

<document_classification>
1. Nhận diện Đơn Mẫu 18 qua cụm: "ĐƠN ĐỀ NGHỊ", "trợ cấp thờ cúng liệt sĩ", "Mối quan hệ với liệt sĩ",
   "được ủy quyền thờ cúng".
2. Nhận diện CCCD qua "CĂN CƯỚC CÔNG DÂN"/"Citizen Identity Card"/"Số / No.".
3. Bằng TQGC (tiêu đề "TỔ QUỐC GHI CÔNG", "Bằng số", "Quyết định số") là nguồn thông tin liệt sĩ.
   Tên file chỉ là tín hiệu phụ, OCR là nguồn chính.
</document_classification>

<nguoi_de_nghi>
1. ToKhai_HoTen, ToKhai_NgaySinh, ToKhai_GioiTinh, ToKhai_SoDinhDanh, ToKhai_NgayCap, ToKhai_NoiCap,
   ToKhai_DienThoai, ToKhai_MoiQuanHeVoiLietSi lấy ở phần thông tin người đề nghị.
2. ToKhai_LietSiThoCung là họ tên liệt sĩ mà người đề nghị được ủy quyền/đứng ra thờ cúng.
3. Quê quán và Nơi thường trú người đề nghị là object {quocGia,tinh,xa,diaChi}. quocGia mặc định "Việt Nam";
   tinh giữ đủ "Tỉnh ..."/"Thành phố ..."; xa giữ đủ "Xã ..."/"Phường ..."; diaChi chỉ giữ thôn/tổ/số nhà/đường.
</nguoi_de_nghi>

<liet_si>
1. LietSi_QueQuan trả NGUYÊN CHUỖI địa chỉ quê quán liệt sĩ (không tách cấp), vd
   "TDP Mãn Xá Đông, phường Song Liễu, tỉnh Bắc Ninh".
2. LietSi_SoBang, LietSi_SoQuyetDinh, LietSi_NgayQuyetDinh lấy từ Bằng TQGC. Bỏ field nào không có nguồn.
</liet_si>

<than_nhan>
1. ToKhai_ThanNhan là mảng thân nhân liệt sĩ (thường là bố/mẹ đẻ đã mất). Mỗi item:
   hoTen, namSinh, namMat, noiThuongTru, moiQuanHe.
2. namSinh/namMat chỉ là NĂM (4 chữ số). namMat ưu tiên lấy từ trích lục khai tử.
3. Không được chỉ lấy dòng đầu nếu có nhiều thân nhân. Giữ đúng thứ tự. Bảng trống thì bỏ field.
</than_nhan>

<cccd>
1. Person1_NgayCap lấy ở mặt sau CCCD, KHÔNG lấy ngày sinh/ngày hết hạn.
2. Person1_NoiCuTru là object {quocGia,tinh,xa,diaChi}.
</cccd>

<output_examples>
Đúng:
{"fields":{"ToKhai_HoTen":"Nguyễn Hữu H","ToKhai_MoiQuanHeVoiLietSi":"Anh ruột","ToKhai_LietSiThoCung":"Nguyễn Hữu K","LietSi_QueQuan":"TDP Mãn Xá Đông, phường Song Liễu, tỉnh Bắc Ninh","LietSi_SoBang":"7L-496x","ToKhai_ThanNhan":[{"hoTen":"Nguyễn Hữu K","namSinh":"1931","namMat":"2026","moiQuanHe":"Bố đẻ"}]}}

Sai:
{"fields":{"data[UqTcLs]":"Nguyễn Hữu K","LietSi_QueQuan":{"tinh":"Bắc Ninh"}}}
Lý do sai: trả field UI data[...]; và LietSi_QueQuan phải là chuỗi đầy đủ, không phải object.
</output_examples>"""

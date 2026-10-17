"""Quy tắc compact prompt cho "Cấp bổ sung hoặc cấp lại giấy chứng nhận người có công" (1.010814)."""

EXTRA_RULES = """<critical_rules>
1. "ĐƠN ĐỀ NGHỊ Cấp bổ sung hoặc cấp lại giấy chứng nhận ..." (Mẫu số 25) là NGUỒN CHÍNH cho mọi Don_*.
2. CCCD/thẻ căn cước chỉ trả Person1_*. Giấy chứng nhận đã cấp (thân nhân liệt sĩ/thương binh/...) chỉ trả GCN_*.
3. Giấy chứng nhận cũ có thể ghi thông tin của NGƯỜI KHÁC (vd liệt sĩ). Không bao giờ chép số liệu từ giấy
   chứng nhận sang Don_* hay Person1_*.
4. Không trả field UI dạng data[...]; chỉ trả field nguồn trong schema. Ô trống thì bỏ field, không bịa.
</critical_rules>

<document_classification>
1. Đơn M25: có "ĐƠN ĐỀ NGHỊ", "Cấp bổ sung hoặc cấp lại giấy chứng nhận", "Tôi là", "Lý do", "Mẫu số 25".
2. CCCD: "CĂN CƯỚC"/"Citizen Identity Card"/"Số định danh cá nhân".
3. Giấy chứng nhận đã cấp: tiêu đề "GIẤY CHỨNG NHẬN" + thân nhân liệt sĩ/thương binh/bệnh binh..., có "Được cấp
   theo Quyết định số", không có mục "Lý do".
</document_classification>

<don_mau_25>
1. Don_DienNguoiCoCong lấy NGUYÊN VĂN sau chữ "Tôi là" (diện người có công), không phải họ tên.
2. Don_SoQuyetDinh / Don_NgayQuyetDinh / Don_CoQuanQuyetDinh tách từ dòng "Đã được hưởng trợ cấp theo quyết định
   số ... ngày ... của ...". Don_SoQuyetDinh chỉ giữ số hiệu (vd "1256/QĐ-LĐTBXH").
3. Don_LoaiGiayChungNhan là tên loại giấy ở chú thích (1)/(5), vd "Giấy chứng nhận thân nhân liệt sĩ".
4. Don_LyDo chép nguyên văn mục Lý do.
5. Quê quán, Nơi thường trú là object {quocGia,tinh,xa,diaChi}: tinh giữ "Tỉnh ..."/"Thành phố ...", xa giữ
   "Xã ..."/"Phường ...", diaChi chỉ thôn/tổ/số nhà/đường, KHÔNG lặp xã/tỉnh. Địa chỉ chỉ có xã + tỉnh thì
   diaChi rỗng.
</don_mau_25>

<output_examples>
Đúng:
{"fields":{"Don_HoTen":"TRẦN VĂN A","Don_DienNguoiCoCong":"Thân nhân liệt sĩ (con của liệt sĩ Trần Văn B)","Don_SoQuyetDinh":"123/QĐ-LĐTBXH","Don_NgayQuyetDinh":"01/02/2010","Don_CoQuanQuyetDinh":"Giám đốc Sở Lao động - Thương binh và Xã hội tỉnh X","Don_LoaiGiayChungNhan":"Giấy chứng nhận thân nhân liệt sĩ","Don_LoaiDeNghi":"Cấp lại","Don_NoiThuongTru":{"quocGia":"Việt Nam","tinh":"Tỉnh Mẫu","xa":"Xã Mẫu","diaChi":"Thôn 1"}}}

Sai:
{"fields":{"data[fullname]":"TRẦN VĂN A","Don_DienNguoiCoCong":"TRẦN VĂN A"}}
Lý do sai: trả field UI data[...]; "Tôi là" là diện người có công, không phải họ tên.
</output_examples>"""

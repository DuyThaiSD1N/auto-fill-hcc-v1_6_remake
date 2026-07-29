"""Procedure-specific compact prompt rules for mai táng phí dân công hỏa tuyến."""

EXTRA_RULES = """<critical_rules>
1. Chỉ trả field compact nằm trong schema. Không trả field UI như data[fullname], data[ownerFullname].
2. Không lấy thông tin người từ trần để điền người nộp/chủ hồ sơ.
3. Dùng OCR làm nguồn chính; tên file chỉ dùng như tín hiệu phụ khi OCR quá ít chữ.
</critical_rules>

<document_roles>
1. CCCD/CMND: trả Person1_*; nếu có hai giấy tờ tùy thân khác nhau thì trả thêm Person2_*.
2. Bản khai thân nhân đề nghị hưởng chế độ mai táng phí theo Quyết định số 49/2015/QĐ-TTg:
   trả nhóm ToKhai_ThanNhan*.
3. Mỗi nhóm Person* phải lấy trọn từ đúng một CCCD/CMND, không trộn dữ liệu giữa hai người.
</document_roles>

<declaration_extraction>
1. Nhận diện bản khai bằng các cụm như "Bản khai của thân nhân", "Đề nghị hưởng chế độ mai táng phí",
   "Quyết định số 49/2015/QĐ-TTg", hoặc "dân công hỏa tuyến".
2. Chỉ trích mục "1. Phần khai về thân nhân (người đứng khai nhận trợ cấp)".
3. Mapping trong mục 1:
   - "Họ và tên" -> ToKhai_ThanNhanHoTen.
   - "Ngày, tháng, năm sinh" -> ToKhai_ThanNhanNgaySinh.
   - "Số điện thoại" -> ToKhai_ThanNhanSoDienThoai.
   - "Trú quán" hoặc dòng xác nhận "Hiện cư trú tại" -> ToKhai_ThanNhanTruQuan.
   - "Quan hệ với người từ trần" -> ToKhai_QuanHeNguoiTuTran nếu có giá trị thật.
4. Không lấy các dòng trong mục "2. Phần khai về người từ trần" như họ tên người chết, ngày chết,
   nguyên quán, giấy chứng tử, quyết định hưởng trợ cấp.
5. Nếu có cả "Trú quán" ở mục 1 và "Hiện cư trú tại" trong phần xác nhận, ưu tiên "Trú quán"; nếu
   "Trú quán" mờ/thiếu thì dùng "Hiện cư trú tại".
</declaration_extraction>

<cccd_extraction>
1. Bắt buộc cố đọc Person*_NgayCap cho từng CCCD đã nhận diện. Ngày cấp nằm ở mặt sau ngay sau/gần
   nhãn "Ngày, tháng, năm / Date, month, year". Không lấy ngày sinh, không lấy ngày hết hạn.
2. Bắt buộc cố đọc Person*_NoiCap từ mặt sau CCCD. Nếu OCR thấy "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ
   HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" thì trả "Cục Cảnh sát quản lý hành chính về trật tự xã hội".
   Nếu là thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN"/"MINISTRY OF PUBLIC SECURITY" thì trả "Bộ Công an".
3. Với Person*_NoiCuTru, nếu OCR có xã/phường/thị trấn thì trả key "xa"; "diaChi" chỉ giữ phần
   chi tiết như số nhà/khu/xóm/thôn/bản/tổ dân phố, không lặp xã/huyện/tỉnh.
</cccd_extraction>

<address_rules>
1. Field địa chỉ trả object {"quocGia":"Việt Nam","tinh":"<tỉnh/thành>","xa":"<xã/phường/thị trấn>",
   "diaChi":"<chi tiết trước xã>"}.
2. Với chuỗi như "Tổ dân phố Tả Làn Than, phường Tân Phong, tỉnh Lai Châu", trả
   {"quocGia":"Việt Nam","tinh":"Lai Châu","xa":"Tân Phong","diaChi":"Tổ dân phố Tả Làn Than"}.
3. Nếu có cấp huyện/quận ở giữa, bỏ cấp huyện/quận; không đưa huyện vào diaChi.
</address_rules>

<output_contract>
Ví dụ đúng:
{"fields":{"ToKhai_ThanNhanHoTen":"Vũ Đình Thiết","ToKhai_ThanNhanNgaySinh":"26/04/2003","ToKhai_ThanNhanSoDienThoai":"0976134251","ToKhai_ThanNhanTruQuan":{"quocGia":"Việt Nam","tinh":"Lai Châu","xa":"Tân Phong","diaChi":"Tổ dân phố Tả Làn Than"},"Person1_HoTen":"VŨ ĐÌNH THIẾT","Person1_SoDinhDanh":"040203015844","Person1_GioiTinh":"Nam"}}

Ví dụ sai:
{"fields":{"data[fullname]":"Vũ Đình Thiết","ToKhai_ThanNhanHoTen":"người từ trần"}}
Sai vì trả field UI và lấy nhầm người từ trần.
</output_contract>"""


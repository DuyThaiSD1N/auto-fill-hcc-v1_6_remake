"""Procedure-specific compact prompt rules for "Xác định mức độ khuyết tật"."""

EXTRA_RULES = """<procedure>
Thủ tục: Xác định, xác định lại mức độ khuyết tật và cấp Giấy xác nhận khuyết tật.
Đầu vào thường gồm:
1. ĐƠN ĐỀ NGHỊ XÁC ĐỊNH, XÁC ĐỊNH LẠI MỨC ĐỘ KHUYẾT TẬT VÀ CẤP/CẤP ĐỔI/CẤP LẠI GIẤY XÁC NHẬN KHUYẾT TẬT.
2. CCCD/CMND của người đứng đơn/người đại diện hợp pháp hoặc người khuyết tật.
Có thể kèm hồ sơ bệnh án, trích lục khai sinh hoặc giấy tờ y tế khác để bổ sung thông tin người khuyết tật.
</procedure>

<critical_rules>
1. Không trả field UI như data[NktHoTen], data[fullname], data[khuyetTat...]. Chỉ trả các field compact trong schema.
2. Không dùng tên file để kết luận dạng khuyết tật, mức độ hoạt động hoặc nội dung đề nghị; phải dựa trên OCR.
3. Đơn đề nghị là nguồn chính cho Nkt_*, Ndd_*, DeNghi_NoiDung, KhuyetTat_* và MucDo_HoatDong.
4. ChuHoSo_* là người đứng đơn/người đại diện hợp pháp trong Mẫu số 01. Nếu mục người đại diện để trống và người khuyết tật tự đề nghị thì ChuHoSo_* là người khuyết tật.
5. Hồ sơ bệnh án/trích lục khai sinh chỉ dùng để bổ sung thông tin người khuyết tật còn thiếu hoặc đối chiếu ngày sinh/số định danh; không được thay thế các ô đánh dấu trong đơn đề nghị nếu đơn đã rõ.
6. NguoiNop_* chỉ được trích từ block matched_requester_ocr do Python cung cấp. formContext UI chỉ là mỏ neo xác định đúng người; mọi ngày sinh, giới tính, ngày cấp, nơi cấp, địa chỉ và thông tin khác vẫn phải có trong OCR đúng người.
7. Không mặc định CCCD duy nhất là của chủ hồ sơ. Chỉ ghép CCCD vào ChuHoSo_* khi họ tên hoặc số định danh khớp đúng người đứng đơn đã xác định trong Mẫu số 01.
</critical_rules>

<source_priority>
- NguoiNop_*: chỉ lấy từ matched_requester_ocr. Ưu tiên CCCD/CMND đúng người cho họ tên, số định danh, ngày sinh, giới tính, ngày cấp, nơi cấp, quốc tịch và nơi thường trú; tài liệu khác chỉ bổ sung field còn thiếu của cùng người.
- ChuHoSo_*: ưu tiên đúng mục người đứng đơn/người đại diện hợp pháp trong Mẫu số 01; bổ sung họ tên, số định danh, ngày sinh, giới tính, ngày cấp, nơi cấp và quốc tịch từ CCCD/CMND khớp đúng người. Nếu có mặt trước + mặt sau thì gộp theo số định danh/họ tên/MRZ.
- ChuHoSo_NoiCuTru và ChuHoSo_DienThoai: ưu tiên đúng mục người đứng đơn/người đại diện trong đơn; CCCD chỉ bổ sung địa chỉ khi đơn thiếu.
- Nkt_HoTen/Nkt_NgaySinh/Nkt_GioiTinh/Nkt_ThuongTru/Nkt_NoiOHienNay: ưu tiên mục I "Người được xác định mức độ khuyết tật" trong đơn đề nghị.
- Nkt_SoDinhDanh: ưu tiên mục I trong đơn; nếu đơn bỏ trống thì bổ sung từ hồ sơ bệnh án/trích lục khai sinh đúng người.
- Ndd_*: lấy từ mục II "Người đại diện hợp pháp" trong đơn đề nghị.
- Nếu cùng một thông tin xuất hiện ở nhiều giấy tờ, ưu tiên giấy tờ định danh chính thức cho số định danh/ngày sinh; ưu tiên đơn đề nghị cho nội dung khai và các bảng đánh dấu.
</source_priority>

<role_rules>
- Người nộp hồ sơ là người đã được Python đối chiếu mỏ neo tên + CCCD từ UI với tài liệu. BẮT BUỘC trả mọi NguoiNop_* đọc được trong matched_requester_ocr; không lấy người ký đơn, người đại diện hoặc CCCD khác làm NguoiNop_* nếu không nằm trong block này.
- NguoiNop_HoTen và NguoiNop_SoDinhDanh cũng phải được trả từ OCR để Python kiểm tra lại với formContext; không chép giá trị chỉ vì nó xuất hiện trong phần hướng dẫn context.
- Nếu mục II "Người đại diện hợp pháp" có thông tin rõ và người này đứng đơn thì ChuHoSo_* lấy từ mục II cùng CCCD khớp người đó.
- Khi người đại diện hợp pháp là ChuHoSo_*, BẮT BUỘC trả đầy đủ mọi thông tin đọc được của cùng người vào CẢ HAI nhóm ChuHoSo_* và Ndd_*; không được bỏ ChuHoSo_NoiCuTru, ChuHoSo_DienThoai, ChuHoSo_SoDinhDanh hoặc field ChuHoSo_* khác chỉ vì giá trị đã xuất hiện trong Ndd_*. Việc lặp lại giữa hai namespace là bắt buộc vì chúng điền hai khối khác nhau trên biểu mẫu.
- Ánh xạ cùng người đại diện: Ndd_HoTen -> ChuHoSo_HoTen; Ndd_SoDinhDanh -> ChuHoSo_SoDinhDanh; Ndd_NoiCuTru -> ChuHoSo_NoiCuTru; Ndd_SoDienThoai -> ChuHoSo_DienThoai. Ngày sinh, giới tính, ngày cấp, nơi cấp, quốc tịch chỉ bổ sung vào ChuHoSo_* khi đúng mục II hoặc CCCD khớp người đại diện có ghi rõ; không suy đoán field không có nguồn.
- Nếu mục II để trống và đơn thể hiện người khuyết tật tự đề nghị thì ChuHoSo_* lấy từ mục I cùng CCCD khớp người khuyết tật.
- Nkt_* và Ndd_* vẫn phải trả độc lập để điền phần chi tiết Mẫu số 01, kể cả khi một trong hai người đồng thời là ChuHoSo_*.
- Không lấy người chết, cán bộ tiếp nhận, cán bộ xác nhận, bác sĩ, người ký thay hoặc người chỉ xuất hiện trong chữ ký làm ChuHoSo_*.
- Ngày cấp và nơi cấp phải thuộc cùng số giấy tờ, cùng người; không ghép chéo hai CCCD.
</role_rules>

<address_rules>
- Mọi địa chỉ trả object {quocGia,tinh,xa,diaChi}; quocGia mặc định "Việt Nam" nếu là địa chỉ trong nước.
- Địa chỉ hành chính hiện hành chỉ dùng 2 cấp: xã/phường/thị trấn và tỉnh/thành phố.
- Nếu OCR có dạng cũ "[chi tiết], xã/phường, huyện/quận/thị xã, tỉnh" thì bỏ cấp huyện/quận/thị xã.
- diaChi chỉ giữ phần chi tiết đứng trước xã/phường: số nhà, đường/phố, tổ, tổ dân phố, bản, thôn, xóm, khu.
  Không lặp xã/huyện/tỉnh vào diaChi.
- Ví dụ: "Số nhà 003, phố Yết Kiêu, Tổ 16, phường Tân Phong, Lai Châu"
  -> {"quocGia":"Việt Nam","tinh":"Lai Châu","xa":"Tân Phong","diaChi":"Số nhà 003, phố Yết Kiêu, Tổ 16"}.
</address_rules>

<cccd_rules>
- Khi matched_requester_ocr là CCCD người nộp, BẮT BUỘC cố đọc NguoiNop_NgaySinh, NguoiNop_GioiTinh, NguoiNop_NgayCap, NguoiNop_NoiCap, NguoiNop_NoiCuTru và NguoiNop_QuocTich từ đúng thẻ.
- Bắt buộc cố đọc ChuHoSo_NgayCap và ChuHoSo_NoiCap từ mặt sau CCCD đúng chủ hồ sơ nếu mặt sau có trong OCR.
- Ngày cấp nằm gần nhãn "Ngày, tháng, năm / Date, month, year"; không lấy ngày hết hạn hoặc ngày sinh.
- Không có dòng cơ quan cấp rõ thì bỏ field NoiCap tương ứng; không suy nơi cấp chỉ từ ngày cấp.
- Nếu đúng thẻ có "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" thì chuẩn hóa NoiCap của CHÍNH người trên thẻ thành "Cục Cảnh sát quản lý hành chính về trật tự xã hội": thẻ matched_requester_ocr ghi vào NguoiNop_NoiCap, thẻ chủ hồ sơ ghi vào ChuHoSo_NoiCap.
- Nếu là thẻ Căn cước mới và OCR ghi "BỘ CÔNG AN"/"MINISTRY OF PUBLIC SECURITY" thì chuẩn hóa NoiCap tương ứng thành "Bộ Công an".
</cccd_rules>

<proposal_rules>
- DeNghi_NoiDung = "xac_dinh" khi ô/dòng được chọn là "Xác định mức độ khuyết tật và cấp Giấy xác nhận khuyết tật".
- DeNghi_NoiDung = "xac_dinh_lai" khi ô/dòng được chọn là "Xác định lại mức độ khuyết tật và cấp/cấp đổi/cấp lại Giấy xác nhận khuyết tật".
- Chỉ chọn theo ô được đánh dấu rõ (X, ☑, ✓, hoặc dòng được chọn). Nếu OCR không rõ ô nào được chọn thì bỏ field này.
</proposal_rules>

<representative_rules>
- Ndd_QuanHe giữ theo OCR nhưng nên chuẩn hóa nhẹ về quan hệ phổ biến:
  "bố", "bố đẻ", "cha đẻ" -> "Cha"; "mẹ", "mẹ đẻ" -> "Mẹ"; "ông nội/ông ngoại" -> "Ông"; "bà nội/bà ngoại" -> "Bà".
- Không lấy người ký đơn nếu khác với mục II người đại diện hợp pháp.
- Số điện thoại chỉ lấy số liên hệ ở mục người đại diện hoặc thông tin liên hệ rõ ràng, không lấy số hồ sơ/phiếu.
</representative_rules>

<disability_type_rules>
Đọc bảng "III. Dạng khuyết tật" trong đơn đề nghị. Chỉ trả mã có ô "Có"/ô tương ứng được đánh dấu.
Nhóm mã:
- kt1 = Khuyết tật vận động.
- kt2 = Khuyết tật nghe, nói.
- kt3 = Khuyết tật nhìn.
- kt4 = Khuyết tật thần kinh, tâm thần.
- kt5 = Khuyết tật trí tuệ.
- kt6 = Khuyết tật khác.
Mục con trả dạng ktX_Y, ví dụ kt5_1, kt5_3.
Không suy luận một mục "Không" chỉ vì ô trống; nếu không có đánh dấu rõ thì không trả mục đó.
Nếu thấy mục con ktX_Y được đánh dấu thì cũng trả nhóm cha ktX trong KhuyetTat_DanhMuc.
OCR bảng có thể bị vỡ dòng/mất ký tự kẻ bảng. Khi một chữ "X" tách riêng xuất hiện trong cùng dòng OCR hoặc ngay sau nội dung của mục con,
trước khi sang mục số tiếp theo, hãy coi đó là dấu chọn "Có" cho mục đó dù không có ký tự "|".
Ví dụ: "5.3 Khó khăn trong việc đọc, viết, tính toán ... so với người X\ncùng tuổi do chậm phát triển trí tuệ"
=> trả KhuyetTat_ChiTiet có "kt5_3" và KhuyetTat_DanhMuc có "kt5".
Chỉ áp dụng với chữ "X" tách riêng/marker rõ; không coi chữ x thường nằm trong từ tiếng Việt là dấu chọn.
</disability_type_rules>

<activity_level_rules>
Đọc bảng "Mức độ thực hiện các hoạt động". MucDo_HoatDong là object key "1".."10".
Giá trị hợp lệ:
- THD = Thực hiện được.
- CTG = Thực hiện được nhưng cần trợ giúp.
- KTHD = Không thực hiện được.
- KXD = Không xác định được.
Chỉ trả dòng có ô được đánh dấu rõ. Không lấy dấu gạch/chữ ở phần hướng dẫn làm đáp án.
Các dòng tương ứng:
1 đi lại; 2 ăn uống; 3 tiểu tiện/đại tiện; 4 vệ sinh cá nhân; 5 mặc/cởi quần áo;
6 nghe và hiểu; 7 diễn đạt ý muốn; 8 làm việc gia đình/lao động/sản xuất; 9 giao tiếp xã hội;
10 đọc, viết, tính toán/kỹ năng học tập khác.
</activity_level_rules>

<output_reminder>
Chỉ trả JSON object trong code block với key "fields". Không giải thích, không markdown ngoài code block.
</output_reminder>"""

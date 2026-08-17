"""Procedure-specific compact prompt rules for "Xác định mức độ khuyết tật"."""

EXTRA_RULES = """<procedure>
Thủ tục: Xác định, xác định lại mức độ khuyết tật và cấp Giấy xác nhận khuyết tật.
Đầu vào thường gồm:
1. ĐƠN ĐỀ NGHỊ XÁC ĐỊNH, XÁC ĐỊNH LẠI MỨC ĐỘ KHUYẾT TẬT VÀ CẤP/CẤP ĐỔI/CẤP LẠI GIẤY XÁC NHẬN KHUYẾT TẬT.
2. CCCD/CMND của chủ hồ sơ/người nộp. Thường người nộp là chủ hồ sơ.
Có thể kèm hồ sơ bệnh án, trích lục khai sinh hoặc giấy tờ y tế khác để bổ sung thông tin người khuyết tật.
</procedure>

<critical_rules>
1. Không trả field UI như data[NktHoTen], data[fullname], data[khuyetTat...]. Chỉ trả các field compact trong schema.
2. Không dùng tên file để kết luận dạng khuyết tật, mức độ hoạt động hoặc nội dung đề nghị; phải dựa trên OCR.
3. Đơn đề nghị là nguồn chính cho Nkt_*, Ndd_*, DeNghi_NoiDung, KhuyetTat_* và MucDo_HoatDong.
4. CCCD/CMND là nguồn chính cho Cccd_* của chủ hồ sơ/người nộp.
5. Hồ sơ bệnh án/trích lục khai sinh chỉ dùng để bổ sung thông tin người khuyết tật còn thiếu hoặc đối chiếu ngày sinh/số định danh; không được thay thế các ô đánh dấu trong đơn đề nghị nếu đơn đã rõ.
</critical_rules>

<source_priority>
- Cccd_*: lấy từ CCCD/CMND. Nếu có mặt trước + mặt sau thì gộp thành một người theo số định danh/họ tên/MRZ.
- Nkt_HoTen/Nkt_NgaySinh/Nkt_GioiTinh/Nkt_ThuongTru/Nkt_NoiOHienNay: ưu tiên mục I "Người được xác định mức độ khuyết tật" trong đơn đề nghị.
- Nkt_SoDinhDanh: ưu tiên mục I trong đơn; nếu đơn bỏ trống thì bổ sung từ hồ sơ bệnh án/trích lục khai sinh đúng người.
- Ndd_*: lấy từ mục II "Người đại diện hợp pháp" trong đơn đề nghị.
- Nếu cùng một thông tin xuất hiện ở nhiều giấy tờ, ưu tiên giấy tờ định danh chính thức cho số định danh/ngày sinh; ưu tiên đơn đề nghị cho nội dung khai và các bảng đánh dấu.
</source_priority>

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
- Bắt buộc cố đọc Cccd_NgayCap và Cccd_NoiCap từ mặt sau CCCD nếu mặt sau có trong OCR.
- Ngày cấp nằm gần nhãn "Ngày, tháng, năm / Date, month, year"; không lấy ngày hết hạn hoặc ngày sinh.
- Nếu OCR thấy "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" thì trả
  Cccd_NoiCap = "Cục Cảnh sát quản lý hành chính về trật tự xã hội".
- Nếu là thẻ Căn cước mới và OCR ghi "BỘ CÔNG AN"/"MINISTRY OF PUBLIC SECURITY" thì trả "Bộ Công an".
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
Đọc bảng "III. Dạng khuyết tật" (hoặc "Thông tin về dạng khuyết tật") trong đơn đề nghị.

**CẤU TRÚC BẢNG**: 4 cột theo thứ tự trái → phải:
1. STT ("1", "1.1", ... "6.3")
2. Các dạng khuyết tật (nội dung mô tả)
3. **Có**   ← cột đánh dấu nếu CÓ dạng khuyết tật này
4. **Không** ← cột đánh dấu nếu KHÔNG có

**ĐẦU RA CHÍNH — KhuyetTat_BangDanhDau**: object, key là SỐ DÒNG in trên đơn, value là:
- "co"    khi dấu X/✓/☑ nằm ở cột "Có";
- "khong" khi dấu nằm ở cột "Không";
- ""      khi dòng để trống HOẶC không chắc chắn dấu thuộc cột nào.
Trả ĐỦ mọi dòng đọc được (37 dòng: 1, 1.1..1.6, 2, 2.1..2.6, 3, 3.1..3.7, 4, 4.1..4.5,
5, 5.1..5.4, 6, 6.1..6.3). Dòng "khong" cũng PHẢI trả — bảng này gần như luôn có rất nhiều "khong".

**HAI LỖI PHẢI TRÁNH (đây là nguyên nhân sai thực tế)**:
1. Rất nhiều dòng có nội dung bắt đầu bằng "Có kết luận của cơ sở y tế cấp tỉnh trở lên về..."
   (các dòng 1.6, 2.6, 3.7, 4.5, 5.4, 6.1, 6.2, 6.3). Chữ "Có" ở đây là NỘI DUNG MÔ TẢ, KHÔNG
   phải ô đánh dấu. Tuyệt đối không vì thấy chữ "Có" trong câu mà kết luận dòng đó = "co".
2. Khi OCR làm phẳng bảng (mất dấu "|"), dòng chỉ còn dạng "3.6 Bị dị tật, biến dạng ở vùng mắt X"
   thì dấu X KHÔNG cho biết nó ở cột "Có" hay "Không" → value phải là "" (không chắc), TUYỆT ĐỐI
   KHÔNG mặc định là "co". Chỉ khi đối chiếu được với các dòng cùng bảng còn giữ cột (hoặc cả bảng
   rõ ràng chỉ đánh vào một cột) mới được kết luận.

**Suy luận nhất quán**:
- Dòng nhóm (1..6) là "co" nếu chính nó đánh cột "Có" HOẶC có ít nhất một dòng con "co".
- Ngược lại, nhóm đánh "Không" thì mọi dòng con của nhóm đó cũng "khong".
- KhuyetTat_DanhMuc / KhuyetTat_ChiTiet chỉ liệt kê các mã "co" (kt1..kt6 / ktX_Y), suy ra từ
  KhuyetTat_BangDanhDau, phải khớp nhau. Mã: 1→kt1, 1.1→kt1_1, 5.3→kt5_3...
  kt1 vận động (6 dòng con), kt2 nghe-nói (6), kt3 nhìn (7), kt4 thần kinh-tâm thần (5),
  kt5 trí tuệ (4), kt6 khác (3).
- KHÔNG coi chữ "x" thường trong từ tiếng Việt là dấu chọn.

**Ví dụ đọc bảng**:
```
| STT | Dạng khuyết tật      | Có | Không |
| 1   | Khuyết tật vận động  |    | X     |
| 1.1 | Mềm nhão...          |    | X     |
| 1.6 | Có kết luận của cơ sở y tế... |  | X |
| 4   | Khuyết tật thần kinh | X  |       |
| 4.1 | Thường ngồi một mình...| X |      |
```
→ KhuyetTat_BangDanhDau = {"1":"khong","1.1":"khong","1.6":"khong","4":"co","4.1":"co", ...}
→ KhuyetTat_DanhMuc = ["kt4"], KhuyetTat_ChiTiet = ["kt4_1"]
→ KHÔNG trả kt1/kt1_1/kt1_6 vì dấu X nằm ở cột "Không" (dòng 1.6 có chữ "Có" trong nội dung).
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

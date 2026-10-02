"""Procedure-specific compact prompt rules for "Đăng ký việc nuôi con nuôi trong nước"."""

EXTRA_RULES = """
<procedure>
Thủ tục: Đăng ký việc nuôi con nuôi trong nước.
Đầu vào thường gồm: Đơn xin nhận con nuôi trong nước (có phần khai người nhận con nuôi cột Ông/Bà,
phần khai người được nhận làm con nuôi, cam đoan); CCCD/căn cước của cha mẹ nuôi; giấy chứng nhận kết
hôn; giấy khám sức khỏe; giấy khai sinh của trẻ; giấy tờ chứng minh chỗ ở, thu nhập (sổ đỏ, bảng lương,
xác nhận thu nhập); có thể kèm CCCD và giấy xác nhận tình trạng hôn nhân của MẸ ĐẺ.
</procedure>

<critical_rules>
1. Trả ONLY các field compact trong schema. Không trả tên ô UI như HoVaTenC, HoVaTenM, HoVaTenCha,
   HoVaTenCN, gdHoTen...
2. Cha nuôi/mẹ nuôi CHỈ là người trong phần "Phần khai về người nhận con nuôi" của đơn (cột Ông →
   AdoptiveFather_*, cột Bà → AdoptiveMother_*) hoặc là chồng/vợ trên giấy chứng nhận kết hôn của họ.
   Người nhận con nuôi đơn thân thì chỉ trả bên tương ứng, bên còn lại để trống.
3. MẸ ĐẺ / CHA ĐẺ trên giấy khai sinh của trẻ (và CCCD, giấy xác nhận tình trạng hôn nhân của họ) KHÔNG
   PHẢI cha mẹ nuôi. TUYỆT ĐỐI không lấy tên, số CCCD, ngày sinh, nơi cư trú của mẹ đẻ/cha đẻ gán vào
   AdoptiveMother_* / AdoptiveFather_*.
4. Giấy khám sức khỏe của trẻ đôi khi ghi "Họ tên bố, mẹ hoặc người giám hộ: Mẹ <tên mẹ nuôi>"; dòng
   này không đổi vai trò ai cả. Giấy chứng nhận quyền sử dụng đất, bảng lương, xác nhận thu nhập chỉ
   là giấy tờ chứng minh điều kiện kinh tế, KHÔNG lấy nơi cư trú từ địa chỉ thửa đất hay địa chỉ công ty.
5. Không lấy các giá trị có sẵn trong HTML tĩnh của cổng nếu không xuất hiện trong OCR giấy tờ.
</critical_rules>

<source_priority_rules>
- Nhân thân cha/mẹ nuôi (họ tên, ngày sinh, số định danh, ngày cấp, nơi cấp): CCCD của chính người đó
  là nguồn chuẩn; khớp với đơn qua họ tên/số. Không có CCCD thì lấy theo đơn, rồi giấy chứng nhận kết hôn.
- Nơi cư trú cha/mẹ nuôi: ƯU TIÊN nơi cư trú ghi trên ĐƠN (địa chỉ hiện tại, đã theo địa giới mới).
  CCCD cũ thường in địa chỉ trước sắp xếp đơn vị hành chính nên chỉ dùng khi đơn không ghi.
- Số điện thoại cha/mẹ nuôi: lấy ở dòng "Điện thoại/email" cột Ông/Bà của đơn.
- Con nuôi: giấy khai sinh là nguồn chuẩn cho họ tên, ngày sinh, giới tính, dân tộc, quốc tịch, số
  định danh, nơi sinh; đơn bổ sung khi giấy khai sinh thiếu. Nơi cư trú con nuôi lấy theo đơn
  ("Nơi cư trú" ở phần người được nhận làm con nuôi); đơn chỉ ghi xã/tỉnh mà giấy khai sinh ghi nơi
  cư trú của mẹ đẻ CÙNG xã thì được lấy thêm thôn/bản/tổ từ đó làm diaChi.
- Child_IdIssueDate/Child_IdIssuePlace: CHỈ khi trẻ có thẻ CCCD/căn cước riêng. Trẻ chỉ có giấy khai
  sinh thì bỏ qua hai field này (không lấy ngày/nơi đăng ký khai sinh).
- Registration_Agency: chép nguyên văn cơ quan ở dòng "Kính gửi" của đơn.
- Child_Category: chép đúng mục "Thuộc đối tượng" nếu đơn có ghi/tích (vd "Trẻ em sống tại gia đình",
  "Trẻ em bị bỏ rơi", "Con riêng", "Cháu ruột"). Đơn để trống thì KHÔNG tự suy, bỏ qua field này.
- AdoptiveFather_Relation/AdoptiveMother_Relation: chỉ trả khi giấy tờ thể hiện rõ quan hệ (cha dượng,
  mẹ kế, chú/cậu/bác ruột, cô/dì/bác ruột). Không rõ thì bỏ qua, Python tự xử lý.
</source_priority_rules>

<living_with_rules>
- Dòng "Hiện đang sống tại gia đình của Ông/Bà" → LivingWith_Type="Gia đình"; LivingWith_FullName chép
  đúng họ tên ghi ở đó (có thể là hai người, giữ nguyên dấu phẩy); LivingWith_Residence là nơi cư trú
  ghi ngay dưới; LivingWith_Phone là "Điện thoại/email liên lạc".
- Dòng "Hiện đang sống tại cơ sở nuôi dưỡng" → LivingWith_Type="Cơ sở nuôi dưỡng" và
  LivingWith_FacilityName là tên cơ sở.
- LivingWith_Gender chỉ trả khi nơi trẻ sống là MỘT người.
</living_with_rules>

<identity_doc_rules>
- Với mỗi CCCD/Căn cước/CMND, cố đọc: họ tên, số định danh, ngày sinh, giới tính, quốc tịch,
  nơi thường trú/cư trú, ngày cấp, nơi cấp.
- CCCD cũ có dòng "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" -> nơi cấp
  "Cục Cảnh sát quản lý hành chính về trật tự xã hội".
- Thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN"/"MINISTRY OF PUBLIC SECURITY" -> nơi cấp "Bộ Công an".
- Nhiều CCCD trong cùng file: ghép mặt sau theo số CCCD trong MRZ/IDVNM, không gán theo thứ tự mơ hồ.
- Giấy chứng nhận kết hôn đời cũ ghi số CMND 9 chữ số: KHÔNG dùng số này làm IdNumber khi đã có CCCD.
</identity_doc_rules>

<address_split_rules>
- Mọi địa chỉ trả object {quocGia,tinh,xa,diaChi}.
- tinh và xa GIỮ loại đơn vị nếu OCR đọc được: "Tỉnh Ninh Bình", "Phường Hoa Lư", "Xã Gia Viễn".
- diaChi chỉ là phần chi tiết như tổ/bản/thôn/số nhà/đường hoặc tên bệnh viện, không lặp xã/tỉnh.
- Ví dụ "Tổ 7, phường Hoa Lư, tỉnh Ninh Bình" -> tinh="Tỉnh Ninh Bình", xa="Phường Hoa Lư", diaChi="Tổ 7".
- Ví dụ nơi sinh "Bệnh viện Đa khoa tỉnh Ninh Bình, phường Hoa Lư, tỉnh Ninh Bình" ->
  tinh="Tỉnh Ninh Bình", xa="Phường Hoa Lư", diaChi="Bệnh viện Đa khoa tỉnh Ninh Bình".
- Địa chỉ có cấp huyện cũ thì bỏ cấp huyện: "Thôn 3, Gia Lạc, Gia Viễn, Ninh Bình" ->
  tinh="Ninh Bình", xa="Gia Lạc", diaChi="Thôn 3".
</address_split_rules>

<output_reminder>
Chỉ trả JSON compact theo schema. Không bịa số điện thoại/email nếu giấy tờ không ghi rõ.
</output_reminder>
"""

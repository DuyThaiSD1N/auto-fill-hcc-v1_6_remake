"""Extraction rules for the combined birth/recognition procedure."""

EXTRA_RULES = """
<procedure>
Thủ tục đăng ký khai sinh kết hợp đăng ký nhận cha, mẹ, con. Một bộ hồ sơ được dùng để điền
hai eForm liên tiếp nhưng lần trích xuất này chỉ trả các SOURCE FACT trong schema chung.
</procedure>

<document_roles>
- Tờ khai đăng ký khai sinh: nguồn chính cho người yêu cầu, tên dự kiến của trẻ, dân tộc/quốc tịch,
  quê quán, cha và mẹ.
- Tờ khai đăng ký nhận cha, mẹ, con: nguồn chính để xác định ai nhận ai, vai trò cha/con và tên
  dự kiến của trẻ.
- Giấy chứng sinh: nguồn chính cho ngày sinh, giới tính, nơi sinh, số giấy chứng sinh và tên người mẹ.
- CCCD/Căn cước: nguồn chính cho số định danh, ngày sinh, GIỚI TÍNH, ngày cấp, nơi cấp và nơi cư trú
  của đúng người mang thẻ. Ngày sinh/giới tính trên thẻ THẮNG tờ khai khi hai nơi ghi khác nhau (chữ
  viết tay hay bị OCR đọc sai); tờ khai chỉ bù khi người đó không có thẻ trong hồ sơ.
- Kết quả ADN/giám định: chứng cứ quan hệ và nguồn đối chiếu tên/số định danh của các bên.
- Giấy chứng tử/quyết định ly hôn: chứng cứ tình trạng hôn nhân, không biến người trên giấy đó
  thành Requester/Father/Mother/Child nếu tờ khai không xác lập vai trò.
</document_roles>

<identity_and_role_rules>
1. Chia người theo nhãn và nội dung tờ khai, không theo thứ tự xuất hiện hoặc tên file.
2. Nếu người yêu cầu cũng là cha thì vẫn trả cả Requester_* và Father_*.
3. Không lấy tên người ký/cán bộ y tế/người đã chết làm thành viên hồ sơ.
4. Mọi số CCCD/định danh là chuỗi và phải giữ số 0 ở đầu.
5. Không trả field UI như HoTenKS, HoTenChaKS, HotenA, hotenB, loaiXacNhan.
</identity_and_role_rules>

<child_name_resolution>
- Child_FullName là tên được đề nghị đăng ký. Ưu tiên tên trên hai tờ khai khi hai tờ khai thống nhất.
- Child_NameOnBirthCertificate luôn ghi riêng đúng tên trên giấy chứng sinh nếu giấy có tên.
- Nếu giấy chứng sinh khác hai tờ khai, không tự sửa Child_FullName theo giấy chứng sinh; giữ cả hai
  field để hệ thống cảnh báo người nộp rà soát.
- ADN chỉ kiểm chứng tên; không thắng hai tờ khai thống nhất về tên dự kiến đăng ký.
</child_name_resolution>

<recognition_rules>
- Recognition_ConfirmationType chỉ được là: "Cha nhận con", "Mẹ nhận con", "Con nhận cha",
  "Con nhận mẹ".
- Người yêu cầu là nam, đề nghị được công nhận là cha/bố của trẻ -> "Cha nhận con".
- Recognition_RegistrationType mặc định "Đăng ký mới" trừ khi giấy tờ nêu rõ đã đăng ký ở nước ngoài.
- Requester_RelationshipToChild chuẩn hóa Bố/Bố ruột thành Cha; Mẹ ruột thành Mẹ.
</recognition_rules>

<marriage_rules>
- Chỉ trả Parents_MarriageRegistrationInfo khi có số/ngày/nơi đăng ký kết hôn rõ ràng.
- Cha mẹ chưa đăng ký kết hôn, giấy chứng tử của chồng cũ hoặc quyết định ly hôn không phải thông tin
  giấy chứng nhận kết hôn của cha mẹ hiện tại; khi đó bỏ field này.
</marriage_rules>

<address_split_rules>
- Địa chỉ trong nước trả object {quocGia,tinh,xa,diaChi}.
- tinh là tỉnh/thành phố; xa là xã/phường/thị trấn; diaChi chỉ là số nhà, đường, tổ, thôn, bản, xóm.
- Loại bỏ cấp huyện/quận/thành phố thuộc tỉnh khỏi object; không dồn cấp huyện vào diaChi.
- Tên đơn vị có thể bắt đầu bằng Nậm, Mường, Pa, Bản; xác định cấp xã theo vị trí và nhãn hành chính,
  không dùng một danh sách tên mẫu cố định.
- Nếu địa chỉ chỉ ghi phường/xã và tỉnh thì diaChi để trống, không chép tên phường/xã vào diaChi.
- Child_BirthPlaceDomestic khác địa chỉ cư trú: diaChi có thể là đầy đủ tên bệnh viện/cơ sở y tế.
</address_split_rules>

<output_contract>
Chỉ trả JSON compact theo schema. Không bịa dữ liệu còn thiếu. Không dùng dữ liệu HTML có sẵn.
</output_contract>
"""


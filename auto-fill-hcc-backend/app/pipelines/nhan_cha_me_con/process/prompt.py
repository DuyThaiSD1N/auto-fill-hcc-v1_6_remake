"""Procedure-specific compact prompt rules for "Đăng ký nhận cha, mẹ, con"."""

EXTRA_RULES = """
<procedure>
Thủ tục: Đăng ký nhận cha, mẹ, con.
Đầu vào thường gồm tờ khai đăng ký nhận cha, mẹ, con; CCCD/Căn cước của các bên;
giấy khai sinh/giấy chứng sinh của con; kết quả xét nghiệm ADN hoặc chứng cứ quan hệ cha/mẹ/con.
</procedure>

<critical_rules>
1. Trả ONLY các field compact trong schema. Không trả field UI như HoVaTenC, HotenA, hotenB,
   loaiXacNhan, noicutruA_TrongNuoc...
2. Tờ khai là nguồn chính để chia 3 vai trò:
   người yêu cầu -> Requester_*;
   phần "Thông tin về cha/mẹ" hoặc "người được công nhận là cha/mẹ" -> Parent_*;
   phần "Thông tin về người con" -> Child_*.
3. Không lấy các giá trị có sẵn trong HTML tĩnh như VŨ ĐÌNH THIẾT, 040203015844, Tỉnh Nghệ An,
   Xã Tam Hợp nếu không xuất hiện trong OCR giấy tờ.
4. Nếu người yêu cầu cũng chính là cha/mẹ trong hồ sơ, vẫn trả cả Requester_* và Parent_*.
5. Không dựa vào tên file để chia vai trò. Dựa vào nhãn trong tờ khai và đối chiếu tên/số định danh.
</critical_rules>

<source_priority_rules>
- Requester_*: ưu tiên phần "Họ, chữ đệm, tên người yêu cầu" trong tờ khai; CCCD chỉ bổ sung
  số định danh, ngày cấp, nơi cấp, ngày sinh/nơi cư trú nếu cùng người.
- Parent_*: ưu tiên phần "Đề nghị cơ quan công nhận người có tên dưới đây" hoặc phần cha/mẹ trên tờ khai.
  CCCD/ADN chỉ bổ sung hoặc kiểm chứng khi cùng tên/số định danh.
- Child_*: ưu tiên phần "là ... của người có tên dưới đây" trên tờ khai và giấy khai sinh/giấy chứng sinh.
  Nếu tờ khai ghi tên/ngày sinh con rõ, không lấy nhầm tên mẹ trên giấy chứng sinh làm Child_*.
- Kết quả ADN là chứng cứ quan hệ. Dùng để kiểm chứng/fallback tên, ngày sinh, số định danh của cha/con
  và Relationship_Claim, nhưng không thay thế tờ khai khi tờ khai rõ vai trò.
- Giấy chứng sinh: tên mẹ trên giấy chứng sinh KHÔNG phải Child_*. Tên con, ngày sinh, giới tính con,
  số GCS, nơi cấp/ngày cấp giấy chứng sinh mới là dữ liệu Child_*.
</source_priority_rules>

<confirmation_type_rules>
- Confirmation_Type chỉ được là một trong 4 option:
  "Cha nhận con", "Mẹ nhận con", "Con nhận cha", "Con nhận mẹ".
- Nếu người yêu cầu/Parent là nam và quan hệ ghi "Bố", "Cha", "cha-con", "bố-con" -> Confirmation_Type="Cha nhận con".
- Nếu người yêu cầu/Parent là nữ và quan hệ ghi "Mẹ", "mẹ-con" -> Confirmation_Type="Mẹ nhận con".
- Nếu quan hệ của người yêu cầu là "Con" và Parent_Gender="Nam" -> Confirmation_Type="Con nhận cha".
- Nếu quan hệ của người yêu cầu là "Con" và Parent_Gender="Nữ" -> Confirmation_Type="Con nhận mẹ".
- Không trả các giá trị khác như "Bố nhận con"; chuẩn hóa "Bố" thành "Cha".
</confirmation_type_rules>

<registration_rules>
- Registration_Agency lấy từ dòng "Kính gửi" nếu có.
- Registration_Type mặc định "Đăng ký mới" nếu tờ khai không ghi đăng ký ở nước ngoài.
- Nếu tờ khai/HTML thể hiện "Ghi vào sổ việc nhận cha, mẹ, con đã được đăng ký tại cơ quan có thẩm quyền của nước ngoài"
  thì trả đúng cụm đó.
- Requester_RelationshipToRecognized lấy từ dòng "Quan hệ với người nhận cha/mẹ/con"; chuẩn hóa "Bố" là "Cha".
- CopyRequest_WantsCopy lấy từ mục "Đề nghị cấp bản sao": tích Có -> "Có", tích Không -> "Không".
- CopyRequest_Quantity lấy số lượng bản nếu ghi rõ, ví dụ "05 bản" -> "5". Nếu không thấy thì bỏ qua.
</registration_rules>

<identity_doc_rules>
- Với mỗi CCCD/Căn cước/CMND, cố đọc: họ tên, số định danh, ngày sinh, giới tính, quốc tịch,
  nơi thường trú/cư trú, ngày cấp, nơi cấp.
- CCCD cũ có dòng "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" -> nơi cấp
  "Cục Cảnh sát quản lý hành chính về trật tự xã hội".
- Thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN"/"MINISTRY OF PUBLIC SECURITY" -> nơi cấp "Bộ Công an".
- Phân biệt loại giấy tờ theo nơi cấp: "Bộ Công an" là Thẻ Căn cước mới; "Cục Cảnh sát QLHC về TTXH"
  là Thẻ căn cước công dân cũ.
- Nếu nhiều CCCD trong cùng file, ghép mặt sau theo số CCCD trong MRZ/IDVNM hoặc số định danh lặp lại
  gần khối ngày cấp; không gán theo thứ tự xuất hiện mơ hồ.
</identity_doc_rules>

<birth_document_rules>
- Nếu giấy ghi "Mã số GCS", "Giấy chứng sinh", "Giấy khai sinh" thì trả Child_BirthDocument*.
- Child_BirthDocumentType là "Giấy chứng sinh" hoặc "Giấy khai sinh" theo giấy tờ.
- Child_BirthDocumentNumber là số GCS/số giấy khai sinh; không đưa số GCS vào Child_IdNumber.
- Nếu con có Thẻ Căn cước/CCCD riêng thì trả Child_IdNumber, Child_IdIssueDate, Child_IdIssuePlace.
  Nếu con chỉ có giấy chứng sinh/khai sinh thì không bịa Child_IdIssueDate/Child_IdIssuePlace.
</birth_document_rules>

<address_split_rules>
- Mọi địa chỉ trong nước trả object {quocGia,tinh,xa,diaChi}.
- tinh và xa nên GIỮ loại đơn vị nếu OCR đọc được: "Tỉnh Lai Châu", "Phường Đoàn Kết", "Xã Phong Thổ".
  Nếu giấy chỉ ghi "Lai Châu" thì trả "Lai Châu"; Python sẽ thêm tiền tố tỉnh khi cần.
- diaChi chỉ là phần chi tiết như tổ/bản/thôn/số nhà/đường, không lặp phường/xã/huyện/tỉnh.
- Nếu địa chỉ dạng "Thôn Tây Sơn, Mường So, Phong Thổ, Lai Châu" thì:
  tinh="Lai Châu", xa="Mường So", diaChi="Thôn Tây Sơn"; bỏ cấp huyện "Phong Thổ".
- Nếu địa chỉ dạng "TDP 4, phường Đoàn Kết, tỉnh Lai Châu" thì:
  tinh="Tỉnh Lai Châu", xa="Phường Đoàn Kết", diaChi="TDP 4".
</address_split_rules>

<output_reminder>
Chỉ trả JSON compact theo schema. Không bịa số điện thoại/email/captcha nếu giấy tờ không ghi rõ.
</output_reminder>
"""


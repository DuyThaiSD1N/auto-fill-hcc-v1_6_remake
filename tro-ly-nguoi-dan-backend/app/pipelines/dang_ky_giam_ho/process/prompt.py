"""Procedure-specific compact prompt rules for "Đăng ký giám hộ"."""

EXTRA_RULES = """
<procedure>
Thủ tục: Đăng ký giám hộ.
Đầu vào thường gồm tờ khai đăng ký giám hộ, CCCD người yêu cầu, CCCD người giám hộ,
giấy khai sinh/người được giám hộ, và có thể có trích xuất CSDL dân cư.
</procedure>

<critical_rules>
1. Trả ONLY các field compact trong schema. Không trả field UI như HoVaTenC, hotenA, hotenB,
   TT_TinhThanhC, lydo, CapBanSao...
2. Phân biệt đúng 3 vai trò theo tờ khai:
   người yêu cầu đăng ký giám hộ -> Requester_*;
   người giám hộ -> Guardian_*;
   người được giám hộ -> Ward_*.
3. Không dựa vào tên file để chia vai trò. Tờ khai là nguồn chính để xác định vai trò.
4. CCCD dùng để bổ sung số định danh, ngày cấp, nơi cấp, ngày sinh/giới tính/nơi cư trú nếu tờ khai thiếu.
5. CSDL dân cư chỉ là nguồn fallback. Nếu CSDL dân cư ghi số CMND cũ nhưng CCCD/tờ khai có số CCCD 12 số,
   ưu tiên số CCCD/tờ khai 12 số.
</critical_rules>

<role_split_rules>
- Người yêu cầu nằm ở phần "I. Thông tin về người yêu cầu đăng ký giám hộ" hoặc nhãn
  "Họ, chữ đệm, tên người yêu cầu".
- Người giám hộ nằm ở phần "II. Thông tin về người giám hộ" hoặc nhãn "người giám hộ".
- Người được giám hộ nằm ở phần "III. Thông tin về người được giám hộ" hoặc nhãn
  "người được giám hộ".
- Trong ví dụ thực tế: Nguyễn Thị Phương Thảo là người yêu cầu; Hà Thị Kiều là người giám hộ;
  Bùi Gia Hoàng Thịnh là người được giám hộ. Đây là ví dụ vai trò, không hard-code tên nếu hồ sơ khác.
</role_split_rules>

<source_priority_rules>
- Requester_*: ưu tiên phần người yêu cầu trên tờ khai; CCCD/CSDL chỉ bổ sung ngày cấp, nơi cấp,
  nơi cư trú hoặc chỉnh họ tên/số định danh nếu cùng người và tờ khai OCR thiếu.
- Guardian_*: ưu tiên phần người giám hộ trong tờ khai; CCCD người giám hộ bổ sung ngày sinh,
  giới tính, số định danh, ngày/nơi cấp, nơi cư trú. Dân tộc nếu CCCD không ghi thì lấy từ tờ khai.
- Ward_*: ưu tiên phần người được giám hộ trong tờ khai và giấy khai sinh. Số định danh cá nhân
  của trẻ lấy từ giấy khai sinh/tờ khai.
- Với dòng "Giấy khai sinh/Giấy tờ tùy thân" của người được giám hộ:
  nếu nội dung ghi "Thẻ CC", "Thẻ CCCD", "Thẻ căn cước", "Căn cước công dân", "CCCD" hoặc "CMND"
  kèm số/ngày cấp/nơi cấp, BẮT BUỘC trả Ward_IdNumber, Ward_IdIssueDate, Ward_IdIssuePlace theo giấy tờ đó.
  Ví dụ "Thẻ CC số: 012320003527, Bộ Công an cấp ngày 16/08/2024" ->
  Ward_IdNumber="012320003527", Ward_IdIssuePlace="Bộ Công an", Ward_IdIssueDate="16/08/2024".
- Nếu dòng "Giấy khai sinh/Giấy tờ tùy thân" chỉ ghi số định danh hoặc giấy khai sinh, không có ngày/nơi cấp
  giấy tờ tùy thân, không được tự coi đó là CCCD có ngày/nơi cấp.
- Ward_ResidenceDomestic ưu tiên nơi cư trú ghi trên tờ khai. Nếu tờ khai thiếu, có thể lấy theo nơi cư trú
  của cha/mẹ trên giấy khai sinh khi rõ ràng cùng địa chỉ của trẻ.
- Nếu phần người được giám hộ trên tờ khai có dòng "Nơi cư trú", BẮT BUỘC trả Ward_ResidenceDomestic.
  Không được bỏ qua chỉ vì giấy khai sinh cũng có nơi cư trú của cha/mẹ.
- Nếu dòng "Giấy khai sinh/Giấy tờ tùy thân" ghi "Giấy khai sinh số ... do ... cấp ngày ..." thì trả:
  Ward_BirthCertificateNumber = số giấy khai sinh, Ward_BirthCertificateIssuePlace = cơ quan cấp,
  Ward_BirthCertificateIssueDate = ngày cấp/ngày đăng ký. Ví dụ "Giấy khai sinh số 234 do UBND phường
  Tân Phong cấp ngày 08/10/2018" -> number="234", issuePlace="UBND phường Tân Phong",
  issueDate="08/10/2018".
- Nếu cùng có cả Ward_Id* của Thẻ CC/CCCD và Ward_BirthCertificate*, vẫn trả cả hai nhóm compact.
  Python sẽ ưu tiên Thẻ CC/CCCD để điền cụm giấy tờ tùy thân của người được giám hộ.
</source_priority_rules>

<cccd_rules>
- Với mỗi CCCD/CMND, cố đọc: họ tên, số định danh, ngày sinh, giới tính, quốc tịch, nơi thường trú/cư trú,
  ngày cấp, nơi cấp.
- CCCD cũ có dòng "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" -> nơi cấp
  "Cục Cảnh sát quản lý hành chính về trật tự xã hội".
- Thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN"/"MINISTRY OF PUBLIC SECURITY" -> nơi cấp "Bộ Công an".
- Phân biệt loại giấy tờ theo nơi cấp: "Bộ Công an" là Thẻ Căn cước mới; "Cục Cảnh sát QLHC về TTXH"
  hoặc biến thể "Cục CS QLHC", "CCSQLHC VTTXH" là Thẻ căn cước công dân cũ.
- Nếu nhiều CCCD trong cùng file, ghép mặt sau theo số CCCD trong MRZ/IDVNM hoặc số định danh lặp lại
  gần khối ngày cấp, không gán theo thứ tự xuất hiện mơ hồ.
</cccd_rules>

<paper_declaration_rules>
- Registration_Agency lấy từ "Kính gửi" nếu có.
- Registration_Reason lấy từ nhãn "Lý do đăng ký giám hộ"; giữ nguyên nội dung chính, không tự viết lại.
- Registration_RelationshipType lấy nếu tờ khai ghi rõ loại/quan hệ giám hộ như giám hộ đương nhiên,
  giám hộ được cử, bà ngoại - cháu...
- CopyRequest_WantsCopy lấy từ mục "Đề nghị cấp bản sao": tích Có -> "Có", tích Không -> "Không".
- CopyRequest_Quantity lấy số lượng bản nếu ghi rõ, ví dụ "05 bản" -> "5". Nếu không thấy số lượng thì bỏ qua.
- CopyRequest_Quantity là field compact riêng; không trả field UI "soluong".
</paper_declaration_rules>

<address_split_rules>
- Mọi địa chỉ trong nước trả object {quocGia,tinh,xa,diaChi}.
- Với thủ tục này, tinh và xa nên GIỮ loại đơn vị nếu OCR đọc được: "Tỉnh Lai Châu", "Phường Tân Phong",
  "Xã Đông Phong". Nếu giấy chỉ ghi "Lai Châu" thì trả "Lai Châu"; Python sẽ thêm tiền tố tỉnh khi cần.
- diaChi chỉ là phần chi tiết như tổ/bản/thôn/số nhà/đường, không lặp phường/xã/huyện/tỉnh.
- Nếu địa chỉ dạng "[chi tiết], phường/xã, thành phố/huyện, tỉnh" thì bỏ cấp huyện/thành phố,
  lấy xa là phần phường/xã và diaChi là phần trước đó.
- Ví dụ "Tổ 1, phường Tân Phong, tỉnh Lai Châu" ->
  tinh="Tỉnh Lai Châu", xa="Phường Tân Phong", diaChi="Tổ 1".
- Ví dụ "Tổ 22, phường Đông Phong, tỉnh Lai Châu" ->
  tinh="Tỉnh Lai Châu", xa="Phường Đông Phong", diaChi="Tổ 22".
</address_split_rules>

<output_reminder>
Chỉ trả JSON compact theo schema. Không trả field UI/default. Không bịa điện thoại/email/captcha vì eForm này không có nguồn giấy tờ rõ.
</output_reminder>
"""

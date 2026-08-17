"""Procedure-specific compact prompt rules for "Đăng ký lại khai tử"."""

EXTRA_RULES = """
<procedure>
Thủ tục: Đăng ký lại khai tử.
Đầu vào thường gồm tờ khai đăng ký khai tử bản giấy/viết tay, CCCD/CMND của người yêu cầu,
CCCD/CMND hoặc giấy tờ liên quan tới người đã chết, và nếu có thì giấy chứng tử/trích lục/giấy tờ
thể hiện việc đăng ký khai tử trước đây.
</procedure>

<critical_rules>
1. Trả ONLY các field compact trong schema. Không trả field UI như HoTen, HoVaTenC, NgayMat,
   loaiDangKy, CapBanSao, coQuanDKTruocDay...
2. Phân biệt vai trò bằng NỘI DUNG OCR, không dựa vào tên file. Tờ khai là nguồn chính để xác định
   "người yêu cầu" và "người được khai tử".
3. Nếu có nhiều CCCD trong cùng hồ sơ, dùng tên/số trong tờ khai và requester_context làm mỏ neo:
   CCCD trùng người yêu cầu → Requester_*; CCCD trùng người chết → Deceased_*.
4. Không bịa thông tin đăng ký khai tử trước đây. Chỉ trả PreviousDeathRegistration_* khi giấy/tờ khai
   ghi rõ số/quyển/ngày/cơ quan đăng ký cũ.
5. Với nơi cư trú của người yêu cầu và người chết, ưu tiên địa chỉ ghi trên tờ khai. CCCD chỉ dùng
   để bổ sung khi tờ khai không ghi nơi cư trú tương ứng.
</critical_rules>

<role_split_rules>
- Trong tờ khai giấy, người yêu cầu nằm ở phần đầu: "Họ, chữ đệm, tên người yêu cầu", "Nơi cư trú",
  "Giấy tờ tùy thân", "Quan hệ với người đã chết".
- Người đã chết nằm sau cụm "Đề nghị cơ quan đăng ký khai tử cho người có tên dưới đây" hoặc phần
  "Thông tin về người được đăng ký khai tử".
- Không lấy chữ ký cuối trang làm họ tên người chết hoặc người yêu cầu nếu phần thông tin chính đã có tên.
- Nếu requester_context khác với người yêu cầu ghi trong tờ khai, vẫn trích Requester_* theo tờ khai;
  requester_context chỉ là mỏ neo phụ để phân biệt CCCD khi tài liệu mơ hồ.
</role_split_rules>

<cccd_rules>
- Với mỗi CCCD/CMND, luôn cố đọc đầy đủ: họ tên, số định danh, ngày sinh, giới tính, quốc tịch,
  nơi thường trú/cư trú, ngày cấp, nơi cấp.
- CCCD cũ có dòng "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → nơi cấp
  "Cục Cảnh sát quản lý hành chính về trật tự xã hội".
- Thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN"/"MINISTRY OF PUBLIC SECURITY" → nơi cấp "Bộ Công an".
- CCCD/CMND của người yêu cầu bổ sung vào Requester_IdNumber, Requester_IdIssueDate,
  Requester_IdIssuePlace nếu khớp người yêu cầu. Chỉ dùng Requester_ResidenceDomestic từ CCCD
  khi tờ khai không có "Nơi cư trú" của người yêu cầu.
- CCCD/CMND của người đã chết bổ sung vào Deceased_IdNumber, Deceased_IdIssueDate,
  Deceased_IdIssuePlace, Deceased_BirthDate, Deceased_Gender. Chỉ dùng Deceased_ResidenceDomestic
  từ CCCD khi tờ khai không có "Nơi cư trú cuối cùng" của người chết.
- Nếu OCR gộp nhiều CCCD, mặt trước có thể xuất hiện trước rồi mặt sau xuất hiện sau. KHÔNG gán ngày cấp
  theo thứ tự gần nhất. Hãy ghép mặt sau theo số CCCD trong dòng MRZ/IDVNM sau khối "Ngày, tháng, năm".
  Ví dụ khối mặt sau có "04/05/2023" và dòng MRZ chứa số 012066002534 thì ngày cấp đó thuộc CCCD
  012066002534, không thuộc CCCD khác.
- Nếu tờ khai viết tay và CCCD có cùng số định danh nhưng họ tên bị OCR lệch nhẹ, ưu tiên họ tên pháp lý
  trên CCCD cho Requester_FullName/Deceased_FullName; tờ khai vẫn là nguồn chính cho quan hệ, nơi chết,
  nguyên nhân chết và thông tin khai tử.
</cccd_rules>

<paper_declaration_rules>
- Tờ khai đăng ký lại khai tử/tờ khai đăng ký khai tử có thể viết tay. OCR có thể nhiễu, nhưng vẫn phải
  suy luận theo vị trí nhãn.
- Requester_Relationship lấy từ nhãn "Quan hệ với người đã chết".
- Requester_ResidenceDomestic lấy từ nhãn "Nơi cư trú" trong phần người yêu cầu trên tờ khai.
  Nếu tờ khai ghi "Nơi cư trú: Tổ dân phố Tân phú nhiều, phường Tân phong, tỉnh Lai Châu" thì trả
  tinh="Lai Châu", xa="Tân Phong", diaChi="Tổ dân phố Tân phú nhiều". Không thay bằng nơi thường trú
  trên CCCD.
- Deceased_BirthDate lấy đủ dd/mm/yyyy nếu có đủ ngày/tháng/năm; nếu thật sự chỉ thấy năm thì trả yyyy.
- Deceased_DeathDate và Deceased_DeathTime lấy từ nhãn "Đã chết vào lúc" hoặc "Tử vong lúc".
  Không lấy ngày lập tờ khai, ngày cấp CCCD, ngày cấp giấy báo tử.
- Deceased_DeathTime trả "HH:mm" nếu đọc được giờ và phút; ví dụ "09 giờ 40 phút" → "09:40".
- Deceased_ResidenceDomestic lấy từ "Nơi cư trú cuối cùng" của người chết.
- Nếu "Nơi cư trú cuối cùng" trên tờ khai có đủ địa chỉ, ưu tiên địa chỉ này hơn nơi thường trú trên
  CCCD của người chết.
- Deceased_DeathPlaceDomestic bắt buộc lấy từ nhãn "Nơi chết"/"Nơi tử vong" khi dòng này có nội dung.
  Không được bỏ qua chỉ vì không có giấy báo tử hoặc vì địa chỉ bị xuống dòng trong OCR.
- Nếu "Nơi chết" ghi "Tổ dân phố 3, phường Tân Phong, tỉnh Lai Châu" thì trả
  tinh="Lai Châu", xa="Tân Phong", diaChi="Tổ dân phố 3".
- Nếu ghi "tại nhà" và cùng địa chỉ cư trú thì trả địa chỉ đó, diaChi có thể thêm "tại nhà" nếu OCR
  thể hiện rõ.
- Deceased_DeathCause lấy từ "Nguyên nhân chết".
</paper_declaration_rules>

<previous_registration_rules>
- PreviousDeathRegistration_* chỉ lấy từ tài liệu ghi nhận việc khai tử đã đăng ký trước đây
  (giấy chứng tử cũ, trích lục khai tử, bản sao khai tử cũ, hoặc mục riêng trong tờ khai đăng ký lại).
- PreviousDeathRegistration_AgencyProvince = tỉnh/thành phố của cơ quan đăng ký trước đây.
- PreviousDeathRegistration_AgencyCommune = xã/phường/thị trấn hoặc tên cơ quan đăng ký trước đây.
- PreviousDeathRegistration_Number = số đăng ký khai tử trước đây. Không lấy số định danh cá nhân,
  số giấy báo tử, số thứ tự mục "(11)", "(14)".
- PreviousDeathRegistration_BookNumber = quyển số đăng ký khai tử trước đây nếu giấy ghi rõ; không tự tính.
- PreviousDeathRegistration_Date = ngày đăng ký khai tử trước đây; không nhầm với ngày chết hoặc ngày lập tờ khai.
</previous_registration_rules>

<death_notice_rules>
- DeathNotice_* dùng cho giấy báo tử/giấy tờ thay giấy báo tử hiện có trong hồ sơ.
- DeathNotice_Number chỉ lấy khi có số giấy báo tử/giấy tờ thay thế thật. Nếu dòng này để trống hoặc chỉ
  toàn dấu chấm thì bỏ qua.
- DeathNotice_IssueAgency và DeathNotice_IssueDate chỉ trả khi đọc được rõ cơ quan/ngày cấp.
</death_notice_rules>

<copy_request_rules>
- Nếu tờ khai mục "Đề nghị cấp bản sao" tích "Có" → CopyRequest_WantsCopy = "Có";
  nếu tích "Không" → "Không".
- CopyRequest_Quantity lấy số lượng bản nếu ghi rõ, ví dụ "01 bản" → "1". Nếu tích Có nhưng không thấy
  số lượng thì bỏ qua quantity, Python sẽ mặc định 1.
</copy_request_rules>

<address_split_rules>
- Mọi địa chỉ trong nước trả object {quocGia,tinh,xa,diaChi}.
- xa = tên phường/xã/thị trấn, bỏ tiền tố "Xã/Phường/Thị trấn/TT".
- diaChi = phần chi tiết trước xã/phường như tổ, bản, thôn, số nhà, đường. Không lặp huyện/tỉnh trong diaChi.
- Nếu địa chỉ dạng cũ 3 cấp "[chi tiết], xã, huyện, tỉnh", bỏ cấp huyện; lấy xã là phần trước huyện.
- Nếu giấy ghi tỉnh Lai Châu và xã/phường Tân Phong, trả tinh="Lai Châu", xa="Tân Phong".
- Nếu địa chỉ có 4 cấp "[chi tiết dòng 1], [xã/phường dòng 2 hoặc cụm kế tiếp], [huyện/thành phố],
  [tỉnh]" thì phần ngay trước huyện/thành phố là xã/phường, phần trước đó mới là diaChi.
  Ví dụ "Tẩn Phủ Nhiêu / Bản Giang, Tam Đường, Lai Châu" → tinh="Lai Châu", xa="Bản Giang",
  diaChi="Tẩn Phủ Nhiêu"; không được trả xa="Tẩn Phủ Nhiêu", diaChi="Bản Giang".
- Với địa chỉ từ tờ khai dạng "Tổ dân phố Tân phú nhiều, phường Tân phong, tỉnh Lai Châu" →
  tinh="Lai Châu", xa="Tân Phong", diaChi="Tổ dân phố Tân phú nhiều".
- OCR có thể xuống dòng giữa tên phường/xã, ví dụ "phường Đoàn\nKết" phải ghép thành
  xa="Đoàn Kết".
</address_split_rules>

<reminder>
Chỉ trả JSON compact theo schema. Không trả field UI/default. Không suy luận số đăng ký khai tử cũ nếu giấy không ghi rõ.
</reminder>
"""


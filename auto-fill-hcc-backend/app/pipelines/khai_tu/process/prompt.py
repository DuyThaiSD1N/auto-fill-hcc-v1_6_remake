"""Procedure-specific compact prompt rules for "Đăng ký khai tử"."""

EXTRA_RULES = """
<task_contract>
- Thủ tục: Đăng ký khai tử. Chỉ trích các dữ kiện được tài liệu OCR ghi rõ; không tự hoàn thiện hồ sơ,
  không suy giá trị từ việc một ô bị bỏ trống và không dùng kiến thức ngoài OCR để bịa dữ liệu.
- Hồ sơ có thể thiếu file CCCD hoặc tờ khai giấy vì người dân nộp trực tuyến, dữ liệu người yêu cầu đã có
  trong requester_context, hoặc giấy báo tử được chia sẻ điện tử. Thiếu loại tài liệu nào thì chỉ bỏ các field
  không có bằng chứng từ loại đó; không coi hồ sơ là sai và không lấy tài liệu khác thay sai mục đích.
- Khi quy tắc chung, mô tả field và quy tắc thủ tục khác nhau, áp dụng quy tắc thủ tục này.
- Tên file chỉ hỗ trợ nhận diện; nội dung OCR và nhãn trên tài liệu mới là bằng chứng.
</task_contract>

<execution_order>
Thực hiện đúng thứ tự trước khi xuất JSON:
1. Nhận diện riêng từng tài liệu.
2. Xác định người yêu cầu và người được đăng ký khai tử.
3. Đọc dữ kiện của từng tài liệu độc lập, không ghép vội các nguồn.
4. Chọn một giá trị cho từng field theo SOURCE_AUTHORITY bên dưới.
5. Tách địa chỉ sau khi đã chọn đúng nguồn; không dùng cách viết địa chỉ để đảo thứ tự nguồn.
6. Chạy VERIFICATION_LOOP rồi mới xuất JSON.
</execution_order>

<document_inventory>
- requester_identity: CCCD/CMND/Căn cước/Hộ chiếu của người yêu cầu.
- deceased_identity: giấy tờ tùy thân của người được đăng ký khai tử.
- paper_declaration: tài liệu có tiêu đề "TỜ KHAI ĐĂNG KÝ KHAI TỬ".
- death_notice: chính tài liệu có tiêu đề "GIẤY BÁO TỬ". Không xếp "TRÍCH LỤC KHAI TỬ" vào nhóm này.
- death_extract: tài liệu có tiêu đề "TRÍCH LỤC KHAI TỬ", "TRÍCH LỤC KHAI TỬ (BẢN SAO)" hoặc số hiệu
  TLKT/TLKT-BS. Đây là kết quả đăng ký hộ tịch, KHÔNG phải Giấy báo tử/nguồn metadata Gbt_*.
- death_event_proof: tài liệu/chứng cứ có thẩm quyền chứng minh sự kiện chết khi không có giấy báo tử,
  thường gặp với người chết đã lâu.
- death_registration_correspondence: công văn của UBND/Công an/cơ quan quản lý về xác minh cư trú,
  mộ phần hoặc phối hợp xử lý hồ sơ, có ghi rõ đang đăng ký khai tử cho một người cụ thể.
- death_place_proof: tài liệu chứng minh nơi chết hoặc nơi phát hiện thi thể khi không xác định được nơi
  cư trú cuối cùng.
- authorization: văn bản ủy quyền hoặc giấy tờ chứng minh quan hệ; không phải nguồn danh tính người chết.
</document_inventory>

<role_routing>
- Nếu có <phan_vai_da_xac_dinh>, dùng nguyên hai vai trong đó; không tự phân vai lại từ OCR.
- Cccd_* chỉ lấy giấy tờ người yêu cầu; NguoiMat_* chỉ lấy người chết hoặc sự kiện chết;
  Gbt_* chỉ là metadata của giấy báo tử/giấy tờ thay thế.
- Nếu chưa có kết quả phân vai: requester_context khớp số định danh trước; với đúng 2 CCCD và đúng 1 thẻ
  khớp requester, thẻ còn lại là người chết kể cả khi thiếu tờ khai/giấy báo tử.
- Trong tờ khai, người trước câu "Đề nghị cơ quan đăng ký khai tử..." là người yêu cầu, người sau câu đó
  là người chết. Không lấy chữ ký cuối trang làm tên người chết.
- Giữ nguyên cụm họ tên, số giấy tờ, ngày sinh, địa chỉ và ngày/nơi cấp theo đúng một người.
- Không lấy người nhận công văn, người ký, vợ/chồng, chủ hộ hoặc CCCD bị đánh dấu không thuộc hai vai.
- ToKhai_QuanHeNguoiYeuCau chỉ lấy từ nhãn "Quan hệ với người đã chết" có giá trị thật.
- Không suy giới tính chỉ từ cách xưng hô "ông/bà"; không chắc thì bỏ field.
</role_routing>

<historical_death_correspondence_case>
Áp dụng khi không có tờ khai, giấy báo tử hoặc giấy tờ tùy thân người chết, nhưng hồ sơ có công văn hành
chính về người chết lâu năm:
- Cụm "tiếp nhận/yêu cầu đăng ký khai tử ... cho ông/bà <HỌ TÊN>" xác định <HỌ TÊN> là người chết.
- Cùng câu/đoạn ghi rõ người đó "sinh năm <yyyy>, chết năm <yyyy>" thì trả đúng độ chính xác yyyy.
- Tên mâu thuẫn do OCR: ưu tiên câu "đăng ký khai tử cho", rồi tiêu đề/về việc, cuối cùng công văn cư trú.
- Tuân thủ ROLE_ROUTING; không lấy CCCD/địa chỉ của người yêu cầu hoặc người khác sang người chết.
- Không suy giới tính, dân tộc, quốc tịch, số định danh, nơi chết hoặc nguyên nhân chết.
  Nơi an táng/mộ phần không mặc nhiên là nơi chết.
- Metadata công văn xác minh KHÔNG phải Gbt_So/Gbt_NgayCap/Gbt_CoQuanCap của giấy báo tử.
- Bỏ trang OCR rác/lặp không tạo thành câu hành chính mạch lạc.
</historical_death_correspondence_case>

<source_authority>
Chỉ chuyển xuống nguồn sau khi nguồn trước không có, để trống, OCR không đọc chắc chắn, hoặc không nói về
đúng người/đúng field. Không thay nguồn ưu tiên chỉ vì nguồn thấp hơn trình bày rõ hoặc có địa chỉ ngắn hơn.

- Danh tính người yêu cầu Cccd_*:
  requester_identity khớp requester_context. Tờ khai chỉ hỗ trợ phân vai, không biến dữ liệu khai tay thành
  dữ liệu "trên CCCD".

- Họ tên, ngày sinh, giới tính, quốc tịch, số định danh người chết:
  1. deceased_identity được xác định chắc chắn;
  2. death_notice/giấy tờ thay thế;
  3. paper_declaration;
  4. death_event_proof hoặc death_registration_correspondence có ghi rõ.

- Ngày cấp và nơi cấp giấy tờ tùy thân người chết:
  1. chính deceased_identity;
  2. dòng giấy tờ tùy thân của người chết trên death_notice hoặc paper_declaration.
  Không suy ngày/nơi cấp từ loại thẻ.

- NguoiMat_DanToc:
  1. nhãn "Dân tộc" trong khối NGƯỜI CHẾT của paper_declaration;
  2. death_notice/giấy chứng tử;
  3. tài liệu khác có nhãn dân tộc rõ ràng;
  4. deceased_identity chỉ khi chính giấy tờ có in dân tộc.
  Mâu thuẫn ngày sinh, số định danh hoặc địa chỉ không làm mất dân tộc đọc rõ từ nguồn ưu tiên.

- NguoiMat_NoiCuTruCuoiCung — NƠI CƯ TRÚ CUỐI CÙNG:
  1. mục "Nơi cư trú cuối cùng" trong paper_declaration;
  2. mục "Nơi cư trú trước khi chết/cuối cùng" trong death_notice/giấy tờ thay thế;
  3. với người chết lâu năm: địa chỉ cư trú gần thời điểm chết nhất mà văn bản có thẩm quyền xác nhận
     trực tiếp thuộc người chết; không dùng địa chỉ người yêu cầu, vợ/chồng hoặc chủ hộ khác;
  4. "Nơi thường trú/Place of residence" trên deceased_identity, chỉ là fallback.

- NguoiMat_NgayMat, NguoiMat_GioMat, NguoiMat_NoiChet, NguoiMat_NguyenNhanMat:
  1. death_notice/giấy tờ thay thế;
  2. death_event_proof hoặc death_place_proof có ghi đúng field;
  3. paper_declaration;
  4. death_registration_correspondence chỉ với dữ kiện chết được ghi trực tiếp.

- Gbt_So, Gbt_CoQuanCap, Gbt_NgayCap:
  CHỈ được lấy từ một trong hai nguồn sau:
  1. nhãn tương ứng trên chính death_notice có tiêu đề "GIẤY BÁO TỬ";
  2. giá trị thật tại dòng dẫn chiếu "Số Giấy báo tử/Giấy tờ thay thế..." trong paper_declaration.
  death_extract/"TRÍCH LỤC KHAI TỬ"/số TLKT hoặc TLKT-BS TUYỆT ĐỐI KHÔNG được dùng cho ba field này,
  kể cả trích lục có nhãn "Số", cơ quan ban hành và ngày lập rõ ràng.

- ToKhai_LoaiDangKy:
  CHỈ nhãn "Loại đăng ký" trên paper_declaration/mẫu hộ tịch điện tử; không có thì bỏ để Python mặc định
  "Đăng ký đúng hạn".

- CopyRequest_WantsCopy và CopyRequest_Quantity:
  CHỈ paper_declaration; không lấy từ giấy báo tử, trích lục, CCCD hoặc tài liệu khác.
</source_authority>

<source_priority_example>
Ví dụ cho NguoiMat_NoiCuTruCuoiCung:
- paper_declaration ghi "Số 12 đường Hoa Mai, phường Bình An, tỉnh Minh Sơn".
- death_notice ghi "Thôn Đông, xã Phú Lộc, tỉnh An Phúc".
- deceased_identity ghi "Số 88 đường Núi Trúc, phường Tân Lập, tỉnh An Phúc".
→ Chọn paper_declaration và trả {"quocGia":"Việt Nam","tinh":"Minh Sơn","xa":"Bình An",
"diaChi":"Số 12 đường Hoa Mai"}; không ghép hoặc thay bằng địa chỉ từ hai nguồn sau.
</source_priority_example>

<identity_document_rules>
- CMND có 9 chữ số; CCCD/Căn cước thường có 12 chữ số. Giữ nguyên số đọc được; MRZ chỉ hỗ trợ khi mặt
  trước mờ và phải khớp đúng người.
- CCCD/Căn cước thông thường KHÔNG in dân tộc. Không suy dân tộc từ họ tên, quê quán, quốc tịch hoặc
  mặc định "Kinh".
- Nơi cấp phải giữ đúng cơ quan tài liệu ghi:
  + CMND ghi "Công an tỉnh/thành phố ..." → giữ nguyên, không đổi thành Cục Cảnh sát.
  + CCCD ghi Cục CSQLHC/Cục Cảnh sát → chuẩn hóa thành
    "Cục Cảnh sát quản lý hành chính về trật tự xã hội".
  + Mặt sau CCCD bị OCR mất tiền tố, chỉ còn "QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI"
    hoặc "QUẢN LÝ HÀNH CHÍNH TRẬT TỰ XÃ HỘI" → vẫn trả đầy đủ
    "Cục Cảnh sát quản lý hành chính về trật tự xã hội".
  + Căn cước mới ghi "BỘ CÔNG AN/MINISTRY OF PUBLIC SECURITY" → "Bộ Công an".
- Ngày cấp lấy từ mặt sau, gần nhãn "Ngày, tháng, năm / Date, month, year". Khi thẻ thuộc người chết,
  định tuyến ngày/nơi cấp vào NguoiMat_NgayCapGiayTo và NguoiMat_NoiCapGiayTo.
</identity_document_rules>

<copy_request_rules>
- CẤP BẢN SAO:
  + Dấu chọn thật gồm ☑, ☒, [x], X hoặc dấu viết tay rõ nằm trong/ngay cạnh đúng ô.
  + ☐ và □ là ô trống. Chữ in sẵn "Có"/"Không" chỉ là nhãn, không phải lựa chọn.
  + Chọn Có → CopyRequest_WantsCopy="Có"; chọn Không → CopyRequest_WantsCopy="Không".
  + Số lượng dương ghi thật → CopyRequest_Quantity là số nguyên bỏ số 0 đầu và đồng thời
    CopyRequest_WantsCopy="Có".
  + "Có ☐, Không ☐" hoặc "Có □, Không □" và "Số lượng: ...... bản" nghĩa là CHƯA KHAI:
    bỏ cả CopyRequest_WantsCopy và CopyRequest_Quantity. Không diễn giải ô trống thành "Không".
  + Dấu chọn không xác định được và số lượng trống → bỏ cả hai field, không đoán.
</copy_request_rules>

<death_event_rules>
- NguoiMat_NgayMat lấy từ "Đã chết vào lúc"/"Tử vong lúc"; không lấy ngày vào viện, ngày ký, ngày lập tờ khai
  hay ngày cấp giấy tờ tùy thân.
- NguoiMat_GioMat trả "HH:mm"; bỏ nếu không chắc cả giờ và phút.
- NguoiMat_NoiChet chỉ lấy từ nhãn "Nơi chết/Nơi tử vong" hoặc death_place_proof rõ ràng.
  Cơ quan/cơ sở cấp giấy báo tử KHÔNG mặc nhiên là nơi chết.
- Gbt_So lấy số hiệu ở nhãn "Số" đầu giấy báo tử; nếu dạng "<số>/<ký hiệu>" thì lấy phần số đầu tiên.
- Gbt_CoQuanCap lấy cơ quan/cơ sở ban hành ở letterhead hoặc khối ký; chỉ lấy tên cơ quan.
- Gbt_NgayCap lấy dòng địa danh + ngày lập/cấp giấy, không nhầm với ngày chết hoặc ngày sinh.
- "TRÍCH LỤC KHAI TỬ" là death_extract: số trích lục, cơ quan ký/cấp và ngày lập/đăng ký trích lục
  không phải số/cơ quan/ngày cấp Giấy báo tử; không xuất vào bất kỳ Gbt_* nào.
- Nếu paper_declaration chỉ in nhãn số/cơ quan/ngày cấp nhưng để trống, toàn dấu chấm hoặc OCR nhiễu thì
  bỏ Gbt_So/Gbt_CoQuanCap/Gbt_NgayCap.
</death_event_rules>

<address_rules>
Áp dụng cho Cccd_NoiCuTru, NguoiMat_NoiCuTruCuoiCung và NguoiMat_NoiChet:
1. Chọn đúng nguồn theo SOURCE_AUTHORITY trước.
2. Từ đúng nguồn đó, tách object {quocGia,tinh,xa,diaChi}.
3. Không ghép số nhà/đường của nguồn này với xã/tỉnh của nguồn khác.

- xa chỉ giữ TÊN đơn vị, bỏ tiền tố Xã/Phường/Thị trấn/TT.
- tinh là tỉnh/thành phố trực thuộc trung ương.
- diaChi chỉ là phần chi tiết như số nhà, đường, tổ, tổ dân phố, khu, thôn, xóm, bản, ấp; không chứa
  xã/phường, huyện/quận hoặc tỉnh.
- Nếu chuỗi dạng "[chi tiết], xã, huyện/quận/thành phố thuộc tỉnh, tỉnh": lấy xã, bỏ cấp huyện khỏi output.
- Ưu tiên địa giới 2 cấp là bước CHUẨN HÓA SAU KHI CHỌN NGUỒN. Không được bỏ paper_declaration để chọn
  CCCD chỉ vì CCCD có cách viết 2 cấp rõ hơn.
- Nếu nguồn đã chọn ghi tên xã mới theo mô hình 2 cấp thì dùng tên mới. Nếu chỉ có địa chỉ cũ, giữ đúng
  chi tiết của nguồn đó để Python remap địa giới; không tự thay bằng một địa chỉ khác người/khác nơi.
</address_rules>

<omission_rules>
- Không bịa field không có bằng chứng.
- Không trả một field chỉ vì nhãn in sẵn nhưng phần giá trị để trống.
- Không dùng mâu thuẫn ở field A làm lý do bỏ field B khi field B có nhãn và giá trị rõ.
- Không trả field UI/default như HoVaTenC, HoTen, NgayMat, gbtLoai, loaiDangKy, CapBanSao, SoLuong,
  loại cư trú, radio trong/ngoài nước hoặc các field giấy tờ duplicate.
- Nếu nguồn không ghi quốc tịch người chết thì bỏ NguoiMat_QuocTich; Python sẽ mặc định Việt Nam.
</omission_rules>

<verification_loop>
Trước khi xuất JSON, kiểm tra lần lượt:
1. Cccd_* và NguoiMat_* có thuộc đúng người không; hai CCCD khác người không bị trộn mặt/field.
2. Tờ khai có "Dân tộc: <giá trị>" trong khối người chết thì output phải có NguoiMat_DanToc.
3. NguoiMat_NoiCuTruCuoiCung có lấy "Nơi cư trú cuối cùng" của tờ khai trước CCCD không.
4. NguoiMat_NoiChet có đến từ nhãn nơi chết, không phải cơ quan cấp giấy báo tử không.
5. Nếu cả Có/Không đều là ô trống và số lượng trống thì output không có hai CopyRequest_*.
6. Nếu số lượng bản sao dương thì output có cả Quantity và WantsCopy="Có".
7. Gbt_So/Gbt_CoQuanCap/Gbt_NgayCap có đúng từ GIẤY BÁO TỬ hoặc đúng mục dẫn chiếu trên tờ khai không;
   nếu chỉ thấy metadata trên TRÍCH LỤC KHAI TỬ thì đã loại bỏ cả ba field chưa.
8. Công văn có câu "đăng ký khai tử ... cho ông/bà <HỌ TÊN>" thì output có NguoiMat_HoTen,
   không lấy người nhận/người yêu cầu/người ký/CCCD không liên quan thay thế.
9. Mỗi NguoiMat_SoDinhDanh/NguoiMat_NgayCapGiayTo/NguoiMat_NoiCapGiayTo/NguoiMat_NoiCuTruCuoiCung
   có nguồn gán trực tiếp cho người chết; nếu đang thuộc người khác thì loại bỏ.
</verification_loop>

"""

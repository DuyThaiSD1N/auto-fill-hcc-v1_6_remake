"""Procedure prompt blocks for compact "Dang ky lai khai sinh" extraction."""

SYSTEM_PROMPT = """
<critical_rules>
Các rule sau không được vi phạm:

1. Trích facts theo VAI TRÒ NGHIỆP VỤ, không theo tên field UI. Ưu tiên nhãn vai trò ghi trên giấy;
   CHỈ suy vai theo giới tính khi giấy KHÔNG ghi rõ (vd khai sinh thiếu tên cha nhưng hồ sơ có CCCD).
2. Output luôn dùng một schema duy nhất: Subject_*, Father_*, Mother_*,
   PreviousRegistration_*. KHÔNG trích người yêu cầu (không có field Requester_*). Không tự tạo field khác.
3. Chỉ trả field chắc chắn trong danh sách FIELD ĐƯỢC PHÉP TRẢ ở trên.
4. Không trả field UI như HoVaTenC, HoTenKS, HoTenChaKS, NamSinhMeKS, QuanHe, LoaiDangKy.
5. Không bịa. Nếu OCR không đủ căn cứ cho một field thì bỏ field đó.
6. KHÔNG lấy chữ trên con dấu/tiêu đề/chức danh ("TƯ PHÁP", "ỦY BAN NHÂN DÂN", "CHỦ TỊCH",
   "PHÓ CHỦ TỊCH", "CỘNG HÒA XÃ HỘI..."...) làm họ tên người. Mục nào bị bỏ trống trên giấy (vd tên cha)
   thì để trống, TUYỆT ĐỐI không điền bằng chữ gần đó.
7. KHI HỒ SƠ CÓ 2 CCCD + TRÍCH LỤC KHAI TỬ (hoặc giấy chứng tử): xác định vai trò theo các bước:
   a) CCCD có tên TRÙNG với người trong trích lục khai tử = người ĐÃ MẤT → đưa vào nhóm cha/mẹ tương ứng
      giới tính, đánh dấu ResidenceDomestic = {"diaChi":"Đã chết"}.
   b) CCCD KHÔNG trùng tên người trong trích lục khai tử = người CÒN SỐNG.
   c) So sánh năm sinh của 2 CCCD còn sống (hoặc CCCD không trùng tên khai tử):
      - CCCD CÓ NĂM SINH TRẺ HƠN (năm lớn hơn) → là NGƯỜI ĐƯỢC ĐĂNG KÝ LẠI KHAI SINH (Subject_*).
        Giới tính của CCCD này → Subject_Gender. Lấy ngày sinh, số CCCD này vào Subject_BirthDate,
        Subject_IdNumber (nếu có trong schema).
      - CCCD CÓ NĂM SINH GIÀ HƠN (năm nhỏ hơn) → là CHA hoặc MẸ theo giới tính CCCD đó
        (Nam → Father_*, Nữ → Mother_*).
   d) Nếu KHÔNG thể phân biệt năm sinh (bằng nhau hoặc không đọc được) → dùng nhãn nghiệp vụ ghi trên
      giấy khai sinh cũ (nếu có) để xác định cha/mẹ/con.
</critical_rules>

<output_contract>
Nội dung JSON trong code block phải có đúng object:
{"fields":{"<field_hop_le>":<value>}}

Ví dụ ĐÚNG:
{"fields":{"Subject_FullName":"NGUYỄN THỊ HOÀI MINH","Subject_BirthDate":"17/11/1976"}}
{"fields":{"Father_FullName":"NGUYỄN ĐỨC NGUYÊN","Father_ResidenceDomestic":{"quocGia":"","tinh":"","xa":"","diaChi":"Đã chết"},"Mother_ResidenceDomestic":{"quocGia":"","tinh":"","xa":"","diaChi":"Đã chết"}}}

Không trả reasoning, không trả nguồn chứng cứ, không trả giải thích sau JSON.
</output_contract>

<document_understanding>
Nhận diện từng tài liệu theo nội dung OCR trước khi trích xuất:

1. Giấy tờ định danh: CCCD/CMND/hộ chiếu, có số định danh, ngày sinh, giới tính, ngày cấp, nơi cấp, nơi cư trú.
2. Tờ khai đăng ký lại khai sinh bản giấy: có các mục người yêu cầu, người được khai sinh, cha, mẹ,
   quan hệ với người được khai sinh, thông tin đăng ký trước đây.
3. Giấy khai sinh cũ/bản sao/trích lục khai sinh: có thông tin khai sinh đã được cơ quan hộ tịch cấp.
4. Bản cam đoan: tài liệu tự khai/tự cam đoan, chỉ dùng để đối chiếu hoặc bổ sung khi nguồn chính thiếu.
5. Giấy tờ thay thế hoặc tài liệu phụ: học bạ, bằng tốt nghiệp, giấy chứng nhận, hồ sơ học tập,
   xác nhận của cơ quan/đơn vị.
</document_understanding>

<role_assignment>
Quy trình gán vai trò:

0. Nếu prompt có khối <phan_vai_da_xac_dinh>, BẮT BUỘC dùng đúng <con>/<me>/<cha> trong khối đó;
   khối nào ghi "Không xác định" thì không trả field của vai ấy.
1. Trích tất cả người xuất hiện trong hồ sơ và gom thông tin chắc chắn thuộc cùng một người.
2. CHỈ gán 3 vai: Subject = người được đăng ký lại khai sinh; Father/Mother = cha/mẹ của Subject.
   KHÔNG trích người yêu cầu (cổng đã điền sẵn).
3. Vai trò phải suy từ nhãn nghiệp vụ như "người được khai sinh", "cha", "mẹ". Giới tính chỉ là tín
   hiệu phụ, không quyết định vai trò (trừ khi giấy khai sinh thiếu tên cha/mẹ mà có CCCD — xem source_priority).
4. Không trộn thông tin của hai người khác nhau: số định danh, ngày cấp, nơi cấp phải đi cùng đúng người đứng tên giấy tờ.
</role_assignment>

<source_priority>
Ưu tiên nguồn theo từng nhóm thông tin:

1. Thông tin định danh của một người: ưu tiên giấy tờ định danh chính thức của chính người đó.
2. Thông tin khai sinh của Subject: ưu tiên giấy khai sinh cũ/bản sao/trích lục nếu có.
3. Nếu không có giấy khai sinh cũ/bản sao/trích lục thì dùng tờ khai đăng ký lại khai sinh bản giấy.
4. Danh tính cha/mẹ: nếu cha/mẹ CÓ CCCD/CMND riêng thì họ tên, số định danh, ngày cấp, nơi cấp,
   nơi cư trú, ngày/năm sinh, dân tộc LẤY TỪ CCCD đó (nguồn sạch), KHÔNG lấy tên từ giấy khai sinh
   (tên trên khai sinh thường nhiễu OCR). Chỉ dùng giấy khai sinh/tờ khai cho cha/mẹ khi người đó
   KHÔNG có CCCD trong hồ sơ.
   Gán vai cha/mẹ: ưu tiên nhãn "cha"/"mẹ" ghi rõ trên giấy. Khi giấy khai sinh KHÔNG ghi tên cha
   (hoặc mẹ) mà hồ sơ CÓ CCCD của người đó (thường tên file "cccd bố"/"cccd mẹ") thì gán CCCD giới
   tính Nam = cha, CCCD giới tính Nữ = mẹ. Chỉ KHÔNG suy theo giới tính khi giấy đã có nhãn cha/mẹ rõ.
5. Bản cam đoan là nguồn phụ. Không dùng bản cam đoan để ghi đè thông tin đã chắc từ CCCD,
   giấy khai sinh cũ hoặc tờ khai bản giấy.
6. Nếu cùng một field xuất hiện ở nhiều nguồn, chọn cách viết rõ và có thẩm quyền hơn cho field đó.
</source_priority>

<mot_nguoi_mot_nguon_dinh_danh>
QUY TẮC TỐI QUAN TRỌNG (áp dụng cho Subject_*, Father_*, Mother_*):
Khi một người CÓ thẻ CCCD/CMND riêng trong hồ sơ thì TẤT CẢ trường của người đó phải lấy ĐỒNG BỘ TỪ
CHÍNH thẻ CCCD đó. TUYỆT ĐỐI không trộn các trường của một người từ nhiều giấy khác nhau (mỗi CCCD là
của MỘT người khác nhau — đừng lấy ngày sinh của người này gán cho người kia).
- CON (Subject): người lớn tự đăng ký lại khai sinh thường nộp CCCD của CHÍNH MÌNH. Khi đó ngày sinh,
  giới tính, quê quán, nơi sinh của con LẤY TỪ CCCD CỦA CON — TUYỆT ĐỐI không lấy ngày sinh/nơi cư trú
  của CHA hay MẸ gán cho con. (Nhận diện CCCD của con qua tên trùng tên con, thường tên file "cccd <tên con>".)
- Giấy khai sinh thường ghi thiếu/nhiễu về cha mẹ (chỉ có năm sinh, thiếu số định danh, thiếu ngày
  cấp, nơi cư trú cũ) → CHỈ dùng cho cha/mẹ khi người đó KHÔNG có CCCD trong hồ sơ.
- CẤM lấy "Số định danh cá nhân" của CON in trên giấy khai sinh làm số định danh của cha/mẹ.
- Ngày sinh cha/mẹ: có CCCD thì lấy ĐỦ ngày/tháng/năm từ CCCD, KHÔNG rút còn mỗi năm.
- Nơi cư trú cha/mẹ: có CCCD thì lấy "Nơi thường trú" trên CCCD, KHÔNG lấy nơi cư trú ghi trên giấy khai sinh.
</mot_nguoi_mot_nguon_dinh_danh>

<field_extraction_rules>
Quy tắc trích các field nghiệp vụ:

1. Subject_BirthDate: phải ưu tiên lấy đủ ngày/tháng/năm nếu tờ khai hoặc giấy khai sinh có đủ.
   Luôn kiểm tra cả phần số và phần "ghi bằng chữ"; phần bằng chữ là nguồn hợp lệ để khôi phục
   ngày/tháng khi phần số OCR bị nhiễu.
   Ví dụ "Ngày mười bẩy/mười bảy, tháng mười một, năm một chín bảy sáu" -> "17/11/1976".
   Chỉ trả "yyyy" khi cả phần số và phần bằng chữ đều không xác định được ngày/tháng.
2. Father_BirthDateOrYear và Mother_BirthDateOrYear: nếu chỉ có năm sinh thì giữ nguyên "yyyy".

3. PreviousRegistration_* (Number/BookNumber/Date/AgencyProvince) là SỐ / QUYỂN SỐ / NGÀY / NƠI
   ĐĂNG KÝ KHAI SINH LẦN ĐẦU
   của Subject. CHỈ lấy từ tài liệu GHI NHẬN VIỆC KHAI SINH CỦA SUBJECT: GIẤY KHAI SINH (cũ) /
   BẢN SAO GIẤY KHAI SINH / TRÍCH LỤC KHAI SINH / TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH (mục "Đã đăng ký
   khai sinh tại").
   TUYỆT ĐỐI KHÔNG lấy từ tài liệu ghi nhận SỰ KIỆN KHÁC — DÙ chúng CŨNG có nhãn "Số:" và "Quyển số:"
   ở đầu giấy và có ngày ở cuối:
   - GIẤY CHỨNG NHẬN KẾT HÔN / GIẤY ĐĂNG KÝ KẾT HÔN (nhận ra vì ghi "Họ và tên chồng" + "Họ và tên vợ"):
     "Số:"/"Quyển số:"/ngày ở đây là của ĐĂNG KÝ KẾT HÔN, KHÔNG phải khai sinh.
   - TRÍCH LỤC KHAI TỬ / GIẤY CHỨNG TỬ (số thường có đuôi "TLKT" như "63/2126/TLKT"): là đăng ký KHAI TỬ.
   - CCCD/CMND.
   CÁCH PHÂN BIỆT theo sự kiện: giấy khai sinh ghi việc MỘT người (Subject) ĐƯỢC SINH RA; giấy kết hôn
   ghi việc HAI người (chồng & vợ) KẾT HÔN; trích lục khai tử ghi việc một người CHẾT.
   Nếu hồ sơ KHÔNG có giấy khai sinh cũ/bản sao/trích lục khai sinh/tờ khai đăng ký lại → BỎ TRỐNG
   TOÀN BỘ PreviousRegistration_* (KHÔNG suy từ giấy chứng nhận kết hôn / khai tử / CCCD).

4. PreviousRegistration_Number = SỐ ĐĂNG KÝ KHAI SINH ở nhãn "Số:" đầu giấy — CHỈ KHI tài liệu đó là GIẤY KHAI
   SINH / TRÍCH LỤC KHAI SINH của Subject. Dạng "NN" (vd 30, 40) hoặc "NN/YYYY" (vd 13/2026, 55/2021).
   KHÔNG lấy "Số:"/"Quyển số:" của giấy kết hôn hay khai tử; KHÔNG lấy số thứ tự mục "(7)", "(10)".
   PreviousRegistration_BookNumber = giá trị ở nhãn "Quyển số" của đúng giấy khai sinh/trích lục/tờ khai;
   chỉ trả khi tài liệu ghi rõ, TUYỆT ĐỐI KHÔNG tính hoặc suy từ PreviousRegistration_Number/ngày đăng ký.
   PreviousRegistration_Date = ngày đăng ký ghi trên chính giấy khai sinh đó (KHÔNG lấy ngày ký giấy
   kết hôn / khai tử).

</field_extraction_rules>

<copy_request_rules>
- CopyRequest_* CHỈ lấy từ mục "Đề nghị cấp bản sao" trên TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH.
- Trước khi trả CopyRequest_*, BẮT BUỘC đọc đúng TIÊU ĐỀ của tài liệu chứa mục này. Tài liệu hợp lệ phải
  có tiêu đề thể hiện đủ "TỜ KHAI" + "ĐĂNG KÝ LẠI" + "KHAI SINH".
- BẮT BUỘC trả CopyRequest_SourceDocumentTitle = tiêu đề nguyên văn đọc được từ OCR của chính tài liệu hợp lệ.
  Không tự tạo tiêu đề theo tên thủ tục đang xử lý.
- "TỜ KHAI CẤP BẢN SAO TRÍCH LỤC HỘ TỊCH" là tài liệu KHÔNG HỢP LỆ cho CopyRequest_* — dù tờ khai đó
  đề nghị cấp trích lục giấy khai sinh, có dòng "Số lượng bản sao yêu cầu cấp", và có đủ số/quyển đăng ký.
  Gặp tài liệu này phải bỏ toàn bộ CopyRequest_SourceDocumentTitle/CopyRequest_WantsCopy/CopyRequest_Quantity.
- Tích/chọn "Có" → CopyRequest_WantsCopy = "Có"; tích/chọn "Không" → "Không".
- CopyRequest_Quantity = số lượng bản sao ghi thật trên tờ khai, trả số nguyên dương. Có số lượng rõ thì
  đồng thời trả CopyRequest_WantsCopy = "Có".
- Không đọc được lựa chọn thì bỏ CopyRequest_WantsCopy; không ghi số lượng thì bỏ CopyRequest_Quantity.
  TUYỆT ĐỐI KHÔNG mặc định "Có" và KHÔNG mặc định số lượng là 1.
</copy_request_rules>

<normalization_rules>
Chuẩn hóa giá trị:

1. Ngày tháng trả dd/mm/yyyy. Ví dụ "6/5/2025" -> "06/05/2025".
2. Nếu chỉ có năm sinh thì trả "yyyy" cho field cho phép năm.
3. Họ tên giữ nguyên hoa/dấu theo OCR đọc được, không tự sửa tên.
4. Nơi cấp CCCD gắn chip: nếu OCR thấy "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI",
   trả "Cục Cảnh sát quản lý hành chính về trật tự xã hội". Nếu là thẻ CĂN CƯỚC mới (tiêu đề "CĂN CƯỚC"/"IDENTITY CARD", cấp từ 01/7/2024) ghi "BỘ CÔNG AN"/"MINISTRY OF PUBLIC SECURITY" thì trả "Bộ Công an".
4b. GIẤY CHỨNG MINH NHÂN DÂN (CMND) — trường hợp giấy tờ ghi "Giấy CMND"/"Chứng minh nhân dân", số CMND
   thường CHỈ ~9 chữ số (khác CCCD 12 số). Với CMND: *_IdIssuePlace là "Công an tỉnh/thành phố ..." GHI
   NGAY TRÊN GIẤY, cùng dòng với số CMND. Ví dụ "Giấy CMND số 045065352, Công an tỉnh Lai Châu cấp ngày
   28/03/2014" → *_IdNumber="045065352", *_IdIssuePlace="Công an tỉnh Lai Châu", *_IdIssueDate="28/03/2014".
   TUYỆT ĐỐI KHÔNG suy "Cục Cảnh sát..." hay "Bộ Công an" cho CMND — nơi cấp CMND là Công an cấp tỉnh.
5. Địa chỉ trong nước hiện hành CHỈ có 2 cấp: XÃ/PHƯỜNG/THỊ TRẤN rồi đến TỈNH/THÀNH PHỐ
   (KHÔNG còn cấp huyện/quận). Trả object {"quocGia":"Việt Nam","tinh":"<tỉnh/thành phố đầy đủ>","xa":"<xã/phường/thị trấn đầy đủ>","diaChi":"<chi tiết>"}.
   BẮT BUỘC viết đầy đủ loại đơn vị hành chính nếu tài liệu thể hiện: "TP."/“TP” → "Thành phố",
   "P."/“P” → "Phường", "X."/“X” → "Xã", "TT."/“TT” → "Thị trấn"; không trả chữ viết tắt.
   Riêng cấp tỉnh Hồ Chí Minh luôn trả "Thành phố Hồ Chí Minh", không trả "TP. Hồ Chí Minh",
   "TP Hồ Chí Minh", "TPHCM" hoặc chỉ "Hồ Chí Minh".
6. Cách tách địa chỉ — áp dụng CẢ khi chuỗi CCCD chỉ NGĂN BẰNG DẤU PHẨY, KHÔNG có nhãn "xã/huyện".
   Địa chỉ CCCD cũ thường theo thứ tự: [chi tiết], xã/phường/thị trấn, HUYỆN/QUẬN, tỉnh. ĐẾM TỪ CUỐI:
   - tinh = phần CUỐI (tỉnh/thành phố trực thuộc trung ương).
   - Phần NGAY TRƯỚC tỉnh nếu là CẤP HUYỆN (huyện/quận/thị xã/thành phố thuộc tỉnh) thì BỎ HẲN —
     không đưa vào xa lẫn diaChi (địa chỉ hiện hành chỉ 2 cấp).
   - xa = tên xã/phường/thị trấn = phần đứng ngay TRƯỚC cấp huyện (nếu địa chỉ đã 2 cấp thì là phần ngay
     trước tỉnh). BẮT BUỘC giữ hoặc mở rộng đầy đủ tiền tố "Xã"/"Phường"/"Thị trấn" khi nguồn xác định
     được loại đơn vị; không bỏ tiền tố và không trả "X.", "P.", "TT.". BẮT BUỘC điền xa khi chuỗi có phần cấp xã.
     LƯU Ý QUAN TRỌNG: tên xã/phường vùng cao CÓ THỂ bắt đầu bằng "Bản", "Nậm", "Mường", "Pa"... (một xã
     có thể tên là "Bản ..."); TUYỆT ĐỐI KHÔNG coi phần đó là chi tiết chỉ vì bắt đầu bằng "Bản" — VỊ TRÍ
     trong chuỗi (áp chót, ngay trước cấp huyện/tỉnh) mới quyết định đó là xã.
   - diaChi = phần CHI TIẾT còn lại ĐỨNG TRƯỚC tên xã (bản/tổ/tổ dân phố/xóm/khu/số nhà/đường).
     Tên xã, huyện/quận, tỉnh KHÔNG được đưa vào diaChi. KHÔNG để xa trống rồi dồn cả xã + huyện vào diaChi.
     Nếu không có phần chi tiết đứng trước xã thì diaChi để TRỐNG.
   - Ví dụ (chung, KHÔNG phải dữ liệu thật):
     "Xóm 3, Bản Mạ, Mường Chà, Điện Biên" -> diaChi="Xóm 3", xa="Bản Mạ", tinh="Điện Biên" (BỎ huyện Mường Chà).
     "Bản Mạ, Mường Chà, Điện Biên" -> xa="Bản Mạ", tinh="Điện Biên", diaChi="" (BỎ huyện Mường Chà).
7. Quốc tịch chỉ trả khi tài liệu ghi rõ hoặc chắc chắn từ mẫu là Việt Nam.
8. Tách từ dính liền: nếu một cụm (địa chỉ chi tiết, tên xã, họ tên) bị viết DÍNH không có dấu cách
   nhưng có chữ HOA đứng giữa cụm (chữ hoa ngay sau chữ thường), tách thành các từ riêng bằng dấu cách.
</normalization_rules>

<ambiguous_or_missing_data>
Xử lý thiếu/mờ/mâu thuẫn:

1. Field không chắc chắn thì bỏ qua, không trả null, không trả chuỗi rỗng.
2. Nếu OCR chỉ đọc được năm sinh thì trả năm sinh cho field cho phép năm.
3. Nếu trong cùng khối cha/mẹ có marker người đó đã chết, marker này override địa chỉ cư trú nhiễu.
   Trả residence object {"quocGia":"","tinh":"","xa":"","diaChi":"Đã chết"} cho người đó.
   Các marker cần hiểu là cùng nghĩa: "đã chết", "da chet", "dã chết", "đã mất", "da mat", "mất",
   "từ trần", "tu tran", OCR nhiễu như "D.d. Chat", "L.D.d. Chat", "L.D. Chat", "(Da Chet)".
4. Nếu marker đã chết nằm ngay sau dòng "Nơi cư trú" hoặc trong phần cha/mẹ trước khi sang khối tiếp theo,
   vẫn trả residence object "Đã chết"; không bỏ field chỉ vì OCR không có dấu hoặc sai chữ.
5. Nếu marker nhiễu như "L.D.d. Chat" xuất hiện trong khối mẹ trước nhãn "Họ, chữ đệm, tên người cha",
   hiểu đó là trạng thái của mẹ và trả Mother_ResidenceDomestic với diaChi "Đã chết".
6. Nếu marker nhiễu như "Da Chet" xuất hiện trong khối cha trước phần "Đã đăng ký khai sinh tại",
   hiểu đó là trạng thái của cha và trả Father_ResidenceDomestic với diaChi "Đã chết".
6b. Marker "đã chết" CHỈ áp cho *_ResidenceDomestic. Khi cha/mẹ đã mất mà hồ sơ có TRÍCH LỤC KHAI TỬ /
   GIẤY CHỨNG TỬ của chính cha/mẹ đó, VẪN PHẢI trích Father_BirthDateOrYear/Mother_BirthDateOrYear
   (năm sinh), Father_Ethnicity/Mother_Ethnicity (dân tộc), Father_Nationality/Mother_Nationality
   (quốc tịch) TỪ trích lục khai tử đó — trích lục khai tử ghi rõ "Ngày, tháng, năm sinh", "Dân tộc",
   "Quốc tịch" của người đã mất. TUYỆT ĐỐI KHÔNG bỏ trống các field này chỉ vì người đó đã chết.
   ĐẶC BIỆT: Khi cha/mẹ đã mất, trích lục khai tử thường ghi dòng "Nơi thường trú", "Nơi cư trú" hoặc
   "Quê quán" của người đó. Hãy trích địa chỉ đó vào Father_HometownFromDeathCert (với cha) hoặc
   Mother_HometownFromDeathCert (với mẹ) theo cùng format object {quocGia, tinh, xa, diaChi}:
   - Ưu tiên "Nơi thường trú"/"Nơi cư trú" (nơi sinh sống trước khi mất).
   - Nếu trích lục không ghi nơi cư trú thì lấy "Quê quán".
   Đây là địa chỉ thay thế để điền vào ô nơi cư trú trên form khi không có CCCD.
   Chỉ trả field này khi cha/mẹ đã mất VÀ có trích lục khai tử/giấy chứng tử trong hồ sơ.
7. Nếu có số giống số đăng ký nhưng không có nhãn nghiệp vụ hoặc không nằm trong khối đăng ký trước đây,
   bỏ PreviousRegistration_Number. ĐẶC BIỆT: "Số:" + "Quyển số:" ở đầu GIẤY CHỨNG NHẬN KẾT HÔN
   (Mẫu TP/HT...) rất giống số/quyển giấy khai sinh — đây là BẪY, TUYỆT ĐỐI KHÔNG lấy cho
   PreviousRegistration_* vì đó là số đăng ký KẾT HÔN.
8. Nếu thông tin định danh của hai người bị lẫn trong OCR, chỉ gán số định danh/ngày cấp/nơi cấp
   khi chắc chắn thuộc đúng người.
</ambiguous_or_missing_data>

<reminder>
Nhắc lại trước khi output:

1. Chỉ trả schema Subject_*, Father_*, Mother_*, PreviousRegistration_*, CopyRequest_* (KHÔNG có Requester_*).
2. Không trả field UI.
3. Không lấy số thứ tự mục như "(7)" làm số đăng ký khai sinh trước đây.
4. Nếu cha/mẹ có marker "Da Chet" hoặc OCR nhiễu tương đương thì trả *_ResidenceDomestic với diaChi "Đã chết".
</reminder>
""".strip()

EXTRA_RULES = SYSTEM_PROMPT

"""Procedure-specific compact prompt rules for civil-status extract copy."""

EXTRA_RULES = """<procedure_context>
Thủ tục: Cấp bản sao Giấy khai sinh, bản sao Trích lục hộ tịch.
Đầu vào thường gồm CCCD/CMND của NGƯỜI YÊU CẦU và một giấy tờ hộ tịch đã đăng ký trước đây:
- Giấy khai sinh / trích lục khai sinh.
- Giấy chứng nhận kết hôn / trích lục kết hôn / trích lục ghi chú kết hôn.
- Trích lục khai tử.
</procedure_context>

<multi_cccd_rules>
- Nyc_* CHỈ là CCCD/CMND của NGƯỜI YÊU CẦU; ChuThe_* CHỈ là giấy tờ của NGƯỜI ĐƯỢC ĐĂNG KÝ.
- Nếu CONTEXT có tên/số định danh người yêu cầu: CCCD khớp tên HOẶC số đó → Nyc_*.
  CONTEXT chỉ để CHỌN thẻ nào là của người yêu cầu, KHÔNG PHẢI nguồn dữ liệu: TUYỆT ĐỐI không
  lấy tên/số trong CONTEXT làm giá trị field và không bịa ngày sinh/ngày cấp/nơi cư trú cho
  người đó. MỌI giá trị trả về phải đọc được trong tài liệu; không có thẻ nào khớp CONTEXT thì
  KHÔNG trả Nyc_* theo CONTEXT.
- THẺ CĂN CƯỚC/CCCD (12 số) VÀ CMND (9 số) CÙNG MỘT HỌ TÊN LÀ MỘT NGƯỜI, không phải hai người:
  CMND là bản CŨ của chính chủ thẻ căn cước và người dân rất hay nộp kèm cả hai. Khi đó CHỈ trả
  thẻ CCCD/Căn cước 12 số vào vai của người đó — số, ngày cấp, nơi cấp, loại giấy tờ đều theo
  CCCD — và BỎ HẲN CMND, TUYỆT ĐỐI không đẩy CMND sang vai còn lại.
- Nếu có đúng 2 CCCD của HAI NGƯỜI KHÁC NHAU và 1 thẻ đã khớp người yêu cầu →
  thẻ còn lại BẮT BUỘC vào ChuThe_*, kể cả hồ sơ không có tờ khai/giấy hộ tịch.
  Luật này KHÔNG áp dụng cho cặp CCCD + CMND cùng một người ở gạch đầu dòng trên.
- Chỉ có 1 CCCD và thẻ đó khớp CONTEXT người yêu cầu → chỉ trả Nyc_*; Python sẽ dùng cùng người đó
  cho cả người yêu cầu và người được đăng ký, KHÔNG trả lặp sang ChuThe_*.
- Chỉ có 1 CCCD, có CONTEXT nhưng thẻ KHÔNG khớp CONTEXT, và hồ sơ không có tờ khai ghi người yêu
  cầu → đó là thẻ của NGƯỜI ĐƯỢC ĐĂNG KÝ → trả vào ChuThe_*, KHÔNG trả Nyc_* (người yêu cầu đã là
  người đăng nhập, cổng tự điền). MỘT thẻ chỉ được trả vào MỘT nhóm: TUYỆT ĐỐI không chép cùng thẻ
  sang cả Nyc_* lẫn ChuThe_*. Ngoại lệ duy nhất là luật ƯU TIÊN CAO bên dưới (giấy hộ tịch nêu
  chủ thể KHÁC thẻ).
- Ghép mặt trước và mặt sau cùng thẻ bằng số CCCD/MRZ và họ tên; không phụ thuộc tên file hoặc thứ tự upload.
- Không có CONTEXT: thẻ khớp HoTich_* là ChuThe_*; thẻ khác chủ thể mới có thể là Nyc_*.
  Chỉ có 1 CCCD và KHÔNG có mỏ neo nào (không tờ khai, không giấy hộ tịch nêu tên/số chủ thể)
  → giữ vào ChuThe_*, không tự coi là người yêu cầu.
- ƯU TIÊN CAO — giấy hộ tịch đã nêu rõ CHỦ THỂ mà thẻ trong hồ sơ là NGƯỜI KHÁC (lệch cả tên lẫn số)
  → thẻ đó BẮT BUỘC vào Nyc_*, KHÔNG được nhét vào ChuThe_*. Áp dụng kể cả khi thẻ KHÔNG khớp CONTEXT
  (người đăng nhập thường là người nộp hộ, khác hẳn người yêu cầu ghi trên hồ sơ giấy).
- TRÍCH LỤC KHAI TỬ: người được đăng ký ĐÃ CHẾT nên KHÔNG BAO GIỜ có thẻ căn cước trong hồ sơ. Mọi
  CCCD/CMND đi kèm trích lục khai tử là của NGƯỜI YÊU CẦU → Nyc_*. Giấy tờ tùy thân của người chết chỉ
  tồn tại dưới dạng dòng chữ IN TRÊN trích lục ("Giấy tờ tùy thân: Giấy CMND số ..."), và nó thuộc về
  HoTich_SoGiayToTuyThan/HoTich_NgayCapGiayToTuyThan/HoTich_NoiCapGiayToTuyThan — TUYỆT ĐỐI không
  chuyển sang ChuThe_*.
  Trang "CĂN CƯỚC ĐIỆN TỬ" (màn hình VNeID có "Số định danh cá nhân", "Họ, chữ đệm và tên / Full name")
  CŨNG LÀ thẻ căn cước, kể cả khi nằm CHUNG MỘT FILE PDF với trích lục → BẮT BUỘC trả vào Nyc_*.
- Có hơn 2 CCCD mà không đủ mỏ neo phân vai → chỉ trả người chắc chắn; không đoán theo tuổi hoặc tên file.
</multi_cccd_rules>

<to_khai_uu_tien>
- TỜ KHAI CẤP BẢN SAO là NGUỒN ƯU TIÊN SỐ 1 cho CẢ HAI người; CCCD/CMND chỉ để BÙ field mà tờ khai
  không có hoặc không đọc được. Không có tờ khai thì mới dùng hoàn toàn CCCD.
- Tờ khai có HAI block người, KHÔNG được trộn:
  + Phần ĐẦU (trước "cho người có tên dưới đây") = NGƯỜI YÊU CẦU → nhóm TkNyc_*:
    TkNyc_HoTen, TkNyc_NoiCuTru, TkNyc_LoaiGiayToTuyThan, TkNyc_SoGiayToTuyThan,
    TkNyc_NgayCapGiayToTuyThan, TkNyc_NoiCapGiayToTuyThan.
    BẮT BUỘC trả các field này khi tờ khai có ghi, KỂ CẢ khi hồ sơ đã có CCCD của người yêu cầu.
  + Block SAU "cho người có tên dưới đây" = NGƯỜI ĐƯỢC ĐĂNG KÝ → nhóm HoTich_* (như mô tả bên dưới).
- Người yêu cầu trên tờ khai có thể KHÁC người đang đăng nhập cổng và KHÁC người được đăng ký; cứ trả
  đúng những gì tờ khai ghi, không tự sửa cho khớp CCCD hay khớp người đăng nhập.
- Người yêu cầu và người được đăng ký có thể là CÙNG một người (tự xin cho mình) — khi đó vẫn trả CẢ
  TkNyc_* lẫn HoTich_*, không gộp, không bỏ bên nào.
- Tờ khai ghi CMND 9 số cũ trong khi hồ sơ có thẻ căn cước 12 số của chính người đó: vẫn trả ĐÚNG
  những gì mỗi nguồn ghi (TkNyc_* theo tờ khai, Nyc_* theo thẻ), KHÔNG tự sửa số bên nào. Python
  chọn giấy tờ để điền và luôn ưu tiên CCCD.
</to_khai_uu_tien>

<source_rules>
- Nyc_* CHỈ lấy từ giấy tờ CĂN CƯỚC/CMND/Hộ chiếu của người yêu cầu (nguồn BÙ THIẾU cho TkNyc_*).
- BẮT BUỘC cố đọc Nyc_NgayCap/Nyc_NoiCap từ mặt sau CCCD. Nơi cấp nằm ngay sau/gần dòng
  "Ngày, tháng, năm / Date, month, year"; nếu OCR thấy "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH
  VỀ TRẬT TỰ XÃ HỘI" thì trả Nyc_NoiCap = "Cục Cảnh sát quản lý hành chính về trật tự xã hội". Nếu là thẻ CĂN CƯỚC mới (tiêu đề "CĂN CƯỚC"/"IDENTITY CARD", thường cấp từ 01/7/2024) ghi "BỘ CÔNG AN"/"MINISTRY OF PUBLIC SECURITY" thì trả Nyc_NoiCap = "Bộ Công an"; KHÔNG mặc định "Cục Cảnh sát..." cho thẻ này.
- Nyc_NoiCuTru và ChuThe_NoiCuTru tách thành object {quocGia,tinh,xa,diaChi}:
  + xa = TÊN xã/phường/thị trấn, CHỈ lấy TÊN (bỏ tiền tố Xã/Phường/Thị trấn); tinh = tỉnh/thành phố;
    diaChi = chi tiết đứng TRƯỚC xã (bản/tổ/tổ dân phố/thôn/xóm/số nhà/đường). KHÔNG đưa xã/huyện/tỉnh vào diaChi.
  + Với MỌI object địa chỉ (Nyc_NoiCuTru, ChuThe_NoiCuTru và HoTich_NoiCuTru), cấp tỉnh Hồ Chí Minh luôn trả
    "Thành phố Hồ Chí Minh"; không trả "TP.HCM", "TP HCM", "TP. Hồ Chí Minh", "TP Hồ Chí Minh",
    "TPHCM", "HCM" hoặc chỉ "Hồ Chí Minh".
  + Ghép các dòng địa chỉ rồi ĐẾM TỪ CUỐI với chuỗi 3 cấp hành chính
    "[chi tiết], [xã], [huyện], [tỉnh]": cuối = tỉnh; áp cuối = huyện và PHẢI BỎ; cụm trước huyện = xã.
    Tên huyện thường không có chữ "huyện" trên CCCD, nhưng vị trí áp cuối vẫn là cấp huyện, KHÔNG được chọn làm xa.
    Vd "Thôn Bình Minh / Tân Phú, Yên Lạc, Vĩnh Phúc" → diaChi="Thôn Bình Minh",
    xa="Tân Phú", tinh="Vĩnh Phúc" (bỏ huyện Yên Lạc).
  + XUỐNG DÒNG trong địa chỉ là một DẤU PHÂN CÁCH như dấu phẩy. Cụm cuối dòng trên và cụm đầu dòng
    dưới là HAI cấp khác nhau, KHÔNG được bỏ cụm nào: MỌI cụm đứng trước xã đều vào diaChi, giữ nguyên
    thứ tự. Vd "Xóm 3, Thôn Đông\\nNghi Hoa, Nghi Lộc, Nghệ An" → diaChi="Xóm 3, Thôn Đông",
    xa="Nghi Hoa", tinh="Nghệ An" (bỏ huyện Nghi Lộc); SAI nếu diaChi chỉ còn "Xóm 3".
- Tách NGUỒN, không gộp trực tiếp:
  + TỜ KHAI CẤP BẢN SAO chỉ sinh ToKhai_*. Mục (4) sinh ToKhai_LoaiSuKien/ToKhai_TenGiayTo;
    block sau "cho người có tên dưới đây" sinh ToKhai_HoTenNguoiDuocCap và các ToKhai_* cá nhân;
    block "Đã đăng ký tại" sinh ToKhai_CoQuanDangKy/ToKhai_So/ToKhai_QuyenSo/ToKhai_NgayDangKy.
  + Giấy hộ tịch đính kèm chỉ sinh HoTich_* của CHÍNH giấy đó. Không sao chép dữ liệu TỜ KHAI vào HoTich_*.
  + Python sẽ dùng ToKhai_LoaiSuKien + ToKhai_HoTenNguoiDuocCap làm khóa
    (LOẠI GIẤY ĐƯỢC YÊU CẦU, NGƯỜI ĐƯỢC CẤP), ưu tiên mọi ToKhai_* không trống và chỉ giữ HoTich_*
    làm nguồn bổ sung khi giấy khớp CẢ loại giấy được yêu cầu VÀ người được cấp.
  + Giấy chỉ đúng loại nhưng sai người, hoặc đúng người nhưng sai loại, KHÔNG PHẢI nguồn bổ sung.
    Không trộn số/quyển/ngày/nơi đăng ký từ giấy khác loại hoặc khác người.
  + ToKhai_LoaiSuKien chỉ phân loại đúng chữ tại mục (4) của TỜ KHAI và phải khớp ToKhai_TenGiayTo;
    tuyệt đối không đổi nó theo loại của bất kỳ giấy hộ tịch đính kèm nào.
  + ToKhai_SoDinhDanh chỉ trả số đúng 12 chữ số. Số 9 chữ số chỉ là CMND: trả vào
    ToKhai_SoGiayToTuyThan, không trả vào ToKhai_SoDinhDanh.
- Chỉ khi KHÔNG có TỜ KHAI CẤP BẢN SAO hoặc mục (4) không ghi loại yêu cầu mới chọn giấy hộ tịch chính
  từ tài liệu đính kèm; nếu có nhiều giấy thì ưu tiên giấy có thông tin đăng ký rõ nhất và nhất quán một chủ thể.
</source_rules>

<giay_uy_quyen_rules>
- GIẤY ỦY QUYỀN (xin cấp bản sao thay người khác) KHÔNG phải giấy tờ hộ tịch: không sinh HoTich_* hay
  ToKhai_CoQuanDangKy/ToKhai_So/ToKhai_QuyenSo/ToKhai_NgayDangKy từ nó.
- Trang CHỨNG THỰC chữ ký ("Số chứng thực: ... quyển số ... SCT", ngày chứng thực, "Trung tâm phục vụ
  hành chính công"/"UBND xã" thực hiện chứng thực) là sổ CHỨNG THỰC, TUYỆT ĐỐI không lấy làm
  HoTich_So/HoTich_QuyenSo/HoTich_NgayDangKy/HoTich_CoQuanDangKy. Hồ sơ không có giấy khai sinh/trích lục/
  tờ khai ghi thông tin đăng ký thì BỎ TRỐNG toàn bộ các field đó.
- Vai trong giấy ủy quyền: BÊN ỦY QUYỀN = người được cấp bản sao → CCCD của bên ủy quyền vào ChuThe_*
  (không vào Nyc_*). BÊN ĐƯỢC ỦY QUYỀN = người yêu cầu → TkNyc_HoTen, TkNyc_SoGiayToTuyThan (số CCCD ghi
  trên giấy, bỏ dấu cách), TkNyc_NoiCuTru lấy từ dòng của bên được ủy quyền; CCCD của bên được ủy quyền
  (nếu có) vào Nyc_*.
- Giấy ủy quyền không có dòng "Quan hệ với người được cấp bản sao" → KHÔNG trả CopyRequest_QuanHe (bên
  ủy quyền và bên được ủy quyền là HAI người, tuyệt đối không trả "Bản thân").
- Loại giấy được ủy quyền xin ("giấy khai sinh bản sao", "trích lục kết hôn"...) sinh ToKhai_LoaiSuKien/
  ToKhai_TenGiayTo như mục (4) của tờ khai.
</giay_uy_quyen_rules>

<supplementary_subject_rules>
- GIẤY CHỨNG SINH và TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ (CT01) là tài liệu BỔ TRỢ xác định
  người được cấp bản sao; không coi chúng là giấy tờ hộ tịch chính và không sinh HoTich_* từ chúng.
- Với GIẤY CHỨNG SINH: NguoiDuocCap_HoTen lấy ở "Dự định đặt tên con";
  NguoiDuocCap_NgaySinh lấy ngày trong "Đã sinh con ... ngày ...";
  NguoiDuocCap_GioiTinh lấy ở "Giới tính của con". Không lấy họ tên, CCCD hoặc địa chỉ của mẹ.
- Với CT01: NguoiDuocCap_HoTen/NguoiDuocCap_NgaySinh/NguoiDuocCap_GioiTinh lấy đúng người
  tại mục 1/2/3. Không lấy chủ hộ ở mục 7, số định danh chủ hộ ở mục 9, người ký hoặc người giám hộ.
- NguoiDuocCap_* chỉ mô tả người ở mục II. Không sao chép Nyc_SoDinhDanh/Nyc_NgayCap/
  Nyc_NoiCap/Nyc_NoiCuTru của người yêu cầu sang người này.
- Nếu đã có GIẤY KHAI SINH/TRÍCH LỤC/giấy tờ hộ tịch chính thì BỎ toàn bộ NguoiDuocCap_*;
  các field này chỉ dùng khi hồ sơ không có giấy tờ hộ tịch chính mà chỉ có GIẤY CHỨNG SINH hoặc CT01.
</supplementary_subject_rules>

<classification_rules>
- Nếu TỜ KHAI mục (4) ghi "Giấy khai sinh"/"Trích lục khai sinh" thì ToKhai_LoaiSuKien = "birth";
  ghi kết hôn thì = "marriage"; ghi khai tử/chứng tử thì = "death". Không trả giá trị này vào HoTich_LoaiSuKien.
- Phân loại từng giấy hộ tịch đính kèm riêng như sau để sinh HoTich_LoaiSuKien của giấy đó.
- Nếu OCR của giấy đang xét có "GIẤY KHAI SINH", "KHAI SANH", "TRÍCH LỤC KHAI SINH", "TRÍCH Y SỔ BỘ",
  "TRÍCH Y SỐ BỘ" hoặc "Sổ hộ tịch việc khai sinh" thì HoTich_LoaiSuKien = "birth".
- Nếu OCR của giấy đang xét có "GIẤY CHỨNG NHẬN KẾT HÔN", "TRÍCH LỤC KẾT HÔN", "TRÍCH LỤC GHI CHÚ KẾT HÔN",
  hoặc các mục vợ/chồng, nơi đăng ký kết hôn, ngày đăng ký kết hôn thì HoTich_LoaiSuKien = "marriage".
- Nếu OCR của giấy đang xét có "TRÍCH LỤC KHAI TỬ", "Sổ hộ tịch việc khai tử", thông tin người chết và ngày đăng ký khai tử
  thì HoTich_LoaiSuKien = "death".
- Chỉ trả HoTich_LoaiSuKien khi chắc chắn loại sự kiện từ OCR. Không đoán từ tên file.
</classification_rules>

<field_rules>
- HoTich_TenGiayTo là tên GIẤY TỜ HỘ TỊCH ĐƯỢC YÊU CẦU CẤP BẢN SAO, ví dụ "Giấy khai sinh",
  "Giấy chứng nhận kết hôn", "Trích lục khai tử". KHÔNG trả "Tờ khai đăng ký lại khai sinh",
  "Tờ khai cấp bản sao trích lục hộ tịch" hoặc "Bản cam đoan" làm HoTich_TenGiayTo.
- HoTich_CoQuanDangKy = CƠ QUAN ĐÃ ĐĂNG KÝ/CẤP giấy tờ hộ tịch trước đây. Phải tuân thủ khóa nguồn
  (loại giấy được yêu cầu, người được cấp) ở <source_rules>. Lấy theo thứ tự ưu tiên:
  + TỜ KHAI: lấy nhãn "Đã đăng ký tại" trong block người được cấp.
  + Nếu tờ khai thiếu, lấy nhãn rõ "Nơi đăng ký", "Cơ quan đăng ký", "Nơi đăng ký kết hôn" trên giấy
    khớp CẢ loại được yêu cầu và người được cấp.
  + GIẤY KHAI SINH / TRÍCH LỤC hộ tịch thường KHÔNG có nhãn trên: lấy cơ quan ghi ở PHẦN ĐẦU văn bản
    (tiêu đề trên cùng, vd "UBND xã/phường/thị trấn ...", "TỈNH ... / UBND ...", "Sở Tư pháp ...")
    HOẶC ở PHẦN KÝ TÊN cuối (chức danh + nơi ký, vd "TM. UBND PHƯỜNG ĐOÀN KẾT - CHỦ TỊCH").
  + Chuẩn hóa "UBND" -> "Ủy ban nhân dân"; ghép kèm cấp tỉnh nếu OCR có
    (vd OCR "TỈNH LAI CHÂU / UBND PHƯỜNG ĐOÀN KẾT" -> "Ủy ban nhân dân phường Đoàn Kết, tỉnh Lai Châu").
  + Chỉ để trống khi giấy tờ THẬT SỰ không ghi bất kỳ cơ quan đăng ký/cấp nào.
- HoTich_So ưu tiên số trong block "Đã đăng ký tại" của TỜ KHAI. Nếu thiếu, chỉ lấy khi giấy hộ tịch
  khớp CẢ loại được yêu cầu và người được cấp có dòng "Số:", "Số đăng ký" hoặc "Số trích lục".
  Dòng "Số: <mã>/<năm>" ở phần đầu, ngay trước hoặc sát tiêu đề "GIẤY KHAI SINH"/"TRÍCH LỤC..."
  chính là HoTich_So; giữ nguyên toàn bộ mã và năm. Không lấy số CCCD, số định danh, số mục,
  số trang hoặc số điện thoại làm HoTich_So.
- HoTich_SoDinhDanh CHỈ là dãy SỐ ghi ở dòng "Số định danh cá nhân" của CHÍNH người được đăng ký
  (12 chữ số; giấy hộ tịch cũ có thể ghi CMND 9 chữ số). Dòng "Số: <mã>/<năm>" ở đầu giấy là
  HoTich_So: TUYỆT ĐỐI không dùng nó (hay quyển số, số hồ sơ, số trang) làm HoTich_SoDinhDanh hoặc
  HoTich_SoGiayToTuyThan. Giấy in nhãn "Số định danh cá nhân:" nhưng BỎ TRỐNG (chưa cấp số cho trẻ)
  thì BỎ HẲN HoTich_SoDinhDanh — để cổng trống, không suy ra từ bất kỳ số nào khác.
- HoTich_QuyenSo chỉ trả khi OCR có nhãn "Quyển số"/"Quyển" VÀ có giá trị thật ngay sau nhãn.
  Nếu tờ khai ghi "Giấy khai sinh số: 123, quyển số ngày 01/02/1990" thì quyển số đang để TRỐNG:
  HoTich_So="123" và BỎ HoTich_QuyenSo. "Số bộ 123", "sổ bộ số 123", "bộ số 123", "số hiệu 123"
  đều là số đăng ký/số hiệu, KHÔNG phải quyển số.
- HoTich_NgayDangKy = NGÀY ĐĂNG KÝ sự kiện hộ tịch trước đây, dd/mm/yyyy. ƯU TIÊN NGUỒN:
  + (1) TỜ KHAI cấp bản sao: ở cụm "Đã đăng ký tại: <cơ quan> ngày D tháng M năm Y số ...".
    Ngày NGAY SAU "Đã đăng ký tại ..." (và trước "số ...") CHÍNH LÀ ngày đăng ký — KHÔNG cần có nhãn
    "Ngày đăng ký" rõ ràng. Xuống dòng không cắt block; dấu chấm sau D/M là đường chấm của mẫu.
    Có đủ D, M, Y thì BẮT BUỘC trả dd/mm/yyyy, KHÔNG coi là field không chắc chắn.
  + (2) GIẤY KHAI SINH / TRÍCH LỤC: nhãn "Ngày, tháng, năm đăng ký", "Ngày đăng ký", "Đăng ký ngày",
    hoặc ngày ở phần dưới/nơi ký.
  BẮT BUỘC điền nếu OCR đọc được ngày; TUYỆT ĐỐI không bỏ trống chỉ vì thiếu nhãn "Ngày đăng ký".
- Với giấy khai sinh, HoTich_HoTenNguoiDuocDangKy là người được khai sinh (CON).
- HoTich_NoiCuTru trên TỜ KHAI CẤP BẢN SAO: BẮT BUỘC lấy dòng "Nơi cư trú" trong block sau
  "cho người có tên dưới đây"; không lấy dòng "Nơi cư trú" của người yêu cầu ở phần đầu.
  Nyc_NoiCuTru (người yêu cầu) và HoTich_NoiCuTru (người được đăng ký) là HAI field ĐỘC LẬP: phải
  trả CẢ HAI, kể cả khi địa chỉ TRÙNG NHAU (ca tự làm) — KHÔNG gộp, KHÔNG bỏ một trong hai, KHÔNG
  mượn cái này chắp cái kia (hai người có thể ở khác địa chỉ).
- Có thể lấy HoTich_NoiCuTru từ chính GIẤY HỘ TỊCH của chủ thể (giấy khai sinh, trích lục khai tử,
  giấy đăng ký kết hôn) khi giấy đó ghi nơi cư trú của người được đăng ký.
- Phân biệt NGUỒN giấy tờ tùy thân trong hồ sơ khai sinh:
  + TỜ KHAI CẤP BẢN SAO TRÍCH LỤC HỘ TỊCH có HAI BLOCK ĐỘC LẬP. Block 1 từ
    "Họ, chữ đệm, tên người yêu cầu" đến trước "Quan hệ với người được cấp" chỉ sinh Nyc_*.
    Block 2 bắt đầu sau "cho người có tên dưới đây"; dòng "Giấy tờ tùy thân" trong block 2 là của
    CHÍNH người được cấp và phải sinh HoTich_*. Xác định vai trò theo VỊ TRÍ BLOCK, không yêu cầu họ tên
    hai block phải khớp vì OCR có thể đọc sai một vài ký tự trong tên.
  + TUYỆT ĐỐI KHÔNG KHỬ TRÙNG giữa Nyc_* và HoTich_*. Nếu block 1 và block 2 ghi cùng số giấy tờ,
    cùng ngày cấp, cùng cơ quan cấp (trường hợp người yêu cầu tự xin bản sao cho mình), vẫn BẮT BUỘC
    trả CẢ HAI nhóm field độc lập. Không được chỉ trả Nyc_* rồi bỏ HoTich_* vì giá trị giống nhau.
  + Nếu block 2 có dạng "Giấy tờ tùy thân: <12 chữ số> do <cơ quan công an> cấp ngày <ngày>" nhưng
    không ghi rõ chữ "CCCD"/"Căn cước", vẫn BẮT BUỘC trả đủ HoTich_LoaiGiayToTuyThan,
    HoTich_SoGiayToTuyThan, HoTich_NgayCapGiayToTuyThan, HoTich_NoiCapGiayToTuyThan và trả:
    HoTich_SoDinhDanh = <12 chữ số>, HoTich_LoaiGiayToTuyThan = "Căn cước",
    HoTich_SoGiayToTuyThan = <12 chữ số>, HoTich_NgayCapGiayToTuyThan = <ngày>,
    HoTich_NoiCapGiayToTuyThan = <cơ quan>. Thiếu tên loại không được làm mất số/ngày/nơi cấp.
  + Chỉ lấy các giá trị trên khi block 2 THỰC SỰ có dòng "Giấy tờ tùy thân". Nếu block 2 để trống,
    không tự sao chép Nyc_* từ block 1 sang HoTich_* chỉ vì đây có thể là trường hợp tự yêu cầu.
  + Trên GIẤY KHAI SINH, dòng "Giấy tờ tùy thân: Thẻ căn cước/CCCD số ... cấp ngày ... tại ..."
  là của NGƯỜI ĐI KHAI SINH (cha/mẹ/người thân), KHÔNG PHẢI của con. TUYỆT ĐỐI KHÔNG lấy dòng này vào
  HoTich_LoaiGiayToTuyThan/HoTich_SoGiayToTuyThan/HoTich_NgayCapGiayToTuyThan/HoTich_NoiCapGiayToTuyThan
  . Nếu GIẤY KHAI SINH chỉ có "Số định danh cá nhân" của trẻ và không có CCCD/Căn cước của chính trẻ
    thì chỉ trả HoTich_SoDinhDanh; bỏ các field GiayToTuyThan.
- Giấy kết hôn có HAI chủ thể (vợ và chồng). Chọn MỘT người làm HoTich_* theo thứ tự sau:
  + ƯU TIÊN 1: NGƯỜI ĐANG ĐĂNG NHẬP ở <requester_context> nếu người đó CHÍNH LÀ vợ hoặc chồng ghi
    trên giấy (trùng họ tên hoặc trùng số giấy tờ tùy thân). Trích lục là của cuộc hôn nhân của chính
    họ, nên họ vừa là người yêu cầu vừa là NGƯỜI ĐƯỢC ĐĂNG KÝ — lấy CHÍNH họ làm HoTich_*, kể cả khi
    họ là vợ/bên nữ, và trả CopyRequest_QuanHe = "Bản thân".
  + ƯU TIÊN 2: người mà TỜ KHAI (ToKhai_HoTenNguoiDuocCap) nêu tên, nếu hồ sơ có tờ khai cấp bản sao.
  + MẶC ĐỊNH: người chồng/bên nam.
  Chỉ trả MỘT người, không trả cả hai. Bên còn lại đưa vào HoTich_NguoiThan với quanHe "vợ"/"chồng"
  đúng vai của họ so với người đã chọn.
- Với giấy kết hôn, HoTich_NgaySinh/HoTich_DanToc/HoTich_QuocTich/HoTich_SoDinhDanh/HoTich_NoiCuTru
  cũng lấy theo ĐÚNG người đã chọn ở trên khi OCR có nhiều cột vợ/chồng — không trộn cột.
- Với giấy kết hôn, HoTich_GioiTinh suy ra từ vai của người đã chọn ("Nam" cho chồng/bên nam, "Nữ"
  cho vợ/bên nữ) kể cả giấy không in nhãn giới tính riêng.
- Với giấy kết hôn, nếu block của NGƯỜI ĐÃ CHỌN có "Giấy tờ tùy thân: Thẻ căn cước công dân số ...
  cấp ngày ..." thì trả:
  HoTich_LoaiGiayToTuyThan = "Căn cước công dân",
  HoTich_SoGiayToTuyThan = số CCCD trong block người đã chọn,
  HoTich_SoDinhDanh = cùng số đó nếu không có số định danh riêng,
  HoTich_NgayCapGiayToTuyThan = ngày cấp trong block người đã chọn,
  HoTich_NoiCapGiayToTuyThan = cơ quan cấp trong block người đã chọn.
- Với giấy kết hôn có hai giấy tờ tùy thân, KHÔNG lấy số/ngày cấp/cơ quan cấp của người còn lại —
  số của người còn lại chỉ đi vào soGiayTo trong HoTich_NguoiThan.
- Với giấy kết hôn, cố tách HoTich_NoiCuTru của người đã chọn thành object:
  {"quocGia":"Việt Nam","tinh":"<tỉnh/thành>","xa":"<xã/phường/thị trấn>","diaChi":"<số nhà/tổ/thôn/xóm/bản/tổ dân phố>"}.
  Ví dụ OCR "Tổ dân phố Cư Nhà La, phường Đoàn Kết, tỉnh Lai Châu" thì trả
  tinh="Lai Châu", xa="Đoàn Kết", diaChi="Tổ dân phố Cư Nhà La".
  ĐẾM TỪ CUỐI khi địa chỉ liệt kê không nhãn (dạng cũ 3 cấp "[chi tiết], xã, HUYỆN, tỉnh"): cuối = tỉnh;
  phần NGAY TRƯỚC tỉnh nếu là CẤP HUYỆN (huyện/quận/thị xã/thành phố thuộc tỉnh) thì BỎ HẲN; phần trước đó
  = xã. Tên xã/phường vùng cao CÓ THỂ bắt đầu bằng "Bản"/"Nậm"/"Mường"/"Pa" — KHÔNG coi là chi tiết chỉ vì
  bắt đầu bằng "Bản", VỊ TRÍ (áp chót, trước cấp huyện/tỉnh) mới quyết định là xã. BẮT BUỘC điền xa.
- Dân tộc "Mông" thì GIỮ NGUYÊN HoTich_DanToc = "Mông" (KHÔNG đổi thành "Mông (Hmông)"). CHỈ khi OCR ghi
  biến thể HMÔNG có chữ "H" đứng đầu ("Hmông", "H'Mông", "H Mông", "HMỗng" hoặc tương tự) thì mới chuẩn hóa
  HoTich_DanToc = "Mông (Hmông)".
- Với mọi dân tộc khác, giữ nguyên tên đọc được vào HoTich_DanToc; không tự trả "Khác".
  Python sẽ chọn "Khác" và điền ô dân tộc khác nếu tên đó không có trong danh sách của biểu mẫu.
- Với giấy khai tử, HoTich_HoTenNguoiDuocDangKy là người chết/người được khai tử.
- Với TRÍCH LỤC KHAI TỬ, nếu block NGƯỜI CHẾT ghi
  "Giấy tờ tùy thân: <loại> số <số>, <cơ quan> cấp ngày <ngày>" thì BẮT BUỘC trả đủ:
  HoTich_LoaiGiayToTuyThan, HoTich_SoGiayToTuyThan, HoTich_NgayCapGiayToTuyThan,
  HoTich_NoiCapGiayToTuyThan. Dòng này phải nằm trong block người chết, trước thông tin chết hoặc trước
  nhãn "Họ, chữ đệm, tên người đi khai tử". KHÔNG lấy số/ngày/nơi cấp ở block NGƯỜI ĐI KHAI TỬ.
- Chuẩn hóa "Cục CS QLHC về trật tự xã hội", "Cục CSQLHC về TTXH" thành
  "Cục Cảnh sát quản lý hành chính về trật tự xã hội".
</field_rules>

<copy_request_rules>
- CopyRequest_Quantity lấy từ mục yêu cầu cấp bản sao trên TỜ KHAI hoặc tài liệu yêu cầu, nhận các nhãn:
  "Đề nghị cấp bản sao", "Số lượng bản sao yêu cầu cấp", "Số lượng".
- Nếu có số lượng nguyên dương ghi rõ, ví dụ "Số lượng: 10 bản", BẮT BUỘC trả
  CopyRequest_Quantity=10, kể cả dòng "Có, Không" không thể hiện rõ ô nào được tích.
- Chỉ đọc cụm chữ số ngay trước từ "bản". Dấu chấm/phẩy xen giữa các chữ số là nhiễu OCR/đường chấm:
  ghép các chữ số, bỏ số 0 ở đầu và trả số nguyên dương; KHÔNG diễn giải thành số thập phân.
- Form điện tử thủ tục này KHÔNG có field Có/Không cấp bản sao: không trả CopyRequest_WantsCopy,
  không trả CapBanSao. Không có số lượng thì bỏ CopyRequest_Quantity; không tự mặc định số lượng 3.
- CopyRequest_QuanHe lấy từ TỜ KHAI dòng "Quan hệ với người được cấp bản sao Giấy khai sinh/
  Trích lục hộ tịch: ..." — trả ĐÚNG chữ ghi sau dấu hai chấm (vd "Mẹ đẻ", "Bố đẻ", "Bản thân",
  "Con đẻ", "Vợ", "Chồng", "Ông", "Bà"). Không có dòng này thì bỏ qua, KHÔNG suy diễn từ việc người
  yêu cầu có trùng người được cấp bản sao hay không — Python tự đối chiếu số định danh/họ tên giữa
  mục I và mục II để tick "Bản thân"/"Khác" khi field này trống.
  TRÍCH LỤC KHAI TỬ: người được đăng ký đã chết, TUYỆT ĐỐI không trả CopyRequest_QuanHe = "Bản thân".
- HoTich_NguoiThan: BẮT BUỘC trả khi CHÍNH giấy hộ tịch có dòng ghi tên người thân của người được
  đăng ký (giấy khai sinh ghi cha/mẹ; giấy chứng nhận kết hôn ghi vợ/chồng; trích lục khai tử ghi
  người thân nếu có). Mỗi dòng là một object {quanHe, hoTen, soGiayTo}: quanHe lấy ĐÚNG vai ở nhãn
  của dòng đó, hoTen là họ tên đầy đủ, soGiayTo chỉ điền khi giấy ghi số giấy tờ của chính người đó.
  Đây là nguồn để Python tick ô "Quan hệ với người được cấp bản sao" khi hồ sơ không có tờ khai:
  thiếu nó thì ô quan hệ bị tick "Khác" dù giấy đã ghi rõ vai. Nhãn nào giấy không ghi vai thì BỎ
  dòng đó, KHÔNG suy quan hệ từ họ, tuổi hay địa chỉ.
</copy_request_rules>

<chu_the_giay_to_tuy_than_rules>
- Trong hồ sơ CÓ THỂ có CCCD/Thẻ căn cước/CMND/Hộ chiếu của CHÍNH người được đăng ký (chủ thể hộ tịch),
  tách biệt với CCCD của người yêu cầu. Vd con đã có thẻ căn cước dù giấy khai sinh cũ.
- QUY TẮC KHỚP: khi có HoTich_*, ChuThe_* lấy từ thẻ trùng HoTich_SoDinhDanh hoặc
  HoTich_HoTenNguoiDuocDangKy. Khi không có HoTich_* nhưng có đúng 2 thẻ và 1 thẻ khớp CONTEXT người
  yêu cầu, thẻ còn lại là ChuThe_*.
- ChuThe_* và Nyc_* phải là HAI thẻ KHÁC nhau; ChuThe_SoDinhDanh trùng Nyc_SoDinhDanh là sai.
- ChuThe_* là nguồn BÙ THIẾU cho người được đăng ký: tờ khai/giấy hộ tịch (HoTich_*) ghi gì thì ưu
  tiên cái đó, thẻ căn cước chỉ điền vào chỗ tờ khai bỏ trống.
- Khi khớp đúng, BẮT BUỘC điền TỪ CHÍNH THẺ CỦA CHỦ THỂ:
  ChuThe_HoTen, ChuThe_SoDinhDanh, ChuThe_NgaySinh, ChuThe_GioiTinh, ChuThe_QuocTich,
  ChuThe_LoaiGiayTo, ChuThe_NgayCap, ChuThe_NoiCap và ChuThe_NoiCuTru.
- TUYỆT ĐỐI KHÔNG lấy ChuThe_* từ dòng "Giấy tờ tùy thân" trên giấy khai sinh (đó là người đi khai sinh).
- Nếu KHÔNG có thẻ riêng khớp chủ thể thì bỏ trống toàn bộ ChuThe_*.
</chu_the_giay_to_tuy_than_rules>

<do_not_return>
- Không trả trực tiếp field UI NYC_QuanHe; quan hệ chỉ trả qua CopyRequest_QuanHe (mapper tự tick radio).
- Không trả field UI/default như NYC_HoVaTen, HoVaTenC, NDK_HoVaTen, HoSo_LoaiYeuCau,
  HoSo_TenGiayTo, HoSo_So, HoSo_QuyenSo, HoSo_NgayCapSo, PhuongThucNhanKQ.
- Không trả loại giấy tờ, loại cư trú, quốc tịch mặc định, radio trong/ngoài nước, hoặc số giấy tờ duplicate.
- Nếu giấy tờ hộ tịch không ghi quốc tịch người được đăng ký thì bỏ qua HoTich_QuocTich; Python sẽ mặc định Việt Nam khi cần.
- Mỗi nhóm Nyc_*, ChuThe_* và HoTich_* phải lấy đúng người/đúng tài liệu; không trộn dữ liệu giữa hai thẻ.
</do_not_return>"""
  
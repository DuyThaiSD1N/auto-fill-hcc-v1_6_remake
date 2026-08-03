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
- Nếu có đúng 2 CCCD khác nhau và 1 thẻ đã khớp người yêu cầu → thẻ còn lại BẮT BUỘC vào ChuThe_*,
  kể cả hồ sơ không có tờ khai/giấy hộ tịch.
- Chỉ có 1 CCCD và thẻ đó khớp CONTEXT người yêu cầu → chỉ trả Nyc_*; Python sẽ dùng cùng người đó
  cho cả người yêu cầu và người được đăng ký, KHÔNG trả lặp sang ChuThe_*.
- Ghép mặt trước và mặt sau cùng thẻ bằng số CCCD/MRZ và họ tên; không phụ thuộc tên file hoặc thứ tự upload.
- Không có CONTEXT: thẻ khớp HoTich_* là ChuThe_*; thẻ khác chủ thể mới có thể là Nyc_*.
  Chỉ có 1 CCCD và không có mỏ neo nào → giữ vào ChuThe_*, không tự coi là người yêu cầu.
- Có hơn 2 CCCD mà không đủ mỏ neo phân vai → chỉ trả người chắc chắn; không đoán theo tuổi hoặc tên file.
</multi_cccd_rules>

<source_rules>
- Nyc_* CHỈ lấy từ giấy tờ CĂN CƯỚC/CMND/Hộ chiếu của người yêu cầu.
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
- HoTich_* không lấy từ CCCD. Nếu KHÔNG có giấy tờ hộ tịch gốc, TỜ KHAI CẤP BẢN SAO là nguồn chính:
  lấy thông tin người được cấp trong block sau "cho người có tên dưới đây", cùng cơ quan đăng ký, số,
  quyển số, ngày đăng ký và số lượng bản sao. Không lấy block người yêu cầu hoặc người ký.
- Nếu hồ sơ có GIẤY KHAI SINH cũ/TRÍCH LỤC/KHAI SANH/TRÍCH Y SỔ BỘ thì ưu tiên tài liệu hộ tịch gốc
  cho dữ liệu sự kiện; tờ khai chỉ bổ sung field còn thiếu và không được đổi HoTich_TenGiayTo thành tên tờ khai.
- Nếu OCR có nhiều tài liệu hộ tịch chính, ưu tiên tài liệu có thông tin đăng ký rõ nhất.
</source_rules>

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
- Nếu OCR có "GIẤY KHAI SINH", "KHAI SANH", "TRÍCH LỤC KHAI SINH", "TRÍCH Y SỔ BỘ",
  "TRÍCH Y SỐ BỘ" hoặc "Sổ hộ tịch việc khai sinh" thì HoTich_LoaiSuKien = "birth".
- Nếu OCR có "GIẤY CHỨNG NHẬN KẾT HÔN", "TRÍCH LỤC KẾT HÔN", "TRÍCH LỤC GHI CHÚ KẾT HÔN",
  hoặc các mục vợ/chồng, nơi đăng ký kết hôn, ngày đăng ký kết hôn thì HoTich_LoaiSuKien = "marriage".
- Nếu OCR có "TRÍCH LỤC KHAI TỬ", "Sổ hộ tịch việc khai tử", thông tin người chết và ngày đăng ký khai tử
  thì HoTich_LoaiSuKien = "death".
- Chỉ trả HoTich_LoaiSuKien khi chắc chắn loại sự kiện từ OCR. Không đoán từ tên file.
</classification_rules>

<field_rules>
- HoTich_TenGiayTo là tên GIẤY TỜ HỘ TỊCH ĐƯỢC YÊU CẦU CẤP BẢN SAO, ví dụ "Giấy khai sinh",
  "Giấy chứng nhận kết hôn", "Trích lục khai tử". KHÔNG trả "Tờ khai đăng ký lại khai sinh",
  "Tờ khai cấp bản sao trích lục hộ tịch" hoặc "Bản cam đoan" làm HoTich_TenGiayTo.
- HoTich_CoQuanDangKy = CƠ QUAN ĐÃ ĐĂNG KÝ/CẤP giấy tờ hộ tịch trước đây. BẮT BUỘC điền nếu giấy tờ CÓ
  cơ quan này, TUYỆT ĐỐI KHÔNG bỏ trống. Lấy theo thứ tự ưu tiên:
  + Nếu có nhãn rõ "Nơi đăng ký", "Cơ quan đăng ký", "Nơi đăng ký kết hôn" thì lấy giá trị đó.
  + GIẤY KHAI SINH / TRÍCH LỤC hộ tịch thường KHÔNG có nhãn trên: lấy cơ quan ghi ở PHẦN ĐẦU văn bản
    (tiêu đề trên cùng, vd "UBND xã/phường/thị trấn ...", "TỈNH ... / UBND ...", "Sở Tư pháp ...")
    HOẶC ở PHẦN KÝ TÊN cuối (chức danh + nơi ký, vd "TM. UBND PHƯỜNG ĐOÀN KẾT - CHỦ TỊCH").
  + Chuẩn hóa "UBND" -> "Ủy ban nhân dân"; ghép kèm cấp tỉnh nếu OCR có
    (vd OCR "TỈNH LAI CHÂU / UBND PHƯỜNG ĐOÀN KẾT" -> "Ủy ban nhân dân phường Đoàn Kết, tỉnh Lai Châu").
  + Chỉ để trống khi giấy tờ THẬT SỰ không ghi bất kỳ cơ quan đăng ký/cấp nào.
- HoTich_So BẮT BUỘC trả khi giấy tờ hộ tịch chính có dòng "Số:", "Số đăng ký" hoặc "Số trích lục".
  Dòng "Số: <mã>/<năm>" ở phần đầu, ngay trước hoặc sát tiêu đề "GIẤY KHAI SINH"/"TRÍCH LỤC..."
  chính là HoTich_So; giữ nguyên toàn bộ mã và năm. Không lấy số CCCD, số định danh, số mục,
  số trang hoặc số điện thoại làm HoTich_So.
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
- Phân biệt NGUỒN giấy tờ tùy thân trong hồ sơ khai sinh:
  + Trên TỜ KHAI CẤP BẢN SAO, dòng "Giấy tờ tùy thân" nằm trong block sau "cho người có tên dưới đây"
    là của CHÍNH người được cấp. BẮT BUỘC trả đủ HoTich_LoaiGiayToTuyThan,
    HoTich_SoGiayToTuyThan, HoTich_NgayCapGiayToTuyThan, HoTich_NoiCapGiayToTuyThan nếu OCR có.
  + Trên GIẤY KHAI SINH, dòng "Giấy tờ tùy thân: Thẻ căn cước/CCCD số ... cấp ngày ... tại ..."
  là của NGƯỜI ĐI KHAI SINH (cha/mẹ/người thân), KHÔNG PHẢI của con. TUYỆT ĐỐI KHÔNG lấy dòng này vào
  HoTich_LoaiGiayToTuyThan/HoTich_SoGiayToTuyThan/HoTich_NgayCapGiayToTuyThan/HoTich_NoiCapGiayToTuyThan
  . Nếu GIẤY KHAI SINH chỉ có "Số định danh cá nhân" của trẻ và không có CCCD/Căn cước của chính trẻ
    thì chỉ trả HoTich_SoDinhDanh; bỏ các field GiayToTuyThan.
- Với giấy kết hôn, HoTich_HoTenNguoiDuocDangKy BẮT BUỘC lấy người chồng/bên nam.
  Không trả cả hai người, không lấy họ tên vợ/bên nữ.
- Với giấy kết hôn, HoTich_NgaySinh/HoTich_DanToc/HoTich_QuocTich/HoTich_SoDinhDanh/HoTich_NoiCuTru
  cũng lấy theo người chồng/bên nam nếu OCR có nhiều cột vợ/chồng.
- Với giấy kết hôn, HoTich_GioiTinh của người chồng/bên nam là "Nam" kể cả giấy không in nhãn giới tính riêng.
- Với giấy kết hôn, nếu block chồng/bên nam có "Giấy tờ tùy thân: Thẻ căn cước công dân số ... cấp ngày ..."
  thì trả:
  HoTich_LoaiGiayToTuyThan = "Căn cước công dân",
  HoTich_SoGiayToTuyThan = số CCCD trong block chồng/bên nam,
  HoTich_SoDinhDanh = cùng số đó nếu không có số định danh riêng,
  HoTich_NgayCapGiayToTuyThan = ngày cấp trong block chồng/bên nam,
  HoTich_NoiCapGiayToTuyThan = cơ quan cấp trong block chồng/bên nam.
- Với giấy kết hôn có hai giấy tờ tùy thân, không lấy số/ngày cấp/cơ quan cấp của vợ/bên nữ.
- Với giấy kết hôn, cố tách HoTich_NoiCuTru của người chồng/bên nam thành object:
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
</copy_request_rules>

<chu_the_giay_to_tuy_than_rules>
- Trong hồ sơ CÓ THỂ có CCCD/Thẻ căn cước/CMND/Hộ chiếu của CHÍNH người được đăng ký (chủ thể hộ tịch),
  tách biệt với CCCD của người yêu cầu. Vd con đã có thẻ căn cước dù giấy khai sinh cũ.
- QUY TẮC KHỚP: khi có HoTich_*, ChuThe_* lấy từ thẻ trùng HoTich_SoDinhDanh hoặc
  HoTich_HoTenNguoiDuocDangKy. Khi không có HoTich_* nhưng có đúng 2 thẻ và 1 thẻ khớp CONTEXT người
  yêu cầu, thẻ còn lại là ChuThe_*.
- ChuThe_* và Nyc_* phải là HAI thẻ KHÁC nhau; ChuThe_SoDinhDanh trùng Nyc_SoDinhDanh là sai.
- Khi khớp đúng, BẮT BUỘC điền TỪ CHÍNH THẺ CỦA CHỦ THỂ:
  ChuThe_HoTen, ChuThe_SoDinhDanh, ChuThe_NgaySinh, ChuThe_GioiTinh, ChuThe_QuocTich,
  ChuThe_LoaiGiayTo, ChuThe_NgayCap, ChuThe_NoiCap và ChuThe_NoiCuTru.
- TUYỆT ĐỐI KHÔNG lấy ChuThe_* từ dòng "Giấy tờ tùy thân" trên giấy khai sinh (đó là người đi khai sinh).
- Nếu KHÔNG có thẻ riêng khớp chủ thể thì bỏ trống toàn bộ ChuThe_*.
</chu_the_giay_to_tuy_than_rules>

<do_not_return>
- Không trả field quan hệ NYC_QuanHe; thủ tục này để người dùng tự chọn.
- Không trả field UI/default như NYC_HoVaTen, HoVaTenC, NDK_HoVaTen, HoSo_LoaiYeuCau,
  HoSo_TenGiayTo, HoSo_So, HoSo_QuyenSo, HoSo_NgayCapSo, PhuongThucNhanKQ.
- Không trả loại giấy tờ, loại cư trú, quốc tịch mặc định, radio trong/ngoài nước, hoặc số giấy tờ duplicate.
- Nếu giấy tờ hộ tịch không ghi quốc tịch người được đăng ký thì bỏ qua HoTich_QuocTich; Python sẽ mặc định Việt Nam khi cần.
- Mỗi nhóm Nyc_*, ChuThe_* và HoTich_* phải lấy đúng người/đúng tài liệu; không trộn dữ liệu giữa hai thẻ.
</do_not_return>"""

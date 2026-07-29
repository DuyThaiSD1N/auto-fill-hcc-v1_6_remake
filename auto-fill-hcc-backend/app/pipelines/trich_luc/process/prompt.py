"""Procedure-specific compact prompt rules for civil-status extract copy."""

EXTRA_RULES = """<procedure_context>
Thủ tục: Cấp bản sao Giấy khai sinh, bản sao Trích lục hộ tịch.
Đầu vào thường gồm CCCD/CMND của NGƯỜI YÊU CẦU và một giấy tờ hộ tịch đã đăng ký trước đây:
- Giấy khai sinh / trích lục khai sinh.
- Giấy chứng nhận kết hôn / trích lục kết hôn / trích lục ghi chú kết hôn.
- Trích lục khai tử.
</procedure_context>

<multi_cccd_rules>
- Có thể upload NHIỀU CCCD (vd mẹ đi làm bản sao khai sinh cho con → có cả CCCD mẹ lẫn con).
- Nếu phần CONTEXT cung cấp tên/số định danh NGƯỜI YÊU CẦU (đăng nhập): Cccd_* CHỈ lấy từ CCCD TRÙNG
  tên/số định danh đó. CCCD KHÔNG trùng là của người khác → TUYỆT ĐỐI không đưa vào Cccd_*.
- Nếu KHÔNG có thông tin người yêu cầu: người yêu cầu là người trên CCCD KHÔNG PHẢI chủ thể của giấy
  hộ tịch (người được khai sinh/kết hôn/khai tử). Nếu chỉ có 1 CCCD và trùng chủ thể → đó là tự làm cho mình.
- Người yêu cầu (Cccd_*) thường KHÁC người được đăng ký (HoTich_*): đừng mặc định lấy CCCD của chủ thể.
</multi_cccd_rules>

<source_rules>
- Cccd_* CHỈ lấy từ giấy tờ CĂN CƯỚC/CMND/Hộ chiếu của người yêu cầu.
- BẮT BUỘC cố đọc Cccd_NgayCap/Cccd_NoiCap từ mặt sau CCCD. Nơi cấp nằm ngay sau/gần dòng
  "Ngày, tháng, năm / Date, month, year"; nếu OCR thấy "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH
  VỀ TRẬT TỰ XÃ HỘI" thì trả Cccd_NoiCap = "Cục Cảnh sát quản lý hành chính về trật tự xã hội". Nếu là thẻ CĂN CƯỚC mới (tiêu đề "CĂN CƯỚC"/"IDENTITY CARD", thường cấp từ 01/7/2024) ghi "BỘ CÔNG AN"/"MINISTRY OF PUBLIC SECURITY" thì trả Cccd_NoiCap = "Bộ Công an"; KHÔNG mặc định "Cục Cảnh sát..." cho thẻ này.
- Cccd_NoiCuTru (nơi thường trú trên CCCD) tách thành object {quocGia,tinh,xa,diaChi}:
  + xa = TÊN xã/phường/thị trấn, CHỈ lấy TÊN (bỏ tiền tố Xã/Phường/Thị trấn); tinh = tỉnh/thành phố;
    diaChi = chi tiết đứng TRƯỚC xã (bản/tổ/tổ dân phố/thôn/xóm/số nhà/đường). KHÔNG đưa xã/huyện/tỉnh vào diaChi.
  + ĐẾM TỪ CUỐI khi liệt kê không nhãn ("[chi tiết], xã, HUYỆN, tỉnh"): cuối = tỉnh; phần trước tỉnh nếu là
    CẤP HUYỆN (huyện/quận/thị xã/thành phố thuộc tỉnh) thì BỎ HẲN; phần trước đó = xã. BẮT BUỘC điền xa khi CCCD có.
    Vd "Nơi cư trú: Bản Seo Pả / Lản Nhì Thàng, Phong Thổ, Lai Châu" → diaChi="Bản Seo Pả", xa="Lản Nhì Thàng",
    tinh="Lai Châu" (bỏ huyện Phong Thổ).
- HoTich_* CHỈ lấy từ tài liệu hộ tịch chính, không lấy từ CCCD.
- FEW-SHOT địa danh hiện hành: nguồn ghi "10/4 Đường A, phường 3, Đà Lạt, Lâm Đồng" →
  HoTich_NoiCuTru={"quocGia":"Việt Nam","tinh":"Lâm Đồng","xa":"Phường Xuân Hương","diaChi":"10/4 Đường A"}.
  BẮT BUỘC đổi Phường 3 thuộc Đà Lạt thành "Phường Xuân Hương"; không trả "Phường 3"/"phường 3".
- TỜ KHAI yêu cầu cấp bản sao/đăng ký lại KHÔNG phải giấy tờ hộ tịch chính. Nếu hồ sơ có GIẤY KHAI SINH
  cũ/TRÍCH LỤC/KHAI SANH/TRÍCH Y SỔ BỘ thì ưu tiên tài liệu hộ tịch gốc đó cho HoTich_TenGiayTo,
  HoTich_HoTenNguoiDuocDangKy, HoTich_So và dữ liệu sự kiện. Tờ khai chỉ bổ sung field còn thiếu như
  cơ quan/ngày đăng ký; không được đổi HoTich_TenGiayTo thành tên tờ khai.
- Nếu OCR có nhiều tài liệu hộ tịch chính, ưu tiên tài liệu có thông tin đăng ký rõ nhất.
</source_rules>

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
- HoTich_So lấy từ số giấy tờ/số đăng ký gần tiêu đề hoặc nhãn "Số:", "Số đăng ký", "Số trích lục".
  Không lấy số CCCD, số mục, số trang, số điện thoại làm HoTich_So.
- HoTich_QuyenSo chỉ trả khi OCR có nhãn "Quyển số"/"Quyển" VÀ có giá trị thật ngay sau nhãn.
  Nếu tờ khai ghi "Giấy khai sinh số: 123, quyển số ngày 01/02/1990" thì quyển số đang để TRỐNG:
  HoTich_So="123" và BỎ HoTich_QuyenSo. "Số bộ 123", "sổ bộ số 123", "bộ số 123", "số hiệu 123"
  đều là số đăng ký/số hiệu, KHÔNG phải quyển số.
- HoTich_NgayDangKy = NGÀY ĐĂNG KÝ sự kiện hộ tịch trước đây, dd/mm/yyyy. ƯU TIÊN NGUỒN:
  + (1) TỜ KHAI cấp bản sao: ở cụm "Đã đăng ký tại: <cơ quan> ngày D tháng M năm Y số ...".
    Ngày NGAY SAU "Đã đăng ký tại ..." (và trước "số ...") CHÍNH LÀ ngày đăng ký — KHÔNG cần có nhãn
    "Ngày đăng ký" rõ ràng.
  + (2) GIẤY KHAI SINH / TRÍCH LỤC: nhãn "Ngày, tháng, năm đăng ký", "Ngày đăng ký", "Đăng ký ngày",
    hoặc ngày ở phần dưới/nơi ký.
  BẮT BUỘC điền nếu OCR đọc được ngày; TUYỆT ĐỐI không bỏ trống chỉ vì thiếu nhãn "Ngày đăng ký".
- Với giấy khai sinh, HoTich_HoTenNguoiDuocDangKy là người được khai sinh (CON).
- GIẤY TỜ TÙY THÂN trên GIẤY KHAI SINH: dòng "Giấy tờ tùy thân: Thẻ căn cước/CCCD số ... cấp ngày ... tại ..."
  là của NGƯỜI ĐI KHAI SINH (cha/mẹ/người thân), KHÔNG PHẢI của con. TUYỆT ĐỐI KHÔNG lấy dòng này vào
  HoTich_LoaiGiayToTuyThan/HoTich_SoGiayToTuyThan/HoTich_NgayCapGiayToTuyThan/HoTich_NoiCapGiayToTuyThan
  (các field đó CHỈ dùng cho GIẤY KẾT HÔN — giấy tờ chồng/vợ). Con được khai sinh KHÔNG có CCCD, CHỈ có
  "Số định danh cá nhân" → HoTich_SoDinhDanh = số định danh của CON. Bỏ trống các field GiayToTuyThan cho khai sinh.
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
- Với giấy khai tử, HoTich_HoTenNguoiDuocDangKy là người chết/người được khai tử.
</field_rules>

<copy_request_rules>
- CopyRequest_Quantity lấy từ mục yêu cầu cấp bản sao trên TỜ KHAI hoặc tài liệu yêu cầu, nhận các nhãn:
  "Đề nghị cấp bản sao", "Số lượng bản sao yêu cầu cấp", "Số lượng".
- Nếu có số lượng nguyên dương ghi rõ, ví dụ "Số lượng: 10 bản", BẮT BUỘC trả
  CopyRequest_Quantity=10, kể cả dòng "Có, Không" không thể hiện rõ ô nào được tích.
- Form điện tử thủ tục này KHÔNG có field Có/Không cấp bản sao: không trả CopyRequest_WantsCopy,
  không trả CapBanSao. Không có số lượng thì bỏ CopyRequest_Quantity; không tự mặc định số lượng 3.
</copy_request_rules>

<chu_the_giay_to_tuy_than_rules>
- Trong hồ sơ CÓ THỂ có CCCD/Thẻ căn cước/CMND/Hộ chiếu của CHÍNH người được đăng ký (chủ thể hộ tịch),
  tách biệt với CCCD của người yêu cầu. Vd con đã có thẻ căn cước dù giấy khai sinh cũ.
- QUY TẮC KHỚP BẮT BUỘC: ChuThe_* CHỈ lấy từ thẻ mà SỐ trên thẻ TRÙNG HoTich_SoDinhDanh
  (hoặc HỌ TÊN trên thẻ TRÙNG HoTich_HoTenNguoiDuocDangKy). Nghĩa là ChuThe_SoGiayToTuyThan PHẢI BẰNG
  HoTich_SoDinhDanh. Thẻ nào KHÔNG khớp chủ thể (vd thẻ của mẹ/người yêu cầu) TUYỆT ĐỐI KHÔNG đưa vào ChuThe_*.
- ChuThe_* và Cccd_* PHẢI là HAI thẻ KHÁC nhau: Cccd_* = thẻ người yêu cầu; ChuThe_* = thẻ chủ thể.
  KHÔNG BAO GIỜ dùng chung một thẻ cho cả hai. Nếu ChuThe_SoGiayToTuyThan trùng Cccd_SoDinhDanh là SAI.
- Khi khớp đúng, BẮT BUỘC điền TỪ CHÍNH THẺ CỦA CHỦ THỂ:
  ChuThe_LoaiGiayToTuyThan, ChuThe_SoGiayToTuyThan (= HoTich_SoDinhDanh),
  ChuThe_NgayCapGiayToTuyThan (ngày cấp trên thẻ đó, dd/mm/yyyy),
  ChuThe_NoiCapGiayToTuyThan (nơi cấp: thẻ CĂN CƯỚC mới "BỘ CÔNG AN" → "Bộ Công an";
  CCCD cũ "CỤC TRƯỞNG CỤC CẢNH SÁT..." → "Cục Cảnh sát quản lý hành chính về trật tự xã hội").
- TUYỆT ĐỐI KHÔNG lấy ChuThe_* từ dòng "Giấy tờ tùy thân" trên giấy khai sinh (đó là người đi khai sinh).
- Nếu KHÔNG có thẻ riêng khớp chủ thể thì bỏ trống toàn bộ ChuThe_*.
- VÍ DỤ ĐÚNG: người yêu cầu = mẹ "VÀNG THỊ LÀ" (số 012192006609), chủ thể = con "GIÀNG THỊ XÊ"
  (số định danh 012312000298). Cccd_* lấy thẻ MẸ (012192006609). ChuThe_* lấy thẻ CON:
  ChuThe_SoGiayToTuyThan="012312000298", ChuThe_NgayCapGiayToTuyThan + ChuThe_NoiCapGiayToTuyThan
  lấy từ CHÍNH thẻ con (KHÔNG PHẢI 012192006609/ngày-nơi cấp của mẹ).
</chu_the_giay_to_tuy_than_rules>

<do_not_return>
- Không trả field quan hệ NYC_QuanHe; thủ tục này để người dùng tự chọn.
- Không trả field UI/default như NYC_HoVaTen, HoVaTenC, NDK_HoVaTen, HoSo_LoaiYeuCau,
  HoSo_TenGiayTo, HoSo_So, HoSo_QuyenSo, HoSo_NgayCapSo, PhuongThucNhanKQ.
- Không trả loại giấy tờ, loại cư trú, quốc tịch mặc định, radio trong/ngoài nước, hoặc số giấy tờ duplicate.
- Nếu giấy tờ hộ tịch không ghi quốc tịch người được đăng ký thì bỏ qua HoTich_QuocTich; Python sẽ mặc định Việt Nam khi cần.
- Mỗi nhóm Cccd_* và HoTich_* phải lấy từ đúng loại tài liệu, không trộn dữ liệu CCCD vào giấy tờ hộ tịch.
</do_not_return>"""

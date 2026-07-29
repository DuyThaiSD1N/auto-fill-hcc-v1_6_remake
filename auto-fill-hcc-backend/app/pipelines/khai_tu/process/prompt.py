"""Procedure-specific compact prompt rules for "Đăng ký khai tử"."""

EXTRA_RULES = """
<procedure>
Đầu vào thường gồm CCCD/CMND của NGƯỜI YÊU CẦU và một nguồn khai tử:
giấy báo tử, giấy chứng tử/giấy tờ thay thế, hoặc tờ khai đăng ký khai tử bản giấy.
</procedure>

<critical_source_split>
- Cccd_* CHỈ lấy từ CCCD/CMND của NGƯỜI YÊU CẦU. Nếu phần CONTEXT cung cấp tên/số định danh người
  yêu cầu (đăng nhập), thì Cccd_* CHỈ lấy từ CCCD TRÙNG tên/số định danh đó.
- QUAN TRỌNG: một CCCD KHÔNG trùng người yêu cầu (đăng nhập) = CCCD của NGƯỜI ĐÃ MẤT (người được khai tử)
  → trích danh tính của người đó vào nhóm Gbt_*: Gbt_HoTenNguoiMat, Gbt_NgaySinhNguoiMat (đủ dd/mm/yyyy
  nếu CCCD có), Gbt_GioiTinhNguoiMat, Gbt_DanTocNguoiMat, Gbt_QuocTichNguoiMat, Gbt_SoDinhDanhNguoiMat,
  Gbt_NgayCapDDNguoiMat, Gbt_NoiCapDDNguoiMat, Gbt_NoiCuTruNguoiMat. TUYỆT ĐỐI không để CCCD người mất vào Cccd_*.
- DÙ đặt vào nhóm nào, LUÔN trích ĐẦY ĐỦ danh tính người trên CCCD: họ tên, NGÀY SINH, GIỚI TÍNH, DÂN TỘC,
  quốc tịch, số định danh, ngày/nơi cấp, nơi cư trú. Không bao giờ bỏ sót ngày sinh/giới tính/dân tộc.
- Nếu người yêu cầu xuất hiện cả trong CCCD và tờ khai giấy, CCCD là nguồn ưu tiên cho Cccd_*.
- Gbt_* là nhóm thông tin NGƯỜI ĐƯỢC KHAI TỬ và sự kiện chết. Có thể lấy từ: CCCD của người đã mất,
  giấy báo tử/giấy chứng tử/giấy tờ thay thế, hoặc tờ khai đăng ký khai tử bản giấy.
- Không trộn CCCD của người yêu cầu vào người tử vong và ngược lại.
- Trong tờ khai giấy, tên người yêu cầu nằm trước cụm "Đề nghị cơ quan đăng ký khai tử cho người có tên dưới đây";
  tên người chết nằm sau cụm đó. Không lấy chữ ký cuối trang hoặc "Người yêu cầu" làm Gbt_HoTenNguoiMat.
</critical_source_split>

<cccd_rules>
- NHẬN DẠNG LOẠI GIẤY TỜ: CMND có 9 chữ số, CCCD/Căn cước có 12 chữ số.
  Trích nguyên số không thêm/bớt chữ số. Ô Cccd_SoDinhDanh và Gbt_SoDinhDanhNguoiMat đều chấp nhận cả 9 và 12 chữ số.
- BẮT BUỘC cố đọc Cccd_NgayCap/Cccd_NoiCap từ mặt sau CCCD. Nơi cấp nằm ngay sau/gần dòng
  "Ngày, tháng, năm / Date, month, year"; nếu OCR thấy "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH
  VỀ TRẬT TỰ XÃ HỘI" thì trả Cccd_NoiCap = "Cục Cảnh sát quản lý hành chính về trật tự xã hội". Nếu là thẻ CĂN CƯỚC mới (tiêu đề "CĂN CƯỚC"/"IDENTITY CARD", thường cấp từ 01/7/2024) ghi "BỘ CÔNG AN"/"MINISTRY OF PUBLIC SECURITY" thì trả Cccd_NoiCap = "Bộ Công an"; KHÔNG mặc định "Cục Cảnh sát..." cho thẻ này.
- Cccd_NoiCuTru lấy từ "Nơi thường trú/Place of residence"; object {quocGia,tinh,diaChi}.
- Quy tắc đọc ngày cấp/nơi cấp ở trên áp dụng CHO MỌI CCCD. Nếu CCCD là của NGƯỜI ĐÃ MẤT thì BẮT BUỘC
  trích ngày cấp vào Gbt_NgayCapDDNguoiMat và nơi cấp vào Gbt_NoiCapDDNguoiMat (cùng cách suy luận
  "Cục Cảnh sát..."/"Bộ Công an"). Hễ mặt sau có ngày cấp + nơi cấp thì PHẢI trả, không được bỏ trống.
</cccd_rules>

<paper_declaration_rules>
- Tài liệu tờ khai giấy thường có tiêu đề "TỜ KHAI ĐĂNG KÝ KHAI TỬ" và các mục:
  người yêu cầu, quan hệ với người đã chết, họ tên người chết, ngày sinh, giới tính,
  dân tộc, quốc tịch, nơi cư trú cuối cùng, giấy tờ tùy thân, đã chết vào lúc,
  nơi chết, nguyên nhân chết, số giấy báo tử/giấy tờ thay thế.
- ToKhai_QuanHeNguoiYeuCau chỉ lấy nếu mục "Quan hệ với người đã chết" có nội dung thật.
  Nếu dòng này để trống, toàn dấu chấm, hoặc OCR không đọc rõ thì bỏ qua.
- Gbt_NgaySinhNguoiMat: lấy đủ dd/mm/yyyy nếu có. Nếu chỉ chắc chắn có năm sinh thì trả năm yyyy.
- Gbt_NgayMat/Gbt_GioMat: lấy từ cụm "Đã chết vào lúc" trong tờ khai hoặc "Tử vong lúc" trong giấy báo tử.
  Không lấy ngày lập tờ khai, ngày cấp CCCD, ngày vào viện, dòng "Vào cơ sở KCB lúc", ngày cấp giấy báo tử.
- Gbt_GioMat trả "HH:mm" khi có cả giờ và phút; nếu tờ khai để trống giờ/phút thì bỏ qua giờ.
- Nếu OCR đọc ngày chết không hợp lệ rõ ràng như ngày 42 hoặc tháng 19 thì không trả ngày đó,
  trừ khi toàn bộ ngữ cảnh cho thấy chắc chắn đó là lỗi OCR của một ngày hợp lệ.
- Gbt_NoiCuTruNguoiMat (mục "(10) Nơi cư trú cuối cùng" của NGƯỜI CHẾT) = nhãn "Nơi thường trú"/"Nơi cư trú
  cuối cùng"/"Nơi cư trú" nằm trong KHỐI THÔNG TIN NGƯỜI CHẾT trên giấy báo tử/tờ khai (ngay dưới họ tên/ngày
  sinh/dân tộc người chết); object {quocGia,tinh,xa,diaChi} theo quy tắc tách địa chỉ. BẮT BUỘC trích nếu giấy có,
  KHÔNG để trống, KHÔNG điền "Đã chết" khi giấy ghi rõ địa chỉ. Đây là nơi cư trú của NGƯỜI CHẾT, không phải người yêu cầu.
- Gbt_NoiChet lấy từ nhãn "Nơi chết"/"Nơi tử vong"; trả object {quocGia,tinh,xa,diaChi}.
- Gbt_NguyenNhanMat lấy từ nhãn "Nguyên nhân chết".
- CẤP BẢN SAO — CHỈ đọc từ mục "Đề nghị cấp bản sao" trên tài liệu có đúng tiêu đề
  "TỜ KHAI ĐĂNG KÝ KHAI TỬ"; không lấy yêu cầu/số lượng bản sao từ giấy tờ khác:
  + Tích/chọn Có -> CopyRequest_WantsCopy = "Có"; tích/chọn Không -> "Không".
  + CopyRequest_Quantity = số lượng bản sao dương ghi thật trên chính tờ khai, bỏ số 0 đứng đầu
    (ví dụ "03 bản" -> "3").
  + Nếu có số lượng dương thì BẮT BUỘC trả CopyRequest_WantsCopy = "Có", kể cả OCR không thể hiện rõ
    ô Có hay Không được tích. Số lượng dương là bằng chứng người khai có đề nghị cấp bản sao.
  + Không có dấu chọn và không có số lượng thì bỏ cả hai field. TUYỆT ĐỐI không mặc định "Có"
    và không mặc định số lượng.
</paper_declaration_rules>

<address_split_rules>
- TÁCH ĐỊA CHỈ (áp dụng Cccd_NoiCuTru, Gbt_NoiCuTruNguoiMat, Gbt_NoiChet — object {quocGia,tinh,xa,diaChi}):
  + xa = TÊN phường/xã/thị trấn, CHỈ lấy TÊN — KHÔNG kèm tiền tố loại (Xã/Phường/Thị trấn). Vd "Xã Tả Lèng" →
    xa="Tả Lèng"; "Phường Tân Phong" → xa="Tân Phong". tinh = tỉnh/thành phố; diaChi = phần CHI TIẾT đứng TRƯỚC
    xã/phường (tổ, tổ dân phố, bản, thôn, xóm, khu, số nhà, đường). TUYỆT ĐỐI KHÔNG đưa tên phường/xã (hay huyện/tỉnh) vào diaChi.
  + XÃ LUÔN BẮT BUỘC: KHÔNG bỏ trống xa khi giấy có phường/xã. Nếu chỉ ra "chi tiết + tỉnh" mà thiếu xã, soát lại —
    phần đứng NGAY TRƯỚC tỉnh (bỏ cấp huyện nếu có) chính là xã. ĐẾM TỪ CUỐI khi liệt kê không nhãn
    ("[chi tiết], xã, HUYỆN, tỉnh"): cuối = tỉnh; phần trước tỉnh nếu là CẤP HUYỆN (huyện/quận/thị xã/thành phố
    thuộc tỉnh) thì BỎ HẲN; phần trước đó = xã. Tên xã vùng cao có thể bắt đầu "Bản"/"Nậm"/"Mường"/"Pa" —
    vị trí (áp chót) mới quyết định là xã, không coi là chi tiết.
  + ƯU TIÊN NGUỒN 2 CẤP: cùng một người/nơi mà một giấy ghi kiểu CŨ 3 cấp (xã, HUYỆN, tỉnh) còn giấy khác ghi
    2 cấp (xã → tỉnh, KHÔNG huyện — đơn vị hành chính HIỆN HÀNH) thì DÙNG bản 2 cấp, kể cả khi tên xã hai bản
    khác nhau do sáp nhập.
</address_split_rules>

<death_notice_metadata_rules>
- Nhận diện GIẤY BÁO TỬ: tài liệu có tiêu đề "GIẤY BÁO TỬ" (hoặc giấy chứng tử/giấy tờ thay thế). Khi ĐÚNG là
  giấy báo tử thật thì BẮT BUỘC trích đủ 3 trường Gbt_So, Gbt_CoQuanCap, Gbt_NgayCap:
  + Gbt_So = số hiệu ở nhãn "Số:" ĐẦU trang, lấy PHẦN SỐ đầu tiên (vd: "Số: 12/GBT" → "12").
  + Gbt_CoQuanCap = tên cơ quan/cơ sở CẤP giấy: thường ở LETTERHEAD đầu trang ("ỦY BAN NHÂN DÂN XÃ/PHƯỜNG ...",
    bệnh viện/trung tâm y tế), hoặc ở khối ký tên cuối trang. Chỉ lấy TÊN cơ quan, không kèm địa chỉ dài.
    Vd letterhead "ỦY BAN NHÂN DÂN XÃ ĐOÀN KẾT" → "UBND xã ĐOÀN KẾT".
  + Gbt_NgayCap = ngày lập/cấp giấy báo tử ở dòng ĐỊA DANH + NGÀY (vd "Tân Phong, ngày 1 tháng 1 năm 2022" → "01/01/2022"),
    thường nằm gần khối ký/con dấu. KHÔNG nhầm với ngày chết (Gbt_NgayMat) hay ngày sinh.
- Với TỜ KHAI GIẤY, mục "Số Giấy báo tử/Giấy tờ thay thế" nếu để trống, dấu chấm, hoặc OCR nhiễu không rõ thì
  bỏ qua Gbt_So/Gbt_CoQuanCap/Gbt_NgayCap (không bịa).
</death_notice_metadata_rules>

<forbidden_ui_fields>
- Không trả field UI/default như HoVaTenC, HoTen, NgayMat, gbtLoai, loaiDangKy, số giấy tờ duplicate,
  loại giấy tờ, loại cư trú, radio trong/ngoài nước, CapBanSao, SoLuong.
- Nếu nguồn khai tử không ghi quốc tịch người tử vong thì bỏ qua Gbt_QuocTichNguoiMat; Python sẽ mặc định Việt Nam.
</forbidden_ui_fields>"""

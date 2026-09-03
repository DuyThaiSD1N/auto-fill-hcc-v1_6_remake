"""Procedure-specific compact prompt rules for "Đăng ký kết hôn"."""

EXTRA_RULES = """
Đầu vào gồm giấy tờ của hai người đăng ký kết hôn (CCCD/CMND, tờ khai và giấy tờ liên quan),
có thể không được gắn role chồng/vợ.

NGUỒN DỮ LIỆU:
- Tự phân biệt hai CCCD bằng trường giới tính trên chính giấy tờ: Nam -> nhóm CccdNam_*, Nữ -> nhóm CccdNu_*.
- CccdNam_* CHỈ lấy từ giấy tờ có tiêu đề CĂN CƯỚC/CMND và giới tính "Nam".
- CccdNu_* CHỈ lấy từ giấy tờ có tiêu đề CĂN CƯỚC/CMND và giới tính "Nữ".
- Không phân biệt nam/nữ theo tên file, thứ tự upload, hoặc suy đoán từ họ tên.
- SỐ ĐỊNH DANH/CCCD (CccdNam_SoDinhDanh, CccdNu_SoDinhDanh): CHỈ đọc ở MẶT TRƯỚC
  CCCD/CMND, lấy đúng dãy 12 chữ số ngay sau nhãn "Số / No." của đúng người. TUYỆT ĐỐI không
  lấy bất kỳ cụm số nào từ dòng MRZ/IDVNM ở mặt sau, kể cả khi mặt sau có chuỗi giống số định danh.
  Không có mặt trước hoặc mặt trước không đọc rõ đủ 12 số thì BỎ field, không dùng MRZ để bù.
- SAU KHI GÁN, BẮT BUỘC ĐỐI CHIẾU CHÉO: Kiểm tra lại số định danh và họ tên trong CccdNam_* phải
  khớp với CCCD/CMND ghi giới tính "Nam"; số định danh và họ tên trong CccdNu_* phải khớp với CCCD/CMND
  ghi giới tính "Nữ". Nếu phát hiện lẫn lộn (vd CccdNam_SoDinhDanh là số trên thẻ ghi "Nữ") → PHẢI
  đảo lại cho đúng trước khi trả kết quả.
- BẮT BUỘC cố đọc CccdNam_NoiCap/CccdNu_NoiCap (cơ quan cấp) trên CCCD/Căn cước, trả ĐÚNG cơ quan ghi trên thẻ:
  + Thẻ CĂN CƯỚC mới (tiêu đề "CĂN CƯỚC"/"IDENTITY CARD", thường cấp từ 01/7/2024): cơ quan cấp ghi
    "BỘ CÔNG AN"/"MINISTRY OF PUBLIC SECURITY" -> trả "Bộ Công an".
  + Thẻ CĂN CƯỚC CÔNG DÂN gắn chip cũ: nếu thấy "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ
    XÃ HỘI" -> trả "Cục Cảnh sát quản lý hành chính về trật tự xã hội".
  + TUYỆT ĐỐI không mặc định "Cục Cảnh sát..." cho thẻ Căn cước mới do Bộ Công an cấp.
- NGUỒN NƠI CƯ TRÚ — PHẢI TRÍCH RIÊNG TỪNG NGUỒN, KHÔNG TỰ CHỌN NGUỒN:
  + ToKhaiNam_NoiCuTru_TrongNuoc / ToKhaiNu_NoiCuTru_TrongNuoc CHỈ lấy từ hàng "Nơi cư trú" ở đúng
    cột Bên nam/Bên nữ của TỜ KHAI ĐĂNG KÝ KẾT HÔN. Đối chiếu đúng cột theo tiêu đề, họ tên và/hoặc số định danh.
  + CccdNam_NoiCuTru_TrongNuoc / CccdNu_NoiCuTru_TrongNuoc CHỈ lấy nơi cư trú in trên CCCD/CMND của chính người đó.
    TOÀN BỘ thông tin (tinh + xa + diaChi) của CccdNam_NoiCuTru_TrongNuoc phải đọc từ ĐÚNG thẻ CCCD có
    cùng số định danh với CccdNam_SoDinhDanh; tương tự CccdNu_NoiCuTru_TrongNuoc phải từ thẻ có số định
    danh CccdNu_SoDinhDanh. TUYỆT ĐỐI không lấy diaChi từ thẻ người này gán cho người kia.
  + Nếu có cả tờ khai và CCCD thì BẮT BUỘC trả CẢ HAI field nguồn tương ứng; mapper sẽ tự ưu tiên tờ khai.
  + Không lấy địa chỉ từ giấy xác nhận tình trạng hôn nhân, giấy phép lái xe, bản cam đoan hoặc giấy tờ phụ
    gán vào bất kỳ field nơi cư trú nào nêu trên.
- TÁCH ĐỊA CHỈ (mọi field *_NoiCuTru_TrongNuoc — object {quocGia,tinh,xa,diaChi}):
  + xa = tên đơn vị cấp xã KÈM tiền tố đầy đủ "Phường"/"Xã"/"Thị trấn"; tinh CHỈ chứa tên
    tỉnh/thành phố trực thuộc trung ương, không chứa quận/huyện/xã hay phần địa chỉ chi tiết;
    diaChi = phần chi tiết đứng TRƯỚC xã (tổ/tổ dân phố/thôn/xóm/bản/số nhà/đường). KHÔNG đưa tên xã/huyện/tỉnh vào diaChi.
  + BẮT BUỘC mở rộng viết tắt trong xa trước khi trả: P9/P.9/P 9 → "Phường 9";
    X5/X.5/X 5 → "Xã 5"; TT Tam Đường/TT. Tam Đường → "Thị trấn Tam Đường".
    Không trả "P9", "P.9", "X5", "X.5", "TT." hoặc tên trần khi nguồn xác định rõ loại đơn vị.
  + Cấp tỉnh Hồ Chí Minh luôn trả đúng "Thành phố Hồ Chí Minh". Mọi dạng "TP.HCM", "TP HCM", "TPHCM",
    "HCM", "TP.Hồ Chí Minh", "TP Hồ Chí Minh" hoặc "Hồ Chí Minh" đều phải chuẩn hóa thành tên đầy đủ này.
  + Khi địa chỉ trên tờ khai có nhãn rõ "Xã ..." hoặc "Phường ..." thì đơn vị mang nhãn đó BẮT BUỘC là xa;
    các thành phần "Thôn ...", "Tổ ...", "Khu phố ..." đứng trước vẫn thuộc diaChi, không được chọn chúng làm xa.
  + XÃ BẮT BUỘC khi giấy có phường/xã. ĐẾM TỪ CUỐI khi liệt kê không nhãn ("[chi tiết], xã, HUYỆN, tỉnh"):
    cuối = tỉnh; phần NGAY TRƯỚC tỉnh nếu là CẤP HUYỆN (huyện/quận/thị xã/thành phố thuộc tỉnh) thì BỎ HẲN;
    phần trước đó = xã. Tên xã vùng cao có thể bắt đầu "Bản"/"Nậm"/"Mường"/"Pa" — vị trí (áp chót) mới quyết định là xã.
- QUỐC TỊCH (CccdNam_QuocTich, CccdNu_QuocTich): CHỈ điền khi giấy tờ KHÔNG phải Việt Nam.
  + Suy từ tiêu đề quốc gia: "CỘNG HOÀ NHÂN DÂN TRUNG HOA" → "Trung Quốc"; "CỘNG HOÀ DÂN CHỦ NHÂN DÂN LÀO" → "Lào"; "VƯƠNG QUỐC CAMPUCHIA" → "Campuchia".
  + Hoặc nhãn "Quốc tịch:" nếu ghi rõ trên giấy tờ.
  + CCCD/Căn cước Việt Nam → BỎ QUA field này (Python tự mặc định "Việt Nam").
  + quocGia trong object địa chỉ cũng phải khớp quốc tịch: người Trung Quốc → quocGia="Trung Quốc".
- DÂN TỘC (CccdNam_DanToc = dân tộc BÊN NAM, CccdNu_DanToc = dân tộc BÊN NỮ): CCCD/Căn cước gắn chip
  KHÔNG ghi dân tộc. CHỈ lấy từ CÁC GIẤY TỜ KHÁC khi OCR có NHÃN "Dân tộc" và giá trị được ghi trực tiếp
  cho đúng người (TỜ KHAI ĐĂNG KÝ KẾT HÔN, bản cam đoan, giấy tờ hộ tịch khác):
  + Nếu toàn bộ hồ sơ chỉ có CCCD/Căn cước hoặc không xuất hiện nhãn "Dân tộc" → BỎ CẢ HAI field dân tộc.
  + Họ, chữ đệm, tên, quê quán, nơi cư trú, địa danh và vùng miền KHÔNG phải chứng cứ dân tộc. TUYỆT ĐỐI
    không suy đoán dân tộc từ các thông tin này dù có vẻ liên quan.
  + TỜ KHAI ĐĂNG KÝ KẾT HÔN THƯỜNG có hàng "Dân tộc" ghi cho CẢ HAI cột (bên nam VÀ bên nữ). Khi đó BẮT BUỘC
    trả ĐỦ CẢ HAI: CccdNam_DanToc VÀ CccdNu_DanToc — KHÔNG được bỏ sót bên nào, KỂ CẢ khi hai bên GIỐNG hệt
  + Bảng tờ khai có thể xếp cột theo THỨ TỰ BẤT KỲ (nhiều tờ ghi cột "Bên nữ" TRƯỚC cột "Bên nam"). Xác định cột
    nào là nam/nữ theo TIÊU ĐỀ cột ("Bên nam"/"Bên nữ") hoặc theo hàng Họ tên, TUYỆT ĐỐI không mặc định nam đứng trước.
  + Đối chiếu theo HỌ TÊN và/hoặc SỐ ĐỊNH DANH để biết dân tộc đó là của bên nam hay bên nữ; gán dân tộc
    cho ĐÚNG người đó. TUYỆT ĐỐI không lấy dân tộc của người này gán cho người kia.
  + Nếu KHÔNG có nhãn "Dân tộc" ghi rõ giá trị của người đó → BỎ field tương ứng (KHÔNG bịa, KHÔNG mặc định).
  + VÍ DỤ: nếu CHỈ tờ khai của BÊN NỮ ghi dân tộc, còn bên nam không giấy nào ghi → CHỈ trả CccdNu_DanToc,
    ĐỂ TRỐNG CccdNam_DanToc (TUYỆT ĐỐI KHÔNG copy dân tộc bên nữ sang bên nam và ngược lại).
  + Lưu ý option trên form: dân tộc H'Mông" (gồm các cách"H'Mông"/"H Mông"/"Hmông") PHẢI trả là
    "Mông (Hmông)"
  + Còn dân tộc Mông thì ghi "Mông"
- Quốc tịch chỉ trả nếu giấy tờ ghi rõ hoặc khác Việt Nam; mặc định Việt Nam.
- SỐ LẦN KẾT HÔN: nếu tờ khai/giấy tờ có mục "Kết hôn lần thứ mấy" (hoặc "Số lần kết hôn") ghi số cho từng bên
  thì trả CccdNam_SoLanKetHon (cột BÊN NAM) và CccdNu_SoLanKetHon (cột BÊN NỮ) là SỐ NGUYÊN (vd "1", "2", "3").
  Đối chiếu ĐÚNG CỘT nam/nữ theo tiêu đề bảng. Không có mục này → bỏ qua để mapper xử lý mặc định theo từng bên.
- TÌNH TRẠNG HÔN NHÂN: chỉ trả mã số 1–6 cho CccdNam_TinhTrangHonNhan/CccdNu_TinhTrangHonNhan khi tờ khai ghi rõ
  hoặc quyết định/bản án ly hôn thật xác định đúng người đó là đương sự. Với từng quyết định, đối chiếu riêng
  từng đương sự với từng CCCD theo điều kiện CHẶT: (a) họ tên phải khớp chính xác sau khi chỉ chuẩn hóa
  hoa-thường, dấu tiếng Việt và khoảng trắng; hoặc (b) số CCCD/số định danh trên quyết định khớp chính xác.
  TUYỆT ĐỐI không fuzzy/sửa họ tên để tạo khớp: lệch, thiếu hoặc thừa dù chỉ một chữ mà quyết định không có
  số CCCD khớp thì KHÔNG coi là cùng người; cùng năm sinh, địa chỉ hoặc giới tính cũng không đủ thay thế.
  Xử lý từng quyết định độc lập: quyết định của người nào chỉ gán mã cho đúng người đó, không thấy hồ sơ có
  hai CCCD rồi tự gán ly hôn cho cả hai, không lấy cặp đương sự của văn bản này ghép với CCCD của văn bản khác.
  Người có quyết định ly hôn → mã 3 ("Đã đăng ký kết hôn hoặc đã có vợ/chồng nhưng đã ly hôn; hiện tại chưa đăng ký kết hôn với ai").
  Không trả cả câu dài, chỉ trả một mã số duy nhất.
  Không có chứng cứ trực tiếp → bỏ field để mapper xử lý mặc định theo từng bên; không tự suy luận mã từ CCCD.
- BẢN ÁN/QUYẾT ĐỊNH LY HÔN: khi CccdNam_TinhTrangHonNhan hoặc CccdNu_TinhTrangHonNhan = mã 3 (đúng người đó
  là đương sự theo điều kiện đối chiếu ở trên), BẮT BUỘC trả thêm từ CHÍNH văn bản bản án/quyết định ly hôn đó:
  + CccdNam_BanAnLyHon_So / CccdNu_BanAnLyHon_So: số bản án/quyết định (vd "336/2023/QĐST-HNGD"), lấy nguyên
    văn dòng "Số:" trên văn bản.
  + CccdNam_BanAnLyHon_Ngay / CccdNu_BanAnLyHon_Ngay: ngày ban hành, dd/mm/yyyy (dòng "..., ngày ... tháng ...
    năm ..." ở đầu văn bản).
  + CccdNam_BanAnLyHon_CoQuan / CccdNu_BanAnLyHon_CoQuan: tên cơ quan ban hành ghi ở góc trên văn bản
    (vd "Tòa án nhân dân thành phố Đà Lạt, tỉnh Lâm Đồng").
  Mỗi bên lấy đúng số/ngày/cơ quan của văn bản xác định người đó là đương sự; hai bên ly hôn với nhau thì
  dùng CHUNG một văn bản (số/ngày/cơ quan giống nhau cho cả hai). Không suy diễn hay bịa khi văn bản không
  ghi rõ; thiếu bất kỳ phần nào thì bỏ field đó, không để trống bằng giá trị đoán.
- LOẠI ĐĂNG KÝ: nếu TỜ KHAI có mục "Loại đăng ký" được tích/ghi rõ thì trả ToKhai_LoaiDangKy
  đúng nhãn được chọn (vd "Đăng ký lần đầu", "Đăng ký lại"). Tờ khai không có mục này hoặc không
  tích ô nào → bỏ field; TUYỆT ĐỐI không tự suy hoặc yêu cầu mapper mặc định "Đăng ký lần đầu".
- CẤP BẢN SAO — CHỈ đọc từ mục "Đề nghị cấp bản sao" trên tài liệu có đúng tiêu đề
  "TỜ KHAI ĐĂNG KÝ KẾT HÔN"; không lấy yêu cầu/số lượng bản sao từ giấy tờ khác:
  + Tích/chọn Có -> CopyRequest_WantsCopy = "Có"; tích/chọn Không -> "Không".
  + CopyRequest_Quantity = số lượng bản sao dương ghi thật trên chính tờ khai, bỏ số 0 đứng đầu
    (ví dụ "02 bản" -> "2").
  + Nếu có số lượng dương thì BẮT BUỘC trả CopyRequest_WantsCopy = "Có", kể cả OCR không thể hiện rõ
    ô Có hay Không được tích. Số lượng dương là bằng chứng người khai có đề nghị cấp bản sao.
  + Không có dấu chọn và không có số lượng thì bỏ cả hai field. TUYỆT ĐỐI không mặc định "Có"
    và không mặc định số lượng.
- Không trả field UI/default như HoTenBenNam, HoTenBenNu, LoaiGiayToDinhDanh_*, SoGiayToDinhDanh_*,
  LoaiCuTru_*, NoiCuTru_*, SoLanKetHon_BenNam/BenNu, tình trạng hôn nhân, loaiDangKy,
  CapBanSao, SoLuong. Loại đăng ký đọc được từ tờ khai thì trả qua ToKhai_LoaiDangKy.
- Họ tên/số định danh/ngày sinh/ngày-nơi cấp của mỗi nhóm CccdNam_*/CccdNu_* phải lấy trọn từ
  đúng MỘT CCCD, không trộn giữa hai người. RIÊNG dân tộc được phép lấy từ giấy tờ khác theo quy tắc DÂN TỘC;
  nơi cư trú phải tách riêng từng nguồn theo quy tắc NGUỒN NƠI CƯ TRÚ ở trên.
- BẮT BUỘC KIỂM TRA CHÉO ĐỊA CHỈ: sau khi gán, kiểm tra CccdNam_NoiCuTru_TrongNuoc phải là địa chỉ
  đọc từ CCCD có cùng số định danh với CccdNam_SoDinhDanh; CccdNu_NoiCuTru_TrongNuoc phải là địa chỉ
  từ CCCD có cùng số định danh với CccdNu_SoDinhDanh. Nếu phát hiện địa chỉ bị gán nhầm (địa chỉ lấy
  từ CCCD của người kia) → hoán đổi lại cho đúng.
  
<dia_chi_cccd>
Địa chỉ CCCD/CMND không tiền tố = dãy tên ngăn dấu phẩy, xếp NHỎ→LỚN. Cấp HUYỆN/QUẬN (tên thứ 2 TỪ CUỐI,
sát tỉnh) LUÔN bị XÓA HẲN — không cho vào xa lẫn diaChi (biểu mẫu chỉ có 2 cấp xã-tỉnh). Xử lý theo ĐÚNG
SỐ TÊN, KHÔNG được đảo:
• ĐÚNG 3 tên "A, B, C" (KHÔNG có phần chi tiết): A = xa; B = huyện → XÓA; C = tinh; diaChi = RỖNG.
  ⚠ Đây là chỗ HAY SAI: TUYỆT ĐỐI KHÔNG lấy B (sát tỉnh) làm xa, KHÔNG đẩy A xuống diaChi.
  VD1: "Nội Duệ, Tiên Du, Bắc Ninh" → xa="Nội Duệ", huyen="Tiên Du", tinh="Bắc Ninh",
  diaChi="".
• 4 tên "D, A, B, C" (D là chi tiết: thôn/xóm/tổ dân phố/số nhà): D = diaChi; A = xa; B = huyện → XÓA;
  C = tinh. VD2: "Thôn Đại Vi, Đại Đồng, Tiên Du, Bắc Ninh" → diaChi="Thôn Đại Vi", xa="Đại Đồng", huyen="Tiên Du",
  tinh="Bắc Ninh".
• 2 tên "A, C": A = xa; C = tinh; diaChi rỗng (không có huyện để xóa).
</dia_chi_cccd>
  """

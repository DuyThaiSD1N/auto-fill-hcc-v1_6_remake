"""Luật trích theo TỪNG LOẠI GIẤY của thủ tục "Đăng ký kết hôn" — chèn vào <quy_tac_theo_giay> của base_prompt.

Khung chung (vai trò, giấy nào → nhóm field nào, bên nam/bên nữ, định dạng, địa chỉ, output) nằm ở base_prompt;
ở đây chỉ luật riêng từng giấy. Ví dụ chỉ dùng tên giả / mô tả: model từng chép nguyên giá trị của ví dụ (số bản
án, tên đương sự) vào hồ sơ không hề có văn bản đó.
"""

EXTRA_RULES = """
<the_can_cuoc>
- SỐ ĐỊNH DANH (BenNam_SoDinhDanh, BenNu_SoDinhDanh): CHỈ đọc ở MẶT TRƯỚC thẻ, đúng dãy 12 chữ số ngay sau nhãn
  "Số / No." hoặc "Số định danh cá nhân / Personal identification number" (CMND cũ: 9 số). TUYỆT ĐỐI không lấy bất kỳ
  cụm số nào từ dòng MRZ/IDVNM ở mặt sau, kể cả khi mặt sau có chuỗi giống số định danh — dòng mã máy chỉ dùng để
  biết mặt sau là của ai (xem <hai_ben>). Không có mặt trước hoặc mặt trước không đọc rõ đủ số thì BỎ field,
  không dùng MRZ để bù.
- NGÀY CẤP: thẻ CĂN CƯỚC mới đọc dòng "Ngày, tháng, năm cấp / Date of issue"; thẻ CĂN CƯỚC CÔNG DÂN gắn chip đọc dòng
  "Ngày, tháng, năm / Date, month, year" ở mặt sau (cạnh chữ ký, con dấu, vân tay). KHÔNG lấy "Có giá trị đến /
  Date of expiry", "Ngày, tháng, năm hết hạn" hay ngày sinh làm ngày cấp. Không thấy dòng ngày cấp → bỏ field.
- NƠI CẤP: BẮT BUỘC cố đọc BenNam_NoiCap/BenNu_NoiCap, trả ĐÚNG cơ quan in trên CHÍNH thẻ đó:
  + Thẻ CĂN CƯỚC mới (tiêu đề "CĂN CƯỚC" / "IDENTITY CARD", cấp từ 01/7/2024), mặt sau ghi "BỘ CÔNG AN" /
    "MINISTRY OF PUBLIC SECURITY" → "Bộ Công an".
  + Thẻ CĂN CƯỚC CÔNG DÂN gắn chip (tiêu đề "CĂN CƯỚC CÔNG DÂN" / "Citizen Identity Card"), mặt sau có "CỤC TRƯỞNG
    CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội".
  + CMND cũ ghi "Công an tỉnh ..." → chép nguyên cơ quan đó.
  + Mỗi thẻ đọc riêng: hai người có thể dùng HAI loại thẻ khác nhau. TUYỆT ĐỐI không mặc định "Cục Cảnh sát..." cho
    thẻ Căn cước mới do Bộ Công an cấp, không lấy nơi cấp của thẻ người này cho người kia.
- NƠI CƯ TRÚ (BenNam_NoiCuTru_TrongNuoc / BenNu_NoiCuTru_TrongNuoc): chỉ lấy "Nơi thường trú" / "Nơi cư trú" in
  trên thẻ của CHÍNH người đó — thẻ CCCD gắn chip in ở cuối MẶT TRƯỚC, thẻ CĂN CƯỚC mới in ở đầu MẶT SAU. Toàn bộ
  tinh + xa + diaChi phải từ ĐÚNG thẻ có cùng số định danh với nhóm đó; TUYỆT ĐỐI không lấy diaChi từ thẻ người này
  gán cho người kia, không lấy từ tờ khai, bản án hay giấy khác (trừ GIẤY THAY THẺ ở <giay_to>). Tách theo
  <dia_chi>.
- QUỐC TỊCH (BenNam_QuocTich, BenNu_QuocTich): CHỈ trả khi giấy tờ KHÔNG phải của Việt Nam — suy từ quốc hiệu in
  trên giấy ("CỘNG HOÀ NHÂN DÂN TRUNG HOA" → "Trung Quốc"; "CỘNG HOÀ DÂN CHỦ NHÂN DÂN LÀO" → "Lào"; "VƯƠNG QUỐC
  CAMPUCHIA" → "Campuchia") hoặc nhãn "Quốc tịch:" ghi rõ. CCCD/Căn cước Việt Nam → BỎ QUA (Python tự mặc định
  "Việt Nam").
- LOẠI GIẤY TỜ (BenNam_LoaiGiayTo, BenNu_LoaiGiayTo): CHỈ khi là giấy tờ nước ngoài (hộ chiếu, chứng minh thư nước
  ngoài); CCCD/Căn cước Việt Nam → bỏ.
</the_can_cuoc>

<to_khai>
TỜ KHAI ĐĂNG KÝ KẾT HÔN là bảng hai cột Bên nam / Bên nữ, thường viết tay. Đọc TỪNG HÀNG, gán theo tiêu đề cột
(<hai_ben>); hàng nào để trống ở cột nào thì bỏ field tương ứng:
- "Họ, chữ đệm, tên" → ToKhaiNam_HoTen / ToKhaiNu_HoTen.
- "Ngày, tháng, năm sinh" → ToKhaiNam_NgaySinh / ToKhaiNu_NgaySinh.
- "Dân tộc" → ToKhaiNam_DanToc / ToKhaiNu_DanToc (xem <dan_toc>).
- "Nơi cư trú" → ToKhaiNam_NoiCuTru_TrongNuoc / ToKhaiNu_NoiCuTru_TrongNuoc, tách theo <dia_chi>.
- "Giấy tờ tùy thân" → ToKhai*_SoDinhDanh (dãy số), ToKhai*_NgayCap, ToKhai*_NoiCap — CHỈ phần nào chính dòng đó GHI
  trên tờ khai. Ô chỉ ghi số thì chỉ trả số; KHÔNG chép ngày cấp / nơi cấp từ thẻ sang tờ khai. Nơi cấp viết tắt
  ("CCS QLHC về TTXH", "Cục CS QLHC", "C06") chép nguyên văn như tờ khai.
- "Kết hôn lần thứ mấy" → BenNam_SoLanKetHon / BenNu_SoLanKetHon là SỐ NGUYÊN theo đúng cột: "1", "01", "Lần
  đầu", "Lần thứ nhất", "Một", "Thứ nhất" → "1"; "2", "02", "Lần thứ hai", "Hai" → "2". Hàng có ghi thì BẮT BUỘC trả
  cho cả hai bên. Không ghi → bỏ.
Có cả tờ khai và thẻ thì BẮT BUỘC trả CẢ HAI nhóm (ToKhai*_* và nhân thân BenNam_* / BenNu_*), kể cả khi giống nhau: mapper ưu tiên thẻ
(bản in) cho nhân thân, mapper sẽ tự ưu tiên tờ khai cho nơi cư trú; tờ khai bù chỗ thẻ thiếu.
LOẠI ĐĂNG KÝ (ToKhai_LoaiDangKy): CHỈ khi tờ khai có in chữ "Loại đăng ký" kèm các ô "Đăng ký lần đầu" / "Đăng ký
lại" và một ô được tích → trả đúng nhãn của ô được tích. Mẫu tờ khai thông dụng KHÔNG có mục này: không thấy chữ
"Loại đăng ký" trên giấy → TUYỆT ĐỐI không trả field. Hàng "Kết hôn lần thứ mấy" (01, 02, lần đầu, lần hai) là số lần
kết hôn, KHÔNG phải loại đăng ký. TUYỆT ĐỐI không tự suy hoặc mặc định "Đăng ký lần đầu".
CẤP BẢN SAO — CHỈ đọc từ dòng "Đề nghị cấp bản sao: Có ☐, Không ☐" và "Số lượng: ... bản" ở cuối tài liệu có đúng
tiêu đề "TỜ KHAI ĐĂNG KÝ KẾT HÔN"; không lấy từ giấy khác:
- Ô "Có" được tích → CopyRequest_WantsCopy = "Có"; ô "Không" được tích → "Không".
- CopyRequest_Quantity = số lượng bản sao DƯƠNG ghi thật ở "Số lượng" (bỏ số 0 đứng đầu: "02 bản" → "2").
  "Số lượng: ……bản" để chấm, "0", "00" → KHÔNG có số lượng.
- Nếu có số lượng dương thì BẮT BUỘC trả CopyRequest_WantsCopy = "Có", kể cả không rõ ô nào được tích.
- Cả hai ô TRỐNG và không có số lượng dương → BỎ CẢ HAI field. Đây là trường hợp phổ biến nhất; ô vuông in sẵn
  ("☐", "□") không phải dấu tích. TUYỆT ĐỐI không mặc định "Có" hay "Không" và không mặc định số lượng.
</to_khai>

<dan_toc>
CCCD/Căn cước gắn chip KHÔNG ghi dân tộc. Dân tộc CHỈ lấy khi giấy có NHÃN "Dân tộc" ghi giá trị trực tiếp cho đúng
người:
- Hàng "Dân tộc" trên TỜ KHAI → ToKhaiNam_DanToc / ToKhaiNu_DanToc theo đúng cột. Tờ khai thường ghi CẢ HAI cột
  → BẮT BUỘC trả ĐỦ CẢ HAI, kể cả khi hai bên giống hệt nhau.
- Nhãn "Dân tộc" trên giấy khác của đúng một người (giấy xác nhận tình trạng hôn nhân, xác nhận / phiếu thông tin
  cư trú, kết quả tra cứu thông tin công dân, bản cam đoan) → BenNam_DanToc / BenNu_DanToc của người có họ tên /
  số định danh trên giấy đó.
- CHÉP NGUYÊN VĂN chữ trên giấy, giữ dấu nháy và chữ đứng trước: "K'Ho", "H'Mông", "Hmông", "M'Nông", "Cil",
  "Chil", "Xrê", "Ra-glai", "Chu Ru" — Python tự chuẩn hóa về option của dropdown; không tự đổi sang tên khác, không
  bỏ field chỉ vì tên lạ.
- Nếu toàn bộ hồ sơ chỉ có CCCD/Căn cước hoặc không xuất hiện nhãn "Dân tộc" → BỎ CẢ HAI field dân tộc.
- Họ tên, quê quán, nơi cư trú, địa danh, vùng miền KHÔNG phải chứng cứ dân tộc: TUYỆT ĐỐI không suy đoán dân tộc từ
  các thông tin này. Chỉ một bên có nhãn thì chỉ trả bên đó; TUYỆT ĐỐI không chép dân tộc của bên này sang bên kia.
</dan_toc>

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
- NHÂN THÂN TRÊN TỜ KHAI (ToKhaiNam_* / ToKhaiNu_*: HoTen, NgaySinh, SoDinhDanh, NgayCap, NoiCap, DanToc):
  + ToKhaiNam_DanToc / ToKhaiNu_DanToc: hàng "Dân tộc" ở đúng cột, chép NGUYÊN VĂN kể cả khi là tên nhóm
    địa phương lạ (K'Ho, Cil, Chil, Xrê...) — KHÔNG bỏ field chỉ vì không chắc là tên dân tộc chuẩn.
  + CHỈ lấy ở đúng cột Bên nam/Bên nữ của TỜ KHAI ĐĂNG KÝ KẾT HÔN; KHÔNG chép từ CCCD sang.
  + Có tờ khai thì BẮT BUỘC trả, KỂ CẢ khi đã có CCCD: mapper ưu tiên CCCD (bản in), tờ khai chỉ bù
    phần thẻ thiếu (vd hồ sơ thiếu CCCD một bên, hoặc chỉ có mặt trước nên thiếu ngày/nơi cấp).
- NGUỒN NƠI CƯ TRÚ — PHẢI TRÍCH RIÊNG TỪNG NGUỒN, KHÔNG TỰ CHỌN NGUỒN:
  + ToKhaiNam_NoiCuTru_TrongNuoc / ToKhaiNu_NoiCuTru_TrongNuoc CHỈ lấy từ hàng "Nơi cư trú" ở đúng
    cột Bên nam/Bên nữ của TỜ KHAI ĐĂNG KÝ KẾT HÔN. Đối chiếu đúng cột theo tiêu đề, họ tên và/hoặc số định danh.
  + CccdNam_NoiCuTru_TrongNuoc / CccdNu_NoiCuTru_TrongNuoc CHỈ lấy nơi cư trú in trên CCCD/CMND của chính người đó.
    TOÀN BỘ thông tin (tinh + xa + diaChi) của CccdNam_NoiCuTru_TrongNuoc phải đọc từ ĐÚNG thẻ CCCD có
    cùng số định danh với CccdNam_SoDinhDanh; tương tự CccdNu_NoiCuTru_TrongNuoc phải từ thẻ có số định
    danh CccdNu_SoDinhDanh. TUYỆT ĐỐI không lấy diaChi từ thẻ người này gán cho người kia.
  + HAI THẺ LIỀN NHAU TRONG MỘT FILE: thẻ CĂN CƯỚC mới in "Nơi cư trú", ngày cấp, "BỘ CÔNG AN" ở MẶT SAU,
    và mặt sau KẾT THÚC bằng MRZ (dòng IDVNM...<12 số định danh><<, dòng giới tính M/F, dòng họ tên không dấu).
    Mọi thông tin đứng SAU MRZ của người thứ nhất và TRƯỚC MRZ tiếp theo thuộc người có tên/số trong MRZ
    tiếp theo đó, KHÔNG thuộc người có MRZ ngay phía trên. Thẻ CCCD cũ in "Nơi thường trú" ở MẶT TRƯỚC,
    cùng mặt với "Số / No." của chính người đó.
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
    Ô dân tộc để trống sẽ được tô ĐỎ trên form cho người dùng tự chọn — bỏ trống luôn an toàn hơn đoán sai.
  + VÍ DỤ: nếu CHỈ tờ khai của BÊN NỮ ghi dân tộc, còn bên nam không giấy nào ghi → CHỈ trả CccdNu_DanToc,
    ĐỂ TRỐNG CccdNam_DanToc (TUYỆT ĐỐI KHÔNG copy dân tộc bên nữ sang bên nam và ngược lại).
  + Lưu ý option trên form: dân tộc H'Mông" (gồm các cách"H'Mông"/"H Mông"/"Hmông") PHẢI trả là
    "Mông (Hmông)"
  + Còn dân tộc Mông thì ghi "Mông"
- Quốc tịch chỉ trả nếu giấy tờ ghi rõ hoặc khác Việt Nam; mặc định Việt Nam.
- SỐ LẦN KẾT HÔN: nếu tờ khai/giấy tờ có mục "Kết hôn lần thứ mấy" (hoặc "Số lần kết hôn") ghi số cho từng bên
  thì trả CccdNam_SoLanKetHon (cột BÊN NAM) và CccdNu_SoLanKetHon (cột BÊN NỮ) là SỐ NGUYÊN (vd "1", "2", "3").
  Đối chiếu ĐÚNG CỘT nam/nữ theo tiêu đề bảng. Không có mục này → bỏ qua; mapper tự suy theo tình trạng hôn
  nhân của từng bên (đã ly hôn/vợ-chồng đã chết → lần 2, tô vàng để người dùng rà lại).
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
- BẢN ÁN/QUYẾT ĐỊNH LY HÔN — MỖI BÊN MỘT VĂN BẢN RIÊNG, GÁN THEO ĐƯƠNG SỰ:
  Hồ sơ kết hôn RẤT HAY có NHIỀU quyết định ly hôn khác nhau (bên nam ly hôn với người khác, bên nữ ly hôn
  với người khác), thường nằm liền nhau trong CÙNG một file PDF. BẮT BUỘC duyệt TỪNG văn bản độc lập:
  B0. VĂN BẢN NÀO ĐƯỢC TÍNH LÀ "văn bản ly hôn" — KHÔNG CHỈ loại có chữ "ly hôn" trên tiêu đề. Tính ĐỦ CẢ:
      "Quyết định công nhận thuận tình ly hôn", "Bản án ly hôn", "Bản án/Quyết định KHÔNG CÔNG NHẬN QUAN HỆ
      VỢ CHỒNG" (hai người chung sống nhưng chưa đăng ký kết hôn, toà tuyên chấm dứt), "Bản án/Quyết định
      HỦY VIỆC KẾT HÔN TRÁI PHÁP LUẬT". Tiêu đề kiểu V/v "Không công nhận quan hệ vợ chồng, tranh chấp về
      nuôi con chung" VẪN LÀ văn bản ly hôn của các đương sự trong đó — KHÔNG được bỏ qua chỉ vì thiếu chữ
      "ly hôn". Số của loại này thường ghi "Bản án số: 06/2020/HNGĐ - ST" → trả "06/2020/HNGĐ-ST" (bỏ khoảng
      trắng quanh dấu gạch, giữ nguyên phần còn lại).
  B1. Với MỖI văn bản ly hôn, đọc riêng danh sách đương sự (nguyên đơn/bị đơn, "công nhận thuận tình ly hôn
      giữa ... và ...", "không công nhận quan hệ vợ chồng giữa ... và ...") và cơ quan ban hành của CHÍNH
      văn bản đó.
  B2. So khớp CHẶT họ tên đương sự với CccdNam_HoTen / CccdNu_HoTen (chỉ chuẩn hóa hoa-thường, dấu tiếng Việt,
      khoảng trắng) hoặc số CCCD ghi trên văn bản. Không fuzzy, không sửa tên để tạo khớp.
  B3. Chỉ gán số/ngày/cơ quan cho người có tên TRONG CHÍNH văn bản đó.
  TUYỆT ĐỐI KHÔNG: lấy văn bản của bên này gán cho bên kia; không dùng một văn bản (vd văn bản đọc được sau
  cùng) điền cho CẢ HAI bên; không thấy hồ sơ có một quyết định ly hôn rồi suy ra cả hai bên cùng văn bản đó.
  CHỈ khi CẢ HAI họ tên nam và nữ cùng là đương sự TRONG CÙNG MỘT văn bản thì hai bên mới dùng chung
  số/ngày/cơ quan giống hệt nhau. Người nào không có văn bản nào ghi tên → BỎ TRỐNG cả 4 field ly hôn của
  người đó, kể cả khi người kia có.
  RÀNG BUỘC VỚI TÌNH TRẠNG HÔN NHÂN: văn bản nào là căn cứ để kết luận một bên có mã 3 thì CHÍNH văn bản đó
  phải được trả vào *_BanAnLyHon_So/_Ngay/_CoQuan/_DuongSu của bên đó. Trả CccdNam_TinhTrangHonNhan=3 (hoặc
  CccdNu_...=3) mà lại lấy số/ngày/cơ quan của văn bản thuộc bên kia là SAI NGHIÊM TRỌNG — nghĩa là văn bản
  của bên này đã bị bỏ sót, phải quay lại B0/B1 quét lại toàn bộ tài liệu cho đúng bên đó.
  TỰ KIỂM TRA TRƯỚC KHI TRẢ KẾT QUẢ: với mỗi bên có *_BanAnLyHon_So, họ tên của CHÍNH bên đó (CccdNam_HoTen /
  CccdNu_HoTen) BẮT BUỘC phải nằm trong *_BanAnLyHon_DuongSu của bên đó. Không nằm trong → văn bản đang gán
  là của người khác: quét lại hồ sơ tìm văn bản có tên người này (kể cả các loại ở B0); vẫn không có thì
  BỎ TRỐNG cả 4 field ly hôn của bên đó, TUYỆT ĐỐI không giữ văn bản của bên kia.
  Hai bên KHÔNG được có *_BanAnLyHon_So giống hệt nhau trừ khi cả hai tên đều nằm trong cùng một DuongSu.
  + CccdNam_BanAnLyHon_So / CccdNu_BanAnLyHon_So: số bản án/quyết định (vd "336/2023/QĐST-HNGD"), lấy nguyên
    văn dòng "Số:" trên ĐÚNG văn bản đã khớp tên người đó.
  + CccdNam_BanAnLyHon_Ngay / CccdNu_BanAnLyHon_Ngay: ngày ban hành, dd/mm/yyyy (dòng "..., ngày ... tháng ...
    năm ..." ở đầu ĐÚNG văn bản đó).
  + CccdNam_BanAnLyHon_CoQuan / CccdNu_BanAnLyHon_CoQuan: tên cơ quan ban hành ghi ở GÓC TRÊN của CHÍNH văn
    bản đó, gộp đủ các dòng tiêu đề (vd "Tòa án nhân dân huyện An Lão, thành phố Hải Phòng",
    "Tòa án nhân dân thành phố Sơn La, tỉnh Sơn La").
  + CccdNam_BanAnLyHon_DuongSu / CccdNu_BanAnLyHon_DuongSu: BẮT BUỘC trả kèm khi có 3 field trên — chép họ tên
    ĐẦY ĐỦ của TẤT CẢ đương sự ghi trong CHÍNH văn bản đã gán cho người này, nối bằng "; "
    (vd "Nguyễn Hoàng Hải Thanh; Lưu Hùng Nguyên"). Bỏ chức danh/xưng hô (ông/bà/anh/chị) và năm sinh.
    Hệ thống dùng field này để tự kiểm tra chéo: nếu họ tên người đó KHÔNG nằm trong danh sách này thì TOÀN BỘ
    phần ly hôn của người đó sẽ bị loại bỏ.
  VÍ DỤ hồ sơ có 2 quyết định (rất hay gặp):
    - "Số 70/2018/QĐST-HNGĐ", Toà án nhân dân huyện An Lão, thành phố Hải Phòng, ngày 09/5/2018, ly hôn giữa
      chị Nguyễn Hoàng Hải Thanh và anh Lưu Hùng Nguyên → CHỈ gán cho BÊN NỮ Nguyễn Hoàng Hải Thanh
      (CccdNu_BanAnLyHon_So="70/2018/QĐST-HNGĐ", _Ngay="09/05/2018",
      _CoQuan="Tòa án nhân dân huyện An Lão, thành phố Hải Phòng",
      _DuongSu="Nguyễn Hoàng Hải Thanh; Lưu Hùng Nguyên").
    - "Số: 52/2023/QĐST-HNGĐ", Toà án nhân dân thành phố Sơn La, ngày 17/02/2023, ly hôn giữa chị Lường Thị Ly
      và anh Mè Minh Tuấn → CHỈ gán cho BÊN NAM Mè Minh Tuấn.
    SAI NGHIÊM TRỌNG nếu điền 52/2023 (hoặc 70/2018) cho cả hai bên.
  VÍ DỤ hai văn bản KHÁC LOẠI (lỗi thật đã gặp — bên nam bị bỏ sót vì tiêu đề không có chữ "ly hôn"):
    - "Bản án số: 06/2020/HNGĐ - ST" ngày 7/9/2020, Tòa án nhân dân thị xã Sa Pa - tỉnh Lào Cai,
      V/v "Không công nhận quan hệ vợ chồng, tranh chấp về nuôi con chung", nguyên đơn chị Châu Thị Si,
      bị đơn anh Giàng A Chư → ĐÂY LÀ văn bản ly hôn của BÊN NAM Giàng A Chư:
      CccdNam_BanAnLyHon_So="06/2020/HNGĐ-ST", _Ngay="07/09/2020",
      _CoQuan="Tòa án nhân dân thị xã Sa Pa, tỉnh Lào Cai", _DuongSu="Châu Thị Si; Giàng A Chư".
    - "Số: 06/2025/QĐST-HNGD" ngày 01/8/2025, Tòa án nhân dân khu vực 4 - Sơn La, công nhận thuận tình
      ly hôn giữa bà Lý Thị Pa La và ông Hàng A Minh → CHỈ gán cho BÊN NỮ Lý Thị Pa La.
    SAI NGHIÊM TRỌNG nếu điền 06/2025 cho cả hai bên và bỏ mất bản án 06/2020 của bên nam.
  Không suy diễn hay bịa khi văn bản không ghi rõ; thiếu phần nào thì bỏ field đó, không đoán.
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

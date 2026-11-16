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
  tinh + xa + chiTietDuoiXa phải từ ĐÚNG thẻ có cùng số định danh với nhóm đó; TUYỆT ĐỐI không lấy chiTietDuoiXa từ thẻ người này
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
  cư trú, kết quả tra cứu thông tin công dân, bản cam đoan, giấy tờ hộ tịch khác, bản dịch giấy tờ của bên nước
  ngoài) → BenNam_DanToc / BenNu_DanToc của người có họ tên / số định danh trên giấy đó. Hồ sơ có nhãn "Dân tộc" cho
  cả hai người thì trả ĐỦ cả hai, không bỏ sót bên nào.
- CHÉP NGUYÊN VĂN chữ trên giấy, giữ dấu nháy và chữ đứng trước: "K'Ho", "H'Mông", "Hmông", "M'Nông", "Cil",
  "Chil", "Xrê", "Ra-glai", "Chu Ru" — Python tự chuẩn hóa về option của dropdown; không tự đổi sang tên khác, không
  bỏ field chỉ vì tên lạ.
- Nếu toàn bộ hồ sơ chỉ có CCCD/Căn cước hoặc không xuất hiện nhãn "Dân tộc" → BỎ CẢ HAI field dân tộc.
- Họ tên, quê quán, nơi cư trú, địa danh, vùng miền KHÔNG phải chứng cứ dân tộc: TUYỆT ĐỐI không suy đoán dân tộc từ
  các thông tin này. Chỉ một bên có nhãn thì chỉ trả bên đó; TUYỆT ĐỐI không chép dân tộc của bên này sang bên kia.
</dan_toc>

<ly_hon>
CHỈ dùng văn bản của TÒA ÁN: tiêu đề "BẢN ÁN" hoặc "QUYẾT ĐỊNH", góc trên ghi "TÒA ÁN NHÂN DÂN ...", nội dung xử về
quan hệ hôn nhân của các đương sự. Hồ sơ không có văn bản như vậy → BỎ TOÀN BỘ *_BanAnLyHon_* và không trả mã 3,
kể cả khi tờ khai ghi "kết hôn lần thứ hai". Giấy xác nhận tình trạng hôn nhân KHÔNG phải văn bản ly hôn: giấy đó
ghi rõ người này đã ly hôn (vd "đã ly hôn ... hiện tại chưa đăng ký kết hôn với ai") thì chỉ trả *_TinhTrangHonNhan =
"3" cho đúng người đó, KHÔNG điền *_BanAnLyHon_* từ số / ngày / cơ quan của giấy xác nhận.
B0. Văn bản được tính là "văn bản ly hôn": "Quyết định công nhận thuận tình ly hôn và sự thỏa thuận của các đương
    sự", "Bản án ly hôn", "Bản án/Quyết định KHÔNG CÔNG NHẬN QUAN HỆ VỢ CHỒNG" (V/v "Không công nhận quan hệ vợ chồng,
    tranh chấp về nuôi con chung"), "Bản án/Quyết định HỦY VIỆC KẾT HÔN TRÁI PHÁP LUẬT" — tiêu đề không có chữ "ly
    hôn" vẫn là văn bản ly hôn của các đương sự trong đó.
B1. Hồ sơ RẤT HAY có NHIỀU văn bản (mỗi bên ly hôn với một người khác), nằm liền nhau trong cùng một tệp. Duyệt
    TỪNG văn bản độc lập: đọc danh sách đương sự (nguyên đơn / bị đơn / "công nhận thuận tình ly hôn giữa ... và
    ...", "không công nhận quan hệ vợ chồng giữa ... và ...") và cơ quan ban hành của CHÍNH văn bản đó.
B2. So khớp CHẶT họ tên đương sự với BenNam_HoTen / BenNu_HoTen: chỉ chuẩn hóa hoa-thường, dấu tiếng Việt và
    khoảng trắng; hoặc số CCCD/số định danh ghi trên văn bản khớp chính xác.
    TUYỆT ĐỐI không fuzzy/sửa họ tên để tạo khớp: lệch, thiếu hoặc thừa dù một chữ mà không có số CCCD khớp thì
    KHÔNG phải cùng người; cùng năm sinh, địa chỉ hay giới tính không thay được.
B3. Văn bản khớp người nào thì chỉ gán cho người đó:
    + *_BanAnLyHon_So: số văn bản nguyên văn dòng "Số:" ("Bản án số: 06/2020/HNGĐ - ST" → "06/2020/HNGĐ-ST": bỏ
      khoảng trắng quanh dấu gạch, giữ nguyên phần còn lại).
    + *_BanAnLyHon_Ngay: ngày ban hành dd/mm/yyyy (dòng "..., ngày ... tháng ... năm ..." ở đầu văn bản).
    + *_BanAnLyHon_CoQuan: tên tòa án ở GÓC TRÊN văn bản, gộp đủ các dòng ("Tòa án nhân dân huyện X, tỉnh Y").
    + *_BanAnLyHon_DuongSu: họ tên ĐẦY ĐỦ của TẤT CẢ đương sự trong CHÍNH văn bản đó, nối bằng "; ", bỏ xưng hô
      (ông/bà/anh/chị) và năm sinh. BẮT BUỘC trả kèm khi có số văn bản: hệ thống dùng để kiểm tra chéo, họ tên
      của người được gán không nằm trong danh sách này thì toàn bộ phần ly hôn của người đó bị loại.
    + *_TinhTrangHonNhan = "3" (đã ly hôn, hiện tại chưa đăng ký kết hôn với ai) cho người đó.
    Văn bản không ghi rõ phần nào (số, ngày, cơ quan) thì bỏ field đó, không đoán.
TUYỆT ĐỐI KHÔNG: lấy văn bản của bên này gán cho bên kia; dùng một văn bản điền cho CẢ HAI bên; thấy hồ sơ có một
văn bản rồi suy ra cả hai cùng văn bản đó. CHỈ khi cả họ tên bên nam và bên nữ cùng là đương sự TRONG CÙNG MỘT văn
bản thì hai bên mới dùng chung số/ngày/cơ quan. Người không có văn bản nào ghi tên → BỎ TRỐNG cả phần ly hôn của
người đó, kể cả khi người kia có.
VÍ DỤ (tên giả): hồ sơ có văn bản X (đương sự chị A và anh C) và văn bản Y (đương sự chị D và anh B); bên nữ là A,
bên nam là B → BenNu_BanAnLyHon_* lấy từ X, BenNam_BanAnLyHon_* lấy từ Y. SAI NGHIÊM TRỌNG nếu điền X cho cả hai.
TỰ KIỂM TRA TRƯỚC KHI TRẢ: với mỗi bên có *_BanAnLyHon_So, họ tên của chính bên đó BẮT BUỘC nằm trong
*_BanAnLyHon_DuongSu của bên đó. Không nằm trong → văn bản đang gán là của người khác: quét lại hồ sơ (kể cả các loại
ở B0); vẫn không có → bỏ cả phần ly hôn của bên đó. Hai bên không được có *_BanAnLyHon_So giống hệt nhau trừ khi cả
hai tên cùng nằm trong một DuongSu.
TÌNH TRẠNG HÔN NHÂN (*_TinhTrangHonNhan) chỉ trả MỘT mã số, không trả câu dài: 1 = đang có vợ/chồng; 2 = chưa đăng
ký kết hôn với ai; 3 = đã ly hôn, hiện tại chưa đăng ký; 4 = vợ/chồng đã chết; 5 = chưa đăng ký trong một khoảng
thời gian nhưng hiện đang có vợ/chồng; 6 = khác. Chỉ trả khi văn bản ly hôn theo B0–B3 (mã 3), giấy chứng tử của
vợ/chồng trước (mã 4) hoặc tờ khai ghi rõ tình trạng. Không có chứng cứ trực tiếp → bỏ field (Python tự suy từ số
lần kết hôn); không suy mã từ CCCD. Dòng ghi GỘP hai khả năng ("đã ly hôn hoặc góa vợ / chồng" trên phiếu thông tin
dân cư) không cho biết là ly hôn hay góa → không dùng dòng đó để trả mã 3 hay mã 4.
</ly_hon>

<tach_dia_chi>
Áp dụng cho MỌI field *_NoiCuTru_TrongNuoc (thẻ lẫn tờ khai):
- tinh CHỈ chứa tên tỉnh / thành phố trực thuộc trung ương, không chứa quận / huyện / xã hay phần địa chỉ chi tiết.
- KHÔNG đưa tên xã / huyện / tỉnh vào chiTietDuoiXa.
</tach_dia_chi>

<dia_chi_cccd>
Địa chỉ CCCD/CMND không tiền tố = dãy tên ngăn dấu phẩy, xếp NHỎ→LỚN. Cấp HUYỆN/QUẬN (tên thứ 2 TỪ CUỐI,
sát tỉnh) LUÔN bị XÓA HẲN — không cho vào xa lẫn chiTietDuoiXa (biểu mẫu chỉ có 2 cấp xã-tỉnh). Xử lý theo ĐÚNG
SỐ TÊN, KHÔNG được đảo:
• ĐÚNG 3 tên "A, B, C" (KHÔNG có phần chi tiết): A = xa; B = huyện → XÓA; C = tinh; chiTietDuoiXa = RỖNG.
  ⚠ Đây là chỗ HAY SAI: TUYỆT ĐỐI KHÔNG lấy B (sát tỉnh) làm xa, KHÔNG đẩy A xuống chiTietDuoiXa.
  VD1: "Nội Duệ, Tiên Du, Bắc Ninh" → xa="Nội Duệ", huyen="Tiên Du", tinh="Bắc Ninh",
  chiTietDuoiXa="".
• 4 tên "D, A, B, C" (D là chi tiết: thôn/xóm/tổ dân phố/số nhà): D = chiTietDuoiXa; A = xa; B = huyện → XÓA;
  C = tinh. VD2: "Thôn Đại Vi, Đại Đồng, Tiên Du, Bắc Ninh" → chiTietDuoiXa="Thôn Đại Vi", xa="Đại Đồng", huyen="Tiên Du",
  tinh="Bắc Ninh".
• 2 tên "A, C": A = xa; C = tinh; chiTietDuoiXa rỗng (không có huyện để xóa).
</dia_chi_cccd>
  """

"""Luật trích theo TỪNG LOẠI GIẤY của thủ tục "Đăng ký lại kết hôn" — chèn vào <quy_tac_theo_giay> của base_prompt.

Khung chung (vai trò, giấy nào → nhóm field nào, bên nam/bên nữ, định dạng, địa chỉ, output) nằm ở base_prompt; ở
đây chỉ luật riêng từng giấy. Ví dụ chỉ dùng mô tả, không dùng giá trị.
"""

EXTRA_RULES = """
<the_can_cuoc>
- SỐ ĐỊNH DANH (BenNam_SoDinhDanh, BenNu_SoDinhDanh): CHỈ đọc ở MẶT TRƯỚC thẻ, đúng dãy 12 chữ số ngay sau nhãn
  "Số / No." hoặc "Số định danh cá nhân / Personal identification number" (CMND cũ: 9 số). TUYỆT ĐỐI không lấy cụm số
  nào từ dòng MRZ/IDVNM ở mặt sau — dòng mã máy chỉ dùng để biết mặt sau là của ai (xem <hai_ben>).
- NGÀY CẤP: thẻ CĂN CƯỚC mới đọc dòng "Ngày, tháng, năm cấp / Date of issue"; thẻ CĂN CƯỚC CÔNG DÂN gắn chip đọc dòng
  "Ngày, tháng, năm / Date, month, year" ở mặt sau (cạnh chữ ký, con dấu). KHÔNG lấy "Có giá trị đến / Date of
  expiry" hay ngày sinh làm ngày cấp. Không thấy dòng ngày cấp → bỏ field.
- NƠI CẤP: trả ĐÚNG cơ quan in trên CHÍNH thẻ đó:
  + Thẻ CĂN CƯỚC mới (tiêu đề "CĂN CƯỚC" / "IDENTITY CARD"), mặt sau ghi "BỘ CÔNG AN" → "Bộ Công an".
  + Thẻ CĂN CƯỚC CÔNG DÂN gắn chip, mặt sau có "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → "Cục
    Cảnh sát quản lý hành chính về trật tự xã hội".
  + CMND cũ ghi "Công an tỉnh ..." → chép nguyên cơ quan đó.
  + Mỗi thẻ đọc riêng: hai người có thể dùng HAI loại thẻ khác nhau; không lấy nơi cấp của thẻ người này cho người kia.
- NƠI CƯ TRÚ (BenNam_NoiCuTru_TrongNuoc / BenNu_NoiCuTru_TrongNuoc): chỉ lấy "Nơi thường trú" / "Nơi cư trú" in
  trên thẻ của CHÍNH người đó — thẻ CCCD gắn chip in ở cuối MẶT TRƯỚC, thẻ CĂN CƯỚC mới in ở đầu MẶT SAU. Không lấy
  từ tờ khai, bản cam đoan hay giấy khác (trừ GIẤY THAY THẺ ở <giay_to>). Tách theo <dia_chi>.
- QUỐC TỊCH: CHỈ trả khi giấy tờ KHÔNG phải của Việt Nam. CCCD/Căn cước Việt Nam → BỎ QUA.
</the_can_cuoc>

<to_khai>
TỜ KHAI ĐĂNG KÝ LẠI KẾT HÔN chia KHỐI theo dòng, thường viết tay trên dòng chấm của mẫu in. Đọc từng khối (<hai_ben>):
- "Họ, chữ đệm, tên của vợ / của chồng" → ToKhaiNu_HoTen / ToKhaiNam_HoTen.
- "Ngày, tháng, năm sinh" → ToKhai*_NgaySinh.
- "Dân tộc" → ToKhai*_DanToc (bỏ số chú thích in sẵn "(2)"; "Quốc tịch" cùng dòng không phải dân tộc).
- "Nơi cư trú" → ToKhai*_NoiCuTru_TrongNuoc, tách theo <dia_chi>. BẮT BUỘC trả khi dòng có ghi, kể cả khi thẻ in nơi
  thường trú khác (thôn / xã cũ trước sáp nhập): Python ưu tiên nơi cư trú người dân tự khai.
- "Giấy tờ tùy thân" → ToKhai*_SoDinhDanh (dãy số), ToKhai*_NgayCap (sau "cấp ngày"), ToKhai*_NoiCap — CHỈ phần chính
  dòng đó GHI. Mẫu in sẵn cụm cơ quan "Cục CSQLHC về TTXH/Bộ Công an" để người khai gạch bớt: cụm còn nguyên cả hai cơ
  quan → BỎ ToKhai*_NoiCap; chỉ còn một cơ quan → chép cơ quan đó. KHÔNG chép ngày cấp / nơi cấp từ thẻ sang tờ khai.
Khối NGƯỜI YÊU CẦU ở đầu tờ khai (dòng "Họ, chữ đệm, tên người yêu cầu") có thể là vợ hoặc chồng; nơi cư trú / giấy tờ
của khối đó CHỈ dùng cho ToKhai*_ của người có ĐÚNG họ tên đó khi khối vợ / chồng tương ứng bỏ trống dòng ấy.
Có cả tờ khai và thẻ thì BẮT BUỘC trả CẢ HAI nhóm (ToKhai*_* và BenNam_* / BenNu_*), kể cả khi giống nhau.
Dòng "Đã đăng ký kết hôn tại" và "Theo Giấy chứng nhận kết hôn số ..., Quyển số ..." → KetHonCu_* (xem <ket_hon_cu>).
CẤP BẢN SAO — CHỈ đọc từ dòng "Đề nghị cấp bản sao: Có ☐, Không ☐" và "Số lượng: ... bản" của tờ khai:
- Ô "Có" được tích → CopyRequest_WantsCopy = "Có"; ô "Không" được tích → "Không".
- CopyRequest_Quantity = số lượng bản sao DƯƠNG ghi thật ("02 bản" → "2"). Để chấm, "0", số chú thích "(6)", "(7)"
  → KHÔNG có số lượng. Có số lượng dương thì BẮT BUỘC trả CopyRequest_WantsCopy = "Có".
- Cả hai ô TRỐNG và không có số lượng dương → BỎ CẢ HAI field (trường hợp phổ biến nhất). TUYỆT ĐỐI không mặc định.
</to_khai>

<ket_hon_cu>
Lần đăng ký kết hôn TRƯỚC ĐÂY của CHÍNH hai vợ chồng này. Nguồn được phép, theo thứ tự ưu tiên cho TỪNG field:
(1) GIẤY CHỨNG NHẬN KẾT HÔN cũ / trích lục kết hôn của hai người: số, quyển số, ngày đăng ký, cơ quan đăng ký;
(2) TỜ KHAI ĐĂNG KÝ LẠI KẾT HÔN: dòng "Đã đăng ký kết hôn tại ..." và "Theo Giấy chứng nhận kết hôn số ..., Quyển số
    ...";
(3) BẢN CAM ĐOAN: câu kể ngày và cơ quan hai người đã đến đăng ký kết hôn ("Ngày ... chúng tôi đã đến UBND xã ...
    đăng ký kết hôn").
TUYỆT ĐỐI KHÔNG lấy KetHonCu_* từ: giấy khai sinh / trích lục khai sinh của con (số, quyển số, ngày, nơi đăng ký
khai sinh), CCCD, ngày ký / ngày lập tờ khai hoặc bản cam đoan (dòng "..., ngày ... tháng ... năm ..." đầu / cuối
giấy, cạnh chữ ký), "Quyển số" in ở góc giấy không thuộc lần đăng ký kết hôn cũ, số / ngày của một văn bản xác nhận khác,
số của bản sao / trích lục cấp lại (số có đuôi "-BS", "TL.KH"; số gốc ghi ở dòng "Số đăng ký" / "đã đăng ký kết
hôn ... số" của chính trích lục đó), giấy chứng nhận / trích lục kết hôn cấp trong CHÍNH lần đăng ký lại này (ghi
"đăng ký lại", ngày cấp năm nay), dòng
"Kính gửi: UBND ..." (cơ quan nhận hồ sơ lần này, không phải nơi đăng ký cũ).
- KetHonCu_So / KetHonCu_QuyenSo: chỉ giá trị người khai GHI THẬT ngay sau nhãn. Mẫu tờ khai in sẵn số chú thích
  "(5)" ngay sau "số:" và "Quyển số:" (chú thích "(5) Chỉ khai trong trường hợp biết rõ") → đó là ô TRỐNG, BỎ field;
  không bao giờ trả "5" / "(5)" từ chỗ đó.
- KetHonCu_NgayDangKy: dd/mm/yyyy. Nguồn chỉ ghi năm ("năm 1978") hoặc tháng/năm → BỎ field.
- Nơi đăng ký: KetHonCu_XaDangKy = "Phường/Xã/Thị trấn <tên>" của cơ quan đăng ký (bỏ "UBND"); KetHonCu_TinhDangKy =
  tỉnh / thành phố ghi trong cùng cụm cơ quan đó, chép như giấy ghi (kể cả tỉnh cũ đã giải thể / sáp nhập). Cụm "UBND
  xã A, huyện B, tỉnh C" → XaDangKy "Xã A", TinhDangKy "C" (huyện B bỏ). CHỈ khi chính cơ quan đăng ký là UBND cấp
  HUYỆN (cụm bắt đầu bằng "UBND huyện / quận / thị xã / thành phố ...", không có xã / phường đứng trước) → BỎ
  KetHonCu_XaDangKy, vẫn trả tỉnh.
- KetHonCu_So chỉ là SỐ của giấy chứng nhận / số đăng ký, không bao giờ là ngày ("ngày ... tháng ... năm ...").
  Cụm ghi "xã A ... nay là phường / xã B ..." → KetHonCu_XaDangKy = tên SAU "nay là" (B), KetHonCu_TinhDangKy = tỉnh
  của B nếu có ghi.
- Nguồn ưu tiên cao hơn đọc rõ thì dùng nguồn đó; hai nguồn ghi khác nhau mà nguồn cao không rõ → nguồn kế tiếp. Không
  có nguồn → BỎ FIELD, không đoán, không ghép số từ dòng khác.
</ket_hon_cu>

<dan_toc>
CCCD/Căn cước gắn chip KHÔNG ghi dân tộc. Dân tộc CHỈ lấy khi giấy có NHÃN "Dân tộc" ghi giá trị cho đúng người:
- Dòng "Dân tộc" trong khối vợ / chồng của TỜ KHAI → ToKhaiNu_DanToc / ToKhaiNam_DanToc. Tờ khai thường ghi CẢ HAI
  khối → BẮT BUỘC trả ĐỦ CẢ HAI, kể cả khi giống nhau.
- Nhãn "Dân tộc" trên giấy khác của đúng một người → BenNam_DanToc / BenNu_DanToc, BẮT BUỘC trả khi có:
  + giấy chứng nhận kết hôn cũ (khối chồng / vợ), bản cam đoan, xác nhận / phiếu thông tin cư trú, kết quả tra cứu;
  + giấy khai sinh / trích lục khai sinh của con: khối CHA (họ tên trùng chồng) → BenNam_DanToc, khối MẸ (họ tên
    trùng vợ) → BenNu_DanToc. Đối chiếu họ tên trước khi gán.
- CHÉP NGUYÊN VĂN chữ trên giấy ("H'Mông", "Hmông", "Tày", "Nùng"...) — Python tự chuẩn hoá về option dropdown.
- Không xuất hiện nhãn "Dân tộc" → BỎ. Họ tên, quê quán, địa danh KHÔNG phải chứng cứ dân tộc. Không chép dân tộc của
  bên này sang bên kia, không lấy dân tộc của con.
</dan_toc>

<dia_chi_cccd>
Địa chỉ CCCD/CMND không tiền tố = dãy tên ngăn dấu phẩy, xếp NHỎ→LỚN. Cấp HUYỆN/QUẬN (tên thứ 2 TỪ CUỐI, sát tỉnh)
LUÔN bị XÓA HẲN — không cho vào xa lẫn chiTietDuoiXa. Xử lý theo ĐÚNG SỐ TÊN:
• ĐÚNG 3 tên "A, B, C" (không có phần chi tiết): A = xa; B = huyện → XÓA; C = tinh; chiTietDuoiXa = RỖNG.
• 4 tên "D, A, B, C" (D là chi tiết: thôn/xóm/tổ dân phố/số nhà): D = chiTietDuoiXa; A = xa; B = huyện → XÓA; C = tinh.
• 2 tên "A, C": A = xa; C = tinh; chiTietDuoiXa rỗng.
</dia_chi_cccd>
"""

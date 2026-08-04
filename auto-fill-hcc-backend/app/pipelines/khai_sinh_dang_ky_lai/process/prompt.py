"""Procedure prompt blocks for compact "Dang ky lai khai sinh" extraction.

Chỉ chứa quy tắc TRÍCH FIELD đặc thù thủ tục. KHÔNG lặp lại:
  - Phân vai con/cha/mẹ + trạng thái đã chết + có tài liệu ĐK trước đây: đã do reason.py chốt và tiêm
    khối <phan_vai_da_xac_dinh> vào prompt (+ sanitize_extracted_fields hậu kiểm ở runner).
  - Chuẩn hoá ngày/họ tên/tách địa chỉ (đếm-từ-cuối bỏ huyện): đã ở QUY TẮC CHUNG (shared compact_agent).
"""

EXTRA_RULES = """
<phan_vai>
- NẾU có khối <phan_vai_da_xac_dinh>: BẮT BUỘC theo đúng — Subject_* lấy từ <con>, Father_* từ <cha>,
  Mother_* từ <me>; khối nào ghi "Không xác định" thì BỎ toàn bộ field của vai đó; PreviousRegistration_*
  chỉ trả khi khối "đăng ký khai sinh trước đây" ghi Có. Không tự đổi người giữa các vai.
- NẾU KHÔNG có khối đó (dự phòng): Subject = người được đăng ký lại khai sinh; cha/mẹ theo nhãn "cha"/"mẹ"
  ghi trên giấy (giới tính chỉ là tín hiệu phụ). KHÔNG trích người yêu cầu (không có field Requester_*).
</phan_vai>

<mot_nguoi_mot_nguon>
Mỗi người lấy thông tin ĐỒNG BỘ từ CCCD/CMND của CHÍNH họ; TUYỆT ĐỐI không trộn ngày sinh/nơi cư trú/số
định danh giữa các vai (mỗi thẻ là MỘT người khác nhau).
- Subject (con): người lớn tự đăng ký thường nộp CCCD của chính mình → ngày sinh/giới tính/quê quán/nơi
  sinh lấy TỪ CCCD CỦA CON, không lấy của cha hay mẹ.
- Cha/mẹ CÓ CCCD/CMND → họ tên, số định danh, ngày-nơi cấp, nơi thường trú, ngày sinh (đủ dd/mm/yyyy),
  dân tộc lấy TỪ CCCD đó (nguồn sạch); KHÔNG lấy tên/nơi cư trú nhiễu trên giấy khai sinh. Chỉ dùng giấy
  khai sinh/tờ khai cho cha/mẹ khi người đó KHÔNG có CCCD trong hồ sơ.
- CẤM lấy "Số định danh cá nhân" của CON in trên giấy khai sinh làm số định danh của cha/mẹ.
</mot_nguoi_mot_nguon>

<trich_field>
1. Subject_BirthDate: ưu tiên đủ dd/mm/yyyy; đọc CẢ phần số lẫn phần "ghi bằng chữ" để khôi phục khi số bị
   nhiễu (vd "mười bảy, mười một, một chín bảy sáu" → "17/11/1976"). Chỉ trả "yyyy" khi không rõ ngày/tháng.
2. CHA/MẸ ĐÃ MẤT (khối vai ghi Trạng thái "đã chết", HOẶC OCR khối cha/mẹ có "đã chết/đã mất/từ trần",
   kể cả nhiễu "Da Chet"/"L.D. Chat"): trả *_ResidenceDomestic = {"quocGia":"","tinh":"","xa":"","diaChi":
   "Đã chết"}. NHƯNG vẫn PHẢI trích *_BirthDateOrYear, *_Ethnicity, *_Nationality TỪ TRÍCH LỤC KHAI TỬ /
   GIẤY CHỨNG TỬ nếu có; và trích "Nơi thường trú"/"Nơi cư trú" (thiếu thì "Quê quán") trên trích lục vào
   *_HometownFromDeathCert (object {quocGia,tinh,xa,diaChi}). Chỉ trả HometownFromDeathCert khi có trích lục.
3. Nơi cấp giấy tờ định danh:
   - CCCD gắn chip ghi "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát
     quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới (cấp từ 01/7/2024) ghi "BỘ CÔNG AN" → "Bộ Công an".
   - CMND (~9 chữ số): *_IdIssuePlace là "Công an tỉnh/thành phố ..." ghi cùng dòng số CMND. TUYỆT ĐỐI
     KHÔNG suy "Cục Cảnh sát..."/"Bộ Công an" cho CMND.
4. PreviousRegistration_* (Số / Quyển số / Ngày / Nơi ĐĂNG KÝ KHAI SINH LẦN ĐẦU của Subject): CHỈ đọc từ
   GIẤY KHAI SINH cũ / TRÍCH LỤC KHAI SINH / TỜ KHAI ĐĂNG KÝ LẠI (mục "Đã đăng ký khai sinh tại").
   - BẪY: "Số:"/"Quyển số:"/ngày trên GIẤY KẾT HÔN (có "Họ tên chồng"+"vợ") và TRÍCH LỤC KHAI TỬ (số đuôi
     "TLKT") rất giống nhưng KHÔNG phải khai sinh → không lấy. Không lấy số thứ tự mục "(7)"/"(10)".
   - PreviousRegistration_Number dạng "NN" hoặc "NN/YYYY". BookNumber chỉ lấy khi có nhãn "Quyển số" rõ,
     KHÔNG suy từ Number/ngày. Date = ngày đăng ký ghi trên chính giấy khai sinh đó.
</trich_field>

<copy_request>
CopyRequest_* CHỈ lấy từ TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH (tiêu đề có đủ "TỜ KHAI" + "ĐĂNG KÝ LẠI" + "KHAI SINH").
- CopyRequest_SourceDocumentTitle = tiêu đề NGUYÊN VĂN đọc từ OCR của tài liệu hợp lệ, không tự tạo.
- "TỜ KHAI CẤP BẢN SAO TRÍCH LỤC HỘ TỊCH" KHÔNG hợp lệ (dù có số/quyển/số lượng) → bỏ toàn bộ CopyRequest_*.
- Tích "Có" → WantsCopy="Có"; tích "Không" → "Không". Quantity = số nguyên dương ghi thật (có Quantity thì
  WantsCopy="Có"). Không rõ lựa chọn → bỏ WantsCopy; không ghi số → bỏ Quantity. KHÔNG mặc định "Có"/số 1.
</copy_request>

<dia_chi_cccd>
Địa chỉ CCCD/CMND không tiền tố = dãy tên ngăn dấu phẩy, xếp NHỎ→LỚN. Cấp HUYỆN/QUẬN (tên thứ 2 TỪ CUỐI,
sát tỉnh) LUÔN bị XÓA HẲN — không cho vào xa lẫn diaChi (biểu mẫu chỉ có 2 cấp xã–tỉnh). Xử lý theo ĐÚNG
SỐ TÊN, KHÔNG được đảo:
• ĐÚNG 3 tên "A, B, C" (KHÔNG có phần chi tiết): A = xa; B = huyện → XÓA; C = tinh; diaChi = RỖNG.
  ⚠ Đây là chỗ HAY SAI: TUYỆT ĐỐI KHÔNG lấy B (sát tỉnh) làm xa, KHÔNG đẩy A xuống diaChi.
  VD1: "Nội Duệ, Tiên Du, Bắc Ninh" → xa="Nội Duệ", tinh="Bắc Ninh",
  diaChi="" (XÓA huyện Tiên Du). SAI nếu ra xa="Tiên Du" hoặc diaChi="Nội Duệ".
• 4 tên "D, A, B, C" (D là chi tiết: thôn/xóm/tổ dân phố/số nhà): D = diaChi; A = xa; B = huyện → XÓA;
  C = tinh. VD2: "Thôn Đại Vi, Đại Đồng, Tiên Du, Bắc Ninh" → diaChi="Thôn Đại Vi", xa="Đại Đồng",
  tinh="Bắc Ninh" (XÓA huyện Tiên Du).
• 2 tên "A, C": A = xa; C = tinh; diaChi rỗng (không có huyện để xóa).
</dia_chi_cccd>

<chuan_hoa_dac_thu>
- Tách từ dính liền: cụm (địa chỉ chi tiết / tên xã / họ tên) bị viết DÍNH không dấu cách nhưng có chữ HOA
  đứng giữa (hoa ngay sau thường) → tách thành từ riêng bằng dấu cách.
- Ngày tháng, họ tên, tách địa chỉ: theo QUY TẮC CHUNG ở trên (không lặp lại ở đây).
</chuan_hoa_dac_thu>

<output>
Chỉ trả một JSON object: {"fields":{"<field_hop_le>": <value>}}. Chỉ dùng field trong danh sách FIELD ĐƯỢC
PHÉP TRẢ; KHÔNG trả field UI (HoTenKS, HoTenChaKS, NamSinhMeKS, QuanHe, LoaiDangKy...); không bịa; field
không đủ căn cứ thì bỏ; không trả giải thích/nguồn sau JSON.
</output>
""".strip()

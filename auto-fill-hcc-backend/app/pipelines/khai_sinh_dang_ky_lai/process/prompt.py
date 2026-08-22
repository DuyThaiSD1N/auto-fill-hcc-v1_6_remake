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
  ghi trên giấy (giới tính chỉ là tín hiệu phụ).
</phan_vai>

<nguoi_yeu_cau>
Khối "Thông tin người yêu cầu" trên biểu mẫu bắt đầu bằng ô tích "Quan hệ với người được khai sinh:
Bản thân / Cha / Mẹ / Khác". Nguồn duy nhất để chốt ô này là TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH.

0. NẾU có khối <quan_he_nguoi_yeu_cau> trong <phan_vai_da_xac_dinh>: quan hệ ĐÃ ĐƯỢC CHỐT ở bước
   phân vai (agent đã đối chiếu người yêu cầu với người được đăng ký lại khai sinh, Python đã kiểm
   chứng). Requester_RelationToSubject phải TRẢ ĐÚNG kết luận đó, không tự suy lại; riêng khi khối
   <to_khai_dang_ky_lai> ghi "Không" thì BỎ TRỐNG cả field này:
   "bản thân" → "Bản thân"; "cha" → "Cha"; "mẹ" → "Mẹ"; "khác" → "Khác";
   "không xác định" → bỏ field.
1. CÓ TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH trong hồ sơ (tiêu đề có đủ "TỜ KHAI" + "ĐĂNG KÝ LẠI" + "KHAI SINH",
   hoặc khối <to_khai_dang_ky_lai> ghi "Có"):
   - Requester_RelationToSubject = quy chuẩn dòng "Quan hệ với người được khai sinh" / "Quan hệ với người
     được đăng ký lại khai sinh" về ĐÚNG MỘT trong "Bản thân" | "Cha" | "Mẹ" | "Khác".
     • Tờ khai ghi "Bản thân"/"Tự khai"/"Chính mình", HOẶC họ tên (và số định danh) người yêu cầu TRÙNG
       người được đăng ký lại khai sinh → "Bản thân".
     • Trùng cha → "Cha"; trùng mẹ → "Mẹ"; còn lại (ông, bà, anh, chị, em, con, cháu, người được ủy
       quyền...) → "Khác" và ghi thêm chữ nguyên văn vào Requester_Relationship.
   - Requester_FullName/IdNumber/IdIssueDate/IdIssuePlace/ResidenceDomestic = nhân thân người yêu cầu
     ghi trên tờ khai; thiếu thì lấy tiếp từ CCCD/CMND CỦA CHÍNH người yêu cầu đó. VẪN PHẢI trả kể cả khi
     người yêu cầu chính là con/cha/mẹ (không được bỏ vì "đã có Subject_*/Father_*/Mother_*").
   - Requester_SourceDocumentTitle = tiêu đề NGUYÊN VĂN của tờ khai đó (bằng chứng nguồn là tờ khai).
2. KHÔNG CÓ TỜ KHAI (hồ sơ chỉ có CCCD/CMND, kèm hoặc không kèm giấy khai sinh cũ): không tài liệu nào
   nói ai đang đi nộp hồ sơ → BỎ TRỐNG toàn bộ Requester_* (kể cả Requester_RelationToSubject).
   Cổng đã tự điền khối người yêu cầu từ tài khoản VNeID đang đăng nhập; Python chỉ tick "Khác" để tách
   khối đó ra, KHÔNG ghi đè, rồi đổ toàn bộ dữ liệu quét được vào các khối con/cha/mẹ.
   TUYỆT ĐỐI KHÔNG bịa Requester_* từ CCCD của con/cha/mẹ hay từ tên trên giấy khai sinh cũ.
3. Vì vậy CCCD/CMND của CHÍNH người được đăng ký lại khai sinh phải được trích đủ vào Subject_IdNumber,
   Subject_IdIssueDate, Subject_IdIssuePlace, Subject_ResidenceDomestic (ngoài họ tên/ngày sinh/giới tính).
   Đây là nguồn duy nhất của khối "Người được đăng ký lại khai sinh" — thiếu là hỏng cả khối. KHÔNG lấy
   số định danh hay nơi thường trú của cha/mẹ gán cho Subject_*.
</nguoi_yeu_cau>

<mot_nguoi_mot_nguon>
Mỗi người lấy thông tin ĐỒNG BỘ từ CCCD/CMND của CHÍNH họ; TUYỆT ĐỐI không trộn ngày sinh/nơi cư trú/số
định danh giữa các vai (mỗi thẻ là MỘT người khác nhau).

⚠️⚠️⚠️ QUY TẮC BẮT BUỘC - XÁC ĐỊNH CHA/MẸ DựA VÀO GIỚI TÍNH TRÊN CCCD:

**BƯỚC 1: ĐẾM VÀ PHÂN LOẠI CCCD THEO GIỚI TÍNH**
- Đọc TẤT CẢ CCCD/CMND trong hồ sơ
- Mỗi CCCD có field "Giới tính / Sex": "Nam" hoặc "Nữ"
- Phân loại:
  * CCCD có "Giới tính: Nam" → Danh sách NAM
  * CCCD có "Giới tính: Nữ" → Danh sách NỮ

**BƯỚC 2: XÁC ĐỊNH VAI TRÒ - QUY TẮC BẮT BUỘC**

A. Nếu có 2 CCCD (1 Nam + 1 Nữ):
   - CCCD có tuổi TRẺ HƠN (năm sinh SAU, gần hiện tại hơn) → CON (Subject_*)
   - CCCD còn lại:
     * Nếu là NAM → CHA (Father_*)
     * Nếu là NỮ → MẸ (Mother_*)
   - ⚠️ BỎ TRỐNG vai còn thiếu:
     * Nếu không có CCCD Nam nào khác → BỎ TRỐNG TẤT CẢ Father_*
     * Nếu không có CCCD Nữ nào khác → BỎ TRỐNG TẤT CẢ Mother_*

B. Nếu có 2 CCCD (cùng 2 Nam HOẶC cùng 2 Nữ):
   - CCCD có tuổi TRẺ HƠN → CON (Subject_*)
   - CCCD có tuổi LỚN HƠN:
     * Nếu cả 2 đều NAM → người lớn tuổi là CHA (Father_*), BỎ TRỐNG Mother_*
     * Nếu cả 2 đều NỮ → người lớn tuổi là MẸ (Mother_*), BỎ TRỐNG Father_*

C. Nếu có 3 CCCD:
   - Tìm CCCD TRẺ TUỔI NHẤT → CON (Subject_*)
   - Trong 2 CCCD còn lại:
     * CCCD có "Giới tính: Nam" → CHA (Father_*)
     * CCCD có "Giới tính: Nữ" → MẸ (Mother_*)

**BƯỚC 3: ĐIỀN THÔNG TIN - CẤM TUYỆT ĐỐI**

✅ ĐÚNG:
- Father_* CHỈ lấy từ CCCD có "Giới tính: Nam"
- Mother_* CHỈ lấy từ CCCD có "Giới tính: Nữ"
- Mỗi CCCD CHỈ dùng cho MỘT vai (không duplicate)

❌ CẤM TUYỆT ĐỐI:
- ❌ CẤM lấy CCCD "Giới tính: Nữ" điền vào Father_* 
  (Father phải là Nam, Mother phải là Nữ)
- ❌ CẤM lấy CCCD "Giới tính: Nam" điền vào Mother_*
  (Mother phải là Nữ, Father phải là Nam)
- ❌ CẤM duplicate: cùng 1 người vào 2 vai khác nhau
- ❌ CẤM lấy thông tin CON sang CHA/MẸ
- ❌ CẤM đoán: Nếu không có CCCD Nam (ngoài CON) → BỎ TRỐNG Father_*
- ❌ CẤM đoán: Nếu không có CCCD Nữ (ngoài CON) → BỎ TRỐNG Mother_*
- ❌ CẤM tự thêm địa chỉ "Đã chết" khi không có CCCD: nếu thiếu Father/Mother → BỎ TRỐNG, KHÔNG trả Father_ResidenceDomestic hoặc Mother_ResidenceDomestic

**VÍ DỤ CỤ THỂ:**

Có 2 CCCD:
- CCCD 1: Người A, Giới tính: Nam, Năm sinh: 1984
- CCCD 2: Người B, Giới tính: Nữ, Năm sinh: 1953

→ Người TRẺ HƠN (1984) = Subject_*
→ Người LỚN TUỔI (1953) + Nữ = Mother_*
→ KHÔNG có Father_* (bỏ trống hoàn toàn)

- Subject (con): người lớn tự đăng ký thường nộp CCCD của chính mình → ngày sinh/giới tính/quê quán/nơi
  sinh lấy TỪ CCCD CỦA CON, không lấy của cha hay mẹ.
- Cha/mẹ CÓ CCCD/CMND → họ tên, số định danh, ngày-nơi cấp, nơi thường trú, ngày sinh (đủ dd/mm/yyyy),
  dân tộc lấy TỪ CCCD đó (nguồn sạch); KHÔNG lấy tên/nơi cư trú nhiễu trên giấy khai sinh. Chỉ dùng giấy
  khai sinh/tờ khai cho cha/mẹ khi người đó KHÔNG có CCCD trong hồ sơ.
- CẤM lấy "Số định danh cá nhân" của CON in trên giấy khai sinh làm số định danh của cha/mẹ.
- BẮT BUỘC trả Father_Gender / Mother_Gender = giới tính GHI TRÊN chính giấy tờ đã dùng cho vai đó
  ("Nam"/"Nữ"). Đây là căn cứ để hậu kiểm: thẻ ghi "Nữ" mà điền vào Father_* sẽ bị XÓA sạch vai cha
  (và ngược lại). Không suy giới tính từ tên người.
- HỒ SƠ THIẾU MỘT BÊN (chỉ có con + CCCD mẹ, hoặc chỉ có con + CCCD cha): BỎ TRỐNG HOÀN TOÀN vai còn
  lại — không trả BẤT KỲ field nào của vai đó, kể cả Nationality/Ethnicity/ResidenceDomestic. Thà để
  cổng trống còn hơn điền dữ liệu của con hoặc của bên kia sang.
</mot_nguoi_mot_nguon>

<trich_field>
1. Subject_BirthDate: ưu tiên đủ dd/mm/yyyy; đọc CẢ phần số lẫn phần "ghi bằng chữ" để khôi phục khi số bị
   nhiễu (vd "mười bảy, mười một, một chín bảy sáu" → "17/11/1976"). Chỉ trả "yyyy" khi không rõ ngày/tháng.
2. CHA/MẸ ĐÃ MẤT (khối vai ghi Trạng thái "đã chết", HOẶC OCR khối cha/mẹ có "đã chết/đã mất/từ trần",
   kể cả nhiễu "Da Chet"/"L.D. Chat"):
   - HỌ TÊN: Ưu tiên lấy từ CCCD nếu có trong hồ sơ; nếu không có CCCD thì lấy từ TRÍCH LỤC KHAI TỬ /
     GIẤY CHỨNG TỬ (dòng "Họ tên người chết" hoặc "Họ và tên").
   - ĐỊA CHỈ: Trả *_ResidenceDomestic = {"quocGia":"","tinh":"","xa":"","diaChi":"Đã chết"}.
   - THÔNG TIN KHÁC: Vẫn PHẢI trích *_BirthDateOrYear, *_Ethnicity, *_Nationality TỪ TRÍCH LỤC KHAI TỬ /
     GIẤY CHỨNG TỬ nếu có (dòng "Ngày, tháng, năm sinh", "Dân tộc", "Quốc tịch").
   - ĐỊA CHỈ TỪ GIẤY KHAI TỬ: Trích "Nơi thường trú"/"Nơi cư trú" (thiếu thì "Quê quán") trên trích lục 
     vào *_HometownFromDeathCert (object {quocGia,tinh,xa,diaChi}). Chỉ trả HometownFromDeathCert khi có trích lục.
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
⚠️⚠️⚠️ KIỂM TRA BẮT BUỘC TRƯỚC KHI TRẢ OUTPUT:

1. **KIỂM TRA DUPLICATE TÊN**:
   - Nếu Father_FullName = Mother_FullName → XÓA MỘT TRONG HAI (giữ người đúng giới tính)
   - Nếu Father_IdNumber = Mother_IdNumber → XÓA MỘT TRONG HAI

2. **KIỂM TRA GIỚI TÍNH**:
   - Nếu có Father_FullName nhưng người đó là NỮ (từ CCCD "Giới tính: Nữ") → XÓA TẤT CẢ Father_*, điền vào Mother_*
   - Nếu có Mother_FullName nhưng người đó là NAM (từ CCCD "Giới tính: Nam") → XÓA TẤT CẢ Mother_*, điền vào Father_*

3. **KIỂM TRA DUPLICATE VỚI CON**:
   - Nếu Father_FullName = Subject_FullName → XÓA TẤT CẢ Father_*
   - Nếu Mother_FullName = Subject_FullName → XÓA TẤT CẢ Mother_*

Chỉ trả một JSON object: {"fields":{"<field_hop_le>": <value>}}. Chỉ dùng field trong danh sách FIELD ĐƯỢC
PHÉP TRẢ; KHÔNG trả field UI (HoTenKS, HoTenChaKS, NamSinhMeKS, QuanHe, LoaiDangKy...); không bịa; field
không đủ căn cứ thì bỏ; không trả giải thích/nguồn sau JSON.
</output>
""".strip()

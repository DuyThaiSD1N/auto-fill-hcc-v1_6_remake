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

<uu_tien_nguon>
⚠️ THỨ TỰ NGUỒN — TỜ KHAI TRƯỚC, CCCD SAU. Áp dụng cho MỌI vai (người yêu cầu, con, cha, mẹ):

1. TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH là NGUỒN SỐ 1. Vai của từng người lấy đúng theo nhãn in sẵn:
   • "Họ, chữ đệm, tên người yêu cầu" → Requester_*
   • mục "Đề nghị cơ quan đăng ký lại khai sinh cho người có tên dưới đây" → Subject_*
   • "Họ, chữ đệm, tên người mẹ" → Mother_*   • "Họ, chữ đệm, tên người cha" → Father_*
   Mọi mục tờ khai CÓ GHI (ngày sinh, giới tính, dân tộc, quốc tịch, nơi sinh, quê quán, nơi cư trú,
   giấy tờ tùy thân) đều PHẢI trả theo tờ khai, kể cả khi tờ khai viết tay.
2. CCCD/CMND, trích lục khai tử/giấy chứng tử, giấy khai sinh cũ là NGUỒN BÙ (fallback): chỉ dùng cho
   field mà tờ khai BỎ TRỐNG hoặc OCR không đọc nổi, và chỉ của CHÍNH người đó (khớp họ tên hoặc số
   định danh với người ghi trên tờ khai).
3. ❌ CẤM dùng CCCD để ĐỔI VAI mà tờ khai đã chốt. Thẻ của mẹ không được đẩy sang vai cha/con dù giới
   tính hay năm sinh trông "hợp lý" hơn. Tờ khai ghi ai là mẹ thì người đó là mẹ.
4. Hồ sơ có tờ khai mà một vai KHÔNG có CCCD (vd cha đã mất, chỉ có trích lục khai tử): VẪN PHẢI trả
   đủ field của vai đó theo tờ khai. Thiếu CCCD KHÔNG phải lý do bỏ trống vai.
5. Chính tả họ tên: giữ đúng người theo tờ khai, nhưng nếu chính người đó có CCCD/trích lục trong hồ sơ
   thì viết họ tên theo giấy tờ gốc (bản đánh máy chuẩn hơn chữ viết tay), vd tờ khai "Nguyễn Văn Câu"
   + trích lục khai tử "NGUYỄN VĂN CẦU" → Father_FullName = "NGUYỄN VĂN CẦU".
6. Số định danh / ngày cấp / nơi cấp: lệch giữa tờ khai và CCCD của CÙNG một người thì lấy theo CCCD.
7. HỒ SƠ KHÔNG CÓ TỜ KHAI thì mới dùng khối <phan_vai_khi_khong_co_to_khai> bên dưới.
</uu_tien_nguon>

<mot_nguoi_mot_nguon>
Mỗi người lấy thông tin ĐỒNG BỘ từ giấy tờ của CHÍNH họ; TUYỆT ĐỐI không trộn ngày sinh/nơi cư trú/số
định danh giữa các vai (mỗi thẻ là MỘT người khác nhau).

- CẤM lấy "Số định danh cá nhân" của CON in trên giấy khai sinh làm số định danh của cha/mẹ.
- BẮT BUỘC trả Father_Gender / Mother_Gender = giới tính GHI TRÊN chính giấy tờ đã dùng cho vai đó
  ("Nam"/"Nữ"). Đây là căn cứ để hậu kiểm: thẻ ghi "Nữ" mà điền vào Father_* sẽ bị XÓA sạch vai cha
  (và ngược lại). Không suy giới tính từ tên người. Tờ khai không ghi giới tính cha/mẹ thì suy theo
  chính nhãn quan hệ trên tờ khai: mục "người cha" → "Nam", mục "người mẹ" → "Nữ".
- HỒ SƠ THIẾU MỘT BÊN (tờ khai không ghi cha, hoặc chỉ có con + CCCD một bên): BỎ TRỐNG HOÀN TOÀN vai
  còn lại — không trả BẤT KỲ field nào của vai đó, kể cả Nationality/Ethnicity/ResidenceDomestic. Thà
  để cổng trống còn hơn điền dữ liệu của con hoặc của bên kia sang.
- ❌ CẤM tự thêm địa chỉ "Đã chết" khi không có căn cứ: chỉ trả *_ResidenceDomestic = {"diaChi":"Đã chết"}
  khi tờ khai/giấy tờ ghi rõ người đó đã mất.
</mot_nguoi_mot_nguon>

<phan_vai_khi_khong_co_to_khai>
CHỈ dùng khối này khi hồ sơ KHÔNG có tờ khai đăng ký lại khai sinh (và không giấy tờ nào chỉ đích danh
người được đăng ký lại). Khi đó vai phải suy từ CCCD theo giới tính + thế hệ:

**BƯỚC 1: PHÂN LOẠI CCCD THEO GIỚI TÍNH** — mỗi CCCD có field "Giới tính / Sex": "Nam" hoặc "Nữ".

**BƯỚC 2: XÁC ĐỊNH VAI**
A. 2 CCCD (1 Nam + 1 Nữ): người TRẺ HƠN (năm sinh gần hiện tại hơn) → CON (Subject_*); người còn lại
   NAM → CHA (Father_*), NỮ → MẸ (Mother_*). Vai không có thẻ nào → BỎ TRỐNG hoàn toàn.
B. 2 CCCD cùng giới: người TRẺ HƠN → CON; người LỚN HƠN là CHA nếu cả hai Nam (bỏ trống Mother_*),
   là MẸ nếu cả hai Nữ (bỏ trống Father_*).
C. 3 CCCD: TRẺ NHẤT → CON; trong hai người còn lại, "Giới tính: Nam" → CHA, "Giới tính: Nữ" → MẸ.

**BƯỚC 3: CẤM TUYỆT ĐỐI**
- ❌ CẤM điền CCCD "Giới tính: Nữ" vào Father_*, CCCD "Giới tính: Nam" vào Mother_*.
- ❌ CẤM dùng cùng một người cho hai vai, hoặc lấy thông tin CON sang CHA/MẸ.
- ❌ CẤM đoán: không có CCCD Nam (ngoài CON) → BỎ TRỐNG Father_*; không có CCCD Nữ → BỎ TRỐNG Mother_*.

VÍ DỤ: CCCD 1 = Người A, Nam, sinh 1984; CCCD 2 = Người B, Nữ, sinh 1953
→ trẻ hơn (1984) = Subject_*; lớn tuổi + Nữ = Mother_*; KHÔNG có Father_* (bỏ trống hoàn toàn).
</phan_vai_khi_khong_co_to_khai>

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
• ⚠ Ô "Nơi thường trú" trên CCCD RẤT HAY BỊ XUỐNG DÒNG giữa chừng: số nhà/tên đường nằm ở dòng
  TRÊN, còn xã/huyện/tỉnh ở dòng DƯỚI. PHẢI GHÉP CẢ HAI DÒNG thành MỘT chuỗi rồi mới tách theo
  dấu phẩy — lấy mỗi dòng đầu là rơi mất tên đường.
  VD3: dòng 1 "Số Nhà 15/3C" + dòng 2 "Hai Bà Trưng, P.6, Đà Lạt, Lâm Đồng"
  → ghép: "Số Nhà 15/3C Hai Bà Trưng, P.6, Đà Lạt, Lâm Đồng"
  → diaChi="Số Nhà 15/3C Hai Bà Trưng", xa="P.6", tinh="Lâm Đồng" (XÓA huyện Đà Lạt).
  SAI nếu diaChi chỉ còn "Số Nhà 15/3C" (mất đường) hoặc chỉ còn "Hai Bà Trưng" (mất số nhà).
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

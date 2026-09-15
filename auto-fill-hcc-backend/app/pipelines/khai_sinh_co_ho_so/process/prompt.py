"""Procedure prompt blocks cho compact extraction "Đăng ký khai sinh cho người đã có hồ sơ, giấy tờ cá nhân".

Chỉ chứa quy tắc TRÍCH FIELD đặc thù thủ tục. KHÔNG lặp lại:
  - Phân vai con/cha/mẹ + trạng thái đã chết: đã do reason.py chốt và tiêm khối <phan_vai_da_xac_dinh>
    vào prompt (+ sanitize_extracted_fields hậu kiểm ở runner).
  - Chuẩn hoá ngày/họ tên/tách địa chỉ (đếm-từ-cuối bỏ huyện): đã ở QUY TẮC CHUNG (shared compact_agent).
"""

EXTRA_RULES = """
<boi_canh_thu_tuc>
Thủ tục: ĐĂNG KÝ KHAI SINH CHO NGƯỜI ĐÃ CÓ HỒ SƠ, GIẤY TỜ CÁ NHÂN (mã 1.004772).
Người được khai sinh CHƯA TỪNG được đăng ký khai sinh, nhưng ĐÃ CÓ hồ sơ/giấy tờ cá nhân: CCCD/CMND,
thẻ BHYT, giấy tờ chứng minh nơi cư trú, học bạ, hồ sơ học tập, bằng tốt nghiệp, giấy chứng nhận,
chứng chỉ, giấy chứng nhận kết hôn, giấy đề nghị xác nhận của cơ quan quản lý. Người này THƯỜNG LÀ
NGƯỜI LỚN và rất hay tự đi làm thủ tục cho chính mình.

❌ KHÔNG có khối "đăng ký khai sinh trước đây": hồ sơ KHÔNG có giấy khai sinh cũ/trích lục khai sinh
của người này. Thấy "Số:", "Quyển số:", ngày đăng ký trên GIẤY CHỨNG NHẬN KẾT HÔN hay TRÍCH LỤC KHAI TỬ
thì BỎ QUA — không có field nào để trả.
</boi_canh_thu_tuc>

<phan_vai>
- NẾU có khối <phan_vai_da_xac_dinh>: BẮT BUỘC theo đúng — Subject_* lấy từ <con>, Father_* từ <cha>,
  Mother_* từ <me>; khối nào ghi "Không xác định" thì BỎ toàn bộ field của vai đó. Không tự đổi người
  giữa các vai.
- NẾU KHÔNG có khối đó (dự phòng): Subject = người được đăng ký khai sinh; cha/mẹ theo nhãn "cha"/"mẹ"
  ghi trên giấy (giới tính chỉ là tín hiệu phụ).
</phan_vai>

<nguoi_yeu_cau>
Khối "Thông tin người yêu cầu" trên biểu mẫu bắt đầu bằng ô tích "Quan hệ với người được khai sinh".
Nguồn duy nhất để chốt ô này là TỜ KHAI ĐĂNG KÝ KHAI SINH.

0. NẾU có khối <quan_he_nguoi_yeu_cau> trong <phan_vai_da_xac_dinh>: quan hệ ĐÃ ĐƯỢC CHỐT ở bước
   phân vai (agent đã đối chiếu người yêu cầu với người được khai sinh, Python đã kiểm chứng).
   Requester_RelationToSubject phải TRẢ ĐÚNG kết luận đó, không tự suy lại; riêng khi khối
   <to_khai_dang_ky_khai_sinh> ghi "Không" thì BỎ TRỐNG cả field này:
   "bản thân" → "Bản thân"; "cha" → "Cha"; "mẹ" → "Mẹ"; "khác" → "Khác";
   "không xác định" → bỏ field.
1. CÓ TỜ KHAI ĐĂNG KÝ KHAI SINH trong hồ sơ (tiêu đề có đủ "TỜ KHAI" + "ĐĂNG KÝ KHAI SINH",
   hoặc khối <to_khai_dang_ky_khai_sinh> ghi "Có"):
   - Requester_RelationToSubject = quy chuẩn dòng "Quan hệ với người được khai sinh" về ĐÚNG MỘT
     trong "Bản thân" | "Cha" | "Mẹ" | "Khác".
     • Tờ khai ghi "Bản thân"/"Tự khai"/"Chính mình", HOẶC họ tên (và số định danh) người yêu cầu TRÙNG
       người được khai sinh → "Bản thân". Đây là ca PHỔ BIẾN NHẤT của thủ tục này.
     • Trùng cha → "Cha"; trùng mẹ → "Mẹ"; còn lại (ông, bà, anh, chị, em, con, cháu, người được ủy
       quyền...) → "Khác" và ghi thêm chữ nguyên văn vào Requester_Relationship.
   - Requester_FullName/IdNumber/IdIssueDate/IdIssuePlace/ResidenceDomestic = nhân thân người yêu cầu
     ghi trên tờ khai; thiếu thì lấy tiếp từ CCCD/CMND CỦA CHÍNH người yêu cầu đó. VẪN PHẢI trả kể cả khi
     người yêu cầu chính là con/cha/mẹ (không được bỏ vì "đã có Subject_*/Father_*/Mother_*").
   - Requester_SourceDocumentTitle = tiêu đề NGUYÊN VĂN của tờ khai đó (bằng chứng nguồn là tờ khai).
2. KHÔNG CÓ TỜ KHAI (hồ sơ chỉ có CCCD/CMND, BHYT, học bạ, GCN kết hôn...): không tài liệu nào
   nói ai đang đi nộp hồ sơ → BỎ TRỐNG toàn bộ Requester_* (kể cả Requester_RelationToSubject).
   Cổng đã tự điền khối người yêu cầu từ tài khoản VNeID đang đăng nhập; Python chỉ tick "Khác" để tách
   khối đó ra, KHÔNG ghi đè, rồi đổ toàn bộ dữ liệu quét được vào các khối con/cha/mẹ.
   TUYỆT ĐỐI KHÔNG bịa Requester_* từ CCCD của con/cha/mẹ.
3. Vì vậy CCCD/CMND của CHÍNH người được khai sinh phải được trích đủ vào Subject_IdNumber,
   Subject_IdIssueDate, Subject_IdIssuePlace, Subject_ResidenceDomestic (ngoài họ tên/ngày sinh/giới tính).
   Đây là nguồn duy nhất của khối "Người được đăng ký khai sinh" — thiếu là hỏng cả khối. KHÔNG lấy
   số định danh hay nơi thường trú của cha/mẹ gán cho Subject_*.
</nguoi_yeu_cau>

<uu_tien_nguon>
⚠️ THỨ TỰ NGUỒN — TỜ KHAI TRƯỚC, GIẤY TỜ CÁ NHÂN SAU. Áp dụng cho MỌI vai:

1. TỜ KHAI ĐĂNG KÝ KHAI SINH là NGUỒN SỐ 1. Vai của từng người lấy đúng theo nhãn in sẵn:
   • "Họ, chữ đệm, tên người yêu cầu" → Requester_*
   • mục "Đề nghị cơ quan đăng ký khai sinh cho người có tên dưới đây" → Subject_*
   • "Họ, chữ đệm, tên người mẹ" → Mother_*   • "Họ, chữ đệm, tên người cha" → Father_*
   Mọi mục tờ khai CÓ GHI (ngày sinh, ngày sinh bằng chữ, giới tính, dân tộc, quốc tịch, nơi sinh,
   quê quán, nơi cư trú, giấy tờ tùy thân) đều PHẢI trả theo tờ khai, kể cả khi tờ khai viết tay.
2. CCCD/CMND, thẻ BHYT, học bạ, bằng tốt nghiệp, giấy chứng nhận kết hôn, giấy đề nghị xác nhận,
   trích lục khai tử/giấy chứng tử là NGUỒN BÙ (fallback): chỉ dùng cho field mà tờ khai BỎ TRỐNG hoặc
   OCR không đọc nổi, và chỉ của CHÍNH người đó (khớp họ tên hoặc số định danh với người ghi trên tờ khai).
3. ❌ CẤM dùng CCCD để ĐỔI VAI mà tờ khai đã chốt. Thẻ của mẹ không được đẩy sang vai cha/con dù giới
   tính hay năm sinh trông "hợp lý" hơn. Tờ khai ghi ai là mẹ thì người đó là mẹ.
4. Hồ sơ có tờ khai mà một vai KHÔNG có CCCD (rất phổ biến: cha/mẹ đã mất, chỉ có trích lục khai tử hoặc
   chỉ được nhắc tên trên tờ khai): VẪN PHẢI trả đủ field của vai đó theo tờ khai. Thiếu CCCD KHÔNG phải
   lý do bỏ trống vai.
5. Chính tả họ tên: giữ đúng người theo tờ khai, nhưng nếu chính người đó có CCCD/trích lục trong hồ sơ
   thì viết họ tên theo giấy tờ gốc (bản đánh máy chuẩn hơn chữ viết tay).
6. Số định danh / ngày cấp / nơi cấp: lệch giữa tờ khai và CCCD của CÙNG một người thì lấy theo CCCD.
   NGÀY SINH và GIỚI TÍNH cũng là thông tin IN trên thẻ: chính người đó (con, cha, mẹ) có CCCD/CMND
   trong hồ sơ thì lấy NGÀY SINH + GIỚI TÍNH theo CCCD, kể cả khi tờ khai ghi khác (chữ viết tay hay bị
   OCR đọc sai). Tờ khai/giấy khác chỉ bù khi thẻ không có hoặc không đọc được.
7. HỒ SƠ KHÔNG CÓ TỜ KHAI thì mới dùng khối <phan_vai_khi_khong_co_to_khai> bên dưới.
</uu_tien_nguon>

<mot_nguoi_mot_nguon>
Mỗi người lấy thông tin ĐỒNG BỘ từ giấy tờ của CHÍNH họ; TUYỆT ĐỐI không trộn ngày sinh/nơi cư trú/số
định danh giữa các vai (mỗi thẻ là MỘT người khác nhau).

- CẤM lấy số định danh của NGƯỜI ĐƯỢC KHAI SINH (trên CCCD/BHYT/học bạ của chính họ) làm số định danh
  của cha/mẹ.
- BẮT BUỘC trả Father_Gender / Mother_Gender = giới tính GHI TRÊN chính giấy tờ đã dùng cho vai đó
  ("Nam"/"Nữ"). Đây là căn cứ để hậu kiểm: thẻ ghi "Nữ" mà điền vào Father_* sẽ bị XÓA sạch vai cha
  (và ngược lại). Không suy giới tính từ tên người. Tờ khai không ghi giới tính cha/mẹ thì suy theo
  chính nhãn quan hệ trên tờ khai: mục "người cha" → "Nam", mục "người mẹ" → "Nữ".
- HỒ SƠ THIẾU MỘT BÊN: BỎ TRỐNG HOÀN TOÀN vai còn lại — không trả BẤT KỲ field nào của vai đó, kể cả
  Nationality/Ethnicity/ResidenceDomestic. Thà để cổng trống còn hơn điền dữ liệu của người khác sang.
- ❌ CẤM tự thêm địa chỉ "Đã chết" khi không có căn cứ: chỉ trả *_ResidenceDomestic = {"diaChi":"Đã chết"}
  khi tờ khai/giấy tờ ghi rõ người đó đã mất.
</mot_nguoi_mot_nguon>

<phan_vai_khi_khong_co_to_khai>
CHỈ dùng khối này khi hồ sơ KHÔNG có tờ khai đăng ký khai sinh (và không giấy tờ nào chỉ đích danh
người được khai sinh). Khi đó vai phải suy từ CCCD theo giới tính + thế hệ:

**BƯỚC 1: PHÂN LOẠI CCCD THEO GIỚI TÍNH** — mỗi CCCD có field "Giới tính / Sex": "Nam" hoặc "Nữ".

**BƯỚC 2: XÁC ĐỊNH VAI**
A. CHỈ CÓ ĐÚNG MỘT thẻ căn cước/CMND: người trên thẻ đó CHÍNH LÀ người được khai sinh (Subject_*) —
   chính chủ tự đi làm cho mình. BỎ TRỐNG hoàn toàn Father_* và Mother_*.
B. 2 CCCD (1 Nam + 1 Nữ): người TRẺ HƠN (năm sinh gần hiện tại hơn) → Subject_*; người còn lại
   NAM → CHA (Father_*), NỮ → MẸ (Mother_*). Vai không có thẻ nào → BỎ TRỐNG hoàn toàn.
C. 2 CCCD cùng giới: người TRẺ HƠN → Subject_*; người LỚN HƠN là CHA nếu cả hai Nam (bỏ trống Mother_*),
   là MẸ nếu cả hai Nữ (bỏ trống Father_*).
D. 3 CCCD: TRẺ NHẤT → Subject_*; trong hai người còn lại, "Giới tính: Nam" → CHA, "Giới tính: Nữ" → MẸ.

**BƯỚC 3: CẤM TUYỆT ĐỐI**
- ❌ CẤM điền CCCD "Giới tính: Nữ" vào Father_*, CCCD "Giới tính: Nam" vào Mother_*.
- ❌ CẤM dùng cùng một người cho hai vai, hoặc lấy thông tin Subject sang CHA/MẸ.
- ❌ CẤM đoán: không có CCCD Nam (ngoài Subject) → BỎ TRỐNG Father_*; không có CCCD Nữ → BỎ TRỐNG Mother_*.
</phan_vai_khi_khong_co_to_khai>

<trich_field>
1. Subject_BirthDate: ưu tiên đủ dd/mm/yyyy; đọc CẢ phần số lẫn phần "ghi bằng chữ" để khôi phục khi số bị
   nhiễu (vd "mùng chín tháng mười một năm một nghìn chín trăm bảy mươi ba" → "09/11/1973").
   Chỉ trả "yyyy" khi không rõ ngày/tháng. Người được khai sinh có CCCD/CMND trong hồ sơ thì Subject_BirthDate
   và Subject_Gender lấy theo thẻ (xem <uu_tien_nguon> mục 6); Subject_BirthDateInWords vẫn chép từ tờ khai.
2. Subject_BirthDateInWords: CHÉP NGUYÊN VĂN cụm chữ ghi ngày sinh trên tờ khai (thường trong ngoặc ngay
   sau ngày sinh). KHÔNG tự chuyển số sang chữ, KHÔNG viết lại theo ý mình. Tờ khai không ghi → bỏ field.
3. NĂM SINH CHA/MẸ: tờ khai của thủ tục này thường CHỈ GHI NĂM (vd "1952", "1953"). Khi đó trả đúng
   "1952"/"1953" vào Father_BirthDateOrYear/Mother_BirthDateOrYear — KHÔNG tự bịa ngày/tháng.
   Chỉ trả dd/mm/yyyy khi chính người đó có CCCD/CMND trong hồ sơ.
4. CHA/MẸ ĐÃ MẤT (khối vai ghi Trạng thái "đã chết", HOẶC OCR khối cha/mẹ có "đã chết/đã mất/từ trần",
   kể cả nhiễu "Da Chet"/"L.D. Chat"):
   - HỌ TÊN: Ưu tiên lấy từ CCCD nếu có trong hồ sơ; nếu không có CCCD thì lấy từ TỜ KHAI, GIẤY ĐỀ NGHỊ
     XÁC NHẬN, GIẤY CHỨNG NHẬN KẾT HÔN hoặc TRÍCH LỤC KHAI TỬ (dòng "Họ tên người chết"/"Họ và tên").
   - ĐỊA CHỈ: Trả *_ResidenceDomestic = {"quocGia":"","tinh":"","xa":"","diaChi":"Đã chết"}.
   - THÔNG TIN KHÁC: Vẫn PHẢI trích *_BirthDateOrYear, *_Ethnicity, *_Nationality TỪ TỜ KHAI hoặc
     TRÍCH LỤC KHAI TỬ / GIẤY CHỨNG TỬ nếu có.
   - ĐỊA CHỈ TỪ GIẤY KHAI TỬ: Trích "Nơi thường trú"/"Nơi cư trú" (thiếu thì "Quê quán") trên trích lục
     vào *_HometownFromDeathCert (object {quocGia,tinh,xa,diaChi}). Chỉ trả khi có trích lục.
5. Nơi cấp giấy tờ định danh:
   - CCCD gắn chip ghi "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát
     quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới (cấp từ 01/7/2024) ghi "BỘ CÔNG AN" → "Bộ Công an".
   - CMND (~9 chữ số): *_IdIssuePlace là "Công an tỉnh/thành phố ..." ghi cùng dòng số CMND. TUYỆT ĐỐI
     KHÔNG suy "Cục Cảnh sát..."/"Bộ Công an" cho CMND.
6. THẺ BHYT, HỌC BẠ, BẰNG TỐT NGHIỆP, GIẤY ĐỀ NGHỊ XÁC NHẬN: là giấy tờ CỦA CHÍNH người được khai sinh
   → chỉ dùng bù cho Subject_* (họ tên, ngày sinh, giới tính, nơi sinh, quê quán, nơi cư trú, dân tộc).
   Mã số BHXH/số thẻ BHYT/số hiệu bằng KHÔNG phải số định danh cá nhân → KHÔNG điền vào *_IdNumber.
7. GIẤY CHỨNG NHẬN KẾT HÔN của cha mẹ: dùng để bù HỌ TÊN + NĂM SINH của cha/mẹ khi thiếu CCCD.
   Số/quyển số/ngày trên giấy kết hôn KHÔNG được trả vào bất kỳ field nào.
8. DÂN TỘC ≠ QUỐC TỊCH. Tờ khai viết tay rất hay bị ghi nhầm "Dân tộc: Việt Nam" — "Việt Nam" là
   QUỐC TỊCH, KHÔNG phải dân tộc và KHÔNG có trong danh mục dân tộc.
   - Gặp ô "Dân tộc" ghi "Việt Nam"/"Việt"/"Vietnam" → BỎ QUA giá trị đó, đi tìm dân tộc THẬT của
     CHÍNH người đó trên giấy tờ khác trong hồ sơ (giấy chứng nhận kết hôn, trích lục khai tử, giấy
     đề nghị xác nhận, học bạ — các giấy này có dòng "Dân tộc" ghi đúng: Kinh, Mông, Thái, Tày…).
   - Không giấy nào ghi dân tộc thật → BỎ HẲN field *_Ethnicity, KHÔNG trả "Việt Nam".
   - ❌ CẤM suy dân tộc của người này từ dân tộc của người khác trong hồ sơ.
</trich_field>

<copy_request>
CopyRequest_* CHỈ lấy từ TỜ KHAI ĐĂNG KÝ KHAI SINH (tiêu đề có đủ "TỜ KHAI" + "ĐĂNG KÝ KHAI SINH").
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
  VD1: "Nùng Nàng, Tam Đường, Lai Châu" → xa="Nùng Nàng", tinh="Lai Châu",
  diaChi="" (XÓA huyện Tam Đường). SAI nếu ra xa="Tam Đường" hoặc diaChi="Nùng Nàng".
• 4 tên "D, A, B, C" (D là chi tiết: thôn/bản/xóm/tổ dân phố/số nhà): D = diaChi; A = xa; B = huyện → XÓA;
  C = tinh. VD2: "Bản Chin Chu Chải, Nùng Nàng, Tam Đường, Lai Châu" → diaChi="Bản Chin Chu Chải",
  xa="Nùng Nàng", tinh="Lai Châu" (XÓA huyện Tam Đường).
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

3. **KIỂM TRA DUPLICATE VỚI NGƯỜI ĐƯỢC KHAI SINH**:
   - Nếu Father_FullName = Subject_FullName → XÓA TẤT CẢ Father_*
   - Nếu Mother_FullName = Subject_FullName → XÓA TẤT CẢ Mother_*

Chỉ trả một JSON object: {"fields":{"<field_hop_le>": <value>}}. Chỉ dùng field trong danh sách FIELD ĐƯỢC
PHÉP TRẢ; KHÔNG trả field UI (HoTenKS, HoTenChaKS, NamSinhMeKS, QuanHe, LoaiDangKy...); không bịa; field
không đủ căn cứ thì bỏ; không trả giải thích/nguồn sau JSON.
</output>
""".strip()

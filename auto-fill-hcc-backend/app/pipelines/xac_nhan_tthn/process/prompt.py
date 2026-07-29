"""Procedure-specific compact prompt rules for "Xác nhận tình trạng hôn nhân"."""

EXTRA_RULES = """<procedure>
Thủ tục có HAI TRƯỜNG HỢP:

A. BẢN THÂN: người yêu cầu chính là người cần giấy XNTTHN. Chỉ có CCCD của một người.
   → Chỉ trả Cccd_* (+ giấy tờ hôn nhân nếu có). KHÔNG trả PoA_*.

B. ỦY QUYỀN: có GIẤY ỦY QUYỀN kèm theo. Người được ủy quyền (đi nộp hộ) có CCCD riêng.
   → Trả Cccd_* từ CCCD của người ĐI NỘP (người được ủy quyền - Section II giấy ủy quyền).
   → Trả PoA_* từ GIẤY ỦY QUYỀN của người ỦY QUYỀN (người CẦN giấy - Section I giấy ủy quyền).

Đầu vào thường có CCCD/CMND; có thể có thêm giấy ủy quyền, quyết định/bản án ly hôn,
giấy chứng tử/trích lục khai tử/giấy báo tử của vợ/chồng đã chết, HOẶC GIẤY XÁC NHẬN TÌNH TRẠNG
HÔN NHÂN CŨ (đã cấp trước đây).
</procedure>

<giay_uy_quyen>
NHẬN DẠNG GIẤY ỦY QUYỀN: tài liệu có tiêu đề "GIẤY ỦY QUYỀN" hoặc "GIẤY UỶ QUYỀN", có phần
"I. Người ủy quyền" (hoặc "Bên ủy quyền") và "II. Người được ủy quyền" (hoặc "Bên nhận ủy quyền"),
kết thúc bằng "Nội dung ủy quyền" hoặc "Phạm vi ủy quyền".

TRÍCH XUẤT KHI CÓ GIẤY ỦY QUYỀN:

Section I — NGƯỜI ỦY QUYỀN (người CẦN giấy XNTTHN) → các field PoA_Subject*:
- PoA_SubjectName  = họ tên người ủy quyền ở phần "I. Người ủy quyền / Họ và tên: ..."
- PoA_SubjectDoB   = ngày sinh người ủy quyền ("sinh ngày ..."), dd/mm/yyyy
- PoA_SubjectIdNumber = số CCCD/CMND/Hộ chiếu của người ủy quyền ("CMND/CCCD/số hộ chiếu: ...")
- PoA_SubjectIdDate   = ngày cấp giấy tờ của người ủy quyền ("cấp ngày ..."), dd/mm/yyyy
- PoA_SubjectIssuer   = nơi cấp giấy tờ của người ủy quyền ("do ... cấp")
  + Nếu OCR thấy "Cục Cảnh sát QLHC" / "quản lý hành chính về trật tự" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
  + Nếu thấy "Bộ Công an" → "Bộ Công an"
- PoA_SubjectAddress  = nơi cư trú người ủy quyền ("Nơi cư trú / Địa chỉ: ..."), object {tinh, xa, diaChi}
  (áp quy tắc <noi_cu_tru> để tách tinh/xa/diaChi)

Section II — NGƯỜI ĐƯỢC ỦY QUYỀN (người ĐI NỘP hộ) → CCCD của người này thường được upload kèm.
Thông tin từ CCCD upload → điền vào Cccd_* như bình thường.
KHÔNG trích thông tin người được ủy quyền từ giấy ủy quyền vào Cccd_* (dùng CCCD upload).

LƯU Ý QUAN TRỌNG:
- Nếu giấy ủy quyền chỉ ghi tên KHÔNG kèm CCCD/ngày sinh người ủy quyền → vẫn trả PoA_SubjectName,
  bỏ qua các field còn lại nếu không có.
- Khi có cả CCCD và giấy ủy quyền: CCCD upload thường là của người ĐƯỢC ủy quyền (đi nộp hộ).
  Đối chiếu tên CCCD với Section II giấy ủy quyền để xác nhận.
- TUYỆT ĐỐI KHÔNG nhầm người ủy quyền (Section I) với người được ủy quyền (Section II).
</giay_uy_quyen>

<giay_xntthn_cu>
Nếu có GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN CŨ (tiêu đề "GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN"), giấy này
NHẮC LẠI tình trạng hôn nhân + giấy tờ liên quan + mục đích → được phép dùng làm NGUỒN:
- Nếu dòng tình trạng hôn nhân ghi "... chồng/vợ đã chết (theo Giấy chứng tử/Trích lục khai tử số <N> do <CQ>
  cấp ngày <D>)" → DeathCert_Number=<N> (SỐ ĐĂNG KÝ GỐC, KHÔNG kèm hậu tố TLKT-BS), DeathCert_Date=<D>
  (dd/mm/yyyy), DeathCert_Agency=<CQ> (bỏ chữ "cấp").
- Nếu ghi "... đã ly hôn (Bản án/Quyết định ly hôn số <N> ngày <D> của <CQ>)"
  → DivorceDecision_Number/Date/Agency tương ứng.
- Purpose: lấy từ "Giấy này được sử dụng để: <mục đích>." — BỎ phần chú thích trong ngoặc
  (vd "(Không có giá trị đăng ký kết hôn)"). Ví dụ → "Làm thủ tục vay vốn ngân hàng".
</giay_xntthn_cu>

<source_rules>
- Cccd_* CHỈ lấy từ CCCD/CMND upload (thẻ vật lý được chụp/scan kèm hồ sơ):
  + Trường hợp BẢN THÂN: CCCD upload là của chính người cần giấy XNTTHN.
  + Trường hợp ỦY QUYỀN: CCCD upload là của người ĐƯỢC ủy quyền (đi nộp hộ) — thông tin
    người cần giấy (người ủy quyền) lấy từ GIẤY ỦY QUYỀN → điền vào PoA_Subject*.
- Nếu có nhiều ảnh CCCD thì gộp mặt trước + mặt sau của cùng một người.
- RIÊNG Cccd_DanToc (dân tộc) — thẻ CCCD/Căn cước mẫu mới thường KHÔNG in dân tộc. THỨ TỰ ƯU TIÊN NGUỒN:
  (1) TỜ KHAI cấp Giấy XNTTHN — dòng "Dân tộc: ..." (ở khối người được cấp/người yêu cầu);
  (2) thẻ CCCD/CMND nếu có in. BẮT BUỘC điền Cccd_DanToc nếu bất kỳ giấy nào ghi — ĐỪNG bỏ trống chỉ vì thẻ CCCD không in.
- Cccd_NgayCap (ngày cấp CCCD) — BẮT BUỘC trả nếu BẤT KỲ giấy nào có; TUYỆT ĐỐI KHÔNG được có thông tin
  mà bỏ trống. Khi có NGÀY Ở NHIỀU CHỖ (mặt sau CCCD và tờ khai), CHỌN THEO THỨ TỰ ƯU TIÊN, ĐỪNG vì phân vân
  mà bỏ trống:
  + (1) ƯU TIÊN NHẤT: MẶT SAU CCCD — ngày ở dòng "Ngày, tháng, năm / Date, month, year" (dd/mm/yyyy). Ngày này
    CÓ THỂ DÍNH LIỀN nhãn do OCR gộp, vd "...Date, month, year01/05/2021" → Cccd_NgayCap = "01/05/2021".
  + (2) Nếu MẶT SAU CCCD KHÔNG đọc được ngày cấp → lấy Ở TỜ KHAI (dòng "Giấy tờ tùy thân: CCCD số ... cấp ngày <D>").
  + Cccd_NoiCap nằm gần dòng ngày cấp; nếu OCR thấy "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH
  VỀ TRẬT TỰ XÃ HỘI" thì trả Cccd_NoiCap = "Cục Cảnh sát quản lý hành chính về trật tự xã hội". Nếu là thẻ CĂN CƯỚC mới (tiêu đề "CĂN CƯỚC"/"IDENTITY CARD", thường cấp từ 01/7/2024) ghi "BỘ CÔNG AN"/"MINISTRY OF PUBLIC SECURITY" thì trả Cccd_NoiCap = "Bộ Công an"; KHÔNG mặc định "Cục Cảnh sát..." cho thẻ này.
- DivorceDecision_* lấy từ OCR của tài liệu là quyết định/bản án ly hôn thật, HOẶC từ dòng tình trạng
  hôn nhân trên giấy XNTTHN cũ (nhắc lại "Bản án/Quyết định ly hôn số ..."). Không dùng tên file để kết luận.
- Một tài liệu ly hôn thật thường có các dấu hiệu: "TÒA ÁN NHÂN DÂN" hoặc "TAND",
  tiêu đề "QUYẾT ĐỊNH"/"BẢN ÁN", và nội dung như "công nhận thuận tình ly hôn",
  "ly hôn", "về quan hệ hôn nhân".
- DeathCert_* lấy từ OCR tài liệu khai tử thật của VỢ/CHỒNG (giấy chứng tử, trích lục khai tử, giấy
  báo tử), HOẶC từ dòng tình trạng hôn nhân trên giấy XNTTHN cũ (nhắc lại "Giấy chứng tử số ..."). KHÔNG
  lấy từ CCCD người yêu cầu; thông tin người chết là VỢ/CHỒNG, không phải người yêu cầu — không điền Cccd_*.
</source_rules>

<death_cert_extraction>
- DeathCert_Number = SỐ ĐĂNG KÝ KHAI TỬ GỐC (số trong Sổ đăng ký khai tử), KHÔNG phải số của bản sao/trích lục:
  + TRÍCH LỤC KHAI TỬ (BẢN SAO): số ở mục "Số:" ĐẦU trang là số của CHÍNH BẢN SAO — thường có hậu tố loại
    ("/TLKT-BS", "/TLKT", "-BS"), vd "212/2022/TLKT-BS". TUYỆT ĐỐI KHÔNG dùng số này. Lấy số GỐC ở dòng thân
    "Đã được đăng ký khai tử tại: <cơ quan> ... Số: <N> ngày <D>".".
  + GIẤY CHỨNG TỬ GỐC (không phải bản sao/trích lục): số "Số:" ở đầu chính là số đăng ký → dùng số đó.
  + Ưu tiên số GỐC KHÔNG kèm hậu tố "TLKT"/"BS".
- DeathCert_Date = ngày ĐĂNG KÝ KHAI TỬ GỐC:
  + Trích lục (bản sao): lấy ngày trên CHÍNH dòng "Đã được đăng ký khai tử tại ... Số: <N> ngày <D>" (cùng nguồn với số gốc).
  + Giấy chứng tử gốc: lấy ngày cấp/lập giấy (dòng địa danh + ngày). KHÔNG lấy ngày chết/ngày sinh của người chết.
- DeathCert_Agency = cơ quan ĐÃ ĐĂNG KÝ khai tử (dòng "Đã được đăng ký khai tử tại: <cơ quan>"), vd "UBND thị trấn Đạ Tẻh";
  nếu là giấy chứng tử gốc thì lấy cơ quan cấp/ký giấy. Chuẩn hóa "UBND" → "Ủy ban nhân dân" nếu cần.
- Chỉ trả DeathCert_* khi tài liệu thật sự là giấy khai tử/chứng tử/báo tử/trích lục khai tử có đủ dấu hiệu.
  Nếu chỉ có CCCD thì bỏ qua toàn bộ DeathCert_*.
</death_cert_extraction>

<divorce_decision_extraction>
- DivorceDecision_Number: lấy số ở nhãn "Số:" NGAY ĐẦU văn bản (phần tiêu đề, ngay dưới tên Tòa án).
  TUYỆT ĐỐI KHÔNG lấy số ở các cụm DẪN CHIẾU trong phần nội dung như "Tại quyết định dân sự số ...",
  "tại bản án số ...", "theo quyết định số ..." — đó là số văn bản GỐC được trích lục/dẫn chiếu,
  KHÔNG phải số của văn bản đang xét.
  Không lấy số thụ lý, số biên lai, số án phí, số trang hoặc số mục trong nội dung.
- DivorceDecision_Date: lấy ngày ban hành/cấp quyết định ở dòng địa danh + ngày tháng năm
  gần đầu văn bản, ví dụ "Thị xã Lai Châu, ngày 03 tháng 5 năm 2012" -> "03/05/2012".
  Không lấy ngày hòa giải, ngày thụ lý, ngày biên lai, ngày hiệu lực hoặc ngày sinh.
- DivorceDecision_Agency: lấy cơ quan ban hành/cấp quyết định từ đầu văn bản hoặc phần ký.
  Chuẩn hóa "TAND" thành "Tòa án nhân dân". Ví dụ "TAND THỊ XÃ LAI CHÂU / TỈNH LAI CHÂU"
  -> "Tòa án nhân dân thị xã Lai Châu, tỉnh Lai Châu".
- Chỉ trả DivorceDecision_* khi tài liệu có đủ dấu hiệu quyết định/bản án ly hôn.
  Nếu chỉ có CCCD hoặc giấy tờ không chứng minh ly hôn thì bỏ qua toàn bộ DivorceDecision_*.
</divorce_decision_extraction>

<marriage_extraction>
- Marriage_* lấy từ GIẤY CHỨNG NHẬN KẾT HÔN / GIẤY ĐĂNG KÝ KẾT HÔN thật (dấu hiệu: tiêu đề
  "GIẤY CHỨNG NHẬN KẾT HÔN"/"ĐĂNG KÝ KẾT HÔN", có thông tin CHỒNG và VỢ, ngày đăng ký, cơ quan đăng ký).
  Đây là trường hợp NGƯỜI YÊU CẦU HIỆN ĐANG CÓ VỢ/CHỒNG.
- Marriage_SpouseName = họ tên của NGƯỜI CÒN LẠI (vợ/chồng), tức người KHÁC với người yêu cầu.
  Đối chiếu với tên trên CCCD người yêu cầu: trên giấy có 2 người (chồng + vợ) → lấy tên người KHÔNG trùng CCCD.
- Marriage_Number = số Giấy chứng nhận kết hôn (số đăng ký kết hôn) ở phần "Số:" của giấy.
- Marriage_Date = ngày đăng ký kết hôn (dd/mm/yyyy). Marriage_Agency = cơ quan đăng ký (vd UBND xã/phường...),
  chuẩn hóa "UBND" → "Ủy ban nhân dân" nếu cần.
- Chỉ trả Marriage_* khi tài liệu THẬT SỰ là giấy chứng nhận/đăng ký kết hôn. Nếu tài liệu là ly hôn/khai tử
  thì KHÔNG trả Marriage_* (ưu tiên ly hôn/góa hơn đang có vợ/chồng).
</marriage_extraction>

<noi_cu_tru>
- NGUỒN ƯU TIÊN Cccd_NoiCuTru: (1) TỜ KHAI cấp Giấy XNTTHN — dòng "Nơi cư trú: ..." của NGƯỜI YÊU CẦU /
  NGƯỜI ĐƯỢC CẤP (đây là nơi cư trú HIỆN TẠI người dân khai, thường MỚI HƠN CCCD vì có thể đã chuyển chỗ);
  (2) CHỈ khi tờ khai KHÔNG có nơi cư trú mới lấy "Nơi thường trú" trên CCCD. TUYỆT ĐỐI KHÔNG lấy địa chỉ
  nằm trong đoạn "Tình trạng hôn nhân" (đó là địa chỉ CŨ nhắc lại trong nội dung, không phải nơi cư trú hiện tại).
  Áp quy tắc tách địa chỉ bên dưới cho địa chỉ ĐÃ CHỌN.
- Cccd_NoiCuTru trả object {quocGia, tinh, xa, diaChi}. Địa chỉ hành chính hiện hành CHỈ 2 cấp:
  XÃ/PHƯỜNG/THỊ TRẤN rồi đến TỈNH/THÀNH PHỐ (KHÔNG còn cấp huyện/quận).
- xa = tên xã/phường/thị trấn. tinh = tỉnh/thành phố.
- diaChi = phần CHI TIẾT đứng TRƯỚC xã/phường: tổ, tổ dân phố, bản, thôn, xóm, khu, số nhà, đường.
  TÊN xã/phường/thị trấn, huyện/quận, tỉnh KHÔNG được đưa vào diaChi.
  Nếu không có phần chi tiết đứng trước xã/phường thì diaChi để TRỐNG.
- ĐẾM TỪ CUỐI khi địa chỉ liệt kê không nhãn (dạng cũ 3 cấp "[chi tiết], xã, HUYỆN, tỉnh"): cuối = tỉnh;
  phần NGAY TRƯỚC tỉnh nếu là CẤP HUYỆN (huyện/quận/thị xã/thành phố thuộc tỉnh) thì BỎ HẲN; phần trước đó
  = xã. Tên xã/phường vùng cao CÓ THỂ bắt đầu bằng "Bản"/"Nậm"/"Mường"/"Pa" — KHÔNG coi là chi tiết chỉ vì
  bắt đầu bằng "Bản", VỊ TRÍ (áp chót, trước cấp huyện/tỉnh) mới quyết định là xã. BẮT BUỘC điền xa.
</noi_cu_tru>

<forbidden_ui_fields>
- Không trả field UI/default như HoVaTenC, HoVaTenC1, SoDinhDanhC, SoDinhDanhC1,
  LoaiGiayToDinhDanhC, LoaiGiayToDinhDanhC1, quanhevoinguoiduocxacminh, mucdich, nhapmucdichkhac,
  loại cư trú, radio trong/ngoài nước. (Purpose vẫn TRẢ — Python sẽ điền vào ô Nhập mục đích.)
- Không trả TinhTrangHonNhanC1. Python sẽ chọn tình trạng hôn nhân theo THỨ TỰ ƯU TIÊN: GÓA khi đủ
  DeathCert_*; ĐÃ LY HÔN khi đủ DivorceDecision_*; HIỆN ĐANG CÓ VỢ/CHỒNG khi có Marriage_* (giấy kết hôn).
- Không suy luận tình trạng hôn nhân từ CCCD vì CCCD không chứa dữ liệu này.
- Nếu thiếu quốc tịch thì bỏ qua Cccd_QuocTich; Python sẽ mặc định Việt Nam.
</forbidden_ui_fields>"""

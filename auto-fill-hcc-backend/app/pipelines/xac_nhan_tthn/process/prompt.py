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

<critical_tokhai_extraction>
QUAN TRỌNG: Khi có TỜ KHAI cấp giấy XNTTHN, BẮT BUỘC trả TẤT CẢ các field ToKhai_* tương ứng với thông tin
trong phần "Đề nghị cấp Giấy xác nhận tình trạng hôn nhân cho người có tên dưới đây" (Section II - người được cấp):
- ToKhai_HoTen (từ "Họ, chữ đệm, tên:")
- ToKhai_NgaySinh (từ "Ngày, tháng, năm sinh:", dd/mm/yyyy)
- ToKhai_GioiTinh (từ "Giới tính:", "Nam" hoặc "Nữ")
- ToKhai_DanToc (từ "Dân tộc:")
- ToKhai_QuocTich (từ "Quốc tịch:")
- ToKhai_SoDinhDanh (từ "Giấy tờ tùy thân: ... số")
- ToKhai_NgayCapGiayTo (từ "Cấp ngày...", dd/mm/yyyy)
- ToKhai_NoiCapGiayTo (từ "tại ..." sau "Cấp ngày")
- ToKhai_NoiCuTru (từ "Nơi cư trú:", object {quocGia,tinh,xa,diaChi})

TUYỆT ĐỐI KHÔNG bỏ qua các field ToKhai_* chỉ vì CCCD cũng có thông tin tương tự. CẢ HAI NGUỒN (ToKhai_* VÀ Cccd_*) 
đều phải được trả khi đều có thông tin. Python mapper sẽ quyết định ưu tiên nguồn nào, KHÔNG phải LLM.
</critical_tokhai_extraction>

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

<purpose_extraction>
- BẮT BUỘC trả Purpose khi TỜ KHAI có dòng "Mục đích sử dụng Giấy xác nhận tình trạng hôn nhân: ...".
- Lấy toàn bộ nội dung sau nhãn trên, nối các dòng liên tiếp; dừng trước "Tôi cam đoan", "Làm tại" hoặc
  "Người yêu cầu". Bỏ "(5)" và nhãn, không bỏ field chỉ vì OCR sai nhẹ trong nội dung.
- Thứ tự nguồn: TỜ KHAI hiện tại → "Giấy này được sử dụng để: ..." trên giấy XNTTHN cũ.
</purpose_extraction>

<to_khai_status_relation>
- Từ dòng "Tình trạng hôn nhân" trên TỜ KHAI:
  + Nếu ghi "đã đăng ký kết hôn nhưng chồng đã chết" hoặc "đã đăng ký kết hôn nhưng vợ đã chết"
    hoặc "vợ/chồng đã chết" VÀ CÓ dòng "Theo giấy chứng tử số ... do ... cấp ngày ..." → BẮT BUỘC
    trích xuất DeathCert_Number, DeathCert_Date, DeathCert_Agency từ dòng đó (xem chi tiết ở
    <death_cert_from_tokhai>). TUYỆT ĐỐI KHÔNG trả TinhTrangHonNhanC1 trong trường hợp này
    (Python mapper sẽ tự điền trạng thái GÓA từ DeathCert_*).
  + Nếu ghi "đã ly hôn" hoặc "đã đăng ký kết hôn nhưng đã ly hôn" VÀ CÓ dòng "Theo bản án/quyết định
    ly hôn số ... do/của ... cấp/ngày ..." → trích xuất DivorceDecision_* (tương tự death cert).
    KHÔNG trả TinhTrangHonNhanC1.
  + Nếu nội dung bắt đầu bằng "Chưa kết hôn" hoặc CHỈ ghi "hiện tại chưa đăng ký kết hôn với ai"
    (KHÔNG có thông tin về chồng/vợ đã chết hay ly hôn) → TinhTrangHonNhanC1 = "Hiện tại chưa đăng ký kết hôn với ai".
  + Nếu ghi rõ "hiện tại đang có chồng" hoặc "hiện tại đang có vợ" → TinhTrangHonNhanC1 = "Hiện tại đang có vợ/chồng".
- Trả ToKhai_LaBanThan=true CHỈ khi dòng quan hệ ghi "Tự khai"/"Bản thân" VÀ họ tên người yêu cầu
  trùng họ tên người được cấp.
</to_khai_status_relation>

<death_cert_from_tokhai>
Khi TỜ KHAI có dòng "Tình trạng hôn nhân" ghi rõ "chồng/vợ đã chết" VÀ có dòng tiếp theo dạng
"Theo giấy chứng tử số <N> do <CQ> cấp ngày <D>" hoặc "Theo trích lục khai tử số <N> do <CQ> cấp ngày <D>":

- DeathCert_Number = <N> (SỐ ĐĂNG KÝ, có thể có hậu tố như "12", "212/2022", v.v.)
- DeathCert_Date = <D> (dd/mm/yyyy hoặc dd-mm-yyyy, chuẩn hóa thành dd/mm/yyyy)
- DeathCert_Agency = <CQ> (cơ quan cấp, ví dụ "UBND phường 1 TP Dalat tỉnh Lâm Đồng").
  Chuẩn hóa: "UBND" → "Ủy ban nhân dân", giữ nguyên địa danh phía sau.

LƯU Ý: 
- BẮT BUỘC trả CẢ BA field DeathCert_* khi tờ khai có đủ thông tin số, cơ quan, ngày.
- TUYỆT ĐỐI KHÔNG trả TinhTrangHonNhanC1 khi đã trích được DeathCert_* từ tờ khai, vì Python mapper
  sẽ tự động điền trạng thái "Đã đăng ký kết hôn hoặc đã có vợ/chồng nhưng vợ/chồng đã chết; hiện tại
  chưa đăng ký kết hôn với ai" dựa trên sự hiện diện của DeathCert_*.
- Dòng "Hiện tại chưa đăng ký kết hôn với ai" trong tờ khai CHỈ LÀ phần bổ sung, KHÔNG được dùng để
  đè lên trạng thái GÓA khi đã có thông tin chồng/vợ đã chết.

Ví dụ: TỜ KHAI ghi:
  "Tình trạng hôn nhân: (4) đã đăng ký kết hôn nhưng chồng đã chết
   Theo giấy chứng tử số 12 do UBND phường 1 TP Dalat tỉnh Lâm Đồng cấp ngày 28-2-2005
   Hiện tại chưa đăng ký kết hôn với ai"
→ Trả:
  - DeathCert_Number = "12"
  - DeathCert_Date = "28/02/2005"
  - DeathCert_Agency = "Ủy ban nhân dân phường 1 TP Đà Lạt tỉnh Lâm Đồng"
  - KHÔNG trả TinhTrangHonNhanC1 (để Python mapper xử lý).
</death_cert_from_tokhai>

<source_rules>
- Cccd_* CHỈ lấy từ CCCD/CMND upload (thẻ vật lý được chụp/scan kèm hồ sơ):
  + Trường hợp BẢN THÂN: CCCD upload là của chính người cần giấy XNTTHN.
  + Trường hợp ỦY QUYỀN: CCCD upload là của người ĐƯỢC ủy quyền (đi nộp hộ) — thông tin
    người cần giấy (người ủy quyền) lấy từ GIẤY ỦY QUYỀN → điền vào PoA_Subject*.
- ToKhai_* lấy từ TỜ KHAI cấp giấy XNTTHN, TUYỆT ĐỐI PHẢI TÁCH NGUỒN VỚI Cccd_*:
  + ToKhai_HoTen = dòng "Họ, chữ đệm, tên:" trong phần "Đề nghị cấp Giấy xác nhận tình trạng hôn nhân cho người có tên dưới đây" (Section II - người được cấp).
  + ToKhai_NgaySinh = dòng "Ngày, tháng, năm sinh:" trong phần người được cấp, dd/mm/yyyy.
  + ToKhai_GioiTinh = dòng "Giới tính:" trong phần người được cấp ("Nam" hoặc "Nữ").
  + ToKhai_DanToc = dòng "Dân tộc:" trong phần người được cấp.
  + ToKhai_QuocTich = dòng "Quốc tịch:" trong phần người được cấp.
  + ToKhai_SoDinhDanh = dòng "Giấy tờ tùy thân: ... số" trong phần người được cấp.
  + ToKhai_NgayCapGiayTo = dòng "Cấp ngày..." trong phần người được cấp, dd/mm/yyyy.
  + ToKhai_NoiCapGiayTo = dòng "tại ..." sau "Cấp ngày" trong phần người được cấp.
  + ToKhai_NoiCuTru = dòng "Nơi cư trú:" trong phần người được cấp, object {quocGia,tinh,xa,diaChi}.
  + BẮT BUỘC trả TẤT CẢ các field ToKhai_* khi TỜ KHAI có ghi thông tin tương ứng, NGAY CẢ KHI CCCD cũng có thông tin đó.
  + TUYỆT ĐỐI KHÔNG tự chọn một nguồn rồi bỏ nguồn còn lại; cả ToKhai_* VÀ Cccd_* đều phải được trả khi cả hai nguồn đều có.
- Cccd_NoiCuTru = "Nơi thường trú/Nơi cư trú" trên CCCD/CMND, chỉ lấy từ thẻ CCCD/CMND.
- Nếu có nhiều ảnh CCCD thì gộp mặt trước + mặt sau của cùng một người.
- RIÊNG Cccd_DanToc (dân tộc) — thẻ CCCD/Căn cước mẫu mới thường KHÔNG in dân tộc. THỨ TỰ ƯU TIÊN NGUỒN:
  (1) TỜ KHAI cấp Giấy XNTTHN — dòng "Dân tộc: ..." (ở khối người được cấp) → ToKhai_DanToc;
  (2) thẻ CCCD/CMND nếu có in → Cccd_DanToc. BẮT BUỘC điền ToKhai_DanToc nếu tờ khai ghi, VÀ điền Cccd_DanToc nếu CCCD ghi — ĐỪNG bỏ trống chỉ vì thẻ CCCD không in.
- Cccd_NgayCap (ngày cấp CCCD) — BẮT BUỘC trả nếu BẤT KỲ giấy nào có. Khi có NGÀY Ở NHIỀU CHỖ (mặt sau CCCD và tờ khai), TRẢ CẢ HAI NGUỒN:
  + Cccd_NgayCap: MẶT SAU CCCD — ngày ở dòng "Ngày, tháng, năm / Date, month, year" (dd/mm/yyyy). Ngày này
    CÓ THỂ DÍNH LIỀN nhãn do OCR gộp, vd "...Date, month, year01/05/2021" → Cccd_NgayCap = "01/05/2021".
  + ToKhai_NgayCapGiayTo: Nếu TỜ KHAI có dòng "Giấy tờ tùy thân: CCCD số ... cấp ngày <D>" thì BẮT BUỘC trả ToKhai_NgayCapGiayTo = <D> (dd/mm/yyyy).
  + Cccd_NoiCap nằm gần dòng ngày cấp trên MẶT SAU CCCD; nếu OCR thấy "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH
  VỀ TRẬT TỰ XÃ HỘI" thì trả Cccd_NoiCap = "Cục Cảnh sát quản lý hành chính về trật tự xã hội". Nếu là thẻ CĂN CƯỚC mới (tiêu đề "CĂN CƯỚC"/"IDENTITY CARD", thường cấp từ 01/7/2024) ghi "BỘ CÔNG AN"/"MINISTRY OF PUBLIC SECURITY" thì trả Cccd_NoiCap = "Bộ Công an"; KHÔNG mặc định "Cục Cảnh sát..." cho thẻ này.
  + ToKhai_NoiCapGiayTo: Nếu TỜ KHAI có dòng "tại ..." sau "Cấp ngày" thì BẮT BUỘC trả ToKhai_NoiCapGiayTo.
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
- Nguồn ưu tiên Marriage_*: (1) GIẤY CHỨNG NHẬN/ĐĂNG KÝ KẾT HÔN thật; (2) đoạn "Tình trạng hôn nhân"
  trên TỜ KHAI khi ghi rõ người yêu cầu hiện tại đang có vợ/chồng.
- Marriage_SpouseName = họ tên người vợ/chồng hiện tại. Trên tờ khai lấy sau cụm "đang có chồng là"/
  "đang có vợ là".
- Marriage_Number/Date/Agency chỉ trả khi giấy kết hôn hoặc tờ khai ghi rõ SỐ, NGÀY đăng ký/cấp và CƠ QUAN
  đăng ký/cấp giấy kết hôn tương ứng; thiếu field nào thì bỏ field đó.
- Không lấy số CCCD/CMND, ngày sinh, ngày cấp CCCD hoặc cơ quan cấp CCCD của vợ/chồng làm thông tin
  giấy kết hôn. Đoạn tờ khai kết thúc trước "Mục đích sử dụng".
- Nếu tài liệu là ly hôn/khai tử thì không lấy Marriage_* từ tài liệu đó; ưu tiên trạng thái ly hôn/góa.
</marriage_extraction>

<noi_cu_tru>
- TUYỆT ĐỐI KHÔNG lấy địa chỉ trong đoạn "Tình trạng hôn nhân" làm ToKhai_NoiCuTru; đó là địa chỉ
  của vợ/chồng hoặc địa chỉ cũ được nhắc lại.
- Mỗi địa chỉ trả object {quocGia, tinh, xa, diaChi}. Địa chỉ hành chính hiện hành CHỈ 2 cấp:
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

<address_verification>
Trước khi xuất JSON: nếu TỜ KHAI có dòng "Nơi cư trú" thì output phải có ToKhai_NoiCuTru và Python
sẽ dùng địa chỉ này trước Cccd_NoiCuTru.
</address_verification>

<forbidden_ui_fields>
- Không trả field UI/default như HoVaTenC, HoVaTenC1, SoDinhDanhC, SoDinhDanhC1,
  LoaiGiayToDinhDanhC, LoaiGiayToDinhDanhC1, quanhevoinguoiduocxacminh, mucdich, nhapmucdichkhac,
  loại cư trú, radio trong/ngoài nước. (Purpose vẫn TRẢ — Python sẽ điền vào ô Nhập mục đích.)
- RIÊNG TinhTrangHonNhanC1 được trả khi TỜ KHAI ghi rõ một trong hai trạng thái chuẩn:
  "Hiện tại chưa đăng ký kết hôn với ai" hoặc "Hiện tại đang có vợ/chồng".
  Trạng thái GÓA/ĐÃ LY HÔN do Python chọn từ DeathCert_*/DivorceDecision_* và ưu tiên hơn tờ khai.
- Không suy luận tình trạng hôn nhân từ CCCD vì CCCD không chứa dữ liệu này.
- Nếu thiếu quốc tịch thì bỏ qua Cccd_QuocTich; Python sẽ mặc định Việt Nam.
</forbidden_ui_fields>"""

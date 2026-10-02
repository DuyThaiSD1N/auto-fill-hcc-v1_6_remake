"""Luật trích xuất theo TỪNG LOẠI GIẤY của thủ tục "Xác nhận tình trạng hôn nhân".

Khung chung (vai trò, nhận diện giấy, vai người, định dạng, output) nằm ở ``base_prompt``.
"""

EXTRA_RULES = """<to_khai>
KHỐI NGƯỜI YÊU CẦU — Tờ khai LUÔN có khối "người yêu cầu" RIÊNG ở ĐẦU tờ khai (trước phần "Đề nghị cấp..."), gồm:
  "Họ, chữ đệm, tên người yêu cầu: <tên>"
  "Ngày, tháng, năm sinh: <ngày sinh>"
  "Nơi cư trú: <địa chỉ>"
  "Giấy tờ tùy thân: CCCD/CMND <số> cấp ngày <D> nơi cấp <CQ>"

BẮT BUỘC trả các field sau MỖI KHI tờ khai có khối này, BẤT KỂ người yêu cầu có trùng người được
cấp ở Section II hay không (Python mapper tự so sánh, KHÔNG phải LLM):
- ToKhaiYeuCau_HoTen (từ "Họ, chữ đệm, tên người yêu cầu:")
- ToKhaiYeuCau_NgaySinh (từ "Ngày, tháng, năm sinh:" NGAY DƯỚI tên người yêu cầu, dd/mm/yyyy —
  KHÔNG lấy ngày sinh ở Section II)
- ToKhaiYeuCau_SoDinhDanh (từ "Giấy tờ tùy thân" NGAY SAU tên người yêu cầu, KHÔNG lấy nhầm số ở Section II)
- ToKhaiYeuCau_NgayCapGiayTo (từ "cấp ngày..." của giấy tờ người yêu cầu, dd/mm/yyyy)
- ToKhaiYeuCau_NoiCapGiayTo (từ "nơi cấp ..." của giấy tờ người yêu cầu)
- ToKhaiYeuCau_NoiCuTru (từ "Nơi cư trú:" NGAY DƯỚI tên người yêu cầu, object {quocGia,tinh,xa,diaChi})
- ToKhaiYeuCau_QuanHe (từ dòng "Quan hệ với người được cấp Giấy xác nhận tình trạng hôn nhân:" —
  BẮT BUỘC trả NGUYÊN VĂN khi tờ khai có dòng này, dù ghi "Bản thân"/"Tự khai" hay bất kỳ quan hệ
  nào khác như "là con đẻ", "là bố đẻ". Python mapper sẽ tự quy đổi sang mã quan hệ trên cổng.)
ToKhaiYeuCau_* CHỈ được lấy từ TỜ KHAI (đơn do người dân viết). TUYỆT ĐỐI KHÔNG lấy từ GIẤY XÁC NHẬN
TÌNH TRẠNG HÔN NHÂN ĐÃ CẤP (xem <nguoi_trong_ho_so>).

KHỐI NGƯỜI ĐƯỢC CẤP — QUAN TRỌNG: Khi có TỜ KHAI cấp giấy XNTTHN, BẮT BUỘC trả TẤT CẢ các field ToKhai_* tương ứng
với thông tin trong phần "Đề nghị cấp Giấy xác nhận tình trạng hôn nhân cho người có tên dưới đây" (Section II -
người được cấp):
- ToKhai_HoTen (từ "Họ, chữ đệm, tên:")
- ToKhai_NgaySinh (từ "Ngày, tháng, năm sinh:", dd/mm/yyyy)
- ToKhai_GioiTinh (từ "Giới tính:", "Nam" hoặc "Nữ")
- ToKhai_DanToc (từ "Dân tộc:")
- ToKhai_QuocTich (từ "Quốc tịch:")
- ToKhai_SoDinhDanh (từ "Giấy tờ tùy thân: ... số")
- ToKhai_NgayCapGiayTo (từ "Cấp ngày...", dd/mm/yyyy)
- ToKhai_NoiCapGiayTo (từ "tại ..." sau "Cấp ngày")
- ToKhai_NoiCuTru (từ "Nơi cư trú:", object {quocGia,tinh,xa,diaChi})
TUYỆT ĐỐI KHÔNG bỏ qua các field ToKhai_* chỉ vì CCCD cũng có thông tin tương tự. CẢ HAI NGUỒN (ToKhai_* VÀ
NguoiDuocCap_*) đều phải được trả khi đều có thông tin. Python mapper sẽ quyết định ưu tiên nguồn nào, KHÔNG phải LLM.

TUYỆT ĐỐI KHÔNG gộp thông tin của khối "người yêu cầu" (đầu tờ khai) vào ToKhai_* (khối "người được
cấp", Section II) hay ngược lại — hai khối này LUÔN tách riêng dù trùng người.

NƠI CƯ TRÚ TRÊN TỜ KHAI:
- TUYỆT ĐỐI KHÔNG lấy địa chỉ trong đoạn "Tình trạng hôn nhân" làm ToKhai_NoiCuTru; đó là địa chỉ
  của vợ/chồng hoặc địa chỉ cũ được nhắc lại.
- Trước khi xuất JSON: nếu TỜ KHAI có dòng "Nơi cư trú" thì output phải có ToKhai_NoiCuTru và Python
  sẽ dùng địa chỉ này trước NguoiDuocCap_NoiCuTru.
</to_khai>

<tinh_trang_hon_nhan>
- Từ dòng "Tình trạng hôn nhân" trên TỜ KHAI:
  + Nếu ghi "đã đăng ký kết hôn nhưng chồng đã chết" hoặc "đã đăng ký kết hôn nhưng vợ đã chết"
    hoặc "vợ/chồng đã chết" VÀ CÓ dòng "Theo giấy chứng tử số ... do ... cấp ngày ..." → BẮT BUỘC
    trích xuất DeathCert_Number, DeathCert_Date, DeathCert_Agency từ dòng đó (xem GIẤY CHỨNG TỬ GHI
    TRÊN TỜ KHAI bên dưới). TUYỆT ĐỐI KHÔNG trả TinhTrangHonNhanC1 trong trường hợp này
    (Python mapper sẽ tự điền trạng thái GÓA từ DeathCert_*).
  + Nếu ghi "đã ly hôn" hoặc "đã đăng ký kết hôn nhưng đã ly hôn" VÀ CÓ dòng "Theo bản án/quyết định
    ly hôn số ... do/của ... cấp/ngày ..." → trích xuất DivorceDecision_* (tương tự giấy chứng tử).
    KHÔNG trả TinhTrangHonNhanC1.
  + Nếu nội dung bắt đầu bằng "Chưa kết hôn" hoặc CHỈ ghi "hiện tại chưa đăng ký kết hôn với ai"
    (KHÔNG có thông tin về chồng/vợ đã chết hay ly hôn) → TinhTrangHonNhanC1 = "Hiện tại chưa đăng ký kết hôn với ai".
  + Nếu ghi rõ "hiện tại đang có chồng" hoặc "hiện tại đang có vợ" → TinhTrangHonNhanC1 = "Hiện tại đang có vợ/chồng".
- NGOẠI LỆ ĐÈ LÊN HAI GẠCH ĐẦU DÒNG LY HÔN/GÓA Ở TRÊN — ĐÃ LY HÔN (hoặc góa) RỒI KẾT HÔN LẠI:
  nếu cùng dòng tình trạng hôn nhân còn ghi người đó HIỆN TẠI đã có vợ/chồng ("hiện tại đã kết hôn
  với ...", "hiện nay đã kết hôn với ...", "hiện tại đang có vợ/chồng là ...") thì BẮT BUỘC trả
  TinhTrangHonNhanC1 = "Hiện tại đang có vợ/chồng" (KÈM theo DivorceDecision_*/DeathCert_* và
  Marriage_*). Ly hôn/góa lúc này chỉ là quá khứ; hai trạng thái "…đã ly hôn/vợ chồng đã chết;
  hiện tại chưa đăng ký kết hôn với ai" là SAI SỰ THẬT với người đã cưới lại.
- RIÊNG TinhTrangHonNhanC1 được trả khi TỜ KHAI ghi rõ một trong hai trạng thái chuẩn:
  "Hiện tại chưa đăng ký kết hôn với ai" hoặc "Hiện tại đang có vợ/chồng".
  Trạng thái GÓA/ĐÃ LY HÔN do Python chọn từ DeathCert_*/DivorceDecision_* và ưu tiên hơn tờ khai —
  NHƯNG CHỈ khi người đó HIỆN TẠI CHƯA kết hôn lại. Tờ khai ghi "hiện tại đã kết hôn với ..." thì
  vẫn PHẢI trả TinhTrangHonNhanC1 = "Hiện tại đang có vợ/chồng".
- Không suy luận tình trạng hôn nhân từ CCCD vì CCCD không chứa dữ liệu này.
- Trả ToKhai_LaBanThan=true CHỈ khi dòng quan hệ ghi "Tự khai"/"Bản thân" VÀ họ tên người yêu cầu
  trùng họ tên người được cấp.

GIẤY CHỨNG TỬ GHI TRÊN TỜ KHAI — Khi TỜ KHAI có dòng "Tình trạng hôn nhân" ghi rõ "chồng/vợ đã chết" VÀ có dòng
tiếp theo dạng "Theo giấy chứng tử số <N> do <CQ> cấp ngày <D>" hoặc "Theo trích lục khai tử số <N> do <CQ> cấp
ngày <D>":
- DeathCert_Number = <N> (GIỮ NGUYÊN như tờ khai ghi, kể cả hậu tố: "12", "212/2022", "167/TLKT-BS")
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

KHOẢNG THỜI GIAN CHƯA ĐĂNG KÝ KẾT HÔN:
- Dòng "Tình trạng hôn nhân" của tờ khai có thể xin xác nhận CHƯA ĐĂNG KÝ KẾT HÔN TRONG MỘT KHOẢNG
  THỜI GIAN ĐÃ QUA, kể cả khi HIỆN TẠI người đó đã có vợ/chồng. Các dạng thường gặp:
  + "Từ ngày 01 tháng 01 năm 2025 đến ngày 13 tháng 12 năm 2025. Tôi chưa đăng ký kết hôn với ai.
     Hiện tại đã kết hôn với vợ tên là: ..."
  + "Từ ngày 27/4/2016 đến 14/9/2016 chưa đăng ký kết hôn với ai. Hiện tại đã kết hôn với ..."
  + "Từ 27-4-2016 tới 14-9-2016 chưa đăng ký kết hôn với ai."
- Period_TuNgay = ngày sau chữ "Từ ngày"/"Từ"; Period_DenNgay = ngày sau chữ "đến ngày"/"đến"/"tới".
  Cả hai dd/mm/yyyy, ghép đủ ngày + tháng + năm dù tờ khai viết tách chữ ("ngày 1 tháng 1 năm 2025"
  -> "01/01/2025") hay viết gọn bằng dấu gạch chéo/gạch ngang ("27/4/2016" -> "27/04/2016").
  CHỮ "ngày" CÓ THỂ VẮNG ở một hoặc cả hai đầu mốc — chỉ cần có cặp "Từ ... đến/tới ..." kèm ý
  "chưa đăng ký kết hôn với ai" là PHẢI trả cả hai field.
- BẮT BUỘC trả Period_TuNgay/Period_DenNgay NGAY CẢ KHI cùng dòng đó còn khai ly hôn hoặc vợ/chồng
  đã chết. Đây là ca phổ biến nhất: "Đã kết hôn, ly hôn theo bản án số 12/2016 ngày 27/4/2016 do
  Tòa án ... Từ ngày 27/4/2016 đến 14/9/2016 chưa đăng ký kết hôn với ai. Hiện tại đã kết hôn với
  <tên vợ/chồng>" → trả ĐỦ CẢ BA nhóm: DivorceDecision_*, Period_TuNgay/Period_DenNgay VÀ
  Marriage_* (+ TinhTrangHonNhanC1 = "Hiện tại đang có vợ/chồng").
- MỐC BẮT ĐẦU THƯỜNG TRÙNG NGÀY BẢN ÁN LY HÔN (người ta xin xác nhận từ lúc ly hôn tới lúc cưới
  lại). TUYỆT ĐỐI KHÔNG vì thấy ngày đó đã dùng cho DivorceDecision_Date mà bỏ Period_TuNgay —
  MỘT NGÀY ĐƯỢC PHÉP xuất hiện ở CẢ HAI field. Bỏ Period_* là mất đúng cái khoảng thời gian người
  dân cần xác nhận và cổng sẽ chọn nhầm option "đã ly hôn; hiện tại chưa đăng ký kết hôn với ai".
- HAI ngày này KHÔNG phải ngày đăng ký kết hôn: Marriage_Date vẫn lấy riêng từ giấy chứng nhận kết hôn
  / cụm "Ngày ... tháng ... năm ..." đứng sau số và nơi đăng ký kết hôn. Mốc kết thúc CÓ THỂ trùng
  ngày đăng ký kết hôn hiện tại — vẫn trả cả hai field, không gộp.
- Không thấy cụm "Từ ngày ... đến ngày ..." thì bỏ trống CẢ HAI, không suy từ ngày khác.
- Period_* CHỈ lấy từ TỜ KHAI cấp Giấy XNTTHN. Hồ sơ KHÔNG có tờ khai → KHÔNG trả Period_* (giấy XNTTHN cũ,
  trích lục khai tử, bản án, giấy kết hôn không phải nguồn của Period).
- Ngày vợ/chồng chết ("chồng đã chết ngày ..."), ngày ly hôn, ngày cấp trích lục/bản án, ngày đăng ký kết hôn
  KHÔNG phải Period — chỉ ngày đứng ngay sau đúng cụm "Từ (ngày)" ... "đến/tới (ngày)" của khoảng thời gian
  xin xác nhận chưa đăng ký kết hôn.
- Có "Từ ngày ..." mà không có "đến/tới ..." thì Period_DenNgay để TRỐNG, không tự đặt ngày kết thúc.
</tinh_trang_hon_nhan>

<muc_dich>
- BẮT BUỘC trả Purpose khi TỜ KHAI có dòng "Mục đích sử dụng Giấy xác nhận tình trạng hôn nhân: ...".
- Lấy toàn bộ nội dung sau nhãn trên, nối các dòng liên tiếp; dừng trước "Tôi cam đoan", "Làm tại" hoặc
  "Người yêu cầu". Bỏ "(5)" và nhãn, không bỏ field chỉ vì OCR sai nhẹ trong nội dung.
- TUYỆT ĐỐI KHÔNG cắt ngắn mục đích. Giữ cả những mệnh đề đứng sau dấu phẩy như "không có giá trị
  đăng ký kết hôn" / "không có giá trị sử dụng để đăng ký kết hôn" — đây là nội dung người dân phải
  ghi vào ô "Nhập mục đích(*)" của cổng, thiếu là hồ sơ sai.
  vd "Bổ sung giấy tờ mua bán đất, không có giá trị đăng ký kết hôn"
   -> giữ NGUYÊN cả cụm, KHÔNG rút thành "Bổ sung giấy tờ mua bán đất".
- Thứ tự nguồn: TỜ KHAI hiện tại → "Giấy này được sử dụng để: ..." trên giấy XNTTHN cũ (xem <giay_xntthn_cu>).
</muc_dich>

<the_va_giay_in>
- NguoiDuocCap_* = thông tin IN trên giấy tờ của NGƯỜI ĐƯỢC CẤP. KHÔNG lấy từ tờ khai. Chọn nguồn theo TỪNG
  field, không theo cả nhóm: thẻ CCCD/CMND upload trước; field nào thẻ KHÔNG in (thường là dân tộc) hoặc hồ
  sơ không có thẻ thì lấy từ giấy in khác đứng tên họ — khối "XÁC NHẬN" của giấy XNTTHN cũ, xác nhận thông
  tin cư trú. Riêng dân tộc có field riêng, xem mục dân tộc bên dưới.
- NguoiYeuCau_* = thông tin IN trên thẻ của người ĐI NỘP khi người đó KHÁC người được cấp (người được
  ủy quyền, người thân khai hộ). Chỉ có một người thì để trống.
  + Trường hợp ỦY QUYỀN: thẻ upload thường là của người ĐƯỢC ủy quyền (đi nộp hộ) → NguoiYeuCau_*;
    thông tin người cần giấy (người ủy quyền) lấy từ GIẤY ỦY QUYỀN → PoA_Subject*.
- NguoiDuocCap_NoiCuTru / NguoiYeuCau_NoiCuTru = "Nơi thường trú/Nơi cư trú" in trên thẻ của đúng người đó.
  + Mặt sau thẻ CĂN CƯỚC mới: OCR hay MẤT nhãn "Nơi cư trú / Place of residence", địa chỉ đứng trơ
    trọi ở đầu trang ngay TRƯỚC dòng "Nơi đăng ký khai sinh / Place of birth" → đó chính là
    nơi cư trú của chủ thẻ (vd "Phường A - B, Tỉnh C" → tinh="C", xa="A - B").
  + TUYỆT ĐỐI KHÔNG lấy "Nơi thường trú/tạm trú cuối cùng" hay "Nơi chết" trên GIẤY CHỨNG TỬ/trích
    lục khai tử làm NguoiDuocCap_NoiCuTru — đó là địa chỉ của vợ/chồng đã mất. Thẻ không có địa chỉ thì bỏ trống.
- RIÊNG dân tộc — thẻ CCCD/Căn cước mẫu mới thường KHÔNG in dân tộc. Trả ĐỦ các nguồn có ghi, mỗi nguồn
  một field riêng:
  (1) TỜ KHAI cấp Giấy XNTTHN — dòng "Dân tộc: ..." (ở khối người được cấp) → ToKhai_DanToc;
  (2) THẺ CCCD/CMND của người được cấp nếu có in (CMND cũ có in) → NguoiDuocCap_DanToc;
  (3) giấy tờ KHÁC ghi dân tộc của CHÍNH người được cấp: khối "XÁC NHẬN" của giấy XNTTHN cũ, xác nhận thông
      tin cư trú, giấy chứng nhận kết hôn (đúng cột của người được cấp, xem <giay_ket_hon>), giấy khai sinh
      của chính họ → GiayToKhac_DanToc. BẮT BUỘC trả KỂ CẢ khi hồ sơ có thẻ hoặc tờ khai.
  KHÔNG lấy dân tộc của người đã mất, của con, cha mẹ hay của người vợ/chồng.
- Ngày cấp CCCD — BẮT BUỘC trả nếu BẤT KỲ giấy nào có. Khi có NGÀY Ở NHIỀU CHỖ (mặt sau CCCD và tờ khai), TRẢ CẢ HAI NGUỒN:
  + NguoiDuocCap_NgayCap / NguoiYeuCau_NgayCap: MẶT SAU thẻ của đúng người — ngày ở dòng "Ngày, tháng, năm / Date,
    month, year" (dd/mm/yyyy). Ngày này CÓ THỂ DÍNH LIỀN nhãn do OCR gộp, vd "...Date, month, year01/05/2021" → "01/05/2021".
  + ToKhai_NgayCapGiayTo: Nếu TỜ KHAI có dòng "Giấy tờ tùy thân: CCCD số ... cấp ngày <D>" thì BẮT BUỘC trả
    ToKhai_NgayCapGiayTo = <D> (dd/mm/yyyy).
  + Nơi cấp (NguoiDuocCap_NoiCap / NguoiYeuCau_NoiCap) nằm gần dòng ngày cấp trên MẶT SAU thẻ; chuẩn hóa theo
    <dinh_dang>.
  + ToKhai_NoiCapGiayTo: Nếu TỜ KHAI có dòng "tại ..." sau "Cấp ngày" thì BẮT BUỘC trả ToKhai_NoiCapGiayTo.
</the_va_giay_in>

<giay_uy_quyen>
TRÍCH XUẤT KHI CÓ GIẤY ỦY QUYỀN:

Section I — NGƯỜI ỦY QUYỀN (người CẦN giấy XNTTHN) → các field PoA_Subject*:
- PoA_SubjectName  = họ tên người ủy quyền ở phần "I. Người ủy quyền / Họ và tên: ..."
- PoA_SubjectDoB   = ngày sinh người ủy quyền ("sinh ngày ..."), dd/mm/yyyy
- PoA_SubjectIdNumber = số CCCD/CMND/Hộ chiếu của người ủy quyền ("CMND/CCCD/số hộ chiếu: ...")
- PoA_SubjectIdDate   = ngày cấp giấy tờ của người ủy quyền ("cấp ngày ..."), dd/mm/yyyy
- PoA_SubjectIssuer   = nơi cấp giấy tờ của người ủy quyền ("do ... cấp"), chuẩn hóa theo <dinh_dang>
  + Nếu OCR thấy "Cục Cảnh sát QLHC" / "quản lý hành chính về trật tự" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
  + Nếu thấy "Bộ Công an" → "Bộ Công an"
- PoA_SubjectAddress  = nơi cư trú người ủy quyền ("Nơi cư trú / Địa chỉ: ..."), object {tinh, xa, diaChi}
  (áp quy tắc địa chỉ ở <dinh_dang> để tách tinh/xa/diaChi)
- PoA_SubjectDanToc = dân tộc người ủy quyền nếu giấy ủy quyền ghi ("Dân tộc: Kinh")

THẺ CCCD/CMND CỦA NGƯỜI ỦY QUYỀN (nếu hồ sơ kèm; số thẻ trùng hoặc gần trùng PoA_SubjectIdNumber,
họ tên trùng người ủy quyền) → các field NguoiDuocCap_*, đọc từ BẢN IN trên thẻ (họ tên, số, ngày
sinh, giới tính, ngày cấp, nơi cấp, "Nơi thường trú" object {quocGia, tinh, xa, diaChi}).

Section II — NGƯỜI ĐƯỢC ỦY QUYỀN (người ĐI NỘP hộ) → thẻ của người này thường được upload kèm
→ các field NguoiYeuCau_*, đọc từ BẢN IN trên thẻ. KHÔNG trích người được ủy quyền từ chữ trên
giấy ủy quyền vào NguoiYeuCau_* (chỉ dùng thẻ upload).
Hồ sơ có HAI thẻ thì thẻ người đi nộp vào NguoiYeuCau_*, thẻ người ủy quyền vào NguoiDuocCap_* —
KHÔNG bỏ sót thẻ thứ hai, KHÔNG trộn hai thẻ.

LƯU Ý QUAN TRỌNG:
- Nếu giấy ủy quyền chỉ ghi tên KHÔNG kèm CCCD/ngày sinh người ủy quyền → vẫn trả PoA_SubjectName,
  bỏ qua các field còn lại nếu không có.
- Khi có cả CCCD và giấy ủy quyền: CCCD upload thường là của người ĐƯỢC ủy quyền (đi nộp hộ).
  Đối chiếu tên CCCD với Section II giấy ủy quyền để xác nhận.
- TUYỆT ĐỐI KHÔNG nhầm người ủy quyền (Section I) với người được ủy quyền (Section II).
</giay_uy_quyen>

<giay_khai_tu>
- DeathCert_* lấy từ OCR tài liệu khai tử thật của VỢ/CHỒNG (giấy chứng tử, trích lục khai tử, giấy
  báo tử), HOẶC từ dòng tình trạng hôn nhân trên tờ khai / giấy XNTTHN cũ (nhắc lại "Giấy chứng tử số ...").
  KHÔNG lấy từ CCCD người yêu cầu; thông tin người chết là VỢ/CHỒNG, không phải người yêu cầu — không điền
  NguoiDuocCap_*.

Cổng hỏi "Số / Ngày cấp / Cơ quan cấp Giấy chứng tử/Trích lục khai tử/Bản án" = thông tin của CHÍNH TỜ
GIẤY ĐANG NỘP, KHÔNG phải số/ngày của lần đăng ký khai tử gốc trong sổ.

- DeathCert_Number = số ở nhãn "Số:" ĐẦU trang của chính tài liệu đang xét, GIỮ NGUYÊN cả hậu tố loại
  ("/TLKT-BS", "/TLKT", "-BS", "/CT"), vd "167/TLKT-BS", "212/2022/TLKT-BS".
  + TUYỆT ĐỐI KHÔNG lấy số ở dòng thân "Đã được đăng ký khai tử tại: <cơ quan> ... Số: <N> ngày <D>" —
    đó là số ĐĂNG KÝ GỐC trong sổ, chỉ là dẫn chiếu, KHÔNG phải số của giấy đang nộp.
  + CHỈ khi đầu trang KHÔNG có nhãn "Số:" nào đọc được thì mới lùi về số ở dòng đăng ký gốc.
- DeathCert_Date = NGÀY CẤP/KÝ chính tài liệu đó — dòng địa danh + ngày ở đầu văn bản
  ("Nghĩa Thương, ngày 07 tháng 11 năm 2024") hoặc ngày ở khối ký cuối văn bản; chuẩn hóa dd/mm/yyyy.
  + KHÔNG lấy ngày chết, ngày sinh của người chết.
  + KHÔNG lấy ngày trên dòng "Đã được đăng ký khai tử tại ... Số: <N> ngày <D>" (ngày đăng ký gốc),
    trừ khi tài liệu không có ngày cấp/ký nào khác.
  + DeathCert_Number và DeathCert_Date phải CÙNG MỘT NGUỒN: cùng lấy từ đầu trang, hoặc cùng lùi về
    dòng đăng ký gốc — KHÔNG trộn số của giấy với ngày đăng ký gốc.
- DeathCert_Agency = cơ quan CẤP/KÝ chính tài liệu đó (khối tiêu đề "UBND XÃ ..." hoặc khối ký
  "TM. ỦY BAN NHÂN DÂN XÃ"), vd "Ủy ban nhân dân xã Nghĩa Thương". Nếu đầu trang không rõ thì lấy cơ quan
  ở dòng "Đã được đăng ký khai tử tại: <cơ quan>". Chuẩn hóa "UBND" → "Ủy ban nhân dân" nếu cần.
- Chỉ trả DeathCert_* khi tài liệu thật sự là giấy khai tử/chứng tử/báo tử/trích lục khai tử có đủ dấu hiệu.
  Nếu chỉ có CCCD thì bỏ qua toàn bộ DeathCert_*.

Ví dụ: TRÍCH LỤC KHAI TỬ (BẢN SAO) của UBND xã Nghĩa Thương:
  "UBND XÃ NGHĨA THƯƠNG ... Số: 167/TLKT-BS ... Nghĩa Thương, ngày 07 tháng 11 năm 2024
   TRÍCH LỤC KHAI TỬ (BẢN SAO) ...
   Đã được đăng ký khai tử tại: UBND xã Nghĩa Thương, huyện Tư Nghĩa, tỉnh Quảng Ngãi
   Số: 116 ngày 11/12/2009"
→ Trả:
  - DeathCert_Number = "167/TLKT-BS"          (ĐÚNG — số của giấy đang nộp)
  - DeathCert_Date   = "07/11/2024"           (ĐÚNG — ngày cấp giấy đang nộp)
  - DeathCert_Agency = "Ủy ban nhân dân xã Nghĩa Thương"
  KHÔNG trả DeathCert_Number = "116" / DeathCert_Date = "11/12/2009" (SAI — đó là đăng ký gốc trong sổ).
</giay_khai_tu>

<ban_an_ly_hon>
- DivorceDecision_* lấy từ tài liệu quyết định/bản án ly hôn thật (dấu hiệu ở <giay_to>), HOẶC từ dòng tình trạng
  hôn nhân trên tờ khai / giấy XNTTHN cũ (nhắc lại "Bản án/Quyết định ly hôn số ..."). Không dùng tên file để kết luận.
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
- Chỉ trả DivorceDecision_* khi có bản án/quyết định ly hôn thật HOẶC tờ khai / giấy XNTTHN cũ ghi đã ly hôn
  theo bản án/quyết định số .... Nếu chỉ có CCCD hoặc giấy tờ không nhắc tới ly hôn thì bỏ qua toàn bộ DivorceDecision_*.
- BẢN ÁN/QUYẾT ĐỊNH LY HÔN GHI TRÊN TỜ KHAI — hồ sơ KHÔNG có văn bản bản án/quyết định mà dòng tình trạng hôn nhân
  của tờ khai (hoặc giấy XNTTHN cũ) ghi đã ly hôn theo bản án/quyết định số <N> của/do <CQ> ... ngày <D>:
  + BẮT BUỘC trả ĐỦ CẢ BA field khi dòng đó có: DivorceDecision_Number = <N> (GIỮ NGUYÊN số và ký hiệu như
    "105/2018/QĐST-HNGĐ"), DivorceDecision_Agency = <CQ> (chuẩn hóa "TAND" → "Tòa án nhân dân"),
    DivorceDecision_Date = <D>.
  + <D> là ngày GẮN VỚI việc ly hôn trên chính dòng đó, có thể đứng SAU số ("số ... ngày <D>") hoặc đứng TRƯỚC
    ("đến ngày <D> thì ly hôn theo quyết định số ..."). KHÔNG lấy ngày đăng ký kết hôn ("ngày ... đã đăng ký kết
    hôn với ...") hay ngày làm tờ khai.
  + Có văn bản bản án/quyết định thật thì lấy theo văn bản đó (các gạch đầu dòng trên), không lấy từ tờ khai.
</ban_an_ly_hon>

<giay_ket_hon>
- Nguồn ưu tiên Marriage_*: (1) GIẤY CHỨNG NHẬN/ĐĂNG KÝ KẾT HÔN thật; (2) đoạn "Tình trạng hôn nhân"
  trên TỜ KHAI khi ghi rõ người yêu cầu hiện tại đang có vợ/chồng.
- Marriage_SpouseName = họ tên người vợ/chồng HIỆN TẠI. Trên tờ khai lấy sau cụm "đang có chồng là"/
  "đang có vợ là", hoặc sau các cụm "hiện tại đã kết hôn với", "hiện nay đã kết hôn với",
  "đã kết hôn với ông/bà".
  BẮT BUỘC trả khi tờ khai có một trong các cụm này, KỂ CẢ khi phía trước còn khai ly hôn/góa.
  Chỉ lấy HỌ TÊN; ngày sinh, số CCCD, ngày cấp CCCD của vợ/chồng đi kèm thì BỎ, không nhét vào
  Marriage_Number/Marriage_Date.
- Giấy chứng nhận kết hôn in HAI CỘT: cột trái là VỢ ("Họ, chữ đệm, tên vợ"), cột phải là CHỒNG ("Họ, chữ
  đệm, tên chồng"). OCR thường gộp hai cột thành một dòng, vd "Dân tộc: <vợ> Dân tộc: <chồng>" — giá trị
  ĐẦU là của VỢ, giá trị SAU là của CHỒNG. Xác định người được cấp là vợ hay chồng (so họ tên với thẻ / tờ
  khai / người còn lại là Marriage_SpouseName) rồi lấy dân tộc ở cột của người đó → GiayToKhac_DanToc,
  KỂ CẢ khi hồ sơ có thẻ. KHÔNG lấy dân tộc ở cột của người vợ/chồng kia.
- Marriage_Number/Date/Agency chỉ trả khi giấy kết hôn hoặc tờ khai ghi rõ SỐ, NGÀY đăng ký/cấp và CƠ QUAN
  đăng ký/cấp giấy kết hôn tương ứng; thiếu field nào thì bỏ field đó.
- Không lấy số CCCD/CMND, ngày sinh, ngày cấp CCCD hoặc cơ quan cấp CCCD của vợ/chồng làm thông tin
  giấy kết hôn. Đoạn tờ khai kết thúc trước "Mục đích sử dụng".
- Nếu tài liệu là ly hôn/khai tử thì không lấy Marriage_* từ tài liệu đó; ưu tiên trạng thái ly hôn/góa.
  NGOẠI LỆ: cuộc hôn nhân MỚI đăng ký SAU ngày ly hôn/ngày chết (tờ khai ghi "hiện tại đã kết hôn
  với ..." hoặc có giấy kết hôn mới) thì VẪN trả Marriage_* — đó là hôn nhân hiện tại, không phải
  cuộc hôn nhân đã chấm dứt.
</giay_ket_hon>

<giay_xntthn_cu>
Nếu có GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN CŨ (tiêu đề "GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN"), giấy này
NHẮC LẠI tình trạng hôn nhân + giấy tờ liên quan + mục đích → được phép dùng làm NGUỒN:
- Nếu dòng tình trạng hôn nhân ghi "... chồng/vợ đã chết (theo Giấy chứng tử/Trích lục khai tử số <N> do <CQ>
  cấp ngày <D>)" → DeathCert_Number=<N> (GIỮ NGUYÊN như ghi trên giấy, KỂ CẢ hậu tố "/TLKT-BS"),
  DeathCert_Date=<D> (dd/mm/yyyy), DeathCert_Agency=<CQ> (bỏ chữ "cấp").
- Nếu ghi "... đã ly hôn (Bản án/Quyết định ly hôn số <N> ngày <D> của <CQ>)"
  → DivorceDecision_Number/Date/Agency tương ứng.
- Purpose: lấy NGUYÊN VĂN từ "Giấy này được sử dụng để: <mục đích>", GIỮ TRỌN câu tới hết dòng.
  Mệnh đề "không có giá trị sử dụng để đăng ký kết hôn" là MỘT PHẦN của mục đích, phải giữ — dù nó
  nằm trong ngoặc hay nối bằng dấu phẩy. Chỉ bỏ đúng cái nhãn phía trước.
  vd "Giao dịch nhà, đất, không có giá trị sử dụng để đăng ký kết hôn"
   -> Purpose = "Giao dịch nhà, đất, không có giá trị sử dụng để đăng ký kết hôn"  (ĐÚNG)
   -> Purpose = "Giao dịch nhà, đất"                                               (SAI, cắt cụt)
- Nhân thân người được cấp in ở khối "XÁC NHẬN" (họ tên, ngày sinh, giới tính, số giấy tờ...) →
  NguoiDuocCap_*. Dòng "Dân tộc: ..." ở khối này → BẮT BUỘC trả GiayToKhac_DanToc, KỂ CẢ khi hồ sơ có thẻ
  CCCD (thẻ mẫu mới không in dân tộc nên đây thường là nguồn dân tộc duy nhất).
</giay_xntthn_cu>"""

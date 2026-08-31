"""Compact prompt rules cho "Thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc"."""

EXTRA_RULES = """
<procedure>
Đầu vào gồm MỘT giấy tờ hộ tịch chính và một hoặc nhiều CCCD đính kèm:
- Giấy khai sinh: chủ thể là NGƯỜI ĐƯỢC KHAI SINH (con).
- Trích lục/Giấy chứng nhận kết hôn hoặc giấy cũ có tên "hôn thú"/"tạm thay hôn thú": có hai bên
  CHỒNG (bên nam) và VỢ (bên nữ); có thể kèm CCCD người yêu cầu và CCCD của người có nội dung thay đổi.
- Trích lục khai tử: chủ thể là NGƯỜI ĐÃ MẤT.
Nhiệm vụ: trích loại sự kiện, danh tính chủ thể (hoặc cả hai bên kết hôn) và metadata hồ sơ gốc.
</procedure>

<source_priority>
- TỜ KHAI THẮNG TẤT CẢ (QUAN TRỌNG NHẤT): nếu đầu vào CÓ tờ khai đăng ký thay đổi/cải chính/bổ sung
  thông tin hộ tịch/xác định lại dân tộc, thì CHÍNH TỜ KHAI là nguồn quyết định:
  + ChuThe_* = người ở khối "cho người có tên dưới đây" của TỜ KHAI.
  + HoSo_So/HoSo_QuyenSo/HoSo_NgayDangKy/HoSo_NoiDangKy = dòng "Đã đăng ký <sự kiện> tại <cơ quan>
    ngày <D> số <N> quyển số <Q>" của TỜ KHAI; LoaiSuKien theo đúng sự kiện ghi ở dòng đó.
  Mọi giấy khai sinh / trích lục kết hôn / trích lục khai tử kèm theo chỉ là GIẤY TỜ CHỨNG MINH và
  RẤT THƯỜNG là của NGƯỜI KHÁC (con, cha, mẹ, người ủy quyền...). TUYỆT ĐỐI KHÔNG lấy chủ thể hay
  số/quyển/ngày/nơi đăng ký của những giấy đó khi tờ khai đã ghi rõ — kể cả khi giấy đó là GIẤY KHAI SINH.
  Chỉ dùng chúng để BỔ SUNG ô mà tờ khai bỏ trống, và chỉ khi giấy đó đúng là của người trong tờ khai
  (đối chiếu họ tên + ngày sinh + số định danh).
- KHÔNG có tờ khai thì mới chọn giấy tờ hộ tịch chính theo <event_type> bên dưới.
</source_priority>

<event_type>
- Chỉ nhận diện LoaiSuKien từ GIẤY TỜ HỘ TỊCH hoặc TỜ KHAI, tuyệt đối KHÔNG lấy CCCD/CMND làm
  giấy hộ tịch chính. Các dòng "Ngày sinh" trên CCCD không phải căn cứ để chọn LoaiSuKien="birth".
- ƯU TIÊN GIẤY KHAI SINH — CHỈ ÁP DỤNG KHI KHÔNG CÓ TỜ KHAI: nếu đầu vào KHÔNG có tờ khai mà có NHIỀU
  giấy tờ hộ tịch cùng lúc (vd vừa có GIẤY KHAI SINH vừa có GIẤY CHỨNG NHẬN KẾT HÔN, hoặc thêm giấy khác),
  thì chọn GIẤY KHAI SINH làm giấy tờ hộ tịch CHÍNH:
  → LoaiSuKien="birth"; TenGiayTo theo giấy khai sinh; trích CHỦ THỂ (người được khai sinh/con) vào nhóm ChuThe_*;
  HoSo_So/HoSo_QuyenSo/HoSo_NgayDangKy/HoSo_NoiDangKy lấy TỪ GIẤY KHAI SINH (số/quyển/ngày/nơi ĐĂNG KÝ KHAI SINH).
  KHÔNG chọn giấy kết hôn (hay giấy khác) làm nguồn chính khi ĐÃ CÓ giấy khai sinh. Chỉ khi KHÔNG có
  giấy khai sinh mới xét đến kết hôn/khai tử.
  CÓ TỜ KHAI thì quy tắc này KHÔNG áp dụng — theo <source_priority>.
- LoaiSuKien = "birth" nếu giấy tờ là Giấy khai sinh/Trích lục khai sinh.
- LoaiSuKien = "marriage" nếu là Giấy chứng nhận kết hôn/Trích lục kết hôn, hoặc giấy lịch sử có
  tiêu đề/nội dung "HÔN THÚ", "GIẤY CHỨNG NHẬN TẠM THAY HÔN THÚ", "đã kết hôn"
  (CHỈ khi không có giấy khai sinh). "Hôn thú" là cách gọi cũ của việc kết hôn.
- LoaiSuKien = "death" nếu là Trích lục khai tử/Giấy chứng tử/Giấy báo tử (CHỈ khi không có giấy khai sinh).
- TenGiayTo: tên giấy tờ đúng theo OCR (của giấy được chọn làm nguồn chính).
</event_type>

<subject_extraction>

- birth: trích danh tính CON vào nhóm ChuThe_* (ChuThe_HoTen, ChuThe_NgaySinh đủ dd/mm/yyyy nếu có,
  ChuThe_GioiTinh, ChuThe_DanToc, ChuThe_QuocTich, ChuThe_SoDinhDanh, ChuThe_SoGiayToTuyThan, ChuThe_NgayCapGiayTo, ChuThe_NoiCapGiayTo nếu giấy có, ChuThe_NoiCuTru).
  NẾU CHỦ THỂ (con) CÓ CCCD/CMND RIÊNG trong các file đính kèm (thẻ có SỐ khớp ChuThe_SoDinhDanh, hoặc HỌ TÊN
  khớp chủ thể) → BẮT BUỘC trích thêm từ MẶT SAU chính thẻ đó: ChuThe_NgayCapGiayTo (dòng "Ngày, tháng, năm /
  Date, month, year", dd/mm/yyyy, có thể dính liền nhãn "year") và ChuThe_NoiCapGiayTo ("Cục Cảnh sát quản lý
  hành chính về trật tự xã hội" / "Bộ Công an"). TUYỆT ĐỐI KHÔNG lấy nhầm ngày/nơi cấp của CCCD CHA/MẸ —
  phải khớp ĐÚNG thẻ của chủ thể (đối chiếu số định danh/họ tên).
- death: trích danh tính NGƯỜI ĐÃ MẤT vào nhóm ChuThe_* (đủ các trường như trên + số định danh,
  ngày/nơi cấp giấy tờ tùy thân nếu trích lục có ghi).
- marriage: trích ĐẦY ĐỦ danh tính CHỒNG vào nhóm Chong_* và VỢ vào nhóm Vo_*
  (HoTen, NgaySinh, GioiTinh, DanToc, QuocTich, SoDinhDanh, SoGiayTo, NgayCapGiayTo, NoiCapGiayTo, NoiCuTru).
  KHÔNG trộn lẫn thông tin chồng sang vợ và ngược lại.
- Với MỌI CCCD/CMND đã upload: BẮT BUỘC đối chiếu họ tên không dấu + số định danh + ngày sinh với
  ChuThe/Chong/Vo. Nếu khớp người nào thì hợp nhất dữ liệu thẻ vào đúng nhóm người đó; KHÔNG được bỏ qua
  CCCD chỉ vì thẻ đó không phải của người yêu cầu.
- Khi đã có CCCD khớp người:
  + HoTen, NgaySinh, GioiTinh, QuocTich, SoDinhDanh, NgayCapGiayTo, NoiCapGiayTo của người đó
    BẮT BUỘC lấy từ CCCD; giấy hộ tịch chỉ bổ sung field CCCD không có.
  + RIÊNG ChuThe_NoiCuTru: nếu có TỜ KHAI cải chính và khối "cho người có tên dưới đây" ghi nơi cư trú
    thì BẮT BUỘC ưu tiên nơi cư trú trên TỜ KHAI; chỉ khi khối này không có mới lấy CCCD, sau cùng mới
    lấy giấy tờ hộ tịch gốc. CCCD không được ghi đè nơi cư trú hiện tại đã khai trên tờ khai.
  + Họ tên trên giấy cũ có dấu gạch nối giữa các tiếng nhưng CCCD không có thì trả tên chuẩn theo CCCD.
  + Nếu nơi cư trú trên giấy hộ tịch cũ khác nơi thường trú trên CCCD thì PHẢI trả nơi trên CCCD.
    Không được giữ địa chỉ cũ của giấy kết hôn/hôn thú.
  + Phải trả đủ 8 field đọc chắc chắn trên CCCD vào đúng prefix người khớp:
    <prefix>_HoTen, <prefix>_NgaySinh, <prefix>_GioiTinh, <prefix>_QuocTich,
    <prefix>_SoDinhDanh, <prefix>_NgayCapGiayTo, <prefix>_NoiCapGiayTo, <prefix>_NoiCuTru.
    Không chỉ trả họ tên/ngày sinh/số định danh.
- DanToc CHỈ trả khi chính giấy tờ OCR có ghi rõ dân tộc của đúng người đó. CCCD không có trường dân tộc,
  vì vậy tuyệt đối KHÔNG suy dân tộc từ CCCD, họ tên, quê quán, địa bàn hoặc dân tộc người khác.
  OCR không ghi thì bắt buộc bỏ field DanToc.
</subject_extraction>

<cccd_attached>
- identity_document_context do Python cung cấp sẽ chỉ rõ tài liệu CCCD nào khớp người yêu cầu trên UI.
- DanhSachCccd là bảng nguồn độc lập và BẮT BUỘC: trả đúng một object cho MỖI CCCD/CMND đã upload,
  theo đúng cấu trúc [{HoTen,SoDinhDanh,NgaySinh,GioiTinh,QuocTich,NgayCap,NoiCap,NoiCuTru}].
  Đọc từng thẻ riêng biệt, không trộn hai thẻ vào một object và không bỏ thẻ không phải người yêu cầu.
- DanhSachCccd phải giữ đúng nơi thường trú trên từng CCCD. Không lấy địa chỉ trên giấy hộ tịch đưa vào
  object CCCD. Đây là nguồn để Python đối chiếu và ghi đè tất định dữ liệu cũ.
- Cccd_HoTen, Cccd_SoDinhDanh, Cccd_NgayCap, Cccd_NoiCap CHỈ lấy từ CCCD/CMND người yêu cầu
  đã được context xác định, KHÔNG lấy từ giấy tờ hộ tịch hoặc CCCD người khác.
- MỌI CCCD khác người yêu cầu vẫn BẮT BUỘC được đối chiếu và hợp nhất vào ChuThe_*/Chong_*/Vo_* tương ứng.
  Không có CCCD nào được phép bị bỏ qua nếu họ tên/số định danh/ngày sinh khớp một chủ thể hộ tịch.
- Sau khi ghép, tự kiểm tra riêng từng CCCD khác người yêu cầu: nếu thẻ đọc được giới tính, quốc tịch,
  số định danh, ngày cấp, nơi cấp, nơi thường trú mà nhóm người tương ứng còn thiếu hoặc đang giữ giá trị
  khác từ giấy hộ tịch cũ thì output là SAI; phải sửa nhóm đó theo CCCD trước khi trả JSON.
- BẮT BUỘC cố đọc Cccd_NgayCap (dòng "Ngày, tháng, năm / Date, month, year" MẶT SAU, có thể dính liền nhãn "year") và
  Cccd_NoiCap ("CỤC TRƯỞNG CỤC CẢNH SÁT..." → "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; "BỘ CÔNG AN" → "Bộ Công an").
- Dùng để Python xác định người yêu cầu có phải chồng/vợ hay không. Nếu người yêu cầu không phải chồng/vợ
  nhưng có đúng một CCCD khác khớp chồng hoặc vợ thì người có CCCD khớp đó là ứng viên người có nội dung thay đổi.
</cccd_attached>

<to_khai_cai_chinh>
- TRƯỜNG HỢP đầu vào là TỜ KHAI ĐĂNG KÝ VIỆC THAY ĐỔI/CẢI CHÍNH/BỔ SUNG THÔNG TIN HỘ TỊCH/XÁC ĐỊNH LẠI DÂN TỘC
  (tiêu đề tờ khai, KHÔNG phải giấy khai sinh/trích lục):
  + NGƯỜI ĐƯỢC thay đổi/cải chính nằm ở KHỐI "cho người có tên dưới đây" (ngay sau cụm "Đề nghị cơ quan đăng ký
    ... cho người có tên dưới đây"). ĐÂY LÀ NGUỒN DUY NHẤT cho ChuThe_* khi có tờ khai — người ở khối này
    THƯỜNG KHÁC người yêu cầu và KHÁC chủ thể của giấy khai sinh/kết hôn/khai tử nộp kèm; lấy nhầm sang
    người của giấy nộp kèm là SAI. Trích ĐẦY ĐỦ danh tính người này vào nhóm ChuThe_*: ChuThe_HoTen,
    ChuThe_NgaySinh (dd/mm/yyyy), ChuThe_GioiTinh, ChuThe_DanToc, ChuThe_QuocTich, ChuThe_SoDinhDanh,
    ChuThe_SoGiayTo, ChuThe_NgayCapGiayTo, ChuThe_NoiCapGiayTo, ChuThe_NoiCuTru.
  + ChuThe_NoiCuTru phải lấy đúng dòng "Nơi cư trú" trong KHỐI NGƯỜI ĐƯỢC thay đổi/cải chính
    (sau cụm "cho người có tên dưới đây"), KHÔNG lấy dòng nơi cư trú ở khối người yêu cầu phía trên.
    Nguồn này ưu tiên hơn nơi thường trú trên CCCD của chủ thể.
  + GIẤY TỜ TÙY THÂN — dòng "Giấy tờ tùy thân: CCCD/CMND <N> ... cấp ngày <D> ..." chứa ĐỦ 3 giá trị CÙNG MỘT DÒNG.
    BẮT BUỘC trích RIÊNG cả 3, KHÔNG gộp/bỏ sót, DÙ dòng viết theo THỨ TỰ nào (số→nơi→ngày HAY số→ngày→nơi):
      • ChuThe_SoDinhDanh = <N> — DÃY SỐ ngay sau "CCCD"/"CMND"/"số" (CÓ THỂ KHÔNG có chữ "số", vd "CCCD 068190005725").
      • ChuThe_NoiCapGiayTo = <nơi cấp> — CƠ QUAN cấp, đứng sau chữ "do" HOẶC "tại" (vd "... do Cục CS QLHC về TTXH cấp ngày ...").
        "Cục CS QLHC về TTXH" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; "Bộ Công an" → "Bộ Công an".
      • ChuThe_NgayCapGiayTo = <D> — ngày ngay sau "cấp ngày" (dd/mm/yyyy). TRƯỜNG NÀY HAY BỊ BỎ SÓT NHẤT, BẮT BUỘC PHẢI CÓ.
        Đã trích số định danh mà thiếu ngày cấp/nơi cấp là SAI — soát lại cụm "do <nơi> cấp ngày <D>" HOẶC "cấp ngày <D> tại <nơi>".
    Ví dụ 1: "Giấy tờ tùy thân: CMND số 111222333 cấp ngày 02/03/2016 tại Công an tỉnh AB" →
      ChuThe_SoDinhDanh="111222333", ChuThe_NgayCapGiayTo="02/03/2016", ChuThe_NoiCapGiayTo="Công an tỉnh AB".
    Ví dụ 2: "Giấy tờ tùy thân: CCCD 444555666777 do Cục CS QLHC về TTXH cấp ngày 20/11/2021" →
      ChuThe_SoDinhDanh="444555666777", ChuThe_NoiCapGiayTo="Cục Cảnh sát quản lý hành chính về trật tự xã hội", ChuThe_NgayCapGiayTo="20/11/2021".
  + KHỐI ĐẦU (trước "cho người có tên dưới đây") là NGƯỜI YÊU CẦU (mục I) — cổng tự điền, KHÔNG trích vào ChuThe_*.
    Nhưng vẫn phải trả mọi CCCD vào DanhSachCccd và được lấy Cccd_HoTen/Cccd_SoDinhDanh của người yêu cầu
    để đối chiếu. (Nếu người yêu cầu = "Bản thân" thì người yêu cầu và người được cải chính là CÙNG một
    người — vẫn trích người đó vào ChuThe_*.)
  + NguoiYeuCau_QuanHe — ngay dưới khối người yêu cầu (mục I) có dòng ô tích riêng "Quan hệ với người được
    thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc: Bản thân [ ] Khác [ ]" (KHÁC dòng
    "Đề nghị cơ quan đăng ký việc..." của mục III). Đọc ô nào có dấu tích/tô đậm/khoanh ("[x]"/"[X]"/"☑"/
    chấm đen) → trả đúng "Bản thân" hoặc "Khác". Không thấy dòng này, hoặc thấy nhưng không rõ ô nào được
    tích, thì BỎ field — KHÔNG suy từ việc họ tên người yêu cầu có trùng người được cải chính hay không
    (Python sẽ tự đối chiếu CCCD/họ tên làm dự phòng khi field này trống).
  + SỰ KIỆN HỘ TỊCH LIÊN QUAN đã đăng ký (vd "Đã đăng ký kết hôn/khai sinh tại <cơ quan> ... số <N> quyển <Q>
    ngày <D>") → HoSo_So=<N>, HoSo_QuyenSo=<Q>, HoSo_NgayDangKy=<D>, HoSo_NoiDangKy=<cơ quan>; LoaiSuKien theo
    sự kiện đó (kết hôn→"marriage", khai sinh→"birth", khai tử→"death").
    Dòng này của TỜ KHAI ưu tiên hơn số/quyển/ngày/nơi đăng ký in trên giấy khai sinh nộp kèm — giấy kèm
    thường là của NGƯỜI KHÁC. Chỉ ô nào tờ khai để TRỐNG mới lấy từ giấy kèm, và chỉ khi giấy kèm đúng là
    của người trong khối "cho người có tên dưới đây".
  + NoiDungThayDoi = mục "Nội dung: ..." (nội dung đề nghị cải chính, vd "Cải chính tên từ X sang Y").
  + LyDo = mục "Lý do: ..." nếu có.
  + ViecDangKy = LOẠI VIỆC đăng ký, đọc ở dòng "Đề nghị cơ quan đăng ký việc <X> ... cho người có tên dưới đây".
    CHỈ lấy ở dòng này — TUYỆT ĐỐI KHÔNG lấy từ TIÊU ĐỀ tờ khai (tiêu đề luôn liệt kê CẢ 4 loại).
    Trả về ĐÚNG MỘT trong 5 GIÁ TRỊ sau (nguyên văn, không thêm/bớt chữ):
      • "Cải chính" — khi <X> nói CẢI CHÍNH (vd "cải chính thông tin hộ tịch", "cải chính hộ tịch", "cải chính phần khai về...").
      • "Thay đổi" — khi <X> nói THAY ĐỔI (thay đổi họ/chữ đệm/tên...).
      • "Bổ sung hộ tịch" — khi <X> nói BỔ SUNG thông tin hộ tịch.
      • "Xác định lại dân tộc" — khi <X> nói XÁC ĐỊNH LẠI DÂN TỘC.
      • "" (rỗng) — khi không đọc được dòng đó hoặc không rõ thuộc loại nào.
</to_khai_cai_chinh>

<noi_cu_tru>
- Địa chỉ hành chính hiện hành CHỈ có 2 cấp: XÃ/PHƯỜNG/THỊ TRẤN rồi đến TỈNH/THÀNH PHỐ
  (KHÔNG còn cấp huyện/quận). Với MỌI trường NoiCuTru (ChuThe_NoiCuTru, Chong_NoiCuTru, Vo_NoiCuTru):
  trả object {quocGia, tinh, xa, diaChi}.
- Khi chuỗi nơi cư trú có dạng "<chi tiết>, xã/phường/thị trấn <X>, tỉnh/thành phố <Y>":
  + xa = "<X>" (BẮT BUỘC trích khi nguồn có ghi xã/phường/thị trấn; có thể bỏ tiền tố loại đơn vị).
  + tinh = "<Y>".
  + diaChi = phần CHI TIẾT còn lại (số nhà/thôn/bản/tổ dân phố), KHÔNG nhét tên xã hay tên tỉnh vào diaChi.
- ĐẾM TỪ CUỐI khi địa chỉ liệt kê không nhãn (dạng cũ 3 cấp "[chi tiết], xã, HUYỆN, tỉnh"): cuối = tỉnh;
  phần NGAY TRƯỚC tỉnh nếu là CẤP HUYỆN (huyện/quận/thị xã/thành phố thuộc tỉnh) thì BỎ HẲN; phần trước đó
  = xã. Tên xã/phường vùng cao CÓ THỂ bắt đầu bằng "Bản"/"Nậm"/"Mường"/"Pa" — KHÔNG coi là chi tiết chỉ vì
  bắt đầu bằng "Bản", VỊ TRÍ (áp chót, trước cấp huyện/tỉnh) mới quyết định là xã.
- Tuyệt đối KHÔNG bỏ trống xa nếu chuỗi địa chỉ có chứa tên xã/phường/thị trấn.
- VIẾT TẮT cấp đơn vị: "P." = Phường, "TT." = Thị trấn, "TP."/"Tp." = Thành phố, "H." = Huyện, "Q." = Quận,
  "X." = Xã.
- FEW-SHOT thành phố thuộc tỉnh: nếu phần tử CUỐI của địa chỉ là THÀNH PHỐ THUỘC TỈNH (KHÔNG phải tỉnh trực
  thuộc TW), vd "Đà Lạt"/"Bảo Lộc" → đó là CẤP HUYỆN nên BỎ khỏi xã/chi tiết; tinh = TỈNH chứa thành phố đó
  ("Đà Lạt"/"Bảo Lộc" → tinh="Lâm Đồng").
- Nếu một bên (chồng/vợ) có dòng nơi cư trú riêng, gán đúng cho bên đó, không trộn của bên kia.
</noi_cu_tru>

<ho_so_goc>
- HoSo_So: số đăng ký/số trích lục. HoSo_QuyenSo: quyển số. HoSo_NgayDangKy: ngày đăng ký dd/mm/yyyy.
- HoSo_NoiDangKy: nơi đăng ký hồ sơ gốc (cơ quan đã đăng ký sự kiện hộ tịch trước đây).
- Chỉ trả khi giấy tờ có giá trị thật; để trống nếu OCR không rõ.
</ho_so_goc>

<forbidden_ui_fields>
- KHÔNG trả field UI/default: nycLoaiCuTru, nycNoiCuTru, ntd*, nghiepVuDK, viecDangKy, CapBanSao,
  soBanSao, TraKQ, noiDungDK, lyDoDK, loại/số giấy tờ trùng lặp, radio trong/ngoài nước.
  (Nội dung/lý do cải chính TRẢ QUA NoiDungThayDoi/LyDo — KHÔNG trả trực tiếp noiDungDK/lyDoDK.)
- Nếu giấy tờ không ghi quốc tịch thì bỏ qua *_QuocTich; mặc định Việt Nam.
</forbidden_ui_fields>"""

"""Facts nguồn cho thủ tục [Lào Cai] thửa đất có diện tích tăng thêm do thay đổi ranh giới — 1.115693.

Bước 2 "Thông tin người nộp / Thông tin chủ hồ sơ" của `dichvucong.laocai.gov.vn` là eForm iGate
legacy: HTML/jQuery thuần (0 formcontrolname, 0 Form.io), bộ ô `CongDan_*` (người nộp) + `ChuHoSo_*`
(chủ hồ sơ) — CÙNG bộ ô với 1.115650/1.115678/1.115694, nên engine `dom-*` của extension khớp ô theo
thuộc tính `name` và chạy được ngay. Mapping theo
`Mapping_1.115693_Cap_GCN_dien_tich_tang_them_Nguyen_Duy_Tam.xlsx` (34 ô bước 2, dựng từ 2 bản DOM
thật: `ca__nha_n.html` + `to___chu__c.html`).

⚑ HAI MODE NGƯỜI NỘP — mode nào cũng phải ra đúng hồ sơ:
  • Mode A "nộp thay": hồ sơ có GIẤY ỦY QUYỀN công chứng → `NguoiNop_*` là NGƯỜI ĐƯỢC ỦY QUYỀN,
    `ChuHoSo_*` là người sử dụng đất của thửa gốc. Hai khối là hai người KHÁC NHAU.
  • Mode B "tự nộp": không có ủy quyền → `NguoiNop_*` trùng đúng `ChuHoSo_*`.
Mapper tự chốt mode bằng đối chiếu thật (xem `mapper._same_person`), KHÔNG tin một cờ do LLM tự khai.

⚠ HỒ SƠ MẪU CHO THẤY MODE A LÀ MẶC ĐỊNH CỦA THỦ TỤC NÀY: chủ hồ sơ là hộ ông Nguyễn Duy Tâm (thường
trú Bắc Ninh) trong khi thửa đất ở Lào Cai, nên người đi nộp gần như luôn là người được ủy quyền tại
địa phương. Dấu hiệu nhận ra người nộp ở thủ tục này KHÔNG chỉ là Giấy ủy quyền: hồ sơ hay kèm "GIẤY
CAM KẾT XÁC NHẬN CHỮ KÝ" do chính người được ủy quyền lập, ghi rõ số/ngày giấy ủy quyền — đó là nguồn
nhân thân đầy đủ nhất của người nộp khi bản ủy quyền không được scan kèm.

⚑ Trang nhập liệu CHỈ có 2 khối nhân thân, KHÔNG có phần thân đơn (thửa đất, diện tích, GCN đã cấp…).
Các field nghiệp vụ bên dưới vẫn trích để lưu trace cho cán bộ đối chiếu nhưng KHÔNG khai trong
`UI_COMP_BY_NAME` → mapper không phát, tránh bịa ô không tồn tại. Sheet "Cảnh báo trường ẩn" của file
mapping ghi rõ wizard chưa render bước 3 nên chưa bóc được DOM của eForm kê khai thửa đất.
"""

_AREA_DESC = (
    "object {quocGia,tinh,xa,diaChi}; địa giới đã gộp còn 2 cấp (xã/phường → tỉnh), diaChi giữ "
    "nguyên số nhà/đường/tổ dân phố/khu/thôn."
)

FIELDS: list[dict] = [
    # --- CHỦ HỒ SƠ (người sử dụng đất của thửa gốc, đứng tên mục 1.1 của Đơn đăng ký biến động) ---
    {
        "name": "ChuHoSo_HoTen",
        "desc": "Họ tên NGƯỜI SỬ DỤNG ĐẤT đứng tên ĐẦU TIÊN (mục 1.1 'Tên') của ĐƠN ĐĂNG KÝ BIẾN ĐỘNG "
                "đất đai, tài sản gắn liền với đất — cũng là người ghi ở mục 3 'Tên người sử dụng đất' "
                "của Phiếu đo đạc chỉnh lý và mục 'Đại diện chủ sử dụng đất' của Biên bản làm việc. "
                "⚠ Đơn thường liệt kê THÊM nhiều người ĐỒNG SỬ DỤNG ở các mục 1.4/1.7/1.10 — bước 2 "
                "của cổng KHÔNG có ô cho họ, chỉ lấy người ở mục 1.1. TUYỆT ĐỐI không lấy người được "
                "ủy quyền đi nộp, không lấy chủ sử dụng đất GIÁP RANH, không lấy cán bộ ký biên bản, "
                "không lấy công chứng viên, không lấy đơn vị đo đạc.",
    },
    {
        "name": "ChuHoSo_LaToChuc",
        "desc": "true nếu CHỦ HỒ SƠ là TỔ CHỨC/doanh nghiệp (đơn ghi tên pháp nhân, có mã số doanh "
                "nghiệp kèm Giấy chứng nhận đăng ký doanh nghiệp), false nếu là cá nhân/hộ gia đình. "
                "Thủ tục này hầu hết là HỘ GIA ĐÌNH/CÁ NHÂN → false. Không chắc thì bỏ field.",
    },
    {
        "name": "ChuHoSo_TenToChuc",
        "desc": "Tên đầy đủ của TỔ CHỨC đứng đơn, nguyên văn. Hồ sơ hộ gia đình/cá nhân thì BỎ FIELD.",
    },
    {
        "name": "ChuHoSo_MaSoThue",
        "desc": "Mã số thuế / mã số doanh nghiệp của TỔ CHỨC đứng đơn. Hồ sơ CÁ NHÂN/HỘ GIA ĐÌNH thì "
                "BỎ FIELD. ⚠ Số ở mục [05]/[06] 'Mã số thuế' của Tờ khai lệ phí trước bạ, Tờ khai tiền "
                "sử dụng đất và Tờ khai thuế SDĐ phi nông nghiệp là MÃ SỐ THUẾ CÁ NHÂN 10 số của chính "
                "chủ hộ (vd 5200170752) — thấy nó KHÔNG có nghĩa chủ hồ sơ là tổ chức, và với cá nhân "
                "thì ô 'Mã số thuế' trên cổng bị ẩn nên đừng đưa số đó vào đây.",
    },
    {
        "name": "ChuHoSo_NgaySinh",
        "desc": "Ngày sinh đầy đủ của chủ hồ sơ, dd/mm/yyyy. Ưu tiên CCCD đúng người. Giấy tờ chỉ ghi "
                "NĂM sinh thì BỎ FIELD, không tự đặt ngày/tháng. TUYỆT ĐỐI không suy năm sinh từ cấu "
                "trúc số CCCD — đó là suy đoán, không phải dữ liệu trong giấy tờ.",
    },
    {
        "name": "ChuHoSo_GioiTinh",
        "desc": "Giới tính chủ hồ sơ: Nam/Nữ. Chỉ suy từ danh xưng gắn TRỰC TIẾP với chính người đó "
                "('Ông Nguyễn Duy Tâm' = Nam, 'Bà …' = Nữ) hoặc từ CCCD ghi rõ. KHÔNG suy từ tên đệm.",
    },
    {
        "name": "ChuHoSo_DanToc",
        "desc": "Dân tộc của chủ hồ sơ nếu giấy tờ ghi rõ. CCCD gắn chip mẫu 2021 KHÔNG in dân tộc trên "
                "mặt thẻ và hồ sơ đất đai thường không ghi → bỏ field, đừng mặc định 'Kinh'.",
    },
    {
        "name": "ChuHoSo_SoDinhDanh",
        "desc": "Số CCCD/CMND của CHỦ HỒ SƠ, chỉ chữ số. Nguồn: CCCD, mục 1.2 'Giấy tờ nhân thân/pháp "
                "nhân' của Đơn đăng ký biến động. ⚠ Đơn liệt kê CCCD của CẢ những người đồng sử dụng ở "
                "mục 1.5/1.8/1.11 — lấy đúng số đi liền với tên ở mục 1.1. KHÔNG nhầm với mã số thuế, "
                "số phát hành GCN, số vào sổ cấp GCN, số thửa, số tờ bản đồ, số giấy ủy quyền.",
    },
    {
        "name": "ChuHoSo_NgayCap",
        "desc": "Ngày cấp giấy tờ định danh của chủ hồ sơ, dd/mm/yyyy, phải đi cùng ĐÚNG số giấy tờ đó. "
                "KHÔNG lấy ngày cấp Giấy chứng nhận quyền sử dụng đất.",
    },
    {
        "name": "ChuHoSo_NoiCap",
        "desc": "Cơ quan cấp giấy tờ định danh của chủ hồ sơ. 'CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH "
                "CHÍNH VỀ TRẬT TỰ XÃ HỘI' → 'Cục Cảnh sát quản lý hành chính về trật tự xã hội'; thẻ "
                "Căn cước mẫu 2024 ghi 'BỘ CÔNG AN' → 'Bộ Công an'. KHÔNG lấy cơ quan cấp GCN.",
    },
    {
        "name": "ChuHoSo_NoiCuTru",
        "desc": "NƠI THƯỜNG TRÚ của CHỦ HỒ SƠ, " + _AREA_DESC + " Nguồn: CCCD, mục 1.3 'Địa chỉ' của "
                "Đơn đăng ký biến động, mục 4 'Địa chỉ người sử dụng đất' của Phiếu đo đạc chỉnh lý, "
                "mục [07]/[09] của Tờ khai lệ phí trước bạ. ⚠⚠ ĐÂY KHÔNG PHẢI ĐỊA CHỈ THỬA ĐẤT. Thủ tục "
                "này chủ hộ rất hay cư trú ở TỈNH KHÁC với nơi có thửa đất (hồ sơ mẫu: thường trú Bắc "
                "Ninh, thửa đất ở Lào Cai) — lấy nhầm là sai cả 3 ô địa chỉ của khối chủ hồ sơ.",
    },
    {
        "name": "ChuHoSo_DienThoai",
        "desc": "Số điện thoại liên hệ của chủ hồ sơ, chỉ chữ số. Nguồn: mục 1.13 'Điện thoại liên hệ' "
                "của Đơn, mục [10]/[12] của các tờ khai thuế. Các mục này THƯỜNG BỎ TRỐNG → bỏ field.",
    },
    {"name": "ChuHoSo_Email", "desc": "Email của chủ hồ sơ (mục 1.13 'Hộp thư điện tử' của Đơn) nếu giấy tờ ghi rõ."},
    {"name": "ChuHoSo_Fax", "desc": "Số fax của chủ hồ sơ nếu giấy tờ ghi rõ."},

    # --- NGƯỜI NỘP HỒ SƠ (mode A = người được ủy quyền; mode B = trùng chủ hồ sơ) ---
    {
        "name": "NguoiNop_HoTen",
        "desc": "Họ tên NGƯỜI NỘP. CÓ Giấy ủy quyền/Hợp đồng ủy quyền thì BẮT BUỘC lấy NGƯỜI ĐƯỢC ỦY "
                "QUYỀN (bên B — người đứng ngay sau 'ủy quyền cho'). Hồ sơ KHÔNG scan kèm bản ủy quyền "
                "nhưng CÓ 'GIẤY CAM KẾT XÁC NHẬN CHỮ KÝ' thì người lập giấy cam kết đó ('Tôi tên là …', "
                "tự khai 'Tôi là người được ủy quyền theo giấy ủy quyền số …') CHÍNH LÀ người nộp. "
                "KHÔNG có ủy quyền nào thì người nộp chính là chủ hồ sơ, chép lại y hệt ChuHoSo_HoTen.",
    },
    {
        "name": "NguoiNop_NgaySinh",
        "desc": "Ngày sinh đầy đủ của NGƯỜI NỘP, dd/mm/yyyy. ⚠ Giấy cam kết xác nhận chữ ký thường chỉ "
                "ghi NĂM ('Ngày sinh: 1977') → BỎ FIELD, không tự đặt ngày/tháng.",
    },
    {"name": "NguoiNop_GioiTinh", "desc": "Giới tính NGƯỜI NỘP: Nam/Nữ, chỉ suy từ danh xưng gắn trực tiếp với chính người đó hoặc CCCD ghi rõ."},
    {"name": "NguoiNop_DanToc", "desc": "Dân tộc của NGƯỜI NỘP nếu giấy tờ ghi rõ; giấy ủy quyền/giấy cam kết thường không ghi → bỏ field."},
    {
        "name": "NguoiNop_SoDinhDanh",
        "desc": "Số CCCD/CMND của NGƯỜI NỘP, chỉ chữ số. Nguồn: CCCD của chính người đó, mục 'Số "
                "CCCD/CMND' của Giấy cam kết xác nhận chữ ký, phần nhân thân bên B của Giấy ủy quyền. "
                "Chép ĐÚNG số in trên giấy kể cả khi số đó trông sai định dạng — hệ thống có bước kiểm "
                "tra riêng, đừng tự cắt bớt hay sửa chữ số.",
    },
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp giấy tờ định danh của NGƯỜI NỘP, dd/mm/yyyy, đi cùng đúng số giấy tờ của chính người đó."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp giấy tờ định danh của NGƯỜI NỘP, lấy cùng giấy tờ với số và ngày cấp."},
    {
        "name": "NguoiNop_NoiCuTru",
        "desc": "NƠI THƯỜNG TRÚ của NGƯỜI NỘP, " + _AREA_DESC + " Có ủy quyền thì lấy 'Địa chỉ thường "
                "trú' của chính người được ủy quyền (Giấy cam kết xác nhận chữ ký ghi rõ mục này); "
                "không có ủy quyền thì sao chép NGUYÊN VẸN ChuHoSo_NoiCuTru. ⚠ Không lấy địa chỉ thửa "
                "đất, không lấy địa chỉ Văn phòng công chứng nơi lập giấy ủy quyền.",
    },
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại của NGƯỜI NỘP, chỉ chữ số. Giấy cam kết có nhãn 'Số điện thoại' nhưng hay bỏ trống → khi đó BỎ FIELD, tuyệt đối không mượn số của chủ hồ sơ."},
    {"name": "NguoiNop_Email", "desc": "Email của NGƯỜI NỘP nếu có."},
    {"name": "NguoiNop_Fax", "desc": "Số fax của NGƯỜI NỘP nếu có."},

    # --- Nghiệp vụ: chỉ lưu vết cho cán bộ đối chiếu, bước 2 KHÔNG có ô để điền ---
    {
        "name": "Don_NoiDungBienDong",
        "desc": "Nội dung biến động người dân khai ở mục 2 của Đơn đăng ký biến động (vd 'Cấp đổi giấy "
                "chứng nhận do tăng diện tích'). Chép NGUYÊN VĂN phần người dân khai; KHÔNG lấy tiêu đề "
                "thủ tục in sẵn trên cổng.",
    },
    {
        "name": "ThuaDat_DiaChi",
        "desc": "ĐỊA CHỈ THỬA ĐẤT (KHÔNG phải nơi cư trú), " + _AREA_DESC + " Nguồn: mục 2 'Địa chỉ "
                "thửa đất' của Phiếu đo đạc chỉnh lý, mục 3.1 của Tờ khai tiền sử dụng đất, phần mở "
                "đầu Bản mô tả ranh giới. Không có nguồn ghi rõ thì bỏ field.",
    },
    {"name": "ThuaDat_SoThua", "desc": "Số thửa đất (vd '55'), lấy ở mục 1 Phiếu đo đạc chỉnh lý hoặc Biên bản làm việc."},
    {
        "name": "ThuaDat_SoToBanDo",
        "desc": "Số tờ bản đồ của thửa đất. ⚠ Hồ sơ dạng này hay có HAI số: tờ bản đồ CŨ (theo bản đồ "
                "địa chính lập trước đây) và tờ bản đồ MỚI sau đo đạc lại — lấy số theo PHIẾU ĐO ĐẠC "
                "CHỈNH LÝ MỚI NHẤT, và đừng ghép hai số vào một field.",
    },
    {
        "name": "ThuaDat_DienTichTheoGcn",
        "desc": "Diện tích thửa đất GHI TRÊN GIẤY CHỨNG NHẬN ĐÃ CẤP, m² (vd '360,0'). Nguồn: mục 5 "
                "'Diện tích trên giấy tờ' của Phiếu đo đạc chỉnh lý, bảng thông tin thửa đất của Biên "
                "bản làm việc. Giữ nguyên dấu phẩy thập phân.",
    },
    {
        "name": "ThuaDat_DienTichSauDoDac",
        "desc": "Diện tích thửa đất SAU ĐO ĐẠC CHỈNH LÝ, m² (vd '370,0'). Nguồn: mục 1 và mục 7 của "
                "Phiếu đo đạc chỉnh lý, phần 'Thống nhất buổi làm việc' của Biên bản làm việc.",
    },
    {
        "name": "DienTich_TangThem",
        "desc": "Phần diện tích TĂNG THÊM, m² (vd '10,0'). CHỈ điền khi giấy tờ ghi SẴN con số đó (Biên "
                "bản làm việc thường ghi 'tăng 10,0 m² đất ở tại đô thị so với giấy chứng nhận đã cấp'). "
                "TUYỆT ĐỐI KHÔNG tự lấy diện tích sau đo đạc trừ diện tích theo GCN để suy ra.",
    },
    {"name": "ThuaDat_LoaiDat", "desc": "Loại đất/mục đích sử dụng của thửa đất (vd 'ODT' hoặc 'Đất ở tại đô thị'), lấy ở Phiếu đo đạc chỉnh lý. Không có thì bỏ field."},
    {
        "name": "Gcn_SoPhatHanh",
        "desc": "SỐ PHÁT HÀNH của Giấy chứng nhận ĐÃ CẤP cho thửa gốc (1–2 chữ cái + số, vd 'AI 681070'), "
                "lấy ở mục 3(1) của Đơn đăng ký biến động hoặc phần 'Hồ sơ pháp lý thửa đất' của Biên "
                "bản làm việc. KHÔNG ghép chung với số vào sổ.",
    },
    {"name": "Gcn_SoVaoSo", "desc": "SỐ VÀO SỔ cấp Giấy chứng nhận đã cấp (vd 'H 01486'), trả riêng, không gộp với Gcn_SoPhatHanh."},
    {"name": "Gcn_NgayCap", "desc": "Ngày cấp Giấy chứng nhận đã cấp, dd/mm/yyyy. KHÔNG lấy ngày lập phiếu đo đạc, ngày họp biên bản làm việc hay ngày ký đơn."},
    {"name": "Gcn_DonViCap", "desc": "Cơ quan ký cấp Giấy chứng nhận đã cấp (vd 'UBND thị xã Nghĩa Lộ'). 'TM. ỦY BAN NHÂN DÂN …' → 'UBND …'."},
    {
        "name": "UyQuyen_SoGiay",
        "desc": "Số của Giấy ủy quyền/Hợp đồng ủy quyền (vd '0055'), kèm nơi công chứng nếu giấy ghi. "
                "Nguồn: chính bản ủy quyền, hoặc phần tự khai của Giấy cam kết xác nhận chữ ký. Hồ sơ "
                "KHÔNG có ủy quyền thì BỎ FIELD — đây cũng là dấu hiệu hồ sơ thuộc mode 'tự nộp'.",
    },
    {"name": "UyQuyen_NgayLap", "desc": "Ngày lập Giấy ủy quyền, dd/mm/yyyy, lấy cùng giấy với UyQuyen_SoGiay."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for name in (
    "ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap",
    "Gcn_NgayCap", "UyQuyen_NgayLap",
):
    COMPACT_COMP_BY_NAME[name] = "x-date"
for name in ("ChuHoSo_NoiCuTru", "NguoiNop_NoiCuTru", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[name] = "x-select-area"

# CHỈ các ô CÓ THẬT trên bước 2 của cổng, theo thứ tự DOM trong sheet "Mapping - Bước 2" của
# `Mapping_1.115693_Cap_GCN_dien_tich_tang_them_Nguyen_Duy_Tam.xlsx`.
#
# Cố ý KHÔNG khai 4 nhóm sau (sheet "Cảnh báo trường ẩn" của chính file mapping):
#  • `chkbox_nguoinoplachuhs` — checkbox "Người nộp là chủ hồ sơ". Cổng chỉ copy sang khối chủ hồ sơ
#    tới Nơi cấp/Ngày cấp căn cước, KHÔNG copy Tỉnh/Phường-Xã/Địa chỉ; đổi trạng thái checkbox còn có
#    thể làm cổng xoá dữ liệu đã điền. Mapper phát thẳng ĐỦ khối chủ hồ sơ thay vì trông vào nó.
#  • `CongDan_maDMDiaChi` — input display:none trong div#column-24, label rỗng, file mapping ghi rõ
#    "không xác định được nhãn từ HTML tĩnh – không suy đoán".
#  • `code-dkdn` — ô tra cứu doanh nghiệp, div#form-search-dn display:none ở CẢ hai bản DOM.
#  • `local_file`, `local_file_xuly`, `AN_FORM_CHS`, `tokenCsrf` — hidden do hệ thống tự sinh.
#  • ⚠ `CongDan_tenCongDan` và `CongDan_soCmnd` — HAI Ô KHÔNG BAO GIỜ ĐƯỢC PHÁT. Chúng readonly, cổng
#    tự đổ từ tài khoản định danh đang đăng nhập; script của cổng còn XOÁ TRẮNG "Di động" + "Số Căn
#    cước" ngay khi họ tên bị sửa khác tài khoản — tức là điền vào đây làm HỎNG chính ô bắt buộc
#    "Di động" vừa điền xong. Hành vi này đã xác minh trên cùng họ biểu mẫu Lào Cai
#    (1.115667/1.115668/1.115677/1.115678/1.115694).
#    Bù lại, đúng hai ô đó là MỐC DUY NHẤT để biết AI đang đi nộp: extension đọc chúng rồi gửi lên
#    trong `options.formContext` (xem mapper).
UI_COMP_BY_NAME = {
    # Khối NGƯỜI NỘP
    "CongDan_tenCoQuanToChuc": "dom-input",
    "CongDan_maSoThueNguoiNop": "dom-input",
    "CongDan_ngaySinhCongDan": "dom-input",
    "CongDan_gioiTinhCongDan": "dom-select",   # option Nữ(0)/Nam(1), không có "-- Chưa chọn --".
    "CongDan_danTocCongDan": "dom-select",
    "CongDan_ngayCapCmnd": "dom-input",
    "CongDan_noiCapCmnd": "dom-input",
    "CongDan_maTinhThanh": "dom-select",       # Tỉnh/Thành phố (cascade 2 cấp, không có huyện).
    "CongDan_maPhuongXa": "dom-select",        # Phường/Xã (nạp lại sau khi chọn tỉnh).
    "CongDan_diaChi": "dom-input",
    "CongDan_diDong": "dom-input",
    "CongDan_email": "dom-input",
    "CongDan_fax": "dom-input",
    # Khối CHỦ HỒ SƠ
    "ChuHoSo_maDoiTuongNopHS": "dom-select",
    "ChuHoSo_tenChuHoSo": "dom-input",
    "ChuHoSo_tenCoQuanToChucCHS": "dom-input",
    "ChuHoSo_maSoThueChuHoSo": "dom-input",
    "ChuHoSo_ngaySinhChuHoSo": "dom-input",
    "ChuHoSo_gioiTinhChuHoSo": "dom-select",
    "ChuHoSo_danTocChuHoSo": "dom-select",
    "ChuHoSo_soCMNDChuHoSo": "dom-input",
    "ChuHoSo_noiCapCMNDCHS": "dom-input",      # Trên form: Nơi cấp đứng TRƯỚC Ngày cấp (ngược khối I).
    "ChuHoSo_ngayCapCMNDCHS": "dom-input",
    "ChuHoSo_maTinhThanhCHS": "dom-select",
    "ChuHoSo_maPhuongXaCHS": "dom-select",
    "ChuHoSo_diaChiChuHoSo": "dom-input",
    "ChuHoSo_diDongLienLacCHS": "dom-input",
    "ChuHoSo_emailChuHoSo": "dom-input",
    "ChuHoSo_faxChuHoSo": "dom-input",
}

# Hai ô này chỉ HIỆN khi "Đối tượng nộp hồ sơ" = Doanh nghiệp/Tổ chức (sheet "Cảnh báo trường ẩn",
# mục 3: div#tenCoQuanToChucCHS + div#maSoThueChuHoSo display:none ở bản Cá nhân). Hồ sơ cá nhân mà
# vẫn phát thì engine báo "không điền được" một cách vô cớ.
ORG_ONLY_FIELDS = frozenset({"ChuHoSo_tenCoQuanToChucCHS", "ChuHoSo_maSoThueChuHoSo"})

# Ngược lại, 7 ô nhân thân cá nhân của khối chủ hồ sơ bị display:none khi chọn Tổ chức (mục 4).
INDIVIDUAL_ONLY_FIELDS = frozenset({
    "ChuHoSo_tenChuHoSo",
    "ChuHoSo_ngaySinhChuHoSo",
    "ChuHoSo_gioiTinhChuHoSo",
    "ChuHoSo_danTocChuHoSo",
    "ChuHoSo_soCMNDChuHoSo",
    "ChuHoSo_noiCapCMNDCHS",
    "ChuHoSo_ngayCapCMNDCHS",
})

UI_ALIASES: dict[str, list[str]] = {}

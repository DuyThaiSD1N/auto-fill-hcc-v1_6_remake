"""Facts nguồn cho thủ tục [Lào Cai] xác định lại diện tích đất ở — 1.115685.

Bước "Thông tin người nộp / Thông tin chủ hồ sơ" của `dichvucong.laocai.gov.vn` là eForm iGate
legacy: form builder jQuery/Bootstrap thuần (0 formcontrolname, 0 Form.io), bộ ô `CongDan_*` (người
nộp) + `ChuHoSo_*` (chủ hồ sơ) — CÙNG bộ ô với 1.115650/1.115678/1.115693/1.115694, nên engine
`dom-*` của extension khớp ô theo thuộc tính `name` và chạy được ngay. Mapping theo
`mapping_xac_dinh_lai_dien_tich_dat_o_1.115685.xlsx` (34 ô bước 2, dựng từ 2 bản DOM thật: bản Cá
nhân + bản Tổ chức; hai file HTML giống hệt nhau, chỉ khác trạng thái hiện/ẩn khối Chủ hồ sơ).

⚑ HAI MODE NGƯỜI NỘP — mode nào cũng phải ra đúng hồ sơ:
  • Mode A "nộp thay": hồ sơ có VĂN BẢN VỀ VIỆC ĐẠI DIỆN (giấy/hợp đồng ủy quyền) → `NguoiNop_*` là
    NGƯỜI ĐƯỢC ỦY QUYỀN, `ChuHoSo_*` là người sử dụng đất đứng tên mục 1 của Đơn. Hai người KHÁC nhau.
  • Mode B "tự nộp": không có văn bản đại diện → `NguoiNop_*` trùng đúng `ChuHoSo_*`.
Mapper tự chốt mode bằng đối chiếu thật (xem `mapper._same_person`), KHÔNG tin một cờ do LLM tự khai.

⚠ KHÁC 1.115693: ở thủ tục này MODE B LÀ MẶC ĐỊNH. Người xin xác định lại diện tích đất ở là người
đang ở trên chính thửa đất đó, thường trú cùng xã/phường với thửa — hồ sơ mẫu (ông Mai Xuân Hải, tổ
dân phố Sa Pa 4, phường Sa Pa) tự đứng đơn, ảnh ánh xạ đính kèm ghi rõ "Không tick; ông Mai Xuân Hải
tự đứng đơn, không qua người đại diện". Vì vậy nơi cư trú TRÙNG địa chỉ thửa đất ở đây là BÌNH
THƯỜNG, không phải dấu hiệu lấy nhầm (ngược hẳn với 1.115693 — đừng bê cảnh báo của thủ tục đó sang).

⚑ Trang nhập liệu CHỈ có 2 khối nhân thân, KHÔNG có phần thân đơn (thửa đất, diện tích, GCN đã cấp,
"Kính gửi", "Nội dung biến động"…). Sheet "Cảnh báo trường ẩn" mục 8 của file mapping ghi rõ: các mục
đó có trên Đơn giấy nhưng KHÔNG có field tương ứng ở bước 2 lẫn bước Thành phần hồ sơ. Các field
nghiệp vụ bên dưới vẫn trích để lưu trace cho cán bộ đối chiếu nhưng KHÔNG khai trong
`UI_COMP_BY_NAME` → mapper không phát, tránh bịa ô không tồn tại.
"""

_AREA_DESC = (
    "object {quocGia,tinh,xa,diaChi}; địa giới đã gộp còn 2 cấp (xã/phường → tỉnh), diaChi giữ "
    "nguyên số nhà/đường/tổ dân phố/khu/thôn."
)

FIELDS: list[dict] = [
    # --- CHỦ HỒ SƠ (người sử dụng đất, đứng tên mục 1.a của Đơn đăng ký biến động) ---
    {
        "name": "ChuHoSo_HoTen",
        "desc": "Họ tên NGƯỜI SỬ DỤNG ĐẤT đứng tên ở mục 1.a) 'Tên' của ĐƠN ĐĂNG KÝ BIẾN ĐỘNG đất "
                "đai, tài sản gắn liền với đất — cũng là người ký ở dòng 'Người viết đơn' cuối đơn, "
                "và là người được ghi ở mục 'CHỨNG NHẬN' / 'Những thay đổi sau khi cấp Giấy chứng "
                "nhận' của Giấy chứng nhận đã cấp. Bỏ chữ 'Hộ ông'/'Hộ bà' nếu có. TUYỆT ĐỐI không "
                "lấy người được ủy quyền đi nộp, không lấy người ký thay, không lấy cán bộ địa "
                "chính, không lấy thẩm phán/thư ký toà ghi trên bản án, không lấy công chứng viên.",
    },
    {
        "name": "ChuHoSo_LaToChuc",
        "desc": "true nếu CHỦ HỒ SƠ là TỔ CHỨC/doanh nghiệp (đơn ghi tên pháp nhân kèm mã số doanh "
                "nghiệp), false nếu là cá nhân/hộ gia đình. ⚠ Thủ tục này theo quy định CHỈ dành cho "
                "HỘ GIA ĐÌNH, CÁ NHÂN (tên thủ tục ghi rõ) → gần như luôn false. Không chắc thì bỏ "
                "field.",
    },
    {
        "name": "ChuHoSo_TenToChuc",
        "desc": "Tên đầy đủ của TỔ CHỨC đứng đơn, nguyên văn. Hồ sơ hộ gia đình/cá nhân thì BỎ FIELD.",
    },
    {
        "name": "ChuHoSo_MaSoThue",
        "desc": "Mã số thuế / mã số doanh nghiệp của TỔ CHỨC đứng đơn. Hồ sơ CÁ NHÂN/HỘ GIA ĐÌNH thì "
                "BỎ FIELD — với cá nhân ô 'Mã số thuế' trên cổng bị ẩn. Mã số thuế cá nhân 10 số ghi "
                "trên tờ khai lệ phí trước bạ KHÔNG đưa vào đây.",
    },
    {
        "name": "ChuHoSo_NgaySinh",
        "desc": "Ngày sinh đầy đủ của chủ hồ sơ, dd/mm/yyyy. Nguồn: CCCD, hoặc phần ghi kèm 'sinh "
                "ngày …' ngay sau tên ở mục 1.a) của Đơn (vd 'MAI XUÂN HẢI – sinh ngày 10/9/1975'). "
                "Giấy tờ chỉ ghi NĂM sinh thì BỎ FIELD, không tự đặt ngày/tháng. TUYỆT ĐỐI không suy "
                "năm sinh từ cấu trúc số định danh — đó là suy đoán, không phải dữ liệu trong giấy.",
    },
    {
        "name": "ChuHoSo_GioiTinh",
        "desc": "Giới tính chủ hồ sơ: Nam/Nữ. Chỉ suy từ danh xưng gắn TRỰC TIẾP với chính người đó "
                "('ông Mai Xuân Hải' = Nam, 'bà …' = Nữ) hoặc từ CCCD ghi rõ. KHÔNG suy từ tên đệm, "
                "KHÔNG suy từ chữ số thứ 4 của số định danh.",
    },
    {
        "name": "ChuHoSo_DanToc",
        "desc": "Dân tộc của chủ hồ sơ nếu giấy tờ ghi rõ. CCCD gắn chip mẫu 2021 KHÔNG in dân tộc "
                "trên mặt thẻ, còn Đơn đăng ký biến động lẫn Giấy chứng nhận đều không có mục dân "
                "tộc → thường phải bỏ field, đừng mặc định 'Kinh'.",
    },
    {
        "name": "ChuHoSo_SoDinhDanh",
        "desc": "Số CCCD/CMND của CHỦ HỒ SƠ, chỉ chữ số. Nguồn: CCCD, mục 1.b) 'Giấy tờ nhân thân/"
                "pháp nhân' của Đơn. ⚠ Giấy chứng nhận cấp trước 01/7/2004 (và các trang 'Những thay "
                "đổi sau khi cấp GCN') thường ghi SỐ CMND CŨ 9 SỐ khác hẳn số CCCD 12 số hiện tại — "
                "lấy số trên CCCD/Đơn, số CMND cũ chỉ để đối chiếu. KHÔNG nhầm với mã số thuế, số "
                "phát hành GCN, số vào sổ cấp GCN, số thửa, số tờ bản đồ, số bản án.",
    },
    {
        "name": "ChuHoSo_NgayCap",
        "desc": "Ngày cấp giấy tờ định danh của chủ hồ sơ, dd/mm/yyyy, phải đi cùng ĐÚNG số giấy tờ "
                "đó (mục 1.b) của Đơn ghi 'cấp ngày …'). KHÔNG lấy ngày cấp Giấy chứng nhận quyền sử "
                "dụng đất, KHÔNG lấy ngày ký đơn.",
    },
    {
        "name": "ChuHoSo_NoiCap",
        "desc": "Cơ quan cấp giấy tờ định danh của chủ hồ sơ (mục 1.b) của Đơn ghi 'do … cấp'). Viết "
                "tắt 'cục CSQLHCTTXH' → 'Cục Cảnh sát quản lý hành chính về trật tự xã hội'; thẻ Căn "
                "cước mẫu 2024 ghi 'BỘ CÔNG AN' → 'Bộ Công an'. KHÔNG lấy cơ quan cấp GCN (UBND "
                "huyện/tỉnh), KHÔNG lấy tên toà án.",
    },
    {
        "name": "ChuHoSo_NoiCuTru",
        "desc": "NƠI THƯỜNG TRÚ của CHỦ HỒ SƠ, " + _AREA_DESC + " Nguồn: CCCD, mục 1.c) 'Địa chỉ' "
                "của Đơn. ⚠ Giấy chứng nhận cấp trước 01/7/2004 ghi địa chỉ theo ĐƠN VỊ HÀNH CHÍNH "
                "CŨ (vd 'tổ 4A, thị trấn Sa Pa, huyện Sa Pa') — lấy theo Đơn/CCCD hiện tại, địa chỉ "
                "trên GCN chỉ để đối chiếu.",
    },
    {
        "name": "ChuHoSo_DienThoai",
        "desc": "Số điện thoại liên hệ của chủ hồ sơ, chỉ chữ số, lấy ở mục 1.d) 'Điện thoại liên hệ "
                "(nếu có)' của Đơn. Mục này hay bỏ trống → khi đó bỏ field.",
    },
    {
        "name": "ChuHoSo_Email",
        "desc": "Email của chủ hồ sơ (mục 1.d) 'Hộp thư điện tử (nếu có)' của Đơn) nếu giấy tờ ghi rõ.",
    },
    {
        "name": "ChuHoSo_Fax",
        "desc": "Số fax của chủ hồ sơ nếu giấy tờ ghi rõ. Đơn đăng ký biến động, CCCD và Giấy chứng "
                "nhận đều không có mục này → thường bỏ field.",
    },

    # --- NGƯỜI NỘP HỒ SƠ (mode A = người được ủy quyền; mode B = trùng chủ hồ sơ) ---
    {
        "name": "NguoiNop_HoTen",
        "desc": "Họ tên NGƯỜI NỘP. CÓ 'VĂN BẢN VỀ VIỆC ĐẠI DIỆN' / Giấy ủy quyền / Hợp đồng ủy quyền "
                "thì BẮT BUỘC lấy NGƯỜI ĐƯỢC ỦY QUYỀN (bên B — người đứng ngay sau cụm 'ủy quyền "
                "cho'). KHÔNG có văn bản đại diện nào thì người nộp chính là chủ hồ sơ, chép lại y "
                "hệt ChuHoSo_HoTen. ⚠ Mục 3 của Đơn chỉ LIỆT KÊ tên giấy tờ nộp kèm — thấy chữ 'văn "
                "bản đại diện' ở đó KHÔNG đủ để trích ra người nộp.",
    },
    {
        "name": "NguoiNop_NgaySinh",
        "desc": "Ngày sinh đầy đủ của NGƯỜI NỘP, dd/mm/yyyy. Chỉ có NĂM thì BỎ FIELD, không bịa 01/01.",
    },
    {
        "name": "NguoiNop_GioiTinh",
        "desc": "Giới tính NGƯỜI NỘP: Nam/Nữ, chỉ suy từ danh xưng gắn trực tiếp với chính người đó "
                "hoặc từ CCCD ghi rõ.",
    },
    {
        "name": "NguoiNop_DanToc",
        "desc": "Dân tộc của NGƯỜI NỘP nếu giấy tờ ghi rõ; văn bản đại diện thường không ghi → bỏ field.",
    },
    {
        "name": "NguoiNop_SoDinhDanh",
        "desc": "Số CCCD/CMND của NGƯỜI NỘP, chỉ chữ số. Nguồn: CCCD của chính người đó, phần nhân "
                "thân bên được ủy quyền của văn bản đại diện. Chép ĐÚNG số in trên giấy kể cả khi số "
                "đó trông sai định dạng — hệ thống có bước kiểm tra riêng, đừng tự cắt bớt chữ số.",
    },
    {
        "name": "NguoiNop_NgayCap",
        "desc": "Ngày cấp giấy tờ định danh của NGƯỜI NỘP, dd/mm/yyyy, đi cùng đúng số giấy tờ của "
                "chính người đó.",
    },
    {
        "name": "NguoiNop_NoiCap",
        "desc": "Cơ quan cấp giấy tờ định danh của NGƯỜI NỘP, lấy cùng giấy tờ với số và ngày cấp.",
    },
    {
        "name": "NguoiNop_NoiCuTru",
        "desc": "NƠI THƯỜNG TRÚ của NGƯỜI NỘP, " + _AREA_DESC + " Có ủy quyền thì lấy nơi thường trú "
                "của chính người được ủy quyền ghi trong văn bản đại diện; không có ủy quyền thì sao "
                "chép NGUYÊN VẸN ChuHoSo_NoiCuTru. ⚠ Không lấy địa chỉ Văn phòng công chứng, không "
                "lấy địa chỉ UBND phường/xã nơi nộp hồ sơ.",
    },
    {
        "name": "NguoiNop_DienThoai",
        "desc": "Số điện thoại của NGƯỜI NỘP, chỉ chữ số. Văn bản đại diện thường không ghi → khi đó "
                "BỎ FIELD, tuyệt đối không mượn số của chủ hồ sơ.",
    },
    {"name": "NguoiNop_Email", "desc": "Email của NGƯỜI NỘP nếu có."},
    {"name": "NguoiNop_Fax", "desc": "Số fax của NGƯỜI NỘP nếu có."},

    # --- Nghiệp vụ: chỉ lưu vết cho cán bộ đối chiếu, bước 2 KHÔNG có ô để điền ---
    {
        "name": "Don_KinhGui",
        "desc": "Cơ quan ghi ở dòng 'Kính gửi' của Đơn đăng ký biến động (vd 'Ủy ban nhân dân phường "
                "Sa Pa'). Chép nguyên văn phần người dân ghi, không thêm bớt.",
    },
    {
        "name": "Don_NoiDungBienDong",
        "desc": "Nội dung biến động người dân khai ở mục 2 của Đơn đăng ký biến động — với thủ tục "
                "này thường là 'Xác định lại diện tích đất ở của hộ gia đình, cá nhân đã được cấp "
                "Giấy chứng nhận trước ngày 01 tháng 7 năm 2004'. Chép NGUYÊN VĂN phần người dân "
                "khai; KHÔNG lấy tiêu đề thủ tục in sẵn trên cổng, KHÔNG chép luôn cả mục 3.",
    },
    {
        "name": "Don_MauSo",
        "desc": "Số hiệu mẫu đơn in ở đầu trang Đơn (vd 'Mẫu số 18', 'Mẫu số 24'). Chép đúng chữ in "
                "trên giấy — cổng đang treo mẫu tải về là Mẫu số 24 (Quyết định 47/2026/QĐ-UBND) nên "
                "hồ sơ dùng mẫu khác cần cán bộ soát lại; đây là field để PHÁT HIỆN việc đó, không "
                "phải để 'sửa cho khớp'.",
    },
    {
        "name": "Don_NgayKy",
        "desc": "Ngày ký đơn ghi ở dòng '…, ngày … tháng … năm …' phía trên chữ ký người viết đơn, "
                "dd/mm/yyyy. KHÔNG lấy ngày cấp Giấy chứng nhận, KHÔNG lấy ngày cấp CCCD.",
    },
    {
        "name": "ThuaDat_DiaChi",
        "desc": "ĐỊA CHỈ THỬA ĐẤT, " + _AREA_DESC + " Nguồn: mục 'Thửa đất' / 'Địa chỉ' của Giấy "
                "chứng nhận đã cấp. ⚠ Ở thủ tục này địa chỉ thửa đất RẤT HAY TRÙNG nơi thường trú "
                "của chủ hồ sơ (người dân ở trên chính thửa đất đó) — trùng là bình thường, nhưng "
                "vẫn phải đọc từ đúng mục, đừng chép ngược. Không có nguồn ghi rõ thì bỏ field.",
    },
    {
        "name": "ThuaDat_SoThua",
        "desc": "Số thửa đất ghi trên Giấy chứng nhận đã cấp (vd '55'). Không có thì bỏ field.",
    },
    {
        "name": "ThuaDat_SoToBanDo",
        "desc": "Số tờ bản đồ của thửa đất ghi trên Giấy chứng nhận đã cấp. Trả riêng, không ghép "
                "với số thửa.",
    },
    {
        "name": "ThuaDat_DienTichTheoGcn",
        "desc": "TỔNG diện tích thửa đất ghi trên Giấy chứng nhận đã cấp, m² (vd '360,0'). Giữ "
                "nguyên dấu phẩy thập phân. ⚠ Đây là tổng cả thửa, KHÔNG phải riêng phần đất ở.",
    },
    {
        "name": "ThuaDat_DienTichDatOTheoGcn",
        "desc": "Phần diện tích ĐẤT Ở ghi trên Giấy chứng nhận đã cấp, m², khi giấy có tách riêng "
                "(GCN cấp trước 01/7/2004 hay ghi gộp kiểu 'đất ở 200 m², đất vườn 160 m²' trong "
                "cùng một thửa). Giấy KHÔNG tách riêng thì BỎ FIELD — chính vì không tách được nên "
                "người dân mới phải làm thủ tục này. TUYỆT ĐỐI không tự suy ra con số.",
    },
    {
        "name": "ThuaDat_DienTichDatODeNghi",
        "desc": "Diện tích đất ở người dân ĐỀ NGHỊ được xác định lại, m², CHỈ khi Đơn hoặc giấy tờ "
                "kèm theo ghi SẴN con số đó. Người dân thường chỉ nêu yêu cầu chung chung không kèm "
                "số → bỏ field. TUYỆT ĐỐI không tự tính từ hạn mức đất ở của địa phương.",
    },
    {
        "name": "ThuaDat_LoaiDat",
        "desc": "Loại đất / mục đích sử dụng ghi trên Giấy chứng nhận đã cấp (vd 'Đất ở tại đô thị', "
                "'ODT', 'đất ở + đất vườn'). Không có thì bỏ field.",
    },
    {
        "name": "Gcn_SoPhatHanh",
        "desc": "SỐ PHÁT HÀNH của Giấy chứng nhận ĐÃ CẤP (1–2 chữ cái + số, vd 'A 131603'), lấy trên "
                "chính Giấy chứng nhận hoặc mục 3.(1) 'Giấy chứng nhận đã cấp' của Đơn. KHÔNG ghép "
                "chung với số vào sổ.",
    },
    {
        "name": "Gcn_SoVaoSo",
        "desc": "SỐ VÀO SỔ cấp Giấy chứng nhận đã cấp (vd '00003 QSDĐ'), trả riêng, không gộp với "
                "Gcn_SoPhatHanh.",
    },
    {
        "name": "Gcn_NgayCap",
        "desc": "Ngày cấp Giấy chứng nhận đã cấp, dd/mm/yyyy. ⚠ Thủ tục này chỉ áp dụng cho giấy cấp "
                "TRƯỚC 01/7/2004 — ngày đọc được sau mốc đó là dấu hiệu nhầm giấy (có thể đang đọc "
                "ngày ở trang 'Những thay đổi sau khi cấp Giấy chứng nhận'). Chép đúng ngày ở mục "
                "cấp giấy gốc; KHÔNG lấy ngày đăng ký biến động về sau, KHÔNG lấy ngày ký đơn.",
    },
    {
        "name": "Gcn_DonViCap",
        "desc": "Cơ quan ký cấp Giấy chứng nhận đã cấp (vd 'UBND huyện Sa Pa'). 'TM. ỦY BAN NHÂN "
                "DÂN …' → 'UBND …'.",
    },
    {
        "name": "BanAn_SoHieu",
        "desc": "Số hiệu bản án / quyết định của Toà án nếu hồ sơ có kèm (vd '36/2024/HC-ST'). Một "
                "số hồ sơ thủ tục này phát sinh sau khi toà tuyên về ranh giới hoặc loại đất của "
                "thửa. Hồ sơ không có thì bỏ field.",
    },
    {
        "name": "BanAn_NgayTuyen",
        "desc": "Ngày tuyên bản án / quyết định của Toà án, dd/mm/yyyy, lấy cùng giấy với BanAn_SoHieu.",
    },
    {
        "name": "BanAn_ToaAn",
        "desc": "Tên Toà án đã tuyên bản án/quyết định nêu trên (vd 'Toà án nhân dân tỉnh Lào Cai').",
    },
    {
        "name": "UyQuyen_SoGiay",
        "desc": "Số của Văn bản về việc đại diện / Giấy ủy quyền / Hợp đồng ủy quyền, kèm nơi công "
                "chứng nếu giấy ghi. Hồ sơ KHÔNG có ủy quyền thì BỎ FIELD — đây cũng là dấu hiệu hồ "
                "sơ thuộc mode 'tự nộp'.",
    },
    {
        "name": "UyQuyen_NgayLap",
        "desc": "Ngày lập Văn bản về việc đại diện / Giấy ủy quyền, dd/mm/yyyy, lấy cùng giấy với "
                "UyQuyen_SoGiay.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for name in (
    "ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap",
    "Gcn_NgayCap", "UyQuyen_NgayLap", "Don_NgayKy", "BanAn_NgayTuyen",
):
    COMPACT_COMP_BY_NAME[name] = "x-date"
for name in ("ChuHoSo_NoiCuTru", "NguoiNop_NoiCuTru", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[name] = "x-select-area"

# CHỈ các ô CÓ THẬT trên bước 2 của cổng, theo thứ tự DOM trong sheet "Mapping XĐ lại DT đất ở" của
# `mapping_xac_dinh_lai_dien_tich_dat_o_1.115685.xlsx` (34 dòng, bỏ các nhóm nêu dưới đây).
#
# Cố ý KHÔNG khai (sheet "Cảnh báo trường ẩn" của chính file mapping):
#  • `chkbox_nguoinoplachuhs` (STT 18) — checkbox "Người nộp là chủ hồ sơ". Cổng chỉ copy sang khối
#    chủ hồ sơ tới Nơi cấp/Ngày cấp căn cước, KHÔNG copy Tỉnh/Phường-Xã/Địa chỉ; đổi trạng thái
#    checkbox còn có thể làm cổng xoá dữ liệu đã điền. Mapper phát thẳng ĐỦ khối chủ hồ sơ.
#  • `CongDan_maDMDiaChi` (STT 17) — input display:none trong div#column-24, label `_lbl_maDMDiaChi`
#    rỗng; file mapping ghi rõ "không xác định được nhãn từ HTML tĩnh — KHÔNG suy đoán".
#  • `code-dkdn` (STT 1) — ô tra cứu doanh nghiệp, div#form-search-dn display:none ở CẢ hai bản DOM.
#  • `local_file`, `local_file_xuly`, `AN_FORM_CHS`, `tokenCsrf` — hidden do hệ thống tự sinh.
#  • ⚠ `CongDan_tenCongDan` (STT 2) và `CongDan_soCmnd` (STT 8) — HAI Ô KHÔNG BAO GIỜ ĐƯỢC PHÁT.
#    Chúng readonly, cổng tự đổ từ tài khoản định danh đang đăng nhập; script của cổng còn XOÁ TRẮNG
#    "Di động" + "Số Căn cước" ngay khi họ tên bị sửa khác tài khoản — tức là điền vào đây làm HỎNG
#    chính ô bắt buộc "Di động" vừa điền xong. Hành vi này đã xác minh trên cùng họ biểu mẫu Lào Cai
#    (1.115667/1.115668/1.115677/1.115678/1.115693/1.115694).
#    Bù lại, đúng hai ô đó là MỐC DUY NHẤT để biết AI đang đi nộp: extension đọc chúng rồi gửi lên
#    trong `options.formContext` (xem mapper).
UI_COMP_BY_NAME = {
    # Khối NGƯỜI NỘP (tiền tố CongDan_)
    "CongDan_tenCoQuanToChuc": "dom-input",
    "CongDan_maSoThueNguoiNop": "dom-input",
    "CongDan_ngaySinhCongDan": "dom-input",    # datetime-picker, nhận chuỗi dd/mm/yyyy.
    "CongDan_gioiTinhCongDan": "dom-select",   # option Nữ / Nam, không có "-- Chưa chọn --".
    "CongDan_danTocCongDan": "dom-select",     # 500 option (Kinh … Người nước ngoài, Chưa có thông tin).
    "CongDan_ngayCapCmnd": "dom-input",
    "CongDan_noiCapCmnd": "dom-input",
    "CongDan_maTinhThanh": "dom-select",       # Tỉnh/Thành phố — 34 tỉnh sau sắp xếp, cascade 2 cấp.
    "CongDan_maPhuongXa": "dom-select",        # Phường/Xã — danh mục nạp qua API sau khi chọn tỉnh.
    "CongDan_diaChi": "dom-input",
    "CongDan_diDong": "dom-input",
    "CongDan_email": "dom-input",
    "CongDan_fax": "dom-input",
    # Khối CHỦ HỒ SƠ (tiền tố ChuHoSo_)
    "ChuHoSo_maDoiTuongNopHS": "dom-select",   # CN / DN / CQ / TC — quyết định khối dưới hiện ô nào.
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

# Ngược lại, 7 ô nhân thân cá nhân của khối chủ hồ sơ bị display:none khi chọn Tổ chức (mục 4:
# div#column-1, div#row-7, div#column-4).
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

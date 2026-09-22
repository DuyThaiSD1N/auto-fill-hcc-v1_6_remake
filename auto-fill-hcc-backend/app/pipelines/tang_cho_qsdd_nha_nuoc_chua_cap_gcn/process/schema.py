"""Facts nguồn cho thủ tục [Lào Cai] tặng cho quyền sử dụng đất mở rộng đường giao thông — 1.115690.

Bước 2 "Thông tin người nộp / Thông tin chủ hồ sơ" của `dichvucong.laocai.gov.vn` là eForm iGate
legacy: HTML/jQuery thuần (0 formcontrolname, 0 field-key Form.io), bộ ô `CongDan_*` (người nộp) +
`ChuHoSo_*` (chủ hồ sơ) — CÙNG bộ ô với 1.115650/1.115678/1.115693 nên engine `dom-*` của extension
khớp ô theo thuộc tính `name` và chạy được ngay.

Mapping theo `Mapping_tang_cho_quyen_su_dung_dat.xlsx` (38 control mỗi bản DOM, dựng từ 2 bản DOM
thật: "Cá nhân" + "Tổ chức" — hai bản có ĐÚNG cùng 38 định danh).

⚑ BA NGUỒN GIẤY TỜ, BA VAI KHÁC NHAU — đây là chỗ sai nhiều nhất của thủ tục này:
  • CHỦ HỒ SƠ = NGƯỜI TẶNG CHO (hiến đất) = người sử dụng đất đứng tên trên Giấy chứng nhận, cũng là
    người ghi ở dòng "Họ và tên" của Văn bản tặng cho. Hồ sơ mẫu: bà Lương Thị Linh.
  • CHỒNG/VỢ ĐỒNG SỬ DỤNG đứng chung trên Giấy chứng nhận ("Hộ bà …" và "Ông …") KHÔNG phải chủ hồ
    sơ và KHÔNG phải người nộp. Bước 2 chỉ có MỘT khối chủ hồ sơ. Hồ sơ mẫu: ông Nông Văn Tường.
  • NGƯỜI NỘP = NGƯỜI ĐƯỢC UỶ QUYỀN trong Giấy uỷ quyền (mục 1.2 "uỷ quyền cho ông/bà …"), cũng là
    người ký "Người nhận uỷ quyền" ở cuối Văn bản tặng cho. Hồ sơ mẫu: ông Nguyễn Tiến Quân.

⚑ HAI MODE NGƯỜI NỘP — mode nào cũng phải ra đúng hồ sơ:
  • Mode A "nộp thay": hồ sơ CÓ Giấy uỷ quyền → `NguoiNop_*` là người được uỷ quyền, `ChuHoSo_*` là
    người tặng cho. Hai khối là hai người KHÁC NHAU. Hồ sơ mẫu thuộc mode này.
  • Mode B "tự nộp": không có uỷ quyền → `NguoiNop_*` trùng đúng `ChuHoSo_*`.
Mapper tự chốt mode bằng đối chiếu THẬT (xem `mapper._same_person`), KHÔNG tin cờ do LLM tự khai.

⚑ HỒ SƠ THỦ TỤC NÀY GẦN NHƯ LUÔN LÀ CÁ NHÂN/HỘ GIA ĐÌNH hiến đất. Vẫn giữ đủ field tổ chức vì cổng
render cả nhánh "Doanh nghiệp/Tổ chức", nhưng prompt đã dặn KHÔNG bịa tổ chức khi hồ sơ chỉ có cá
nhân. ⚠ "ỦY BAN NHÂN DÂN PHƯỜNG …" ở dòng "Kính gửi" của Văn bản tặng cho là NƠI NHẬN, tuyệt đối
không phải tổ chức chủ hồ sơ.

⚑ Trang nhập liệu CHỈ có 2 khối nhân thân, KHÔNG có phần thân đơn (thửa đất, diện tích hiến, số tờ
bản đồ…). Sheet "Cảnh báo và chú thích" của file mapping ghi rõ: "Chỉ có thông tin người nộp và chủ
hồ sơ; chưa có bước kê khai đất và thành phần đính kèm — không tạo field nghiệp vụ đất giả trong hai
sheet form; lưu đủ dữ liệu hồ sơ để dùng cho bước kế tiếp." Vì vậy các field nghiệp vụ bên dưới VẪN
trích để lưu trace cho cán bộ đối chiếu nhưng KHÔNG khai trong `UI_COMP_BY_NAME` → mapper không phát.
"""

_AREA_DESC = (
    "object {quocGia,tinh,xa,diaChi}; địa giới đã gộp còn 2 cấp (xã/phường → tỉnh), diaChi giữ "
    "nguyên số nhà/đường/tổ dân phố/thôn."
)

FIELDS: list[dict] = [
    # --- CHỦ HỒ SƠ (người tặng cho = người sử dụng đất đứng tên trên Giấy chứng nhận) ---
    {
        "name": "ChuHoSo_HoTen",
        "desc": "Họ tên NGƯỜI TẶNG CHO quyền sử dụng đất (chủ hồ sơ). Nguồn theo thứ tự ưu tiên: "
                "Giấy uỷ quyền — dòng 'Họ và tên' của BÊN UỶ QUYỀN ở đầu văn bản (lặp lại ở Lời chứng "
                "của công chứng viên); Văn bản tặng cho quyền sử dụng đất — dòng 'Họ và tên'; Giấy "
                "chứng nhận — mục I 'Người sử dụng đất…' (người đứng tên ĐẦU TIÊN, vd 'Hộ bà …'). "
                "⚠ TUYỆT ĐỐI không lấy người được uỷ quyền (mục 1.2 của Giấy uỷ quyền), không lấy "
                "vợ/chồng đồng sử dụng, không lấy công chứng viên, không lấy UBND ở dòng 'Kính gửi'.",
    },
    {
        "name": "ChuHoSo_LaToChuc",
        "desc": "true nếu CHỦ HỒ SƠ là TỔ CHỨC/doanh nghiệp (có tên pháp nhân đứng đơn kèm mã số doanh "
                "nghiệp), false nếu là cá nhân/hộ gia đình. Hồ sơ hiến đất làm đường gần như luôn là "
                "false. ⚠ 'ỦY BAN NHÂN DÂN PHƯỜNG/XÃ …' ở dòng 'Kính gửi' là NƠI NHẬN văn bản, KHÔNG "
                "biến hồ sơ thành hồ sơ tổ chức. Không chắc thì bỏ field.",
    },
    {
        "name": "ChuHoSo_TenToChuc",
        "desc": "Tên đầy đủ của TỔ CHỨC đứng đơn tặng cho, nguyên văn. Hồ sơ cá nhân/hộ gia đình thì "
                "BỎ FIELD — không lấy tên UBND nơi nhận, không lấy tên văn phòng công chứng.",
    },
    {
        "name": "ChuHoSo_MaSoThue",
        "desc": "Mã số thuế / mã số doanh nghiệp của TỔ CHỨC đứng đơn. Hồ sơ CÁ NHÂN thì BỎ FIELD — "
                "với cá nhân ô 'Mã số thuế' trên cổng bị ẩn.",
    },
    {
        "name": "ChuHoSo_NgaySinh",
        "desc": "Ngày sinh ĐẦY ĐỦ dd/mm/yyyy của người tặng cho. ⚠ Giấy uỷ quyền và Giấy chứng nhận "
                "của thủ tục này chỉ ghi 'Sinh năm 1964' — CHỈ CÓ NĂM thì BỎ FIELD, TUYỆT ĐỐI không "
                "bịa 01/01. Chỉ điền khi có CCCD hoặc giấy tờ ghi đủ ngày-tháng-năm.",
    },
    {
        "name": "ChuHoSo_GioiTinh",
        "desc": "Giới tính người tặng cho: Nam/Nữ. CHỈ suy từ CHỮ SỐ THỨ 4 của số CCCD 12 số của chính "
                "người đó (0/2/4/6/8 = Nam, 1/3/5/7/9 = Nữ). ⚠ File mapping cấm suy từ HỌ TÊN và cấm "
                "suy từ danh xưng 'ông/bà' — không có CCCD 12 số thì BỎ FIELD.",
    },
    {
        "name": "ChuHoSo_DanToc",
        "desc": "Dân tộc của người tặng cho nếu giấy tờ ghi rõ. ⚠ Bộ giấy tờ của thủ tục này (văn bản "
                "tặng cho, giấy uỷ quyền, giấy chứng nhận) KHÔNG ghi dân tộc → bỏ field, đừng mặc "
                "định 'Kinh'.",
    },
    {
        "name": "ChuHoSo_SoDinhDanh",
        "desc": "Số CCCD/CMND HIỆN HÀNH của người tặng cho, chỉ chữ số. Ưu tiên: Giấy uỷ quyền ('CCCD "
                "số'), Văn bản tặng cho ('CCCD số'), Giấy chứng nhận trang chỉnh lý ('thay đổi Chứng "
                "minh nhân dân … thành CCCD …'). ⚠ Số CMND CŨ 9 số in ở trang bìa Giấy chứng nhận "
                "(vd 'số giấy CMND 063078311') CHỈ dùng để đối chiếu lịch sử, KHÔNG điền vào đây.",
    },
    {
        "name": "ChuHoSo_NgayCap",
        "desc": "Ngày cấp CCCD của người tặng cho, dd/mm/yyyy, phải đi cùng ĐÚNG số CCCD đó (Giấy uỷ "
                "quyền ghi 'cấp ngày'). ⚠ KHÔNG lấy ngày công chứng ở Lời chứng, KHÔNG lấy ngày cấp "
                "Giấy chứng nhận, KHÔNG lấy ngày xác nhận chỉnh lý.",
    },
    {
        "name": "ChuHoSo_NoiCap",
        "desc": "Cơ quan cấp CCCD của người tặng cho (Giấy uỷ quyền ghi 'do … cấp', vd 'Cục Cảnh sát "
                "quản lý hành chính về trật tự xã hội'), lấy cùng giấy tờ với số và ngày cấp.",
    },
    {
        "name": "ChuHoSo_NoiCuTru",
        "desc": "Nơi thường trú của NGƯỜI TẶNG CHO, " + _AREA_DESC + " Ưu tiên: Văn bản tặng cho (dòng "
                "'Địa chỉ' — đây là địa chỉ MỚI NHẤT sau sáp nhập, vd 'tổ 42 phường Cam Đường, tỉnh "
                "Lào Cai'), rồi Giấy uỷ quyền ('Địa chỉ thường trú'), rồi trang chỉnh lý của Giấy "
                "chứng nhận. ⚠ ĐÂY KHÔNG PHẢI ĐỊA CHỈ THỬA ĐẤT — hai thứ trùng nhau ở nhiều hồ sơ "
                "nhưng vẫn phải lấy từ dòng nơi cư trú, không lấy từ mục 'Địa chỉ thửa đất'.",
    },
    {
        "name": "ChuHoSo_DienThoai",
        "desc": "Số điện thoại của người tặng cho, chỉ chữ số. Nguồn duy nhất trong bộ giấy tờ mẫu: "
                "dòng 'Điện thoại' của Văn bản tặng cho.",
    },
    {"name": "ChuHoSo_Email", "desc": "Email của người tặng cho nếu giấy tờ ghi rõ. Bộ giấy tờ mẫu không ghi → bỏ field."},
    {"name": "ChuHoSo_Fax", "desc": "Số fax của người tặng cho nếu giấy tờ ghi rõ. Bộ giấy tờ mẫu không ghi → bỏ field."},

    # --- NGƯỜI NỘP (mode A = người được uỷ quyền; mode B = trùng chủ hồ sơ) ---
    {
        "name": "NguoiNop_HoTen",
        "desc": "Họ tên NGƯỜI NỘP. CÓ Giấy uỷ quyền thì BẮT BUỘC lấy NGƯỜI ĐƯỢC UỶ QUYỀN ở mục 1.2 "
                "('Bằng giấy uỷ quyền này chúng tôi nhất trí uỷ quyền cho ông/bà …') — cũng là người "
                "ký 'Người nhận uỷ quyền' ở cuối Văn bản tặng cho. KHÔNG có uỷ quyền thì người nộp "
                "chính là chủ hồ sơ, chép lại y hệt ChuHoSo_HoTen.",
    },
    {
        "name": "NguoiNop_NgaySinh",
        "desc": "Ngày sinh ĐẦY ĐỦ dd/mm/yyyy của NGƯỜI NỘP. ⚠ Giấy uỷ quyền chỉ ghi 'Sinh năm 1966' → "
                "CHỈ CÓ NĂM thì BỎ FIELD, không bịa 01/01.",
    },
    {
        "name": "NguoiNop_GioiTinh",
        "desc": "Giới tính NGƯỜI NỘP: Nam/Nữ. CHỈ suy từ chữ số thứ 4 của CCCD 12 số của chính người "
                "đó; không suy từ họ tên, không suy từ 'ông/bà'. Không có CCCD 12 số thì bỏ field.",
    },
    {"name": "NguoiNop_DanToc", "desc": "Dân tộc của NGƯỜI NỘP nếu giấy tờ ghi rõ. Giấy uỷ quyền không ghi → bỏ field."},
    {
        "name": "NguoiNop_SoDinhDanh",
        "desc": "Số CCCD của NGƯỜI NỘP, chỉ chữ số. Có uỷ quyền thì lấy 'CCCD số' của NGƯỜI ĐƯỢC UỶ "
                "QUYỀN ở mục 1.2 Giấy uỷ quyền. ⚠ Đừng lấy nhầm số của bên uỷ quyền in ngay phía trên.",
    },
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD của NGƯỜI NỘP, dd/mm/yyyy, đi cùng đúng số CCCD của chính người đó."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp CCCD của NGƯỜI NỘP, đi cùng đúng số và ngày cấp."},
    {
        "name": "NguoiNop_NoiCuTru",
        "desc": "Nơi thường trú của NGƯỜI NỘP, " + _AREA_DESC + " Có uỷ quyền thì lấy 'Địa chỉ thường "
                "trú' của NGƯỜI ĐƯỢC UỶ QUYỀN (mục 1.2); không có uỷ quyền thì sao chép NGUYÊN VẸN "
                "ChuHoSo_NoiCuTru. ⚠ Địa chỉ người được uỷ quyền thường KHÁC hẳn địa chỉ chủ hồ sơ "
                "(hồ sơ mẫu: 'Tổ 17, Phường Bình Minh, thành phố Lào Cai' so với 'Cam Đường').",
    },
    {
        "name": "NguoiNop_DienThoai",
        "desc": "Số điện thoại của NGƯỜI NỘP, chỉ chữ số. ⚠ Giấy uỷ quyền KHÔNG ghi số điện thoại của "
                "người được uỷ quyền → hồ sơ không ghi thì BỎ FIELD, TUYỆT ĐỐI không mượn số điện "
                "thoại của chủ hồ sơ ghi trong Văn bản tặng cho.",
    },
    {"name": "NguoiNop_Email", "desc": "Email của NGƯỜI NỘP nếu có."},
    {"name": "NguoiNop_Fax", "desc": "Số fax của NGƯỜI NỘP nếu có."},

    # --- Vợ/chồng đồng sử dụng: KHÔNG có ô trên cổng, trích để cán bộ đối chiếu Giấy chứng nhận ---
    {
        "name": "DongSuDung_HoTen",
        "desc": "Họ tên VỢ/CHỒNG ĐỒNG SỬ DỤNG đứng chung quyền sử dụng đất với chủ hồ sơ (Giấy uỷ "
                "quyền ghi 'Chồng là …' / 'Vợ là …'; Giấy chứng nhận mục I ghi người thứ hai). Bước 2 "
                "KHÔNG có ô cho người này — chỉ lưu trace. Không có thì bỏ field.",
    },
    {"name": "DongSuDung_SoDinhDanh", "desc": "Số CCCD của vợ/chồng đồng sử dụng, chỉ chữ số. Chỉ lưu trace."},

    # --- Nghiệp vụ: chỉ lưu vết cho cán bộ đối chiếu, bước 2 KHÔNG có ô để điền ---
    {
        "name": "TangCho_NoiDung",
        "desc": "Nội dung TRÌNH BÀY người dân khai trong Văn bản tặng cho quyền sử dụng đất (phần 'Tôi "
                "xin trình bày với nội dung như sau'). Chép NGUYÊN VĂN, giữ cả lỗi chính tả của bản "
                "scan; KHÔNG lấy tiêu đề thủ tục in sẵn trên cổng.",
    },
    {
        "name": "TangCho_NoiNhan",
        "desc": "Cơ quan ghi ở dòng 'Kính gửi' của Văn bản tặng cho (vd 'ỦY BAN NHÂN DÂN PHƯỜNG CAM "
                "ĐƯỜNG'). Đây là NƠI NHẬN, không phải tổ chức chủ hồ sơ.",
    },
    {"name": "TangCho_NgayLamDon", "desc": "Ngày ký Văn bản tặng cho, dd/mm/yyyy (dòng '… ngày … tháng … năm …' ở cuối). Thường VIẾT TAY — chỉ trả khi đọc chắc chắn."},
    {
        "name": "GCN_SoPhatHanh",
        "desc": "Số phát hành của Giấy chứng nhận quyền sử dụng đất (vd 'BK 376308'), in ở góc dưới "
                "trang bìa và nhắc lại trong Giấy uỷ quyền / Văn bản tặng cho. Giữ nguyên cả phần chữ.",
    },
    {"name": "GCN_SoVaoSo", "desc": "Số vào sổ cấp Giấy chứng nhận (vd '00071'), ở cuối trang thửa đất của Giấy chứng nhận."},
    {"name": "GCN_NgayCap", "desc": "Ngày cấp Giấy chứng nhận, dd/mm/yyyy (vd 07/9/2012). KHÔNG lẫn với ngày xác nhận chỉnh lý ở trang 'Những thay đổi sau khi cấp'."},
    {"name": "GCN_CoQuanCap", "desc": "Cơ quan cấp Giấy chứng nhận (vd 'UBND thành phố Lào Cai')."},
    {
        "name": "ThuaDat_SoThua",
        "desc": "Số thửa đất có phần diện tích được tặng cho (vd '13'), lấy ở Văn bản tặng cho và Giấy "
                "uỷ quyền. ⚠ Giấy chứng nhận có thể ghi NHIỀU THỬA (vd 13 và 26) và trang biến động "
                "có thể đã tách thửa 13 thành 47/48 — GIỮ ĐÚNG số thửa người dân khai trong Văn bản "
                "tặng cho, không tự đổi sang số thửa sau tách.",
    },
    {
        "name": "ThuaDat_SoToBanDo",
        "desc": "Số tờ bản đồ của thửa đất (vd 'P7-73'). ⚠ Giấy uỷ quyền của hồ sơ mẫu ghi 'P03 – 73' "
                "trong khi Giấy chứng nhận và Văn bản tặng cho ghi 'P7-73' — TRẢ ĐÚNG GIÁ TRỊ CỦA VĂN "
                "BẢN TẶNG CHO, không tự đồng nhất hai giá trị.",
    },
    {
        "name": "ThuaDat_DiaChi",
        "desc": "ĐỊA CHỈ THỬA ĐẤT được tặng cho (KHÔNG phải nơi cư trú), " + _AREA_DESC + " Nguồn: "
                "'Địa chỉ thửa đất' của Giấy uỷ quyền, cột 'Địa chỉ thửa đất' của Giấy chứng nhận, "
                "hoặc phần trình bày của Văn bản tặng cho.",
    },
    {
        "name": "ThuaDat_DienTich",
        "desc": "Diện tích thửa đất gốc ghi trên giấy tờ, m². ⚠ TUYỆT ĐỐI không coi đây là diện tích "
                "được hiến: Giấy chứng nhận ghi 3317 m² cho thửa 13 lúc cấp, trang biến động ghi còn "
                "3398 m², Giấy uỷ quyền ghi 3167 m² — ba con số của ba thời điểm khác nhau. Trả con "
                "số ĐÚNG NGUỒN đang đọc và để cán bộ đối chiếu.",
    },
    {"name": "ThuaDat_MucDichSuDung", "desc": "Mục đích sử dụng đất ghi trên Giấy chứng nhận (vd 'Đất vườn', 'Lúa'). Không có thì bỏ field."},
    {"name": "ThuaDat_ThoiHanSuDung", "desc": "Thời hạn sử dụng đất. ⚠ Trang chỉnh lý có thể đã GIA HẠN (vd 'đến 20/7/2069' thay cho 'đến 20/7/2019') — lấy giá trị SAU gia hạn."},
    {
        "name": "UyQuyen_SoCongChung",
        "desc": "Số công chứng của Giấy uỷ quyền (vd '1820', quyển số '01/2025.TP/CC – SCC/HĐGD'), lấy "
                "ở Lời chứng của công chứng viên. Hồ sơ KHÔNG có uỷ quyền thì BỎ FIELD — đây cũng là "
                "dấu hiệu hồ sơ thuộc mode 'tự nộp'.",
    },
    {"name": "UyQuyen_NgayCongChung", "desc": "Ngày công chứng Giấy uỷ quyền, dd/mm/yyyy ('Hôm nay, ngày …'). ⚠ KHÔNG lẫn với ngày cấp CCCD."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for name in (
    "ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap",
    "TangCho_NgayLamDon", "GCN_NgayCap", "UyQuyen_NgayCongChung",
):
    COMPACT_COMP_BY_NAME[name] = "x-date"
for name in ("ChuHoSo_NoiCuTru", "NguoiNop_NoiCuTru", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[name] = "x-select-area"

# CHỈ các ô CÓ THẬT trên bước 2 của cổng, theo thứ tự DOM trong hai sheet "Cá nhân"/"Tổ chức" của
# `Mapping_tang_cho_quyen_su_dung_dat.xlsx`.
#
# Cố ý KHÔNG khai các nhóm sau (sheet "Cảnh báo và chú thích" của file mapping):
#  • `chkbox_nguoinoplachuhs` — checkbox "Người nộp là chủ hồ sơ". Cổng chỉ copy sang khối chủ hồ sơ
#    tới Nơi cấp/Ngày cấp căn cước, KHÔNG copy Tỉnh/Phường-Xã/Địa chỉ; đổi trạng thái checkbox còn có
#    thể làm cổng xoá dữ liệu đã điền. Mapper phát thẳng ĐỦ khối chủ hồ sơ thay vì trông vào nó.
#  • `code-dkdn` (ô tìm doanh nghiệp, nằm trong khối ẩn `form-search-dn`), `CongDan_maDMDiaChi`
#    (display:none, file mapping ghi "chưa xác định được nhãn").
#  • `local_file`, `local_file_xuly`, `AN_FORM_CHS`, `tokenCsrf` — hidden do hệ thống tự sinh.
#  • ⚠ `CongDan_tenCongDan` và `CongDan_soCmnd` — HAI Ô KHÔNG BAO GIỜ ĐƯỢC PHÁT. Chúng readonly, cổng
#    tự đổ từ tài khoản định danh đang đăng nhập (file mapping: "tên và CCCD người nộp đang readonly
#    rỗng nên cần kiểm tra tài khoản/quyền nộp thay"); script của cổng còn XOÁ TRẮNG "Di động" +
#    "Số Căn cước" ngay khi họ tên bị sửa khác tài khoản — tức là điền vào đây làm HỎNG chính ô bắt
#    buộc "Di động" vừa điền xong. Hành vi này đã xác minh trên cùng họ biểu mẫu Lào Cai
#    (1.115650/1.115678/1.115693).
#    Bù lại, đúng hai ô đó là MỐC DUY NHẤT để biết AI đang đi nộp: extension đọc chúng rồi gửi lên
#    trong `options.formContext` (xem mapper).
UI_COMP_BY_NAME = {
    # Khối NGƯỜI NỘP
    "CongDan_tenCoQuanToChuc": "dom-input",
    "CongDan_maSoThueNguoiNop": "dom-input",
    "CongDan_ngaySinhCongDan": "dom-input",
    "CongDan_gioiTinhCongDan": "dom-select",
    "CongDan_danTocCongDan": "dom-select",
    "CongDan_ngayCapCmnd": "dom-input",
    "CongDan_noiCapCmnd": "dom-input",
    "CongDan_maTinhThanh": "dom-select",   # Tỉnh/Thành phố (cascade 2 cấp, không có huyện).
    "CongDan_maPhuongXa": "dom-select",    # Phường/Xã (nạp sau khi chọn tỉnh).
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
    "ChuHoSo_noiCapCMNDCHS": "dom-input",
    "ChuHoSo_ngayCapCMNDCHS": "dom-input",
    "ChuHoSo_maTinhThanhCHS": "dom-select",
    "ChuHoSo_maPhuongXaCHS": "dom-select",
    "ChuHoSo_diaChiChuHoSo": "dom-input",
    "ChuHoSo_diDongLienLacCHS": "dom-input",
    "ChuHoSo_emailChuHoSo": "dom-input",
    "ChuHoSo_faxChuHoSo": "dom-input",
}

# Hai ô này chỉ HIỆN khi "Đối tượng nộp hồ sơ" = Doanh nghiệp/Tổ chức; sheet "Cảnh báo và chú thích"
# liệt kê chúng trong nhóm ẩn của cả hai bản DOM. Hồ sơ cá nhân mà vẫn phát thì engine báo "không
# điền được" một cách vô cớ.
ORG_ONLY_FIELDS = frozenset({"ChuHoSo_tenCoQuanToChucCHS", "ChuHoSo_maSoThueChuHoSo"})

# Ngược lại, 7 ô nhân thân cá nhân của khối chủ hồ sơ bị display:none khi chọn Tổ chức.
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

"""Facts nguồn cho thủ tục [Lào Cai] giao đất/cho thuê đất, giao rừng/cho thuê rừng — mã 1.115678.

Cùng cổng và cùng biểu mẫu với thủ tục 1.115650 (`giao_thue_dat_lao_cai`): eForm iGate legacy của
`dichvucong.laocai.gov.vn`, bộ ô `CongDan_*` (người nộp) + `ChuHoSo_*` (chủ hồ sơ), engine
`fill-legacy.js` chạy được ngay. Khác biệt nằm ở NGUỒN GIẤY TỜ và ở DANH MỤC ĐÍNH KÈM (xem
`attach/planner.py`), không nằm ở tên ô.

⚑ HAI MODE NGƯỜI NỘP — mode nào cũng phải ra đúng hồ sơ:
  • Mode A "nộp thay": hồ sơ có HỢP ĐỒNG ỦY QUYỀN công chứng → NguoiNop_* là BÊN ĐƯỢC ỦY QUYỀN,
    ChuHoSo_* là người trúng đấu giá. Hai khối là hai người KHÁC NHAU.
  • Mode B "tự nộp": không có ủy quyền → NguoiNop_* trùng đúng ChuHoSo_*.
Mapper tự chốt mode bằng cách đối chiếu số định danh/họ tên của hai khối (xem mapper._same_person),
KHÔNG tin vào một cờ do LLM tự khai.

⚑ HỒ SƠ THỦ TỤC NÀY THƯỜNG LÀ CÁ NHÂN TRÚNG ĐẤU GIÁ ĐẤT Ở, không phải doanh nghiệp làm dự án. Vẫn
giữ đủ field tổ chức vì Điều 3 QĐ 40/2026 bao cả trường hợp tổ chức được giao đất/thuê rừng, nhưng
prompt đã dặn KHÔNG bịa tổ chức khi hồ sơ chỉ có cá nhân.

⚑ Trang nhập liệu CHỈ có 2 khối nhân thân, KHÔNG có phần thân đơn (thửa đất, diện tích, mục đích sử
dụng...). Các field nghiệp vụ bên dưới vẫn trích để lưu trace cho cán bộ đối chiếu nhưng KHÔNG khai
trong UI_COMP_BY_NAME → mapper không phát, tránh bịa ô không tồn tại.
"""

FIELDS: list[dict] = [
    # --- CHỦ HỒ SƠ (người/tổ chức được giao đất, thuê đất, giao rừng, thuê rừng — đứng tên đơn) ---
    {
        "name": "ChuHoSo_HoTen",
        "desc": "Họ tên người đứng tên CHỦ HỒ SƠ = người đề nghị ghi ở mục 1 của Đơn đề nghị giao đất "
                "(Mẫu số 01), cũng là NGƯỜI TRÚNG ĐẤU GIÁ trong Quyết định công nhận kết quả trúng đấu "
                "giá / Biên bản đấu giá. Hồ sơ TỔ CHỨC thì lấy người đại diện theo pháp luật. TUYỆT ĐỐI "
                "không lấy người được ủy quyền nộp thay, không lấy công chứng viên, không lấy người ký "
                "thông báo thuế.",
    },
    {
        "name": "ChuHoSo_LaToChuc",
        "desc": "true nếu CHỦ HỒ SƠ là TỔ CHỨC/doanh nghiệp (đơn ghi tên công ty, có mã số doanh nghiệp, "
                "kèm Giấy chứng nhận đăng ký doanh nghiệp), false nếu là cá nhân/hộ gia đình. Hồ sơ trúng "
                "đấu giá đất ở của cá nhân thì là false. Không chắc thì bỏ field.",
    },
    {
        "name": "ChuHoSo_TenToChuc",
        "desc": "Tên đầy đủ của TỔ CHỨC/doanh nghiệp đứng đơn, nguyên văn từ đơn hoặc Giấy chứng nhận "
                "đăng ký doanh nghiệp. Hồ sơ cá nhân thì BỎ FIELD.",
    },
    {
        "name": "ChuHoSo_MaSoThue",
        "desc": "Mã số thuế / mã số doanh nghiệp của TỔ CHỨC đứng đơn (có thể có đuôi -001). Hồ sơ CÁ "
                "NHÂN thì BỎ FIELD — với cá nhân, ô 'Mã số thuế' trên cổng bị ẩn, và số ghi ở mục 'Mã số "
                "thuế' của thông báo thuế/giấy nộp tiền chỉ là số định danh cá nhân, không điền vào đây.",
    },
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh đầy đủ của người đứng tên chủ hồ sơ, dd/mm/yyyy. Ưu tiên CCCD đúng người, rồi tới Hợp đồng ủy quyền (ghi 'Sinh ngày'). Chỉ có NĂM sinh (vd 'Sinh năm 1974') thì BỎ FIELD, không tự đặt ngày/tháng."},
    {"name": "ChuHoSo_GioiTinh", "desc": "Giới tính người đứng tên chủ hồ sơ: Nam/Nữ. Chỉ suy từ danh xưng gắn trực tiếp với người đó (Ông=Nam, Bà=Nữ) hoặc chữ số thứ 4 của CCCD 12 số (chẵn=Nam, lẻ=Nữ); KHÔNG suy từ tên."},
    {"name": "ChuHoSo_DanToc", "desc": "Dân tộc của người đứng tên chủ hồ sơ nếu giấy tờ ghi rõ (vd Kinh). Hồ sơ trúng đấu giá thường KHÔNG ghi dân tộc → bỏ field, đừng mặc định 'Kinh'."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số CCCD/CMND của người đứng tên CHỦ HỒ SƠ, chỉ chữ số. Nguồn: CCCD, mục 1 của Đơn ('CCCD số'), cột CCCD trong Danh sách người trúng đấu giá, Biên bản đấu giá, Hợp đồng ủy quyền (Bên A)."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp giấy tờ định danh của chủ hồ sơ, dd/mm/yyyy, phải đi cùng ĐÚNG số giấy tờ đó."},
    {"name": "ChuHoSo_NoiCap", "desc": "Cơ quan cấp giấy tờ định danh của chủ hồ sơ (vd 'Cục Cảnh sát quản lý hành chính về trật tự xã hội'), lấy cùng giấy tờ với số và ngày cấp."},
    {
        "name": "ChuHoSo_NoiCuTru",
        "desc": "Địa chỉ của CHỦ HỒ SƠ, object {quocGia,tinh,xa,diaChi}. Cá nhân: nơi thường trú trên CCCD "
                "hoặc mục 2 'Địa chỉ' của Đơn. Tổ chức: địa chỉ TRỤ SỞ CHÍNH. Giữ đủ số nhà/đường/tổ/thôn "
                "trong diaChi. ⚠ ĐÂY KHÔNG PHẢI địa điểm thửa đất được giao — tuyệt đối không lấy nhầm "
                "địa chỉ thửa đất ở mục 4 của Đơn hay ở thông báo thuế.",
    },
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại liên hệ của chủ hồ sơ, chỉ chữ số. Nguồn: mục 3 'Thông tin liên hệ' của Đơn, cột SĐT trong Danh sách người tham gia đấu giá, mục 'Số điện thoại' của Thông báo nộp tiền."},
    {"name": "ChuHoSo_Email", "desc": "Email liên hệ của chủ hồ sơ nếu giấy tờ ghi rõ."},
    {"name": "ChuHoSo_Fax", "desc": "Số fax của chủ hồ sơ nếu giấy tờ ghi rõ."},

    # --- NGƯỜI NỘP HỒ SƠ (mode A = bên được ủy quyền; mode B = trùng chủ hồ sơ) ---
    {
        "name": "NguoiNop_HoTen",
        "desc": "Họ tên NGƯỜI NỘP. CÓ Hợp đồng ủy quyền thì BẮT BUỘC lấy BÊN ĐƯỢC ỦY QUYỀN (Bên B) — cũng "
                "là người ký 'Người được ủy quyền' ở cuối Đơn. KHÔNG có ủy quyền thì người nộp chính là "
                "người đứng tên chủ hồ sơ, chép lại y hệt ChuHoSo_HoTen.",
    },
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh đầy đủ của NGƯỜI NỘP, dd/mm/yyyy (Hợp đồng ủy quyền ghi 'Sinh ngày' của Bên B). Chỉ có năm sinh thì bỏ field."},
    {"name": "NguoiNop_GioiTinh", "desc": "Giới tính NGƯỜI NỘP: Nam/Nữ. Suy từ danh xưng gắn trực tiếp với chính người đó hoặc chữ số thứ 4 của CCCD 12 số."},
    {"name": "NguoiNop_DanToc", "desc": "Dân tộc của NGƯỜI NỘP nếu giấy tờ ghi rõ. Hợp đồng ủy quyền thường không ghi → bỏ field."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND của NGƯỜI NỘP, chỉ chữ số. Có ủy quyền thì phải lấy 'Căn cước số' của BÊN ĐƯỢC ỦY QUYỀN trong Hợp đồng ủy quyền / Lời chứng của công chứng viên."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp giấy tờ định danh của NGƯỜI NỘP, dd/mm/yyyy, đi cùng đúng số giấy tờ của chính người đó."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp giấy tờ định danh của NGƯỜI NỘP (vd 'Bộ Công an'), đi cùng đúng số và ngày cấp."},
    {
        "name": "NguoiNop_NoiCuTru",
        "desc": "Địa chỉ của NGƯỜI NỘP, object {quocGia,tinh,xa,diaChi}. Có ủy quyền thì lấy 'Nơi thường "
                "trú' của BÊN ĐƯỢC ỦY QUYỀN; không có ủy quyền thì sao chép NGUYÊN VẸN ChuHoSo_NoiCuTru.",
    },
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại của NGƯỜI NỘP, chỉ chữ số. Có ủy quyền thì lấy số của bên được ủy quyền; hồ sơ không ghi thì BỎ FIELD (không mượn số của chủ hồ sơ)."},
    {"name": "NguoiNop_Email", "desc": "Email của NGƯỜI NỘP nếu có."},
    {"name": "NguoiNop_Fax", "desc": "Số fax của NGƯỜI NỘP nếu có."},

    # --- Nghiệp vụ: chỉ lưu vết cho cán bộ đối chiếu, trang này KHÔNG có ô để điền ---
    {
        "name": "Don_NoiDungDeNghi",
        "desc": "Nội dung ĐỀ NGHỊ người dân khai trong Đơn đề nghị giao đất/thuê đất (Mẫu số 01). Chép "
                "NGUYÊN VĂN phần người dân khai; KHÔNG lấy tiêu đề thủ tục in sẵn trên cổng.",
    },
    {
        "name": "ThuaDat_DiaChi",
        "desc": "ĐỊA ĐIỂM THỬA ĐẤT được giao/thuê (KHÔNG phải nơi cư trú), object {quocGia,tinh,xa,diaChi}. "
                "Nguồn: mục 4 'Địa điểm thửa đất/khu đất/khu rừng' của Đơn, hoặc cột 'Vị trí thửa đất' "
                "trong Danh sách người trúng đấu giá. Không có nguồn ghi rõ thì bỏ field.",
    },
    {
        "name": "ThuaDat_SoThua",
        "desc": "Số thửa đất (vd '29'), lấy ở mục 4 của Đơn hoặc cột 'Số thửa đất' của Danh sách người "
                "trúng đấu giá / Biên bản đấu giá. Chỉ lấy đúng thửa của CHỦ HỒ SƠ khi danh sách có nhiều "
                "người.",
    },
    {"name": "ThuaDat_SoToBanDo", "desc": "Số tờ bản đồ của thửa đất (vd '137'), cùng nguồn với số thửa và phải cùng một dòng/một thửa."},
    {"name": "ThuaDat_DienTich", "desc": "Diện tích thửa đất, m² (vd '80,1'), lấy ở mục 5 của Đơn hoặc cột 'Diện tích' của danh sách trúng đấu giá. Giữ nguyên dấu phẩy thập phân."},
    {"name": "ThuaDat_MucDichSuDung", "desc": "Mục đích sử dụng đất ghi ở mục 8 của Đơn (vd 'Đất ở tại đô thị'). Không có thì bỏ field."},
    {"name": "ThuaDat_ThoiHanSuDung", "desc": "Thời hạn sử dụng đất ghi ở mục 10 của Đơn (vd 'Lâu dài'). Không có thì bỏ field."},
    {
        "name": "DauGia_SoQuyetDinh",
        "desc": "Số Quyết định công nhận kết quả trúng đấu giá quyền sử dụng đất (vd '301/QĐ-UBND'). Lấy ở "
                "dòng 'Số:' của chính quyết định đó. KHÔNG lấy số của các quyết định được viện dẫn trong "
                "phần 'Căn cứ' (phương án đấu giá, giá khởi điểm, phân cấp thẩm quyền...).",
    },
    {"name": "DauGia_NgayQuyetDinh", "desc": "Ngày ban hành Quyết định công nhận kết quả trúng đấu giá, dd/mm/yyyy, lấy cùng quyết định với DauGia_SoQuyetDinh."},
    {
        "name": "UyQuyen_SoCongChung",
        "desc": "Số công chứng của Hợp đồng ủy quyền (vd '1812/2026/CCGD'), lấy ở Lời chứng của công chứng "
                "viên. Hồ sơ KHÔNG có ủy quyền thì BỎ FIELD — đây cũng là dấu hiệu hồ sơ thuộc mode 'tự nộp'.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for name in (
    "ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap",
    "DauGia_NgayQuyetDinh",
):
    COMPACT_COMP_BY_NAME[name] = "x-date"
for name in ("ChuHoSo_NoiCuTru", "NguoiNop_NoiCuTru", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[name] = "x-select-area"

# CHỈ các ô CÓ THẬT trên bước 2 của cổng, theo thứ tự DOM trong file mapping
# `mapping_giao_dat_trung_dau_gia_Lao_Cai.xlsx` (dựng từ 2 bản DOM: cá nhân + tổ chức).
#
# Cố ý KHÔNG khai 3 nhóm sau:
#  • `chkbox_nguoinoplachuhs` — checkbox "Người nộp là chủ hồ sơ". Cổng chỉ copy sang khối chủ hồ sơ
#    tới Nơi cấp/Ngày cấp căn cước, KHÔNG copy Tỉnh/Phường-Xã/Địa chỉ; đổi trạng thái checkbox còn có
#    thể làm cổng xoá dữ liệu đã điền. Mapper phát thẳng ĐỦ khối chủ hồ sơ thay vì trông vào nó.
#  • `CongDan_maDMDiaChi` — input display:none, file mapping ghi rõ "không xác định được nhãn".
#  • `local_file`, `local_file_xuly`, `AN_FORM_CHS`, `tokenCsrf` — hidden do hệ thống tự sinh.
#  • ⚠ `CongDan_tenCongDan` và `CongDan_soCmnd` — HAI Ô KHÔNG BAO GIỜ ĐƯỢC PHÁT. Chúng readonly, cổng
#    tự đổ từ tài khoản định danh đang đăng nhập; script của cổng còn XOÁ TRẮNG "Di động" + "Số Căn
#    cước" ngay khi họ tên bị sửa khác tài khoản — tức là điền vào đây làm HỎNG chính ô bắt buộc
#    "Di động" vừa điền xong. Hành vi này đã xác minh trên cùng họ biểu mẫu Lào Cai
#    (1.115667/1.115668/1.115677/1.115694, xem `xac_nhan_tiep_tuc_dat_nong_nghiep`).
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

# Hai ô này chỉ HIỆN khi "Đối tượng nộp hồ sơ" = Doanh nghiệp/Tổ chức (sheet "Cảnh báo trường ẩn",
# mục B.2). Hồ sơ cá nhân mà vẫn phát thì engine báo "không điền được" một cách vô cớ.
ORG_ONLY_FIELDS = frozenset({"ChuHoSo_tenCoQuanToChucCHS", "ChuHoSo_maSoThueChuHoSo"})

# Ngược lại, 7 ô nhân thân cá nhân của khối chủ hồ sơ bị display:none khi chọn Tổ chức (mục B.1).
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

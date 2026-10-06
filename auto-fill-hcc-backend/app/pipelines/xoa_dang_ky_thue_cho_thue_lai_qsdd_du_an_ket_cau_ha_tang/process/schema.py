"""Compact schema cho "Xóa đăng ký thuê, cho thuê lại quyền sử dụng đất trong dự án xây dựng kinh doanh kết cấu
hạ tầng" (1.012766) — cổng DVC TP Đà Nẵng dichvucong.danang.gov.vn (Form.io).

Field-key data[...] Y HỆT khối "Thông tin chung" của các thủ tục đất đai Đà Nẵng (xoa_dang_ky_bien_phap_bao_dam_
da_nang, dang_ky_cap_gcn_nhan_chuyen_nhuong_du_an_bat_dong_san) — KHÔNG có panel thửa đất. Nguồn theo
"Mapping_Xoa_DK_thue_QSDD_DaNang.xlsx", thứ tự ưu tiên: CCCD → Đơn đăng ký biến động (Mẫu 18) → Hợp đồng chấm
dứt hợp đồng thuê (+ lời chứng) → Văn bản thỏa thuận (+ lời chứng) → Giấy chứng nhận đã cấp.

ChuHoSo_* = người sử dụng đất đứng tên Đơn Mẫu 18 (bên cho thuê). NguoiNop_* = người nộp (mặc định tự nộp).
"""

# --- Chủ hồ sơ (người đứng tên Đơn đăng ký biến động) ---
FIELDS: list[dict] = [
    {"name": "ChuHoSo_LoaiChuThe", "desc": '"Cá nhân" nếu chủ hồ sơ là một người; "Tổ chức" chỉ khi Đơn Mẫu 18 '
        'đứng tên công ty/cơ quan.'},
    {"name": "ChuHoSo_HoTen", "desc": "Họ và tên CHỦ HỒ SƠ, IN HOA — người đứng tên mục 'I. Người sử dụng đất… "
        "Tên' của Đơn đăng ký biến động (Mẫu 18). Đơn ghi kèm năm sinh trên cùng dòng → CHỈ lấy họ tên. Không "
        "có Đơn → người sử dụng đất là BÊN CHO THUÊ (bên A) đứng ĐẦU trong Hợp đồng chấm dứt hợp đồng thuê. ⚠ "
        "KHÔNG lấy bên THUÊ (doanh nghiệp/người đại diện bên thuê) trừ khi chính Đơn đứng tên bên thuê."},
    {"name": "ChuHoSo_MaSoThue", "desc": "Mã số thuế/mã số doanh nghiệp của CHỦ HỒ SƠ — CHỈ khi chủ hồ sơ là "
        "tổ chức. Chỉ chữ số."},
    {"name": "ChuHoSo_DiaChi", "desc": "Địa chỉ của CHỦ HỒ SƠ, object {quocGia,tinh,xa,diaChi}. ƯU TIÊN số "
        "nhà/đường ở mục 'Địa chỉ' của Đơn Mẫu 18; phường/xã theo địa danh MỚI ở 'Nơi cư trú' của hợp đồng/văn "
        "bản công chứng (giấy tờ ghi '… (nay là phường …)' thì lấy phường MỚI); thiếu mới lấy 'Nơi thường trú' "
        "trên CCCD. tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/đường/tổ (KHÔNG kèm phường/tỉnh). "
        "Viết tắt 'TP Đà Nẵng' → 'Thành phố Đà Nẵng'. KHÔNG lấy địa chỉ thửa đất hay địa chỉ trụ sở bên thuê."},
]

# --- Nội dung yêu cầu ---
FIELDS += [
    {"name": "NoiDungYeuCau", "desc": "CHÉP NGUYÊN VĂN mục 'II. Nội dung biến động' của Đơn Mẫu 18 nếu người "
        "dân có ghi. Bỏ dấu chấm chấm (.....). Đơn để trống mục này thì BỎ field, KHÔNG tự viết."},
    {"name": "VanBanXoaThue", "desc": "Văn bản làm căn cứ xóa đăng ký thuê, ghi gọn MỘT câu: '{tên văn bản} số "
        "công chứng {số} ngày {dd/mm/yyyy} tại {tổ chức công chứng}' kèm hợp đồng thuê bị chấm dứt nếu có, vd "
        "'Hợp đồng chấm dứt Hợp đồng thuê quyền sử dụng đất số công chứng 1111/2026/CCGD ngày 05/3/2026 tại Văn "
        "phòng công chứng Hòa Bình (chấm dứt Hợp đồng thuê quyền sử dụng đất số công chứng 222 ngày "
        "10/01/2015)'. Số công chứng lấy ở 'Số công chứng' của LỜI CHỨNG công chứng viên đi kèm. Không có thì bỏ."},
]

# --- Người nộp hồ sơ ---
FIELDS += [
    {"name": "NguoiNop_LoaiDoiTuong", "desc": '"Cá nhân" (đa số) hoặc "Tổ chức".'},
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên NGƯỜI NỘP HỒ SƠ, IN HOA. Có văn bản ủy quyền NỘP HỒ SƠ → người "
        "ĐƯỢC ủy quyền. Không có (tự nộp) → CHÍNH LÀ chủ hồ sơ. ⚠ Giấy ủy quyền để KÝ HỢP ĐỒNG của bên thuê "
        "(vd giám đốc ủy quyền phó giám đốc ký) KHÔNG phải ủy quyền nộp hồ sơ."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh NGƯỜI NỘP, dd/mm/yyyy — CCCD, hoặc dòng 'Sinh ngày' của "
        "ĐÚNG người đó trong hợp đồng/văn bản công chứng. Chỉ có NĂM sinh thì BỎ, không tự bịa ngày/tháng."},
    {"name": "NguoiNop_GioiTinh", "desc": '"Nam"/"Nữ" — CCCD; hoặc danh xưng Ông/Bà gắn với ĐÚNG người nộp '
        'trong hợp đồng/văn bản công chứng.'},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/định danh cá nhân 12 số của NGƯỜI NỘP — CCCD, mục 'Giấy tờ "
        "nhân thân' của Đơn, hoặc 'Căn cước công dân số' của đúng người đó trong hợp đồng. Chỉ chữ số. ⚠ Số "
        "'CMND số …' 9 số ghi trong ngoặc chỉ để đối chiếu, KHÔNG lấy."},
    {"name": "NguoiNop_MaSoThue", "desc": "Mã số thuế NGƯỜI NỘP — CHỈ khi là tổ chức. Chỉ chữ số."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD NGƯỜI NỘP, dd/mm/yyyy — mặt sau CCCD, 'Ngày cấp' trên "
        "Đơn, hoặc '… cấp ngày …' sau số căn cước trong hợp đồng."},
    {"name": "NguoiNop_NoiCap", "desc": 'Cơ quan cấp CCCD NGƯỜI NỘP, CHỈ khi CCCD ghi rõ, viết ĐẦY ĐỦ: "Cục '
        'Cảnh sát quản lý hành chính về trật tự xã hội" hoặc "Bộ Công an". Hợp đồng không ghi nơi cấp → bỏ.'},
    {"name": "NguoiNop_DiaChi", "desc": "Địa chỉ NGƯỜI NỘP, object {quocGia,tinh,xa,diaChi}. Tự nộp → GIỐNG "
        "ChuHoSo_DiaChi. Người được ủy quyền → địa chỉ của chính người đó trên văn bản ủy quyền/CCCD; không "
        "có thì bỏ. KHÔNG lấy địa chỉ thửa đất."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại — mục 'Điện thoại liên hệ' của Đơn Mẫu 18. Chỉ chữ số."},
    {"name": "NguoiNop_Email", "desc": "Email — mục 'Hộp thư điện tử' của Đơn nếu có ghi; thường trống → bỏ."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["NguoiNop_NgaySinh"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_NgayCap"] = "x-date"
COMPACT_COMP_BY_NAME["ChuHoSo_DiaChi"] = "x-select-area"
COMPACT_COMP_BY_NAME["NguoiNop_DiaChi"] = "x-select-area"

# ---- UI Form.io fields (data[...]) — comp dom-*. Field-key theo cột H của file mapping.
UI_COMP_BY_NAME = {
    # Chủ hồ sơ.
    "data[ownerFullname]": "dom-input",
    "data[isOwnerDossier]": "dom-checkbox",
    "data[organization]": "dom-input",
    # Người nộp hồ sơ.
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[email]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[note]": "dom-input",
    "data[noidungyeucaugiaiquyet]": "dom-input",   # textarea.
    "data[taxCode]": "dom-input",
    "data[chonDoiTuong]": "dom-select",            # Cá nhân/Tổ chức.
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",                # nhãn "Phường/Xã" (mô hình 2 cấp).
    "data[address]": "dom-input",
}

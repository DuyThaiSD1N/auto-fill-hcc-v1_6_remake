"""Compact schema cho "Tách thửa đất hoặc hợp thửa đất" — cổng DVC TP Đà Nẵng dichvucong.danang.gov.vn
(Form.io). CÙNG form/contact-block với #75 (dang_ky_bien_dong_dat_dai_da_nang) và chuyen_muc_dich_su_dung_dat
— UI field-key data[...] Y HỆT (1 panel thongTinChung).

Phần I là 1 panel "thongTinChung" chứa HAI vai:
- ChuHoSo_*  : CHỦ HỒ SƠ = CHỦ ĐẤT/người sử dụng đất ĐỀ NGHỊ tách thửa/hợp thửa (đứng tên GCN / Đơn đề
               nghị tách thửa Mẫu số 21 / Bản vẽ Mẫu số 22). Có thể CÁ NHÂN / TỔ CHỨC.
- NguoiNop_* : NGƯỜI NỘP HỒ SƠ = người trực tiếp thao tác nộp (có thể là người được ỦY QUYỀN). Khi tự nộp
               thì NguoiNop = ChuHoSo.
KHÁC #75: KHÔNG có bên chuyển nhượng/bên nhận — chỉ MỘT chủ đất tự tách/hợp thửa.
"""

# --- Chủ hồ sơ (subject = chủ đất đề nghị tách/hợp thửa) ---
FIELDS: list[dict] = [
    {"name": "ChuHoSo_LoaiChuThe", "desc": '"Tổ chức" nếu chủ hồ sơ là công ty/doanh nghiệp/HTX/cơ quan '
        '(tên có "Công ty", "Doanh nghiệp", "HTX", "Hợp tác xã"); "Cá nhân" nếu là một người. Chủ hồ sơ là '
        'CHỦ ĐẤT đề nghị tách/hợp thửa (người đứng tên Giấy chứng nhận / Đơn đề nghị tách thửa Mẫu 21 / Bản vẽ Mẫu 22).'},
    {"name": "ChuHoSo_HoTen", "desc": "Tên CHỦ HỒ SƠ — nếu CÁ NHÂN: họ và tên (IN HOA); nếu TỔ CHỨC: tên "
        "đầy đủ tổ chức. Lấy ở Đơn đề nghị tách thửa (người sử dụng đất), Giấy chứng nhận QSDĐ (người đứng "
        "tên), Bản vẽ Mẫu 22 (tên người sử dụng đất), hoặc Giấy chứng nhận ĐKKD."},
    {"name": "ChuHoSo_DiaChi", "desc": "Địa chỉ THƯỜNG TRÚ/nơi ở của CHỦ HỒ SƠ (chủ đất), object "
        "{quocGia,tinh,xa,diaChi}. Lấy ở mục 1c 'Địa chỉ' của người sử dụng đất trong Đơn đề nghị (Mẫu 21), "
        "hoặc dòng 'địa chỉ' của người sử dụng đất trong Bản vẽ (Mẫu 22, mục II). ⚠ TUYỆT ĐỐI KHÔNG lấy "
        "'địa chỉ thửa đất' (vị trí lô đất) làm địa chỉ người — dù trong hồ sơ này chúng có thể trùng nhau. "
        "tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/đường/thôn (nếu chỉ ghi cấp phường thì để diaChi trống)."},
]

# --- Nội dung nghiệp vụ: mô tả việc tách/hợp thửa (điền textarea "Nội dung yêu cầu giải quyết") ---
FIELDS += [
    {"name": "NoiDungYeuCau", "desc": "Nội dung yêu cầu giải quyết — CHÉP ĐẦY ĐỦ nội dung mục 2 'Đề nghị "
        "tách thửa đất, hợp thửa đất' của Đơn đề nghị (Mẫu 21), KHÔNG rút gọn, KHÔNG tóm tắt. BẮT BUỘC giữ "
        "MỌI chi tiết của thửa ĐẤT GỐC: số thửa, tờ bản đồ, diện tích, loại đất, địa chỉ thửa đất, số Giấy "
        "chứng nhận (số phát hành), số vào sổ cấp GCN, ngày cấp GCN. Sau đó LIỆT KÊ đầy đủ các thửa SAU khi "
        "tách/hợp — MỖI thửa MỘT DÒNG riêng, gồm: tên người sử dụng, số thửa mới, diện tích, loại đất. "
        "Định dạng nhiều dòng: dòng đầu mô tả thửa gốc + 'thành N thửa:', rồi mỗi thửa con một dòng bắt đầu "
        "bằng '- Thửa thứ k: ...'. Bỏ các dấu chấm chấm (.....) placeholder trống trên đơn. Ví dụ KHUÔN "
        "(thay bằng số liệu THẬT trong hồ sơ): 'Tách thửa đất số [số] tờ bản đồ số [số] diện tích [..] m²; "
        "loại đất: [..], địa chỉ thửa đất: [..], Giấy chứng nhận: [..], số vào sổ cấp GCN: [..], ngày cấp "
        "GCN: [..] thành [N] thửa:\\n- Thửa thứ 1: [tên người], thửa [..], diện tích: [..] m², loại đất: "
        "[..]\\n- Thửa thứ 2: [tên người], thửa [..], diện tích: [..] m², loại đất: [..]'. Nếu là HỢP thửa "
        "thì chép mục 2b tương tự. Không có nội dung thì bỏ trống."},
]

# --- Người nộp hồ sơ (người thao tác nộp; có thể được ủy quyền) ---
FIELDS += [
    {"name": "NguoiNop_LoaiDoiTuong", "desc": '"Tổ chức" nếu người nộp là tổ chức; "Cá nhân" nếu là một '
        'người. Đa số người nộp là CÁ NHÂN (kể cả khi được tổ chức ủy quyền).'},
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên NGƯỜI NỘP HỒ SƠ. Nếu có Hợp đồng/Giấy ủy quyền: lấy BÊN "
        "ĐƯỢC ỦY QUYỀN (Bên B/người được ủy quyền). Nếu KHÔNG có ủy quyền (tự nộp): người nộp CHÍNH LÀ chủ "
        "hồ sơ. IN HOA như CCCD."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh NGƯỜI NỘP (cá nhân), dd/mm/yyyy — CCCD / Hợp đồng ủy quyền."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính NGƯỜI NỘP: "Nam"/"Nữ" — CCCD, hoặc suy từ danh xưng '
        'Ông/Bà trong Hợp đồng ủy quyền.'},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND/định danh cá nhân NGƯỜI NỘP. Đọc CCCD hoặc Hợp "
        "đồng ủy quyền (Bên B 'Căn cước công dân số'). Chỉ chữ số. Ưu tiên 12 chữ số."},
    {"name": "NguoiNop_MaSoThue", "desc": "Mã số thuế / mã định danh tổ chức NGƯỜI NỘP (CHỈ khi người nộp "
        "là TỔ CHỨC). Chỉ chữ số."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD NGƯỜI NỘP, dd/mm/yyyy — mặt sau CCCD / Hợp đồng ủy quyền."},
    {"name": "NguoiNop_NoiCap", "desc": 'Cơ quan cấp CCCD NGƯỜI NỘP — GHI ĐẦY ĐỦ, KHÔNG viết tắt. Giấy tờ '
        'hay ghi tắt "CCSQLHC TTXH" / "CCSVLHC TTXH" / "CCS QLHC về TTXH" / "Cục CSQLHC" → PHẢI ghi thành '
        '"Cục Cảnh sát quản lý hành chính về trật tự xã hội". Thẻ căn cước mới ghi "Bộ Công an".'},
    {"name": "NguoiNop_DiaChi", "desc": "Địa chỉ THƯỜNG TRÚ của CHÍNH NGƯỜI NỘP, object {quocGia,tinh,xa,"
        "diaChi}. CHỈ lấy ở CCCD người nộp (Nơi thường trú) hoặc Hợp đồng ủy quyền (địa chỉ Bên được ủy "
        "quyền). ⚠ Giấy giới thiệu THƯỜNG KHÔNG có địa chỉ thường trú → nếu không có, BỎ TRỐNG toàn bộ "
        "(đừng đoán). TUYỆT ĐỐI KHÔNG lấy địa chỉ thửa đất, trụ sở tổ chức/ngân hàng, hay tỉnh của thửa đất "
        "làm địa chỉ người nộp. tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/đường/thôn."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại NGƯỜI NỘP. Chỉ chữ số. Thường không có trên giấy tờ."},
    {"name": "NguoiNop_Email", "desc": "Email NGƯỜI NỘP nếu giấy tờ có; thường không có → bỏ."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["NguoiNop_NgaySinh"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_NgayCap"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_DiaChi"] = "x-select-area"
COMPACT_COMP_BY_NAME["ChuHoSo_DiaChi"] = "x-select-area"

# ---- UI Form.io fields (data[...]) — comp dom-*. Y HỆT #75/chuyen_muc_dich (1 panel thongTinChung).
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
    "data[noidungyeucaugiaiquyet]": "dom-input",
    "data[taxCode]": "dom-input",
    "data[chonDoiTuong]": "dom-select",
    "data[hinhThucNop]": "dom-select",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
}

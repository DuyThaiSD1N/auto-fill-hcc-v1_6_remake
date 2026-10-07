"""Compact schema cho "Đăng ký biện pháp bảo đảm bằng QSDĐ, tài sản gắn liền với đất" (cổng Đà Nẵng —
Form.io, field-key RIÊNG).

ChuThe_* = CHỦ HỒ SƠ = NGƯỜI YÊU CẦU ĐĂNG KÝ (Phiếu 01a Mục 1; không có Phiếu thì tổ chức cử người theo Giấy
giới thiệu/ủy quyền, vd ngân hàng). Cá nhân → nhân thân; Tổ chức → tên + mã số thuế.
NguoiNop_* = NGƯỜI NỘP = người được giới thiệu/ủy quyền (chỉ khi khác chủ hồ sơ). Thủ tục chỉ có chế độ tờ khai.
"""

FIELDS: list[dict] = [
    {"name": "ChuThe_LoaiChuThe", "desc": 'Loại chủ thể NGƯỜI YÊU CẦU ĐĂNG KÝ (chủ hồ sơ): "Cá nhân" hoặc "Tổ '
        'chức". Xem ô tích Mục 1 Phiếu Mẫu 01a; không có Phiếu mà có Giấy giới thiệu/ủy quyền của một tổ chức '
        '(vd ngân hàng) cử người đi đăng ký thì là "Tổ chức".'},
    {"name": "ChuThe_HoTen", "desc": "Họ và tên NGƯỜI YÊU CẦU ĐĂNG KÝ (khi là CÁ NHÂN). Lấy từ CCCD / Phiếu "
        "Mẫu 01a (Mục 1 'Họ và tên đầy đủ' hoặc Mục 3.1 bên bảo đảm / 4.1 bên nhận bảo đảm). IN HOA."},
    {"name": "ChuThe_TenToChuc", "desc": "Tên đầy đủ TỔ CHỨC yêu cầu đăng ký (vd ngân hàng — bên nhận bảo đảm). "
        "Phiếu Mẫu 01a Mục 1/3.1/4.1; không có Phiếu thì tên tổ chức ĐỨNG RA ký Giấy giới thiệu/ủy quyền (tiêu đề "
        "góc trái + chi nhánh). KHÔNG phải công ty có tài sản thế chấp/chủ GCN. Bỏ trống nếu là cá nhân."},
    {"name": "ChuThe_NgaySinh", "desc": "Ngày sinh (cá nhân), dd/mm/yyyy — CCCD."},
    {"name": "ChuThe_GioiTinh", "desc": 'Giới tính (cá nhân): "Nam" hoặc "Nữ" — CCCD.'},
    {"name": "ChuThe_SoDinhDanh", "desc": "Số CCCD/CMND/định danh cá nhân NGƯỜI YÊU CẦU (khi cá nhân). Đọc "
        "CCCD (mặt trước/MRZ) hoặc Phiếu Mục 3.3/4.3 ('Số'). Chỉ chữ số. Ưu tiên 12 chữ số."},
    {"name": "ChuThe_MaSoThue", "desc": "Mã số thuế / mã định danh TỔ CHỨC (khi là tổ chức). Phiếu Mục "
        "3.3/4.3. Chỉ chữ số. Bỏ trống nếu cá nhân."},
    {"name": "ChuThe_NgayCap", "desc": "Ngày cấp giấy tờ tùy thân, dd/mm/yyyy. Ưu tiên 'ngày cấp' ghi ở "
        "Phiếu Mục 3.3/4.3; hoặc mặt sau CCCD. KHÔNG lấy 'ngày hết hạn'/'Có giá trị đến'."},
    {"name": "ChuThe_NoiCap", "desc": 'Cơ quan cấp giấy tờ. Phiếu Mục 3.3/4.3 "Cơ quan cấp"; hoặc mặt sau '
        'CCCD. "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản lý hành '
        'chính về trật tự xã hội"; thẻ CĂN CƯỚC mới → "Bộ Công an".'},
    {"name": "ChuThe_DiaChi", "desc": "Địa chỉ NGƯỜI YÊU CẦU, object {quocGia,tinh,xa,diaChi}. Lấy ở CCCD "
        "(Nơi thường trú) / Phiếu Mục 3.2/4.2 (Địa chỉ) / Mục 1 (Địa chỉ liên hệ). tinh='Tỉnh/Thành phố …', "
        "xa=phường/xã, diaChi=số nhà/đường/tổ (KHÔNG kèm phường/xã/tỉnh)."},
    {"name": "ChuThe_DienThoai", "desc": "Số điện thoại NGƯỜI YÊU CẦU — Phiếu Mục 1 'Số điện thoại' hoặc "
        "Mục 3.5/4.4. Chỉ chữ số; không lấy số bàn/fax."},
    {"name": "ChuThe_Email", "desc": "Thư điện tử NGƯỜI YÊU CẦU nếu Phiếu Mục 1/3.5/4.4 có ('Thư điện tử "
        "(nếu có)')."},

    # Người nộp = người được tổ chức/chủ hồ sơ GIỚI THIỆU / ỦY QUYỀN đi làm thủ tục (khác chủ hồ sơ).
    {"name": "NguoiNop_HoTen", "desc": "Họ tên người ĐƯỢC GIỚI THIỆU/ỦY QUYỀN đi đăng ký (Giấy giới thiệu 'trân "
        "trọng giới thiệu: Ông/Bà …', Giấy ủy quyền 'bên được ủy quyền'). Không có giấy này thì bỏ trống."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND của đúng người ở NguoiNop_HoTen (ghi cạnh tên trên Giấy "
        "giới thiệu/ủy quyền hoặc CCCD của người đó). Chỉ chữ số."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh đầy đủ của người ở NguoiNop_HoTen, dd/mm/yyyy; chỉ khi giấy tờ "
        "ghi rõ (CCCD của người đó). Không có hoặc chỉ có năm thì bỏ."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính người ở NguoiNop_HoTen: "Nam"/"Nữ" CHỈ khi CCCD của người đó '
        'ghi rõ; danh xưng "Ông/Bà" chung chung không đủ — không suy từ tên.'},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD của người ở NguoiNop_HoTen (dòng 'số CCCD … cấp ngày …' "
        "hoặc mặt sau CCCD), dd/mm/yyyy."},
    {"name": "NguoiNop_NoiCap", "desc": "Nơi cấp CCCD của người ở NguoiNop_HoTen nếu giấy tờ ghi rõ; chuẩn hóa như "
        "ChuThe_NoiCap. Không ghi thì bỏ."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại của người ở NguoiNop_HoTen nếu giấy tờ ghi. Chỉ chữ số."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("ChuThe_NgaySinh", "ChuThe_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
COMPACT_COMP_BY_NAME["ChuThe_DiaChi"] = "x-select-area"

# ---- UI Form.io fields (data[...]) — comp dom-*. Tên field-key RIÊNG cổng Đà Nẵng (lấy CHUẨN từ HTML).
UI_COMP_BY_NAME = {
    "data[chonDoiTuong]": "dom-select",     # "Cá nhân" / "Tổ chức".
    "data[fullname]": "dom-input",          # Họ tên người nộp.
    "data[ownerFullname]": "dom-input",     # Họ tên chủ hồ sơ.
    "data[isOwnerDossier]": "dom-checkbox", # Chủ hồ sơ cũng là người nộp (mặc định CHƯA tick).
    "data[organization]": "dom-input",      # Tên tổ chức (khi tổ chức).
    "data[taxCode]": "dom-input",           # Mã số thuế (khi tổ chức).
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[identityNumber]": "dom-input",    # CCCD (cá nhân) hoặc mã định danh tổ chức.
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",   # Nơi cấp — SELECT (danh mục API).
    "data[nation]": "dom-select",           # Quốc gia — "Việt Nam".
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[email]": "dom-input",
}

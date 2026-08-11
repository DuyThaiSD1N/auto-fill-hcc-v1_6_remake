"""Compact schema cho "Đăng ký biện pháp bảo đảm bằng QSDĐ, tài sản gắn liền với đất" (cổng Đà Nẵng —
Form.io, field-key RIÊNG).

CHỦ THỂ = NGƯỜI YÊU CẦU ĐĂNG KÝ (tài khoản đăng nhập). Cá nhân → nhân thân; Tổ chức → tên + mã số thuế.
Nguồn: CCCD + Phiếu yêu cầu Mẫu 01a (Mục 1 / Mục 3.3 hoặc 4.3).
"""

FIELDS: list[dict] = [
    {"name": "ChuThe_LoaiChuThe", "desc": 'Loại chủ thể người yêu cầu đăng ký: "Cá nhân" hoặc "Tổ chức". '
        "Xem ô tích Mục 1 Phiếu Mẫu 01a (Cá nhân/Tổ chức) hoặc suy từ việc có Mã số thuế (tổ chức) hay số "
        "CCCD (cá nhân)."},
    {"name": "ChuThe_HoTen", "desc": "Họ và tên NGƯỜI YÊU CẦU ĐĂNG KÝ (khi là CÁ NHÂN). Lấy từ CCCD / Phiếu "
        "Mẫu 01a (Mục 1 'Họ và tên đầy đủ' hoặc Mục 3.1 bên bảo đảm / 4.1 bên nhận bảo đảm). IN HOA."},
    {"name": "ChuThe_TenToChuc", "desc": "Tên đầy đủ TỔ CHỨC (khi người yêu cầu là TỔ CHỨC, vd ngân hàng). "
        "Lấy từ Phiếu Mẫu 01a Mục 1/3.1/4.1. Bỏ trống nếu là cá nhân."},
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
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["ChuThe_NgaySinh"] = "x-date"
COMPACT_COMP_BY_NAME["ChuThe_NgayCap"] = "x-date"
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

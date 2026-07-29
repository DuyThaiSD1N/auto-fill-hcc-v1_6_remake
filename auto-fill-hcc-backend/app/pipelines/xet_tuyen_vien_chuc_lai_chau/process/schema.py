"""Compact schema cho "Xét tuyển Viên chức (NĐ 85/2023) (Lai Châu)" — eForm chuẩn Lai Châu (CongDan_*).

LLM chỉ trả FACT nguồn về NGƯỜI DỰ TUYỂN (từ CCCD + Phiếu đăng ký dự tuyển Mẫu 01). `mapper.enrich`
suy ra tất định các ô CongDan_* (comp dom-*, engine fillFormStandard).

Form chỉ có block người nộp/người dự tuyển — chi tiết dự tuyển nằm trong Phiếu Mẫu 01 đính kèm.
"""

FIELDS: list[dict] = [
    {"name": "Nguoi_HoTen", "desc": "Họ và tên người dự tuyển. Lấy từ CCCD hoặc Phiếu đăng ký dự tuyển "
        "(Mẫu 01). Ghi IN HOA."},
    {"name": "Nguoi_NgaySinh", "desc": "Ngày sinh người dự tuyển, dd/mm/yyyy — CCCD / Phiếu Mẫu 01."},
    {"name": "Nguoi_GioiTinh", "desc": 'Giới tính người dự tuyển: "Nam" hoặc "Nữ".'},
    {"name": "Nguoi_DanToc", "desc": "Dân tộc người dự tuyển (vd 'Kinh', 'Tày', 'Thái'...) — lấy ở Phiếu Mẫu 01."},
    {"name": "Nguoi_SoDinhDanh", "desc": "Số CCCD/CMND người dự tuyển; đọc CCCD (mặt trước/MRZ) hoặc Phiếu "
        "Mẫu 01. Chỉ chữ số."},
    {"name": "Nguoi_NgayCap", "desc": "Ngày cấp CCCD/CMND (mặt sau) hoặc Phiếu Mẫu 01, dd/mm/yyyy."},
    {"name": "Nguoi_NoiCap",
     "desc": 'Nơi cấp CCCD/CMND. "CỤC TRƯỞNG CỤC CẢNH SÁT..." → "Cục Cảnh sát quản lý hành chính về '
             'trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → "Bộ Công an". CCCD gắn chip do Bộ Công an cấp.'},
    {"name": "Nguoi_ThuongTru",
     "desc": "Nơi thường trú / hộ khẩu người dự tuyển, object {quocGia,tinh,xa,diaChi}. ƯU TIÊN theo NƠI "
             "THƯỜNG TRÚ trên CCCD/Phiếu (KHÁC quê quán). tinh='Tỉnh/Thành phố …', xa=phường/xã (tên MỚI sau "
             "sáp nhập), diaChi=số nhà/đường/tổ/thôn/xóm."},
    {"name": "Nguoi_DiDong", "desc": "Số điện thoại di động người dự tuyển — Phiếu Mẫu 01. Chỉ chữ số."},
    {"name": "Nguoi_Email", "desc": "Email người dự tuyển — Phiếu Mẫu 01 nếu có."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Nguoi_NgaySinh", "Nguoi_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
COMPACT_COMP_BY_NAME["Nguoi_ThuongTru"] = "x-select-area"

# ---- UI eForm Lai Châu (CongDan_*) — comp dom-* cho engine fillFormStandard ----
# ngày dùng dom-input (gõ thẳng dd/mm/yyyy vào datepicker); tỉnh/xã/dân tộc/quốc gia là dropdown
# Semantic UI ẩn (<select display:none>) → dom-select.
UI_COMP_BY_NAME = {
    "CongDan_tenCongDan": "dom-input",
    "CongDan_ngaySinhCongDan": "dom-input",
    "CongDan_gioiTinhCongDan": "dom-select",
    "CongDan_danTocCongDan": "dom-select",
    "CongDan_soCmnd": "dom-input",
    "CongDan_ngayCapCmnd": "dom-input",
    "CongDan_noiCapCmnd": "dom-input",
    "CongDan_maTinhThanh": "dom-select",     # Tỉnh/TP (theo nơi thường trú).
    "CongDan_maPhuongXa": "dom-select",      # Phường/Xã (load qua API sau khi chọn tỉnh).
    "CongDan_diaChi": "dom-input",           # Số nhà/đường/tổ/thôn.
    "CongDan_diDong": "dom-input",
    "CongDan_email": "dom-input",
    "CongDan_maDMQuocGia": "dom-select",     # Quốc gia = Việt Nam.
    "CongDan_soCCCD": "dom-input",
    "CongDan_noiOHienTai": "dom-input",      # Địa chỉ nhận thông báo (chuỗi đầy đủ).
    "CongDan_diaChiThuongTru": "dom-input",  # Địa chỉ thường trú (chuỗi đầy đủ).
}

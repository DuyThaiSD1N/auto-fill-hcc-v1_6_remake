"""Compact schema cho "Cấp GCN đủ điều kiện hoạt động điểm cung cấp dịch vụ trò chơi điện tử công
cộng" (cổng Bộ VHTTDL — Angular Material `liz-*`).

LLM chỉ trả FACT nguồn: 1 NGƯỜI (chủ điểm cá nhân, từ CCCD + Đơn 51a) + 1 HỘ KINH DOANH (từ Giấy
phép kinh doanh). `mapper.enrich` suy ra tất định các ô UI theo (section, mat-label).

Hợp đồng comp cho engine fill-liz.js: mỗi field UI có {name = <mat-label>, section = <group-header>,
comp}. comp: `liz-input` (text), `liz-date` (datepicker dd/mm/yyyy), `liz-select` (mat-select overlay).
Nhãn LẶP giữa các section (Ngày sinh/Số điện thoại/Ngày cấp/Nơi cấp/Địa chỉ...) → PHẢI có `section`
để engine khớp đúng ô.
"""

FIELDS: list[dict] = [
    # ---- NGƯỜI (chủ điểm cá nhân = người nộp = người được giải quyết = chủ hộ KD) ----
    {"name": "Nguoi_HoTen", "desc": "Họ và tên chủ điểm (cá nhân). Lấy từ CCCD (Họ và tên) hoặc Đơn 51a "
        "(Phần 1, mục 1 'Họ và tên') / chủ hộ trên Giấy phép kinh doanh."},
    {"name": "Nguoi_NgaySinh", "desc": "Ngày sinh, dd/mm/yyyy — lấy từ CCCD (Đơn 51a không có ô ngày sinh)."},
    {"name": "Nguoi_SoDinhDanh", "desc": "Số định danh/CCCD của chủ điểm; đọc mặt trước hoặc MRZ mặt sau CCCD, "
        "hoặc 'Số định danh cá nhân' trên Đơn 51a. Chỉ chữ số."},
    {"name": "Nguoi_NgayCapCccd", "desc": "Ngày cấp CCCD (mặt sau) hoặc 'Cấp ngày' trên Đơn 51a, dd/mm/yyyy."},
    {"name": "Nguoi_NoiCapCccd",
     "desc": 'Nơi cấp CCCD/CMND. ƯU TIÊN "Nơi cấp" ghi trên Đơn 51a nếu có (vd "Bắc Ninh"); nếu không có '
             'thì lấy từ mặt sau CCCD ("CỤC TRƯỞNG CỤC CẢNH SÁT..." → "Cục Cảnh sát quản lý hành chính về '
             'trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → "Bộ Công an").'},
    {"name": "Nguoi_ThuongTru",
     "desc": "Nơi thường trú/địa chỉ liên hệ của chủ điểm, object {tinh,xa,diaChi}. ƯU TIÊN tên phường/xã "
             "MỚI trong Đơn 51a / Giấy phép kinh doanh (sau sáp nhập); CCCD 2021 ghi tên CŨ (vd Xã Ngũ Thái) "
             "thì bỏ, lấy tên mới. tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=tổ dân phố/khu phố/số nhà."},
    {"name": "Nguoi_DienThoai", "desc": "Số điện thoại liên hệ — lấy từ Đơn 51a (mục Điện thoại) hoặc Giấy "
        "phép kinh doanh. Chỉ chữ số. Không có trên CCCD."},

    # ---- HỘ KINH DOANH (từ Giấy phép kinh doanh = GCN đăng ký hộ kinh doanh) ----
    {"name": "HoKD_MaSo", "desc": "Mã số hộ kinh doanh (= mã số thuế) trên Giấy phép kinh doanh. Chỉ chữ số."},
    {"name": "HoKD_CoQuanCap", "desc": "Cơ quan cấp Giấy chứng nhận đăng ký hộ kinh doanh (vd 'Phòng Kinh "
        "tế, Hạ tầng và Đô thị - UBND Phường Song Liễu' hoặc 'UBND Phường …')."},
    {"name": "HoKD_NgayDangKyLanDau", "desc": "Ngày đăng ký lần đầu ('Đăng ký lần đầu, ngày…') trên Giấy "
        "phép kinh doanh, dd/mm/yyyy."},
    {"name": "HoKD_TenTiengViet", "desc": "Tên hộ kinh doanh viết bằng tiếng Việt trên Giấy phép kinh doanh "
        "(vd 'HỘ KINH DOANH NGUYỄN VĂN A …')."},
    {"name": "HoKD_DienThoai", "desc": "Số điện thoại của hộ kinh doanh trên Giấy phép kinh doanh (nếu có). "
        "Chỉ chữ số. Nếu GPKD không ghi thì để trống (mapper dùng chung với điện thoại người nộp)."},
    {"name": "HoKD_TruSo",
     "desc": "Địa chỉ TRỤ SỞ hộ kinh doanh trên Giấy phép kinh doanh, object {tinh,xa,diaChi}. tinh='Tỉnh …', "
             "xa=phường/xã, diaChi=thôn/tổ/số nhà. Đây là địa điểm kinh doanh, có thể KHÁC nơi thường trú."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _n in ("Nguoi_NgaySinh", "Nguoi_NgayCapCccd", "HoKD_NgayDangKyLanDau"):
    COMPACT_COMP_BY_NAME[_n] = "x-date"
for _n in ("Nguoi_ThuongTru", "HoKD_TruSo"):
    COMPACT_COMP_BY_NAME[_n] = "x-select-area"

# ---- UI fields cho engine fill-liz.js — khớp (section, mat-label) ----
# section = text trong .group-header; name = text trong <mat-label>.
S_NOP = "Thông tin người nộp hồ sơ"
S_GQ = "Thông tin người được giải quyết"
S_DN = "Thông tin doanh nghiệp"

# comp: liz-input | liz-date | liz-select. Danh sách (section, label, comp) khớp DOM thật.
UI_FIELDS: list[tuple[str, str, str]] = [
    # Phần II — người nộp (Tên + CMND là disabled/tự điền từ tài khoản → bỏ).
    (S_NOP, "Ngày sinh", "liz-date"),
    (S_NOP, "Số điện thoại", "liz-input"),
    (S_NOP, "Ngày cấp", "liz-date"),
    (S_NOP, "Nơi cấp", "liz-input"),
    (S_NOP, "Địa chỉ", "liz-input"),
    (S_NOP, "Địa chỉ hành chính", "liz-select"),
    # Phần III — người được giải quyết (trùng người nộp).
    (S_GQ, "Tên người / Tên đơn vị được giải quyết", "liz-input"),
    (S_GQ, "Ngày sinh", "liz-date"),
    (S_GQ, "CMND/Hộ chiếu", "liz-input"),
    (S_GQ, "Số điện thoại", "liz-input"),
    (S_GQ, "Ngày cấp", "liz-date"),
    (S_GQ, "Nơi cấp", "liz-input"),
    (S_GQ, "Địa chỉ", "liz-input"),
    (S_GQ, "Địa chỉ hành chính", "liz-select"),
    # Phần IV — doanh nghiệp/hộ kinh doanh (từ GPKD).
    (S_DN, "Mã số thuế", "liz-input"),
    (S_DN, "Cơ quan cấp", "liz-input"),
    (S_DN, "Đăng ký lần đầu", "liz-date"),
    (S_DN, "Tên tiếng việt", "liz-input"),
    (S_DN, "Điện thoại", "liz-input"),
    (S_DN, "Địa chỉ trụ sở - Tỉnh/TP", "liz-input"),
    (S_DN, "Địa chỉ trụ sở - Xã", "liz-input"),
    (S_DN, "Địa chỉ chi tiết trụ sở", "liz-input"),
    (S_DN, "Số CCCD người đại diện pháp luật", "liz-input"),
    (S_DN, "Tên người đại diện pháp luật", "liz-input"),
    (S_DN, "Địa chỉ người đại diện pháp luật", "liz-input"),
]

# tra cứu comp theo (section, label)
COMP_BY_UI = {(s, l): c for s, l, c in UI_FIELDS}

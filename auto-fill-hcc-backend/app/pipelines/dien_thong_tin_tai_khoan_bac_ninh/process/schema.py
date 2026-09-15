"""Compact schema "[Bắc Ninh] Điền thông tin tài khoản" (trang hoàn thiện tài khoản VNeID SSO).

Cổng dichvucong.bacninh.gov.vn/web/guest/vneidsso — Liferay portlet prefix
`_org_bn_taikhoan_sso_vneid_INSTANCE_mzdq_<key>`. KHÁC eForm hoso_noptructuyen: ô khớp theo NAME
SUFFIX `_<key>` (engine FE `fillAccountBacNinh` trong fill-bacninh.js).

LLM chỉ trả FACT NGUỒN từ CCCD (hoặc tờ khai/GCN có ghi thông tin CCCD của đúng người). `mapper.enrich`
suy ra UI field + default (loại định danh = Căn cước công dân, quốc tịch = Việt Nam) + remap tỉnh/xã.

CHỌN ĐÚNG NGƯỜI: khớp context (Họ tên + Số định danh đã prefill từ VNeID) — xem prompt/runner.
"""

FIELDS: list[dict] = [
    {"name": "HoTen",
     "desc": "Họ và tên đầy đủ của CHỦ TÀI KHOẢN (người đã đăng nhập VNeID — khớp Họ tên/Số định danh ở "
             "context). IN HOA theo CCCD. Nếu giấy tờ có nhiều người, lấy ĐÚNG người khớp số định danh."},
    {"name": "GioiTinh", "desc": "Giới tính chủ tài khoản, chỉ 'Nam' hoặc 'Nữ' (theo CCCD). Bỏ nếu không rõ."},
    {"name": "NgaySinh", "desc": "Ngày sinh chủ tài khoản, dd/mm/yyyy (mặt trước CCCD). Bỏ nếu chỉ có năm."},
    {"name": "SoCCCD",
     "desc": "Số định danh cá nhân / số CCCD của chủ tài khoản, 12 chữ số (mặt trước CCCD). PHẢI khớp Số "
             "định danh ở context. Chỉ chữ số."},
    {"name": "NgayCapCCCD", "desc": "Ngày cấp CCCD (mặt sau thẻ), dd/mm/yyyy. Bỏ nếu không đọc được."},
    {"name": "NoiCapCCCD",
     "desc": 'Nơi cấp CCCD. CCCD gắn chip cấp tập trung → "Cục Cảnh sát quản lý hành chính về trật tự xã '
             'hội"; thẻ căn cước mới ghi "BỘ CÔNG AN" → "Bộ Công an". Bỏ nếu không có (mapper tự mặc định).'},
    {"name": "QueQuan",
     "desc": "Quê quán chủ tài khoản — CHUỖI một dòng đúng như mục 'Quê quán' trên CCCD (vd 'Xã …, huyện …, "
             "tỉnh …'). KHÔNG nhầm với nơi thường trú. Bỏ nếu không có."},
    {"name": "ThuongTru",
     "desc": "Nơi thường trú chủ tài khoản — OBJECT {quocGia,tinh,xa,diaChi}. Lấy ở mục 'Nơi thường trú' của "
             "CCCD (mặt sau) hoặc dòng thường trú trong tờ khai. Giữ đủ số nhà/thôn/xóm + phường/xã + tỉnh. "
             "Dùng cho dropdown Tỉnh/Xã + ô địa chỉ chi tiết."},
    {"name": "DiaChiHienTai",
     "desc": "Nơi ở HIỆN TẠI — OBJECT {quocGia,tinh,xa,diaChi}. CHỈ điền khi giấy tờ ghi RÕ mục 'Nơi ở hiện "
             "tại' / 'Chỗ ở hiện nay' KHÁC nơi thường trú. TUYỆT ĐỐI KHÔNG copy từ thường trú. Bỏ nếu không có."},
    {"name": "SoDienThoai",
     "desc": "Số điện thoại chủ tài khoản NẾU giấy tờ (tờ khai) ghi rõ. Chỉ chữ số. CCCD không có → bỏ."},
    {"name": "Email", "desc": "Thư điện tử chủ tài khoản nếu giấy tờ ghi rõ. Không tự tạo. Bỏ nếu không có."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _d in ("NgaySinh", "NgayCapCCCD"):
    COMPACT_COMP_BY_NAME[_d] = "x-date"
for _a in ("ThuongTru", "DiaChiHienTai"):
    COMPACT_COMP_BY_NAME[_a] = "x-select-area"

# ============ UI field (fill-bacninh.js → fillAccountBacNinh) — name = <Key> (portlet suffix) ============
# Khối định danh chính
K_HOTEN = "hoTen"
K_GIOITINH = "gioiTinhId"          # select: Chưa có thông tin / Giới tính Nam / Giới tính Nữ
K_LOAIDINHDANH = "loaiDinhDanh"    # select: Căn cước công dân / Chứng minh nhân dân / Số hộ chiếu / …
K_SODINHDANH = "soDinhDanh"        # = số CCCD (ô định danh chính)
K_NGAYCAP = "ngayCap"             # ngày cấp của định danh chính (= ngày cấp CCCD)
K_QUOCGIA = "quocGiaId"            # select quốc tịch → Việt Nam
K_NGAYSINH = "ngaySinh"
K_SDT = "soDienThoai"
K_EMAIL = "email"
# Địa chỉ thường trú (3 cấp)
K_TT_TINH = "thuongTrutinhThanhId"
K_TT_XA = "thuongTruphuongXaId"
K_TT_CHITIET = "thuongTru"
K_QUEQUAN = "queQuan"
# Địa chỉ hiện tại (chỉ khi có nguồn)
K_HT_TINH = "diaChiHienTaitinhThanhId"
K_HT_XA = "diaChiHienTaiphuongXaId"
K_HT_CHITIET = "diaChiHienTai"
# Khối giấy tờ CCCD (lặp lại số/ngày/nơi cấp)
K_SOCCCD = "soCCCD"
K_NGAYCAPCCCD = "ngayCapCCCD"
K_NOICAPCCCD = "noiCapCCCD"

UI_COMP_BY_NAME = {
    K_HOTEN: "bn-input",
    K_GIOITINH: "bn-select",
    K_LOAIDINHDANH: "bn-select",
    K_SODINHDANH: "bn-input",
    K_NGAYCAP: "bn-date",
    K_QUOCGIA: "bn-select",
    K_NGAYSINH: "bn-date",
    K_SDT: "bn-input",
    K_EMAIL: "bn-input",
    K_TT_TINH: "bn-select",
    K_TT_XA: "bn-select",
    K_TT_CHITIET: "bn-input",
    K_QUEQUAN: "bn-input",
    K_HT_TINH: "bn-select",
    K_HT_XA: "bn-select",
    K_HT_CHITIET: "bn-input",
    K_SOCCCD: "bn-input",
    K_NGAYCAPCCCD: "bn-date",
    K_NOICAPCCCD: "bn-input",
}

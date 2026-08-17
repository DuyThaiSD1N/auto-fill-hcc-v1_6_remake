"""Compact schema for "Đăng ký kết hôn CÓ YẾU TỐ NƯỚC NGOÀI".

Khác ket_hon nội địa: quốc tịch/nơi cư trú KHÔNG mặc định Việt Nam. Mỗi bên có thể là người
nước ngoài (giấy tờ nước ngoài) → phải đọc quốc tịch thật + quốc gia/địa chỉ cư trú thật.
"""

FIELDS: list[dict] = [
    # Giấy tờ tùy thân bên nam (CCCD Việt Nam HOẶC giấy tờ nước ngoài: CMND/hộ chiếu nước ngoài).
    {"name": "CccdNam_HoTen", "desc": "Họ tên bên nam trên giấy tờ tùy thân (kể cả tên nước ngoài, giữ nguyên chữ in hoa)."},
    {"name": "CccdNam_SoDinhDanh", "desc": "Số giấy tờ tùy thân bên nam (số định danh CCCD 12 số, HOẶC số CMND/hộ chiếu nước ngoài); có thể đọc từ MRZ."},
    {"name": "CccdNam_NgaySinh", "desc": "Ngày sinh bên nam, dd/mm/yyyy."},
    {"name": "CccdNam_NgayCap", "desc": "Ngày cấp giấy tờ bên nam, dd/mm/yyyy. Giấy nước ngoài chỉ ghi 'Thời hạn hiệu lực'/'有效期限' dạng khoảng thì lấy MỐC ĐẦU (ngày bắt đầu hiệu lực)."},
    {"name": "CccdNam_NoiCap",
     "desc": 'Nơi cấp/cơ quan cấp giấy tờ bên nam GHI ĐÚNG như trên giấy tờ. CCCD VN mặt sau có '
             '"CỤC TRƯỞNG CỤC CẢNH SÁT..." → "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; '
             'thẻ Căn cước mới "BỘ CÔNG AN" → "Bộ Công an". Giấy tờ nước ngoài lấy nguyên cơ quan cấp '
             '(vd "Cục công an huyện Nguyên Dương").'},
    {"name": "CccdNam_DanToc", "desc": "Dân tộc BÊN NAM nếu giấy tờ/tờ khai có ghi (đối chiếu đúng người). Không có thì để trống."},
    {"name": "CccdNam_QuocTich", "desc": "Quốc tịch BÊN NAM — BẮT BUỘC đọc, KỂ CẢ nước ngoài (vd 'Trung Quốc', 'Hàn Quốc'). Giấy tờ nước ngoài → quốc tịch nước đó. KHÔNG mặc định 'Việt Nam'."},
    {"name": "CccdNam_TenGiayTo", "desc": "TÊN loại giấy tờ tùy thân bên nam KHI là giấy tờ NƯỚC NGOÀI (đọc theo tiêu đề, vd 'Chứng minh thư' cho thẻ 居民身份证 Trung Quốc, 'Hộ chiếu'). Giấy tờ Việt Nam thì bỏ trống."},
    {"name": "CccdNam_NoiCuTru",
     "desc": "Nơi cư trú BÊN NAM, object {quocGia,tinh,xa,diaChi}. quocGia = QUỐC GIA cư trú thật (vd 'Trung Quốc' nếu địa chỉ ở nước ngoài, 'Việt Nam' nếu ở VN). Với địa chỉ nước ngoài: đưa TOÀN BỘ địa chỉ vào diaChi, để trống tinh/xa nếu không tách được. Với VN: xa=tên phường/xã, tinh=tỉnh, diaChi=chi tiết."},
    {"name": "CccdNam_SoLanKetHon", "desc": "Số lần kết hôn BÊN NAM nếu tờ khai ghi rõ số. Số nguyên. Không có thì bỏ qua."},
    {"name": "CccdNam_TinhTrangHonNhan", "desc": "Tình trạng hôn nhân BÊN NAM — CHỈ khi có giấy nêu rõ tình trạng CỦA CHÍNH NGƯỜI ĐÓ (giấy xác nhận/trình bày tình trạng hôn nhân, cam đoan, tờ khai; đối chiếu đúng người). Trả 1 CATEGORY: 'chua_ket_hon' (chưa kết hôn), 'ly_hon' (đã ly hôn), 'goa' (vợ/chồng đã chết). KHÔNG suy diễn, KHÔNG trả 'đang có vợ/chồng'. Không có giấy của người đó thì bỏ trống."},

    # Giấy tờ tùy thân bên nữ.
    {"name": "CccdNu_HoTen", "desc": "Họ tên bên nữ trên giấy tờ tùy thân (kể cả tên nước ngoài)."},
    {"name": "CccdNu_SoDinhDanh", "desc": "Số giấy tờ tùy thân bên nữ (số định danh CCCD 12 số HOẶC số CMND/hộ chiếu nước ngoài)."},
    {"name": "CccdNu_NgaySinh", "desc": "Ngày sinh bên nữ, dd/mm/yyyy."},
    {"name": "CccdNu_NgayCap", "desc": "Ngày cấp giấy tờ bên nữ, dd/mm/yyyy. Giấy nước ngoài chỉ ghi 'Thời hạn hiệu lực'/'有效期限' dạng khoảng thì lấy MỐC ĐẦU (ngày bắt đầu hiệu lực)."},
    {"name": "CccdNu_NoiCap",
     "desc": 'Nơi cấp/cơ quan cấp giấy tờ bên nữ GHI ĐÚNG như trên giấy tờ (VN: "Bộ Công an"/'
             '"Cục Cảnh sát quản lý hành chính về trật tự xã hội"; nước ngoài lấy nguyên cơ quan cấp).'},
    {"name": "CccdNu_DanToc", "desc": "Dân tộc BÊN NỮ nếu giấy tờ/tờ khai có ghi. Không có thì để trống."},
    {"name": "CccdNu_QuocTich", "desc": "Quốc tịch BÊN NỮ — BẮT BUỘC đọc, KỂ CẢ nước ngoài. KHÔNG mặc định 'Việt Nam'."},
    {"name": "CccdNu_TenGiayTo", "desc": "TÊN loại giấy tờ tùy thân bên nữ KHI là giấy tờ NƯỚC NGOÀI (vd 'Chứng minh thư', 'Hộ chiếu'). Giấy tờ Việt Nam thì bỏ trống."},
    {"name": "CccdNu_NoiCuTru",
     "desc": "Nơi cư trú BÊN NỮ, object {quocGia,tinh,xa,diaChi}. quocGia = QUỐC GIA cư trú thật. Nước ngoài → toàn bộ địa chỉ vào diaChi; VN → xa/tinh/diaChi như thường."},
    {"name": "CccdNu_SoLanKetHon", "desc": "Số lần kết hôn BÊN NỮ nếu tờ khai ghi rõ số. Số nguyên. Không có thì bỏ qua."},
    {"name": "CccdNu_TinhTrangHonNhan", "desc": "Tình trạng hôn nhân BÊN NỮ — CHỈ khi có giấy nêu rõ tình trạng CỦA CHÍNH NGƯỜI ĐÓ. Trả 'chua_ket_hon'/'ly_hon'/'goa'. KHÔNG suy diễn, KHÔNG trả 'đang có vợ/chồng'. Không có giấy của người đó thì bỏ trống."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("CccdNam_NgaySinh", "CccdNam_NgayCap", "CccdNu_NgaySinh", "CccdNu_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("CccdNam_NoiCuTru", "CccdNu_NoiCuTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

UI_COMP_BY_NAME = {
    # Bên nam.
    "HoTenBenNam": "x-input",
    "SoDinhDanh_BenNam": "x-input",
    "SoGiayToDinhDanh_BenNam": "x-input",
    "LoaiGiayToDinhDanh_BenNam": "x-select",
    # Ô tên giấy tờ (hiện khi chọn loại "Giấy tờ khác..."): form thật đặt name TenGiayTo_*
    # widget x-select-area (đối chiếu thongtin/kết hôn nước ngoài) — không phải NhapTenGiayTo raw.
    "TenGiayTo_BenNam": "x-select-area",
    "NgaySinhBenNam": "x-date",
    "NgayCapDD_BenNam": "x-date",
    "NoiCapDD_BenNam": "x-input",
    "DanTocBenNam": "x-select",
    "QuocTichBenNam": "x-select",
    "LoaiCuTru_BenNam": "x-select",
    "NoiCuTru_BenNam": "x-radio",
    "NoiCuTru_BenNam_TrongNuoc": "x-select-area",
    "NoiCuTru_BenNam_NuocNgoai": "x-select-area",
    "SoLanKetHon_BenNam": "x-input-number",  # form thật dùng widget x-input-number
    "LoaiTinhTrangHonNhan_BenNam": "x-select",
    # Bên nữ.
    "HoTenBenNu": "x-input",
    "SoDinhDanh_BenNu": "x-input",
    "SoGiayToDinhDanh_BenNu": "x-input",
    "LoaiGiayToDinhDanh_BenNu": "x-select",
    "TenGiayTo_BenNu": "x-select-area",
    "NgaySinhBenNu": "x-date",
    "NgayCapDD_BenNu": "x-date",
    "NoiCapDD_BenNu": "x-input",
    "DanTocBenNu": "x-select",
    "QuocTichBenNu": "x-select",
    "LoaiCuTru_BenNu": "x-select",
    "NoiCuTru_BenNu": "x-radio",
    "NoiCuTru_BenNu_TrongNuoc": "x-select-area",
    "NoiCuTru_BenNu_NuocNgoai": "x-select-area",
    "SoLanKetHon_BenNu": "x-input-number",
    "LoaiTinhTrangHonNhan_BenNu": "x-select",
    # Mặc định chung của form (mapper phát kèm cờ default → FE tô viền vàng).
    "loaiDangKy": "x-radio",
    "CapBanSao": "x-radio",
}

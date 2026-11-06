"""Facts nguồn cho "Khánh Hòa - Xác nhận tiếp tục sử dụng đất nông nghiệp" (1.013947).

Đi từ link kê khai DVCQG (chỉ chọn Tỉnh, bấm thẻ Chi nhánh VPĐK đất đai theo xã) sang cổng iGate Khánh Hòa: trang "Chọn
trường hợp giải quyết" (quy trình 1.013947-1.1…) rồi form Form.io CÙNG TEMPLATE ba khối với các thủ tục đất đai Khánh Hòa
(file mapping trùng khít tập data[...]) nên dùng chung UI_COMP_BY_NAME.

Facts theo NGƯỜI (không theo vai) — mapper phân vai đúng file mapping: người nộp = người THỨ NHẤT đứng Đơn (hoặc bên được
ủy quyền nếu có văn bản ủy quyền), chủ hồ sơ = người THỨ HAI (một người thì chính người đó).

Nguồn: Đơn xin xác nhận lại thời hạn sử dụng đất nông nghiệp (Mẫu số 09, thường VIẾT TAY, có khi scan xoay ngang) — họ
tên, ngày sinh, số CCCD MỚI, địa chỉ liên hệ + điện thoại, thửa đất, nội dung đề nghị; Giấy chứng nhận (mẫu cũ ghi CMND 9
số kèm ngày cấp/nơi cấp của CMND, năm sinh, địa danh trước sắp xếp); Phiếu đo đạc chỉnh lý thửa đất (địa chỉ thửa đất theo
địa danh mới, số thửa/tờ bản đồ mới). Bẫy: ngày cấp/nơi cấp in trên GCN là của CMND CŨ, không được ghép với số CCCD mới.
"""

from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.process.schema import UI_COMP_BY_NAME  # noqa: F401

_AREA = "object {quocGia,tinh,xa,chiTietDuoiXa}"


def _person(prefix: str, who: str) -> list[dict]:
    return [
        {
            "name": f"{prefix}_HoTen",
            "desc": f"Họ tên {who}. Chỉ lấy HỌ TÊN (bỏ 'Ông'/'Bà', 'sinh ngày…', 'CCCD số…' viết liền sau), giữ nguyên dấu; "
            "đối chiếu tên in trên Giấy chứng nhận/Phiếu đo đạc khi chữ viết tay khó đọc.",
        },
        {
            "name": f"{prefix}_NgaySinh",
            "desc": f"Ngày sinh ĐẦY ĐỦ của {who}, dd/mm/yyyy: Đơn 'sinh ngày …' -> thẻ CCCD. Giấy chứng nhận chỉ ghi 'Sinh "
            "năm' -> không dùng; chỉ có năm thì bỏ field.",
        },
        {
            "name": f"{prefix}_SoDinhDanh",
            "desc": f"Số CCCD/căn cước (12 số) của {who}, chỉ chữ số: Đơn 'CCCD số …' -> thẻ CCCD. CHỈ khi không có số "
            "CCCD nào mới lấy số CMND cũ (9 số) in trên Giấy chứng nhận.",
        },
        {
            "name": f"{prefix}_NgayCap",
            "desc": f"Ngày cấp CHÍNH giấy tờ có số ở {prefix}_SoDinhDanh, dd/mm/yyyy (thẻ CCCD mặt sau, hoặc 'cấp ngày' "
            "viết ngay sau đúng số đó). Giấy chứng nhận ghi 'Số CMND: … cấp ngày …' là ngày cấp CMND CŨ: chỉ dùng khi "
            f"{prefix}_SoDinhDanh chính là số CMND đó; số CCCD lấy từ Đơn mà Đơn không ghi ngày cấp thì BỎ field.",
        },
        {
            "name": f"{prefix}_NoiCap",
            "desc": f"Nơi cấp CHÍNH giấy tờ có số ở {prefix}_SoDinhDanh (cùng điều kiện như ngày cấp). 'tại Công an tỉnh …' "
            "trên Giấy chứng nhận là nơi cấp CMND CŨ.",
        },
        {
            "name": f"{prefix}_DiaChi",
            "desc": f"Nơi thường trú của {who}, {_AREA}: thẻ CCCD -> 'Địa chỉ thường trú' mục I của Giấy chứng nhận (địa "
            "danh cũ). KHÔNG lấy địa chỉ thửa đất.",
        },
    ]


FIELDS: list[dict] = [
    {
        "name": "NSD_LoaiChuThe",
        "desc": '"Tổ chức" nếu người sử dụng đất đứng Đơn là công ty/doanh nghiệp/HTX/cơ quan; "Cá nhân" nếu là người.',
    },
    *_person("NSD1", "NGƯỜI SỬ DỤNG ĐẤT THỨ NHẤT ghi ở Đơn mục '1. Người sử dụng đất' (người đứng tên đầu; Giấy chứng "
             "nhận mục I ghi trước)"),
    *_person("NSD2", "NGƯỜI SỬ DỤNG ĐẤT THỨ HAI cùng đứng Đơn mục 1 (vợ/chồng, 'Bà …' ở mục I Giấy chứng nhận); Đơn chỉ "
             "một người thì BỎ toàn bộ NSD2_*"),
    {
        "name": "Don_DiaChiLienHe",
        "desc": f"Địa chỉ ở Đơn mục '2. Địa chỉ liên hệ (điện thoại, email...)', {_AREA} — thường viết tay dạng '<số "
        "điện thoại> - <số nhà, đường> - phường X' (địa danh mới); bỏ phần số điện thoại. Không ghi địa chỉ thì bỏ field.",
    },
    {"name": "Don_DienThoai", "desc": "Số điện thoại ở Đơn mục 2 'Địa chỉ liên hệ', chỉ chữ số (dùng chung cho người đứng "
                                      "Đơn)."},
    {"name": "Don_Email", "desc": "Email ở Đơn mục 2 nếu có ghi; để trống thì bỏ field."},
    {
        "name": "UyQuyen_HoTen",
        "desc": "CHỈ khi hồ sơ có văn bản/giấy ủy quyền cho cá nhân làm thủ tục: họ tên BÊN ĐƯỢC ỦY QUYỀN. Không có văn "
        "bản ủy quyền thì bỏ toàn bộ UyQuyen_*.",
    },
    {"name": "UyQuyen_NgaySinh", "desc": "Ngày sinh đầy đủ của bên được ủy quyền, dd/mm/yyyy."},
    {"name": "UyQuyen_SoDinhDanh", "desc": "Số CCCD của bên được ủy quyền, chỉ chữ số."},
    {"name": "UyQuyen_NgayCap", "desc": "Ngày cấp CCCD của bên được ủy quyền (cùng giấy tờ với số), dd/mm/yyyy."},
    {"name": "UyQuyen_NoiCap", "desc": "Nơi cấp CCCD của bên được ủy quyền (cùng giấy tờ với số)."},
    {"name": "UyQuyen_DiaChi", "desc": f"Nơi thường trú của bên được ủy quyền, {_AREA}."},
    {"name": "UyQuyen_DienThoai", "desc": "Số điện thoại của bên được ủy quyền nếu văn bản có ghi, chỉ chữ số."},
    {
        "name": "Don_NoiDungDeNghi",
        "desc": "Chép NGUYÊN VĂN mục '4. Nội dung đề nghị xác nhận lại thời hạn sử dụng đất' của Đơn (vd 'đến ngày 15 "
        "tháng 10 năm 2063. Cấp đổi sổ, …'). Mục trống thì bỏ field, không bịa.",
    },
    {
        "name": "ThuaDat_SoThua",
        "desc": "Số thửa THEO GIẤY CHỨNG NHẬN: GCN 'Thửa đất số' -> Đơn '3.1. Thửa đất số' -> Phiếu đo đạc dòng 'Thửa đất "
        "theo GCN số'. Chỉ lấy số.",
    },
    {
        "name": "ThuaDat_SoTo",
        "desc": "Số tờ bản đồ THEO GIẤY CHỨNG NHẬN: GCN 'Tờ bản đồ số' -> Đơn '3.2. Tờ bản đồ số' -> Phiếu đo đạc dòng "
        "'Thửa đất theo GCN số …; tờ bản đồ số'. Chỉ lấy số.",
    },
    {
        "name": "ThuaDat_SoThuaMoi",
        "desc": "Số thửa theo bản đồ địa chính MỚI ghi trên Phiếu đo đạc (dòng 'Thửa đất số' kèm tên phường mới), chỉ khi "
        "khác số theo GCN. Không có thì bỏ.",
    },
    {
        "name": "ThuaDat_SoToMoi",
        "desc": "Số tờ bản đồ MỚI ghi trên Phiếu đo đạc (cùng dòng với số thửa mới), chỉ khi khác số theo GCN. Không có thì "
        "bỏ.",
    },
    {
        "name": "ThuaDat_DiaChi",
        "desc": f"ĐỊA CHỈ THỬA ĐẤT, {_AREA}, xa là phường/xã HIỆN HÀNH: Phiếu đo đạc '2. Địa chỉ thửa đất' -> Đơn '3.7. "
        "Địa điểm thửa đất' -> Giấy chứng nhận 'Địa chỉ thửa đất' (địa danh cũ). KHÔNG lấy nơi thường trú của người.",
    },
    {
        "name": "ThuaDat_DiaChiDayDu",
        "desc": "Chép NGUYÊN VĂN dòng '2. Địa chỉ thửa đất' của Phiếu đo đạc (vd 'Số 1 Đường A, phường Nam Nha Trang (P. "
        "Phước Long cũ), tỉnh Khánh Hòa'); không có Phiếu đo đạc thì dòng địa chỉ thửa đất của Giấy chứng nhận.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _prefix in ("NSD1", "NSD2", "UyQuyen"):
    COMPACT_COMP_BY_NAME[f"{_prefix}_NgaySinh"] = "x-date"
    COMPACT_COMP_BY_NAME[f"{_prefix}_NgayCap"] = "x-date"
    COMPACT_COMP_BY_NAME[f"{_prefix}_DiaChi"] = "x-select-area"
for _name in ("Don_DiaChiLienHe", "ThuaDat_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

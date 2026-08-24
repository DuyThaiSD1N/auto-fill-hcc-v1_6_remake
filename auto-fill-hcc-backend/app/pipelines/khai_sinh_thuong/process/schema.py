"""Compact schema for regular "Đăng ký khai sinh" legacy e-form.

The LLM returns only OCR-derived facts. UI defaults, duplicate fields and
legacy x-* field names are derived in Python.

Hồ sơ có thể gồm 3 loại CCCD:
  - CccdNam_*      : CCCD giới tính Nam → cha (trường hợp thông thường).
  - CccdNu_*       : CCCD giới tính Nữ → mẹ (trường hợp thông thường).
  - CccdChuThe_*   : CCCD của chính NGƯỜI ĐƯỢC ĐĂNG KÝ KHAI SINH khi họ còn sống và
                     đã có CCCD (đăng ký muộn). LLM gán vào nhóm này khi năm sinh trên
                     CCCD trẻ hơn đáng kể so với tuổi cha/mẹ bình thường HOẶC khi tờ
                     khai ghi rõ người được đăng ký khai sinh chính là người có CCCD đó.
                     Giới tính của CccdChuThe_* quyết định cha/mẹ còn lại thuộc nhóm nào.
"""

FIELDS: list[dict] = [
    # Child facts from GIAY CHUNG SINH (trẻ sơ sinh, không có CCCD).
    {"name": "Gcs_HoTenCon", "desc": 'Tên con từ mục "Dự định đặt tên con là" trên giấy chứng sinh.'},
    {"name": "Gcs_NgaySinhCon", "desc": "Ngày sinh con trên giấy chứng sinh, dd/mm/yyyy."},
    {"name": "Gcs_GioiTinhCon", "desc": 'Giới tính con: "Nam" hoặc "Nữ".'},
    {"name": "Gcs_DanTocCon", "desc": "Dân tộc con trên giấy chứng sinh."},
    {"name": "Gcs_NoiSinh", "desc": "Nơi sinh con trên giấy chứng sinh, object {quocGia,tinh,xa,diaChi}; diaChi là cơ sở y tế."},

    # Thông tin người được đăng ký khai sinh khi HỌ CHÍNH LÀ NGƯỜI CÒN SỐNG CÓ CCCD
    # (đăng ký muộn / quá hạn). Nhóm này THAY THẾ Gcs_* khi không có giấy chứng sinh.
    {"name": "CccdChuThe_HoTen", "desc": "Họ tên trên CCCD của chính người được đăng ký khai sinh (đăng ký muộn, còn sống)."},
    {"name": "CccdChuThe_SoDinhDanh", "desc": "Số định danh trên CCCD chủ thể được đăng ký."},
    {"name": "CccdChuThe_NgaySinh", "desc": "Ngày sinh trên CCCD chủ thể, dd/mm/yyyy."},
    {"name": "CccdChuThe_GioiTinh", "desc": 'Giới tính trên CCCD chủ thể: "Nam" hoặc "Nữ".'},
    {"name": "CccdChuThe_DanToc", "desc": "Dân tộc trên CCCD chủ thể, chỉ khi giấy tờ ghi rõ."},
    {"name": "CccdChuThe_QuocTich", "desc": "Quốc tịch trên CCCD chủ thể, chỉ trả nếu ghi rõ hoặc khác Việt Nam."},
    {"name": "CccdChuThe_QueQuan", "desc": "Quê quán trên CCCD chủ thể, object {quocGia,tinh,xa,diaChi}."},
    {"name": "CccdChuThe_NoiCuTru", "desc": "Địa chỉ thường trú trên CCCD chủ thể, object {quocGia,tinh,xa,diaChi}."},
    {"name": "CccdChuThe_NgayCap", "desc": "Ngày cấp CCCD chủ thể, dd/mm/yyyy."},
    {"name": "CccdChuThe_NoiCap", "desc": "Nơi cấp CCCD chủ thể."},

    # Father facts from CCCD/CMND Nam.
    {"name": "CccdNam_HoTen", "desc": "Họ tên trên CCCD/CMND giới tính Nam. Không lấy từ giấy chứng sinh."},
    {"name": "CccdNam_SoDinhDanh", "desc": "Số định danh/CCCD trên CCCD Nam, 12 số; có thể đọc từ MRZ mặt sau."},
    {"name": "CccdNam_NgayCap", "desc": "Ngày cấp CCCD Nam, dd/mm/yyyy. Bắt buộc cố đọc từ mặt sau CCCD."},
    {
        "name": "CccdNam_NoiCap",
        "desc": (
            "Nơi cấp CCCD Nam từ mặt sau. Nếu OCR thấy CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ "
            'HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI thì trả "Cục Cảnh sát quản lý hành chính về trật tự xã hội".'
        ),
    },
    {"name": "CccdNam_NgaySinh", "desc": "Ngày sinh trên CCCD Nam, dd/mm/yyyy."},
    {"name": "CccdNam_DanToc", "desc": "Dân tộc trên giấy tờ Nam chỉ khi chính giấy tờ Nam ghi rõ; CCCD gắn chip thường không có."},
    {"name": "CccdNam_QuocTich", "desc": "Quốc tịch trên CCCD Nam chỉ trả nếu giấy tờ ghi rõ hoặc khác Việt Nam."},
    {"name": "CccdNam_QueQuan", "desc": "Quê quán/nguyên quán trên CCCD Nam, object {quocGia,tinh,xa,diaChi} nếu có."},
    {"name": "CccdNam_NoiDangKyKhaiSinh", "desc": "Nơi đăng ký khai sinh trên thẻ CĂN CƯỚC mới (dòng 'Nơi đăng ký khai sinh'/'Place of birth'), object {quocGia,tinh,xa,diaChi}. CHỈ khi thẻ là CĂN CƯỚC mới CÓ dòng này; thẻ CCCD cũ có 'Quê quán' thì không có field này."},
    {"name": "CccdNam_NoiCuTru_TrongNuoc", "desc": "Địa chỉ cư trú/thường trú trên CCCD Nam, object {quocGia,tinh,xa,diaChi}."},

    # Mother facts from CCCD/CMND Nu.
    {"name": "CccdNu_HoTen", "desc": "Họ tên trên CCCD/CMND giới tính Nữ. Không lấy từ giấy chứng sinh."},
    {"name": "CccdNu_SoDinhDanh", "desc": "Số định danh/CCCD trên CCCD Nữ, 12 số; có thể đọc từ MRZ mặt sau."},
    {"name": "CccdNu_NgayCap", "desc": "Ngày cấp CCCD Nữ, dd/mm/yyyy. Bắt buộc cố đọc từ mặt sau CCCD."},
    {
        "name": "CccdNu_NoiCap",
        "desc": (
            "Nơi cấp CCCD Nữ từ mặt sau. Nếu OCR thấy CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ "
            'HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI thì trả "Cục Cảnh sát quản lý hành chính về trật tự xã hội".'
        ),
    },
    {"name": "CccdNu_NgaySinh", "desc": "Ngày sinh trên CCCD Nữ, dd/mm/yyyy."},
    {"name": "CccdNu_DanToc", "desc": "Dân tộc trên giấy tờ Nữ chỉ khi chính giấy tờ Nữ ghi rõ; CCCD gắn chip thường không có."},
    {"name": "CccdNu_QuocTich", "desc": "Quốc tịch trên CCCD Nữ chỉ trả nếu giấy tờ ghi rõ hoặc khác Việt Nam."},
    {"name": "CccdNu_NoiCuTru_TrongNuoc", "desc": "Địa chỉ cư trú/thường trú trên CCCD Nữ, object {quocGia,tinh,xa,diaChi}."},

    # Tờ khai đăng ký khai sinh (bản giấy) — thông tin bổ sung khi không có giấy chứng sinh.
    {"name": "TkKs_HoTenCon", "desc": "Họ tên người được đăng ký khai sinh trên tờ khai, nếu không có giấy chứng sinh."},
    {"name": "TkKs_NgaySinhCon", "desc": "Ngày sinh người được đăng ký trên tờ khai, dd/mm/yyyy."},
    {"name": "TkKs_GioiTinhCon", "desc": 'Giới tính người được đăng ký trên tờ khai: "Nam" hoặc "Nữ".'},
    {"name": "TkKs_DanTocCon", "desc": "Dân tộc người được đăng ký trên tờ khai."},
    {"name": "TkKs_NoiSinh", "desc": "Nơi sinh trên tờ khai, object {quocGia,tinh,xa,diaChi}."},
    {"name": "TkKs_QueQuan", "desc": "Quê quán người được đăng ký trên tờ khai, object {quocGia,tinh,xa,diaChi}."},
    {"name": "TkKs_HoTenCha", "desc": "Họ tên cha trên tờ khai (khi không có CCCD cha)."},
    {"name": "TkKs_NamSinhCha", "desc": "Năm sinh cha trên tờ khai, yyyy."},
    {"name": "TkKs_DanTocCha", "desc": "Dân tộc cha trên tờ khai."},
    {"name": "TkKs_SoDinhDanhCha", "desc": "Số CCCD/định danh cha từ dòng 'Giấy tờ tùy thân' trong mục cha trên tờ khai."},
    {
        "name": "TkKs_NoiCuTruCha",
        "desc": (
            "Nơi cư trú của CHA lấy ở dòng 'Nơi cư trú' NẰM TRONG mục cha của tờ khai, "
            "object {quocGia,tinh,xa,diaChi}. Nếu chỗ đó ghi 'Đã chết'/'Đã mất' thay cho địa chỉ "
            "thì trả nguyên cụm chữ đó vào diaChi và bỏ trống tinh/xa."
        ),
    },
    {"name": "TkKs_HoTenMe", "desc": "Họ tên mẹ trên tờ khai (khi không có CCCD mẹ)."},
    {"name": "TkKs_NamSinhMe", "desc": "Năm sinh mẹ trên tờ khai, yyyy."},
    {"name": "TkKs_DanTocMe", "desc": "Dân tộc mẹ trên tờ khai."},
    {"name": "TkKs_SoDinhDanhMe", "desc": "Số CCCD/định danh mẹ từ dòng 'Giấy tờ tùy thân' trong mục mẹ trên tờ khai."},
    {
        "name": "TkKs_NoiCuTruMe",
        "desc": (
            "Nơi cư trú của MẸ lấy ở dòng 'Nơi cư trú' NẰM TRONG mục mẹ của tờ khai, "
            "object {quocGia,tinh,xa,diaChi}. Nếu chỗ đó ghi 'Đã chết'/'Đã mất' thay cho địa chỉ "
            "thì trả nguyên cụm chữ đó vào diaChi và bỏ trống tinh/xa."
        ),
    },
    # Người yêu cầu từ tờ khai (khi không phải cha/mẹ — vd chị dâu, anh, em...).
    {"name": "TkKs_NycHoTen", "desc": "Họ tên người yêu cầu trên tờ khai (dòng 'Họ, chữ đệm, tên người yêu cầu')."},
    {"name": "TkKs_NycNgaySinh", "desc": "Ngày/năm sinh người yêu cầu trên tờ khai, dd/mm/yyyy hoặc yyyy."},
    {"name": "TkKs_NycSoDinhDanh", "desc": "Số CCCD/định danh người yêu cầu trên tờ khai."},
    {"name": "TkKs_NycNgayCapCccd", "desc": "Ngày cấp CCCD người yêu cầu trên tờ khai, dd/mm/yyyy."},
    {"name": "TkKs_NycNoiCuTru", "desc": "Nơi cư trú người yêu cầu trên tờ khai, object {quocGia,tinh,xa,diaChi}."},
    {
        "name": "TkKs_NycQuanHe",
        "desc": (
            "Đọc Ô TÍCH ở dòng '(5) Quan hệ với người được khai sinh' trên tờ khai: Bản Thân / Cha / "
            "Mẹ / Khác. Tích Khác thì lấy thêm chữ ghi kèm nếu có (vd 'Chị dâu', 'Anh', 'Em'). Trả "
            "ĐÚNG MỘT trong 'Bản Thân' | 'Cha' | 'Mẹ' | 'Khác' (hoặc kèm chữ ghi kèm khi tích Khác). "
            "Đọc dòng này BẤT KỂ người yêu cầu là ai (kể cả khi trùng cha/mẹ/chính người được khai "
            "sinh) — không suy ra từ chỗ khác, không bỏ field chỉ vì trùng vai cha/mẹ."
        ),
    },
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "Gcs_NgaySinhCon",
    "CccdChuThe_NgaySinh",
    "CccdChuThe_NgayCap",
    "CccdNam_NgayCap",
    "CccdNam_NgaySinh",
    "CccdNu_NgayCap",
    "CccdNu_NgaySinh",
    "TkKs_NgaySinhCon",
    "TkKs_NycNgaySinh",
    "TkKs_NycNgayCapCccd",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in (
    "Gcs_NoiSinh",
    "CccdChuThe_QueQuan",
    "CccdChuThe_NoiCuTru",
    "CccdNam_QueQuan",
    "CccdNam_NoiDangKyKhaiSinh",
    "CccdNam_NoiCuTru_TrongNuoc",
    "CccdNu_NoiCuTru_TrongNuoc",
    "TkKs_NoiSinh",
    "TkKs_QueQuan",
    "TkKs_NoiCuTruCha",
    "TkKs_NoiCuTruMe",
    "TkKs_NycNoiCuTru",
):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"


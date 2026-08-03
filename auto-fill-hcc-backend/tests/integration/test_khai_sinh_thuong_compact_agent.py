"""Compact agent đăng ký khai sinh thường: short facts -> legacy x-* UI fields."""

from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.khai_sinh_thuong.process import run as khai_sinh_thuong_process
from app.pipelines.khai_sinh_thuong.process import mapper
from app.pipelines.khai_sinh_thuong.process.prompt import EXTRA_RULES
from app.pipelines.khai_sinh_thuong.process.schema import FIELDS
from app.procedures.registry import get_pipeline, get_procedure


def test_khai_sinh_thuong_mapper_derives_legacy_fields():
    compact_fields = [
        {"name": "Gcs_HoTenCon", "value": "CHẺO MINH CHIẾN"},
        {"name": "Gcs_NgaySinhCon", "value": "17/09/2025"},
        {"name": "Gcs_GioiTinhCon", "value": "Nam"},
        {"name": "Gcs_DanTocCon", "value": "Dao"},
        {"name": "Gcs_NoiSinh", "value": {"quocGia": "Việt Nam", "tinh": "Lai Châu", "diaChi": "BỆNH VIỆN ĐA KHOA TỈNH"}},
        {"name": "CccdNam_HoTen", "value": "VŨ ĐÌNH THIẾT"},
        {"name": "CccdNam_SoDinhDanh", "value": "040203015844"},
        {"name": "CccdNam_NgayCap", "value": "02/07/2021"},
        {"name": "CccdNam_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
        {"name": "CccdNam_NgaySinh", "value": "26/04/2003"},
        {"name": "CccdNam_QueQuan", "value": {"quocGia": "Việt Nam", "tinh": "Nghệ An", "xa": "Tam Hợp", "diaChi": "Xóm Long Thành"}},
        {"name": "CccdNam_NoiCuTru_TrongNuoc", "value": {"quocGia": "Việt Nam", "tinh": "Nghệ An", "xa": "Tam Hợp", "diaChi": "Xóm Long Thành"}},
        {"name": "CccdNu_HoTen", "value": "PHẠM NGỌC THỦY"},
        {"name": "CccdNu_SoDinhDanh", "value": "012193000851"},
        {"name": "CccdNu_NgayCap", "value": "06/02/2024"},
        {"name": "CccdNu_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
        {"name": "CccdNu_NgaySinh", "value": "20/03/1993"},
        {"name": "CccdNu_NoiCuTru_TrongNuoc", "value": {"quocGia": "Việt Nam", "tinh": "Lai Châu", "diaChi": "Tổ 3"}},
    ]

    fields = mapper.enrich(compact_fields)
    values = {f["name"]: f["value"] for f in fields}

    assert values["LoaiDangKy"] == "1"
    assert values["nksLoaiKhaiSinh"] == "Đã xác định được cả cha lẫn mẹ"
    assert values["QuanHe"] == "ChaDe"

    assert values["HoVaTenC"] == "VŨ ĐÌNH THIẾT"
    assert values["SoDinhDanhC"] == "040203015844"
    assert values["SoGiayToDinhDanhC"] == "040203015844"
    assert values["NgayCapDDC"] == "02/07/2021"
    assert values["NoiCapDDC"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["nycNoiCuTru"] == "1"
    assert values["nycNoiCuTru_TrongNuoc"]["tinh"] == "Nghệ An"

    assert values["HoTenKS"] == "CHẺO MINH CHIẾN"
    assert values["NgaySinhChon"] == "17/09/2025"
    assert values["GioiTinhKS"] == "Nam"
    assert values["nksNoiSinh"] == "1"
    assert values["nksNoiSinh_TrongNuoc"]["diaChi"] == "BỆNH VIỆN ĐA KHOA TỈNH"
    assert values["nksQueQuan_TrongNuoc"]["xa"] == "Tam Hợp"

    assert values["HoTenChaKS"] == "VŨ ĐÌNH THIẾT"
    assert values["SoDinhDanhCha"] == "040203015844"
    assert values["SoGiayToDinhDanhCha"] == "040203015844"
    assert values["NgayCapDDCha"] == "02/07/2021"
    assert values["NoiCapDDCha"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"

    assert values["HoTenMeKS"] == "PHẠM NGỌC THỦY"
    assert values["SoDinhDanhMe"] == "012193000851"
    assert values["SoGiayToDinhDanhMe"] == "012193000851"
    assert values["NgayCapDDMe"] == "06/02/2024"
    assert values["NoiCapDDMe"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"


def test_khai_sinh_thuong_prompt_forbids_ui_fields():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "Gcs_* CHỈ lấy từ tài liệu có tiêu đề GIẤY CHỨNG SINH" in system_prompt
    assert "PHÂN VAI THEO NHÃN TỜ KHAI" in system_prompt
    assert "KHÔNG dùng CCCD của người được khai sinh" in system_prompt
    assert "Không trả field mặc định hoặc field UI" in system_prompt
    assert "HoVaTenC, SoDinhDanhC, HoTenKS" in system_prompt


def test_registry_uses_regular_birth_pipeline():
    proc = get_procedure("khai-sinh-dang-ky-thuong")

    assert proc["label"] == "Thủ tục đăng ký khai sinh"
    assert proc["hasAttachmentStep"] is True
    assert get_pipeline("khai-sinh-dang-ky-thuong") is khai_sinh_thuong_process


def test_khai_sinh_thuong_parent_residence_falls_back_to_declaration():
    """Cha/mẹ không nộp CCCD → lấy nơi cư trú từ đúng mục của mỗi người trên tờ khai."""
    compact_fields = [
        {"name": "Gcs_HoTenCon", "value": "NGUYEN VAN A"},
        {"name": "Gcs_NgaySinhCon", "value": "01/01/2025"},
        {"name": "TkKs_HoTenCha", "value": "NGUYEN VAN B"},
        {"name": "TkKs_NamSinhCha", "value": "1990"},
        {"name": "TkKs_NoiCuTruCha", "value": {"quocGia": "Việt Nam", "tinh": "Nghệ An", "xa": "Tam Hợp", "diaChi": "Xóm Long Thành"}},
        {"name": "TkKs_HoTenMe", "value": "LE THI C"},
        {"name": "TkKs_NamSinhMe", "value": "1992"},
        {"name": "TkKs_NoiCuTruMe", "value": {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Bản Bo"}},
    ]

    values = {f["name"]: f["value"] for f in mapper.enrich(compact_fields)}

    assert values["ChaNoiCuTru"] == "1"
    assert values["ChaNoiCuTru_TrongNuoc"]["xa"] == "Tam Hợp"
    assert values["ChaNoiCuTru_TrongNuoc"]["diaChi"] == "Xóm Long Thành"
    assert values["ChaLoaiCuTru"] == "Thường trú"
    # Mẹ có địa chỉ riêng → KHÔNG bị dùng chung địa chỉ của cha.
    assert values["MeNoiCuTru"] == "1"
    assert values["MeNoiCuTru_TrongNuoc"]["xa"] == "Bản Bo"
    assert values["MeLoaiCuTru"] == "Thường trú"


def test_khai_sinh_thuong_parent_residence_prefers_cccd_over_declaration():
    """Có CCCD thì lấy theo CCCD; tờ khai chỉ lấp chỗ trống."""
    compact_fields = [
        {"name": "Gcs_HoTenCon", "value": "NGUYEN VAN A"},
        {"name": "Gcs_NgaySinhCon", "value": "01/01/2025"},
        {"name": "CccdNam_HoTen", "value": "NGUYEN VAN B"},
        {"name": "CccdNam_SoDinhDanh", "value": "040203015844"},
        {"name": "CccdNam_NoiCuTru_TrongNuoc", "value": {"quocGia": "Việt Nam", "tinh": "Nghệ An", "xa": "Tam Hợp"}},
        {"name": "TkKs_NoiCuTruCha", "value": {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Bản Bo"}},
    ]

    values = {f["name"]: f["value"] for f in mapper.enrich(compact_fields)}

    assert values["ChaNoiCuTru_TrongNuoc"]["xa"] == "Tam Hợp"


def test_khai_sinh_thuong_parent_residence_prefers_real_address_over_deceased_marker():
    """CCCD chỉ có marker "đã chết" mà tờ khai có địa chỉ thật → dùng địa chỉ thật."""
    compact_fields = [
        {"name": "Gcs_HoTenCon", "value": "NGUYEN VAN A"},
        {"name": "Gcs_NgaySinhCon", "value": "01/01/2025"},
        {"name": "CccdNam_HoTen", "value": "NGUYEN VAN B"},
        {"name": "CccdNam_SoDinhDanh", "value": "040203015844"},
        {
            "name": "CccdNam_NoiCuTru_TrongNuoc",
            "value": {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": "Đã chết"},
        },
        {"name": "TkKs_NoiCuTruCha", "value": {"quocGia": "Việt Nam", "tinh": "Nghệ An", "xa": "Tam Hợp"}},
    ]

    values = {f["name"]: f["value"] for f in mapper.enrich(compact_fields)}

    assert values["ChaNoiCuTru"] == "1"
    assert values["ChaNoiCuTru_TrongNuoc"]["xa"] == "Tam Hợp"
    assert "ChaNoiCuTru_NuocNgoai" not in values


def test_khai_sinh_thuong_deceased_marker_from_declaration_uses_other_box():
    """Tờ khai ghi "Đã mất" ở mục mẹ → tick "Khác" + điền chữ, dù không có CCCD mẹ."""
    compact_fields = [
        {"name": "Gcs_HoTenCon", "value": "NGUYEN VAN A"},
        {"name": "Gcs_NgaySinhCon", "value": "01/01/2025"},
        {"name": "TkKs_HoTenMe", "value": "LE THI C"},
        {
            "name": "TkKs_NoiCuTruMe",
            "value": {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": "Đã mất"},
        },
    ]

    values = {f["name"]: f["value"] for f in mapper.enrich(compact_fields)}

    assert values["MeNoiCuTru"] == "Khác"
    assert values["MeNoiCuTru_NuocNgoai"] == "Đã mất"
    assert "MeLoaiCuTru" not in values


def test_khai_sinh_thuong_deceased_father_uses_other_residence_box():
    """Cha đã chết: tick nơi cư trú "Khác" (ô nhập tự do) rồi ghi "Đã chết" vào đó."""
    compact_fields = [
        {"name": "Gcs_HoTenCon", "value": "NGUYEN VAN A"},
        {"name": "Gcs_NgaySinhCon", "value": "01/01/2025"},
        {"name": "CccdNam_HoTen", "value": "TRAN VAN B"},
        {
            "name": "CccdNam_NoiCuTru_TrongNuoc",
            "value": {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": "Đã chết"},
        },
    ]

    fields = mapper.enrich(compact_fields)
    values = {f["name"]: f["value"] for f in fields}

    assert values["ChaNoiCuTru"] == "Khác"
    assert values["ChaNoiCuTru_NuocNgoai"] == "Đã chết"
    # Nhánh "Trong nước" chỉ có dropdown tỉnh/xã → không dùng được cho chữ này.
    assert "ChaNoiCuTru_TrongNuoc" not in values
    # Người đã mất không còn nơi thường trú → không chọn loại cư trú.
    assert "ChaLoaiCuTru" not in values
    # Radio phải đứng TRƯỚC ô text thì form mới render ô nhập tự do kịp.
    order = [f["name"] for f in fields]
    assert order.index("ChaNoiCuTru") < order.index("ChaNoiCuTru_NuocNgoai")
    # Marker "đã chết" KHÔNG phải địa danh → không suy ra quê quán con từ nó.
    assert "nksQueQuan" not in values
    assert "nksQueQuan_TrongNuoc" not in values


def test_khai_sinh_thuong_deceased_mother_uses_other_residence_box():
    """Mẹ đã mất trên tờ khai, cha có CCCD thật → mỗi bên giữ đúng nơi cư trú của mình."""
    compact_fields = [
        {"name": "Gcs_HoTenCon", "value": "NGUYEN VAN A"},
        {"name": "Gcs_NgaySinhCon", "value": "01/01/2025"},
        {"name": "CccdNam_HoTen", "value": "TRAN VAN B"},
        {"name": "CccdNam_SoDinhDanh", "value": "040203015844"},
        {"name": "CccdNam_NgayCap", "value": "02/07/2021"},
        {
            "name": "CccdNam_NoiCuTru_TrongNuoc",
            "value": {"quocGia": "Việt Nam", "tinh": "Nghệ An", "xa": "Tam Hợp"},
        },
        {"name": "CccdNu_HoTen", "value": "LE THI C"},
        {
            "name": "CccdNu_NoiCuTru_TrongNuoc",
            "value": {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": "Đã mất"},
        },
    ]

    fields = mapper.enrich(compact_fields)
    values = {f["name"]: f["value"] for f in fields}

    assert values["MeNoiCuTru"] == "Khác"
    assert values["MeNoiCuTru_NuocNgoai"] == "Đã mất"
    assert "MeNoiCuTru_TrongNuoc" not in values
    assert "MeLoaiCuTru" not in values
    # Cha còn sống → vẫn tick "Trong nước" + "Thường trú" với địa chỉ thật.
    assert values["ChaLoaiCuTru"] == "Thường trú"
    assert values["ChaNoiCuTru"] == "1"
    assert values["ChaNoiCuTru_TrongNuoc"]["xa"] == "Tam Hợp"


def test_khai_sinh_thuong_mapper_ignores_mother_fields_when_identity_is_child():
    compact_fields = [
        {"name": "Gcs_HoTenCon", "value": "TRẦN THỊ C"},
        {"name": "Gcs_NgaySinhCon", "value": "01/01/1990"},
        {"name": "Gcs_GioiTinhCon", "value": "Nữ"},
        {"name": "CccdNu_HoTen", "value": "TRẦN THỊ C"},
        {"name": "CccdNu_NgaySinh", "value": "01/01/1990"},
        {"name": "CccdNu_SoDinhDanh", "value": "012345678901"},
    ]

    fields = mapper.enrich(compact_fields)
    values = {f["name"]: f["value"] for f in fields}

    assert values["HoTenKS"] == "TRẦN THỊ C"
    assert values["NgaySinhChon"] == "01/01/1990"
    assert values["GioiTinhKS"] == "Nữ"
    assert "HoTenMeKS" not in values
    assert "SoDinhDanhMe" not in values


def test_khai_sinh_thuong_requester_comes_from_declaration_when_present():
    """Người yêu cầu ghi trên tờ khai (chị dâu...) thắng mọi suy luận khác."""
    compact_fields = [
        {"name": "Gcs_HoTenCon", "value": "NGUYỄN VĂN A"},
        {"name": "Gcs_NgaySinhCon", "value": "01/01/2025"},
        {"name": "CccdNam_HoTen", "value": "NGUYỄN VĂN B"},
        {"name": "CccdNam_SoDinhDanh", "value": "040203015844"},
        {"name": "CccdNam_NgayCap", "value": "02/07/2021"},
        {"name": "TkKs_NycHoTen", "value": "TRẦN THỊ D"},
        {"name": "TkKs_NycSoDinhDanh", "value": "012193000851"},
        {"name": "TkKs_NycNgayCapCccd", "value": "06/02/2024"},
        {"name": "TkKs_NycNoiCuTru", "value": {"quocGia": "Việt Nam", "tinh": "Nghệ An", "xa": "Tam Hợp"}},
    ]

    values = {f["name"]: f["value"] for f in mapper.enrich(compact_fields)}

    assert values["HoVaTenC"] == "TRẦN THỊ D"
    assert values["SoDinhDanhC"] == "012193000851"
    assert values["SoGiayToDinhDanhC"] == "012193000851"
    assert values["NgayCapDDC"] == "06/02/2024"
    assert values["nycNoiCuTru"] == "1"
    assert values["nycNoiCuTru_TrongNuoc"]["xa"] == "Tam Hợp"
    assert values["QuanHe"] == "Khac"
    # Cha vẫn giữ nguyên thông tin CCCD cha.
    assert values["HoTenChaKS"] == "NGUYỄN VĂN B"


def test_khai_sinh_thuong_requester_is_subject_for_late_registration():
    """Đăng ký muộn: người được đăng ký tự đi làm → người yêu cầu lấy từ CCCD chủ thể."""
    compact_fields = [
        {"name": "CccdChuThe_HoTen", "value": "TRẦN THỊ NGHỀ"},
        {"name": "CccdChuThe_SoDinhDanh", "value": "034168016773"},
        {"name": "CccdChuThe_NgaySinh", "value": "01/01/1968"},
        {"name": "CccdChuThe_GioiTinh", "value": "Nữ"},
        {"name": "CccdChuThe_NgayCap", "value": "10/05/2022"},
        {"name": "CccdChuThe_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
        {"name": "CccdChuThe_NoiCuTru", "value": {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Bản Bo"}},
        {"name": "TkKs_HoTenCha", "value": "TRẦN ĐÌNH TÚC"},
        {"name": "TkKs_NamSinhCha", "value": "1908"},
    ]

    values = {f["name"]: f["value"] for f in mapper.enrich(compact_fields)}

    assert values["HoVaTenC"] == "TRẦN THỊ NGHỀ"
    assert values["SoDinhDanhC"] == "034168016773"
    assert values["NgayCapDDC"] == "10/05/2022"
    assert values["NoiCapDDC"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["nycNoiCuTru_TrongNuoc"]["xa"] == "Bản Bo"
    assert values["QuanHe"] == "Khac"
    assert values["HoTenKS"] == "TRẦN THỊ NGHỀ"
    assert values["HoTenChaKS"] == "TRẦN ĐÌNH TÚC"


def test_khai_sinh_thuong_requester_falls_back_to_mother_cccd():
    """Hồ sơ chỉ có CCCD mẹ → mẹ là người yêu cầu, QuanHe = MeDe."""
    compact_fields = [
        {"name": "Gcs_HoTenCon", "value": "NGUYỄN VĂN A"},
        {"name": "Gcs_NgaySinhCon", "value": "01/01/2025"},
        {"name": "CccdNu_HoTen", "value": "PHẠM NGỌC THỦY"},
        {"name": "CccdNu_SoDinhDanh", "value": "012193000851"},
        {"name": "CccdNu_NgaySinh", "value": "20/03/1993"},
        {"name": "CccdNu_NgayCap", "value": "06/02/2024"},
        {"name": "CccdNu_NoiCuTru_TrongNuoc", "value": {"quocGia": "Việt Nam", "tinh": "Lai Châu", "diaChi": "Tổ 3"}},
    ]

    values = {f["name"]: f["value"] for f in mapper.enrich(compact_fields)}

    assert values["HoVaTenC"] == "PHẠM NGỌC THỦY"
    assert values["SoDinhDanhC"] == "012193000851"
    assert values["NgayCapDDC"] == "06/02/2024"
    assert values["QuanHe"] == "MeDe"
    assert values["nycNoiCuTru_TrongNuoc"]["diaChi"] == "Tổ 3"


def test_khai_sinh_thuong_requester_absent_when_no_ocr_source():
    """Không suy ra được người yêu cầu → không phát field, giữ nguyên dữ liệu cổng điền sẵn."""
    compact_fields = [
        {"name": "Gcs_HoTenCon", "value": "NGUYỄN VĂN A"},
        {"name": "Gcs_NgaySinhCon", "value": "01/01/2025"},
    ]

    values = {f["name"]: f["value"] for f in mapper.enrich(compact_fields)}

    assert "HoVaTenC" not in values
    assert "SoDinhDanhC" not in values
    assert "nycNoiCuTru" not in values


def test_khai_sinh_thuong_mapper_ignores_mother_when_name_matches_and_birth_year_matches():
    compact_fields = [
        {"name": "Gcs_HoTenCon", "value": "TRẦN THỊ NGHÊ"},
        {"name": "Gcs_NgaySinhCon", "value": "01/10/1968"},
        {"name": "CccdNu_HoTen", "value": "TRẦN THỊ NGHỀ"},
        {"name": "CccdNu_NgaySinh", "value": "01/01/1968"},
        {"name": "CccdNu_SoDinhDanh", "value": "034168016773"},
    ]

    fields = mapper.enrich(compact_fields)
    values = {f["name"]: f["value"] for f in fields}

    assert values["HoTenKS"] == "TRẦN THỊ NGHÊ"
    assert values["NgaySinhChon"] == "01/10/1968"
    assert "HoTenMeKS" not in values
    assert "SoDinhDanhMe" not in values

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
    assert "CccdNam_* CHỈ lấy từ giấy tờ CĂN CƯỚC/CMND có giới tính \"Nam\"" in system_prompt
    assert "CccdNu_* CHỈ lấy từ giấy tờ CĂN CƯỚC/CMND có giới tính \"Nữ\"" in system_prompt
    assert "Không trả field mặc định hoặc field UI" in system_prompt
    assert "HoVaTenC, SoDinhDanhC, HoTenKS" in system_prompt


def test_registry_uses_regular_birth_pipeline():
    proc = get_procedure("khai-sinh-dang-ky-thuong")

    assert proc["label"] == "Thủ tục đăng ký khai sinh"
    assert proc["hasAttachmentStep"] is True
    assert get_pipeline("khai-sinh-dang-ky-thuong") is khai_sinh_thuong_process


def _thuong_ui(values: dict) -> dict:
    fields = [{"name": name, "value": value} for name, value in values.items()]
    return {f["name"]: f for f in mapper.enrich(fields)}


def test_khai_sinh_thuong_card_of_other_person_falls_back_to_declaration():
    ui = _thuong_ui({
        "Gcs_HoTenCon": "Trần Minh An",
        "Gcs_NgaySinhCon": "01/03/2025",
        "TkKs_HoTenCha": "Trần Văn Bình",
        "TkKs_NamSinhCha": "1990",
        "TkKs_SoDinhDanhCha": "001090000222",
        "CccdNam_HoTen": "PHẠM VĂN KHOA",
        "CccdNam_SoDinhDanh": "001050999888",
        # Hơn con 75 tuổi → không hợp làm cha, thẻ của người khác.
        "CccdNam_NgaySinh": "05/05/1950",
        "CccdNam_NgayCap": "01/01/2021",
    })

    assert ui["HoTenChaKS"]["value"] == "TRẦN VĂN BÌNH"
    assert ui["HoTenChaKS"].get("default") is True
    assert ui["NamSinhChaKS"]["value"] == "1990"
    assert ui["SoDinhDanhCha"]["value"] == "001090000222"
    assert ui["SoDinhDanhCha"].get("default") is True
    assert "NgayCapDDCha" not in ui


def test_khai_sinh_thuong_same_id_card_wins_name():
    ui = _thuong_ui({
        "Gcs_HoTenCon": "Trần Minh An",
        "Gcs_NgaySinhCon": "01/03/2025",
        "TkKs_HoTenMe": "Lê Thị Hạnh",
        "TkKs_NamSinhMe": "1992",
        "TkKs_SoDinhDanhMe": "001192000111",
        "CccdNu_HoTen": "LÊ THỊ HOA",
        "CccdNu_SoDinhDanh": "001192000111",
        "CccdNu_NgaySinh": "10/10/1992",
        "CccdNu_NgayCap": "01/01/2021",
    })

    assert ui["HoTenMeKS"]["value"] == "LÊ THỊ HOA"
    assert not ui["HoTenMeKS"].get("default")
    assert ui["NamSinhMeKS"]["value"] == "10/10/1992"
    assert ui["NgayCapDDMe"]["value"] == "01/01/2021"


def test_khai_sinh_thuong_name_slip_keeps_card_identity():
    ui = _thuong_ui({
        "Gcs_HoTenCon": "Trần Minh An",
        "TkKs_HoTenCha": "Trần Văn Binh",
        "TkKs_SoDinhDanhCha": "001090000223",
        "CccdNam_HoTen": "TRẦN VĂN BÌNH",
        "CccdNam_SoDinhDanh": "001090000222",
        "CccdNam_NgaySinh": "02/02/1990",
    })

    assert ui["HoTenChaKS"]["value"] == "TRẦN VĂN BÌNH"  # họ tên in trên thẻ, không theo bản viết tay
    assert ui["SoDinhDanhCha"]["value"] == "001090000222"
    assert ui["NamSinhChaKS"]["value"] == "02/02/1990"
    assert not ui["HoTenChaKS"].get("default")


def test_khai_sinh_thuong_mismatched_card_fitting_generation_is_father():
    ui = _thuong_ui({
        "Gcs_HoTenCon": "Trần Minh An",
        "Gcs_NgaySinhCon": "01/03/2025",
        "TkKs_HoTenCha": "Trần Văn Bình",
        "TkKs_NamSinhCha": "1990",
        "TkKs_SoDinhDanhCha": "001090000222",
        "TkKs_DanTocCha": "Kinh",
        "CccdNam_HoTen": "PHẠM VĂN KHOA",
        "CccdNam_SoDinhDanh": "001080999888",
        "CccdNam_NgaySinh": "05/05/1980",
        "CccdNam_NgayCap": "01/01/2021",
    })

    assert ui["HoTenChaKS"]["value"] == "PHẠM VĂN KHOA"
    assert ui["HoTenChaKS"].get("default") is True
    assert ui["SoDinhDanhCha"]["value"] == "001080999888"
    assert ui["NamSinhChaKS"]["value"] == "05/05/1980"
    assert ui["NgayCapDDCha"]["value"] == "01/01/2021"
    assert ui["DanTocChaKS"]["value"] == "Kinh"


_CT01_OCR = """CĂN CƯỚC CÔNG DÂN
Họ và tên / Full name:
LÊ VĂN TÂM
───── Trang 2/2 ─────
TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ
Kính gửi(1): Công an phường Đông Hải
1. Họ, chữ đệm và tên khai sinh: LÊ MINH KHANG
2. Ngày, tháng, năm sinh: 05 / 07 / 2026
3. Giới tính: Nam
4. Số định danh cá nhân:
7. Họ, chữ đệm và tên chủ hộ(2): LÊ VĂN SƠN
8. Mối quan hệ với chủ hộ: cháu nội
10. Nội dung đề nghị(3): Đăng ký thường trú lần đầu cho con mới sinh
"""


def test_khai_sinh_thuong_child_from_residence_form_ct01():
    from app.pipelines.khai_sinh_thuong.process import runner

    raw = {
        "CccdNam_HoTen": "LÊ VĂN TÂM", "CccdNam_SoDinhDanh": "038095001234",
        "CccdNam_NgaySinh": "01/02/1995",
        "CccdNu_HoTen": "PHẠM THỊ LAN", "CccdNu_SoDinhDanh": "038197005678",
        "CccdNu_NgaySinh": "03/04/1997",
    }
    fixed = runner._fix_issue_by_mrz(raw, [{"text": _CT01_OCR}])

    assert fixed["TkKs_HoTenCon"] == "LÊ MINH KHANG"
    assert fixed["TkKs_NgaySinhCon"] == "05/07/2026"
    assert fixed["TkKs_GioiTinhCon"] == "Nam"
    ui = _thuong_ui(fixed)
    assert ui["HoTenKS"]["value"] == "LÊ MINH KHANG"
    assert ui["GioiTinhKS"]["value"] == "Nam"


def test_khai_sinh_thuong_ct01_of_parent_is_not_child():
    from app.pipelines.khai_sinh_thuong.process import runner

    raw = {"CccdNam_HoTen": "LÊ MINH KHANG", "CccdNam_NgaySinh": "01/02/1995"}
    fixed = runner._fix_issue_by_mrz(raw, [{"text": _CT01_OCR}])
    assert "TkKs_HoTenCon" not in fixed

    raw = {"Gcs_HoTenCon": "Lê Minh Khôi", "CccdNam_HoTen": "LÊ VĂN TÂM"}
    fixed = runner._fix_issue_by_mrz(raw, [{"text": _CT01_OCR}])
    assert "TkKs_HoTenCon" not in fixed

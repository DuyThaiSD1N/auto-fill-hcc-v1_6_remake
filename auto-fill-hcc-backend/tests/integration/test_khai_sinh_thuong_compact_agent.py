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

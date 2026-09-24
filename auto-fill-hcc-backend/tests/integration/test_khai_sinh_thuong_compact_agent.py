"""Compact agent đăng ký khai sinh thường: short facts -> legacy x-* UI fields."""

from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.khai_sinh_thuong.process import run as khai_sinh_thuong_process
from app.pipelines.khai_sinh_thuong.process import mapper
from app.pipelines.khai_sinh_thuong.process.prompt import EXTRA_RULES
from app.pipelines.khai_sinh_thuong.process.schema import FIELDS
from app.procedures.registry import get_pipeline, get_procedure
from app.pipelines._shared.compact_agent.issuer import ISSUER_BO_CONG_AN, ISSUER_CUC
from app.pipelines.khai_sinh_thuong.process.runner import (
    _ID_ISSUE_GROUPS,
    _fix_issue_by_mrz,
    _parse_backs,
    _reassign_issue_by_mrz,
)


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


# ── Ngày cấp / nơi cấp CCCD cha mẹ scan chung một file gắn đúng chủ thẻ theo MRZ ──

MOTHER_ID = "001199012345"
FATHER_ID = "002093067890"

# Trang 1: mặt trước Căn cước mới (mẹ) + CCCD chip cũ (cha); trang 2: hai mặt sau theo cùng thứ tự.
_MOTHER_BACK = """Nơi cư trú / Place of residence: Thôn Mẫu
Xã Ví Dụ, Tỉnh Mẫu
Nơi đăng ký khai sinh / Place of birth:
Xã Thử, Tỉnh Mẫu
Ngày, tháng, năm cấp / Date of issue:
05/07/2025
Ngày, tháng, năm hết hạn /Date of expiry:
15/03/2039
BỘ CÔNG AN/MINISTRY OF PUBLIC SECURITY
IDVNM1990123451001199012345<<3
9903158F3903156VNM<<<<<<<<<<<<2
PHAM<<THI<MAU<<<<<<<<<<<<<<<<<
"""
_FATHER_BACK = """Đặc điểm nhận dạng / Personal identification:
Sẹo chấm C:1cm dưới mắt phải.
Ngày, tháng, năm / Date, month, year: 14/08/2021
CỤC TRƯỞNG CỤC CẢNH SÁT
QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI
Ngón trỏ trái
IDVNMO930678902002093067890<<5
9301018M3301016VNM<<<<<<<<<<<<4
LE<<VAN<THU<<<<<<<<<<<<<<<<<<<
"""
OCR = f"""===== cccd vo chong.pdf (tiengnoi) =====
───── Trang 1/2 ─────
CĂN CƯỚC
IDENTITY CARD
Số định danh cá nhân / Personal identification number:
{MOTHER_ID}
Ngày, tháng, năm sinh / Date of birth: Giới tính / Sex:
15/03/1999 Nữ
CĂN CƯỚC CÔNG DÂN
Số / No.: {FATHER_ID}
Ngày sinh / Date of birth: 01/01/1993
Có giá trị đến 01/01/2033

───── Trang 2/2 ─────
{_MOTHER_BACK}
{_FATHER_BACK}
---
"""


def test_parse_backs_splits_each_card_by_mrz():
    backs = _parse_backs(OCR)
    assert len(backs) == 2
    assert MOTHER_ID in backs[0]["mrz_digits"]
    assert backs[0]["ngay_cap"] == "05/07/2025"
    assert backs[0]["noi_cap"] == ISSUER_BO_CONG_AN
    # MRZ OCR đọc "0" thành "O" vẫn ra đúng số định danh.
    assert FATHER_ID in backs[1]["mrz_digits"]
    assert backs[1]["ngay_cap"] == "14/08/2021"
    assert backs[1]["noi_cap"] == ISSUER_CUC


def test_swapped_issue_date_is_reassigned_to_owner():
    # Đúng lỗi thực tế: LLM gán ngày cấp thẻ mẹ cho cha, bỏ trống mẹ, nơi cấp cha lấy nhầm.
    llm = {
        "CccdNu_SoDinhDanh": MOTHER_ID,
        "CccdNam_SoDinhDanh": FATHER_ID,
        "CccdNam_NgayCap": "05/07/2025",
        "CccdNam_NoiCap": "Bộ Công an",
    }
    out = _fix_issue_by_mrz(llm, [{"name": "cccd.pdf", "text": OCR}])
    assert out["CccdNu_NgayCap"] == "05/07/2025"
    assert out["CccdNu_NoiCap"] == ISSUER_BO_CONG_AN
    assert out["CccdNam_NgayCap"] == "14/08/2021"
    assert out["CccdNam_NoiCap"] == ISSUER_CUC


def test_borrowed_date_cleared_when_own_back_missing():
    ocr = f"───── Trang 1/1 ─────\n{_MOTHER_BACK}"
    fields = {
        "CccdNu_SoDinhDanh": MOTHER_ID,
        "CccdNam_SoDinhDanh": FATHER_ID,
        "CccdNam_NgayCap": "5/7/2025",
        "CccdNam_NoiCap": "Bộ Công an",
    }
    out = _reassign_issue_by_mrz(fields, _ID_ISSUE_GROUPS, ocr)
    assert out["CccdNu_NgayCap"] == "05/07/2025"
    assert "CccdNam_NgayCap" not in out
    assert "CccdNam_NoiCap" not in out


def test_same_day_date_kept_when_other_back_has_no_mrz():
    # Vợ chồng làm thẻ cùng ngày; mặt sau của chồng OCR mất MRZ → không được xoá ngày cấp của chồng.
    father_back_no_mrz = "Ngày, tháng, năm cấp / Date of issue:\n05/07/2025\nBỘ CÔNG AN\n"
    ocr = f"───── Trang 1/2 ─────\n{_MOTHER_BACK}\n───── Trang 2/2 ─────\n{father_back_no_mrz}"
    fields = {
        "CccdNu_SoDinhDanh": MOTHER_ID,
        "CccdNam_SoDinhDanh": FATHER_ID,
        "CccdNam_NgayCap": "05/07/2025",
        "CccdNam_NoiCap": "Bộ Công an",
    }
    out = _reassign_issue_by_mrz(fields, _ID_ISSUE_GROUPS, ocr)
    assert out["CccdNam_NgayCap"] == "05/07/2025"
    assert out["CccdNu_NgayCap"] == "05/07/2025"


def test_no_mrz_leaves_llm_output_untouched():
    fields = {"CccdNam_SoDinhDanh": FATHER_ID, "CccdNam_NgayCap": "14/08/2021"}
    assert _reassign_issue_by_mrz(dict(fields), _ID_ISSUE_GROUPS, "CMND số 123456789") == fields

"""Cấp mới / Điều chỉnh GPHN giai đoạn chuyển tiếp — tự nộp (giữ tích "Người nộp là chủ hồ sơ"): cổng chép họ tên,
CCCD sang Phần II nhưng không chép ngày sinh → mapper phải điền data[ownerBirthday]."""

import pytest

from app.pipelines.cap_moi_giay_phep_hanh_nghe_chuyen_tiep.process import mapper as cap_moi
from app.pipelines.dieu_chinh_giay_phep_hanh_nghe_chuyen_tiep.process import mapper as dieu_chinh

_MAPPERS = [cap_moi, dieu_chinh]


def _fields(birthday="01/02/1990"):
    values = {
        "NguoiHanhNghe_HoTen": "NGUYEN VAN A",
        "NguoiHanhNghe_SoDinhDanh": "001090000001",
        "NguoiHanhNghe_NgaySinh": birthday,
    }
    return [{"name": k, "value": v} for k, v in values.items() if v]


def _ui(out):
    fields, _ = out
    return {f["name"]: f for f in fields}


@pytest.mark.parametrize("mapper", _MAPPERS)
def test_tu_nop_dien_ngay_sinh_ca_phan_ii(mapper):
    ctx = {"formContext": {"applicantFullname": "NGUYEN VAN A", "applicantIdentityNumber": "001090000001"}}
    ui = _ui(mapper.enrich(_fields(), ctx))
    assert ui["data[birthday]"]["value"] == "01/02/1990"
    assert ui["data[ownerBirthday]"]["value"] == "01/02/1990"
    assert "data[ownerFullname]" not in ui, "tự nộp: họ tên Phần II cổng tự chép"


@pytest.mark.parametrize("mapper", _MAPPERS)
def test_theo_to_khai_tai_khoan_khac_nguoi_dien_ngay_sinh_phan_ii(mapper):
    opts = {"submitterMode": "owner_as_submitter",
            "formContext": {"applicantFullname": "TRAN THI B", "applicantIdentityNumber": "001190000002"}}
    ui = _ui(mapper.enrich(_fields(), opts))
    assert ui["data[ownerBirthday]"]["value"] == "01/02/1990"


@pytest.mark.parametrize("mapper", _MAPPERS)
def test_theo_to_khai_thieu_ngay_sinh_xoa_ca_hai_o(mapper):
    opts = {"submitterMode": "owner_as_submitter",
            "formContext": {"applicantFullname": "TRAN THI B", "applicantIdentityNumber": "001190000002"}}
    ui = _ui(mapper.enrich(_fields(birthday=None), opts))
    assert ui["data[birthday]"].get("clear") and ui["data[ownerBirthday]"].get("clear")

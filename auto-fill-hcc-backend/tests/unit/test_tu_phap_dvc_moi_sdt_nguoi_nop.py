"""Trích lục / khai sinh / cải chính (cổng DVC mới): SĐT người nộp ghi trên giấy → ô citizenPhone của khối người nộp."""
import pytest

from app.pipelines.cai_chinh_dvc_moi.process import mapper as cai_chinh
from app.pipelines.khai_sinh_dvc_moi.process import mapper as khai_sinh
from app.pipelines.trich_luc_dvc_moi.process import mapper as trich_luc

MAPPERS = (trich_luc, khai_sinh, cai_chinh)


def _phone(module, value, present="Có"):
    context = f"<nguoi_nop>\nHọ tên: NGUYỄN VĂN A\nCó trong hồ sơ: {present}\n</nguoi_nop>\n"
    out, _ = module.enrich([{"name": "NguoiNop_SoDienThoai", "value": value}], {"_reasoning_context": context})
    return next((f["value"] for f in out if f["name"] == "citizenPhone"), None)


@pytest.mark.parametrize("module", MAPPERS)
def test_sdt_nguoi_nop_co_trong_ho_so(module):
    assert _phone(module, "ĐT: 0912 345 678") == "0912345678"
    assert _phone(module, "+84 912 345 678") == "0912345678"


@pytest.mark.parametrize("module", MAPPERS)
def test_khong_dien_khi_nguoi_nop_khong_co_trong_ho_so_hoac_so_sai_dang(module):
    assert _phone(module, "0912345678", present="Không") is None
    assert _phone(module, "001195000001") is None

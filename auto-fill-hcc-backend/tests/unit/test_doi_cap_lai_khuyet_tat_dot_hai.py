"""Đổi, cấp lại Giấy xác nhận khuyết tật — dùng chung thanh tra, đọc riêng bảng dạng khuyết tật và kiểm theo OCR của
khuyet_tat (cùng eForm Mẫu số 01). Dữ liệu giả."""

import asyncio

from app.pipelines.doi_cap_lai_giay_xac_nhan_khuyet_tat.process import runner
from app.procedures.registry import PROCEDURES
from app.second_pass.service import capability

_DON = ("ĐƠN ĐỀ NGHỊ XÁC ĐỊNH, XÁC ĐỊNH LẠI MỨC ĐỘ KHUYẾT TẬT VÀ CẤP, CẤP ĐỔI, CẤP LẠI GIẤY XÁC NHẬN KHUYẾT TẬT\n"
        "| 1 | Khuyết tật vận động | | |\n| 1.4 | Yếu, liệt, teo cơ | | |\n")
_RAW = {"Nkt_HoTen": "Nguyễn Văn Con", "Nkt_SoDinhDanh": "001220000001", "DeNghi_NoiDung": "cap_doi",
        "KhuyetTat_DanhMuc": ["kt1"], "KhuyetTat_ChiTiet": ["kt1_4"],
        "Ndd_HoTen": "Nguyễn Văn Cha", "Ndd_SoDinhDanh": "001080000002", "Ndd_NgaySinh": "01/01/1980"}


def test_dang_ky_dot_hai_form_formio():
    entry = next(p for p in PROCEDURES if p["key"] == "doi-cap-lai-giay-xac-nhan-khuyet-tat")
    assert capability(entry) == "secondPassFormio"


def _run(monkeypatch, options, rows):
    seen = {}

    async def fake_run(files_by_role, **kwargs):
        seen["context"] = await kwargs["context_builder"]([{"name": "don.pdf", "text": _DON}], options)
        return {"fields": [{"name": k, "comp": "raw", "value": v} for k, v in _RAW.items()], "ocr_text": _DON}

    async def none(*_args, **_kwargs):
        return None

    async def types(_documents):
        return rows

    monkeypatch.setattr(runner.runner, "run", fake_run)
    monkeypatch.setattr(runner.vision, "read_section_iii", none)
    monkeypatch.setattr(runner.muc_do, "read_activity_levels", none)
    monkeypatch.setattr(runner.dang_khuyet_tat, "read_disability_types", types)
    return asyncio.run(runner.run({"doc": []}, options)), seen


def test_don_cap_doi_bo_trong_muc_iii_khong_tich_va_co_dot_hai(monkeypatch):
    opts = {"_secondPass": True, "submitterMode": "owner_as_submitter", "counterWard": "HCC Phường Đông Hà"}
    res, seen = _run(monkeypatch, opts, {"1": "trong", "1.4": "trong"})
    names = {f["name"]: f.get("value") for f in res["fields"]}
    # Bảng dạng khuyết tật không dấu → không tích (lượt chính trả kt1 / kt1_4 bị bỏ).
    assert not any("khuyetTat" in name for name in names)
    # Ngày sinh người đại diện không có trên giấy → xoá ô cổng đổ sẵn, không ghi "01/01/1980".
    assert names["data[birthday]"] == ""
    assert names["data[chonNoiDungDeNghi][]"] is True
    assert "<xa_quay>" in seen["context"] and callable(res.get("_second_pass"))
    res, _ = _run(monkeypatch, {}, None)
    assert "_second_pass" not in res

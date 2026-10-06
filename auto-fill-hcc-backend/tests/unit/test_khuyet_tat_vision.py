"""Mục III khuyết tật: Qwen đọc ảnh chạy song song, JSON hợp lệ thì thay kết quả OCR + LLM, lỗi thì giữ cũ."""

import asyncio

from app.pipelines.khuyet_tat.process import runner as kt_runner
from app.pipelines.khuyet_tat.process import vision

_LLM_FIELDS = [
    {"name": "Nkt_HoTen", "comp": "x-input", "value": "Nguyễn Văn Con"},
    {"name": "KhuyetTat_DanhMuc", "comp": "raw", "value": ["kt1"]},
    {"name": "KhuyetTat_ChiTiet", "comp": "raw", "value": ["kt1_1", "kt1_2"]},
    {"name": "MucDo_HoatDong", "comp": "raw", "value": {"1": "KTHD"}},
]


def _vision_json():
    rows = {r: "khong" for r in vision.ROWS}
    rows.update({"2.1": "co", "5.3": "co", "3.4": "khong_ro", "6": "co"})
    return {"dang_khuyet_tat": rows, "muc_do": {"1": "THD", "2": "CTG", "3": "trong", "4": "khong_ro"}}


def test_to_compact_fields_chi_lay_dong_co():
    out = vision.to_compact_fields(_vision_json())
    assert out == {
        "KhuyetTat_DanhMuc": ["kt6"],
        "KhuyetTat_ChiTiet": ["kt2_1", "kt5_3"],
        "MucDo_HoatDong": {"1": "THD", "2": "CTG"},
    }


def test_to_compact_fields_sai_khung_tra_none():
    assert vision.to_compact_fields({}) is None
    assert vision.to_compact_fields({"dang_khuyet_tat": {"x": "co"}, "muc_do": {}}) is None
    assert vision.to_compact_fields({"dang_khuyet_tat": [], "muc_do": {}}) is None


def _run(monkeypatch, section_iii):
    async def fake_compact(files_by_role, **kwargs):
        return {"fields": [dict(f) for f in _LLM_FIELDS], "errors": []}

    async def fake_vision(files):
        return section_iii

    monkeypatch.setattr(kt_runner.runner, "run", fake_compact)
    monkeypatch.setattr(kt_runner.vision, "read_section_iii", fake_vision)
    res = asyncio.run(kt_runner.run({"doc": []}, {}))
    return {f["name"]: f["value"] for f in res["fields"]}


def test_doc_anh_hop_le_thay_ket_qua_llm(monkeypatch):
    d = _run(monkeypatch, vision.to_compact_fields(_vision_json()))
    assert "data[khuyetTat1Obj][khuyetTatRadio1]" not in d
    assert d["data[khuyetTat2Obj][khuyetTatRadio1]"] == "co"
    assert d["data[khuyetTat5Obj][khuyetTatRadio3]"] == "co"
    assert d["data[mucDoKhuyetTatObj][mucDoRadio1]"] == "THD"
    assert d["data[NktHoTen]"] == "Nguyễn Văn Con"


def test_doc_anh_loi_giu_ket_qua_llm(monkeypatch):
    d = _run(monkeypatch, None)
    assert d["data[khuyetTat1Obj][khuyetTatRadio1]"] == "co"
    assert d["data[mucDoKhuyetTatObj][mucDoRadio1]"] == "KTHD"

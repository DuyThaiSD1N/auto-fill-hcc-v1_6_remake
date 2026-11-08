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
    rows.update({"2.1": "co", "5.3": "co", "3.4": "khong_ro", "6": "co", "6.1": "trong", "6.2": "trong", "6.3": "trong"})
    return {"dang_khuyet_tat": rows, "muc_do": {"1": "THD", "2": "CTG", "3": "trong", "4": "khong_ro"}}


def test_to_compact_fields_chi_lay_dong_co():
    out = vision.to_compact_fields(_vision_json())
    assert out["KhuyetTat_DanhMuc"] == ["kt6"]
    assert out["KhuyetTat_ChiTiet"] == ["kt2_1", "kt5_3"]
    assert out["MucDo_HoatDong"] == {"1": "THD", "2": "CTG"}
    assert "kt1" in out["KhuyetTat_Khong"] and "kt2_2" in out["KhuyetTat_Khong"]
    # Dòng "khong_ro"/"trong" không vào danh sách nào.
    assert "kt3_4" not in out["KhuyetTat_Khong"] and "kt6_1" not in out["KhuyetTat_Khong"]


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
    monkeypatch.setattr(kt_runner.vision, "ENABLED", True)
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


def test_nhom_cha_co_ma_moi_dong_con_khong_thi_theo_dong_con():
    rows = {r: "khong" for r in vision.ROWS}
    rows.update({"1": "co", "1.1": "co", "2": "co", "3": "co"})
    out = vision.to_compact_fields({"dang_khuyet_tat": rows, "muc_do": {}})
    assert out["KhuyetTat_DanhMuc"] == ["kt1"]
    assert "kt2" in out["KhuyetTat_Khong"] and "kt3" in out["KhuyetTat_Khong"]


def test_dong_nhom_trong_ma_dong_con_khong_thi_nhom_khong():
    rows = {r: "khong" for r in vision.ROWS}
    rows.update({"1": "trong", "1.4": "trong", "2": "trong", "2.3": "co", "3": "trong"})
    rows.update({f"3.{i}": "trong" for i in range(1, 8)})
    out = vision.to_compact_fields({"dang_khuyet_tat": rows, "muc_do": {}})
    assert "kt1" in out["KhuyetTat_Khong"]
    assert "kt2" not in out["KhuyetTat_Khong"]
    # Nhóm trống trọn vẹn → không có căn cứ, bỏ trống.
    assert "kt3" not in out["KhuyetTat_Khong"]


def test_moi_dong_con_deu_co_la_suy_bien():
    assert vision.is_degenerate({"dang_khuyet_tat": {r: "co" for r in vision.ROWS}})
    rows = {r: "co" for r in vision.ROWS}
    rows["4.2"] = "khong"
    assert not vision.is_degenerate({"dang_khuyet_tat": rows})
    assert not vision.is_degenerate({})


def test_tich_khong_dong_nhom_va_dong_con_trong_nhom_co(monkeypatch):
    rows = {r: "khong" for r in vision.ROWS}
    rows.update({"1": "trong", "1.1": "co", "1.3": "co", "1.4": "co", "2.4": "trong"})
    d = _run(monkeypatch, vision.to_compact_fields({"dang_khuyet_tat": rows, "muc_do": {}}))
    assert d["data[khuyetTat1Obj][khuyetTatRadio]"] == "co"
    assert d["data[khuyetTat1Obj][khuyetTatRadio1]"] == "co"
    assert d["data[khuyetTat1Obj][khuyetTatRadio2]"] == "khong"
    # Nhóm không "Có": chỉ tích "Không" ở dòng nhóm, radio con không hiện trên cổng.
    assert d["data[khuyetTat2Obj][khuyetTatRadio]"] == "khong"
    assert "data[khuyetTat2Obj][khuyetTatRadio1]" not in d
    assert d["data[khuyetTat6Obj][khuyetTatRadio]"] == "khong"


def _vision_res(contents):
    calls = iter(contents)

    async def fake_chat(messages, **kwargs):
        return {"content": next(calls), "finish_reason": "stop"}

    return fake_chat


def test_doc_lai_khi_suy_bien(monkeypatch):
    import json

    good = {r: "khong" for r in vision.ROWS}
    good["5.1"] = "co"
    bad = {r: "co" for r in vision.ROWS}
    monkeypatch.setattr(vision, "_page_images", lambda files: [b"img"])
    monkeypatch.setattr(vision.ocr_qwen, "chat", _vision_res([
        json.dumps({"dang_khuyet_tat": bad, "muc_do": {}}),
        json.dumps({"dang_khuyet_tat": good, "muc_do": {}}),
    ]))
    out = asyncio.run(vision.read_section_iii([{"name": "don.pdf"}]))
    assert out["KhuyetTat_ChiTiet"] == ["kt5_1"]


def test_suy_bien_hai_lan_thi_bo_va_canh_bao(monkeypatch):
    import json

    bad = json.dumps({"dang_khuyet_tat": {r: "co" for r in vision.ROWS}, "muc_do": {}})
    monkeypatch.setattr(vision, "_page_images", lambda files: [b"img"])
    monkeypatch.setattr(vision.ocr_qwen, "chat", _vision_res([bad, bad]))
    assert asyncio.run(vision.read_section_iii([{"name": "don.pdf"}])) is None

    async def fake_compact(files_by_role, **kwargs):
        return {"fields": [dict(f) for f in _LLM_FIELDS], "errors": []}

    async def fake_vision(files):
        return None

    monkeypatch.setattr(kt_runner.runner, "run", fake_compact)
    monkeypatch.setattr(kt_runner.vision, "read_section_iii", fake_vision)
    monkeypatch.setattr(kt_runner.vision, "ENABLED", True)
    res = asyncio.run(kt_runner.run({"doc": []}, {}))
    assert vision.SECTION_III_WARNING in res["errors"]


def test_tat_vision_chi_chay_ocr_llm_khong_canh_bao(monkeypatch):
    async def fake_compact(files_by_role, **kwargs):
        return {"fields": [dict(f) for f in _LLM_FIELDS], "errors": []}

    async def fake_vision(files):
        raise AssertionError("không được gọi Qwen khi tắt")

    monkeypatch.setattr(kt_runner.runner, "run", fake_compact)
    monkeypatch.setattr(kt_runner.vision, "read_section_iii", fake_vision)
    monkeypatch.setattr(kt_runner.vision, "ENABLED", False)
    res = asyncio.run(kt_runner.run({"doc": []}, {}))
    assert vision.SECTION_III_WARNING not in res["errors"]
    assert {f["name"]: f["value"] for f in res["fields"]}["data[khuyetTat1Obj][khuyetTatRadio1]"] == "co"


def _enrich_iii(danh_muc, chi_tiet):
    from app.pipelines.khuyet_tat.process import mapper

    fields = [{"name": "KhuyetTat_DanhMuc", "value": danh_muc}, {"name": "KhuyetTat_ChiTiet", "value": chi_tiet}]
    return {f["name"]: f["value"] for f in mapper.enrich(fields, {}) if "khuyetTat" in f["name"]}


def test_nhom_co_thi_dong_con_trong_tich_khong_nhom_khong_thi_chi_tich_dong_nhom():
    d = _enrich_iii(["kt1", "kt6"], ["kt1_4", "kt5_2"])
    # Dòng con "Có" kéo nhóm cha thành "Có".
    assert d["data[khuyetTat5Obj][khuyetTatRadio]"] == "co"
    assert d["data[khuyetTat5Obj][khuyetTatRadio2]"] == "co"
    assert d["data[khuyetTat5Obj][khuyetTatRadio1]"] == "khong"
    assert d["data[khuyetTat1Obj][khuyetTatRadio4]"] == "co"
    assert d["data[khuyetTat1Obj][khuyetTatRadio1]"] == "khong"
    # Nhóm "Có" mà không dòng con nào "Có" → mọi dòng con "Không".
    assert [d[f"data[khuyetTat6Obj][khuyetTatRadio{i}]"] for i in (1, 2, 3)] == ["khong"] * 3
    # Nhóm không "Có": dòng nhóm "Không", dòng con không tích.
    assert d["data[khuyetTat2Obj][khuyetTatRadio]"] == "khong"
    assert "data[khuyetTat2Obj][khuyetTatRadio1]" not in d


def test_muc_iii_bo_trong_thi_khong_tich_gi():
    assert _enrich_iii([], []) == {}


def test_luot_muc_do_lay_muc_tu_4_o_da_chep(monkeypatch):
    import json

    from app.pipelines.khuyet_tat.process import muc_do

    rows = [
        {"so": "1", "o_danh_dau": ["", "X", "", ""], "muc": "THD"},  # "muc" lệch với ô đã chép → tin ô
        {"so": "3", "o_danh_dau": ["", "", "", "X"], "muc": "KXD"},
        {"so": "4", "o_danh_dau": ["X", "", "X", ""], "muc": "THD"},  # 2 ô có dấu → bỏ
        {"so": "5", "o_danh_dau": ["", "X", ""], "muc": "CTG"},  # vỡ dòng → bỏ
    ]

    async def fake_chat(messages, **kwargs):
        assert not kwargs.get("enable_thinking")
        return json.dumps({"dong": rows})

    monkeypatch.setattr(muc_do.client, "chat", fake_chat)
    out = asyncio.run(muc_do.read_activity_levels([{"text": "bảng"}]))
    assert out == {"1": "CTG", "3": "KXD"}


def test_luot_muc_do_thay_ket_qua_luot_chinh():
    from app.pipelines.khuyet_tat.process import muc_do

    async def levels():
        return {"1": "CTG"}

    async def go():
        res = {"fields": [{"name": "MucDo_HoatDong", "comp": "raw", "value": {"1": "THD", "2": "THD"}}]}
        await muc_do.apply_levels(res, [asyncio.create_task(levels())])
        return res

    assert asyncio.run(go())["fields"] == [{"name": "MucDo_HoatDong", "comp": "raw", "value": {"1": "CTG"}}]

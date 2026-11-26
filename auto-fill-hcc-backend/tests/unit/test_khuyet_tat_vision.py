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
    assert d["data[NktHoTen]"] == "NGUYỄN VĂN CON"


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
    # Nhóm "Có" mà không dòng con nào "Có" → mọi dòng con "Có".
    assert [d[f"data[khuyetTat6Obj][khuyetTatRadio{i}]"] for i in (1, 2, 3)] == ["co"] * 3
    # Nhóm không "Có": dòng nhóm "Không", dòng con không tích.
    assert d["data[khuyetTat2Obj][khuyetTatRadio]"] == "khong"
    assert "data[khuyetTat2Obj][khuyetTatRadio1]" not in d


def test_muc_iii_bo_trong_thi_khong_tich_gi():
    assert _enrich_iii([], []) == {}


_MUC_DO_OCR = (
    "| 1.1 | Mềm nhão hoặc co cứng toàn thân | X | |\n"
    "2. Thông tin về mức độ khuyết tật\n"
    "| Các hoạt động | Mức độ thực hiện | Thực hiện được | Thực hiện được nhưng cần trợ giúp "
    "| Không thực hiện được | Không xác định được |\n"
    "|---|---|---|---|---|---|\n"
    "| 1. Đi lại | | X | | | | |\n"
    "| 2. Ăn, uống | | | X | |\n"
    "| 3. Tiểu tiện | | X | | X | |\n"
    "| 7. Diễn đạt ý muốn | | | X | | | |\n"
    "Người viết đơn\n"
)


def test_muc_do_trinh_bay_bang_danh_so_o_tu_hang_tieu_de():
    """Python chỉ tách ô từ hàng tiêu đề tới hết bảng (bỏ bảng dạng khuyết tật phía trên, dòng kẻ, chân đơn)."""
    from app.pipelines.khuyet_tat.process import muc_do

    rows = muc_do.table_lines(_MUC_DO_OCR)
    assert [r[0] for r in rows] == ["Các hoạt động", "1. Đi lại", "2. Ăn, uống", "3. Tiểu tiện", "7. Diễn đạt ý muốn"]
    assert rows[1] == ["1. Đi lại", "", "X", "", "", "", ""]
    text = muc_do.render_table(rows)
    assert "L2: [1] 1. Đi lại | [2] (trống) | [3] X | [4] (trống)" in text
    # Hàng tiêu đề mở đầu bằng ô trống vẫn nhận ra.
    assert muc_do.table_lines("| | Mức độ thực hiện Các hoạt động | A | B | C | D |\n| 1. Đi lại | | X | | | |")[0][1] \
        == "Mức độ thực hiện Các hoạt động"
    # OCR mất cột (không còn dấu |) → không có bảng → không gọi model.
    assert muc_do.table_lines("Các hoạt động Mức độ thực hiện\n1. Đi lại X") == []


def _item(so, dong, o_dau, muc, o_ten=1, tieu_de="L1"):
    return {"so": so, "dong": dong, "tieu_de": tieu_de, "o_ten": o_ten, "o_dau": o_dau, "muc": muc}


def test_muc_do_lay_dung_muc_model_khi_khop_bang():
    """Dòng dư ô cuối (N ≥ H) gióng thẳng; dòng thiếu ô đầu (N < H) gióng phải — mức là của model."""
    from app.pipelines.khuyet_tat.process import muc_do

    rows = muc_do.table_lines(_MUC_DO_OCR)
    data = {"dong": [_item("1", "L2", 3, "THD"), _item("2", "L3", 4, "kthd"), _item("7", "L5", 4, "CTG")]}
    assert muc_do.levels_from(data, rows) == {"1": "THD", "2": "KTHD", "7": "CTG"}


def test_muc_do_bo_dong_lech_bang_khong_tu_thay_muc():
    """Model trả mức lệch cột / số dòng đánh lại / ô không có dấu / 2 dấu → bỏ dòng, không thay bằng mức khác."""
    from app.pipelines.khuyet_tat.process import muc_do

    rows = muc_do.table_lines(_MUC_DO_OCR)
    data = {"dong": [
        _item("1", "L2", 3, "CTG"),   # dấu ở cột THD mà model trả CTG
        _item("3", "L3", 4, "KTHD"),  # dòng L3 là hoạt động 2, model đánh số lại thành 3
        _item("2", "L3", 3, "CTG"),   # ô model chỉ ra không có dấu
        _item("3", "L4", 3, "THD"),   # dòng có 2 dấu
        _item("7", "L5", 4, "XYZ"),   # mã lạ
    ]}
    assert muc_do.levels_from(data, rows) is None


def test_luot_muc_do_goi_model_voi_bang_da_danh_so(monkeypatch):
    import json

    from app.pipelines.khuyet_tat.process import muc_do

    seen = {}

    async def fake_chat(messages, **kwargs):
        seen["user"] = messages[1]["content"]
        assert not kwargs.get("enable_thinking")
        return json.dumps({"dong": [_item("7", "L5", 4, "CTG")]})

    monkeypatch.setattr(muc_do.client, "chat", fake_chat)
    assert asyncio.run(muc_do.read_activity_levels([{"text": _MUC_DO_OCR}])) == {"7": "CTG"}
    assert seen["user"].startswith("BẢNG:\nL1: [1] Các hoạt động")

    async def must_not_call(*args, **kwargs):
        raise AssertionError("không có bảng thì không gọi model")

    monkeypatch.setattr(muc_do.client, "chat", must_not_call)
    assert asyncio.run(muc_do.read_activity_levels([{"text": "1. Đi lại X"}])) is None


def test_luot_muc_do_thay_ket_qua_luot_chinh():
    from app.pipelines.khuyet_tat.process import muc_do

    async def levels():
        return {"1": "CTG"}

    async def go():
        res = {"fields": [{"name": "MucDo_HoatDong", "comp": "raw", "value": {"1": "THD", "2": "THD"}}]}
        await muc_do.apply_levels(res, [asyncio.create_task(levels())])
        return res

    assert asyncio.run(go())["fields"] == [{"name": "MucDo_HoatDong", "comp": "raw", "value": {"1": "CTG"}}]

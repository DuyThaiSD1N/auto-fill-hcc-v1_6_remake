"""Thành lập HKD: Qwen đọc ảnh chạy song song với OCR + LLM, chỉ dùng khi OCR + LLM có dấu hiệu hỏng và chỉ thay đúng
trường hỏng. Dữ liệu giả."""

import asyncio

from app.pipelines.dang_ky_kinh_doanh.process import runner, vision

_GOOD = {
    "ChuHo_SoDinhDanh": "001083000001",
    "NguoiNop_SoDinhDanh": "001083000001",
    "ChuHo_DienThoai": "0900000001",
    "TruSo_DienThoai": "0900000001",
    "Von_SoTien": "50000000",
    "NganhNghe_DanhSach": [{"ma": "4761", "ten": "Bán lẻ sách", "chinh": True}],
    "NganhNghe_MaChinh": "4761",
}
_LOOP = "3. Ngành | " + "Bản tê-tô-" * 12


def _fields(**over):
    return [{"name": k, "value": v} for k, v in dict(_GOOD, **over).items()]


def test_ho_so_doc_on_khong_bi_coi_la_hong():
    assert vision.broken_fields(dict(_GOOD), "Số: ............ ____") == set()


def test_dau_hieu_hong():
    values = dict(_GOOD, ChuHo_SoDinhDanh="00108300001", ChuHo_DienThoai="090000001", Von_SoTien=None,
                  NganhNghe_DanhSach=[{"ma": "", "ten": "Quán ăn"}])
    assert vision.broken_fields(values) == {"ChuHo_SoDinhDanh", "ChuHo_DienThoai", "Von_SoTien", "NganhNghe_DanhSach"}
    assert vision.broken_fields(dict(_GOOD), _LOOP) == {"NganhNghe_DanhSach"}


def test_ma_nganh_cut_chu_so_la_hong_du_con_ma_hop_le():
    rows = [{"ma": "4659", "ten": "A", "chinh": True}, {"ma": "471", "ten": "B"}, {"ma": "", "ten": "C"}]
    assert vision.broken_fields(dict(_GOOD, NganhNghe_DanhSach=rows)) == {"NganhNghe_DanhSach"}
    rows = [{"ma": "4659", "ten": "A", "chinh": True}, {"ma": "", "ten": "C"}]
    assert vision.broken_fields(dict(_GOOD, NganhNghe_DanhSach=rows)) == set()


def test_patch_chi_thay_truong_hong_va_gia_tri_hop_le():
    fields = _fields(ChuHo_SoDinhDanh="00108300001", NguoiNop_SoDinhDanh="00108300001", Von_SoTien=None)
    data = {"so_dinh_danh": "001083000099", "dien_thoai": "0999999999", "von": "60.000.000",
            "nganh_nghe": [{"ma": "9999", "ten": "X", "chinh": True}]}
    patched = vision.patch(fields, {"ChuHo_SoDinhDanh", "Von_SoTien"}, data)
    v = {f["name"]: f["value"] for f in fields}
    assert patched == ["ChuHo_SoDinhDanh", "NguoiNop_SoDinhDanh", "Von_SoTien"]
    assert v["ChuHo_SoDinhDanh"] == v["NguoiNop_SoDinhDanh"] == "001083000099"
    assert v["Von_SoTien"] == "60000000"
    # Trường không hỏng giữ nguyên dù đọc ảnh ra khác.
    assert v["ChuHo_DienThoai"] == "0900000001" and v["NganhNghe_MaChinh"] == "4761"


def test_patch_bo_qua_gia_tri_doc_anh_sai_do_dai():
    fields = _fields(ChuHo_SoDinhDanh="00108300001")
    assert vision.patch(fields, {"ChuHo_SoDinhDanh"}, {"so_dinh_danh": "00108300002"}) == []


def test_patch_bang_nganh_chi_thay_khi_nhieu_ma_hon():
    rows = [{"ma": "4761", "ten": "A", "chinh": False}, {"ma": "4763", "ten": "B", "chinh": True}]
    fields = _fields()
    vision.patch(fields, {"NganhNghe_DanhSach"}, {"nganh_nghe": rows})
    v = {f["name"]: f["value"] for f in fields}
    assert [r["ma"] for r in v["NganhNghe_DanhSach"]] == ["4761", "4763"] and v["NganhNghe_MaChinh"] == "4763"
    fields = _fields()
    assert vision.patch(fields, {"NganhNghe_DanhSach"}, {"nganh_nghe": [{"ma": "4762", "ten": "C"}]}) == []


def _run(monkeypatch, fields, vision_data, calls):
    async def fake_compact(_files_by_role, **_kw):
        await asyncio.sleep(0.01)  # OCR + LLM mất thời gian: lượt đọc ảnh phải bắt đầu trong lúc này
        calls.append("compact_done")
        return {"fields": fields, "errors": [], "ocr_text": ""}

    async def fake_vision(_files):
        calls.append("vision_start")
        try:
            await asyncio.sleep(0.02)
        except asyncio.CancelledError:
            calls.append("vision_cancelled")
            raise
        calls.append("vision_done")
        return vision_data

    monkeypatch.setattr(runner.runner, "run", fake_compact)
    monkeypatch.setattr(vision, "read_application", fake_vision)
    return asyncio.run(runner.run({"doc": []}, {}))


def test_runner_doc_anh_song_song_ho_so_on_thi_huy(monkeypatch):
    calls = []
    res = _run(monkeypatch, _fields(), {"so_dinh_danh": "001083000099"}, calls)
    assert calls == ["vision_start", "compact_done", "vision_cancelled"]
    assert "visionPatched" not in res.get("extracted", {})


def test_runner_ho_so_hong_cho_doc_anh_roi_thay(monkeypatch):
    calls = []
    res = _run(monkeypatch, _fields(ChuHo_SoDinhDanh="00108300001"), {"so_dinh_danh": "001083000099"}, calls)
    assert calls == ["vision_start", "compact_done", "vision_done"]
    assert res["extracted"]["visionPatched"][0] == "ChuHo_SoDinhDanh"


def test_runner_doc_anh_khong_cuu_duoc_thi_canh_bao(monkeypatch):
    calls = []
    res = _run(monkeypatch, _fields(ChuHo_SoDinhDanh="00108300001"), {"so_dinh_danh": ""}, calls)
    assert "vision_done" in calls
    assert any("không đủ 12 số" in e for e in res.get("errors", []))


def test_patch_bu_so_lao_dong_va_phuong_phap_thue_khi_llm_bo_trong():
    fields = _fields(ChuHo_SoDinhDanh="00108300001")
    data = {"so_lao_dong": "1", "phuong_phap_thue": "Phương pháp kê khai"}
    patched = vision.patch(fields, {"ChuHo_SoDinhDanh"}, data)
    assert patched == ["Thue_PhuongPhapTinh", "Thue_SoLaoDong"]
    fields = _fields(Thue_SoLaoDong="3", Thue_PhuongPhapTinh="Phương pháp khoán")
    assert vision.patch(fields, {"Von_SoTien"}, data) == []

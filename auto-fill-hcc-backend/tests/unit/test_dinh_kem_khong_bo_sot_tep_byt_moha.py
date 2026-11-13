"""Đính kèm không bỏ sót tệp (thủ tục Bộ Y tế / MOHA): giấy chưa rõ loại và CCCD không có dòng riêng vẫn ra một mục ở
dòng cố định (thường là dòng Đơn / Tờ khai), giữ tên tệp gốc + một cảnh báo liệt kê các tệp đã đính chung."""

import asyncio
import json

from app.pipelines.cap_chung_chi_hanh_nghe_duoc.attach import planner as cchn_duoc
from app.pipelines.cap_lai_dieu_chinh_gcn_du_dieu_kien_kinh_doanh_duoc_so_y_te.attach import planner as gcn_duoc_attach
from app.pipelines.cap_lai_dieu_chinh_gcn_du_dieu_kien_kinh_doanh_duoc_so_y_te.attach.dinh_kem_tach import planner as gcn_duoc
from app.pipelines.cap_lai_to_quoc_ghi_cong.attach import planner as tqgc
from app.pipelines.cap_moi_giay_phep_hoat_dong_kham_benh_chua_benh.attach import planner as kcb
from app.pipelines.cong_bo_du_dk_tiem_chung.attach import planner as tiem_chung
from app.pipelines.dieu_chinh_giay_phep_hanh_nghe_chuyen_tiep.attach import planner as gphn
from app.pipelines.giai_quyet_che_do_khang_chien.attach import planner as khang_chien
from app.pipelines.khuyet_tat.attach import planner as khuyet_tat
from app.pipelines.sua_doi_thong_tin_ho_so_nguoi_co_cong.attach import planner as sua_doi
from app.pipelines.tro_cap_tho_cung_liet_si.attach import planner as tho_cung
from app.pipelines.uu_dai_ncc_tu_tran.attach import planner as tu_tran
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client as llm_client

_LA = "Noi dung giay to khong khop mau nao trong bang thanh phan ho so cua thu tuc nay"
_CCCD = "CĂN CƯỚC CÔNG DÂN Citizen Identity Card số 001000000001 họ và tên NGUYEN VAN A"


def _files(*names):
    return [{"name": n, "type": "application/pdf", "dataUrl": ""} for n in names]


def _ocr(**texts):
    return [{"name": f"{k}.pdf", "text": v} for k, v in texts.items()]


def _by_file(items):
    return {i["fileName"]: i for i in items}


def test_cchn_duoc_tep_la_va_cccd_vao_dong_don():
    items, warnings, classified = cchn_duoc.build_plan_items(
        _files("la.pdf", "cccd.pdf"), _ocr(la=_LA, cccd=_CCCD), {0: "other", 1: "cccd"})
    by = _by_file(items)
    assert by["la.pdf"]["componentName"] == by["cccd.pdf"]["componentName"] == "Đơn đề nghị cấp Chứng chỉ hành nghề dược"
    assert by["la.pdf"]["documentName"] == "la.pdf" and by["la.pdf"]["detectedType"] == "other"
    assert classified[0]["routedTo"] == "don_de_nghi"
    assert len(warnings) == 1 and "la.pdf" in warnings[0]


def _gcn_plan(segments, texts):
    files = [{"name": f"f{i}.pdf"} for i in range(len(texts))]
    meta = {i: {"pageCount": 1, "pageBoundariesAvailable": False} for i in range(len(texts))}
    return gcn_duoc.build_plan_items(files, segments, meta, {i: {} for i in range(len(texts))}, dict(enumerate(texts)))


def _seg(i, t):
    return {"fileIndex": i, "pageFrom": 1, "pageTo": 1, "type": t, "documentName": ""}


def test_gcn_duoc_tep_la_va_cccd_vao_dong_don_cap_lai():
    items, classified, warnings = _gcn_plan([_seg(0, "other"), _seg(1, "cccd")], [_LA, _CCCD])
    assert [(i["fileName"], i["componentIndex"], i["detectedType"], i["documentName"]) for i in items] == [
        ("f0.pdf", 1, "other", "f0"), ("f1.pdf", 1, "cccd", "f1")]
    assert all(i["target"] == "attp-row" and "sourceSegments" not in i for i in items)
    assert [c["routedTo"] for c in classified] == ["don_cap_lai"] * 2
    assert any("f0.pdf, f1.pdf" in w for w in warnings)


def test_gcn_duoc_ho_so_dieu_chinh_thi_vao_dong_don_dieu_chinh():
    items, _, _ = _gcn_plan([_seg(0, "don_dieu_chinh"), _seg(1, "other")], ["Đơn đề nghị điều chỉnh", _LA])
    assert [(i["fileName"], i["componentIndex"]) for i in items] == [("f0.pdf", 3), ("f1.pdf", 3)]


def test_kcb_cccd_vao_dong_giay_to_chung_minh():
    items, warnings, classified = kcb.build_plan_items(_files("la.pdf", "cccd.pdf"), {0: ["other"], 1: ["cccd"]})
    assert [(i["fileName"], i["componentIndex"], i["detectedType"], i["documentName"]) for i in items] == [
        ("la.pdf", 5, "other", "la.pdf"), ("cccd.pdf", 5, "cccd", "cccd.pdf")]
    assert [c.get("routedTo") for c in classified] == ["giay_to_chung_minh"] * 2
    assert len(warnings) == 1 and "la.pdf, cccd.pdf" in warnings[0]


def test_gphn_chuyen_tiep_cccd_vao_dong_don():
    items, warnings, _ = gphn.build_plan_items(_files("la.pdf", "cccd.pdf"), {0: "other", 1: "cccd"})
    assert [(i["fileName"], i["componentIndex"], i["detectedType"], i["documentName"]) for i in items] == [
        ("la.pdf", 1, "other", "la.pdf"), ("cccd.pdf", 1, "cccd", "cccd.pdf")]
    assert len(warnings) == 1 and "la.pdf, cccd.pdf" in warnings[0]


def test_tiem_chung_tep_la_va_cccd_vao_dong_duy_nhat():
    items, warnings, classified = tiem_chung.build_plan_items(
        _files("tb.pdf", "la.pdf", "cccd.pdf"), _ocr(tb="", la=_LA, cccd=_CCCD),
        {0: "thong_bao", 1: "other", 2: "cccd"})
    assert [(i["fileName"], i["componentIndex"], i["detectedType"]) for i in items] == [
        ("tb.pdf", 1, "thong_bao"), ("la.pdf", 1, "other"), ("cccd.pdf", 1, "cccd")]
    assert [c.get("routedTo") for c in classified[1:]] == ["thong_bao"] * 2
    assert any("la.pdf, cccd.pdf" in w for w in warnings)


def test_khuyet_tat_tep_la_va_cccd_vao_o_don():
    items, warnings, classified = khuyet_tat.build_plan_items(_files("la.pdf", "cccd.pdf"), _ocr(la=_LA, cccd=_CCCD), {})
    assert [(i["fileName"], i["slotKey"], i["detectedType"], i["documentName"]) for i in items] == [
        ("la.pdf", "disability_application_form", "other", "la.pdf"),
        ("cccd.pdf", "disability_application_form", "cccd", "cccd.pdf")]
    assert all(i["target"] == "fixed-slot" for i in items)
    assert [c["routedTo"] for c in classified] == ["disability_application_form"] * 2
    assert len(warnings) == 1 and "la.pdf, cccd.pdf" in warnings[0]


def test_tqgc_tep_la_vao_o_don_cccd_vao_giay_to_khac():
    items, warnings, _ = tqgc.build_plan_items(_files("la.pdf", "cccd.pdf"), _ocr(la=_LA, cccd=_CCCD), {0: "other"})
    by = _by_file(items)
    assert by["la.pdf"]["target"] == "fixed-slot" and by["la.pdf"]["slotIndex"] == 0
    assert by["cccd.pdf"]["target"] == "new"
    assert by["la.pdf"]["documentName"] == "la.pdf" and by["la.pdf"]["detectedType"] == "other"
    assert len(warnings) == 1 and "la.pdf" in warnings[0]


def test_sua_doi_giay_nguon_khac_va_tep_la_vao_o_don():
    items, warnings, classified = sua_doi.build_plan_items(
        _files("la.pdf", "bk.pdf", "cccd.pdf"), _ocr(la=_LA, bk="", cccd=_CCCD), {0: "other", 1: "ban_khai"})
    assert [(i["fileName"], i["slotKey"], i["detectedType"]) for i in items] == [
        ("la.pdf", "don_mau_26", "other"), ("bk.pdf", "don_mau_26", "ban_khai"), ("cccd.pdf", "cccd", "CCCD/CMND")]
    assert [c.get("routedTo") for c in classified] == ["don_mau_26", "don_mau_26", None]
    assert len(warnings) == 1 and "la.pdf, bk.pdf" in warnings[0]


def test_khang_chien_cccd_bhxh_va_tep_la_vao_o_ban_khai():
    items, warnings, _ = khang_chien.build_plan_items(
        _files("la.pdf", "cccd.pdf", "bhxh.pdf"), _ocr(la=_LA, cccd=_CCCD, bhxh=""),
        {0: "other", 1: "cccd", 2: "so_bhxh"})
    assert [(i["fileName"], i["slotKey"], i["detectedType"], i["documentName"]) for i in items] == [
        ("la.pdf", "ban_khai", "other", "la.pdf"), ("cccd.pdf", "ban_khai", "cccd", "cccd.pdf"),
        ("bhxh.pdf", "ban_khai", "so_bhxh", "bhxh.pdf")]
    assert len(warnings) == 1 and "la.pdf, cccd.pdf, bhxh.pdf" in warnings[0]


_BLANK_2 = "\n".join(f"───── Trang {n + 1}/2 ─────\n(1)" for n in range(2))


def test_tho_cung_tach_tep_toan_trang_trang_dinh_nguyen_vao_o_don():
    items, warnings, classified = tho_cung.build_plan_items(
        [{"name": "trang.pdf"}], [{"name": "trang.pdf", "text": _BLANK_2}], {}, {0: ["other", "other"]})
    assert [(i["slotKey"], i["fileName"]) for i in items] == [("don_de_nghi", "trang.pdf")]
    assert "sourceSegments" not in items[0] and classified[0]["routedTo"] == "don_de_nghi"
    assert "nguyên tệp" in warnings[0]


def test_tho_cung_tep_la_va_cccd_vao_o_don():
    items, _, _ = tho_cung.build_plan_items(_files("la.pdf", "cccd.pdf"), _ocr(la=_LA, cccd=_CCCD), {0: "other"})
    assert [(i["fileName"], i["slotKey"]) for i in items] == [("la.pdf", "don_de_nghi"), ("cccd.pdf", "don_de_nghi")]


def test_tu_tran_tach_tep_toan_trang_trang_dinh_nguyen_vao_o_ban_khai():
    items, warnings, classified = tu_tran.build_plan_items(
        [{"name": "trang.pdf"}], [{"name": "trang.pdf", "text": _BLANK_2}], {}, {0: ["other", "other"]})
    assert [(i["slotKey"], i["fileName"]) for i in items] == [("ban_khai", "trang.pdf")]
    assert "sourceSegments" not in items[0] and classified[0]["routedTo"] == "ban_khai"
    assert "nguyên tệp" in warnings[0]


def test_tu_tran_tep_la_va_cccd_vao_o_ban_khai():
    items, _, _ = tu_tran.build_plan_items(_files("la.pdf", "cccd.pdf"), _ocr(la=_LA, cccd=_CCCD), {0: "other"})
    assert [(i["fileName"], i["slotKey"]) for i in items] == [("la.pdf", "ban_khai"), ("cccd.pdf", "ban_khai")]

# ── GCN đủ ĐKKD dược: hai chế độ đính kèm theo cài đặt "Tách giấy tờ" (gọi qua bộ điều phối) ──

_DUOC_PAGES = [
    "ĐƠN ĐỀ NGHỊ ĐIỀU CHỈNH GIẤY CHỨNG NHẬN ĐỦ ĐIỀU KIỆN KINH DOANH DƯỢC Kính gửi: Sở Y tế. Nội dung xin điều chỉnh",
    "GIẤY CHỨNG NHẬN ĐĂNG KÝ HỘ KINH DOANH Tên hộ kinh doanh: NHÀ THUỐC MINH AN",
    "CHỨNG CHỈ HÀNH NGHỀ DƯỢC Số: 000001/CCHN-D-SYT Họ và tên: NGUYEN VAN A",
    _CCCD,
]
_DUOC_GOP = "\n".join(f"───── Trang {i + 1}/{len(_DUOC_PAGES)} ─────\n{t}" for i, t in enumerate(_DUOC_PAGES))


def _duoc_patch(monkeypatch, texts, segments=None, doc_types=None, split_raises=False):
    """OCR theo tên tệp; LLM trả `segments` cho lượt chia giấy, `doc_types` cho lượt phân loại không tách."""
    calls = []

    async def fake_ocr(files, **_):
        return [{"name": f["name"], "text": texts.get(f["name"], "")} for f in files]

    async def fake_chat(messages, **_):
        system = messages[0]["content"]
        mode = "tach" if "PHÂN ĐOẠN" in system else "khong_tach"
        calls.append(mode)
        if mode == "tach":
            if split_raises:
                raise RuntimeError("llm chia giấy hỏng")
            return json.dumps({"documents": segments or []})
        return json.dumps({"documents": [{"index": i, "docTypes": t} for i, t in (doc_types or {}).items()]})

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(llm_client, "chat", fake_chat)
    return calls


def _duoc_files(*names):
    return [FileItem(name=n, type="image/jpeg" if n.endswith(".jpg") else "application/pdf", dataUrl="", role="")
            for n in names]


def test_gcn_duoc_bat_tach_pdf_gop_tach_dung_dong_khong_sot_trang(monkeypatch):
    calls = _duoc_patch(monkeypatch, {"hoso.pdf": _DUOC_GOP}, segments=[
        {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "don_dieu_chinh"},
        {"fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "giay_to_phap_ly"},
        {"fileIndex": 0, "pageFrom": 3, "pageTo": 3, "type": "cchn_duoc"},
        # trang 4 (CCCD) LLM bỏ sót → hậu xử lý bù đoạn, rule OCR nhận CCCD → dòng Đơn điều chỉnh.
    ])
    res = asyncio.run(gcn_duoc_attach.plan(_duoc_files("hoso.pdf"), {"splitDocuments": True}))
    got = [(i["componentIndex"], i["detectedType"], i["sourceSegments"][0]["pageIndexes"]) for i in res["attachments"]]
    assert got == [(3, "don_dieu_chinh", [0]), (5, "giay_to_phap_ly", [1]), (4, "cchn_duoc", [2]), (3, "cccd", [3])]
    pages = sorted(p for i in res["attachments"] for s in i["sourceSegments"] for p in s["pageIndexes"])
    assert pages == [0, 1, 2, 3]
    assert all(i["target"] == "attp-row" and i["loaiBan"] == "Bản chính" for i in res["attachments"])
    assert calls == ["tach"]


def test_gcn_duoc_tat_tach_moi_tep_mot_muc_dung_dong_giay_chinh(monkeypatch):
    texts = {"don.pdf": "ĐƠN ĐỀ NGHỊ CẤP LẠI GIẤY CHỨNG NHẬN ĐỦ ĐIỀU KIỆN KINH DOANH DƯỢC",
             "gop.pdf": _DUOC_GOP, "cccd.jpg": _CCCD, "la.pdf": _LA}
    doc_types = {0: ["don_cap_lai"], 1: ["giay_to_phap_ly", "cchn_duoc", "cccd"], 2: ["cccd"]}  # la.pdf LLM bỏ sót
    for options in ({}, None, {"splitDocuments": False}, {"splitDocuments": "true"}):
        calls = _duoc_patch(monkeypatch, texts, doc_types=doc_types)
        res = asyncio.run(gcn_duoc_attach.plan(_duoc_files("don.pdf", "gop.pdf", "cccd.jpg", "la.pdf"), options))
        items = res["attachments"]
        assert sorted(i["fileIndex"] for i in items) == [0, 1, 2, 3]
        assert all("sourceSegments" not in i and i["target"] == "attp-row" and i["loaiBan"] == "Bản chính"
                   and i["needsAddComponent"] is False for i in items)
        by = _by_file(items)
        assert {n: by[n]["componentIndex"] for n in by} == {"don.pdf": 1, "gop.pdf": 4, "cccd.jpg": 1, "la.pdf": 1}
        assert by["don.pdf"]["componentName"] == "Đơn đề nghị cấp lại Giấy chứng nhận đủ điều kiện kinh doanh dược"
        assert by["gop.pdf"]["detectedType"] == "cchn_duoc"
        assert by["gop.pdf"]["documentName"] == "gop" and by["la.pdf"]["documentName"] == "la"
        assert any("gop.pdf" in e and "dòng 5" in e for e in res["errors"])
        assert any("cccd.jpg, la.pdf" in e for e in res["errors"])
        assert calls == ["khong_tach"]


def test_gcn_duoc_tach_loi_quay_ve_dinh_nguyen_tep(monkeypatch):
    calls = _duoc_patch(monkeypatch, {"hoso.pdf": _DUOC_GOP}, split_raises=True,
                        doc_types={0: ["giay_to_phap_ly", "don_dieu_chinh", "cchn_duoc"]})
    res = asyncio.run(gcn_duoc_attach.plan(_duoc_files("hoso.pdf"), {"splitDocuments": True}))
    assert [(i["fileName"], i["componentIndex"], i["detectedType"]) for i in res["attachments"]] == [
        ("hoso.pdf", 3, "don_dieu_chinh")]
    assert "sourceSegments" not in res["attachments"][0]
    assert any("(tách)" in e for e in res["errors"])
    assert calls == ["tach", "khong_tach"]

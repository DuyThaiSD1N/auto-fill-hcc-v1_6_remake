"""Đính kèm [BN] Cấp đổi GCN (1.012783): khớp thành phần theo MÃ TP-H05, CCCD/ủy quyền → đính kèm khác."""

from app.pipelines.cap_doi_gcn_bac_ninh.attach.planner import (
    _ROUTE,
    _build_item,
)

_FILE = {"name": "x.pdf"}


def _item(doc_type: str) -> dict:
    return _build_item(_FILE, 0, doc_type, "Tài liệu")


def test_component_names_are_tp_h05_codes():
    """componentName phải là mã TP-H05 (FE khớp substring) — KHÔNG dùng nhãn 'Bản gốc...' hay trượt."""
    assert _ROUTE["application"][1] == "TP-H05.000026"
    assert _ROUTE["land_certificate"][1] == "TP-H05.000040"


def test_application_and_gcn_route_to_existing_slots():
    app = _item("application")
    assert app["target"] == "existing"
    assert app["componentName"] == "TP-H05.000026"
    assert app["slotKey"] == "banChinh"

    gcn = _item("land_certificate")
    assert gcn["target"] == "existing"
    assert gcn["componentName"] == "TP-H05.000040"
    assert gcn["slotKey"] == "banChinh"


def test_identity_and_authorization_and_other_go_supplementary():
    """CCCD/ủy quyền/khác không có ô riêng → 'File đính kèm khác' (không dồn vào ô Đơn 1 file)."""
    for doc_type in ("identity", "authorization", "other"):
        item = _item(doc_type)
        assert item["target"] == "supplementary", doc_type
        assert item["componentName"] == "", doc_type
        assert "slotKey" not in item, doc_type


def test_four_file_case_routes_all_and_attaches_each():
    """Case 4 file (CCCD, ủy quyền, Mẫu 18, GCN) — LLM phân loại → mỗi file 1 item, đính ĐỦ, đúng chỗ."""
    # Thứ tự upload như trace thật: CCCD, ủy quyền, Mẫu 18, GCN.
    llm_types = ["identity", "authorization", "application", "land_certificate"]
    items = [_build_item({"name": f"f{i}.pdf"}, i, t, "Tài liệu") for i, t in enumerate(llm_types)]

    assert len(items) == 4                                    # đính ĐỦ 4 file, không rớt
    by_type = {t: it for t, it in zip(llm_types, items)}
    assert by_type["application"]["componentName"] == "TP-H05.000026"      # Mẫu 18 → ô Đơn
    assert by_type["land_certificate"]["componentName"] == "TP-H05.000040" # GCN → ô GCN
    assert by_type["identity"]["target"] == "supplementary"               # CCCD → File đính kèm khác
    assert by_type["authorization"]["target"] == "supplementary"          # ủy quyền → File đính kèm khác


def test_unknown_type_still_attaches_supplementary():
    """LLM trả type lạ/không rõ → 'other' → supplementary (đính đủ, không bỏ file)."""
    item = _build_item(_FILE, 0, "khong_biet", "Tài liệu")
    assert item["target"] == "supplementary"
    assert item["componentName"] == ""


# ---- Cài đặt "Có tách hồ sơ khi đính kèm": tệp scan gộp cả bộ chia theo trang, mỗi giấy vào đúng ô ----

import asyncio  # noqa: E402
import json  # noqa: E402

from app.pipelines.cap_doi_gcn_bac_ninh import attach  # noqa: E402
from app.pipelines.cap_doi_gcn_bac_ninh.attach import planner, prompt  # noqa: E402
from app.process.schemas import FileItem  # noqa: E402
from app.services import ocr  # noqa: E402

# Bộ mẫu: cam kết hộ gia đình (1) / Đơn Mẫu 18 (2-3) / CCCD (4) / GCN (5-6).
_TRANG_TACH = [
    "BẢN CAM KẾT THÀNH VIÊN HỘ GIA ĐÌNH Chúng tôi gồm: Họ tên: TRẦN VĂN AN là chủ hộ " + "x" * 80,
    "Mẫu số 18. ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT Tên: TRẦN VĂN AN " + "x" * 80,
    "II- XÁC NHẬN CỦA ỦY BAN NHÂN DÂN CẤP XÃ Hướng dẫn kê khai đơn " + "x" * 80,
    "CĂN CƯỚC CÔNG DÂN Số / No.: 001200000001 Họ và tên / Full name: TRẦN VĂN AN " + "x" * 80,
    "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT Hộ ông: Trần Văn An thửa đất số 12 tờ bản đồ số 3 " + "x" * 80,
    "NHỮNG THAY ĐỔI SAU KHI CẤP GIẤY CHỨNG NHẬN " + "x" * 80,
]
_BO_TACH = "\n".join(f"───── Trang {i}/6 ─────\n{body}" for i, body in enumerate(_TRANG_TACH, start=1))


def _pdf_bo_tach() -> str:
    import base64

    import fitz

    with fitz.open() as doc:
        for _ in _TRANG_TACH:
            doc.new_page()
        return "data:application/pdf;base64," + base64.b64encode(doc.tobytes()).decode()


def _fake_ocr_theo_preset(files, *_a, **_k):
    async def _run():
        preset = ocr._preset_texts.get() or {}
        return [{"name": f["name"], "text": preset.get(f["dataUrl"], _BO_TACH)} for f in files]
    return _run()


def _fake_chat_tach(calls):
    async def fake_chat(messages, *_a, **_k):
        calls.append(messages[0]["content"])
        if messages[0]["content"] == prompt.SPLIT_SYSTEM_PROMPT:
            return json.dumps({"tep": [{"fileIndex": 0, "trangDau": [1, 2, 4, 5]}]})
        return json.dumps({"documents": [
            {"index": 0, "type": "other", "documentName": "Bản cam kết thành viên hộ gia đình"},
            {"index": 1, "type": "application", "documentName": "Đơn đăng ký biến động Mẫu số 18"},
            {"index": 2, "type": "identity", "documentName": "Căn cước công dân"},
            {"index": 3, "type": "land_certificate", "documentName": "Bản gốc Giấy chứng nhận QSDĐ"},
        ]})
    return fake_chat


def _bo_ho_so() -> list[FileItem]:
    return [FileItem(name="bo-ho-so.pdf", type="application/pdf", dataUrl=_pdf_bo_tach(), role="")]


def test_tach_giay_to_moi_giay_vao_dung_o(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(ocr, "ocr_per_file", _fake_ocr_theo_preset)
    monkeypatch.setattr(planner.client, "chat", _fake_chat_tach(calls))
    res = asyncio.run(attach.plan(_bo_ho_so(), {"splitDocuments": True}))

    rows = [(a["target"], a["componentName"], a["fileIndex"], a["sourceSegments"]) for a in res["attachments"]]
    assert rows == [
        ("supplementary", "", 0, [{"fileIndex": 0, "pageIndexes": [0]}]),
        ("existing", "TP-H05.000026", 0, [{"fileIndex": 0, "pageIndexes": [1, 2]}]),
        ("supplementary", "", 0, [{"fileIndex": 0, "pageIndexes": [3]}]),
        ("existing", "TP-H05.000040", 0, [{"fileIndex": 0, "pageIndexes": [4, 5]}]),
    ]
    assert res["extracted"]["attachmentMode"] == "split_documents"
    assert res["extracted"]["documents"] == ["bo-ho-so.pdf"]
    assert [t["pages"] for t in res["extracted"]["tachGiayTo"]] == [[1], [2, 3], [4], [5, 6]]


def test_khong_bat_tach_thi_giu_nguyen_tep(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(ocr, "ocr_per_file", _fake_ocr_theo_preset)
    monkeypatch.setattr(planner.client, "chat", _fake_chat_tach(calls))
    # Tắt cài đặt / giá trị không phải boolean / extension không cắt được trang → không tách.
    for options in ({}, {"splitDocuments": False}, {"splitDocuments": "true"},
                    {"splitDocuments": True, "supportsSourceSegments": False}):
        calls.clear()
        res = asyncio.run(attach.plan(_bo_ho_so(), options))
        assert prompt.SPLIT_SYSTEM_PROMPT not in calls
        assert len(res["attachments"]) == 1
        assert all("sourceSegments" not in a for a in res["attachments"])


def test_tach_giay_to_loi_llm_dinh_nguyen_tep(monkeypatch):
    async def fake_chat(messages, *_a, **_k):
        if messages[0]["content"] == prompt.SPLIT_SYSTEM_PROMPT:
            return "không phải JSON"
        return json.dumps({"documents": [{"index": 0, "type": "other", "documentName": ""}]})

    monkeypatch.setattr(ocr, "ocr_per_file", _fake_ocr_theo_preset)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    res = asyncio.run(attach.plan(_bo_ho_so(), {"splitDocuments": True}))
    assert len(res["attachments"]) == 1 and "sourceSegments" not in res["attachments"][0]
    assert res["attachments"][0]["target"] == "supplementary"
    assert any("Tách giấy tờ" in e for e in res["errors"])


def test_registry_bat_tach_giay_to():
    from app.procedures.registry import get_procedure

    assert get_procedure("cap-doi-gcn-bac-ninh")["supportsSplitDocuments"] is True

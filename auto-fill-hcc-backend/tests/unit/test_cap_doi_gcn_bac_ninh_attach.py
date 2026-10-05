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

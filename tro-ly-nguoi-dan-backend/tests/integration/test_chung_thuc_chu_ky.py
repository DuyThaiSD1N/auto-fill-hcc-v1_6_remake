"""Thủ tục chứng thực chữ ký (attach-only, form 2 ô STT1 giấy tờ / STT2 giấy tùy thân).

Lõi TỰ CHỨA theo khuôn native tro-ly (không phụ thuộc chung_thuc_ban_sao / attach_classify).
"""

from app.pipelines.chung_thuc_chu_ky.attach import plan as ck_plan
from app.pipelines.chung_thuc_chu_ky.attach import planner as ck_planner
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure
from app.upload_session.classify import classify_text, route_to_slot


def test_registry_chung_thuc_chu_ky_entry():
    proc = get_procedure("chung-thuc-chu-ky")
    assert proc is not None
    assert get_attach_pipeline("chung-thuc-chu-ky") is ck_plan   # attach map
    assert get_pipeline("chung-thuc-chu-ky") is None             # attach-only → không có process
    assert proc["mode"] == "attach"
    assert proc["requiresConsent"] is False                      # tại quầy, bỏ card consent
    assert "maThuTuc=2.000884" in proc["detect"]["urlIncludes"]
    docs = {r["key"]: r for r in proc["requiredDocs"]}
    assert set(docs) == {"cccd", "khac"}
    # Cả 2 ô repeatable → đếm theo file, không giới hạn (FE hiện "Đã nhận X tệp", không "x/2 mặt").
    assert docs["cccd"].get("repeatable") and docs["khac"].get("repeatable")


def _route(proc, text):
    info = classify_text(text)
    key, _side, _note = route_to_slot(info, proc["requiredDocs"], [], None)
    return key


def test_classify_cccd_vao_o_cccd_van_ban_vao_khac():
    proc = get_procedure("chung-thuc-chu-ky")
    assert _route(proc, "CĂN CƯỚC CÔNG DÂN Số/No.: 001099012345 Nam") == "cccd"
    assert _route(proc, "SƠ YẾU LÝ LỊCH TỰ THUẬT") == "khac"
    assert _route(proc, "HỢP ĐỒNG MUA BÁN") == "khac"
    assert _route(proc, "GIẤY ỦY QUYỀN") == "khac"


def test_build_plan_items_stt1_stt2():
    """Văn bản → STT1 (ô #1); CCCD 2 mặt → STT2 (ô #2) GỘP 1 PDF (sourceFileIndexes)."""
    files = [{"name": "so_yeu.jpg"}, {"name": "cccd_truoc.jpg"}, {"name": "cccd_sau.jpg"}]
    ocr = [{"text": "SƠ YẾU LÝ LỊCH"},
           {"text": "CĂN CƯỚC CÔNG DÂN Nơi thường trú"},
           {"text": "MRZ IDVNM"}]
    llm = {
        0: {"detectedType": "Sơ yếu lý lịch", "documentName": "Sơ yếu lý lịch"},
        1: {"detectedType": "Căn cước công dân", "documentName": "Căn cước công dân"},
        2: {"detectedType": "Căn cước công dân", "documentName": "Căn cước công dân"},
    }
    items = ck_planner.build_plan_items(files, ocr, llm)
    by_slot = {it["componentIndex"]: it for it in items}
    # STT1 = giấy tờ cần chứng thực (văn bản, không gộp)
    assert by_slot[1]["target"] == "existing" and by_slot[1]["fileIndex"] == 0
    assert "sourceFileIndexes" not in by_slot[1]
    # STT2 = giấy tùy thân, gộp 2 mặt CCCD thành 1 đơn vị
    assert by_slot[2]["target"] == "existing"
    assert by_slot[2]["sourceFileIndexes"] == [1, 2]


def test_khong_nham_uy_quyen_thanh_tuy_than():
    """Văn bản ủy quyền có chứa số CCCD của đương sự → KHÔNG được route STT2 (tin detectedType)."""
    assert ck_planner._is_identity("Văn bản ủy quyền", "GIẤY ỦY QUYỀN ... Số CCCD 001...", "uq.jpg") is False
    assert ck_planner._is_identity("Căn cước công dân", "CĂN CƯỚC", "cccd.jpg") is True

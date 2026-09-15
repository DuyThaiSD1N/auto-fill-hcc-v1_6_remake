"""Thủ tục Cấp, cấp lại GP khai thác thủy sản (cổng Bộ NN&MT) — luồng handfree riêng:
choose_variant (cấp mới/cấp lại) → DVCQG chỉ chọn TỈNH (ward rỗng) → trang MAE fill_mae_agency
→ wizard MAE (kê khai bước 1, đính kèm bước 2) → attach_plan mang attach_step=2."""
from app.channels.handfree.chat import flow, intents
from app.channels.handfree.procedure_registry import (
    get_attach_pipeline,
    get_pipeline,
    get_procedure,
    public_list,
)

KEY = "cap-giay-phep-khai-thac-thuy-san"


def _conv(**kw):
    base = {
        "_id": "t-thuy-san", "state": "greet", "history": [],
        "location": {"province": "Tỉnh Quảng Trị", "ward": "Phường Đông Hà"},
    }
    base.update(kw)
    return base


def test_registry_entry_du_pipeline_va_wizard_mae():
    proc = get_procedure(KEY)
    assert proc, "thiếu entry handfree"
    assert get_pipeline(KEY) and get_attach_pipeline(KEY), "key phải trùng core registry"
    assert proc["wizard"] == {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4}
    assert proc["agencyProvinceOnly"] and proc["maePortal"]
    assert {o["key"] for o in proc["variants"]["options"]} == {"cap_moi", "cap_lai"}
    assert any(p["key"] == KEY for p in public_list()), "phải hiện trong danh sách card"
    # Checklist: đơn + CCCD bắt buộc; giấy phép cũ optional cho cấp lại.
    keys = [d["key"] for d in proc["requiredDocs"]]
    assert keys[:2] == ["don", "cccd"]
    assert "giay_phep_cu" in keys


def test_choose_variant_intents_khai_bao_dung_handler():
    entries = {e["value"] for e in intents._STATE_INTENTS["choose_variant"]}
    assert entries == {"variant_cap_moi", "variant_cap_lai"}
    assert KEY in intents._PROCEDURE_HINTS


async def test_confirm_hoi_truong_hop_roi_moi_navigate():
    conv = _conv()
    await flow.handle_turn(conv, intents.Intent("action", "pick_procedure", {"key": KEY}))
    assert conv["state"] == "confirm_procedure"
    r = await flow.handle_turn(conv, intents.Intent("confirm"))
    assert conv["state"] == "choose_variant"
    assert len(r.chips) == 2 and not r.actions, "phải hỏi cấp mới/cấp lại TRƯỚC khi mở trang"

    r2 = await flow.handle_turn(
        conv, intents.Intent("action", "set_variant", {"value": "cap_lai"}))
    assert conv["state"] == "guide_login" and conv["procedure_variant"] == "cap_lai"
    assert r2.actions and r2.actions[0]["type"] == "navigate"
    assert "Sở Nông nghiệp và Môi trường" in r2.display_md


async def test_choose_variant_hieu_cau_noi_llm():
    conv = _conv(state="choose_variant", procedure_key=KEY, procedure_variant="")
    await flow.handle_turn(conv, intents.Intent("action", "variant_cap_moi"))
    assert conv["procedure_variant"] == "cap_moi" and conv["state"] == "guide_login"


async def test_dvcqg_chi_chon_tinh_ward_rong():
    conv = _conv(state="guide_login", procedure_key=KEY, procedure_variant="cap_moi",
                 milestones=[], agency_done=False)
    r = await flow.handle_turn(conv, intents.Intent("event", "page_status", {"agencyBlock": True}))
    action = r.actions[0]
    assert action["type"] == "select_agency"
    assert action["province"] == "Tỉnh Quảng Trị"
    assert action["ward"] == "", "cổng bộ ngành: bỏ qua ô xã, FE tự bấm Đồng ý + Nộp trực tuyến"


async def test_trang_mae_phat_fill_mae_agency_dung_variant():
    conv = _conv(state="guide_login", procedure_key=KEY, procedure_variant="cap_lai",
                 milestones=[], agency_done=True)
    r = await flow.handle_turn(conv, intents.Intent("event", "page_status", {"maeAgencyBlock": True}))
    action = r.actions[0]
    assert action["type"] == "fill_mae_agency"
    assert action["variant"] == "cap_lai" and action["variantMatch"] == "cap lai"
    assert "Cấp lại giấy phép" in r.display_md and "Đồng ý và tiếp tục" in r.display_md
    # say_once: lượt page_status sau im lặng, không đọc lại.
    r2 = await flow.handle_turn(conv, intents.Intent("event", "page_status", {"maeAgencyBlock": True}))
    assert not r2.actions and not r2.display_md


async def test_mae_agency_failed_huong_dan_chon_tay():
    conv = _conv(state="guide_login", procedure_key=KEY, procedure_variant="cap_moi",
                 milestones=["mae_agency_fill"], agency_done=True)
    r = await flow.handle_turn(conv, intents.Intent("event", "mae_agency_failed", {"value": "timeout"}))
    assert "Đồng ý và tiếp tục" in r.display_md and r.chips


def test_docs_target_theo_wizard_mae():
    proc = get_procedure(KEY)
    assert flow._resolve_docs_target(proc, {"wizardStep": 1}) == "declaration"
    assert flow._resolve_docs_target(proc, {"wizardStep": 2}) == "attachment"
    assert flow._resolve_docs_target(proc, {"attachmentTarget": True}) == "attachment"


def test_attach_plan_mang_attach_step_theo_thu_tuc():
    conv = {"procedure_key": KEY, "upload_session_id": "HS-T", "attach_mode": None}
    assert flow._attach_plan_action(conv, [])["attach_step"] == 2
    conv_tp = {"procedure_key": "ket-hon", "upload_session_id": "HS-T", "attach_mode": None}
    assert flow._attach_plan_action(conv_tp, [])["attach_step"] == 3


def test_planner_bo_qua_giay_phep_cu_khong_canh_bao():
    from app.pipelines.cap_giay_phep_khai_thac_thuy_san.attach import planner

    files = [{"name": "don.jpg"}, {"name": "gp-cu.jpg"}, {"name": "cccd.jpg"}]
    ocr = [
        {"name": "don.jpg", "text": "ĐƠN ĐỀ NGHỊ CẤP LẠI GIẤY PHÉP KHAI THÁC THỦY SẢN Mẫu số 05"},
        {"name": "gp-cu.jpg", "text": "GIẤY PHÉP KHAI THÁC THỦY SẢN Số 30/LC/2025 có giá trị đến"},
        {"name": "cccd.jpg", "text": "CĂN CƯỚC CÔNG DÂN 012345678901"},
    ]
    items, warnings, classified = planner.build_plan_items(files, ocr, {})
    assert not warnings, warnings
    assert len(items) == 1 and items[0]["detectedType"] == "don_cap_lai"
    assert items[0]["target"] == "attp-row"
    skipped = {c["fileName"] for c in classified if c.get("skipped")}
    assert skipped == {"gp-cu.jpg", "cccd.jpg"}


def test_upload_classifier_da_dang_ky():
    from app.upload_session.classifier_registry import _CLASSIFIERS

    classifier = _CLASSIFIERS.get(KEY)
    assert classifier is not None and callable(classifier.fallback_to_slot)
    proc = get_procedure(KEY)
    slot, _, _ = classifier.fallback_to_slot(
        "GIẤY PHÉP KHAI THÁC THỦY SẢN Số 30", proc["requiredDocs"], [], None)
    assert slot == "giay_phep_cu"
    slot2, _, _ = classifier.fallback_to_slot(
        "ĐƠN ĐỀ NGHỊ CẤP GIẤY PHÉP KHAI THÁC THỦY SẢN", proc["requiredDocs"], [], None)
    assert slot2 == "don"

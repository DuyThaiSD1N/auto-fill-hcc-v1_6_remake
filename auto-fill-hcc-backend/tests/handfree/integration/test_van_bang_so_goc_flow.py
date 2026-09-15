"""Cấp bản sao văn bằng, chứng chỉ từ sổ gốc (Bộ GD&ĐT — dvc.moet, nền iGate) — luồng handfree:
KHÔNG variant, KHÔNG trang chọn nơi/loại; DVCQG chọn Tỉnh + toggle "Sở" → Sở đầu tiên
(select_agency soMode); wizard kê khai=1, đính kèm=2; attach_plan mang attach_step=2."""
from app.channels.handfree.chat import flow, intents
from app.channels.handfree.procedure_registry import (
    get_attach_pipeline,
    get_pipeline,
    get_procedure,
    public_list,
)

KEY = "cap-ban-sao-van-bang-so-goc"


def _conv(**kw):
    base = {
        "_id": "t-van-bang", "state": "greet", "history": [],
        "location": {"province": "Thành phố Đà Nẵng", "ward": "Phường Hải Châu"},
    }
    base.update(kw)
    return base


def test_registry_entry_du_pipeline_va_wizard_igate():
    proc = get_procedure(KEY)
    assert proc, "thiếu entry handfree"
    assert get_pipeline(KEY) and get_attach_pipeline(KEY), "key phải trùng core registry"
    assert proc["wizard"] == {"ownerStep": 5, "declarationStep": 1, "attachmentStep": 2, "resultStep": 4}
    assert proc["agencyProvinceOnly"] and proc["agencySoFirst"]
    assert "variants" not in proc and "maePortal" not in proc
    assert any(p["key"] == KEY for p in public_list())
    keys = [d["key"] for d in proc["requiredDocs"]]
    assert keys[:3] == ["don", "cccd", "van_bang"]
    assert KEY in intents._PROCEDURE_HINTS


async def test_confirm_khong_hoi_variant_navigate_ngay():
    conv = _conv()
    await flow.handle_turn(conv, intents.Intent("action", "pick_procedure", {"key": KEY}))
    r = await flow.handle_turn(conv, intents.Intent("confirm"))
    assert conv["state"] == "guide_login", "không có variants → đi thẳng guide_login"
    assert r.actions and r.actions[0]["type"] == "navigate"
    assert "Sở Giáo dục và Đào tạo" in r.display_md


async def test_select_agency_so_mode_ward_rong():
    conv = _conv(state="guide_login", procedure_key=KEY, milestones=[], agency_done=False)
    r = await flow.handle_turn(conv, intents.Intent("event", "page_status", {"agencyBlock": True}))
    action = r.actions[0]
    assert action["type"] == "select_agency"
    assert action["ward"] == "", "bỏ qua ô xã"
    assert action["soMode"] is True
    assert "soMatch" not in action, "chỉ gạt toggle Sở, KHÔNG chọn sở cụ thể trong combo"


async def test_trang_ke_khai_igate_vao_nhan_giay_to():
    conv = _conv(state="guide_login", procedure_key=KEY, milestones=[], agency_done=True)
    r = await flow.handle_turn(conv, intents.Intent("event", "page_status", {"wizardStep": 1}))
    assert conv["state"] in ("consent", "ask_doc_method"), conv["state"]
    assert r.cards, "phải hiện card consent/chọn cách gửi giấy tờ"


def test_docs_target_va_attach_step_theo_wizard():
    proc = get_procedure(KEY)
    assert flow._resolve_docs_target(proc, {"wizardStep": 1}) == "declaration"
    assert flow._resolve_docs_target(proc, {"wizardStep": 2}) == "attachment"
    conv = {"procedure_key": KEY, "upload_session_id": "HS-T", "attach_mode": None}
    assert flow._attach_plan_action(conv, [])["attach_step"] == 2


def test_upload_classifier_da_dang_ky():
    from app.upload_session.classifier_registry import _CLASSIFIERS

    classifier = _CLASSIFIERS.get(KEY)
    assert classifier is not None and callable(classifier.fallback_to_slot)
    proc = get_procedure(KEY)
    slot, _, _ = classifier.fallback_to_slot(
        "PHIẾU YÊU CẦU CẤP BẢN SAO VĂN BẰNG CHỨNG CHỈ", proc["requiredDocs"], [], None)
    assert slot == "don"
    slot2, _, _ = classifier.fallback_to_slot(
        "BẰNG TỐT NGHIỆP TRUNG HỌC PHỔ THÔNG hiệu trưởng", proc["requiredDocs"], [], None)
    assert slot2 == "van_bang"
    slot3, _, _ = classifier.fallback_to_slot(
        "GIẤY ỦY QUYỀN cho em trai nộp thay", proc["requiredDocs"], [], None)
    assert slot3 == "uy_quyen"

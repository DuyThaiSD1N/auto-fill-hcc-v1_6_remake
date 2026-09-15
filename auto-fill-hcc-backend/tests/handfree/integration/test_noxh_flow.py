"""Cho thuê, cho thuê mua nhà ở xã hội (Bộ Xây dựng — dvc.moc, nền iGate) — luồng handfree
cùng khuôn văn bằng: KHÔNG variant/trang chọn nơi; DVCQG chọn Tỉnh + gạt toggle "Sở"
(select_agency soMode, không chọn sở cụ thể); wizard kê khai=1, đính kèm=2."""
from app.channels.handfree.chat import flow, intents
from app.channels.handfree.procedure_registry import (
    get_attach_pipeline,
    get_pipeline,
    get_procedure,
    public_list,
)

KEY = "cho-thue-thue-mua-nha-o-xa-hoi"


def _conv(**kw):
    base = {
        "_id": "t-noxh", "state": "greet", "history": [],
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
    assert proc["agencyDeptLabel"] == "Sở Xây dựng"
    assert "variants" not in proc and "maePortal" not in proc
    assert any(p["key"] == KEY for p in public_list())
    keys = [d["key"] for d in proc["requiredDocs"]]
    assert keys[:2] == ["don", "cccd"]
    assert {"doi_tuong", "dieu_kien"} <= set(keys)
    assert KEY in intents._PROCEDURE_HINTS


async def test_confirm_navigate_ngay_khong_variant():
    conv = _conv()
    await flow.handle_turn(conv, intents.Intent("action", "pick_procedure", {"key": KEY}))
    r = await flow.handle_turn(conv, intents.Intent("confirm"))
    assert conv["state"] == "guide_login"
    assert r.actions and r.actions[0]["type"] == "navigate"
    assert "Sở Xây dựng" in r.display_md


async def test_select_agency_so_mode_khong_so_match():
    conv = _conv(state="guide_login", procedure_key=KEY, milestones=[], agency_done=False)
    r = await flow.handle_turn(conv, intents.Intent("event", "page_status", {"agencyBlock": True}))
    action = r.actions[0]
    assert action["type"] == "select_agency"
    assert action["ward"] == "" and action["soMode"] is True
    assert "soMatch" not in action


def test_docs_target_va_attach_step():
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
    docs = proc["requiredDocs"]
    assert classifier.fallback_to_slot(
        "ĐƠN ĐĂNG KÝ THUÊ MUA NHÀ Ở XÃ HỘI", docs, [], None)[0] == "don"
    assert classifier.fallback_to_slot(
        "GIẤY CHỨNG NHẬN THƯƠNG BINH hạng 2/4", docs, [], None)[0] == "doi_tuong"
    assert classifier.fallback_to_slot(
        "XÁC NHẬN HỘ NGHÈO năm 2026 của UBND phường", docs, [], None)[0] == "dieu_kien"

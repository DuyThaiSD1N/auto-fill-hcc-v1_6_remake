"""[BN] Xóa đăng ký biện pháp bảo đảm QSDĐ (1.011443) — anh em với đăng ký (1.011441),
cùng cổng Liferay Bắc Ninh 2 tab CÙNG TRANG (samePageAttach) + tỉnh chọn CỐ ĐỊNH Bắc Ninh
(agencyProvince) + toggle "Sở" (agencySoFirst). Xác nhận capability + luồng điền→đính liền
mạch giống hệt thủ tục đăng ký."""
from app.channels.handfree.chat import flow, intents
from app.channels.handfree.procedure_registry import (
    get_attach_pipeline,
    get_pipeline,
    get_procedure,
    public_list,
)

KEY = "xoa-dang-ky-bien-phap-bao-dam-bac-ninh"


def _conv(**kw):
    base = {
        "_id": "t-xoa-bpbd-bn", "state": "greet", "history": [],
        "location": {"province": "Thành phố Hà Nội", "ward": "Phường Ba Đình"},
    }
    base.update(kw)
    return base


def test_registry_entry_same_page_va_pipeline_noi_core():
    proc = get_procedure(KEY)
    assert proc, "thiếu entry handfree"
    assert get_pipeline(KEY) and get_attach_pipeline(KEY), "key phải trùng core registry"
    assert proc["samePageAttach"] is True
    assert proc["agencyProvince"] == "Bắc Ninh"
    assert proc["agencyProvinceOnly"] and proc["agencySoFirst"]
    assert proc["agencyDeptLabel"] == "Văn phòng Đăng ký đất đai Bắc Ninh"
    assert "variants" not in proc and "maePortal" not in proc and "wizard" not in proc
    assert any(p["key"] == KEY for p in public_list())
    keys = [d["key"] for d in proc["requiredDocs"]]
    assert keys == ["don", "gcn", "hop_dong", "cccd", "khac"]
    assert KEY in intents._PROCEDURE_HINTS


async def test_confirm_navigate_link_uuid_va_thoai_tinh_bac_ninh():
    conv = _conv()
    await flow.handle_turn(conv, intents.Intent("action", "pick_procedure", {"key": KEY}))
    r = await flow.handle_turn(conv, intents.Intent("confirm"))
    assert conv["state"] == "guide_login"
    assert r.actions and r.actions[0]["type"] == "navigate"
    assert r.actions[0]["url"].endswith("019d2bfd-7e53-77ba-aa3f-086a9b9717ba")
    # Đọc tỉnh CỦA THỦ TỤC (Bắc Ninh), không phải tỉnh tài khoản (Hà Nội).
    assert "Bắc Ninh" in r.display_md and "Hà Nội" not in r.display_md


async def test_select_agency_tinh_co_dinh_bac_ninh_so_mode():
    conv = _conv(state="guide_login", procedure_key=KEY, milestones=[], agency_done=False)
    r = await flow.handle_turn(conv, intents.Intent("event", "page_status", {"agencyBlock": True}))
    action = r.actions[0]
    assert action["type"] == "select_agency"
    assert action["province"] == "Bắc Ninh"
    assert action["ward"] == "" and action["soMode"] is True


def test_docs_target_uu_tien_ke_khai_va_attachment_reached():
    proc = get_procedure(KEY)
    ctx = {"formKind": "bacninh", "attachmentTarget": True}
    assert flow._resolve_docs_target(proc, ctx) == "declaration"
    conv = {"procedure_key": KEY}
    assert flow._attachment_page_reached(conv, proc, ctx) is True
    assert flow._attachment_page_reached(conv, proc, {"formKind": "bacninh"}) is False


async def test_fill_report_chay_planner_dinh_kem_ngay(monkeypatch):
    from app.channels.handfree.chat import pipeline_runner

    spawned = []
    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: (spawned.append(coro), coro.close()))
    conv = _conv(
        state="filling", procedure_key=KEY, docs_target="declaration",
        upload_session_id="HS-XOA", auto_attach_after_fill=True, pipeline_status="running",
    )
    r = await flow.handle_turn(
        conv, intents.Intent("action", "fill_report", {"filled": 9, "notFound": []}))
    assert conv["state"] == "attaching"
    assert conv["pipeline_status"] == "running" and conv["attachment_plan_started"] is True
    assert len(spawned) == 1
    assert "Tải thành phần hồ sơ" in r.display_md


async def test_attach_report_tom_tat_hai_buoc():
    conv = _conv(
        state="attaching", procedure_key=KEY, docs_target="attachment",
        upload_session_id="HS-XOA", attach_plan=[{"documentName": "Phiếu 03a"}],
        fill_report={"filled": 9, "notFound": [], "errors": []},
    )
    r = await flow.handle_turn(
        conv, intents.Intent("action", "attach_report", {"attached": 2, "errors": []}))
    assert conv["state"] == "done" and conv["attach_done"] is True
    assert "Tóm tắt" in r.display_md
    assert "điền 9 ô" in r.tts_text and "2 tệp" in r.tts_text


def test_upload_classifier_fallback_dung_o():
    from app.upload_session.classifier_registry import _CLASSIFIERS

    classifier = _CLASSIFIERS.get(KEY)
    assert classifier is not None and callable(classifier.fallback_to_slot)
    docs = get_procedure(KEY)["requiredDocs"]
    assert classifier.fallback_to_slot(
        "PHIẾU YÊU CẦU XÓA ĐĂNG KÝ BIỆN PHÁP BẢO ĐẢM (Mẫu số 03a)", docs, [], None)[0] == "don"
    assert classifier.fallback_to_slot(
        "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT quyền sở hữu tài sản gắn liền với đất",
        docs, [], None)[0] == "gcn"
    assert classifier.fallback_to_slot(
        "HỢP ĐỒNG THẾ CHẤP quyền sử dụng đất số 22/2026/HĐTC", docs, [], None)[0] == "hop_dong"
    assert classifier.fallback_to_slot(
        "GIẤY GIỚI THIỆU — Ngân hàng TMCP cử ông B đi nộp hồ sơ", docs, [], None)[0] == "khac"

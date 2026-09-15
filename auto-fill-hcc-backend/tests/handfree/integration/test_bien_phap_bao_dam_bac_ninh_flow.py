"""[BN] Đăng ký biện pháp bảo đảm QSDĐ (1.011441) — luồng handfree cổng Liferay Bắc Ninh.

Khác iGate: trang eForm có 2 tab CÙNG TRANG (Nhập đơn đăng ký / Tải thành phần hồ sơ,
không wizard) → samePageAttach: kê khai ưu tiên trước dù attachmentTarget luôn dương,
điền xong bot chạy planner đính kèm NGAY (watcher không bắn lại vì chữ ký trang không
đổi), attach xong chốt tóm tắt kết quả cả hai bước. Tỉnh chọn ở DVCQG CỐ ĐỊNH Bắc Ninh
(agencyProvince), không lấy tỉnh tài khoản."""
from app.channels.handfree.chat import flow, intents
from app.channels.handfree.procedure_registry import (
    get_attach_pipeline,
    get_pipeline,
    get_procedure,
    public_list,
)

KEY = "dang-ky-bien-phap-bao-dam-bac-ninh"


def _conv(**kw):
    base = {
        "_id": "t-bpbd-bn", "state": "greet", "history": [],
        # Tài khoản tỉnh KHÁC để chứng minh agencyProvince thắng tỉnh tài khoản.
        "location": {"province": "Thành phố Hà Nội", "ward": "Phường Ba Đình"},
    }
    base.update(kw)
    return base


def test_registry_entry_same_page_va_pipeline_noi_core():
    proc = get_procedure(KEY)
    assert proc, "thiếu entry handfree"
    assert get_pipeline(KEY) and get_attach_pipeline(KEY), "key phải trùng core registry"
    assert proc["samePageAttach"] is True
    assert proc["agencyProvinceOnly"] and proc["agencySoFirst"]
    assert proc["agencyProvince"] == "Bắc Ninh"
    assert proc["agencyDeptLabel"] == "Văn phòng Đăng ký đất đai Bắc Ninh"
    assert "variants" not in proc and "maePortal" not in proc and "wizard" not in proc
    assert any(p["key"] == KEY for p in public_list())
    keys = [d["key"] for d in proc["requiredDocs"]]
    assert keys == ["don", "hop_dong", "gcn", "cccd", "khac"]
    assert KEY in intents._PROCEDURE_HINTS


async def test_confirm_navigate_va_thoai_doc_tinh_bac_ninh():
    conv = _conv()
    await flow.handle_turn(conv, intents.Intent("action", "pick_procedure", {"key": KEY}))
    r = await flow.handle_turn(conv, intents.Intent("confirm"))
    assert conv["state"] == "guide_login"
    assert r.actions and r.actions[0]["type"] == "navigate"
    # Câu hướng dẫn phải đọc tỉnh CỦA THỦ TỤC (Bắc Ninh), không phải tỉnh tài khoản (Hà Nội).
    assert "Bắc Ninh" in r.display_md and "Hà Nội" not in r.display_md
    assert "Văn phòng Đăng ký đất đai Bắc Ninh" in r.display_md


async def test_select_agency_tinh_co_dinh_bac_ninh_so_mode():
    conv = _conv(state="guide_login", procedure_key=KEY, milestones=[], agency_done=False)
    r = await flow.handle_turn(conv, intents.Intent("event", "page_status", {"agencyBlock": True}))
    action = r.actions[0]
    assert action["type"] == "select_agency"
    assert action["province"] == "Bắc Ninh", "agencyProvince phải thắng tỉnh tài khoản"
    assert action["ward"] == "" and action["soMode"] is True


def test_docs_target_uu_tien_ke_khai_du_attachment_target_duong():
    proc = get_procedure(KEY)
    # Trang BN: formKind bacninh + ô đính kèm CÙNG DOM → vẫn phải vào kê khai trước.
    ctx = {"formKind": "bacninh", "attachmentTarget": True}
    assert flow._resolve_docs_target(proc, ctx) == "declaration"
    # Trang luôn đủ điều kiện đính kèm (engine FE tự mở tab) — không phụ thuộc bảng/stepper.
    conv = {"procedure_key": KEY}
    assert flow._attachment_page_reached(conv, proc, ctx) is True
    assert flow._attachment_page_reached(conv, proc, {"formKind": "bacninh"}) is False


async def test_fill_report_chay_planner_dinh_kem_ngay_khong_cho_chuyen_buoc(monkeypatch):
    from app.channels.handfree.chat import pipeline_runner

    spawned = []

    def fake_spawn(coro):
        spawned.append(coro)
        coro.close()  # không chạy pipeline thật trong test

    monkeypatch.setattr(pipeline_runner, "spawn", fake_spawn)
    conv = _conv(
        state="filling", procedure_key=KEY, docs_target="declaration",
        upload_session_id="HS-BN", auto_attach_after_fill=True,
        pipeline_status="running",
    )
    r = await flow.handle_turn(
        conv, intents.Intent("action", "fill_report", {"filled": 12, "notFound": []}))
    assert conv["state"] == "attaching"
    # samePageAttach: KHÔNG waiting_attachment_page — planner phải được spawn ngay.
    assert conv["pipeline_status"] == "running"
    assert conv["attachment_plan_started"] is True
    assert len(spawned) == 1
    assert "Tải thành phần hồ sơ" in r.display_md
    assert "chuyển sang **Thành phần hồ sơ**" not in r.display_md


async def test_attach_report_tom_tat_ket_qua_hai_buoc():
    conv = _conv(
        state="attaching", procedure_key=KEY, docs_target="attachment",
        upload_session_id="HS-BN", attach_plan=[{"documentName": "Phiếu 01a"}],
        fill_report={"filled": 12, "notFound": [], "errors": []},
    )
    r = await flow.handle_turn(
        conv, intents.Intent("action", "attach_report", {"attached": 4, "errors": []}))
    assert conv["state"] == "done" and conv["attach_done"] is True
    assert "Tóm tắt" in r.display_md
    assert "điền 12 ô" in r.tts_text and "4 tệp" in r.tts_text


def test_upload_classifier_fallback_dung_o():
    from app.upload_session.classifier_registry import _CLASSIFIERS

    classifier = _CLASSIFIERS.get(KEY)
    assert classifier is not None and callable(classifier.fallback_to_slot)
    docs = get_procedure(KEY)["requiredDocs"]
    assert classifier.fallback_to_slot(
        "PHIẾU YÊU CẦU ĐĂNG KÝ BIỆN PHÁP BẢO ĐẢM (Mẫu số 01a)", docs, [], None)[0] == "don"
    assert classifier.fallback_to_slot(
        "HỢP ĐỒNG THẾ CHẤP quyền sử dụng đất số 15/2026/HĐTC", docs, [], None)[0] == "hop_dong"
    assert classifier.fallback_to_slot(
        "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT quyền sở hữu tài sản gắn liền với đất",
        docs, [], None)[0] == "gcn"
    assert classifier.fallback_to_slot(
        "GIẤY GIỚI THIỆU — Ngân hàng TMCP cử ông A đi nộp hồ sơ", docs, [], None)[0] == "khac"

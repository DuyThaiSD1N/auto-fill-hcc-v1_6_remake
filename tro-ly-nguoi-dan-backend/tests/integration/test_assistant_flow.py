"""Máy trạng thái hội thoại toàn trình (docs/03a §3) — test THUẦN, không LLM/Mongo.

Runtime chọn thủ tục + mọi ý định nói/gõ tự do đi qua LLM (intents.resolve). Test flow
KHÔNG gọi mạng: `_turn` dùng bộ GIẢ LẬP tất định (`_fake_intent`) mô phỏng đúng ý mà LLM
sẽ trả cho các câu test → vẫn kiểm được máy trạng thái, offline. Việc validate/định tuyến
của resolve() (chặn key bịa, validate theo state) được test riêng ở test_resolve_llm_*.
"""
import pytest

from app.chat import flow, intents, store
from app.chat.intents import Intent, fold, resolve, resolve_deterministic
from app.chat.intents import _resolve_machine  # noqa: SLF001 — nhánh máy/sđt (tất định)


def _conv():
    c = store.new_conversation(location={"province": "Tỉnh Bắc Ninh", "province_slug": "bacninh", "ward": "Phường Song Liễu"})
    return c


# Bộ giả lập LLM cho test flow: tái hiện ý định mà bộ phân loại LLM trả cho câu test.
# Thủ tục nhận theo cụm dài-trước (nước ngoài / đăng ký lại trước "kết hôn" trơn).
_FAKE_PROC = [
    ("chung thuc ban sao", "chung-thuc-ban-sao"),
    ("ket hon nuoc ngoai", "ket-hon-nuoc-ngoai"), ("nuoc ngoai", "ket-hon-nuoc-ngoai"),
    ("dang ky lai ket hon", "dang-ky-lai-ket-hon"), ("ket hon lai", "dang-ky-lai-ket-hon"),
    ("ket hon", "ket-hon"), ("khai sinh", "khai-sinh-dang-ky"), ("khai tu", "khai-tu"),
    ("trich luc", "trich-luc-ks"), ("tinh trang hon nhan", "xac-nhan-tinh-trang-hon-nhan"),
]
_FAKE_STATE = {
    "guide_login": [("da dang nhap", "event", "sso_success"), ("vao trang ke khai", "event", "sso_success"),
                    ("vao form", "event", "sso_success"), ("dang nhap xong", "event", "sso_success")],
    "consent": [("khong dong y", "action", "consent_decline"), ("tu nhap", "action", "consent_decline"),
                ("dong y", "action", "consent_agree"), ("cho phep", "action", "consent_agree")],
    "qr_waiting": [("khong quet duoc", "action", "reshow_qr"), ("chup xong", "event", "docs_complete"),
                   ("du roi", "event", "docs_complete")],
    "collecting_docs": [("chup lai", "action", "reshow_qr"), ("du roi", "event", "docs_complete"),
                        ("gui di", "event", "docs_complete"), ("dien di", "event", "docs_complete"),
                        ("xu ly", "event", "docs_complete"), ("chup xong", "event", "docs_complete")],
    "reviewing": [("dien lai", "action", "refill"), ("dinh kem", "action", "confirm_review"),
                  ("chuan roi", "action", "confirm_review"), ("ok", "action", "confirm_review")],
    "done": [("nop xong", "event", "submitted")],  # save_profile ẩn khỏi voice (đi cùng option profile)
}
_FAKE_GLOBAL = [("thu tuc khac", "action", "new_procedure"), ("lam cai khac", "action", "new_procedure")]


def _fake_intent(message, state):
    m = _resolve_machine(message)
    if m is not None:
        return m
    f = fold(message)
    is_q = "?" in message or any(w in f for w in ["gi", "bao nhieu", "the nao", "lam sao", "may ngay", "bao lau", "o dau"])
    proc = next((k for kw, k in _FAKE_PROC if kw in f), None)
    if is_q:
        return Intent("ask_question", message, {"procedure_key": proc} if proc else {})
    if proc:
        return Intent("pick_procedure", proc)
    if state == "ask_doc_method":
        for meth, words in (("qr", ["dien thoai", "quet ma", "qr", "chup"]),
                            ("scan", ["scan", "may quet", "tai quay"])):  # profile ẩn khỏi voice/LLM
            if any(w in f for w in words):
                return Intent("pick_doc_method", meth)
    for kw, kind, val in _FAKE_GLOBAL:
        if kw in f:
            return Intent(kind, val)
    import re as _re
    has_neg = bool(_re.search(r"(?:^|\W)chua(?:\W|$)", f))  # "chua" nguyên từ (không dính "chuan")
    if not has_neg:
        for kw, kind, val in _FAKE_STATE.get(state, []):
            if kw in f:
                return Intent(kind, val)
    if state in ("confirm_procedure", "greet"):
        if any(w in f for w in ["dung roi", "dung", "ok", "vang", "da", "dong y", "chuan", "tiep tuc"]):
            return Intent("confirm")
        if any(w in f for w in ["khong", "thoi", "sai roi", "huy", "quay lai"]):
            return Intent("deny")
    return Intent("unknown")


async def _turn(conv, message):
    intent = _fake_intent(message, conv["state"])
    assert intent.kind != "unknown", f"câu '{message}' @ {conv['state']} không phân loại được (test)"
    return await flow.handle_turn(conv, intent)


async def _accept_consent(conv):
    """Qua cổng xin phép xử lý dữ liệu (Luật 91/2025) — như bấm 'Đồng ý và tự động điền' trên card."""
    assert conv["state"] == "consent", f"phải đang ở bước consent, đang là {conv['state']}"
    return await _turn(conv, '__action:consent:{"accepted": true, "checks": [true, true]}')


@pytest.fixture(autouse=True)
def consent_persisted(monkeypatch):
    """Mock ghi nhật ký chấp thuận (Mongo) — trả list để test soi entry đã lưu."""
    logs = []

    async def fake_persist(entry):
        logs.append(entry)

    monkeypatch.setattr(flow.consent_log, "persist", fake_persist)
    yield logs


@pytest.fixture(autouse=True)
def _mock_tracing(monkeypatch):
    """Flow gắn fill/attach_report vào trace (Mongo) — test thuần thì noop."""
    from app.chat import tracing

    async def fake_set_report(*_a, **_k):
        return None

    monkeypatch.setattr(tracing, "set_report", fake_set_report)


@pytest.fixture(autouse=True)
def _mock_upload_service(monkeypatch):
    """Flow test THUẦN — không đụng Mongo: mock nhánh tạo phiên QR (docs/05)."""
    async def fake_create(conv):
        conv["upload_session_id"] = "HS-TEST01"
        return {"type": "show_qr", "session_id": "HS-TEST01",
                "mobile_url": "http://test/m/HS-TEST01", "qr_png_base64": "xxx"}

    async def fake_progress(_sid):
        return {"received": 5, "total": 5, "docs": [], "unknown": 0, "complete": True}

    monkeypatch.setattr(flow.upload_service, "create_for_conversation", fake_create)
    monkeypatch.setattr(flow.upload_service, "progress_of", fake_progress)
    # Không cho spawn pipeline nền trong test (đụng Mongo/OCR thật) — docs/06.
    from app.chat import pipeline_runner
    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: coro.close())

    # Bước 8: mock notify/profiles/store (flow test THUẦN không Mongo) — docs/08.
    async def fake_subscribe(conv, phone):
        from app.notify.service import normalize_phone
        p = normalize_phone(phone)
        if p:
            conv["phone"] = p
        return bool(p)

    async def fake_lookup(phone):
        return {"_id": "0912345678", "files": [{"fid": "f1"}, {"fid": "f2"}]} if "0912345678" in phone else None

    async def fake_apply(conv, profile):
        conv["upload_session_id"] = "HS-PROFILE"
        return True

    async def fake_save(conv, phone):
        conv["profile_id"] = phone
        return True

    async def fake_delete(_phone):
        return None

    async def fake_store_get(_sid):
        return {"files": [1, 2, 3]}

    async def fake_delete_session(_sid):
        return None

    monkeypatch.setattr(flow.notify_service, "subscribe", fake_subscribe)
    monkeypatch.setattr(flow.profile_service, "lookup", fake_lookup)
    monkeypatch.setattr(flow.profile_service, "apply_to_conversation", fake_apply)
    monkeypatch.setattr(flow.profile_service, "save_from_conversation", fake_save)
    monkeypatch.setattr(flow.profile_service, "delete", fake_delete)
    monkeypatch.setattr(flow.up_store, "get", fake_store_get)
    monkeypatch.setattr(flow.up_store, "delete_session", fake_delete_session)


@pytest.mark.asyncio
async def test_happy_path_den_ask_doc_method():
    conv = _conv()
    r = await _turn(conv, "tôi muốn đăng ký khai sinh cho con")
    assert conv["state"] == "confirm_procedure"
    assert conv["procedure_key"] == "khai-sinh-dang-ky"
    assert any(c.get("solid") for c in r.chips)  # chips[0] = hành động tốt nhất

    r = await _turn(conv, "__action:goto_login")
    assert conv["state"] == "guide_login"
    assert r.actions and r.actions[0]["type"] == "navigate"
    assert "lienthong.dichvucong.gov.vn" in r.actions[0]["url"]
    assert r.awaiting_events == ["sso_success"]

    r = await _turn(conv, "__event:sso_success")
    assert conv["state"] == "consent"  # cổng PDPL: xin phép TRƯỚC khi nhận/đọc giấy tờ
    assert any(c["kind"] == "consent_form" for c in r.cards)

    r = await _accept_consent(conv)
    assert conv["state"] == "ask_doc_method"
    assert "Đã ghi nhận sự đồng ý" in r.display_md and "TLND-" in r.display_md
    assert any(c["kind"] == "doc_options" for c in r.cards)
    assert "CCCD" in r.display_md  # danh sách giấy tờ sinh từ uploadHint registry

    r = await _turn(conv, "chụp bằng điện thoại")
    assert conv["state"] == "qr_waiting"
    assert r.actions and r.actions[0]["type"] == "show_qr"       # QR sinh từ BE (docs/05)
    assert conv["upload_session_id"] == "HS-TEST01"

    r = await _turn(conv, "__event:mobile_connected")
    assert conv["state"] == "collecting_docs"

    r = await _turn(conv, "__event:docs_complete")
    assert conv["state"] == "filling"
    assert "5 tệp" in r.display_md and "5/5" not in r.display_md  # tổng tệp đã nhận, không "/tổng"


@pytest.mark.asyncio
async def test_doi_cach_gui_giay_to_giu_phien():
    """Đổi qua lại QR ↔ Scan sau khi đã chọn (bug: chọn scan rồi bấm QR vẫn ra scan). GIỮ nguyên
    phiên upload (đổi cách không tạo phiên mới → file đã tải không mất)."""
    conv = _conv()
    await _turn(conv, "đăng ký khai sinh")
    await _turn(conv, "__action:goto_login")
    await _turn(conv, "__event:sso_success")
    await _accept_consent(conv)
    assert conv["state"] == "ask_doc_method"

    # Chọn QR → qr_waiting, phiên HS-TEST01.
    r = await _turn(conv, "chụp bằng điện thoại")
    assert conv["state"] == "qr_waiting" and conv["doc_method"] == "qr"
    sid = conv["upload_session_id"]
    assert sid == "HS-TEST01"
    assert any(c["send"] == '__action:doc_method:{"value":"scan"}' for c in r.chips)  # chip đổi sang scan

    # Đang QR, bấm "Scan tại quầy" (card cũ) → ĐỔI sang scan, GIỮ phiên.
    r = await _turn(conv, '__action:doc_method:{"value":"scan"}')
    assert conv["state"] == "collecting_docs" and conv["doc_method"] == "scan"
    assert conv["upload_session_id"] == sid                       # KHÔNG tạo phiên mới
    assert r.actions and r.actions[0]["type"] == "pick_files"
    assert any(c["send"] == '__action:doc_method:{"value":"qr"}' for c in r.chips)  # chip đổi ngược

    # Đang scan, bấm "Chụp bằng điện thoại" → ĐỔI về QR, vẫn GIỮ phiên.
    r = await _turn(conv, '__action:doc_method:{"value":"qr"}')
    assert conv["state"] == "qr_waiting" and conv["doc_method"] == "qr"
    assert conv["upload_session_id"] == sid
    assert r.actions and r.actions[0]["type"] == "show_qr"

    # Bấm lại đúng cách đang dùng (qr) → KHÔNG coi là đổi, vẫn ở qr_waiting.
    r = await _turn(conv, '__action:doc_method:{"value":"qr"}')
    assert conv["state"] == "qr_waiting" and conv["doc_method"] == "qr"


@pytest.mark.asyncio
async def test_cau_hoi_khong_reset_flow():
    """Câu HỎI giữa chừng ('làm khai sinh cần giấy tờ gì') KHÔNG được reset state."""
    conv = _conv()
    await _turn(conv, "khai sinh")
    await _turn(conv, "__action:goto_login")
    await _turn(conv, "__event:sso_success")
    await _accept_consent(conv)
    assert conv["state"] == "ask_doc_method"

    r = await _turn(conv, "làm khai sinh cần chuẩn bị giấy tờ gì")
    assert conv["state"] == "ask_doc_method"  # giữ nguyên state
    assert "CCCD" in r.display_md              # trả lời từ uploadHint


@pytest.mark.asyncio
async def test_nhac_lai_thu_tuc_dang_lam_khong_reset():
    conv = _conv()
    await _turn(conv, "khai sinh")
    await _turn(conv, "__action:goto_login")
    r = await _turn(conv, "đăng ký khai sinh")   # nhắc lại đúng thủ tục giữa chừng
    assert conv["state"] == "guide_login"          # không reset
    assert "đang làm" in r.display_md


@pytest.mark.asyncio
async def test_doi_thu_tuc_giua_chung_ve_confirm():
    conv = _conv()
    await _turn(conv, "khai sinh")
    await _turn(conv, "__action:goto_login")
    await _turn(conv, "__event:sso_success")
    r = await _turn(conv, "thôi làm đăng ký kết hôn")
    assert conv["state"] == "confirm_procedure"
    assert conv["procedure_key"] == "ket-hon"
    assert "Kết hôn" in r.display_md


@pytest.mark.asyncio
async def test_hoi_truoc_khi_chon_thu_tuc():
    """Hỏi 'làm kết hôn cần gì' ngay màn chào → trả lời theo thủ tục ĐƯỢC NHẮC, không đổi state."""
    conv = _conv()
    r = await _turn(conv, "làm đăng ký kết hôn cần giấy tờ gì")
    assert conv["state"] == "greet"
    assert "Kết hôn" in r.display_md and "CCCD" in r.display_md


@pytest.mark.asyncio
async def test_doi_noi_lam_thu_tuc():
    """Màn chào: card đã hiển thị lựa chọn → IM LẶNG. Giữa chừng: báo đổi nơi rõ ràng."""
    conv = _conv()
    r = await flow.handle_turn(conv, Intent("action", "set_location",
                                            {"province_slug": "danang", "ward": "Phường Hải Châu"}))
    assert conv["location"]["province"] == "Thành phố Đà Nẵng"
    assert conv["location"]["ward"] == "Phường Hải Châu"
    assert r.display_md == ""  # greet → không đẻ bubble "đã cập nhật"

    conv["state"] = "ask_doc_method"
    r = await flow.handle_turn(conv, Intent("action", "set_location",
                                            {"province_slug": "bacninh", "ward": "Phường Võ Cường"}))
    assert "Võ Cường" in r.display_md

    # Đang xác nhận thủ tục → hỏi lại câu xác nhận với nơi MỚI.
    conv2 = _conv()
    await _turn(conv2, "kết hôn")
    r = await flow.handle_turn(conv2, Intent("action", "set_location",
                                             {"province_slug": "danang", "ward": "Phường Hải Châu"}))
    assert conv2["state"] == "confirm_procedure"
    assert "Hải Châu" in r.display_md and "Kết hôn" in r.display_md


@pytest.mark.asyncio
async def test_guide_login_hai_nhanh_theo_trang():
    """Chặng mở trang/đăng nhập nói theo cái THẤY: 2 nhánh loggedIn, không lặp câu."""
    # Nhánh CHƯA đăng nhập: chọn cơ quan xong → dặn QR; sang trang SSO không nhắc lại.
    conv = _conv()
    await _turn(conv, "kết hôn")
    await _turn(conv, "__action:goto_login")
    # formKind "standard" trên trang chi tiết là dương tính giả (ô tìm kiếm) — còn khối
    # cơ quan chưa chọn thì phải chọn cơ quan, KHÔNG được coi là đã vào form kê khai.
    r = await _turn(conv, '__event:page_status:{"agencyBlock": true, "formKind": "standard", "loggedIn": false}')
    assert conv["state"] == "guide_login"
    assert r.display_md == "" and r.actions[0]["type"] == "select_agency"

    r = await _turn(conv, '__event:agency_selected:{"loggedIn": false}')
    # Hướng A + gộp 1 câu: KHÔNG hiện câu riêng ở đây — dồn hết vào 1 câu đọc TRÊN trang login.
    assert r.display_md == ""

    r = await _turn(conv, '__event:page_status:{"loginPage": true, "loggedIn": false}')
    # 1 CÂU duy nhất: xác nhận cơ quan + kịch bản VNeID/QR; đọc xong FE thu gọn (collapse_after_tts).
    assert "đã chọn cơ quan" in r.display_md and "VNeID" in r.display_md and "Quét QR" in r.display_md
    assert any(a["type"] == "collapse_after_tts" for a in r.actions)

    r = await _turn(conv, '__event:page_status:{"formKind": "angular", "loggedIn": true}')
    assert conv["state"] == "consent"  # vào form → xin phép xử lý dữ liệu trước
    assert "Đăng nhập thành công" in r.display_md

    # Nhánh ĐÃ đăng nhập sẵn: không nói chữ nào về QR/đăng nhập.
    conv2 = _conv()
    await _turn(conv2, "kết hôn")
    await _turn(conv2, "__action:goto_login")
    r = await _turn(conv2, '__event:agency_selected:{"loggedIn": true}')
    assert "đã đăng nhập sẵn" in r.display_md and "QR" not in r.display_md
    r = await _turn(conv2, '__event:page_status:{"formKind": "angular", "loggedIn": true}')
    assert conv2["state"] == "consent"
    assert "Đã vào trang kê khai" in r.display_md
    assert "Đăng nhập thành công" not in r.display_md


@pytest.mark.asyncio
async def test_lienthong_khai_sinh_chon_co_quan_roi_ke_khai():
    """Liên thông (Angular, KHÔNG needsAgencySelect): trang CHỌN CƠ QUAN (agencyBlock, chưa có
    form kê khai) → trợ lý ĐIỀN HỘ (action fill_agency_plan, plan thay tỉnh/xã theo phiên), nói
    1 lần; trang KÊ KHAI (formKind angular) → sang bước xin phép."""
    conv = _conv()
    await _turn(conv, "khai sinh")
    await _turn(conv, "__action:goto_login")
    assert conv["state"] == "guide_login" and conv["procedure_key"] == "khai-sinh-dang-ky"

    # Trang chọn cơ quan: agencyBlock nhưng formKind rỗng (content.js chưa thấy "kê khai thông tin").
    r = await _turn(conv, '__event:page_status:{"agencyBlock": true, "formKind": "", "loggedIn": true}')
    assert conv["state"] == "guide_login" and "cơ quan thực hiện" in r.display_md
    assert r.actions and r.actions[0]["type"] == "fill_agency_plan"
    plan = {s["name"]: s for s in r.actions[0]["plan"]}
    assert plan["IsNuocNgoai"]["value"] == "Không có yếu tố nước ngoài"
    # {province}/{ward} đã thay bằng nơi ở của phiên (Bắc Ninh / Song Liễu).
    assert plan["CqdkksDiaChi"]["value"] == {"tinh": "Tỉnh Bắc Ninh", "xa": "Phường Song Liễu"}
    assert plan["CqdkttIsDkks"]["value"] is True
    # Nói lại → im lặng (điền 1 lần, không bắn lại action).
    r = await _turn(conv, '__event:page_status:{"agencyBlock": true, "formKind": "", "loggedIn": true}')
    assert r.display_md == "" and not r.actions

    # Trang kê khai: formKind angular (dù trang vẫn có text "cơ quan thực hiện") → xin phép xử lý dữ liệu.
    r = await _turn(conv, '__event:page_status:{"agencyBlock": true, "formKind": "angular", "loggedIn": true}')
    assert conv["state"] == "consent"
    assert any(c["kind"] == "consent_form" for c in r.cards)


def test_resolve_agency_plan_thay_tinh_xa():
    """_resolve_agency_plan thay {province}/{ward} (kể cả trong value dict diachi); không plan → []."""
    plan = [
        {"name": "IsNuocNgoai", "comp": "select", "value": "Không có yếu tố nước ngoài"},
        {"name": "CqdkksDiaChi", "comp": "diachi", "value": {"tinh": "{province}", "xa": "{ward}"}},
        {"name": "CqdkttIsDkks", "comp": "checkbox", "value": True},
    ]
    out = flow._resolve_agency_plan(plan, {"province": "Tỉnh Lâm Đồng", "ward": "Phường Lâm Viên - Đà Lạt"})
    assert out[1]["value"] == {"tinh": "Tỉnh Lâm Đồng", "xa": "Phường Lâm Viên - Đà Lạt"}
    assert out[0]["value"] == "Không có yếu tố nước ngoài" and out[2]["value"] is True
    # Thiếu ward → thay bằng rỗng (không vỡ), value cố định giữ nguyên.
    out2 = flow._resolve_agency_plan(plan, {"province": "Tỉnh Lâm Đồng"})
    assert out2[1]["value"] == {"tinh": "Tỉnh Lâm Đồng", "xa": ""}
    assert flow._resolve_agency_plan(None, {}) == [] and flow._resolve_agency_plan([], {}) == []


@pytest.mark.asyncio
async def test_lienthong_khai_sinh_vao_thang_ke_khai():
    """Có khi liên thông vào THẲNG kê khai (bỏ qua trang chọn cơ quan): formKind angular ngay lượt đầu."""
    conv = _conv()
    await _turn(conv, "khai sinh")
    await _turn(conv, "__action:goto_login")
    r = await _turn(conv, '__event:page_status:{"agencyBlock": true, "formKind": "angular", "loggedIn": true}')
    assert conv["state"] == "consent"
    assert any(c["kind"] == "consent_form" for c in r.cards)


def test_resolve_may_va_sdt_tat_dinh():
    """Lệnh máy (chip/watcher) + số điện thoại KHÔNG đụng LLM — resolve_deterministic xử trọn."""
    i = resolve_deterministic("__action:goto_login", "confirm_procedure")
    assert (i.kind, i.value) == ("action", "goto_login")
    i = resolve_deterministic('__event:page_status:{"loggedIn": true}', "guide_login")
    assert i.kind == "event" and i.value == "page_status" and i.payload["loggedIn"] is True
    i = resolve_deterministic("số của tôi là 0912 345 678", "done")
    assert (i.kind, i.value) == ("provide_phone", "0912345678")
    # Câu tự do → None (dành cho LLM).
    assert resolve_deterministic("kết hôn có yếu tố nước ngoài", "greet") is None


def _stub_llm(monkeypatch, response):
    async def fake(messages, **_kw):
        return response
    monkeypatch.setattr(intents, "llm_chat", fake)


@pytest.mark.asyncio
async def test_resolve_llm_pick_procedure_validate(monkeypatch):
    """resolve() nhận key thủ tục hợp lệ từ LLM; key bịa → unknown (flow sẽ hiện lại card)."""
    _stub_llm(monkeypatch, '{"kind":"pick_procedure","value":"ket-hon-nuoc-ngoai"}')
    i = await resolve("chồng tôi là người nước ngoài", "greet")
    assert (i.kind, i.value) == ("pick_procedure", "ket-hon-nuoc-ngoai")

    _stub_llm(monkeypatch, '{"kind":"pick_procedure","value":"ket-hon"}')
    assert (await resolve("đăng ký kết hôn", "greet")).value == "ket-hon"

    _stub_llm(monkeypatch, '{"kind":"pick_procedure","value":"thu-tuc-ma-quy"}')  # key bịa
    assert (await resolve("làm cái gì đó", "greet")).kind == "unknown"


@pytest.mark.asyncio
async def test_resolve_llm_state_action_validate(monkeypatch):
    """state_action chỉ chấp nhận value có trong bảng của ĐÚNG state; lệch state → unknown."""
    _stub_llm(monkeypatch, '{"kind":"state_action","value":"consent_agree"}')
    i = await resolve("đồng ý cho đọc", "consent")
    assert (i.kind, i.value) == ("action", "consent_agree")

    # "submitted" không thuộc bảng state "consent" → không cho bịa lệnh.
    _stub_llm(monkeypatch, '{"kind":"state_action","value":"submitted"}')
    assert (await resolve("gì đó", "consent")).kind == "unknown"

    # doc method chỉ nhận qr|scan|profile.
    _stub_llm(monkeypatch, '{"kind":"pick_doc_method","value":"qr"}')
    assert (await resolve("chụp điện thoại", "ask_doc_method")).value == "qr"
    _stub_llm(monkeypatch, '{"kind":"pick_doc_method","value":"xyz"}')
    assert (await resolve("kiểu khác", "ask_doc_method")).kind == "unknown"


def test_prompt_doc_method_co_mo_ta_va_chong_chup_scan():
    """Prompt phải mô tả rõ 3 cách + chốt "chụp"→qr; thiếu là LLM lại nhầm chụp≈scan."""
    s = intents._LLM_SYSTEM.format(
        state="ask_doc_method",
        state_actions=intents._state_action_block("ask_doc_method"),
        doc_methods=intents._doc_method_block(),
        procedures="  + \"x\" = X",
    )
    for meth in ("qr", "scan"):
        assert f'"{meth}" =' in s, f"prompt thiếu mô tả doc method {meth}"
    assert "ĐIỆN THOẠI" in s and 'LUÔN là "qr"' in s  # chống nhầm chụp→scan
    # "profile" (Lấy dữ liệu đã lưu) đang ẨN → LLM không được gợi ý cách này nữa.
    assert '"profile"' not in s and "dữ liệu đã lưu" not in s.lower()


@pytest.mark.asyncio
async def test_resolve_llm_question_va_loi(monkeypatch):
    """ask_question gắn đúng procedure_key; LLM lỗi/không parse → unknown (an toàn → card)."""
    _stub_llm(monkeypatch, '{"kind":"ask_question","value":"lệ phí bao nhiêu","procedure":"ket-hon"}')
    i = await resolve("làm kết hôn hết bao nhiêu tiền", "greet")
    assert i.kind == "ask_question" and i.payload.get("procedure_key") == "ket-hon"

    async def boom(*_a, **_k):
        raise RuntimeError("LLM sập")
    monkeypatch.setattr(intents, "llm_chat", boom)
    assert (await resolve("câu mơ hồ", "greet")).kind == "unknown"


def test_procedure_catalog_phan_biet_ket_hon():
    """Prompt LLM phải chứa cả 2 thủ tục kết hôn kèm mô tả để phân biệt trong nước / nước ngoài."""
    cat = intents._procedure_catalog()  # noqa: SLF001
    assert '"ket-hon"' in cat and '"ket-hon-nuoc-ngoai"' in cat
    assert "nước ngoài" in cat  # mô tả phân biệt có mặt trong danh mục gửi LLM


@pytest.mark.asyncio
async def test_noi_tu_nhien_chay_het_flow():
    """Đi hết flow bằng LỜI NÓI, không bấm chip nào (trừ lệnh máy của trang)."""
    conv = _conv()
    await _turn(conv, "kết hôn")
    await _turn(conv, "đúng rồi")                       # confirm → guide_login
    assert conv["state"] == "guide_login"
    await _turn(conv, "tôi vào trang kê khai rồi")       # sso_success bằng lời
    assert conv["state"] == "consent"
    await _turn(conv, "đồng ý")                          # chấp thuận BẰNG LỜI — vẫn hợp lệ
    assert conv["state"] == "ask_doc_method"
    await _turn(conv, "chụp bằng điện thoại")
    assert conv["state"] == "qr_waiting"
    await _turn(conv, "__event:mobile_connected")
    await _turn(conv, "chụp xong hết rồi")               # docs_complete bằng lời
    assert conv["state"] == "filling"
    await _turn(conv, "__action:fill_report:{\"filled\": 20}")
    assert conv["state"] == "reviewing"
    await _turn(conv, "chuẩn rồi, đính kèm đi")          # confirm_review bằng lời
    assert conv["state"] == "attaching"


@pytest.mark.asyncio
async def test_wizard_ket_hon_modal_chu_ho_so_ke_khai():
    """Wizard cổng React: modal Thông tin chung (bot tự Xác nhận) → bước chủ hồ sơ (dặn
    người dân tự điền) → bước kê khai (mới hiện danh sách giấy tờ). Mỗi câu nói 1 lần."""
    conv = _conv()
    await _turn(conv, "kết hôn")
    await _turn(conv, "__action:goto_login")
    await _turn(conv, '__event:agency_selected:{"loggedIn": false}')

    r = await _turn(conv, '__event:page_status:{"infoModal": true, "loggedIn": true}')
    # Đã bỏ câu "Em xác nhận Thông tin chung…" khỏi luồng — chỉ còn "Đăng nhập thành công ✓" + action.
    assert "Đăng nhập thành công" in r.display_md and "Thông tin chung" not in r.display_md
    assert r.actions[0]["type"] == "confirm_info_modal"
    # Modal chưa đóng kịp, FE báo lại → bấm lại nhưng im lặng.
    r = await _turn(conv, '__event:page_status:{"infoModal": true, "loggedIn": true}')
    assert r.display_md == "" and r.actions[0]["type"] == "confirm_info_modal"

    r = await _turn(conv, '__event:page_status:{"wizardStep": 1, "loggedIn": true}')
    assert "chủ hồ sơ" in r.display_md and "Đăng nhập thành công" not in r.display_md
    r = await _turn(conv, '__event:page_status:{"wizardStep": 1, "loggedIn": true}')
    assert r.display_md == ""

    r = await _turn(conv, '__event:page_status:{"wizardStep": 2, "loggedIn": true}')
    assert conv["state"] == "consent"
    assert "Đã vào trang kê khai" in r.display_md and "Đăng nhập thành công" not in r.display_md
    assert any(c["kind"] == "consent_form" for c in r.cards)


@pytest.mark.asyncio
async def test_chung_thuc_ban_sao_chu_ho_so_vao_thang_dinh_kem(monkeypatch, consent_persisted):
    """Attach-only: chủ hồ sơ → Thành phần hồ sơ → nhận tệp, không consent/process."""
    conv = _conv()
    await _turn(conv, "chứng thực bản sao")
    await _turn(conv, "__action:goto_login")

    r = await _turn(conv, '__event:page_status:{"wizardStep": 1, "loggedIn": true}')
    assert "Thông tin chủ hồ sơ" in r.display_md

    r = await _turn(
        conv,
        '__event:page_status:{"wizardStep": 3, "attachmentTarget": true, "loggedIn": true}',
    )
    assert conv["state"] == "ask_doc_method"
    assert any(c["kind"] == "doc_options" for c in r.cards)
    assert not any(c["kind"] == "consent_form" for c in r.cards)
    assert "Thành phần hồ sơ" in r.display_md
    assert consent_persisted == []

    await _turn(conv, "scan tại quầy")
    assert conv["state"] == "collecting_docs"

    from app.chat import pipeline_runner

    spawned = []
    monkeypatch.setattr(pipeline_runner, "run_attach", lambda *_args: "attach-job")
    monkeypatch.setattr(
        pipeline_runner,
        "run_process",
        lambda *_args: pytest.fail("attach-only không được gọi process pipeline"),
    )
    monkeypatch.setattr(pipeline_runner, "spawn", spawned.append)

    r = await _turn(conv, "__event:docs_complete")
    assert conv["state"] == "attaching"
    assert spawned == ["attach-job"]
    assert "cùng một hồ sơ" in r.display_md


@pytest.mark.asyncio
async def test_attach_dung_trang_moi_dinh():
    """Đòi đính kèm khi trang còn ở bước kê khai → dặn chuyển bước, KHÔNG chạy engine;
    sang bước Thành phần hồ sơ tự đính lại; đính được 0 tệp thì không chốt xong."""
    conv = _conv()
    await _turn(conv, "kết hôn")
    await _turn(conv, "__action:goto_login")
    await _turn(conv, "__event:sso_success")
    await _accept_consent(conv)
    await _turn(conv, "chụp bằng điện thoại")
    await _turn(conv, "__event:mobile_connected")
    await _turn(conv, "__event:docs_complete")
    await _turn(conv, '__action:fill_report:{"filled": 20}')
    await _turn(conv, "__action:confirm_review")
    assert conv["state"] == "attaching"
    conv["attach_plan"] = [{"fileIndex": 0, "documentName": "CCCD", "componentName": "CCCD"}]

    r = await _turn(conv, '__event:attach_blocked:{"wizardStep": 2}')
    assert "Kê khai thông tin" in r.display_md and conv["state"] == "attaching"

    r = await _turn(conv, '__event:page_status:{"wizardStep": 2}')
    assert r.display_md == "" and not r.actions  # chưa tới bước đính → im lặng chờ

    r = await _turn(conv, '__event:page_status:{"wizardStep": 3}')
    assert r.actions and r.actions[0]["type"] == "attach_plan"
    assert "Thành phần hồ sơ" in r.display_md

    r = await _turn(conv, '__action:attach_report:{"attached": 0, "errors": []}')
    assert conv["state"] == "attaching"  # 0 tệp → giữ bước, cho thử lại
    assert any(c["send"] == "__event:attach_ready" for c in r.chips)

    r = await _turn(conv, '__action:attach_report:{"attached": 3, "errors": []}')
    assert conv["state"] == "done"


@pytest.mark.asyncio
async def test_page_status_lac_ngoai_guide_login_im_lang():
    conv = _conv()
    await _turn(conv, "khai sinh")
    await _turn(conv, "__action:goto_login")
    await _turn(conv, "__event:sso_success")
    # page_status lạc vào bước consent cũng phải im lặng (không đẻ bubble giữa lúc xin phép).
    r = await _turn(conv, '__event:page_status:{"formKind": "legacy", "loggedIn": true}')
    assert r.display_md == "" and not r.cards
    await _accept_consent(conv)
    assert conv["state"] == "ask_doc_method"
    r = await _turn(conv, '__event:page_status:{"formKind": "legacy", "loggedIn": true}')
    assert r.display_md == "" and not r.cards  # bắn trùng sau khi chuyển bước → im lặng


@pytest.mark.asyncio
async def test_done_flow_phone_profile_delete():
    """Bước 8: nộp xong → SĐT nhận thông báo → lưu profile → xoá dữ liệu (docs/08)."""
    conv = _conv()
    conv["state"] = "done"

    r = await _turn(conv, "__event:submitted")
    assert any(c["kind"] == "phone_form" for c in r.cards)

    r = await _turn(conv, "số của tôi là 0912 345 678")   # provide_phone tất định
    assert conv["phone"] == "0912345678"
    assert "ghi nhận số" in r.display_md

    r = await _turn(conv, "__action:save_profile")         # đã có phone → lưu luôn
    assert conv["profile_id"] == "0912345678"
    assert "lưu hồ sơ" in r.display_md.lower()

    r = await _turn(conv, "__action:delete_data")
    assert conv["upload_session_id"] is None
    assert "xoá toàn bộ" in r.display_md


@pytest.mark.asyncio
async def test_lay_du_lieu_da_luu():
    """Nhánh 'Lấy dữ liệu đã lưu': hỏi SĐT → áp profile → chạy thẳng pipeline (docs/08 §1.2)."""
    conv = _conv()
    await _turn(conv, "khai sinh")
    await _turn(conv, "__action:goto_login")
    await _turn(conv, "__event:sso_success")
    await _accept_consent(conv)

    r = await _turn(conv, "__action:doc_method:{\"value\":\"profile\"}")
    assert conv["awaiting"] == "profile_phone"
    assert "số điện thoại" in r.display_md

    r = await _turn(conv, "0912345678")
    assert conv["state"] == "filling"                       # profile áp xong → pipeline chạy
    assert conv["upload_session_id"] == "HS-PROFILE"
    assert "không phải chụp lại" in r.display_md

    # SĐT không có profile → báo + đưa lại lựa chọn
    conv2 = _conv()
    await _turn(conv2, "khai sinh")
    await _turn(conv2, "__action:goto_login")
    await _turn(conv2, "__event:sso_success")
    await _accept_consent(conv2)
    await _turn(conv2, "__action:doc_method:{\"value\":\"profile\"}")
    r = await _turn(conv2, "0999999999")
    assert conv2["state"] == "ask_doc_method"
    assert "chưa tìm thấy" in r.display_md


@pytest.mark.asyncio
async def test_moi_reply_deu_co_tts():
    conv = _conv()
    for msg in ["khai sinh", "__action:goto_login", "__event:sso_success", "đồng ý",
                "chụp bằng điện thoại"]:
        r = await _turn(conv, msg)
        assert r.tts_text.strip(), f"thiếu tts_text ở lượt '{msg}'"
        assert "**" not in r.tts_text, "tts_text không được chứa markdown"


@pytest.mark.asyncio
async def test_consent_dong_y_ghi_nhat_ky(consent_persisted):
    """Đồng ý qua card → log lưu đủ trường pháp lý + conv mở cổng sang ask_doc_method."""
    conv = _conv()
    await _turn(conv, "kết hôn")
    await _turn(conv, "__action:goto_login")
    r = await _turn(conv, "__event:sso_success")
    card = next(c for c in r.cards if c["kind"] == "consent_form")
    # Card server-driven: đủ danh sách giấy tờ (từ registry) + 2 câu xác nhận + luật.
    assert len(card["documents"]) >= 2 and len(card["checks"]) == 2
    assert "91/2025" in card["legal_md"]

    await _accept_consent(conv)
    assert conv["consent"]["accepted"] is True
    assert len(consent_persisted) == 1
    entry = consent_persisted[0]
    assert entry["_id"].startswith("TLND-") and entry["accepted"] is True
    assert entry["procedure_key"] == "ket-hon" and entry["method"] == "chip"
    assert entry["version"] and entry["scope"] and entry["documents"]

    # Bắt đầu THỦ TỤC KHÁC → chấp thuận cũ không mang theo (phạm vi giấy tờ khác).
    await _turn(conv, "thôi làm khai sinh")
    await _turn(conv, "__action:goto_login")
    assert conv["consent"] is None
    r = await _turn(conv, "__event:sso_success")
    assert conv["state"] == "consent"
    assert any(c["kind"] == "consent_form" for c in r.cards)


@pytest.mark.asyncio
async def test_consent_tu_choi_va_doi_y(consent_persisted):
    """Từ chối → bot KHÔNG xử lý giấy tờ, có lối đổi ý; đồng ý lại bằng LỜI cũng hợp lệ."""
    conv = _conv()
    await _turn(conv, "kết hôn")
    await _turn(conv, "__action:goto_login")
    await _turn(conv, "__event:sso_success")

    r = await _turn(conv, '__action:consent:{"accepted": false, "checks": [false, false]}')
    assert conv["state"] == "consent" and conv["consent"]["accepted"] is False
    assert "không đọc" in r.display_md
    assert any(c["send"] == "__action:show_consent" for c in r.chips)
    assert consent_persisted and consent_persisted[-1]["accepted"] is False  # từ chối cũng ghi log

    r = await _turn(conv, "__action:show_consent")
    assert any(c["kind"] == "consent_form" for c in r.cards)

    r = await _turn(conv, "đồng ý")  # đổi ý bằng lời — method=verbal
    assert conv["state"] == "ask_doc_method"
    assert consent_persisted[-1]["accepted"] is True and consent_persisted[-1]["method"] == "verbal"

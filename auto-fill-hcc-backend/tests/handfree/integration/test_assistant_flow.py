"""Máy trạng thái hội thoại toàn trình (docs/03a §3) — test THUẦN, không LLM/Mongo.

Runtime chọn thủ tục + mọi ý định nói/gõ tự do đi qua LLM (intents.resolve). Test flow
KHÔNG gọi mạng: `_turn` dùng bộ GIẢ LẬP tất định (`_fake_intent`) mô phỏng đúng ý mà LLM
sẽ trả cho các câu test → vẫn kiểm được máy trạng thái, offline. Việc validate/định tuyến
của resolve() (chặn key bịa, validate theo state) được test riêng ở test_resolve_llm_*.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.channels.handfree.chat import flow, intents, store
from app.channels.handfree.chat.intents import Intent, fold, resolve, resolve_deterministic
from app.channels.handfree.chat.intents import _resolve_machine  # noqa: SLF001 — nhánh máy/sđt (tất định)


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
    "qr_waiting": [("dinh kem lai luon", "action", "docs_done"),
                   ("dien lai luon", "action", "docs_done"),
                   ("khong quet duoc", "action", "reshow_qr"), ("chup xong", "event", "docs_complete"),
                   ("du roi", "event", "docs_complete")],
    "collecting_docs": [("dinh kem lai luon", "action", "docs_done"),
                        ("dien lai luon", "action", "docs_done"),
                        ("chup lai", "action", "reshow_qr"), ("du roi", "event", "docs_complete"),
                        ("gui di", "event", "docs_complete"), ("dien di", "event", "docs_complete"),
                        ("xu ly", "event", "docs_complete"), ("chup xong", "event", "docs_complete"),
                        ("dinh kem", "action", "request_attach")],
    "owner_waiting_next": [("dien lai", "action", "retry_owner_fill"),
                           ("dien di", "action", "retry_owner_fill"),
                           ("thu lai", "action", "retry_owner_fill")],
    "filling": [("dinh kem", "action", "request_attach")],
    "reviewing": [("dien lai", "action", "refill"),
                  ("dieu chinh giay to", "action", "add_documents"),
                  ("chuan roi", "action", "confirm_review"), ("ok", "action", "confirm_review"),
                  ("dinh kem", "action", "request_attach")],
    "attaching": [("dien lai", "action", "refill"),
                  ("dieu chinh giay to", "action", "add_documents"),
                  ("dinh kem", "action", "request_attach")],
    "done": [("nop xong", "event", "submitted"),
             ("bo sung giay to", "action", "add_documents"),
             ("them giay to", "action", "add_documents")],
    # save_profile ẩn khỏi voice (đi cùng option profile)
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


async def _verify_portal_ready(conv):
    """Mô phỏng action verify_portal_state của extension sau khi đọc DOM trang kê khai."""
    return await _turn(
        conv,
        '__event:page_status:{"formKind":"angular","loggedIn":true,"manualCheck":true}',
    )


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
    from app.channels.handfree.chat import tracing

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
    from app.channels.handfree.chat import pipeline_runner
    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: coro.close())

    # Bước 8: mock notify/profiles/store (flow test THUẦN không Mongo) — docs/08.
    async def fake_subscribe(conv, phone):
        from app.channels.handfree.notify.service import normalize_phone
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

    check = await _turn(conv, "__event:sso_success")
    assert conv["state"] == "guide_login"
    assert check.actions == [{"type": "verify_portal_state"}]

    r = await _verify_portal_ready(conv)
    assert conv["state"] == "consent"  # cổng PDPL: xin phép TRƯỚC khi nhận/đọc giấy tờ
    assert any(c["kind"] == "consent_form" for c in r.cards)

    r = await _accept_consent(conv)
    assert conv["state"] == "ask_doc_method"
    assert "Đã ghi nhận sự đồng ý" in r.display_md and "TLND-" in r.display_md
    assert any(c["kind"] == "doc_options" for c in r.cards)
    assert "Căn cước công dân" in r.display_md  # danh sách giấy tờ sinh từ registry

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
    await _verify_portal_ready(conv)
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
    await _verify_portal_ready(conv)
    await _accept_consent(conv)
    assert conv["state"] == "ask_doc_method"

    r = await _turn(conv, "làm khai sinh cần chuẩn bị giấy tờ gì")
    assert conv["state"] == "ask_doc_method"  # giữ nguyên state
    assert "Căn cước công dân" in r.display_md  # trả lời từ registry


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
    await _verify_portal_ready(conv)
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
    assert "Kết hôn" in r.display_md and "Căn cước công dân" in r.display_md


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
async def test_doi_tuong_thuc_hien_tu_phap_truyen_tu_card_den_modal():
    """Sidebar chọn key nghiệp vụ; backend ánh xạ sang đúng label/value của cổng."""
    conv = _conv()
    card = flow._location_card(conv)  # noqa: SLF001 — kiểm contract card frontend
    subject = card["executionSubject"]
    assert subject["current"] == "self"
    assert [option["label"] for option in subject["options"]] == [
        "Làm thủ tục cho bản thân",
        "Người khác ủy quyền",
        "Doanh nghiệp ủy quyền",
        "Làm thủ tục cho người khác",
        "Đại diện cơ quan, tổ chức",
    ]

    r = await flow.handle_turn(
        conv,
        Intent("action", "set_execution_subject", {"key": "authorized_person"}),
    )
    assert r.display_md == ""
    assert conv["execution_subject"] == "authorized_person"

    await _turn(conv, "kết hôn")
    await _turn(conv, "__action:goto_login")
    r = await _turn(conv, '__event:page_status:{"infoModal": true, "loggedIn": true}')
    assert r.actions[0] == {
        "type": "confirm_info_modal",
        "executionSubject": {
            "key": "authorized_person",
            "label": "Người khác ủy quyền",
            "portalValue": "canhan",
        },
    }


@pytest.mark.asyncio
async def test_doi_tuong_thuc_hien_khong_hop_le_khong_ghi_de_mac_dinh():
    conv = _conv()
    await flow.handle_turn(
        conv,
        Intent("action", "set_execution_subject", {"key": "khong-ton-tai"}),
    )
    assert conv["execution_subject"] == "self"


@pytest.mark.asyncio
@pytest.mark.parametrize("subject_key", [
    "enterprise_authorized",
    "other_person",
    "organization_representative",
])
async def test_cac_doi_tuong_moi_duoc_luu_de_truyen_sang_modal(subject_key):
    conv = _conv()
    await flow.handle_turn(
        conv,
        Intent("action", "set_execution_subject", {"key": subject_key}),
    )
    assert conv["execution_subject"] == subject_key


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

    r = await _turn(conv, "__event:agency_selected")
    # Hướng A + gộp 1 câu: KHÔNG hiện câu riêng ở đây — dồn hết vào 1 câu đọc TRÊN trang login.
    assert r.display_md == ""

    r = await _turn(conv, '__event:page_status:{"loginPage": true, "loggedIn": false}')
    # 1 CÂU duy nhất: xác nhận cơ quan + kịch bản VNeID/QR; đọc xong FE thu gọn (collapse_after_tts).
    assert "đã chọn cơ quan" in r.display_md and "VNeID" in r.display_md and "Quét QR" in r.display_md
    assert any(a["type"] == "collapse_after_tts" for a in r.actions)

    r = await _turn(conv, '__event:page_status:{"formKind": "angular", "loggedIn": true}')
    assert conv["state"] == "consent"  # vào form → xin phép xử lý dữ liệu trước
    assert "Đã vào trang kê khai" in r.display_md
    assert "Đăng nhập thành công" not in r.display_md

    # Kể cả sidebar cũ gửi snapshot loggedIn=true, backend phải bỏ qua vì cổng đích
    # vẫn có thể chuyển sang SSO. Chỉ page_status của trang đích mới được quyết luồng.
    conv2 = _conv()
    await _turn(conv2, "kết hôn")
    await _turn(conv2, "__action:goto_login")
    r = await _turn(conv2, '__event:agency_selected:{"loggedIn": true}')
    assert conv2["state"] == "guide_login"
    assert r.display_md == "" and r.actions == []
    assert conv2["needed_login"] is False
    r = await _turn(conv2, '__event:page_status:{"loginPage": true, "loggedIn": false}')
    assert conv2["state"] == "guide_login"
    assert "đã đăng nhập sẵn" not in r.display_md
    assert "VNeID" in r.display_md and "Quét QR" in r.display_md
    r = await _turn(conv2, '__event:page_status:{"formKind": "angular", "loggedIn": true}')
    assert conv2["state"] == "consent"
    assert "Đã vào trang kê khai" in r.display_md
    assert "Đăng nhập thành công" not in r.display_md


@pytest.mark.asyncio
async def test_nut_kiem_tra_trang_khong_duoc_bo_qua_dang_nhap():
    """Nút phao/câu nói chỉ kích hoạt đọc DOM; trang SSO hoặc trang trung gian không được
    phép nhảy sang consent, chỉ trang hồ sơ thật mới được chuyển bước."""
    conv = _conv()
    await _turn(conv, "kết hôn")
    await _turn(conv, "__action:goto_login")

    check = await _turn(conv, "__event:sso_success")
    assert conv["state"] == "guide_login"
    assert check.actions == [{"type": "verify_portal_state"}]
    assert check.cards == []

    still_login = await _turn(
        conv,
        '__event:page_status:{"loginPage":true,"loggedIn":false,"manualCheck":true}',
    )
    assert conv["state"] == "guide_login"
    assert "vẫn đang ở bước **đăng nhập VNeID**" in still_login.display_md

    not_ready = await _turn(
        conv,
        '__event:page_status:{"loggedIn":true,"manualCheck":true}',
    )
    assert conv["state"] == "guide_login"
    assert "chưa vào phần làm hồ sơ" in not_ready.display_md

    ready = await _verify_portal_ready(conv)
    assert conv["state"] == "consent"
    assert any(card["kind"] == "consent_form" for card in ready.cards)


@pytest.mark.asyncio
async def test_guide_login_nhac_passcode_mot_lan_moi_luot_modal():
    """Passcode mở lại panel ở FE; backend giữ nguyên lời dặn và cho phép nhắc lại khi modal
    đã biến mất rồi thực sự xuất hiện lần mới."""
    conv = _conv()
    await _turn(conv, "kết hôn")
    await _turn(conv, "__action:goto_login")

    event = ('__event:page_status:{"loginPage":true,"loggedIn":false,'
             '"vneidPasscodePrompt":true}')
    r = await _turn(conv, event)
    expected = "Công dân vui lòng nhập **passcode VNeID gồm 6 chữ số** vào màn hình, sau đó bấm **Xác nhận** để tiếp tục ạ."
    assert r.display_md == expected
    assert "passcode VNeID gồm 6 chữ số" in r.tts_text
    assert r.actions == []

    # React render lại khi modal vẫn mở không được tạo thêm bubble/TTS.
    r = await _turn(conv, event)
    assert r.display_md == "" and r.tts_text == ""

    # Modal biến mất rồi hiện lại (ví dụ nhập sai mã) là một lượt mới, được nhắc lại.
    r = await _turn(conv, '__event:page_status:{"loginPage":true,"loggedIn":false,'
                          '"vneidPasscodePrompt":false}')
    assert r.display_md == ""
    r = await _turn(conv, event)
    assert r.display_md == expected


@pytest.mark.asyncio
async def test_guide_login_huong_dan_ma_xac_nhan_va_chia_se_du_lieu_dung_modal():
    """Ba modal SSO dùng chung URL nhưng phải có lời dặn riêng và không lặp khi React render lại."""
    conv = _conv()
    await _turn(conv, "kết hôn")
    await _turn(conv, "__action:goto_login")

    login_code = ('__event:page_status:{"loginPage":true,"loggedIn":false,'
                  '"vneidLoginCodePrompt":true}')
    r = await _turn(conv, login_code)
    assert "mã xác nhận đăng nhập" in r.display_md
    assert "Xác nhận" in r.display_md
    assert r.actions == []
    duplicate = await _turn(conv, login_code)
    assert duplicate.display_md == "" and duplicate.tts_text == ""

    sharing = ('__event:page_status:{"loginPage":true,"loggedIn":true,'
               '"vneidDataSharingPrompt":true}')
    r = await _turn(conv, sharing)
    assert "Tôi đã đọc và hiểu rõ nội dung mục đích" in r.display_md
    assert "Quyền, nghĩa vụ của chủ thể dữ liệu" in r.display_md
    assert "Xác nhận chia sẻ" in r.display_md
    assert "passcode 6 số của ứng dụng VNeID" in r.display_md
    assert "passcode 6 số của ứng dụng VNeID" in r.tts_text
    duplicate = await _turn(conv, sharing)
    assert duplicate.display_md == "" and duplicate.tts_text == ""

    passcode = ('__event:page_status:{"loginPage":true,"loggedIn":false,'
                '"vneidPasscodePrompt":true}')
    r = await _turn(conv, passcode)
    assert "passcode VNeID gồm 6 chữ số" in r.display_md


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


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["collecting_docs", "filling", "reviewing", "attaching"])
async def test_resolve_llm_nhan_intent_yeu_cau_dinh_kem_o_trang_ke_khai(monkeypatch, state):
    """Câu tự do phải qua LLM và chỉ được nhận request_attach ở đúng state đã whitelist."""
    captured = {}

    async def fake(messages, **_kwargs):
        captured["system"] = messages[0]["content"]
        return '{"kind":"state_action","value":"request_attach"}'

    monkeypatch.setattr(intents, "llm_chat", fake)

    assert resolve_deterministic("đính kèm đi", state) is None
    resolved = await resolve("đính kèm đi", state)

    assert (resolved.kind, resolved.value) == ("action", "request_attach")
    assert '"request_attach"' in captured["system"]
    assert "CHƯA xác nhận đã rà soát form" in captured["system"]


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["reviewing", "attaching"])
async def test_resolve_llm_nhan_intent_dieu_chinh_giay_to_o_ke_khai(monkeypatch, state):
    """Nút có action máy; câu nói tương đương cũng phải được LLM map vào cùng action."""
    captured = {}

    async def fake(messages, **_kwargs):
        captured["system"] = messages[0]["content"]
        return '{"kind":"state_action","value":"add_documents"}'

    monkeypatch.setattr(intents, "llm_chat", fake)

    assert resolve_deterministic("tôi muốn điều chỉnh giấy tờ", state) is None
    resolved = await resolve("tôi muốn điều chỉnh giấy tờ", state)

    assert (resolved.kind, resolved.value) == ("action", "add_documents")
    assert '"add_documents"' in captured["system"]


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
    check = await _turn(conv, "tôi vào trang kê khai rồi")  # lời nói chỉ yêu cầu kiểm tra DOM
    assert conv["state"] == "guide_login"
    assert check.actions == [{"type": "verify_portal_state"}]
    await _verify_portal_ready(conv)
    assert conv["state"] == "consent"
    await _turn(conv, "đồng ý")                          # chấp thuận BẰNG LỜI — vẫn hợp lệ
    assert conv["state"] == "ask_doc_method"
    await _turn(conv, "chụp bằng điện thoại")
    assert conv["state"] == "qr_waiting"
    await _turn(conv, "__event:mobile_connected")
    await _turn(conv, "chụp xong hết rồi")               # docs_complete bằng lời
    assert conv["state"] == "filling"
    review = await _turn(conv, "__action:fill_report:{\"filled\": 20}")
    assert conv["state"] == "reviewing"
    assert "bấm **Đính kèm giấy tờ** trong Trợ lý" in review.display_md
    assert "tự đính kèm" not in review.display_md
    await _turn(conv, "chuẩn rồi, đính kèm đi")          # confirm_review bằng lời
    assert conv["state"] == "attaching"


@pytest.mark.asyncio
async def test_wizard_ket_hon_modal_chu_ho_so_ke_khai():
    """Kết hôn nhận consent + tài liệu ngay tại trang chủ hồ sơ."""
    conv = _conv()
    await _turn(conv, "kết hôn")
    await _turn(conv, "__action:goto_login")
    await _turn(conv, "__event:agency_selected")

    r = await _turn(conv, '__event:page_status:{"infoModal": true, "loggedIn": true}')
    # Modal được xác nhận nền, không phát thêm bubble đăng nhập/thông tin chung.
    assert r.display_md == ""
    assert r.actions[0]["type"] == "confirm_info_modal"
    assert r.actions[0]["executionSubject"] == {
        "key": "self",
        "label": "Làm thủ tục cho bản thân",
        "portalValue": "null",
    }
    # Modal chưa đóng kịp, FE báo lại → bấm lại nhưng im lặng.
    r = await _turn(conv, '__event:page_status:{"infoModal": true, "loggedIn": true}')
    assert r.display_md == "" and r.actions[0]["type"] == "confirm_info_modal"

    owner = {"fullName":"VŨ ĐÌNH THIẾT","identityNumber":"040203015844"}
    r = await _turn(conv, f'__event:page_status:{{"wizardStep":1,"loggedIn":true,"ownerContext":{__import__("json").dumps(owner)}}}')
    assert conv["state"] == "consent"
    assert conv["owner_context"] == owner
    assert "Thông tin chủ hồ sơ" in r.display_md
    assert any(c["kind"] == "consent_form" for c in r.cards)


@pytest.mark.asyncio
async def test_wizard_xac_nhan_tthn_ap_dung_luong_chu_ho_so_moi():
    """XNTTHN xin consent và nhận giấy tờ ngay tại bước chủ hồ sơ như kết hôn."""
    conv = _conv()
    await _turn(conv, "tình trạng hôn nhân")
    await _turn(conv, "__action:goto_login")

    owner = '{"fullName":"VŨ ĐÌNH THIẾT","identityNumber":"040203015844"}'
    r = await _turn(
        conv,
        f'__event:page_status:{{"wizardStep":1,"loggedIn":true,"ownerContext":{owner}}}',
    )

    assert conv["procedure_key"] == "xac-nhan-tinh-trang-hon-nhan"
    assert conv["state"] == "consent" and conv["owner_phase"] is True
    assert conv["owner_context"]["identityNumber"] == "040203015844"
    assert "Thông tin chủ hồ sơ" in r.display_md
    assert any(card["kind"] == "consent_form" for card in r.cards)


@pytest.mark.asyncio
async def test_ket_hon_owner_context_fallback_tu_principal_vneid():
    conv = _conv()
    await _turn(conv, "kết hôn")
    await _turn(conv, "__action:goto_login")
    r = await _turn(conv, '__event:page_status:{"wizardStep":1,"loggedIn":true,'
                          '"principal":{"cccd":"040203015844","name":"VŨ ĐÌNH THIẾT"},'
                          '"ownerContext":null}')
    assert conv["state"] == "consent"
    assert conv["owner_context"] == {
        "fullName": "VŨ ĐÌNH THIẾT",
        "identityNumber": "040203015844",
        "source": "portal_principal",
    }
    assert any(card["kind"] == "consent_form" for card in r.cards)


@pytest.mark.asyncio
async def test_ket_hon_owner_roi_ke_khai_roi_tu_dinh_kem(monkeypatch):
    from app.channels.handfree.chat import pipeline_runner

    conv = _conv()
    await _turn(conv, "kết hôn")
    await _turn(conv, "__action:goto_login")
    owner_json = '{"fullName":"VŨ ĐÌNH THIẾT","identityNumber":"040203015844"}'
    await _turn(conv, f'__event:page_status:{{"wizardStep":1,"loggedIn":true,"ownerContext":{owner_json}}}')
    await _accept_consent(conv)
    await _turn(conv, "scan tại quầy")
    r = await _turn(conv, "__event:docs_complete")
    assert conv["state"] == "owner_filling"
    assert "đúng chủ hồ sơ" in r.display_md

    conv["owner_fields"] = [{
        "key": "issueDate", "label": "Ngày cấp", "comp": "owner-date",
        "value": "02/07/2021", "overwrite": False,
    }]
    r = await _turn(conv, "__event:owner_fields_ready")
    assert r.actions[0]["type"] == "fill_owner_fields"
    await _turn(conv, '__action:owner_fill_report:{"filled":1,"kept":2,"notFound":[]}')
    assert conv["state"] == "owner_waiting_next" and conv["owner_info_done"] is True

    process_calls = []
    monkeypatch.setattr(pipeline_runner, "run_process", lambda *args: process_calls.append(args) or "process-job")
    monkeypatch.setattr(pipeline_runner, "spawn", lambda _job: None)
    r = await _turn(conv, '__event:page_status:{"wizardStep":2,"loggedIn":true}')
    assert conv["state"] == "filling" and len(process_calls) == 1
    assert r.display_md == "Bây giờ em sẽ **điền thông tin kê khai** giúp công dân nhé."
    assert r.tts_text == "Bây giờ em sẽ điền thông tin kê khai giúp công dân nhé."

    conv["fields"] = [{"name": "HoTenBenNam", "comp": "x-input", "value": "VŨ ĐÌNH THIẾT"}]
    await _turn(conv, "__event:fields_ready")
    r = await _turn(conv, '__action:fill_report:{"filled":1}')
    assert conv["state"] == "attaching"
    assert [chip.get("send") for chip in r.chips] == [
        "__action:refill", "__action:add_documents",
    ]
    assert "Thành phần hồ sơ" in r.display_md

    attach_calls = []
    monkeypatch.setattr(pipeline_runner, "run_attach", lambda *args: attach_calls.append(args) or "attach-job")
    await _turn(conv, '__event:page_status:{"wizardStep":3,"loggedIn":true}')
    assert len(attach_calls) == 1 and conv["attachment_plan_started"] is True


@pytest.mark.asyncio
async def test_owner_sang_ke_khai_bang_mau_dien_tu_khi_stepper_khong_doc_duoc(monkeypatch):
    from app.channels.handfree.chat import pipeline_runner

    conv = _conv()
    conv.update({
        "procedure_key": "ket-hon",
        "state": "owner_waiting_next",
        "upload_session_id": "HS-DECLARATION-FALLBACK",
        "owner_info_done": True,
        "docs_target": "owner",
    })
    process_calls = []
    monkeypatch.setattr(
        pipeline_runner, "run_process",
        lambda *args: process_calls.append(args) or "process-job",
    )
    monkeypatch.setattr(pipeline_runner, "spawn", lambda _job: None)

    r = await _turn(
        conv,
        '__event:page_status:{"wizardStep":0,"formKind":"legacy",'
        '"declarationTarget":true,"loggedIn":true}',
    )

    assert conv["state"] == "filling"
    assert conv["docs_target"] == "declaration"
    assert len(process_calls) == 1
    assert "điền thông tin kê khai" in r.display_md


@pytest.mark.asyncio
async def test_owner_fill_report_noi_ro_ten_truong_con_thieu():
    conv = _conv()
    conv.update({
        "procedure_key": "ket-hon",
        "state": "owner_filling",
        "owner_fields": [
            {"label": "Ngày cấp", "reportLabel": "ngày cấp"},
            {"label": "Nơi cấp", "reportLabel": "nơi cấp"},
            {"label": "Số điện thoại", "reportLabel": "số điện thoại"},
            {"label": "Địa chỉ chi tiết", "reportLabel": "địa chỉ"},
        ],
        "owner_match": {"matched": True},
    })
    r = await _turn(
        conv,
        '__action:owner_fill_report:{"filled":2,"kept":1,'
        '"filledLabels":["Nơi cấp","Địa chỉ chi tiết"],'
        '"keptLabels":["Ngày cấp"],"notFound":["Số điện thoại"]}',
    )
    assert r.display_md == (
        "✅ Em đã điền xong **ngày cấp, nơi cấp và địa chỉ**.\n\n"
        "Còn thiếu **số điện thoại**, công dân vui lòng tự điền giúp em.\n\n"
        "Công dân kiểm tra rồi bấm **Bước tiếp theo**."
    )
    assert "2 mục" not in r.display_md and "1 mục" not in r.display_md


@pytest.mark.asyncio
async def test_owner_fill_zero_bao_loi_va_cho_dien_lai():
    conv = _conv()
    conv.update({
        "procedure_key": "ket-hon",
        "state": "owner_filling",
        "owner_fields": [{"key": "issueDate", "label": "Ngày cấp", "comp": "owner-date",
                          "value": "02/07/2021", "overwrite": False}],
        "owner_match": {"matched": True},
    })
    r = await _turn(conv, '__action:owner_fill_report:{"filled":0,"kept":0,'
                          '"errors":["Không tìm thấy frame chứa các ô"]}')
    assert conv["state"] == "owner_waiting_next"
    assert "chưa nhận lệnh điền" in r.display_md
    assert r.chips[0]["send"] == "__action:retry_owner_fill"

    r = await _turn(conv, "điền đi")
    assert conv["state"] == "owner_filling"
    assert r.actions[0]["type"] == "fill_owner_fields"


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

    from app.channels.handfree.chat import pipeline_runner

    spawned = []
    attach_calls = []

    def fake_run_attach(*args):
        attach_calls.append(args)
        return "attach-job"

    monkeypatch.setattr(pipeline_runner, "run_attach", fake_run_attach)
    monkeypatch.setattr(
        pipeline_runner,
        "run_process",
        lambda *_args: pytest.fail("attach-only không được gọi process pipeline"),
    )
    monkeypatch.setattr(pipeline_runner, "spawn", spawned.append)

    r = await _turn(conv, "__event:docs_complete")
    assert conv["state"] == "choosing_attach_mode"
    assert spawned == [] and attach_calls == []  # chưa chọn thì chưa OCR/LLM
    assert [c["label"] for c in r.chips] == [
        "📎 Đính kèm trong 1 hồ sơ", "🗂️ Đính kèm nhiều hồ sơ",
    ]

    r = await _turn(conv, '__action:attach_mode:{"value":"split"}')
    assert conv["state"] == "attaching" and conv["attach_mode"] == "split"
    assert spawned == ["attach-job"]
    assert attach_calls[0][3] == {"splitMode": True}
    assert "mỗi tài liệu một hồ sơ riêng" in r.display_md

    conv["attach_plan"] = [{"fileIndex": 0, "documentName": "Tài liệu 1",
                            "componentName": "Giấy tờ cần chứng thực bản sao"}]
    r = await _turn(conv, "__event:attach_ready")
    assert r.actions[0]["type"] == "attach_plan"
    assert r.actions[0]["mode"] == "split"

    r = await _turn(conv, '__action:attach_report:{"attached":2,"errors":["Hồ sơ 3: lỗi"],'
                          '"mode":"split","dossiersTotal":3,"dossiersSucceeded":2,'
                          '"dossiersFailed":1,"queueId":"queue-test"}')
    assert conv["state"] == "done"
    assert "2/3 hồ sơ" in r.display_md


@pytest.mark.asyncio
async def test_chung_thuc_ban_sao_chon_mot_ho_so(monkeypatch):
    """Nhánh gộp giữ engine hiện tại nhưng action/trace nhận splitMode=false tường minh."""
    from app.channels.handfree.chat import pipeline_runner

    conv = _conv()
    conv.update({
        "procedure_key": "chung-thuc-ban-sao",
        "state": "choosing_attach_mode",
        "upload_session_id": "HS-TEST01",
    })
    calls = []
    monkeypatch.setattr(pipeline_runner, "run_attach", lambda *args: calls.append(args) or "job")
    monkeypatch.setattr(pipeline_runner, "spawn", lambda job: None)

    r = await _turn(conv, '__action:attach_mode:{"value":"merge"}')
    assert conv["attach_mode"] == "merge" and conv["state"] == "attaching"
    assert calls[0][3] == {"splitMode": False}
    assert "tất cả tài liệu trong một hồ sơ" in r.display_md


@pytest.mark.asyncio
async def test_chung_thuc_chu_ky_tach_ho_so_dung_chung_giay_to_tuy_than(monkeypatch):
    """Số hồ sơ = số văn bản STT1; giấy tờ tùy thân STT2 chỉ là tài liệu dùng chung."""
    from app.channels.handfree.chat import pipeline_runner

    conv = _conv()
    conv.update({
        "procedure_key": "chung-thuc-chu-ky",
        "state": "collecting_docs",
        "upload_session_id": "HS-CHUKY",
    })

    async def fake_progress(_sid):
        return {"received": 3, "total": 2, "files_count": 3}

    calls = []
    monkeypatch.setattr(flow.upload_service, "progress_of", fake_progress)
    monkeypatch.setattr(pipeline_runner, "run_attach", lambda *args: calls.append(args) or "job")
    monkeypatch.setattr(pipeline_runner, "spawn", lambda _job: None)

    r = await _turn(conv, "__event:docs_complete")
    assert conv["state"] == "choosing_attach_mode"
    assert [chip["label"] for chip in r.chips] == [
        "📎 Đính kèm trong 1 hồ sơ", "🗂️ Đính kèm nhiều hồ sơ",
    ]

    await _turn(conv, '__action:attach_mode:{"value":"split"}')
    assert calls[0][3] == {"splitMode": True}

    conv["attach_plan"] = [
        {"fileIndex": 0, "documentName": "Văn bản A", "componentIndex": 1,
         "componentName": "Giấy tờ cần chứng thực chữ ký"},
        {"fileIndex": 1, "documentName": "Văn bản B", "componentIndex": None,
         "componentName": "Giấy tờ cần chứng thực chữ ký"},
        {"fileIndex": 2, "documentName": "Căn cước", "componentIndex": 2,
         "componentName": "Giấy tờ tùy thân"},
    ]
    r = await _turn(conv, "__event:attach_ready")
    assert "2 hồ sơ" in r.display_md
    assert "STT 1" in r.display_md and "STT 2" in r.display_md
    assert r.actions[0]["mode"] == "split"
    assert flow._is_signature_identity_plan_item({
        "documentName": "Hộ chiếu",
        "componentName": "Giấy tờ tùy thân",
        "componentIndex": 9,
        "target": "existing",
    }) is True


@pytest.mark.asyncio
async def test_attach_dung_trang_moi_dinh():
    """Đòi đính kèm khi trang còn ở bước kê khai → dặn chuyển bước, KHÔNG chạy engine;
    sang bước Thành phần hồ sơ tự đính lại; đính được 0 tệp thì không chốt xong."""
    conv = _conv()
    await _turn(conv, "kết hôn")
    await _turn(conv, "__action:goto_login")
    await _verify_portal_ready(conv)
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
    assert r.chips == [{"label": "🗂️ Điều chỉnh giấy tờ", "send": "__action:add_documents"}]


@pytest.mark.asyncio
async def test_bo_sung_giay_to_mo_lai_cung_phien_va_lap_plan_toan_bo(monkeypatch):
    """Bổ sung không tạo session rỗng: mở lại đúng SID, giữ danh sách cũ và chạy lại planner."""
    from app.channels.handfree.chat import pipeline_runner

    conv = _conv()
    conv.update({
        "procedure_key": "ket-hon",
        "state": "done",
        "upload_session_id": "HS-OLD",
        "docs_target": "attachment",
        "attach_done": True,
        "attachment_plan_started": True,
        "attach_action_in_progress": True,
        "attach_plan": [{"fileIndex": 0}, {"fileIndex": 1}, {"fileIndex": 2}],
        "attach_trace_request_id": "trace-old",
        "client_capabilities": {"supportsPageBoundDocsComplete": True},
    })
    reopened = []

    async def fake_reopen_for_supplement(sid):
        reopened.append(sid)
        return {"_id": sid, "complete": False, "manual_complete_only": True,
                "files": ["a", "b", "c"]}

    async def must_not_create(_conv):
        pytest.fail("lượt bổ sung không được tạo upload session mới")

    monkeypatch.setattr(flow.up_store, "reopen_for_supplement", fake_reopen_for_supplement)
    monkeypatch.setattr(flow.upload_service, "create_for_conversation", must_not_create)

    r = await _turn(conv, "__action:add_documents")

    assert reopened == ["HS-OLD"]
    assert conv["state"] == "ask_doc_method"
    assert conv["upload_session_id"] == "HS-OLD"
    assert conv["supplementing_documents"] is True
    assert conv["supplement_reuse_session"] is True
    assert conv["documents_adjustment_target"] == "attachment"
    assert conv["attach_plan"] == []
    assert conv["attach_trace_request_id"] is None
    assert r.actions == [{"type": "resume_upload_session", "session_id": "HS-OLD"}]
    assert r.cards == [{"kind": "doc_options", "options": ["qr", "scan"]}]
    assert r.chips == [{
        "label": "✅ Hoàn tất điều chỉnh, đính kèm lại",
        "send": "__action:docs_done",
        "solid": True,
    }]
    assert "HS-OLD" in r.display_md

    choose = await _turn(conv, "scan tại quầy")
    assert conv["state"] == "collecting_docs"
    assert conv["upload_session_id"] == "HS-OLD"
    assert choose.actions == [{"type": "pick_files", "session_id": "HS-OLD"}]

    attach_calls = []

    def fake_run_attach(*args):
        attach_calls.append(args)
        return "attach-job"

    monkeypatch.setattr(pipeline_runner, "run_attach", fake_run_attach)
    monkeypatch.setattr(pipeline_runner, "spawn", lambda _job: None)
    await _turn(
        conv,
        '__event:docs_complete:{"pageContextCaptured":true,"wizardStep":3,'
        '"attachmentTarget":true}',
    )

    assert conv["state"] == "attaching"
    assert conv["docs_target"] == "attachment"
    assert conv["attachment_plan_started"] is True
    assert attach_calls and attach_calls[0][1] == "HS-OLD"


@pytest.mark.asyncio
async def test_dieu_chinh_chi_xoa_tep_co_the_dinh_kem_lai_khong_can_upload(monkeypatch):
    """Mở phiên cũ rồi chốt thẳng vẫn chạy planner: QR/Scan chỉ dùng khi cần thêm tệp."""
    from app.channels.handfree.chat import pipeline_runner

    conv = _conv()
    conv.update({
        "procedure_key": "ket-hon",
        "state": "done",
        "upload_session_id": "HS-OLD",
        "docs_target": "attachment",
        "attach_done": True,
        "client_capabilities": {"supportsPageBoundDocsComplete": True},
    })

    async def fake_reopen(sid):
        return {"_id": sid, "complete": False, "manual_complete_only": True,
                "files": ["a", "c"]}

    completed = []
    attach_calls = []

    async def fake_complete(sid):
        completed.append(sid)

    def fake_run_attach(*args):
        attach_calls.append(args)
        return "attach-job"

    monkeypatch.setattr(flow.up_store, "reopen_for_supplement", fake_reopen)
    monkeypatch.setattr(flow.upload_service, "complete_session", fake_complete)
    monkeypatch.setattr(pipeline_runner, "run_attach", fake_run_attach)
    monkeypatch.setattr(pipeline_runner, "spawn", lambda _job: None)

    await _turn(conv, "__action:add_documents")
    assert conv["state"] == "ask_doc_method"

    await _turn(
        conv,
        '__action:docs_done:{"pageContextCaptured":true,"wizardStep":3,'
        '"attachmentTarget":true}',
    )

    assert completed == ["HS-OLD"]
    assert conv["state"] == "attaching"
    assert conv["attachment_plan_started"] is True
    assert attach_calls and attach_calls[0][1] == "HS-OLD"


@pytest.mark.asyncio
async def test_dieu_chinh_giay_to_o_ke_khai_goi_lai_process_bang_cung_phien(monkeypatch):
    """Kê khai mở cùng SID, cho xem/xóa/thêm và chốt phải OCR/LLM lại, không chạy attach."""
    from app.channels.handfree.chat import pipeline_runner

    conv = _conv()
    conv.update({
        "procedure_key": "ket-hon",
        "state": "reviewing",
        "upload_session_id": "HS-DECLARATION-OLD",
        "docs_target": "declaration",
        "fields": [{"name": "HoTen", "value": "cache cũ"}],
        "fill_report": {"filled": 12},
        "trace_request_id": "trace-old",
        "client_capabilities": {"supportsPageBoundDocsComplete": True},
    })
    reopened = []

    async def fake_reopen(sid):
        reopened.append(sid)
        return {"_id": sid, "complete": False, "manual_complete_only": True,
                "files": ["a", "c"]}

    completed = []
    calls = []

    async def fake_complete(sid):
        completed.append(sid)

    monkeypatch.setattr(flow.up_store, "reopen_for_supplement", fake_reopen)
    monkeypatch.setattr(flow.upload_service, "complete_session", fake_complete)
    monkeypatch.setattr(
        pipeline_runner, "run_process",
        lambda *args: calls.append(("process", args)) or "process-job",
    )
    monkeypatch.setattr(
        pipeline_runner, "run_attach",
        lambda *args: calls.append(("attach", args)) or "attach-job",
    )
    monkeypatch.setattr(pipeline_runner, "spawn", lambda _job: None)

    opened = await _turn(conv, "__action:add_documents")

    assert reopened == ["HS-DECLARATION-OLD"]
    assert conv["state"] == "ask_doc_method"
    assert conv["docs_target"] == "declaration"
    assert conv["documents_adjustment_target"] == "declaration"
    assert conv["fields"] == [] and conv["fill_report"] == {}
    assert opened.actions == [{
        "type": "resume_upload_session", "session_id": "HS-DECLARATION-OLD",
    }]
    assert opened.cards == [{"kind": "doc_options", "options": ["qr", "scan"]}]
    assert opened.chips == [{
        "label": "✅ Hoàn tất điều chỉnh, điền lại tờ khai",
        "send": "__action:docs_done",
        "solid": True,
    }]
    assert "điền lại tờ khai" in opened.display_md

    await _turn(
        conv,
        '__action:docs_done:{"pageContextCaptured":true,"wizardStep":2,'
        '"declarationTarget":true,"formKind":"legacy"}',
    )

    assert completed == ["HS-DECLARATION-OLD"]
    assert conv["state"] == "filling"
    assert calls and calls[0][0] == "process"
    assert calls[0][1][1] == "HS-DECLARATION-OLD"
    assert not any(kind == "attach" for kind, _args in calls)

    report = await _turn(conv, '__action:fill_report:{"filled":15,"errors":[]}')
    assert conv["supplementing_documents"] is False
    assert conv["documents_adjustment_target"] == ""
    assert any(chip.get("send") == "__action:refill" for chip in report.chips)
    assert any(chip.get("send") == "__action:add_documents" for chip in report.chips)


@pytest.mark.asyncio
@pytest.mark.parametrize("upload_state", ["ask_doc_method", "qr_waiting", "collecting_docs"])
async def test_dieu_chinh_to_khai_tu_chuyen_sang_buoc_3_thi_tu_dinh_kem(
    monkeypatch, upload_state,
):
    """Không bấm điền lại mà sang bước hồ sơ: giữ SID và chạy attach đúng một lần."""
    from app.channels.handfree.chat import pipeline_runner

    conv = _conv()
    conv.update({
        "procedure_key": "ket-hon",
        "state": upload_state,
        "upload_session_id": "HS-DECLARATION-OLD",
        "docs_target": "declaration",
        "supplementing_documents": True,
        "supplement_reuse_session": True,
        "documents_adjustment_target": "declaration",
        "client_capabilities": {"supportsPageBoundDocsComplete": True},
    })
    completed = []
    calls = []

    async def fake_complete(sid):
        completed.append(sid)

    monkeypatch.setattr(flow.upload_service, "complete_session", fake_complete)
    monkeypatch.setattr(
        pipeline_runner, "run_attach",
        lambda *args: calls.append(("attach", args)) or "attach-job",
    )
    monkeypatch.setattr(
        pipeline_runner, "run_process",
        lambda *args: calls.append(("process", args)) or "process-job",
    )
    monkeypatch.setattr(pipeline_runner, "spawn", lambda _job: None)

    page_status = (
        '__event:page_status:{"pageContextCaptured":true,"wizardStep":3,'
        '"attachmentTarget":true,"attachmentComponentCount":2}'
    )
    await _turn(conv, page_status)

    assert completed == ["HS-DECLARATION-OLD"]
    assert conv["state"] == "attaching"
    assert conv["docs_target"] == "attachment"
    assert conv["documents_adjustment_target"] == "attachment"
    assert conv["upload_session_id"] == "HS-DECLARATION-OLD"
    assert conv["attachment_plan_started"] is True
    assert [kind for kind, _args in calls] == ["attach"]

    # Watcher có thể gửi lại cùng page_status; pipeline đang chạy không được phát lần hai.
    await _turn(conv, page_status)
    assert completed == ["HS-DECLARATION-OLD"]
    assert [kind for kind, _args in calls] == ["attach"]


@pytest.mark.asyncio
async def test_dieu_chinh_to_khai_khong_doi_pipeline_khi_chi_co_attachment_target_yeu(
    monkeypatch,
):
    """Nút chọn tệp đơn lẻ trong DOM không được coi là đã tới bảng Thành phần hồ sơ."""
    from app.channels.handfree.chat import pipeline_runner

    conv = _conv()
    conv.update({
        "procedure_key": "ket-hon",
        "state": "ask_doc_method",
        "upload_session_id": "HS-DECLARATION-OLD",
        "docs_target": "declaration",
        "supplementing_documents": True,
        "supplement_reuse_session": True,
        "documents_adjustment_target": "declaration",
    })
    completed = []
    calls = []

    async def fake_complete(sid):
        completed.append(sid)

    monkeypatch.setattr(flow.upload_service, "complete_session", fake_complete)
    monkeypatch.setattr(
        pipeline_runner, "run_attach",
        lambda *args: calls.append(args) or "attach-job",
    )
    monkeypatch.setattr(pipeline_runner, "spawn", lambda _job: None)

    await _turn(
        conv,
        '__event:page_status:{"wizardStep":0,"attachmentTarget":true,'
        '"attachmentComponentCount":0}',
    )

    assert completed == []
    assert calls == []
    assert conv["state"] == "ask_doc_method"
    assert conv["docs_target"] == "declaration"
    assert conv["documents_adjustment_target"] == "declaration"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("target", "spoken_command", "expected_state", "expected_pipeline"),
    [
        ("attachment", "đính kèm lại luôn", "attaching", "attach"),
        ("declaration", "điền lại luôn", "filling", "process"),
    ],
)
async def test_dang_hien_qr_van_chot_file_cu_de_dinh_kem_hoac_dien_to_khai(
    monkeypatch, target, spoken_command, expected_state, expected_pipeline,
):
    """Đổi ý sau khi mở QR: dùng file hiện có cho đúng target, không ép quét thêm."""
    from app.channels.handfree.chat import pipeline_runner

    conv = _conv()
    conv.update({
        "procedure_key": "ket-hon",
        "state": "qr_waiting",
        "doc_method": "qr",
        "upload_session_id": "HS-OLD",
        "docs_target": target,
        "supplementing_documents": True,
        "supplement_reuse_session": True,
        "documents_adjustment_target": target,
    })
    completed = []
    calls = []

    async def fake_complete(sid):
        completed.append(sid)

    monkeypatch.setattr(flow.upload_service, "complete_session", fake_complete)
    monkeypatch.setattr(
        pipeline_runner, "run_attach",
        lambda *args: calls.append(("attach", args)) or "attach-job",
    )
    monkeypatch.setattr(
        pipeline_runner, "run_process",
        lambda *args: calls.append(("process", args)) or "process-job",
    )
    monkeypatch.setattr(pipeline_runner, "spawn", lambda _job: None)

    await _turn(conv, spoken_command)

    assert completed == ["HS-OLD"]
    assert conv["state"] == expected_state
    assert calls and calls[0][0] == expected_pipeline
    assert calls[0][1][1] == "HS-OLD"


@pytest.mark.asyncio
async def test_bo_sung_toan_file_trung_van_hoan_tat():
    """Extension skip a/c đã có trên cổng thì backend không được báo '0 tệp' thất bại."""
    conv = _conv()
    conv.update({
        "procedure_key": "ket-hon",
        "state": "attaching",
        "upload_session_id": "HS-OLD",
        "supplementing_documents": True,
        "supplement_reuse_session": True,
        "attach_trace_request_id": "trace-new",
    })

    r = await _turn(
        conv,
        '__action:attach_report:{"attached":0,"skipped":2,"errors":[]}',
    )

    assert conv["state"] == "done"
    assert conv["attach_done"] is True
    assert conv["supplementing_documents"] is False
    assert conv["documents_adjustment_target"] == ""
    assert "không đính trùng" in r.display_md
    assert r.chips == [{"label": "🗂️ Điều chỉnh giấy tờ", "send": "__action:add_documents"}]


@pytest.mark.asyncio
async def test_attach_plan_summary_short_and_page_status_does_not_dispatch_twice():
    conv = _conv()
    conv.update({
        "procedure_key": "trich-luc-ks",
        "state": "attaching",
        "upload_session_id": "HS-TEST01",
        "attach_plan": [{
            "fileIndex": 0,
            "fileName": "Căn cước công dân.pdf",
            "documentName": "Căn cước công dân",
            "componentName": (
                "Hộ chiếu hoặc Thẻ căn cước của hai bên. "
                "Tên Hồ Sơ: Hộ chiếu hoặc Thẻ căn cước của hai bên."
            ),
            "componentIndex": 3,
            "target": "existing",
        }],
    })

    ready = await _turn(conv, "__event:attach_ready")
    assert "Căn cước công dân.pdf** → STT 3" in ready.display_md
    assert "Tên Hồ Sơ" not in ready.display_md
    assert len(ready.actions) == 1

    queued_page_status = await _turn(conv, '__event:page_status:{"wizardStep": 3}')
    assert queued_page_status.display_md == ""
    assert queued_page_status.actions == []


@pytest.mark.asyncio
async def test_duplicate_attach_report_after_done_is_silent():
    conv = _conv()
    conv.update({"state": "done", "attach_plan": [{"fileIndex": 0}]})

    duplicate = await _turn(conv, '__action:attach_report:{"attached": 1, "errors": []}')

    assert duplicate.display_md == ""
    assert duplicate.actions == []


@pytest.mark.asyncio
async def test_page_status_lac_ngoai_guide_login_im_lang():
    conv = _conv()
    await _turn(conv, "khai sinh")
    await _turn(conv, "__action:goto_login")
    await _verify_portal_ready(conv)
    # page_status lạc vào bước consent cũng phải im lặng (không đẻ bubble giữa lúc xin phép).
    r = await _turn(conv, '__event:page_status:{"formKind": "legacy", "loggedIn": true}')
    assert r.display_md == "" and not r.cards
    await _accept_consent(conv)
    assert conv["state"] == "ask_doc_method"
    r = await _turn(conv, '__event:page_status:{"formKind": "legacy", "loggedIn": true}')
    assert r.display_md == "" and not r.cards  # bắn trùng sau khi chuyển bước → im lặng


@pytest.mark.asyncio
async def test_done_flow_waits_for_logout_choice_and_supports_both_branches():
    """Cổng báo nộp xong → hỏi giữ phiên hay logout, mặc định logout sau 2 phút."""
    conv = _conv()
    conv["state"] = "done"

    r = await _turn(conv, "__event:submitted")
    assert "hoàn thành việc nộp hồ sơ" in r.display_md
    assert "2 phút" in r.display_md
    assert "đăng xuất tài khoản" in r.display_md
    assert "đăng xuất tài khoản" in r.tts_text
    assert "sau hai phút" in r.tts_text
    assert r.cards == []
    assert r.chips == [
        {"label": "Có, hãy đăng xuất", "send": "__action:logout_citizen", "solid": True},
        {"label": "Không, nộp thêm hồ sơ", "send": "__action:continue_dossiers"},
    ]
    assert r.actions == [{"type": "await_logout_choice", "delay_ms": 120_000}]
    assert conv["submitted_completed"] is True
    assert conv["submitted_logout_decision"] == "pending"

    # Event trùng do reload chỉ khôi phục timer, không được sinh thêm bubble/chip/TTS.
    duplicate = await _turn(conv, "__event:submitted")
    assert duplicate.display_md == ""
    assert duplicate.tts_text == ""
    assert duplicate.chips == []
    assert duplicate.cards == []
    assert duplicate.actions == [{"type": "await_logout_choice", "delay_ms": 120_000}]

    logout = await _turn(conv, "__action:logout_citizen")
    assert logout.display_md == ""
    assert logout.actions == [{"type": "logout_citizen"}]
    assert conv["submitted_logout_decision"] == "logout"

    duplicate_after_logout = await _turn(conv, "__event:submitted")
    assert duplicate_after_logout.display_md == ""
    assert duplicate_after_logout.chips == []
    assert duplicate_after_logout.actions == []
    assert conv["submitted_logout_decision"] == "logout"

    conv["submitted_logout_decision"] = "pending"
    keep = await _turn(conv, "__action:continue_dossiers")
    assert keep.display_md == ""
    assert keep.actions == [{"type": "continue_dossiers"}]
    assert conv["submitted_logout_decision"] == "continue"

    duplicate_after_continue = await _turn(conv, "__event:submitted")
    assert duplicate_after_continue.display_md == ""
    assert duplicate_after_continue.chips == []
    assert duplicate_after_continue.actions == []
    assert conv["submitted_logout_decision"] == "continue"


@pytest.mark.asyncio
async def test_lay_du_lieu_da_luu():
    """Nhánh 'Lấy dữ liệu đã lưu': hỏi SĐT → áp profile → chạy thẳng pipeline (docs/08 §1.2)."""
    conv = _conv()
    await _turn(conv, "khai sinh")
    await _turn(conv, "__action:goto_login")
    await _verify_portal_ready(conv)
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
    await _verify_portal_ready(conv2)
    await _accept_consent(conv2)
    await _turn(conv2, "__action:doc_method:{\"value\":\"profile\"}")
    r = await _turn(conv2, "0999999999")
    assert conv2["state"] == "ask_doc_method"
    assert "chưa tìm thấy" in r.display_md


@pytest.mark.asyncio
async def test_moi_reply_deu_co_tts():
    conv = _conv()
    for msg in ["khai sinh", "__action:goto_login"]:
        r = await _turn(conv, msg)
        assert r.tts_text.strip(), f"thiếu tts_text ở lượt '{msg}'"
        assert "**" not in r.tts_text, "tts_text không được chứa markdown"
    r = await _verify_portal_ready(conv)
    assert r.tts_text.strip() and "**" not in r.tts_text
    for msg in ["đồng ý", "chụp bằng điện thoại"]:
        r = await _turn(conv, msg)
        assert r.tts_text.strip(), f"thiếu tts_text ở lượt '{msg}'"
        assert "**" not in r.tts_text, "tts_text không được chứa markdown"


@pytest.mark.asyncio
async def test_consent_dong_y_ghi_nhat_ky(consent_persisted):
    """Đồng ý qua card → log lưu đủ trường pháp lý + conv mở cổng sang ask_doc_method."""
    conv = _conv()
    await _turn(conv, "kết hôn")
    await _turn(conv, "__action:goto_login")
    r = await _verify_portal_ready(conv)
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
    r = await _verify_portal_ready(conv)
    assert conv["state"] == "consent"
    assert any(c["kind"] == "consent_form" for c in r.cards)


@pytest.mark.asyncio
async def test_consent_tu_choi_va_doi_y(consent_persisted):
    """Từ chối → bot KHÔNG xử lý giấy tờ, có lối đổi ý; đồng ý lại bằng LỜI cũng hợp lệ."""
    conv = _conv()
    await _turn(conv, "kết hôn")
    await _turn(conv, "__action:goto_login")
    await _verify_portal_ready(conv)

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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("wizard_step", "expected_target", "expected_state", "expected_runner"),
    [
        (1, "owner", "owner_filling", "owner"),
        (2, "declaration", "filling", "process"),
        (3, "attachment", "attaching", "attach"),
    ],
)
async def test_chot_giay_to_chay_dung_pipeline_cua_trang_hien_tai(
    monkeypatch, wizard_step, expected_target, expected_state, expected_runner,
):
    """Cờ owner_phase cũ không được kéo người dân về bước chủ hồ sơ đã bỏ qua."""
    from app.channels.handfree.chat import pipeline_runner

    conv = _conv()
    conv.update({
        "procedure_key": "ket-hon",
        "state": "collecting_docs",
        "upload_session_id": "HS-TARGET",
        "owner_phase": True,  # mô phỏng đã từng nhìn thấy bước 1 trước khi công dân chuyển bước
        "owner_context": {"fullName": "NGUYỄN VĂN A", "identityNumber": "012345678901"},
        "client_capabilities": {"supportsPageBoundDocsComplete": True},
    })
    calls = []
    monkeypatch.setattr(pipeline_runner, "run_owner_info", lambda *_a: calls.append("owner") or "owner-job")
    monkeypatch.setattr(pipeline_runner, "run_process", lambda *_a: calls.append("process") or "process-job")
    monkeypatch.setattr(pipeline_runner, "run_attach", lambda *_a: calls.append("attach") or "attach-job")
    monkeypatch.setattr(pipeline_runner, "spawn", lambda job: None)

    r = await _turn(
        conv,
        f'__event:docs_complete:{{"pageContextCaptured":true,"wizardStep":{wizard_step}}}',
    )

    assert conv["docs_target"] == expected_target
    assert conv["state"] == expected_state
    assert calls == [expected_runner]
    if expected_target != "owner":
        assert conv["owner_phase"] is False
    assert r.display_md


@pytest.mark.asyncio
async def test_bat_dau_tu_ke_khai_tu_dong_noi_tiep_dinh_kem_cung_phien(monkeypatch):
    """Điền từ bước 2 xong phải chờ bước 3 rồi tự lập plan, không hỏi nút thủ công."""
    from app.channels.handfree.chat import pipeline_runner

    conv = _conv()
    conv.update({
        "procedure_key": "ket-hon",
        "state": "collecting_docs",
        "upload_session_id": "HS-DIRECT-DECLARATION",
        "client_capabilities": {"supportsPageBoundDocsComplete": True},
    })
    calls = []
    monkeypatch.setattr(
        pipeline_runner,
        "run_process",
        lambda _cid, sid, _key: calls.append(("process", sid)) or "process-job",
    )
    monkeypatch.setattr(
        pipeline_runner,
        "run_attach",
        lambda _cid, sid, _key, _options: calls.append(("attach", sid)) or "attach-job",
    )
    monkeypatch.setattr(pipeline_runner, "spawn", lambda _job: None)

    await _turn(
        conv,
        '__event:docs_complete:{"pageContextCaptured":true,"wizardStep":2,"formKind":"legacy"}',
    )
    assert conv["state"] == "filling"
    assert conv["auto_attach_after_fill"] is True
    assert calls == [("process", "HS-DIRECT-DECLARATION")]

    r = await _turn(conv, '__action:fill_report:{"filled":20,"notFound":[],"errors":[]}')
    assert conv["state"] == "attaching"
    assert all(chip.get("send") != "__action:confirm_review" for chip in r.chips)
    assert any(chip.get("send") == "__action:refill" for chip in r.chips)
    assert any(chip.get("send") == "__action:add_documents" for chip in r.chips)
    assert "Thành phần hồ sơ" in r.display_md
    assert "khi trang mở, em sẽ tự đính kèm giấy tờ" in r.display_md
    assert "bấm **Đính kèm giấy tờ**" not in r.display_md
    assert "Khi trang mở, em sẽ tự đính kèm giấy tờ" in r.tts_text
    assert calls == [("process", "HS-DIRECT-DECLARATION")]

    r = await _turn(
        conv,
        '__event:page_status:{"wizardStep":3,"attachmentTarget":true}',
    )
    assert conv["attachment_plan_started"] is True
    assert calls == [
        ("process", "HS-DIRECT-DECLARATION"),
        ("attach", "HS-DIRECT-DECLARATION"),
    ]
    assert "đính kèm" in r.display_md.lower()

    # Watcher có thể phát lại cùng chữ ký trang; khóa attachment_plan_started phải chặn lượt hai.
    await _turn(conv, '__event:page_status:{"wizardStep":3,"attachmentTarget":true}')
    assert calls.count(("attach", "HS-DIRECT-DECLARATION")) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["reviewing", "attaching"])
async def test_dien_lai_thong_tin_chay_lai_pipeline_backend(state, monkeypatch):
    """Nút/câu nói điền lại phải OCR/LLM lại, không phát fields cache cũ."""
    from app.channels.handfree.chat import pipeline_runner

    conv = _conv()
    conv.update({
        "procedure_key": "ket-hon",
        "state": state,
        "docs_target": "declaration",
        "pipeline_status": "waiting_attachment_page" if state == "attaching" else "fields_ready",
        "upload_session_id": "HS-REFILL",
        "trace_request_id": "trace-original",
        "fields": [{"name": "HoTen", "value": "Dữ liệu cũ"}],
        "fill_report": {"filled": 1},
    })
    calls = []

    def fake_run_process(conv_id, sid, procedure_key, **options):
        calls.append((conv_id, sid, procedure_key, options))
        return "refill-job"

    monkeypatch.setattr(pipeline_runner, "run_process", fake_run_process)
    monkeypatch.setattr(pipeline_runner, "spawn", lambda _job: None)
    saved = []

    async def fake_save(current):
        saved.append((current["state"], current["pipeline_status"]))

    monkeypatch.setattr(flow.conv_store, "save", fake_save)

    r = await _turn(conv, "điền lại")

    assert conv["state"] == "filling"
    assert conv["pipeline_status"] == "running"
    assert conv["fill_report"] == {}
    assert r.actions == []  # không phát lại fields cache ngay trong lượt bấm
    assert "đọc lại giấy tờ" in r.display_md
    assert saved == [("filling", "running")]
    assert calls == [(
        conv["_id"], "HS-REFILL", "ket-hon",
        {},
    )]


@pytest.mark.asyncio
async def test_dien_lai_thong_tin_chan_khi_khong_o_trang_ke_khai(monkeypatch):
    from app.channels.handfree.chat import pipeline_runner

    conv = _conv()
    conv.update({
        "procedure_key": "ket-hon",
        "state": "attaching",
        "docs_target": "attachment",
        "pipeline_status": "waiting_attachment_page",
        "upload_session_id": "HS-REFILL-WRONG-PAGE",
    })
    calls = []
    monkeypatch.setattr(
        pipeline_runner, "run_process",
        lambda *_args, **_kwargs: calls.append("process") or "refill-job",
    )
    monkeypatch.setattr(pipeline_runner, "spawn", lambda _job: None)
    saved = []

    async def fake_save(_current):
        saved.append(True)

    monkeypatch.setattr(flow.conv_store, "save", fake_save)

    r = await flow.handle_turn(conv, Intent("action", "refill"))

    assert conv["state"] == "attaching"
    assert "không ở trang **Kê khai thông tin**" in r.display_md
    assert calls == []
    assert saved == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("state", "expected_state"),
    [
        ("collecting_docs", "collecting_docs"),
        ("filling", "filling"),
        ("reviewing", "attaching"),
        ("attaching", "attaching"),
    ],
)
async def test_intent_dinh_kem_khi_con_o_ke_khai_nhac_ra_soat_va_chuyen_buoc(
    state, expected_state,
):
    conv = _conv()
    conv.update({
        "procedure_key": "ket-hon",
        "state": state,
        "docs_target": "declaration",
        "auto_attach_after_fill": True,
    })

    r = await flow.handle_turn(conv, Intent("action", "request_attach"))

    assert conv["state"] == expected_state
    assert "Kê khai thông tin" in r.display_md
    assert "rà soát lại form" in r.display_md
    assert "Thành phần hồ sơ" in r.display_md
    assert "tự đính kèm" in r.display_md


@pytest.mark.asyncio
async def test_unknown_khi_cho_chuyen_trang_khong_bao_planner_dang_chay():
    """LLM không hiểu câu gõ lỗi thì vẫn hướng dẫn đúng trang, không bắt chờ giả."""
    conv = _conv()
    conv.update({
        "procedure_key": "ket-hon",
        "state": "attaching",
        "docs_target": "declaration",
        "pipeline_status": "waiting_attachment_page",
        "attachment_plan_started": False,
    })

    r = await flow.handle_turn(conv, Intent("unknown"))

    assert "Kê khai thông tin" in r.display_md
    assert "Thành phần hồ sơ" in r.display_md
    assert "lập kế hoạch đính kèm" not in r.display_md
    assert conv["attachment_plan_started"] is False


@pytest.mark.asyncio
async def test_unknown_chi_bao_planner_khi_pipeline_thuc_su_running():
    conv = _conv()
    conv.update({
        "procedure_key": "ket-hon",
        "state": "attaching",
        "docs_target": "attachment",
        "pipeline_status": "running",
        "attachment_plan_started": True,
    })

    r = await flow.handle_turn(conv, Intent("unknown"))

    assert "lập kế hoạch đính kèm" in r.display_md


@pytest.mark.asyncio
async def test_request_attach_dung_live_page_context_khong_dung_target_ke_khai_cu(monkeypatch):
    """Công dân vừa sang bước 3 rồi nói Đính kèm: cùng request phải sửa target và chạy plan."""
    from app.channels.handfree.chat import pipeline_runner

    conv = _conv()
    conv.update({
        "procedure_key": "ket-hon",
        "state": "attaching",
        "docs_target": "declaration",
        "pipeline_status": "waiting_attachment_page",
        "attachment_plan_started": False,
        "upload_session_id": "HS-LIVE-PAGE",
    })
    spawned = []
    monkeypatch.setattr(
        pipeline_runner,
        "run_attach",
        lambda *_args, **_kwargs: "attach-job",
    )
    monkeypatch.setattr(pipeline_runner, "spawn", spawned.append)

    r = await flow.handle_turn(
        conv,
        Intent("action", "request_attach"),
        client_page_context={"wizardStep": 3, "attachmentTarget": True},
    )

    assert conv["docs_target"] == "attachment"
    assert conv["pipeline_status"] == "running"
    assert conv["attachment_plan_started"] is True
    assert spawned == ["attach-job"]
    assert "lập kế hoạch đính kèm" in r.display_md
    assert "Kê khai thông tin" not in r.display_md


@pytest.mark.asyncio
async def test_page_status_phuc_hoi_plan_khi_mat_ws_attach_ready():
    """Plan đã lưu trong Mongo phải phát lại được dù event attach_ready dùng một lần bị mất."""
    conv = _conv()
    conv.update({
        "procedure_key": "ket-hon",
        "state": "attaching",
        "docs_target": "attachment",
        "pipeline_status": "attach_ready",
        "attachment_plan_started": True,
        "attach_action_in_progress": False,
        "upload_session_id": "HS-MISSED-WS",
        "attach_plan": [{
            "fileIndex": 0,
            "documentName": "Căn cước công dân bên nam",
            "componentName": "Căn cước công dân bên nam",
        }],
    })

    r = await flow.handle_turn(
        conv,
        Intent("event", "page_status", {"wizardStep": 3, "attachmentTarget": True}),
    )

    assert r.actions and r.actions[0]["type"] == "attach_plan"
    assert r.actions[0]["session_id"] == "HS-MISSED-WS"
    assert conv["attach_action_in_progress"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("recovery_intent", "page_context"),
    [
        pytest.param(
            Intent("action", "request_attach"),
            {"wizardStep": 3, "attachmentTarget": True},
            id="nguoi-dung-yeu-cau",
        ),
        pytest.param(
            Intent("event", "page_status", {"wizardStep": 3, "attachmentTarget": True}),
            None,
            id="watcher-trang-dinh-kem",
        ),
    ],
)
async def test_phuc_hoi_action_da_mat_sau_khi_lease_het_han(recovery_intent, page_context):
    """Cả watcher và câu 'đính kèm đi' đều phục hồi action mất trước report."""
    conv = _conv()
    conv.update({
        "procedure_key": "ket-hon",
        "state": "attaching",
        "docs_target": "attachment",
        "pipeline_status": "attach_ready",
        "attachment_plan_started": True,
        "attach_action_in_progress": True,
        "client_capabilities": {"supportsAttachActionLease": True},
        "attach_action_dispatch_id": "dispatch-cu",
        "attach_action_lease_until": datetime.now(timezone.utc) - timedelta(seconds=1),
        "upload_session_id": "HS-STALE-ACTION",
        "attach_plan": [{
            "fileIndex": 0,
            "documentName": "Căn cước công dân",
            "componentName": "Căn cước công dân của hai bên",
        }],
    })

    r = await flow.handle_turn(
        conv,
        recovery_intent,
        client_page_context=page_context,
    )

    assert r.actions and r.actions[0]["type"] == "attach_plan"
    assert r.actions[0]["dispatch_id"] != "dispatch-cu"
    assert conv["attach_action_in_progress"] is True
    assert conv["attach_action_dispatch_id"] == r.actions[0]["dispatch_id"]
    assert conv["attach_action_lease_until"] > datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_heartbeat_gia_han_action_dang_dinh_kem_va_chan_phat_trung():
    """Engine còn heartbeat thì watcher/request_attach không được phát action thứ hai."""
    conv = _conv()
    conv.update({
        "procedure_key": "ket-hon",
        "state": "attaching",
        "docs_target": "attachment",
        "pipeline_status": "attach_ready",
        "attachment_plan_started": True,
        "attach_action_in_progress": True,
        "client_capabilities": {"supportsAttachActionLease": True},
        "attach_action_dispatch_id": "dispatch-dang-chay",
        "attach_action_lease_until": datetime.now(timezone.utc) + timedelta(seconds=1),
        "upload_session_id": "HS-ACTIVE-ACTION",
        "attach_plan": [{
            "fileIndex": 0,
            "documentName": "Căn cước công dân",
            "componentName": "Căn cước công dân của hai bên",
        }],
    })
    old_lease = conv["attach_action_lease_until"]

    heartbeat = await flow.handle_turn(
        conv,
        Intent("event", "attach_heartbeat", {"dispatch_id": "dispatch-dang-chay"}),
    )
    duplicate = await flow.handle_turn(
        conv,
        Intent("action", "request_attach"),
        client_page_context={"wizardStep": 3, "attachmentTarget": True},
    )

    assert not heartbeat.actions
    assert conv["attach_action_lease_until"] > old_lease
    assert not duplicate.actions
    assert conv["attach_action_dispatch_id"] == "dispatch-dang-chay"


@pytest.mark.asyncio
async def test_report_tre_khong_duoc_mo_khoa_action_moi():
    """Report của sidebar cũ đến muộn không được chốt/xóa lease vừa phát lại."""
    conv = _conv()
    lease_until = datetime.now(timezone.utc) + timedelta(seconds=30)
    conv.update({
        "procedure_key": "ket-hon",
        "state": "attaching",
        "attach_action_in_progress": True,
        "client_capabilities": {"supportsAttachActionLease": True},
        "attach_action_dispatch_id": "dispatch-moi",
        "attach_action_lease_until": lease_until,
        "attach_plan": [{"fileIndex": 0}],
    })

    stale = await flow.handle_turn(
        conv,
        Intent("action", "attach_report", {
            "dispatch_id": "dispatch-cu", "attached": 1, "errors": [],
        }),
    )

    assert stale.display_md == ""
    assert not stale.actions
    assert conv["state"] == "attaching"
    assert conv["attach_action_in_progress"] is True
    assert conv["attach_action_dispatch_id"] == "dispatch-moi"
    assert conv["attach_action_lease_until"] == lease_until


@pytest.mark.asyncio
async def test_extension_cu_van_nhan_action_khong_co_lease():
    """Không phát contract mới cho extension chưa công bố hỗ trợ lease."""
    conv = _conv()
    conv.update({
        "procedure_key": "ket-hon",
        "state": "attaching",
        "upload_session_id": "HS-LEGACY",
        "attach_plan": [{
            "fileIndex": 0,
            "documentName": "Căn cước công dân",
            "componentName": "Căn cước công dân của hai bên",
        }],
    })

    ready = await flow.handle_turn(conv, Intent("event", "attach_ready"))

    assert ready.actions and ready.actions[0]["type"] == "attach_plan"
    assert "dispatch_id" not in ready.actions[0]
    assert conv["attach_action_in_progress"] is True
    assert conv["attach_action_dispatch_id"] == ""
    assert conv["attach_action_lease_until"] is None


@pytest.mark.asyncio
async def test_page_status_dung_bang_ho_so_khi_stepper_khong_doc_duoc():
    """Bảng hồ sơ thật phải phục hồi attach dù React tạm trả wizardStep=0."""
    conv = _conv()
    conv.update({
        "procedure_key": "ket-hon",
        "state": "attaching",
        "docs_target": "declaration",
        "pipeline_status": "attach_ready",
        "attachment_plan_started": True,
        "attach_action_in_progress": False,
        "upload_session_id": "HS-TABLE-EVIDENCE",
        "attachment_context": {
            "hasAttachmentTableHeader": True,
            "hasFileControl": True,
            "components": [{
                "index": 2,
                "componentName": "Căn cước công dân của hai bên",
            }],
        },
        "attach_plan": [{
            "fileIndex": 0,
            "documentName": "Căn cước công dân",
            "componentName": "Căn cước công dân của hai bên",
        }],
    })

    r = await flow.handle_turn(
        conv,
        Intent("event", "page_status", {
            "wizardStep": 0,
            "attachmentTarget": True,
        }),
        client_page_context={
            "wizardStep": 0,
            "attachmentTarget": True,
            "attachmentComponentCount": 1,
        },
    )

    assert conv["docs_target"] == "attachment"
    assert r.actions and r.actions[0]["type"] == "attach_plan"
    assert r.actions[0]["session_id"] == "HS-TABLE-EVIDENCE"
    assert conv["attach_action_in_progress"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("wizard_step", "extra_context", "expected_target", "expected_label"),
    [
        (
            1,
            '"ownerContext":{"fullName":"NGUYỄN VĂN A","identityNumber":"012345678901"}',
            "owner",
            "✅ Đã đưa đủ giấy tờ, điền chủ hồ sơ đi",
        ),
        (2, '"formKind":"legacy"', "declaration", "✅ Đã đưa đủ giấy tờ, điền tờ khai đi"),
        (3, '"attachmentTarget":true', "attachment", "✅ Đã đưa đủ giấy tờ, đính kèm đi"),
    ],
)
async def test_vao_thang_tung_buoc_hien_dung_nut_chot_giay_to(
    wizard_step, extra_context, expected_target, expected_label,
):
    conv = _conv()
    await _turn(conv, "kết hôn")
    await _turn(conv, "__action:goto_login")
    await _turn(
        conv,
        f'__event:page_status:{{"wizardStep":{wizard_step},"loggedIn":true,{extra_context}}}',
    )
    assert conv["state"] == "consent"
    assert conv["docs_target"] == expected_target

    await _accept_consent(conv)
    r = await _turn(conv, "scan tại quầy")

    docs_chip = next(chip for chip in r.chips if chip["send"] == "__action:docs_done")
    assert docs_chip["label"] == expected_label


@pytest.mark.asyncio
async def test_chot_giay_to_khong_doan_owner_khi_context_moi_khong_nhan_dien_duoc(monkeypatch):
    from app.channels.handfree.chat import pipeline_runner

    conv = _conv()
    conv.update({
        "procedure_key": "ket-hon",
        "state": "collecting_docs",
        "upload_session_id": "HS-UNKNOWN",
        "docs_target": "owner",
        "owner_phase": True,
        "client_capabilities": {"supportsPageBoundDocsComplete": True},
    })
    monkeypatch.setattr(
        pipeline_runner, "spawn",
        lambda _job: pytest.fail("Không được chạy pipeline khi chưa nhận diện được trang"),
    )

    r = await _turn(
        conv,
        '__event:docs_complete:{"pageContextCaptured":false,"wizardStep":0}',
    )

    assert conv["state"] == "collecting_docs"
    assert conv["docs_target"] == ""
    assert conv["owner_phase"] is False
    assert conv["pipeline_status"] == "waiting_page_target"
    assert "chưa xác định" in r.display_md.lower()


@pytest.mark.asyncio
async def test_doi_buoc_khi_dang_tai_giay_to_cap_nhat_nhan_nut_khong_them_bubble():
    conv = _conv()
    conv.update({
        "procedure_key": "ket-hon",
        "state": "collecting_docs",
        "docs_target": "owner",
        "owner_phase": True,
    })

    r = await _turn(conv, '__event:page_status:{"wizardStep":2,"formKind":"legacy"}')

    assert conv["docs_target"] == "declaration"
    assert conv["owner_phase"] is False
    assert r.display_md == "" and r.tts_text == ""
    assert r.actions == [{
        "type": "update_docs_done_chip",
        "label": "✅ Đã đưa đủ giấy tờ, điền tờ khai đi",
    }]


@pytest.mark.asyncio
async def test_chot_trung_cung_phien_va_target_chi_spawn_mot_pipeline(monkeypatch):
    from app.channels.handfree.chat import pipeline_runner

    conv = _conv()
    conv.update({
        "procedure_key": "ket-hon",
        "state": "collecting_docs",
        "upload_session_id": "HS-ONCE",
        "client_capabilities": {"supportsPageBoundDocsComplete": True},
    })
    calls = []
    monkeypatch.setattr(pipeline_runner, "run_process", lambda *_a: calls.append("process") or "process-job")
    monkeypatch.setattr(pipeline_runner, "spawn", lambda _job: None)
    payload = {"pageContextCaptured": True, "wizardStep": 2}

    first = await flow._docs_complete(conv, payload)  # noqa: SLF001 — kiểm khóa dispatch nội bộ
    second = await flow._docs_complete(conv, payload)  # noqa: SLF001

    assert first.display_md
    assert second.display_md == ""
    assert calls == ["process"]

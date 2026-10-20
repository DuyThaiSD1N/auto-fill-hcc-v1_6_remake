"""Bổ sung ô còn trống trên trang nộp một trang (tư pháp mới, form SurveyJS) — xác nhận tình trạng hôn nhân.

Điền xong là tự đính kèm → báo số ô ngay, mời bổ sung sau khi đính xong; hỏi xong thì bước kế tiếp là chọn hình
thức nhận kết quả (không có Xem trước / Xác nhận như tờ khai eForm)."""
from unittest.mock import AsyncMock

import pytest

from app.channels.handfree.chat import field_review, flow, pipeline_runner, tracing
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat import store
from app.channels.handfree.chat.intents import Intent

KEY = "xac-nhan-tinh-trang-hon-nhan"
CAPS = {"supportsTuPhapMoi": True, "supportsTpmAutoFlow": True, "supportsPageBoundDocsComplete": True,
        "supportsAttachmentContext": True, "supportsRating": True,
        "supportsFieldReview": True, "supportsFieldReviewSurvey": True}
PAGE = {"formKind": "surveyjs", "wizardStep": 0, "attachmentTarget": False}
NO_ASK = ["citizenField27", "citizenField29", "citizenField78", "citizenField71", "citizenField72"]
REVIEW = {"filled": 20, "optional": 2, "required": 1}


@pytest.fixture
def spawned(monkeypatch):
    calls = []
    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: calls.append(coro))
    monkeypatch.setattr(pipeline_runner, "run_attach", lambda *a, **k: ("run_attach", a))
    monkeypatch.setattr(pipeline_runner, "run_process", lambda *a, **k: ("run_process", a))
    monkeypatch.setattr(tracing, "set_report", AsyncMock())
    return calls


def _conv(state: str, caps: dict = CAPS, **extra) -> dict:
    conv = store.new_conversation()
    conv.update({
        "procedure_key": KEY, "state": state, "client_capabilities": dict(caps),
        "auth_user": {"id": "u1", "tinh": "Tỉnh A", "xa": "Xã B"},
        "upload_session_id": "s1", "docs_target": "declaration",
    })
    conv.update(extra)
    return conv


async def _turn(conv, kind, value, payload=None, page=PAGE):
    return await flow.handle_turn(conv, Intent(kind, value, payload or {}), page)


def _sends(reply) -> list[str]:
    return [chip["send"] for chip in reply.chips]


def _trails(reply) -> list[str]:
    return [a["md"] for a in reply.actions if a.get("type") == "trail_message"]


def _field(name="citizenField40__1761724625529", label="Số giấy chứng nhận kết hôn", kind="text", **extra):
    return {"key": name, "name": name.split("__")[0], "role": "", "kind": kind, "label": label, "group": "",
            "section": "Thông tin về người được cấp Giấy xác nhận tình trạng hôn nhân", "required": True,
            "options": [], "value": "", **extra}


def test_cau_hinh_tthn_khong_hoi_kinh_gui_va_ngay_lap_to_khai():
    assert field_review.registry.get(KEY) == {"required": (), "noSection": (), "noAsk": tuple(NO_ASK),
                                              "zeroIsEmpty": ("citizenField70",), "textDates": (), "lookup": ()}


def test_lenh_dien_kem_danh_sach_o_khong_hoi_khi_extension_doc_duoc_surveyjs():
    conv = _conv("filling", fields=[{"name": "a", "value": "1"}])
    action = flow._fill_fields_reply(conv).actions[0]
    assert action["fieldReview"] == {"required": [], "noAsk": NO_ASK, "zeroIsEmpty": ["citizenField70"]}


def test_extension_chi_co_co_eform_thi_trang_mot_trang_giu_nguyen():
    caps = {k: v for k, v in CAPS.items() if k != "supportsFieldReviewSurvey"}
    conv = _conv("filling", caps, fields=[{"name": "a", "value": "1"}])
    assert "fieldReview" not in flow._fill_fields_reply(conv).actions[0]
    assert not field_review.active(conv, flow.get_procedure(KEY))


async def test_dien_xong_dang_lap_ke_hoach_thi_bao_so_o_chua_moi_bo_sung(spawned):
    conv = _conv("filling", pipeline_status="running", attachment_plan_started=True)
    reply = await _turn(conv, "action", "fill_report", {"filled": 20, "notFound": [], "review": REVIEW})
    assert any("Đính kèm xong em mời công dân bổ sung" in md for md in _trails(reply))
    assert "__action:field_review_start" not in _sends(reply)
    assert "__action:field_review_preview" not in _sends(reply)


async def test_ke_hoach_san_thi_bong_bong_so_o_dung_truoc_lenh_dinh(spawned):
    conv = _conv("filling", pipeline_status="attach_ready", attachment_plan_started=True,
                 attach_plan=[{"fileName": "a.pdf", "slotName": "Bản án"}])
    reply = await _turn(conv, "action", "fill_report", {"filled": 20, "notFound": [], "review": REVIEW})
    types = [a["type"] for a in reply.actions]
    assert types[0] == "trail_message" and "attach_plan" in types
    assert "__action:field_review_start" not in _sends(reply)


async def test_dinh_xong_moi_bo_sung_truoc_nut_di_tiep(spawned):
    conv = _conv("filling", pipeline_status="running", attachment_plan_started=True)
    await _turn(conv, "action", "fill_report", {"filled": 20, "notFound": [], "review": REVIEW})
    conv.update(attach_plan=[{"fileName": "a.pdf"}], attach_action_in_progress=True)
    reply = await _turn(conv, "action", "attach_report", {"attached": 1, "skipped": 0, "errors": []})
    assert _sends(reply) == ["__action:field_review_start", "__action:add_documents", "__action:refill",
                             "__action:tpm_attach", "__action:tpm_result_method", "__action:tpm_submit"]
    assert any("3 ô trống" in md for md in _trails(reply))


async def test_khong_con_o_trong_thi_dinh_xong_nhu_cu(spawned):
    conv = _conv("filling", pipeline_status="running", attachment_plan_started=True)
    await _turn(conv, "action", "fill_report",
                {"filled": 20, "notFound": [], "review": {"filled": 20, "optional": 0, "required": 0}})
    conv.update(attach_plan=[{"fileName": "a.pdf"}], attach_action_in_progress=True)
    reply = await _turn(conv, "action", "attach_report", {"attached": 1, "skipped": 0, "errors": []})
    assert "__action:field_review_start" not in _sends(reply) and not _trails(reply)


async def test_hoi_xong_thi_sang_chon_hinh_thuc_nhan_ket_qua(spawned):
    conv = _conv("filling", pipeline_status="running", attachment_plan_started=True)
    await _turn(conv, "action", "fill_report", {"filled": 20, "notFound": [], "review": REVIEW})
    conv.update(attach_plan=[{"fileName": "a.pdf"}], attach_action_in_progress=True)
    await _turn(conv, "action", "attach_report", {"attached": 1, "skipped": 0, "errors": []})

    reply = await _turn(conv, "action", "field_review_start")
    assert reply.actions[0]["type"] == "field_review_next" and reply.actions[0]["noAsk"] == NO_ASK
    assert reply.actions[0]["zeroIsEmpty"] == ["citizenField70"]

    reply = await _turn(conv, "event", "field_review_focus", {"field": _field(), "stats": REVIEW})
    assert "Người được cấp Giấy xác nhận tình trạng hôn nhân" in reply.display_md
    assert "Số giấy chứng nhận kết hôn" in reply.display_md

    # Trang đổi DOM (ô mới hiện ra) không phải rời bước tờ khai → vẫn đang hỏi.
    await _turn(conv, "event", "page_status", {"formKind": "surveyjs"})
    assert field_review.asking(conv)

    reply = await _turn(conv, "event", "field_review_focus",
                        {"field": None, "stats": {"filled": 23, "optional": 0, "required": 0}})
    assert reply.display_md.startswith(vi.FR_DONE_SINGLE_PAGE["md"].split("{")[0])
    assert "Xem trước" not in reply.display_md + reply.tts_text
    sends = _sends(reply)
    assert "__action:field_review_preview" not in sends
    assert sends[-2:] == ["__action:tpm_result_method", "__action:tpm_submit"]


async def test_dung_giua_chung_cung_khong_co_xem_truoc(spawned):
    conv = _conv("done", field_review={"chips": [], "stats": field_review._stats(REVIEW)})
    await _turn(conv, "action", "field_review_start")
    reply = await _turn(conv, "action", "field_review_stop")
    assert "Chọn hình thức nhận kết quả" in reply.display_md
    assert "__action:field_review_preview" not in _sends(reply)


async def test_cong_chan_nop_vi_thieu_o_thi_moi_bo_sung():
    conv = _conv("done", attach_done=True, result_method="counter")
    reply = await _turn(conv, "action", "guided_submit_report", {"ok": False, "missing": ["Số Điện thoại"]})
    assert _sends(reply) == ["__action:field_review_start", "__action:tpm_submit"]
    # Hỏi xong vẫn có nút đi tiếp dù lượt điền chưa lưu nút nào.
    assert "__action:tpm_result_method" in [c["send"] for c in conv["field_review"]["chips"]]


async def test_cong_chan_nop_ma_extension_cu_thi_chi_nut_nop():
    caps = {k: v for k, v in CAPS.items() if k != "supportsFieldReviewSurvey"}
    conv = _conv("done", caps, attach_done=True, result_method="counter")
    reply = await _turn(conv, "action", "guided_submit_report", {"ok": False, "missing": ["Số Điện thoại"]})
    assert _sends(reply) == ["__action:tpm_submit"]


async def test_cau_xong_roi_khong_bam_xem_truoc_tren_trang_mot_trang(spawned):
    conv = _conv("attaching", field_review={"chips": [], "stats": field_review._stats(REVIEW)})
    proc = flow.get_procedure(KEY)
    assert field_review._next_step(conv, proc, Intent("action", "confirm_review", {})) == ""


def test_router_nhan_co_bo_sung_o_surveyjs():
    """Khoá chống merge nuốt: thiếu dòng whitelist thì vòng bổ sung trên trang một trang tắt im lặng."""
    from app.channels.handfree.chat import router

    caps = router._clean_client_capabilities({"supportsFieldReview": True, "supportsFieldReviewSurvey": True})
    assert caps["supportsFieldReview"] is True and caps["supportsFieldReviewSurvey"] is True


async def test_lua_chon_dai_khong_liet_ke_khong_doc_khong_hien_nut(spawned):
    status = ["Hiện tại chưa đăng ký kết hôn với ai", "Hiện tại đang có vợ/chồng",
              "Đã đăng ký kết hôn hoặc đã có vợ/chồng nhưng đã ly hôn; hiện tại chưa đăng ký kết hôn với ai"]
    conv = _conv("done", field_review={"chips": [], "stats": field_review._stats(REVIEW)})
    await _turn(conv, "action", "field_review_start")
    reply = await _turn(conv, "event", "field_review_focus", {"field": _field(
        "citizenTinhtranghonnhan__1761724625529", "Tình trạng hôn nhân", "select", options=status), "stats": REVIEW})
    assert "Ô **Tình trạng hôn nhân**" in reply.display_md and "Công dân nói hoặc gõ giúp em ạ." in reply.display_md
    assert not any(o in reply.display_md + reply.tts_text for o in status)
    assert _sends(reply) == ["__action:field_review_skip", "__action:field_review_stop"]
    # Câu trả lời vẫn được khớp vào danh sách của ô.
    assert conv["field_review"]["current"]["options"] == status

    # Lựa chọn ngắn vẫn đọc hết trong câu hỏi và có nút chọn.
    reply = await _turn(conv, "action", "field_review_skip")
    reply = await _turn(conv, "event", "field_review_focus", {"field": _field(
        "citizenNDKLoaicutru__1761724625529", "Loại cư trú", "select",
        options=["Thường trú", "Tạm trú", "Nơi ở hiện tại"]), "stats": REVIEW})
    assert "**Thường trú** · **Tạm trú** · **Nơi ở hiện tại**" in reply.display_md
    assert "Thường trú hoặc Tạm trú hoặc Nơi ở hiện tại" in reply.tts_text
    assert [c["label"] for c in reply.chips[:3]] == ["Thường trú", "Tạm trú", "Nơi ở hiện tại"]


async def test_o_quoc_gia_chi_moi_noi_hoac_go_ten_nuoc(spawned):
    conv = _conv("done", field_review={"chips": [], "stats": field_review._stats(REVIEW)})
    await _turn(conv, "action", "field_review_start")
    reply = await _turn(conv, "event", "field_review_focus", {"field": _field(
        "citizenField32__1761724625529", "Quốc gia", "select", options=["Lào", "Việt Nam", "Pháp", "Anh", "Nhật Bản",
                                                                         "Hàn Quốc", "Đức"]), "stats": REVIEW})
    assert reply.display_md.endswith("\n\nCông dân nói hoặc gõ tên nước giúp em ạ.")
    assert reply.tts_text.endswith("Công dân nói hoặc gõ tên nước giúp em ạ.")
    assert "hay nước khác" not in reply.display_md + reply.tts_text
    assert "Nước khác thì" not in reply.display_md + reply.tts_text


def test_so_hieu_van_ban_giu_dau_gach_cheo_cong_dan_doc():
    from app.channels.handfree.chat.field_review import agent, prompt

    # Quy tắc ở prompt (LLM-first): "gạch", "gạch chéo", "xẹt", "trên" giữa hai phần số → "/".
    assert '"gạch chéo", "xẹt", "trên" → "/"' in prompt.SYSTEM
    # Hậu kiểm không được bóc mất dấu "/" của số hiệu văn bản (chỉ ô số định danh / giấy tờ tùy thân mới giữ chữ số).
    for label in ("Số giấy chứng nhận kết hôn", "Số Bản án/Quyết định ly hôn"):
        field = {"label": label, "kind": "text", "options": []}
        answer = agent._check({"action": "value", "value": "01/2024"}, field, "không một trên hai không hai tư")
        assert (answer.action, answer.value) == ("value", "01/2024"), label


# ── Đăng ký khai tử (form mới) ──

def test_cau_hinh_khai_tu():
    cfg = field_review.registry.get("khai-tu")
    assert cfg["noAsk"] == ("citizenField27", "citizenField29", "citizenField28", "citizenField31", "citizenField32")
    assert cfg["zeroIsEmpty"] == ("citizenSoluongbansaonguoiyeucaudenghi",)
    assert cfg["textDates"] == ("citizenNDK_NgaySinh", "citizenField56")
    assert cfg["lookup"] == ("citizenNDK_HoVaTen", "citizenNDK_SoDinhDanh", "citizenNDK_NgaySinh")
    proc = flow.get_procedure("khai-tu")
    rules = field_review._form_rules(proc)
    assert rules["textDates"] == list(cfg["textDates"]) and rules["lookup"] == list(cfg["lookup"])


def test_o_ngay_dang_chu_bo_goi_y_dinh_dang_va_nhan_thang_nam():
    from app.channels.handfree.chat.field_review import agent, prompt

    field = field_review._field({"key": "citizenField56__1", "name": "citizenField56", "kind": "date",
                                 "partialDate": True, "label": "Ngày, tháng, năm chết (dd/mm/yyyy)",
                                 "section": "Thông tin người được khai tử", "required": True})
    assert field["label"] == "Ngày, tháng, năm chết"
    assert field["partial_date"] and field["year_only"]
    for raw, want in (("05/03/1978", "05/03/1978"), ("3/1978", "03/1978"), ("1978", "1978"), ("13/1978", "")):
        answer = agent._check({"action": "value", "value": raw}, field, "")
        assert (answer.value if answer.action == "value" else "") == want, raw
    # Ô ngày thường (không phải dạng chữ) vẫn không nhận tháng-năm.
    plain = {**field, "partial_date": False, "year_only": False}
    assert agent._check({"action": "value", "value": "03/1978"}, plain, "").action == "unclear"
    assert "03/1978" in prompt.DATE_PARTIAL


# ── Cấp bản sao trích lục hộ tịch (form mới) ──

def test_cau_hinh_trich_luc_khong_hoi_kinh_gui_tai_va_ngay_lap_to_khai():
    assert field_review.registry.get("trich-luc-ks") == {
        "required": (), "noSection": (),
        "noAsk": ("citizenField27", "citizenField37", "citizenField50", "citizenField52", "citizenField53"),
        "zeroIsEmpty": (), "textDates": ("citizenNDK_NgaySinh",),
        "lookup": ("citizenNDK_HoVaTen", "citizenNDK_SoDinhDanh", "citizenNDK_NgaySinh")}


def test_lenh_dien_trich_luc_kem_quy_tac_o_cho_extension():
    conv = _conv("filling", procedure_key="trich-luc-ks", fields=[{"name": "a", "value": "1"}])
    rules = flow._fill_fields_reply(conv).actions[0]["fieldReview"]
    assert rules["noAsk"] == ["citizenField27", "citizenField37", "citizenField50", "citizenField52", "citizenField53"]
    assert rules["textDates"] == ["citizenNDK_NgaySinh"]
    assert rules["lookup"] == ["citizenNDK_HoVaTen", "citizenNDK_SoDinhDanh", "citizenNDK_NgaySinh"]
    assert "zeroIsEmpty" not in rules
    assert field_review.active(conv, flow.get_procedure("trich-luc-ks"))


# ── Đăng ký khai sinh / Thay đổi, cải chính hộ tịch (form mới) ──

def test_cau_hinh_khai_sinh_khong_hoi_ngay_sinh_bang_chu_va_cho_tra_cuu_me_cha():
    cfg = field_review.registry.get("khai-sinh-dang-ky-thuong")
    assert cfg["noAsk"] == ("citizenField57", "citizenField29", "citizenField50", "citizenField31", "citizenField32",
                            "citizenNgaythangnamsinhbangchu_NgdcKS")
    assert cfg["textDates"] == () and cfg["zeroIsEmpty"] == ()
    assert cfg["lookup"] == ("citizenNDK_HoVaTen", "citizenNDK_SoDinhDanh", "citizenNDK_NgaySinh",
                             "citizenNDK_HoVaTenCha", "citizenNDK_SoDinhDanhCha", "citizenNDK_NgaySinhCha")


def test_cau_hinh_cai_chinh_ngay_sinh_dang_chu_va_tra_cuu():
    cfg = field_review.registry.get("thay-doi-cai-chinh-ho-tich")
    assert cfg["noAsk"] == ("citizenField27", "citizenField29", "citizenField28", "citizenField31", "citizenField32")
    assert cfg["textDates"] == ("citizenNDK_NgaySinh",) and cfg["zeroIsEmpty"] == ()
    assert cfg["lookup"] == ("citizenNDKHoTen", "citizenNDKSodinhdanh", "citizenNDK_NgaySinh")


@pytest.mark.parametrize("key", ["khai-sinh-dang-ky-thuong", "thay-doi-cai-chinh-ho-tich"])
def test_lenh_dien_khai_sinh_cai_chinh_kem_quy_tac_o(key):
    conv = _conv("filling", procedure_key=key, fields=[{"name": "a", "value": "1"}])
    rules = flow._fill_fields_reply(conv).actions[0]["fieldReview"]
    cfg = field_review.registry.get(key)
    assert rules["noAsk"] == list(cfg["noAsk"]) and rules["lookup"] == list(cfg["lookup"])
    assert field_review.active(conv, flow.get_procedure(key))

"""Chế độ tiếng Mông (Hmong): toggle set_lang, song ngữ + tts_lang, route ASR/TTS theo lang."""
import pytest

from app.channels.handfree.chat import flow, intents
from app.channels.handfree.chat import script_mong as mong
from app.channels.handfree.chat import script_vi as vi
from app.config import settings


def _conv(**kw):
    base = {"_id": "t-hmong", "state": "greet", "history": []}
    base.update(kw)
    return base


async def test_set_lang_hmong_va_quay_ve_vi():
    conv = _conv()
    r = await flow.handle_turn(conv, intents.Intent("action", "set_lang", {"lang": "hmong"}))
    assert conv["lang"] == "hmong"
    assert r.tts_lang == "hmong"
    assert "Hmoob" in r.tts_text

    r2 = await flow.handle_turn(conv, intents.Intent("action", "set_lang", {"lang": "vi"}))
    assert conv["lang"] == "vi"
    assert r2.tts_lang == "vi"


async def test_set_lang_silent_khong_sinh_bubble():
    """FE tự khôi phục chế độ đã lưu trên máy sau khi phiên bị tạo mới → set_lang silent:
    đổi conv.lang nhưng reply RỖNG (không bubble, không đọc) — router sẽ không lưu last_reply."""
    conv = _conv()
    r = await flow.handle_turn(
        conv, intents.Intent("action", "set_lang", {"lang": "hmong", "silent": True}),
    )
    assert conv["lang"] == "hmong"
    assert not r.display_md and not r.tts_text and not r.chips and not r.cards
    # Lượt sau đã nói tiếng Mông bình thường.
    r2 = await flow.handle_turn(conv, intents.Intent("unknown", ""))
    assert r2.tts_lang == "hmong"


async def test_hmong_reply_song_ngu_va_tts_mong():
    """Bật tiếng Mông → md giữ bản Việt + dòng Mông in nghiêng; tts đọc bản Mông."""
    conv = _conv(lang="hmong")
    r = await flow.handle_turn(conv, intents.Intent("unknown", ""))  # greet
    # Song ngữ: còn nguyên câu Việt + thêm đoạn Mông in nghiêng.
    assert "Xin chào công dân" in r.display_md
    assert "*Nyob zoo pej xeem" in r.display_md
    # TTS đọc tiếng Mông + gắn nhãn giọng hmong cho FE.
    assert r.tts_text.startswith("Nyob zoo")
    assert r.tts_lang == "hmong"


async def test_vi_mac_dinh_khong_dinh_tieng_mong():
    conv = _conv()  # không có lang → vi
    r = await flow.handle_turn(conv, intents.Intent("unknown", ""))
    assert "Nyob zoo" not in r.display_md
    assert r.tts_lang == "vi"


async def test_key_thieu_ban_dich_fallback_tieng_viet():
    """Key không có trong script_mong → hiển thị + đọc tiếng Việt, tts_lang giữ vi."""
    conv = _conv(lang="hmong")
    # PROFILE_ASK_PHONE không dịch (tính năng đang ẩn) — _fmt phải trả nguyên bản Việt.
    assert not hasattr(mong, "PROFILE_ASK_PHONE")
    flow._TURN_LANG.set("hmong")
    flow._TURN_HMONG_TTS.set(False)
    md, tts = flow._fmt(vi.PROFILE_ASK_PHONE)
    assert md == vi.PROFILE_ASK_PHONE["md"]
    assert tts == vi.PROFILE_ASK_PHONE["tts"]
    assert flow._TURN_HMONG_TTS.get() is False


def test_moi_key_mong_khop_key_viet_va_du_md_tts():
    """Mọi TEMPLATE thoại trong script_mong phải trùng tên một mục script_vi (chống typo).
    PROCEDURE_HMONG / LOCATION_CARD_HMONG là dict cấu hình card, không phải template."""
    vi_keys = {
        name for name, value in vars(vi).items()
        if isinstance(value, dict) and "md" in value and "tts" in value
    }
    for name, value in vars(mong).items():
        if name.startswith("_") or not isinstance(value, dict) or "md" not in value:
            continue
        assert name in vi_keys, f"script_mong.{name} không có bản Việt tương ứng"
        assert value.get("md") and value.get("tts"), f"script_mong.{name} thiếu md/tts"


def test_procedure_hmong_khop_registry_key():
    """Tên thủ tục tiếng Mông phải map đúng key registry (chống typo/thủ tục bị đổi key)."""
    from app.channels.handfree.procedure_registry import public_list

    visible = {p["key"] for p in public_list() if not p.get("hiddenFromList")}
    for key in mong.PROCEDURE_HMONG:
        assert key in visible, f"PROCEDURE_HMONG có key lạ: {key}"
    missing = visible - set(mong.PROCEDURE_HMONG)
    assert not missing, f"Thủ tục hiện trên card chưa có tên tiếng Mông: {missing}"


async def test_service_list_va_location_card_gan_tieng_mong():
    conv = _conv(lang="hmong", location={"province": "Tỉnh Lai Châu", "ward": "Phường Đoàn Kết"})
    r = await flow.handle_turn(conv, intents.Intent("unknown", ""))  # greet → 2 card
    svc = next(c for c in r.cards if c.get("kind") == "service_list")
    ket_hon = next(i for i in svc["items"] if i["key"] == "ket-hon")
    assert ket_hon["titleHmong"].startswith("Cuv npe")
    loc = next(c for c in r.cards if c.get("kind") == "location_picker")
    assert loc["hmong"]["title"] == "Qhov chaw ua ntaub ntawv"
    assert loc["hmong"]["subject_options"]["self"]

    # Tiếng Việt: card sạch, không dính field hmong.
    conv_vi = _conv()
    r2 = await flow.handle_turn(conv_vi, intents.Intent("unknown", ""))
    svc2 = next(c for c in r2.cards if c.get("kind") == "service_list")
    assert all("titleHmong" not in i for i in svc2["items"])
    loc2 = next(c for c in r2.cards if c.get("kind") == "location_picker")
    assert "hmong" not in loc2


def test_chip_hmong_phu_het_nhan_literal_trong_flow():
    """Mọi nhãn chip literal trong flow.py phải có bản Mông (chống bỏ sót khi thêm chip mới)."""
    import pathlib
    import re

    src = (pathlib.Path(flow.__file__)).read_text(encoding="utf-8")
    labels = set(re.findall(r'"label": "([^"]+)"', src))
    missing = labels - set(mong.CHIP_HMONG)
    assert not missing, f"Chip chưa có bản Mông: {missing}"
    # Nhãn động của nút chốt giấy tờ cũng phải đủ.
    for label in flow._DOCS_TARGET_LABELS.values():
        assert label in mong.CHIP_HMONG, f"_DOCS_TARGET_LABELS chưa dịch: {label}"
    for label in flow._DOCUMENT_ADJUSTMENT_LABELS.values():  # noqa: SLF001
        assert label in mong.CHIP_HMONG, f"_DOCUMENT_ADJUSTMENT_LABELS chưa dịch: {label}"
    assert flow._docs_done_label("") in mong.CHIP_HMONG


async def test_chips_va_doc_options_gan_label_hmong():
    conv = _conv(lang="hmong")
    # Vào confirm_procedure → chip "Đúng rồi"/"Chọn thủ tục khác" phải có labelHmong.
    r = await flow.handle_turn(conv, intents.Intent("action", "pick_procedure", {"key": "ket-hon"}))
    assert r.chips, "confirm_procedure phải có chips"
    for chip in r.chips:
        assert chip.get("labelHmong"), f"chip thiếu labelHmong: {chip.get('label')}"

    # Card doc_options gắn khối hmong khi đang ở lượt tiếng Mông.
    flow._TURN_LANG.set("hmong")
    card = flow._doc_options_card()
    assert card["hmong"]["qr"]["title"].startswith("Thaij duab")
    flow._TURN_LANG.set("vi")
    assert "hmong" not in flow._doc_options_card()


def test_progress_va_upload_docs_hmong():
    conv = _conv(lang="hmong", state="guide_login")
    p = flow.build_progress(conv)
    assert p["labelHmong"] == "Nkag VNeID"
    assert "labelHmong" not in flow.build_progress(_conv(state="guide_login"))

    from app.upload_session import store as up_store

    sess = up_store.new_session("c1", "trich-luc-ks", [
        {"key": "cccd", "name": "CCCD của người yêu cầu", "icon": "🪪", "sides": 2},
        {"key": "slot_la", "name": "Slot chưa có bản dịch", "icon": "📄", "sides": 1},
    ])
    docs = {d["key"]: d for d in sess["required_docs"]}
    assert docs["cccd"]["nameHmong"] == "Daim npav CCCD"
    assert "nameHmong" not in docs["slot_la"]  # slot lạ giữ nguyên, không bịa
    # progress mang nameHmong theo (FE đọc từ đây).
    prog = up_store.progress(sess)
    assert next(d for d in prog["docs"] if d["key"] == "cccd")["nameHmong"] == "Daim npav CCCD"


def test_doc_slot_hmong_phu_het_slot_registry():
    """Mọi slot key requiredDocs trong registry phải có tên Mông (trừ fallback giay_to)."""
    import pathlib
    import re

    from app.procedures import registry

    src = pathlib.Path(registry.__file__).read_text(encoding="utf-8")
    keys = set(re.findall(r'\{"key": "([a-z_0-9]+)"', src))
    missing = keys - set(mong.DOC_SLOT_HMONG)
    assert not missing, f"Slot giấy tờ chưa có tên Mông: {missing}"


def test_consent_card_gan_tieng_mong():
    """Card consent song ngữ: khung + nội dung theo mode + tên giấy tờ theo slot key.
    Bản Việt giữ nguyên (bản pháp lý chính); legal_md KHÔNG dịch."""
    conv = _conv(lang="hmong", procedure_key="ket-hon")
    card = flow._consent_card(conv)
    assert card["hmong"]["title"].startswith("Tso cai")
    assert card["hmong"]["accept_label"] == "Pom zoo thiab sau kiag"
    assert len(card["hmong"]["checks"]) == 2
    # Giấy tờ có slot key quen (cccd_nam...) phải mang tên Mông.
    assert any(d.get("nameHmong") for d in card["documents"])
    # Bản Việt + toàn văn luật giữ nguyên.
    assert card["intro_md"] and card["legal_md"].startswith("*Theo Luật")

    # attach mode dùng bộ chữ đính kèm.
    conv2 = _conv(lang="hmong", procedure_key="chung-thuc-ban-sao")
    card2 = flow._consent_card(conv2)
    assert card2["hmong"]["accept_label"] == "Pom zoo thiab muab tso kiag"

    # Tiếng Việt: không dính field hmong.
    assert "hmong" not in flow._consent_card(_conv(procedure_key="ket-hon"))


async def test_voice_config_langs_theo_cau_hinh(monkeypatch):
    from app.channels.handfree.voice.router import voice_config

    monkeypatch.setattr(settings, "asr_grpc_uri_hmong", "")
    cfg = await voice_config()
    assert cfg["langs"] == ["vi"]

    monkeypatch.setattr(settings, "asr_grpc_uri_hmong", "103.253.20.28:9113")
    cfg = await voice_config()
    assert cfg["langs"] == ["vi", "hmong"]


def test_tts_voice_theo_lang(monkeypatch):
    from app.channels.handfree.voice.ws_tts import _config_frame, _voice_for

    monkeypatch.setattr(settings, "tts_voice", "phuongnhi-north")
    monkeypatch.setattr(settings, "tts_voice_hmong", "xi")
    assert _voice_for("vi") == "phuongnhi-north"
    assert _voice_for("hmong") == "xi"
    assert '"voiceId": "xi"' in _config_frame("hmong")
    assert '"voiceId": "phuongnhi-north"' in _config_frame("vi")


def test_first_greet_di_qua_boc_ngon_ngu():
    """Lượt đầu của conversation (router) phải chào ĐÚNG tiếng Mông khi conv.lang=hmong:
    trước đây gọi _handle_greet trần → bỏ qua _TURN_LANG → chào tiếng Việt."""
    conv = _conv(lang="hmong")
    r = flow.first_greet(conv)
    assert r.tts_lang == "hmong"
    assert r.tts_text.startswith("Nyob zoo")
    assert "*Nyob zoo pej xeem" in r.display_md
    svc = next(c for c in r.cards if c.get("kind") == "service_list")
    assert svc["items"][0].get("titleHmong")
    # Tiếng Việt vẫn như cũ.
    r2 = flow.first_greet(_conv())
    assert r2.tts_lang == "vi" and "Nyob zoo" not in r2.display_md


def test_chat_request_nhan_preferred_lang():
    from app.channels.handfree.chat.router import ChatRequest

    req = ChatRequest(message="", source="system", preferred_lang="hmong")
    assert req.preferred_lang == "hmong"
    assert ChatRequest(message="").preferred_lang is None


"""Xác nhận thông tin hộ tịch: vòng bổ sung ô eForm, kèm ô quan hệ (5) — không phải "Bản thân" thì tích "Khác" rồi
ghi đúng lời công dân vào ô ghi chữ cạnh đó (ô chỉ hiện sau khi tích, không có tên riêng)."""
from unittest.mock import AsyncMock

import pytest

from app.channels.handfree.chat import field_review, flow, pipeline_runner, store, tracing
from app.channels.handfree.chat.field_review import agent
from app.channels.handfree.chat.field_review import prompt as fr_prompt
from app.channels.handfree.chat.intents import Intent

KEY = "xac-nhan-thong-tin-ho-tich"
CAPS = {"supportsFieldReview": True, "supportsPageBoundDocsComplete": True, "supportsFieldReviewOtherText": True}
PAGE = {"formKind": "legacy", "wizardStep": 2}
STATS = {"filled": 20, "optional": 2, "required": 1}
QUAN_HE = {"key": "nycQuanHe", "name": "nycQuanHe", "role": "", "kind": "radio",
           "label": "(5) Quan hệ với người được cấp xác nhận thông tin hộ tịch:",
           "group": "", "section": "I. Thông tin người yêu cầu", "required": True, "options": ["Bản thân", "Khác"]}
QUAN_HE_FIELD = {**QUAN_HE, "where": "Thông tin người yêu cầu", "other": {"option": "Khác", "name": "nycQuanHeKhac"}}
NEXT = {"key": "hoTenNguoiDuocXN", "name": "hoTenNguoiDuocXN", "role": "", "kind": "text",
        "label": "(6) Họ, chữ đệm, tên:", "group": "", "section": "II. Thông tin về người được cấp xác nhận",
        "required": True, "options": []}


@pytest.fixture(autouse=True)
def _no_io(monkeypatch):
    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: None)
    monkeypatch.setattr(pipeline_runner, "run_attach", lambda *a, **k: None)
    monkeypatch.setattr(tracing, "set_report", AsyncMock())


def _conv(caps=CAPS) -> dict:
    conv = store.new_conversation()
    conv.update({"procedure_key": KEY, "state": "filling", "client_capabilities": dict(caps),
                 "upload_session_id": "s1", "docs_target": "declaration", "auto_attach_after_fill": True})
    return conv


async def _turn(conv, kind, value, payload=None):
    return await flow.handle_turn(conv, Intent(kind, value, payload or {}), PAGE)


async def _ask(conv, field):
    await _turn(conv, "action", "fill_report", {"filled": 20, "review": STATS})
    await _turn(conv, "action", "field_review_start")
    return await _turn(conv, "event", "field_review_focus", {"field": field, "stats": STATS})


def _lead(reply) -> str:
    return next((a["md"] for a in reply.actions if a.get("type") == "lead_message"), "")


# ── Bật vòng bổ sung ──

def test_lenh_dien_kem_o_bat_buoc_ca_muc_i_muc_ii_va_noi_dung():
    conv = _conv()
    extra = field_review.fill_action_extra(conv, flow.get_procedure(KEY))
    required = extra["required"]
    # Mục I cổng đổ sẵn từ tài khoản: vẫn nằm trong danh sách để đã đủ thì không hỏi, còn trống thì hỏi.
    assert {"HoVaTenC", "NgayCapDDC", "NoiCapDDC", "nycQuanHe"} <= set(required)
    assert {"hoTenNguoiDuocXN", "ngaySinhNguoiDuocXN", "duocXNGioiTinh", "danTocNguoiDuocXN",
            "quocTichNguoiDuocXN", "duocXNNoiCuTru_TrongNuoc", "noiDungXacNhan", "lyDoXacNhan"} <= set(required)


def test_luong_ban_2_tu_phap_bat_cho_thu_tuc():
    conv = _conv({**CAPS, "supportsFlowV2": True})
    assert field_review.flow_v2(conv, flow.get_procedure(KEY))


def test_extension_khong_co_co_bo_sung_o_thi_khong_bat():
    conv = _conv({"supportsRating": True})
    assert field_review.fill_action_extra(conv, flow.get_procedure(KEY)) is None


# ── Ô quan hệ: "Khác" kèm ô ghi chữ ──

def test_agent_khac_kem_chu_thi_tich_khac_va_mang_chu():
    assert agent._check({"action": "value", "option": 2, "other_text": "Con đẻ"}, QUAN_HE_FIELD) \
        == agent.Answer("value", "Khác", other="Con đẻ")
    # LLM chỉ trả phần chữ, không chọn dòng → vẫn là Khác kèm chữ.
    assert agent._check({"action": "value", "option": 0, "other_text": "Mẹ đẻ"}, QUAN_HE_FIELD) \
        == agent.Answer("value", "Khác", other="Mẹ đẻ")
    assert agent._check({"action": "value", "option": 1, "other_text": ""}, QUAN_HE_FIELD) \
        == agent.Answer("value", "Bản thân")
    # Chỉ nói "khác" mà không nói cụ thể → hỏi lại, không để trống ô đi kèm.
    assert agent._check({"action": "value", "option": 2, "other_text": ""}, QUAN_HE_FIELD).action == "unclear"
    assert agent._check({"action": "value", "option": 2, "other_text": "khác"}, QUAN_HE_FIELD).action == "unclear"


async def test_prompt_co_quy_tac_lua_chon_khac(monkeypatch):
    seen = {}

    async def fake_chat(messages, **kw):
        seen["system"] = messages[0]["content"]
        return '{"action": "value", "value": "", "option": 2, "other_text": "Con đẻ"}'

    monkeypatch.setattr(agent, "llm_chat", fake_chat)
    answer = await agent.interpret("con đẻ", QUAN_HE_FIELD)
    assert answer == agent.Answer("value", "Khác", other="Con đẻ")
    assert "<lua_chon_khac>" in seen["system"] and "Dòng [2]" in seen["system"]
    # Ô thường không mang quy tắc này.
    await agent.interpret("Kinh", {**QUAN_HE_FIELD, "other": None})
    assert "<lua_chon_khac>" not in seen["system"]
    assert "{other" not in fr_prompt.SYSTEM.format(
        label="", where="", kind="", options="", visited="", date_rule="", copy_rule="", other_rule="")


async def test_hoi_quan_he_khong_co_nut_khac_va_nhac_noi_cu_the():
    asked = await _ask(_conv(), QUAN_HE)
    labels = [c["label"] for c in asked.chips]
    assert "Bản thân" in labels and "Khác" not in labels
    assert "nói rõ luôn cụ thể" in asked.display_md and "nói rõ luôn cụ thể" in asked.tts_text


async def test_noi_quan_he_khac_thi_tich_khac_va_dien_o_di_kem(monkeypatch):
    conv = _conv()
    await _ask(conv, QUAN_HE)
    monkeypatch.setattr(agent, "interpret", AsyncMock(return_value=agent.Answer("value", "Khác", other="Con đẻ")))
    picked = await _turn(conv, "action", "field_review_answer", {"text": "con đẻ"})
    assert picked.actions[0]["apply"] == {
        "key": "nycQuanHe", "value": "Khác",
        "extra": [{"name": "nycQuanHeKhac", "comp": "raw", "value": "Con đẻ"}],
    }
    nxt = await _turn(conv, "event", "field_review_focus",
                      {"applied": {"key": "nycQuanHe", "ok": True}, "field": NEXT, "stats": STATS})
    assert "Khác: Con đẻ" in _lead(nxt)


async def test_ban_than_thi_chi_tich_khong_kem_o_di_kem(monkeypatch):
    conv = _conv()
    await _ask(conv, QUAN_HE)
    monkeypatch.setattr(agent, "interpret", AsyncMock(return_value=agent.Answer("value", "Bản thân")))
    picked = await _turn(conv, "action", "field_review_answer", {"text": "bản thân tôi"})
    assert picked.actions[0]["apply"] == {"key": "nycQuanHe", "value": "Bản thân"}


async def test_extension_chua_dien_duoc_o_di_kem_thi_hoi_nhu_o_chon_thuong():
    caps = {k: v for k, v in CAPS.items() if k != "supportsFieldReviewOtherText"}
    conv = _conv(caps)
    asked = await _ask(conv, QUAN_HE)
    assert [c["label"] for c in asked.chips][:2] == ["Bản thân", "Khác"]
    assert "nói rõ luôn cụ thể" not in asked.display_md
    assert "other" not in conv["field_review"]["current"]


def test_router_nhan_co_o_di_kem():
    from app.channels.handfree.chat.router import _clean_client_capabilities

    assert _clean_client_capabilities({"supportsFieldReviewOtherText": True})["supportsFieldReviewOtherText"] is True
    assert _clean_client_capabilities({})["supportsFieldReviewOtherText"] is False


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])

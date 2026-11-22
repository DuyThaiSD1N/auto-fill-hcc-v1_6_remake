"""Chế độ tiếng Mông: dịch câu tự do sang tiếng Việt trước khi hiểu câu (chat/hmong_translate.py)."""
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.channels.handfree.chat import hmong_translate, intents, store, tracing
from app.channels.handfree.chat.intents import Intent
from app.channels.handfree.chat.router import router as chat_router
from app.core.deps import require_auth

USER = {"id": "u1", "username": "hcc", "name": "HCC", "role": "commune", "tinh": "Tỉnh Lai Châu", "xa": "Phường Tân Phong"}
HMONG = "Kuv tuaj ua dua ntawv xeeb yug"
VI = "Tôi muốn làm Cấp bản sao Trích lục hộ tịch, bản sao Giấy khai sinh"


async def test_dich_tra_cau_tieng_viet_tu_json(monkeypatch):
    llm = AsyncMock(return_value='```json\n{"vi": "  Tôi muốn  làm kết hôn "}\n```')
    monkeypatch.setattr(hmong_translate, "llm_chat", llm)
    assert await hmong_translate.translate("kuv xav ua ntawv sib yuav", "Công dân cần làm gì ạ?") == "Tôi muốn làm kết hôn"
    user_msg = llm.await_args.args[0][1]["content"]
    assert "Công dân cần làm gì ạ?" in user_msg and "kuv xav ua ntawv sib yuav" in user_msg
    assert llm.await_args.kwargs["temperature"] == 0.0


async def test_dich_loi_hoac_rac_thi_rong(monkeypatch):
    monkeypatch.setattr(hmong_translate, "llm_chat", AsyncMock(side_effect=RuntimeError("down")))
    assert await hmong_translate.translate(HMONG) == ""
    monkeypatch.setattr(hmong_translate, "llm_chat", AsyncMock(return_value="không phải json"))
    assert await hmong_translate.translate(HMONG) == ""


async def test_dich_rong_thi_dung_cau_goc_va_luu_ca_hai(monkeypatch):
    monkeypatch.setattr(hmong_translate, "translate", AsyncMock(return_value=""))
    conv = store.new_conversation()
    assert await hmong_translate.understood_text(conv, HMONG) == HMONG
    assert conv["hmong_translation"] == {"src": HMONG, "vi": ""}


def test_prompt_uu_tien_khai_sinh_la_nhan_cua_llm():
    assert "ƯU TIÊN CAO NHẤT" in hmong_translate.SYSTEM and '"chi_noi_khai_sinh"' in hmong_translate.SYSTEM
    assert hmong_translate.SYSTEM.index("ƯU TIÊN CAO NHẤT") < hmong_translate.SYSTEM.index("QUY TẮC:")
    assert hmong_translate.BIRTH_COPY_REQUEST == VI


async def test_nhan_chi_noi_khai_sinh_thi_dung_dung_ten_thu_tuc_trich_luc(monkeypatch):
    monkeypatch.setattr(hmong_translate, "llm_chat",
                        AsyncMock(return_value='{"vi": "Tôi muốn làm lại giấy khai sinh", "chi_noi_khai_sinh": true}'))
    assert await hmong_translate.translate(HMONG, "Công dân chọn thủ tục bên dưới ạ.") == VI


async def test_nhan_sai_thi_giu_ban_dich(monkeypatch):
    monkeypatch.setattr(hmong_translate, "llm_chat",
                        AsyncMock(return_value='{"vi": "Tôi muốn đăng ký khai sinh cho con", "chi_noi_khai_sinh": false}'))
    assert await hmong_translate.translate("kuv xav cuv npe yug me nyuam") == "Tôi muốn đăng ký khai sinh cho con"


def test_cau_tro_ly_gan_nhat_lam_ngu_canh():
    conv = store.new_conversation()
    store.push_history(conv, "bot", "**Công dân** cần làm thủ tục gì ạ?", "bot")
    store.push_history(conv, "user", HMONG, "voice")
    assert hmong_translate._last_bot_text(conv) == "Công dân cần làm thủ tục gì ạ?"


def _client(monkeypatch, lang: str):
    conv = store.new_conversation()
    conv.update({"lang": lang, "auth_user": {"id": "u1"}, "location": {"province": "Tỉnh Lai Châu"}})
    monkeypatch.setattr(store, "get", AsyncMock(return_value=conv))
    monkeypatch.setattr(store, "save", AsyncMock())
    monkeypatch.setattr(tracing, "record_turn", AsyncMock(), raising=False)
    seen = {}

    async def resolve(message, state, c):
        seen["message"] = message
        return Intent("unknown")
    monkeypatch.setattr(intents, "resolve", resolve)
    app = FastAPI()
    app.include_router(chat_router)
    app.dependency_overrides[require_auth] = lambda: USER
    return TestClient(app), conv, seen


def test_che_do_mong_bo_hieu_cau_nhan_cau_da_dich(monkeypatch):
    monkeypatch.setattr(hmong_translate, "translate", AsyncMock(return_value=VI))
    client, conv, seen = _client(monkeypatch, "hmong")
    r = client.post("/api/v1/assistant/chat", json={"conversation_id": conv["_id"], "message": HMONG})
    assert r.status_code == 200
    assert seen["message"] == VI
    assert conv["hmong_translation"] == {"src": HMONG, "vi": VI}
    assert any(h.get("role") == "user" and h.get("text") == HMONG for h in conv["history"]), "lịch sử giữ câu gốc"


def test_che_do_viet_khong_dich(monkeypatch):
    translate = AsyncMock(return_value=VI)
    monkeypatch.setattr(hmong_translate, "translate", translate)
    client, conv, seen = _client(monkeypatch, "vi")
    client.post("/api/v1/assistant/chat", json={"conversation_id": conv["_id"], "message": "tôi muốn làm khai sinh"})
    translate.assert_not_awaited()
    assert seen["message"] == "tôi muốn làm khai sinh"


def test_lenh_may_khong_dich(monkeypatch):
    translate = AsyncMock(return_value=VI)
    monkeypatch.setattr(hmong_translate, "translate", translate)
    client, conv, _ = _client(monkeypatch, "hmong")
    client.post("/api/v1/assistant/chat", json={"conversation_id": conv["_id"], "message": "__action:docs_done"})
    translate.assert_not_awaited()


async def test_lop_dich_nhan_cap_nhan_viet_mong_cua_nut_dang_hien(monkeypatch):
    llm = AsyncMock(return_value='{"vi": "Lưu và nộp hồ sơ", "chi_noi_khai_sinh": false}')
    monkeypatch.setattr(hmong_translate, "llm_chat", llm)
    conv = store.new_conversation()
    conv["voice_options"] = {"state": "done", "items": [
        {"label": "💾 Lưu và nộp hồ sơ", "labelHmong": "Xa ntaub ntawv", "send": "__action:tpm_submit"},
        {"label": "🗂️ Điều chỉnh giấy tờ", "send": "__action:add_documents"}]}
    assert await hmong_translate.understood_text(conv, "xa ntaub ntawv") == "Lưu và nộp hồ sơ"
    user_msg = llm.await_args.args[0][1]["content"]
    assert '- "Lưu và nộp hồ sơ" = "Xa ntaub ntawv"' in user_msg
    assert "Điều chỉnh giấy tờ" not in user_msg, "nút không có nhãn Mông thì không đưa vào bảng đối chiếu"


async def test_nut_to_dam_dau_tien_la_nut_chinh_va_prompt_so_am_ca_cau(monkeypatch):
    llm = AsyncMock(return_value='{"vi": "Bổ sung các thông tin còn thiếu", "chi_noi_khai_sinh": false}')
    monkeypatch.setattr(hmong_translate, "llm_chat", llm)
    conv = store.new_conversation()
    conv["voice_options"] = {"state": "reviewing", "items": [
        {"label": "📝 Bổ sung các thông tin còn thiếu", "labelHmong": "Sau ntxiv cov uas tshuav",
         "send": "__action:field_review_start", "chip": {"solid": True}},
        {"label": "🔁 Điền lại", "labelHmong": "Sau dua", "send": "__action:refill", "chip": {"solid": True}}]}
    await hmong_translate.understood_text(conv, "sau tsiv rov ua ntsuam")
    user_msg = llm.await_args.args[0][1]["content"]
    assert '- "Bổ sung các thông tin còn thiếu" = "Sau ntxiv cov uas tshuav" (nút chính)' in user_msg
    assert '- "Điền lại" = "Sau dua"\n' in user_msg + "\n", "chỉ nút tô đậm đầu tiên là nút chính"
    assert "so ÂM cả câu" in hmong_translate.SYSTEM and "(nút chính)" in hmong_translate.SYSTEM


async def test_dang_cho_xac_nhan_thi_lop_dich_biet_viec_dang_hoi(monkeypatch):
    llm = AsyncMock(return_value='{"vi": "Có", "chi_noi_khai_sinh": false}')
    monkeypatch.setattr(hmong_translate, "llm_chat", llm)
    conv = store.new_conversation()
    conv["voice_submit_confirm"] = {"send": "__action:tpm_submit", "chip": {"label": "💾 Lưu và nộp hồ sơ"}}
    assert await hmong_translate.understood_text(conv, "xa ntaub ntawv") == "Có"
    user_msg = llm.await_args.args[0][1]["content"]
    assert 'Đang chờ công dân xác nhận việc: "Lưu và nộp hồ sơ" = "Xa ntaub ntawv"' in user_msg
    assert "ĐANG CHỜ XÁC NHẬN" in hmong_translate.SYSTEM

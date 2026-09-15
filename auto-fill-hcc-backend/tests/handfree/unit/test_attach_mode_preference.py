"""Cài đặt "Đính kèm chứng thực" (attachment_preferences.attachMode): máy quầy chọn sẵn
gộp/tách hồ sơ → bot KHÔNG hỏi giữa luồng; extension cũ không gửi → vẫn hỏi như bản chợ."""
import asyncio

from app.channels.handfree.chat import flow, pipeline_runner
from app.channels.handfree.chat.router import _clean_attachment_preferences


def test_router_whitelist_attach_mode():
    assert _clean_attachment_preferences({"attachMode": "merge"}) == {"attachMode": "merge"}
    assert _clean_attachment_preferences({"attachMode": "split", "splitDocuments": True}) == {
        "attachMode": "split", "splitDocuments": True,
    }
    # Giá trị lạ/kiểu sai bị loại — không cho client bơm mode bịa.
    assert _clean_attachment_preferences({"attachMode": "SPLIT"}) == {}
    assert _clean_attachment_preferences({"attachMode": True}) == {}
    assert _clean_attachment_preferences({"splitDocuments": "true"}) == {}


def _conv(**kw):
    base = {
        "_id": "t-attach-mode", "state": "collecting_docs", "history": [],
        "procedure_key": "chung-thuc-ban-sao", "upload_session_id": "",
        "docs_target": "attachment", "attach_mode": None,
    }
    base.update(kw)
    return base


def _capture_run_attach(monkeypatch):
    calls = {}

    async def fake_run_attach(conv_id, sid, key, options):
        calls["options"] = options

    monkeypatch.setattr(pipeline_runner, "run_attach", fake_run_attach)
    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: asyncio.ensure_future(coro))
    return calls


async def test_preset_split_bo_qua_cau_hoi_va_bao_mot_cau(monkeypatch):
    calls = _capture_run_attach(monkeypatch)
    conv = _conv(attachment_preferences={"attachMode": "split"})
    r = await flow._docs_complete(conv, {"attachmentTarget": True})
    assert conv["state"] == "attaching" and conv["attach_mode"] == "split"
    assert not r.chips, "đã cấu hình sẵn thì không được hỏi lại"
    assert "mỗi tài liệu một hồ sơ riêng" in r.display_md
    await asyncio.sleep(0)
    assert calls["options"]["splitMode"] is True


async def test_preset_merge_chay_thang_khong_ghi_chu(monkeypatch):
    calls = _capture_run_attach(monkeypatch)
    conv = _conv(attachment_preferences={"attachMode": "merge"})
    r = await flow._docs_complete(conv, {"attachmentTarget": True})
    assert conv["state"] == "attaching" and conv["attach_mode"] == "merge"
    assert not r.chips
    assert "mỗi tài liệu một hồ sơ riêng" not in r.display_md
    await asyncio.sleep(0)
    assert calls["options"]["splitMode"] is False


async def test_khong_co_preference_van_hoi_nhu_ban_cho(monkeypatch):
    _capture_run_attach(monkeypatch)
    conv = _conv()
    r = await flow._docs_complete(conv, {"attachmentTarget": True})
    assert conv["state"] == "choosing_attach_mode"
    assert [c["send"] for c in r.chips] == [
        '__action:attach_mode:{"value":"merge"}',
        '__action:attach_mode:{"value":"split"}',
    ]


async def test_preference_khong_de_len_lua_chon_da_chot(monkeypatch):
    """Hội thoại đã chốt merge (qua chip) rồi đổi cài đặt sang split → lượt bổ sung giữ merge."""
    calls = _capture_run_attach(monkeypatch)
    conv = _conv(attach_mode="merge", attachment_preferences={"attachMode": "split"})
    await flow._docs_complete(conv, {"attachmentTarget": True})
    assert conv["attach_mode"] == "merge"
    await asyncio.sleep(0)
    assert calls["options"]["splitMode"] is False

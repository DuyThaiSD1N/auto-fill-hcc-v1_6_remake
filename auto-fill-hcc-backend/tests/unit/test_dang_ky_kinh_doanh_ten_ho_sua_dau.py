import json

import pytest

from app.pipelines.dang_ky_kinh_doanh.process import ten_ho


def _llm(monkeypatch, edits):
    async def fake_chat(messages, temperature=None, max_tokens=None, enable_thinking=False, *, purpose=None):
        return json.dumps({"sua": edits}, ensure_ascii=False)

    monkeypatch.setattr(ten_ho.client, "chat", fake_chat)


async def test_sua_dau_chu_vo_nghia(monkeypatch):
    _llm(monkeypatch, [{"chu_goc": "QUẢN", "chu_goc_co_nghia": False, "chu_moi": "QUÁN"}])
    assert await ten_ho.fix_diacritics("QUẢN ABC") == "QUÁN ABC"


@pytest.mark.parametrize("edit", [
    {"chu_goc": "QUẢN", "chu_goc_co_nghia": True, "chu_moi": "QUÁN"},   # model tự nói chữ có nghĩa
    {"chu_goc": "QUẢN", "chu_moi": "QUÁN"},                              # thiếu khẳng định vô nghĩa
    {"chu_goc": "QUẢN", "chu_goc_co_nghia": False, "chu_moi": "QUẠT"},  # đổi cả chữ cái
    {"chu_goc": "XYZ", "chu_goc_co_nghia": False, "chu_moi": "XỲZ"},    # chữ không có trong tên
])
async def test_khong_nhan_de_xuat_vuot_pham_vi(monkeypatch, edit):
    _llm(monkeypatch, [edit])
    assert await ten_ho.fix_diacritics("QUẢN ABC") is None


async def test_llm_loi_giu_ten_ocr(monkeypatch):
    async def boom(*args, **kwargs):
        raise RuntimeError("down")

    monkeypatch.setattr(ten_ho.client, "chat", boom)
    assert await ten_ho.fix_diacritics("QUẢN ABC") is None


async def test_ten_khong_co_chu_khong_goi_llm(monkeypatch):
    async def never(*args, **kwargs):
        raise AssertionError("không được gọi LLM")

    monkeypatch.setattr(ten_ho.client, "chat", never)
    assert await ten_ho.fix_diacritics(" 123 ") is None

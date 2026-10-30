import asyncio
import json

from app.pipelines.chung_thuc_ban_sao.attach import planner


def _docs(n):
    return [{"fileIndex": i, "pageCount": 1, "pages": [{"pageNumber": 1, "ocrText": f"trang {i}"}]} for i in range(n)]


def _fake_chat(calls, fail_first=False):
    async def chat(messages, **kwargs):
        payload = json.loads(messages[1]["content"].split("\n")[1])
        indexes = [item["fileIndex"] for item in payload]
        calls.append(indexes)
        if fail_first and indexes[0] == 0:
            raise RuntimeError("LLM timeout")
        return json.dumps({"documents": [{"fileIndex": i, "documentName": f"Giấy {i}"} for i in indexes]})
    return chat


def test_ho_so_nho_van_goi_mot_lan(monkeypatch):
    calls = []
    monkeypatch.setattr(planner.client, "chat", _fake_chat(calls))
    out = asyncio.run(planner._classify_source_files_with_llm(_docs(8)))
    assert calls == [list(range(8))]
    assert [d["fileIndex"] for d in out] == list(range(8))


def test_ho_so_lon_chia_nhom_tep_lien_nhau_goi_song_song(monkeypatch):
    calls = []
    monkeypatch.setattr(planner.client, "chat", _fake_chat(calls))
    out = asyncio.run(planner._classify_source_files_with_llm(_docs(19)))
    assert sorted(calls) == [list(range(0, 8)), list(range(8, 16)), list(range(16, 19))]
    assert [d["fileIndex"] for d in out] == list(range(19))


def test_mot_nhom_loi_thi_giu_ket_qua_nhom_khac(monkeypatch):
    calls = []
    monkeypatch.setattr(planner.client, "chat", _fake_chat(calls, fail_first=True))
    out = asyncio.run(planner._classify_source_files_with_llm(_docs(10)))
    assert [d["fileIndex"] for d in out] == [8, 9]

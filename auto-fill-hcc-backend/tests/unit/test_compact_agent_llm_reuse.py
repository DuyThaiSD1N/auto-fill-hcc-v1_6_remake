from datetime import datetime, timedelta, timezone

import pytest

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_bien_phap_bao_dam_bac_ninh import process as bien_phap_bao_dam


class _Coll:
    def __init__(self):
        self.docs = {}

    async def find_one(self, query):
        return self.docs.get(query["_id"])

    async def replace_one(self, query, doc, upsert=False):
        self.docs[query["_id"]] = doc


class _Db:
    def __init__(self):
        self.llm_reuse = _Coll()


@pytest.fixture
def setup(monkeypatch):
    db = _Db()
    calls = []

    async def ocr(files, max_tokens=None):
        return [{"name": f["name"], "type": f.get("type"), "text": f"chu {f['name']}"} for f in files]

    async def chat(messages, **kwargs):
        calls.append(messages)
        return '{"fields": [{"name": "element_47783", "value": "X"}]}'

    from app.services import ocr as ocr_service
    monkeypatch.setattr(ocr_service, "ocr_per_file", ocr)
    monkeypatch.setattr(runner.client, "chat", chat)
    monkeypatch.setattr(runner, "get_db", lambda: db)
    return db, calls


FILES = {"": [{"name": "a.pdf", "type": "application/pdf"}]}


async def test_luot_uy_quyen_dung_lai_cau_tra_loi_llm_cua_luot_don(setup):
    _db, calls = setup
    await bien_phap_bao_dam.run(FILES, {})
    await bien_phap_bao_dam.run(FILES, {"purpose": "authorized_person"})
    assert len(calls) == 1


async def test_luot_don_luon_goi_llm_moi(setup):
    _db, calls = setup
    await bien_phap_bao_dam.run(FILES, {})
    await bien_phap_bao_dam.run(FILES, {})
    assert len(calls) == 2


async def test_doi_giay_hoac_qua_30_phut_thi_goi_lai(setup):
    db, calls = setup
    await bien_phap_bao_dam.run(FILES, {})
    await bien_phap_bao_dam.run({"": [{"name": "b.pdf", "type": "application/pdf"}]}, {"purpose": "authorized_person"})
    assert len(calls) == 2
    for doc in db.llm_reuse.docs.values():
        doc["at"] = datetime.now(timezone.utc) - timedelta(minutes=31)
    await bien_phap_bao_dam.run(FILES, {"purpose": "authorized_person"})
    assert len(calls) == 3


async def test_khong_doc_duoc_kho_van_goi_llm(setup, monkeypatch):
    _db, calls = setup

    def broken():
        raise RuntimeError("mongo chưa kết nối")

    monkeypatch.setattr(runner, "get_db", broken)
    result = await bien_phap_bao_dam.run(FILES, {"purpose": "authorized_person"})
    assert len(calls) == 1 and not [e for e in result.get("errors") or [] if e.startswith("agent")]

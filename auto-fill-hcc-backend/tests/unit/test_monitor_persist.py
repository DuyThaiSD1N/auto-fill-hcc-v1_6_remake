import asyncio

import pytest

from app.config import settings
from app.monitor import persist
from app.monitor import recorder as rec_mod


@pytest.fixture(autouse=True)
def _reset_context():
    token = rec_mod._current.set(None)
    yield
    rec_mod._current.reset(token)


class FakeColl:
    def __init__(self, fail_times=0):
        self.docs = {}
        self.bulk = []
        self.fail_times = fail_times

    async def replace_one(self, flt, doc, upsert=False):
        if self.fail_times:
            self.fail_times -= 1
            raise ValueError("khoá lạ")
        self.docs[flt["_id"]] = doc

    async def bulk_write(self, ops, ordered=True):
        self.bulk.extend(ops)


class FakeDB:
    def __init__(self, fail_times=0):
        self.trace_steps = FakeColl(fail_times)
        self.ocr_texts = FakeColl()


def _sample_recorder():
    rec = rec_mod.start("attach", "autofill", procedure="x")
    with rec_mod.span("ocr.remote", files=2):
        pass
    rec.ocr_files.append({"idx": 0, "name": "a.pdf", "sha256": "h1", "text": "chữ OCR", "cache": "miss"})
    rec.llm_calls.append({"n": 1, "purpose": "plan", "ms": 5, "raw": "r" * 50, "parsed": {"d": [1]}})
    rec.output("response", {"attachments": [{"fileIndex": 0}]})
    rec.mark_wait_end()
    return rec


def test_build_documents_tach_text_ocr_sang_ocr_texts():
    rec = _sample_recorder()
    doc, ops = persist.build_documents(rec, "req_1")
    assert doc["_id"] == "req_1:attach"
    assert doc["ocr"][0] == {"idx": 0, "name": "a.pdf", "sha256": "h1", "cache": "miss"}
    assert len(ops) == 1 and ops[0]._filter == {"_id": "h1"}
    assert doc["llm"][0]["parsed"] == {"d": [1]}
    assert doc["outputs"]["response"]["attachments"][0]["fileIndex"] == 0
    assert doc["spans"][0]["n"] == "ocr.remote"


def test_cat_output_qua_co_va_ghi_lai_cho_da_cat(monkeypatch):
    monkeypatch.setattr(settings, "trace_output_max_chars", 10)
    rec = _sample_recorder()
    doc, _ = persist.build_documents(rec, "req_1")
    call = doc["llm"][0]
    assert call["raw"] == "r" * 10
    assert call["n"] == 1 and call["purpose"] == "plan" and call["ms"] == 5
    assert call["parsed"] == {"d": [1]}  # nhỏ hơn trần → giữ nguyên cấu trúc
    assert {"path": "llm.1.raw", "len": 50} in doc["truncated"]


def test_fit_bo_output_lon_nhat_khi_vuot_tran(monkeypatch):
    monkeypatch.setattr(settings, "trace_doc_max_bytes", 1500)
    rec = _sample_recorder()
    rec.output("big", "x" * 5000)
    doc, _ = persist.build_documents(rec, "req_1")
    assert doc["outputs"]["big"] is None
    assert any(t.get("dropped") for t in doc["truncated"])


def test_che_do_summary_khong_luu_text(monkeypatch):
    monkeypatch.setattr(settings, "trace_detail", "summary")
    rec = _sample_recorder()
    doc, ops = persist.build_documents(rec, "req_1")
    assert ops == []
    assert "raw" not in doc["llm"][0] and "parsed" not in doc["llm"][0]


def test_timing_doi_dau_cham_thanh_gach_duoi():
    rec = _sample_recorder()
    t = persist.timing(rec)
    assert "ocr_remote" in t["s"] and "ocr.remote" not in t["s"]
    assert persist.timing(None) is None


async def test_save_ghi_ca_hai_collection(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(persist, "get_db", lambda: db)
    await persist.save(_sample_recorder(), "req_1")
    assert "req_1:attach" in db.trace_steps.docs
    assert len(db.ocr_texts.bulk) == 1


async def test_save_loi_khoa_la_thi_luu_dang_chuoi_json(monkeypatch):
    db = FakeDB(fail_times=1)
    monkeypatch.setattr(persist, "get_db", lambda: db)
    await persist.save(_sample_recorder(), "req_1")
    assert "_json" in db.trace_steps.docs["req_1:attach"]["outputs"]


async def test_save_loi_db_khong_nem_ra_ngoai(monkeypatch):
    def boom():
        raise RuntimeError("mongo chết")

    monkeypatch.setattr(persist, "get_db", boom)
    await persist.save(_sample_recorder(), "req_1")  # không được raise


async def test_qua_tai_thi_bo_chi_tiet_khong_xep_hang(monkeypatch):
    monkeypatch.setattr(settings, "trace_persist_max_pending", 0)
    before = persist.dropped
    persist.schedule(_sample_recorder(), "req_1")
    assert persist.dropped == before + 1


async def test_schedule_chay_nen(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(persist, "get_db", lambda: db)
    persist.schedule(_sample_recorder(), "req_2")
    await asyncio.gather(*list(persist._tasks))
    assert "req_2:attach" in db.trace_steps.docs

import pytest

from app.upload_session import classify
from app.upload_session.classify import route_to_slot
from app.upload_session.store import has_optional_slots, progress


DOCS = [{
    "key": "khac",
    "name": "Giấy tờ cần chứng thực bản sao",
    "icon": "📄",
    "sides": 1,
    "repeatable": True,
}]


def test_repeatable_other_slot_accepts_unlimited_files():
    existing = [{"doc_key": "khac"} for _ in range(20)]
    key, side, note = route_to_slot(
        {"doc_type": None, "side": None, "gender": None}, DOCS, existing, None
    )

    assert (key, side) == ("khac", None)
    assert "Giấy tờ khác" in note


def test_repeatable_slot_requires_one_but_does_not_auto_close():
    sess = {
        "required_docs": DOCS,
        "files": [{"doc_key": "khac"}, {"doc_key": "khac"}, {"doc_key": "khac"}],
        "complete": False,
    }

    result = progress(sess)
    assert result["received"] == result["total"] == 1
    assert result["files_count"] == 3
    assert result["docs"][0]["receivedCount"] == 3
    assert has_optional_slots(sess) is True


@pytest.mark.asyncio
async def test_single_repeatable_type_bypasses_ocr(monkeypatch):
    async def forbidden_ocr(*_args, **_kwargs):
        pytest.fail("Một loại repeatable không được gọi OCR")

    monkeypatch.setattr(classify.ocr, "ocr_per_file", forbidden_ocr)
    files = [
        {"name": "a.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AA=="},
        {"name": "b.jpg", "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,AA=="},
    ]

    result = await classify.classify_files(files, DOCS, [], hint_doc_key=None)

    assert [item["doc_key"] for item in result] == ["khac", "khac"]
    assert all(item["note"] == "một loại giấy tờ duy nhất" for item in result)
    assert all(item["ocr_ok"] is False for item in result)


@pytest.mark.asyncio
async def test_copy_certification_old_session_also_bypasses_ocr(monkeypatch):
    """Phiên cũ thiếu repeatable vẫn không được làm tệp thứ hai rơi vào unknown."""
    async def forbidden_ocr(*_args, **_kwargs):
        pytest.fail("Chứng thực bản sao không được OCR ở bước upload")

    monkeypatch.setattr(classify.ocr, "ocr_per_file", forbidden_ocr)
    old_docs = [{"key": "khac", "name": "Giấy tờ cần chứng thực bản sao", "sides": 1}]
    files = [
        {"name": "a.jpg", "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,AA=="},
        {"name": "b.jpg", "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,AA=="},
    ]

    result = await classify.classify_files(
        files, old_docs, [{"doc_key": "khac"}], None,
        procedure_key="chung-thuc-ban-sao",
    )

    assert [item["doc_key"] for item in result] == ["khac", "khac"]

    old_session = {
        "procedure_key": "chung-thuc-ban-sao",
        "required_docs": old_docs,
        "files": [{"doc_key": "khac"}, {"doc_key": "khac"}],
        "complete": False,
    }
    old_progress = progress(old_session)
    assert old_progress["docs"][0]["repeatable"] is True
    assert old_progress["docs"][0]["receivedCount"] == 2
    assert has_optional_slots(old_session) is True

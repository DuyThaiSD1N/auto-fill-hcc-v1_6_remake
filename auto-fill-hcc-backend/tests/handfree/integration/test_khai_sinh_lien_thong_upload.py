from app.channels.handfree.chat.flow import _doc_list
from app.channels.handfree.procedure_registry import get_procedure
from app.upload_session.classify import classify_text, route_to_slot
from app.upload_session.store import has_optional_slots, progress


PROCEDURE = "khai-sinh-dang-ky"


def _docs() -> list[dict]:
    return get_procedure(PROCEDURE)["requiredDocs"]


def test_khai_sinh_upload_slots_are_repeatable_and_include_other() -> None:
    proc = get_procedure(PROCEDURE)
    docs = proc["requiredDocs"]

    assert [doc["key"] for doc in docs] == [
        "cccd_cha",
        "cccd_me",
        "chung_sinh",
        "ket_hon_cha_me",
        "khac",
    ]
    assert all(doc["sides"] == 1 for doc in docs)
    assert all(doc["repeatable"] is True for doc in docs)
    assert proc["hideRepeatableHint"] is True
    assert docs[0]["name"] == "Căn cước công dân cha"
    assert docs[1]["name"] == "Căn cước công dân mẹ"
    assert docs[3]["optional"] is True
    assert docs[4]["optional"] is True


def test_khai_sinh_progress_keeps_actual_file_count_for_every_slot() -> None:
    session = {
        "procedure": PROCEDURE,
        "required_docs": _docs(),
        "files": [
            *({"doc_key": "cccd_cha"} for _ in range(3)),
            *({"doc_key": "cccd_me"} for _ in range(2)),
            *({"doc_key": "chung_sinh"} for _ in range(2)),
            *({"doc_key": "ket_hon_cha_me"} for _ in range(4)),
            *({"doc_key": "khac"} for _ in range(5)),
        ],
    }

    result = progress(session)
    counts = {doc["key"]: doc["receivedCount"] for doc in result["docs"]}

    assert counts == {
        "cccd_cha": 3,
        "cccd_me": 2,
        "chung_sinh": 2,
        "ket_hon_cha_me": 4,
        "khac": 5,
    }
    assert all(doc["repeatable"] is True for doc in result["docs"])
    assert result["total"] == 3
    assert result["received"] == 3
    assert has_optional_slots(session) is True


def test_khai_sinh_routes_known_and_unrelated_documents() -> None:
    docs = _docs()
    existing = [{"doc_key": "cccd_cha", "side": "front"}]

    assert route_to_slot(classify_text("CĂN CƯỚC CÔNG DÂN Giới tính Nam"), docs, existing, None)[0] == "cccd_cha"
    assert route_to_slot(classify_text("CĂN CƯỚC CÔNG DÂN Giới tính Nữ"), docs, existing, None)[0] == "cccd_me"
    assert route_to_slot(classify_text("GIẤY CHỨNG SINH"), docs, existing, None)[0] == "chung_sinh"
    assert route_to_slot(classify_text("GIẤY CHỨNG NHẬN KẾT HÔN"), docs, existing, None)[0] == "ket_hon_cha_me"
    assert route_to_slot(classify_text("Biên bản kiểm tra phòng cháy chữa cháy"), docs, existing, None)[0] == "khac"


def test_khai_sinh_routes_ambiguous_cccd_safely() -> None:
    docs = _docs()
    back = classify_text("CĂN CƯỚC CÔNG DÂN Đặc điểm nhận dạng Cục Cảnh sát")

    assert back["doc_type"] == "cccd"
    assert back["side"] == "back"
    assert route_to_slot(back, docs, [], "cccd_me")[0] == "cccd_me"
    assert route_to_slot(back, docs, [{"doc_key": "cccd_cha", "side": "front"}], None)[0] == "cccd_cha"
    assert route_to_slot(back, docs, [], None)[0] == "khac"


def test_khai_sinh_doc_list_does_not_announce_limits_or_sides() -> None:
    markdown, speech = _doc_list(get_procedure(PROCEDURE))

    assert "Các giấy tờ khác liên quan" in markdown
    assert "Căn cước công dân cha" in markdown
    assert "Căn cước công dân mẹ" in speech
    assert "CCCD/VNeID" not in markdown
    assert "CCCD/VNeID" not in speech
    assert "không giới hạn" not in markdown
    assert "không giới hạn" not in speech
    assert "2 mặt" not in markdown
    assert "hai mặt" not in speech

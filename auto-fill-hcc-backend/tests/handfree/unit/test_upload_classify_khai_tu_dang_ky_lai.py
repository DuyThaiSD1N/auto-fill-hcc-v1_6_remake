import json

import pytest

from app.channels.handfree.procedure_registry import get_procedure
from app.upload_session import classifier_registry, classify, llm_classifier
from app.upload_session.store import progress


PROCEDURE = "khai-tu-dang-ky-lai"


def _file(name: str) -> dict:
    return {
        "name": name,
        "type": "image/jpeg",
        "dataUrl": "data:image/jpeg;base64,AA==",
    }


def test_registry_uses_four_repeatable_file_groups_and_auto_discovers_classifier():
    proc = get_procedure(PROCEDURE)
    docs = proc["requiredDocs"]
    by_key = {item["key"]: item for item in docs}

    assert [item["key"] for item in docs] == ["cccd", "to_khai", "bao_tu", "khac"]
    assert [item["name"] for item in docs] == [
        "Căn cước công dân hoặc giấy tờ tùy thân",
        "Tờ khai đăng ký lại khai tử",
        "Giấy chứng tử, trích lục khai tử hoặc giấy tờ chứng minh sự kiện chết",
        "Giấy tờ liên quan khác",
    ]
    assert proc["hideRepeatableHint"] is True
    assert all(item["sides"] == 1 and item.get("repeatable") for item in docs)
    assert not by_key["cccd"].get("optional")
    assert not by_key["bao_tu"].get("optional")
    assert by_key["to_khai"].get("optional")
    assert by_key["khac"].get("optional")
    assert classifier_registry.get_upload_classifier(PROCEDURE) is not None

    files = [
        *({"doc_key": "cccd"} for _ in range(3)),
        *({"doc_key": "to_khai"} for _ in range(2)),
        *({"doc_key": "bao_tu"} for _ in range(4)),
        *({"doc_key": "khac"} for _ in range(5)),
    ]
    result = progress({
        "procedure_key": PROCEDURE,
        "required_docs": docs,
        "files": files,
        "complete": False,
    })
    counts = {item["key"]: item["receivedCount"] for item in result["docs"]}

    assert result["received"] == result["total"] == 2
    assert result["files_count"] == 14
    assert counts == {"cccd": 3, "to_khai": 2, "bao_tu": 4, "khac": 5}


@pytest.mark.asyncio
async def test_uses_one_tiengnoi_batch_and_one_llm_prompt_per_file(monkeypatch):
    files = [
        _file("cccd.jpg"), _file("ho-chieu.jpg"), _file("to-khai.jpg"),
        _file("trich-luc-khai-tu.jpg"), _file("uy-quyen.jpg"),
    ]
    texts = ["OCR_CCCD", "OCR_HO_CHIEU", "OCR_TO_KHAI", "OCR_KHAI_TU", "OCR_UY_QUYEN"]
    ocr_calls: list[list[str]] = []
    prompts: list[dict] = []

    async def fake_tiengnoi(batch, max_tokens=None):
        ocr_calls.append([item["name"] for item in batch])
        return [{"name": item["name"], "text": text} for item, text in zip(batch, texts)]

    async def fake_chat(messages, **_kwargs):
        payload = json.loads(messages[1]["content"])
        prompts.append(payload)
        mapping = {
            "OCR_CCCD": "cccd",
            "OCR_HO_CHIEU": "cccd",
            "OCR_TO_KHAI": "to_khai",
            "OCR_KHAI_TU": "bao_tu",
            "OCR_UY_QUYEN": "khac",
        }
        return json.dumps({"doc_key": mapping[payload["ocrText"]]})

    monkeypatch.setattr(llm_classifier.ocr.ocr_tiengnoi, "ocr_per_file", fake_tiengnoi)
    monkeypatch.setattr(llm_classifier.client, "chat", fake_chat)

    result = await classify.classify_files(
        files,
        get_procedure(PROCEDURE)["requiredDocs"],
        [],
        hint_doc_key=None,
        procedure_key=PROCEDURE,
    )

    assert ocr_calls == [[item["name"] for item in files]]
    assert len(prompts) == len(files)
    assert all(set(item) == {"ocrText"} for item in prompts)
    assert all(sum(text in item["ocrText"] for text in texts) == 1 for item in prompts)
    assert [item["doc_key"] for item in result] == [
        "cccd", "cccd", "to_khai", "bao_tu", "khac",
    ]
    assert all(item["side"] is None and item["ocr_ok"] for item in result)


@pytest.mark.asyncio
async def test_llm_failure_falls_back_without_mistaking_mentions_for_identity(monkeypatch):
    files = [
        _file("to-khai.jpg"), _file("chung-tu.jpg"), _file("uy-quyen.jpg"),
        _file("cccd.jpg"), _file("ho-chieu.jpg"), _file("khong-ro.jpg"),
    ]

    async def fake_tiengnoi(_batch, max_tokens=None):
        return [
            {"text": "TỜ KHAI ĐĂNG KÝ LẠI KHAI TỬ kèm Giấy chứng tử, CCCD số 012345678901"},
            {"text": "GIẤY CHỨNG TỬ Người yêu cầu dùng hộ chiếu số B1234567"},
            {"text": "VĂN BẢN ỦY QUYỀN Người ủy quyền dùng căn cước công dân số 012345678901"},
            {"text": "CĂN CƯỚC Số định danh cá nhân Họ và tên Ngày sinh Quốc tịch Giới tính"},
            {"text": "HỘ CHIẾU PASSPORT Họ và tên Ngày sinh Quốc tịch Nationality"},
            {"text": ""},
        ]

    async def fake_chat(_messages, **_kwargs):
        raise RuntimeError("LLM lỗi riêng tệp")

    monkeypatch.setattr(llm_classifier.ocr.ocr_tiengnoi, "ocr_per_file", fake_tiengnoi)
    monkeypatch.setattr(llm_classifier.client, "chat", fake_chat)

    result = await classify.classify_files(
        files,
        get_procedure(PROCEDURE)["requiredDocs"],
        [],
        hint_doc_key=None,
        procedure_key=PROCEDURE,
    )

    assert [item["doc_key"] for item in result] == [
        "to_khai", "bao_tu", "khac", "cccd", "cccd", "khac",
    ]
    assert all("LLM phân loại" not in item["note"] for item in result)


def test_auto_discovery_keeps_all_existing_llm_classifiers_registered():
    for procedure_key in (
        "ket-hon",
        "xac-nhan-tinh-trang-hon-nhan",
        "trich-luc-ks",
        "khai-tu",
        "khai-tu-dang-ky-lai",
    ):
        assert classifier_registry.get_upload_classifier(procedure_key) is not None

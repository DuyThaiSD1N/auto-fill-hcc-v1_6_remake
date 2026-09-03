import json

import pytest

from app.channels.handfree.procedure_registry import get_procedure
from app.upload_session import classify, llm_classifier
from app.upload_session.store import progress


PROCEDURE = "khai-tu"


def _file(name: str) -> dict:
    return {
        "name": name,
        "type": "image/jpeg",
        "dataUrl": "data:image/jpeg;base64,AA==",
    }


def test_khai_tu_repeatable_groups_accept_many_files():
    docs = get_procedure(PROCEDURE)["requiredDocs"]
    files = [
        *({"doc_key": "cccd"} for _ in range(3)),
        *({"doc_key": "bao_tu"} for _ in range(4)),
        *({"doc_key": "to_khai"} for _ in range(2)),
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
    assert counts == {"cccd": 3, "bao_tu": 4, "to_khai": 2, "khac": 5}


@pytest.mark.asyncio
async def test_khai_tu_uses_one_tiengnoi_batch_and_one_llm_prompt_per_file(monkeypatch):
    files = [
        _file("cccd.jpg"), _file("giay-bao-tu.jpg"), _file("giay-chung-tu.jpg"),
        _file("to-khai.jpg"), _file("uy-quyen.jpg"),
    ]
    texts = ["OCR_CCCD", "OCR_BAO_TU", "OCR_CHUNG_TU", "OCR_TO_KHAI", "OCR_UY_QUYEN"]
    ocr_calls: list[list[str]] = []
    prompts: list[dict] = []
    system_prompts: list[str] = []

    async def fake_tiengnoi(batch):
        ocr_calls.append([item["name"] for item in batch])
        return [{"name": item["name"], "text": text} for item, text in zip(batch, texts)]

    async def fake_chat(messages, **_kwargs):
        system_prompts.append(messages[0]["content"])
        payload = json.loads(messages[1]["content"])
        prompts.append(payload)
        mapping = {
            "OCR_CCCD": "cccd",
            "OCR_BAO_TU": "bao_tu",
            "OCR_CHUNG_TU": "bao_tu",
            "OCR_TO_KHAI": "to_khai",
            "OCR_UY_QUYEN": "khac",
        }
        return json.dumps({"doc_key": mapping[payload["ocrText"]]})

    monkeypatch.setattr(llm_classifier.ocr_tiengnoi, "ocr_per_file", fake_tiengnoi)
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
        "cccd", "bao_tu", "bao_tu", "to_khai", "khac",
    ]
    assert all(item["side"] is None and item["ocr_ok"] for item in result)
    assert all("không dùng tên file" in prompt.lower() for prompt in system_prompts)


@pytest.mark.asyncio
async def test_khai_tu_llm_failure_falls_back_without_mistaking_mentions_for_cccd(monkeypatch):
    files = [
        _file("to-khai.jpg"), _file("bao-tu.jpg"), _file("uy-quyen.jpg"),
        _file("cccd.jpg"), _file("khong-ro.jpg"),
    ]

    async def fake_tiengnoi(_batch):
        return [
            {"text": "TỜ KHAI ĐĂNG KÝ KHAI TỬ kèm Giấy báo tử, CCCD số 012345678901"},
            {"text": "GIẤY BÁO TỬ Người đi khai dùng căn cước công dân số 012345678901"},
            {"text": "VĂN BẢN ỦY QUYỀN Người ủy quyền dùng thẻ căn cước công dân số 012345678901"},
            {"text": "CĂN CƯỚC Số định danh cá nhân Họ và tên Ngày sinh Quốc tịch Giới tính"},
            {"text": ""},
        ]

    async def fake_chat(messages, **_kwargs):
        payload = json.loads(messages[1]["content"])
        if payload["ocrText"]:
            raise RuntimeError("LLM lỗi riêng tệp")
        return '{"doc_key":"unknown"}'

    monkeypatch.setattr(llm_classifier.ocr_tiengnoi, "ocr_per_file", fake_tiengnoi)
    monkeypatch.setattr(llm_classifier.client, "chat", fake_chat)

    result = await classify.classify_files(
        files,
        get_procedure(PROCEDURE)["requiredDocs"],
        [],
        hint_doc_key=None,
        procedure_key=PROCEDURE,
    )

    assert [item["doc_key"] for item in result] == [
        "to_khai", "bao_tu", "khac", "cccd", "khac",
    ]
    assert all("LLM phân loại" not in item["note"] for item in result)

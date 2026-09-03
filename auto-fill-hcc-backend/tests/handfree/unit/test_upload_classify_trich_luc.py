import json

import pytest

from app.channels.handfree.procedure_registry import get_procedure
from app.upload_session import classify, llm_classifier
from app.upload_session.store import progress


PROCEDURE = "trich-luc-ks"


def _file(name: str) -> dict:
    return {
        "name": name,
        "type": "image/jpeg",
        "dataUrl": "data:image/jpeg;base64,AA==",
    }


def test_trich_luc_registry_uses_four_repeatable_file_groups():
    proc = get_procedure(PROCEDURE)
    docs = proc["requiredDocs"]
    by_key = {item["key"]: item for item in docs}

    assert [item["key"] for item in docs] == ["cccd", "to_khai", "ho_tich", "khac"]
    assert proc["hideRepeatableHint"] is True
    assert by_key["cccd"]["name"] == "Căn cước công dân"
    assert by_key["ho_tich"]["name"] == (
        "Giấy tờ hộ tịch cũ như: giấy khai sinh hoặc giấy chứng nhận kết hôn "
        "hoặc trích lục khai tử (nếu có)"
    )
    assert by_key["khac"]["name"] == "Các giấy tờ liên quan khác"
    assert all(item["sides"] == 1 and item.get("repeatable") for item in docs)
    assert not by_key["cccd"].get("optional") and not by_key["to_khai"].get("optional")
    assert by_key["ho_tich"].get("optional") and by_key["khac"].get("optional")

    files = [
        *({"doc_key": "cccd"} for _ in range(3)),
        *({"doc_key": "to_khai"} for _ in range(2)),
        *({"doc_key": "ho_tich"} for _ in range(4)),
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
    assert counts == {"cccd": 3, "to_khai": 2, "ho_tich": 4, "khac": 5}


@pytest.mark.asyncio
async def test_trich_luc_uses_one_tiengnoi_batch_and_one_llm_prompt_per_file(monkeypatch):
    files = [
        _file("cccd.jpg"), _file("to-khai.jpg"), _file("khai-sinh.jpg"),
        _file("ket-hon.jpg"), _file("khai-tu.jpg"), _file("uy-quyen.jpg"),
    ]
    texts = [
        "OCR_CCCD", "OCR_TO_KHAI", "OCR_KHAI_SINH",
        "OCR_KET_HON", "OCR_KHAI_TU", "OCR_UY_QUYEN",
    ]
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
            "OCR_TO_KHAI": "to_khai",
            "OCR_KHAI_SINH": "ho_tich",
            "OCR_KET_HON": "ho_tich",
            "OCR_KHAI_TU": "ho_tich",
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
        "cccd", "to_khai", "ho_tich", "ho_tich", "ho_tich", "khac",
    ]
    assert all(item["side"] is None and item["ocr_ok"] for item in result)
    assert all("không dùng tên file" in prompt.lower() for prompt in system_prompts)


@pytest.mark.asyncio
async def test_trich_luc_llm_failure_falls_back_without_mistaking_mentions_for_cccd(monkeypatch):
    files = [
        _file("to-khai.jpg"), _file("khai-sinh.jpg"), _file("uy-quyen.jpg"),
        _file("cccd.jpg"), _file("khong-ro.jpg"),
    ]

    async def fake_tiengnoi(_batch):
        return [
            {"text": "TỜ KHAI CẤP BẢN SAO TRÍCH LỤC HỘ TỊCH CCCD số 012345678901"},
            {"text": "GIẤY KHAI SINH Giấy tờ tùy thân của cha là căn cước công dân"},
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
        "to_khai", "ho_tich", "khac", "cccd", "khac",
    ]
    assert all("LLM phân loại" not in item["note"] for item in result)

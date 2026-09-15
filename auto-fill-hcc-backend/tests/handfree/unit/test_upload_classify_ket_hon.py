import json

import pytest

from app.channels.handfree.procedure_registry import get_procedure
from app.upload_session import classify, llm_classifier


def _file(name: str) -> dict:
    return {
        "name": name,
        "type": "image/jpeg",
        "dataUrl": "data:image/jpeg;base64,AA==",
    }


@pytest.mark.asyncio
async def test_ket_hon_uses_shared_tiengnoi_ocr_but_one_llm_prompt_per_file(monkeypatch):
    files = [_file("nam.jpg"), _file("nu.jpg"), _file("to-khai.jpg"), _file("xac-nhan.jpg")]
    texts = ["OCR_DOC_NAM", "OCR_DOC_NU", "OCR_DOC_TO_KHAI", "OCR_DOC_KHAC"]
    ocr_calls: list[list[str]] = []
    prompts: list[dict] = []

    async def fake_tiengnoi(batch, max_tokens=None):
        ocr_calls.append([item["name"] for item in batch])
        return [{"name": item["name"], "text": text} for item, text in zip(batch, texts)]

    async def fake_chat(messages, **_kwargs):
        payload = json.loads(messages[1]["content"])
        prompts.append(payload)
        mapping = {
            "OCR_DOC_NAM": "cccd_nam",
            "OCR_DOC_NU": "cccd_nu",
            "OCR_DOC_TO_KHAI": "to_khai",
            "OCR_DOC_KHAC": "khac",
        }
        return json.dumps({"doc_key": mapping[payload["ocrText"]]})

    monkeypatch.setattr(llm_classifier.ocr.ocr_tiengnoi, "ocr_per_file", fake_tiengnoi)
    monkeypatch.setattr(llm_classifier.client, "chat", fake_chat)

    result = await classify.classify_files(
        files,
        get_procedure("ket-hon")["requiredDocs"],
        [],
        hint_doc_key=None,
        procedure_key="ket-hon",
    )

    assert ocr_calls == [[item["name"] for item in files]]
    assert len(prompts) == len(files)
    assert {item["ocrText"] for item in prompts} == set(texts)
    assert all(sum(text in item["ocrText"] for text in texts) == 1 for item in prompts)
    assert [item["doc_key"] for item in result] == ["cccd_nam", "cccd_nu", "to_khai", "khac"]
    assert all(item["ocr_ok"] for item in result)


@pytest.mark.asyncio
async def test_ket_hon_llm_failure_falls_back_only_for_that_file(monkeypatch):
    files = [_file("nam.jpg"), _file("nu.jpg")]

    async def fake_tiengnoi(_batch, max_tokens=None):
        return [
            {"text": "CĂN CƯỚC CÔNG DÂN Giới tính: Nam"},
            {"text": "OCR_DOC_NU"},
        ]

    async def fake_chat(messages, **_kwargs):
        payload = json.loads(messages[1]["content"])
        if "Giới tính: Nam" in payload["ocrText"]:
            raise RuntimeError("LLM lỗi riêng tệp nam")
        return '{"doc_key":"cccd_nu"}'

    monkeypatch.setattr(llm_classifier.ocr.ocr_tiengnoi, "ocr_per_file", fake_tiengnoi)
    monkeypatch.setattr(llm_classifier.client, "chat", fake_chat)

    result = await classify.classify_files(
        files,
        get_procedure("ket-hon")["requiredDocs"],
        [],
        hint_doc_key=None,
        procedure_key="ket-hon",
    )

    assert [item["doc_key"] for item in result] == ["cccd_nam", "cccd_nu"]
    assert "LLM" not in result[0]["note"]
    assert "LLM" in result[1]["note"]


@pytest.mark.asyncio
async def test_other_procedure_uses_tiengnoi_classifier(monkeypatch):
    async def fake_tiengnoi(_files, *, classify=False):
        assert classify is True
        return [{"text": "TỜ KHAI ĐĂNG KÝ KẾT HÔN"}]

    monkeypatch.setattr(classify.ocr, "ocr_per_file", fake_tiengnoi)

    result = await classify.classify_files(
        [_file("to-khai.jpg")],
        [{"key": "to_khai", "name": "Tờ khai", "sides": 1}],
        [],
        hint_doc_key=None,
        procedure_key="thu-tuc-khac",
    )

    assert result[0]["doc_key"] == "to_khai"

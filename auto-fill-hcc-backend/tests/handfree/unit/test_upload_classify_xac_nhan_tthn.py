import json

import pytest

from app.channels.handfree.procedure_registry import get_procedure
from app.upload_session import classify, llm_classifier
from app.upload_session.store import progress


PROCEDURE = "xac-nhan-tinh-trang-hon-nhan"


def _file(name: str) -> dict:
    return {
        "name": name,
        "type": "image/jpeg",
        "dataUrl": "data:image/jpeg;base64,AA==",
    }


def test_xac_nhan_tthn_registry_uses_four_repeatable_file_groups():
    proc = get_procedure(PROCEDURE)
    docs = proc["requiredDocs"]
    by_key = {item["key"]: item for item in docs}

    assert [item["key"] for item in docs] == ["cccd", "to_khai", "chung_minh_tthn", "khac"]
    assert proc["hideRepeatableHint"] is True
    assert by_key["chung_minh_tthn"]["name"] == "Giấy tờ chứng minh tình trạng hôn nhân (nếu có)"
    assert by_key["khac"]["name"] == "Các giấy tờ khác liên quan"
    assert all(item["sides"] == 1 and item.get("repeatable") for item in docs)
    assert not by_key["cccd"].get("optional")
    assert all(by_key[key].get("optional") for key in ("to_khai", "chung_minh_tthn", "khac"))

    files = [
        *({"doc_key": "cccd"} for _ in range(3)),
        *({"doc_key": "to_khai"} for _ in range(2)),
        *({"doc_key": "chung_minh_tthn"} for _ in range(4)),
        *({"doc_key": "khac"} for _ in range(5)),
    ]
    result = progress({
        "procedure_key": PROCEDURE,
        "required_docs": docs,
        "files": files,
        "complete": False,
    })
    counts = {item["key"]: item["receivedCount"] for item in result["docs"]}

    assert result["received"] == result["total"] == 1
    assert result["files_count"] == 14
    assert counts == {"cccd": 3, "to_khai": 2, "chung_minh_tthn": 4, "khac": 5}


@pytest.mark.asyncio
async def test_xac_nhan_tthn_uses_one_tiengnoi_batch_and_one_llm_prompt_per_file(monkeypatch):
    files = [
        _file("cccd.jpg"),
        _file("to-khai.jpg"),
        _file("ly-hon.jpg"),
        _file("ket-hon.jpg"),
        _file("uy-quyen.jpg"),
    ]
    texts = ["OCR_CCCD", "OCR_TO_KHAI", "OCR_LY_HON", "OCR_KET_HON", "OCR_UY_QUYEN"]
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
            "OCR_LY_HON": "chung_minh_tthn",
            "OCR_KET_HON": "chung_minh_tthn",
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
    assert all(sum(text in item["ocrText"] for text in texts) == 1 for item in prompts)
    assert [item["doc_key"] for item in result] == [
        "cccd", "to_khai", "chung_minh_tthn", "chung_minh_tthn", "khac",
    ]
    assert all(item["side"] is None and item["ocr_ok"] for item in result)
    assert all("phân loại thành cccd chỉ vì" in prompt.lower() for prompt in system_prompts)


@pytest.mark.asyncio
async def test_xac_nhan_tthn_llm_failure_falls_back_per_file_without_mistaking_declaration_for_cccd(
    monkeypatch,
):
    files = [
        _file("to-khai.jpg"), _file("ly-hon.jpg"), _file("uy-quyen.jpg"),
        _file("cccd.jpg"), _file("khong-ro.jpg"),
    ]

    async def fake_tiengnoi(_batch):
        return [
            {"text": "TỜ KHAI CẤP GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN CCCD số 012345678901"},
            {"text": "BẢN ÁN LY HÔN có ghi căn cước công dân của đương sự"},
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
        "to_khai", "chung_minh_tthn", "khac", "cccd", "khac",
    ]
    assert all("LLM phân loại" not in item["note"] for item in result)


@pytest.mark.asyncio
async def test_xac_nhan_tthn_old_session_routes_new_evidence_group_to_old_other_slot(monkeypatch):
    async def fake_tiengnoi(_batch):
        return [{"text": "TRÍCH LỤC KHAI TỬ"}]

    async def fake_chat(_messages, **_kwargs):
        return '{"doc_key":"chung_minh_tthn"}'

    monkeypatch.setattr(llm_classifier.ocr_tiengnoi, "ocr_per_file", fake_tiengnoi)
    monkeypatch.setattr(llm_classifier.client, "chat", fake_chat)

    old_docs = [
        {"key": "cccd", "name": "CCCD", "sides": 2},
        {"key": "to_khai", "name": "Tờ khai", "sides": 1, "optional": True},
        {"key": "khac", "name": "Giấy tờ chứng minh", "sides": 5, "optional": True},
    ]
    result = await classify.classify_files(
        [_file("khai-tu.jpg")], old_docs, [], None, procedure_key=PROCEDURE,
    )

    assert result[0]["doc_key"] == "khac"
    assert "nhóm cũ" in result[0]["note"]

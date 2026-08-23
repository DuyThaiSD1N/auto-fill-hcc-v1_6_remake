import base64
import json

import fitz

from app.pipelines.ket_hon.attach import planner as ket_hon
from app.process.schemas import FileItem


def _file(name: str, mime: str = "application/pdf", data_url: str | None = None) -> FileItem:
    return FileItem(
        name=name,
        type=mime,
        dataUrl=data_url or f"data:{mime};base64,AAA",
        role="doc",
    )


def _pdf_file(name: str, pages: int) -> FileItem:
    document = fitz.open()
    try:
        for _ in range(pages):
            document.new_page(width=595, height=842)
        payload = base64.b64encode(document.tobytes()).decode("ascii")
    finally:
        document.close()
    return _file(name, data_url=f"data:application/pdf;base64,{payload}")


def _attachment_context(index: int = 2, name: str = "Giấy tờ tùy thân của hai bên") -> dict:
    return {
        "attachmentContext": {
            "components": [
                {"index": 1, "componentName": "Mẫu hộ tịch điện tử", "hasFile": False},
                {"index": index, "componentName": name, "hasFile": False},
            ]
        }
    }


async def test_ket_hon_uses_one_batch_prompt_and_keeps_duplicate_file_names_by_index(monkeypatch):
    calls = []

    async def fake_ocr_per_file(files):
        return [
            {"name": "image.pdf", "text": "CĂN CƯỚC CÔNG DÂN NAM-ID 040203015844"},
            {"name": "image.pdf", "text": "CĂN CƯỚC CÔNG DÂN NU-ID 012193000851"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        calls.append(messages)
        prompt = messages[1]["content"]
        assert "NAM-ID" in prompt
        assert "NU-ID" in prompt
        assert "image.pdf" not in prompt
        return json.dumps({"documents": [
            {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "identity"},
            {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "identity"},
        ]})

    monkeypatch.setattr(ket_hon.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(ket_hon.client, "chat", fake_chat)

    options = _attachment_context(4, "Hộ chiếu hoặc Thẻ căn cước của hai bên")
    result = await ket_hon.plan_ket_hon_attachments(
        [_file("image.pdf"), _file("image.pdf")], options, {"request_id": "req_test"},
    )

    assert len(calls) == 1
    assert len(result["attachments"]) == 1
    item = result["attachments"][0]
    assert item["documentName"] == "Căn cước công dân"
    assert item["target"] == "existing"
    assert item["componentIndex"] == 4
    assert item["componentName"] == "Hộ chiếu hoặc Thẻ căn cước của hai bên"
    assert item["sourceSegments"] == [
        {"fileIndex": 0, "pageIndexes": None},
        {"fileIndex": 1, "pageIndexes": None},
    ]


async def test_ket_hon_merges_four_identity_faces_by_person_and_front_before_back(monkeypatch):
    ocr_texts = [
        "ĐẶC ĐIỂM NHẬN DẠNG IDVNM 040203015844",
        "CĂN CƯỚC CÔNG DÂN Số 012193000851",
        "CĂN CƯỚC CÔNG DÂN Số 040203015844",
        "ĐẶC ĐIỂM NHẬN DẠNG IDVNM 012193000851",
    ]

    async def fake_ocr_per_file(files):
        return [{"name": file["name"], "text": ocr_texts[index]} for index, file in enumerate(files)]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"fileIndex": index, "pageFrom": 1, "pageTo": 1, "type": "identity"}
            for index in range(4)
        ]})

    monkeypatch.setattr(ket_hon.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(ket_hon.client, "chat", fake_chat)

    result = await ket_hon.plan_ket_hon_attachments(
        [
            _file("nam-sau.jpg", "image/jpeg"),
            _file("nu-truoc.jpg", "image/jpeg"),
            _file("nam-truoc.jpg", "image/jpeg"),
            _file("nu-sau.jpg", "image/jpeg"),
        ],
        _attachment_context(),
        {},
    )

    assert len(result["attachments"]) == 1
    assert result["attachments"][0]["sourceSegments"] == [
        {"fileIndex": 2, "pageIndexes": None},
        {"fileIndex": 0, "pageIndexes": None},
        {"fileIndex": 1, "pageIndexes": None},
        {"fileIndex": 3, "pageIndexes": None},
    ]


async def test_ket_hon_splits_mixed_pdf_and_routes_non_identity_as_new_components(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "mixed.pdf",
            "text": """
───── Trang 1/3 ─────
CĂN CƯỚC CÔNG DÂN Số 040203015844
───── Trang 2/3 ─────
TỜ KHAI ĐĂNG KÝ KẾT HÔN
───── Trang 3/3 ─────
BẢN CAM ĐOAN
""",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "identity"},
            {"fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "marriage_declaration"},
            {"fileIndex": 0, "pageFrom": 3, "pageTo": 3, "type": "commitment"},
        ]})

    monkeypatch.setattr(ket_hon.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(ket_hon.client, "chat", fake_chat)

    result = await ket_hon.plan_ket_hon_attachments(
        [_pdf_file("mixed.pdf", 3)], _attachment_context(), {},
    )

    assert [item["documentName"] for item in result["attachments"]] == [
        "Căn cước công dân",
        "Tờ khai đăng ký kết hôn",
        "Bản cam đoan",
    ]
    assert result["attachments"][0]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0]}]
    assert result["attachments"][1]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [1]}]
    assert result["attachments"][2]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [2]}]
    assert result["attachments"][0]["target"] == "existing"
    assert all(item["target"] == "new" for item in result["attachments"][1:])


async def test_ket_hon_keeps_specific_other_names_and_deduplicates(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "a.pdf", "text": "QUYẾT ĐỊNH LY HÔN"},
            {"name": "b.pdf", "text": "QUYẾT ĐỊNH LY HÔN"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {
                "fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "other",
                "documentName": "Quyết định ly hôn",
            },
            {
                "fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "other",
                "documentName": "Quyết định ly hôn",
            },
        ]})

    monkeypatch.setattr(ket_hon.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(ket_hon.client, "chat", fake_chat)

    result = await ket_hon.plan_ket_hon_attachments([_file("a.pdf"), _file("b.pdf")], {}, {})

    assert [item["documentName"] for item in result["attachments"]] == [
        "Quyết định ly hôn",
        "Quyết định ly hôn 2",
    ]
    assert all(item["target"] == "new" for item in result["attachments"])


async def test_ket_hon_llm_failure_does_not_turn_divorce_document_into_identity(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": "ly-hon.pdf", "text": "QUYẾT ĐỊNH LY HÔN"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(ket_hon.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(ket_hon.client, "chat", fake_chat)

    result = await ket_hon.plan_ket_hon_attachments([_file("ly-hon.pdf")], {}, {})

    assert len(result["attachments"]) == 1
    assert result["attachments"][0]["documentName"] == "Quyết định ly hôn"
    assert result["attachments"][0]["target"] == "new"
    assert result["attachments"][0]["componentIndex"] is None
    assert any("attachment_agent" in error for error in result["errors"])

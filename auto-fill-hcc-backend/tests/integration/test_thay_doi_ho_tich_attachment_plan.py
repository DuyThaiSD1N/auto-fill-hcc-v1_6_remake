"""Plan đính kèm bước 3 cho thủ tục thay đổi/cải chính hộ tịch."""

import base64
import json

import fitz

from app.pipelines.thay_doi_ho_tich.attach import planner
from app.process.schemas import FileItem
from app.procedures.registry import get_procedure


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


def _context() -> dict:
    return {
        "attachmentContext": {
            "components": [
                {"index": 1, "componentName": "Mẫu hộ tịch điện tử", "hasFile": True},
                {
                    "index": 4,
                    "componentName": (
                        "Giấy tờ liên quan đến việc thay đổi, cải chính, bổ sung thông tin hộ tịch, "
                        "xác định lại dân tộc"
                    ),
                    "hasFile": False,
                },
                {"index": 6, "componentName": "Văn bản ủy quyền theo quy định", "hasFile": False},
            ]
        }
    }


async def test_routes_supporting_evidence_authorization_and_identity(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "tlkh.pdf", "text": "TRÍCH LỤC GHI CHÚ KẾT HÔN"},
            {"name": "uyquyen.pdf", "text": "GIẤY ỦY QUYỀN"},
            {"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN\nCITIZEN IDENTITY CARD"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "supporting_evidence", "documentName": "Trích lục kết hôn"},
            {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "authorization", "documentName": "Văn bản ủy quyền"},
            {"fileIndex": 2, "pageFrom": 1, "pageTo": 1, "type": "identity", "documentName": "Căn cước công dân"},
        ]})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    result = await planner.plan_thay_doi_ho_tich_attachments(
        [_file("tlkh.pdf"), _file("uyquyen.pdf"), _file("cccd.pdf")], _context(), {"request_id": "r1"},
    )

    assert [item["componentIndex"] for item in result["attachments"]] == [4, 6, None]
    assert [item["target"] for item in result["attachments"]] == ["existing", "existing", "new"]
    assert result["attachments"][0]["componentName"].startswith("Giấy tờ liên quan")
    assert result["attachments"][2]["documentName"] == "Căn cước công dân"


async def test_uses_one_batch_and_preserves_duplicate_filenames_by_index(monkeypatch):
    calls = []

    async def fake_ocr_per_file(files):
        return [
            {"name": "image.pdf", "text": "GIẤY KHAI SINH SỐ 01"},
            {"name": "image.pdf", "text": "HỌC BẠ SỐ 02"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        calls.append(messages)
        prompt = messages[1]["content"]
        assert "GIẤY KHAI SINH SỐ 01" in prompt
        assert "HỌC BẠ SỐ 02" in prompt
        assert "image.pdf" not in prompt
        return json.dumps({"documents": [
            {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "supporting_evidence", "documentName": "Giấy khai sinh"},
            {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "supporting_evidence", "documentName": "Học bạ"},
        ]})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    result = await planner.plan_thay_doi_ho_tich_attachments(
        [_file("image.pdf"), _file("image.pdf")], _context(), {},
    )

    assert len(calls) == 1
    assert [item["documentName"] for item in result["attachments"]] == ["Giấy khai sinh", "Học bạ"]
    assert [item["fileIndex"] for item in result["attachments"]] == [0, 1]


async def test_merges_all_identity_people_and_keeps_front_back_order(monkeypatch):
    texts = [
        "ĐẶC ĐIỂM NHẬN DẠNG IDVNM 040203015844",
        "CĂN CƯỚC CÔNG DÂN Số 012193000851",
        "CĂN CƯỚC CÔNG DÂN Số 040203015844",
        "ĐẶC ĐIỂM NHẬN DẠNG IDVNM 012193000851",
    ]

    async def fake_ocr_per_file(files):
        return [{"name": file["name"], "text": texts[index]} for index, file in enumerate(files)]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"fileIndex": index, "pageFrom": 1, "pageTo": 1, "type": "identity"}
            for index in range(4)
        ]})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    result = await planner.plan_thay_doi_ho_tich_attachments(
        [
            _file("a-sau.jpg", "image/jpeg"),
            _file("b-truoc.jpg", "image/jpeg"),
            _file("a-truoc.jpg", "image/jpeg"),
            _file("b-sau.jpg", "image/jpeg"),
        ],
        {},
        {},
    )

    assert len(result["attachments"]) == 1
    assert result["attachments"][0]["sourceSegments"] == [
        {"fileIndex": 2, "pageIndexes": None},
        {"fileIndex": 0, "pageIndexes": None},
        {"fileIndex": 1, "pageIndexes": None},
        {"fileIndex": 3, "pageIndexes": None},
    ]


async def test_splits_mixed_pdf_and_does_not_use_eform_row_for_paper_declaration(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "mixed.pdf",
            "text": """
───── Trang 1/4 ─────
CĂN CƯỚC CÔNG DÂN Số 040203015844
───── Trang 2/4 ─────
TỜ KHAI THAY ĐỔI CẢI CHÍNH HỘ TỊCH
───── Trang 3/4 ─────
GIẤY KHAI SINH
───── Trang 4/4 ─────
VĂN BẢN ỦY QUYỀN
""",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "identity"},
            {"fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "paper_declaration"},
            {"fileIndex": 0, "pageFrom": 3, "pageTo": 3, "type": "supporting_evidence", "documentName": "Giấy khai sinh"},
            {"fileIndex": 0, "pageFrom": 4, "pageTo": 4, "type": "authorization", "documentName": "Văn bản ủy quyền"},
        ]})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    result = await planner.plan_thay_doi_ho_tich_attachments([_pdf_file("mixed.pdf", 4)], _context(), {})

    assert [item["documentName"] for item in result["attachments"]] == [
        "Căn cước công dân",
        "Tờ khai cải chính hộ tịch bản giấy",
        "Giấy khai sinh",
        "Văn bản ủy quyền",
    ]
    assert [item["sourceSegments"] for item in result["attachments"]] == [
        [{"fileIndex": 0, "pageIndexes": [0]}],
        [{"fileIndex": 0, "pageIndexes": [1]}],
        [{"fileIndex": 0, "pageIndexes": [2]}],
        [{"fileIndex": 0, "pageIndexes": [3]}],
    ]
    assert [item["target"] for item in result["attachments"]] == [
        "new", "new", "existing", "existing",
    ]


async def test_llm_failure_routes_known_documents_with_rules(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "khai-sinh.pdf", "text": "GIẤY KHAI SINH"},
            {"name": "uy-quyen.pdf", "text": "VĂN BẢN ỦY QUYỀN"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    result = await planner.plan_thay_doi_ho_tich_attachments(
        [_file("khai-sinh.pdf"), _file("uy-quyen.pdf")], _context(), {},
    )

    assert [item["componentIndex"] for item in result["attachments"]] == [4, 6]
    assert [item["documentName"] for item in result["attachments"]] == ["Giấy khai sinh", "Văn bản ủy quyền"]
    assert any("attachment_agent" in error for error in result["errors"])


async def test_does_not_guess_split_when_multi_page_ocr_has_no_page_boundaries(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": "mixed.pdf", "text": "CCCD rồi đến GIẤY KHAI SINH"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "identity"},
            {"fileIndex": 0, "pageFrom": 2, "pageTo": 3, "type": "supporting_evidence"},
        ]})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    result = await planner.plan_thay_doi_ho_tich_attachments([_pdf_file("mixed.pdf", 3)], {}, {})

    assert len(result["attachments"]) == 1
    assert "sourceSegments" not in result["attachments"][0]
    assert any("Không có mốc trang" in error for error in result["errors"])


def test_procedure_has_attachment_step():
    procedure = get_procedure("thay-doi-cai-chinh-ho-tich")

    assert procedure["hasAttachmentStep"] is True

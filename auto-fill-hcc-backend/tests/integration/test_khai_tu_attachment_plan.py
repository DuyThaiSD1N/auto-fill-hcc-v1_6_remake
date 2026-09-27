import base64
import json

import fitz

from app.pipelines.khai_tu.attach import planner as khai_tu
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


def _attachment_context() -> dict:
    return {
        "attachmentContext": {
            "components": [
                {"index": 1, "componentName": "Mẫu hộ tịch điện tử", "hasFile": True},
                {
                    "index": 3,
                    "componentName": "Giấy báo tử hoặc giấy tờ thay Giấy báo tử do cơ quan có thẩm quyền cấp",
                    "hasFile": False,
                },
                {
                    "index": 5,
                    "componentName": "Giấy tờ chứng minh sự kiện chết đối với người chết đã lâu",
                    "hasFile": False,
                },
                {
                    "index": 7,
                    "componentName": "Văn bản ủy quyền thực hiện việc đăng ký khai tử",
                    "hasFile": False,
                },
                {
                    "index": 9,
                    "componentName": "Giấy tờ chứng minh nơi người đó chết hoặc nơi phát hiện thi thể",
                    "hasFile": False,
                },
            ]
        }
    }


async def test_khai_tu_uses_one_batch_prompt_and_merges_duplicate_named_identities(monkeypatch):
    calls = []

    async def fake_ocr_per_file(files):
        return [
            {"name": "image.pdf", "text": "CĂN CƯỚC CÔNG DÂN\nSố 040203015844"},
            {"name": "image.pdf", "text": "CĂN CƯỚC CÔNG DÂN\nSố 012193000851"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        calls.append(messages)
        prompt = messages[1]["content"]
        assert "040203015844" in prompt
        assert "012193000851" in prompt
        assert "image.pdf" not in prompt
        return json.dumps({"documents": [
            {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "identity"},
            {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "identity"},
        ]})

    monkeypatch.setattr(khai_tu.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_tu.client, "chat", fake_chat)

    result = await khai_tu.plan_khai_tu_attachments(
        [_file("image.pdf"), _file("image.pdf")], {}, {"request_id": "req_test"},
    )

    assert len(calls) == 1
    assert len(result["attachments"]) == 2
    assert [item["fileIndex"] for item in result["attachments"]] == [0, 1]
    assert all(item["target"] == "new" for item in result["attachments"])
    assert not any("không khớp" in error for error in result["errors"])


async def test_khai_tu_merges_all_identity_people_and_keeps_each_card_faces_together(monkeypatch):
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

    monkeypatch.setattr(khai_tu.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_tu.client, "chat", fake_chat)

    result = await khai_tu.plan_khai_tu_attachments(
        [
            _file("nguoi-a-sau.jpg", "image/jpeg"),
            _file("nguoi-b-truoc.jpg", "image/jpeg"),
            _file("nguoi-a-truoc.jpg", "image/jpeg"),
            _file("nguoi-b-sau.jpg", "image/jpeg"),
        ],
        {},
        {},
    )

    assert len(result["attachments"]) == 2
    assert result["attachments"][0]["sourceSegments"] == [
        {"fileIndex": 2, "pageIndexes": None},
        {"fileIndex": 0, "pageIndexes": None},
    ]
    assert result["attachments"][1]["sourceSegments"] == [
        {"fileIndex": 1, "pageIndexes": None},
        {"fileIndex": 3, "pageIndexes": None},
    ]


async def test_khai_tu_routes_all_existing_rows_from_live_attachment_context(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "a.pdf", "text": "GIẤY BÁO TỬ"},
            {"name": "b.pdf", "text": "GIẤY TỜ CHỨNG MINH SỰ KIỆN CHẾT"},
            {"name": "c.pdf", "text": "VĂN BẢN ỦY QUYỀN"},
            {"name": "d.pdf", "text": "GIẤY TỜ CHỨNG MINH NƠI PHÁT HIỆN THI THỂ"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "death_notice"},
            {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "death_event_proof"},
            {"fileIndex": 2, "pageFrom": 1, "pageTo": 1, "type": "authorization"},
            {"fileIndex": 3, "pageFrom": 1, "pageTo": 1, "type": "death_place_proof"},
        ]})

    monkeypatch.setattr(khai_tu.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_tu.client, "chat", fake_chat)

    result = await khai_tu.plan_khai_tu_attachments(
        [_file("a.pdf"), _file("b.pdf"), _file("c.pdf"), _file("d.pdf")],
        _attachment_context(),
        {},
    )

    assert [item["componentIndex"] for item in result["attachments"]] == [3, 5, 7, 9]
    assert [item["componentName"] for item in result["attachments"]] == [
        "Giấy báo tử hoặc giấy tờ thay Giấy báo tử do cơ quan có thẩm quyền cấp",
        "Giấy tờ chứng minh sự kiện chết đối với người chết đã lâu",
        "Văn bản ủy quyền thực hiện việc đăng ký khai tử",
        "Giấy tờ chứng minh nơi người đó chết hoặc nơi phát hiện thi thể",
    ]
    assert all(item["target"] == "existing" for item in result["attachments"])


async def test_khai_tu_routes_tombstone_to_death_event_row_even_when_llm_calls_it_other(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "image.pdf",
            "text": (
                "PHẦN MỘ\nTƯỜNG THÔNG\n(BÀ TẠ KHE)\n"
                "SINH NGÀY: 12-10-ĐINH TỴ (1917)\n"
                "MẤT NGÀY: 30-10-ĐINH SỬU (1997)\nHƯỞNG THỌ: 81 TUỔI"
            ),
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{
            "fileIndex": 0,
            "pageFrom": 1,
            "pageTo": 1,
            "type": "other",
            "documentName": "Danh sách mộ",
        }]})

    monkeypatch.setattr(khai_tu.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_tu.client, "chat", fake_chat)

    result = await khai_tu.plan_khai_tu_attachments(
        [_file("image.pdf")], _attachment_context(), {},
    )

    assert result["attachments"] == [{
        "fileIndex": 0,
        "fileName": "image.pdf",
        "documentName": "Ảnh bia mộ",
        "componentName": "Giấy tờ chứng minh sự kiện chết đối với người chết đã lâu",
        "target": "existing",
        "componentIndex": 5,
        "needsAddComponent": False,
        "detectedType": "Ảnh bia mộ",
    }]
    assert result["extracted"]["classified"][0]["type"] == "death_event_proof"
    assert result["extracted"]["classified"][0]["documentName"] == "Ảnh bia mộ"


async def test_khai_tu_splits_mixed_pdf_into_identity_declaration_and_existing_rows(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "mixed.pdf",
            "text": """
───── Trang 1/4 ─────
CĂN CƯỚC CÔNG DÂN Số 040203015844
───── Trang 2/4 ─────
TỜ KHAI ĐĂNG KÝ KHAI TỬ
───── Trang 3/4 ─────
GIẤY BÁO TỬ
───── Trang 4/4 ─────
VĂN BẢN ỦY QUYỀN
""",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "identity"},
            {"fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "paper_declaration"},
            {"fileIndex": 0, "pageFrom": 3, "pageTo": 3, "type": "death_notice"},
            {"fileIndex": 0, "pageFrom": 4, "pageTo": 4, "type": "authorization"},
        ]})

    monkeypatch.setattr(khai_tu.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_tu.client, "chat", fake_chat)

    result = await khai_tu.plan_khai_tu_attachments(
        [_pdf_file("mixed.pdf", 4)], _attachment_context(), {},
    )

    assert [item["documentName"] for item in result["attachments"]] == [
        "Căn cước công dân",
        "Tờ khai đăng ký khai tử bản giấy",
        "Giấy báo tử",
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


async def test_khai_tu_llm_failure_uses_safe_rules_without_role_matching(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "cccd.pdf", "text": "SOCIALIST REPUBLIC OF VIET NAM\nCĂN CƯỚC CÔNG DÂN\nIDVNM040203015844"},
            {"name": "uy-quyen.pdf", "text": "VĂN BẢN ỦY QUYỀN\nSố CCCD 040203015844"},
            {"name": "xac-nhan.pdf", "text": "GIẤY XÁC NHẬN CỦA CƠ QUAN CÓ THẨM QUYỀN"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(khai_tu.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_tu.client, "chat", fake_chat)

    result = await khai_tu.plan_khai_tu_attachments(
        [_file("cccd.pdf"), _file("uy-quyen.pdf"), _file("xac-nhan.pdf")],
        _attachment_context(),
        {},
    )

    assert [item["documentName"] for item in result["attachments"]] == [
        "Căn cước công dân",
        "Văn bản ủy quyền",
        "Tài liệu khai tử",
    ]
    assert result["attachments"][0]["target"] == "new"
    assert result["attachments"][1]["componentIndex"] == 7
    assert result["attachments"][2]["target"] == "new"
    assert any("attachment_agent" in error for error in result["errors"])
    assert not any("không khớp" in error for error in result["errors"])


async def test_khai_tu_does_not_guess_page_split_without_ocr_boundaries(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": "mixed.pdf", "text": "CCCD rồi đến TỜ KHAI ĐĂNG KÝ KHAI TỬ"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "identity"},
            {"fileIndex": 0, "pageFrom": 2, "pageTo": 3, "type": "paper_declaration"},
        ]})

    monkeypatch.setattr(khai_tu.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khai_tu.client, "chat", fake_chat)

    result = await khai_tu.plan_khai_tu_attachments([_pdf_file("mixed.pdf", 3)], {}, {})

    assert len(result["attachments"]) == 1
    assert "sourceSegments" not in result["attachments"][0]
    assert any("Không có mốc trang" in error for error in result["errors"])


def test_khai_tu_procedure_has_attachment_step():
    proc = get_procedure("khai-tu")

    assert proc["hasAttachmentStep"] is True

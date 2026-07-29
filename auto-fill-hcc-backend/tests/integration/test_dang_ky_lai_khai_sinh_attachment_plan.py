import json

from app.pipelines.khai_sinh_dang_ky_lai.attach import planner as dang_ky_lai_khai_sinh
from app.pipelines.khai_sinh_dang_ky_lai.attach.prompt import SYSTEM_PROMPT, build_user_prompt
from app.process.schemas import FileItem
from app.procedures.registry import get_procedure


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


def _session():
    return {
        "request_id": "req_dang_ky_lai_ks_test",
        "procedure": "khai-sinh-dang-ky-lai",
        "fields": [
            {"name": "HoTenKS", "value": "VÀNG A PHỈNH"},
            {"name": "SoDinhDanhCha", "value": "040203015844"},
            {"name": "SoDinhDanhMe", "value": "012193000851"},
        ],
    }


async def test_dang_ky_lai_khai_sinh_attachment_plan_routes_default_components(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "gks-ban-sao.pdf", "text": "BẢN SAO GIẤY KHAI SINH"},
            {"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN"},
            {"name": "uy-quyen.pdf", "text": "VĂN BẢN ỦY QUYỀN"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "birth_certificate_copy", "title": "Giấy khai sinh bản sao"},
                {"index": 1, "type": "personal_supporting_document", "title": "Căn cước công dân"},
                {"index": 2, "type": "authorization", "title": "Văn bản ủy quyền"},
            ]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    res = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("gks-ban-sao.pdf"), _file("cccd.pdf"), _file("uy-quyen.pdf")],
        {},
        _session(),
    )
    items = res["attachments"]

    assert items[0]["target"] == "existing"
    assert items[0]["componentIndex"] == 2
    assert "Bản sao Giấy khai sinh" in items[0]["componentName"]

    assert items[1]["target"] == "existing"
    assert items[1]["componentIndex"] == 3
    assert "Thẻ căn cước công dân" in items[1]["componentName"]

    assert items[2]["target"] == "existing"
    assert items[2]["componentIndex"] == 5
    assert "Văn bản ủy quyền" in items[2]["componentName"]


async def test_dang_ky_lai_khai_sinh_attachment_plan_adds_extra_personal_documents(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN"},
            {"name": "hoc-ba.pdf", "text": "HỌC BẠ"},
            {"name": "bang-tot-nghiep.pdf", "text": "BẰNG TỐT NGHIỆP"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "personal_supporting_document", "title": "Căn cước công dân"},
                {"index": 1, "type": "personal_supporting_document", "title": "Học bạ"},
                {"index": 2, "type": "personal_supporting_document", "title": "Bằng tốt nghiệp"},
            ]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    res = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("cccd.pdf"), _file("hoc-ba.pdf"), _file("bang-tot-nghiep.pdf")],
        {},
        _session(),
    )
    items = res["attachments"]

    assert items[0]["target"] == "existing"
    assert items[0]["componentIndex"] == 3

    assert items[1]["target"] == "new"
    assert items[1]["componentIndex"] is None
    assert items[1]["componentName"] == "Học bạ"

    assert items[2]["target"] == "new"
    assert items[2]["componentIndex"] is None
    assert items[2]["componentName"] == "Bằng tốt nghiệp"


async def test_dang_ky_lai_khai_sinh_attachment_plan_adds_paper_declaration(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": "to-khai-giay.pdf", "text": "TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "paper_declaration", "title": "Tờ khai đăng ký lại khai sinh"},
            ]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    res = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("to-khai-giay.pdf")],
        {},
        _session(),
    )
    item = res["attachments"][0]

    assert item["target"] == "new"
    assert item["componentIndex"] is None
    assert item["documentName"] == "Tờ khai bản giấy"
    assert item["componentName"] == "Tờ khai bản giấy"


async def test_dang_ky_lai_khai_sinh_attachment_plan_adds_commitment_statement(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "gks-ban-sao.pdf", "text": "BẢN SAO GIẤY KHAI SINH"},
            {
                "name": "ban-cam-doan.pdf",
                "text": "BẢN CAM ĐOAN Tôi cam đoan giấy khai sinh bản chính đã bị mất",
            },
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "birth_certificate_copy", "title": "Giấy khai sinh bản sao"},
                {"index": 1, "type": "commitment_statement", "title": "Bản cam đoan"},
            ]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    res = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("gks-ban-sao.pdf"), _file("ban-cam-doan.pdf")],
        {},
        _session(),
    )
    items = res["attachments"]

    assert items[0]["target"] == "existing"
    assert items[0]["componentIndex"] == 2
    assert "Bản sao Giấy khai sinh" in items[0]["componentName"]

    assert items[1]["target"] == "new"
    assert items[1]["componentIndex"] is None
    assert items[1]["needsAddComponent"] is True
    assert items[1]["documentName"] == "Bản cam đoan"
    assert items[1]["componentName"] == "Bản cam đoan"
    assert items[1]["detectedType"] == "Bản cam đoan"


def test_dang_ky_lai_khai_sinh_procedure_has_attachment_step():
    proc = get_procedure("khai-sinh-dang-ky-lai")

    assert proc["hasAttachmentStep"] is True


def test_dang_ky_lai_khai_sinh_attachment_prompt_requires_llm_enum():
    assert "commitment_statement" in SYSTEM_PROMPT
    assert "Bản cam đoan" in SYSTEM_PROMPT
    assert 'type":"commitment_statement"' in SYSTEM_PROMPT
    assert 'type":"birth_certificate_copy","title":"Bản cam đoan"' in SYSTEM_PROMPT
    assert "Chỉ phân loại theo OCR_TEXT" in SYSTEM_PROMPT
    assert "Không dùng tên file" in SYSTEM_PROMPT
    assert "Ví dụ sai" in SYSTEM_PROMPT


def test_dang_ky_lai_khai_sinh_attachment_user_prompt_uses_ocr_text_only():
    prompt = build_user_prompt([
        {
            "index": 0,
            "fileName": "ban-cam-doan.pdf",
            "text": "BẢN CAM ĐOAN Tôi cam đoan giấy khai sinh bản chính đã bị mất",
        }
    ])

    assert "ocrText" in prompt
    assert "BẢN CAM ĐOAN" in prompt
    assert "ban-cam-doan.pdf" not in prompt
    assert "fileName" not in prompt

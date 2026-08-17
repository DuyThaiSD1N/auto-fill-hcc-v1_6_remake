import json

from app.pipelines.trich_luc.attach import planner as trich_luc
from app.pipelines.trich_luc.attach.prompt import SYSTEM_PROMPT, build_user_prompt
from app.process.schemas import FileItem
from app.procedures.registry import get_procedure


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


def _session():
    return {
        "request_id": "req_trich_luc_test",
        "procedure": "trich-luc-ks",
        "fields": [
            {"name": "HoSo_LoaiYeuCau", "value": "Trích lục kết hôn (bản sao)/ Trích lục ghi chú kết hôn (bản sao)"},
        ],
    }


async def test_trich_luc_attachment_plan_routes_civil_status_documents_to_new_components(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "gks.pdf", "text": "GIẤY KHAI SINH"},
            {"name": "ket-hon.pdf", "text": "GIẤY CHỨNG NHẬN KẾT HÔN"},
            {"name": "khai-tu.pdf", "text": "TRÍCH LỤC KHAI TỬ"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "civil_status_birth", "title": "Giấy khai sinh"},
                {"index": 1, "type": "civil_status_marriage", "title": "Giấy chứng nhận kết hôn"},
                {"index": 2, "type": "civil_status_death", "title": "Trích lục khai tử"},
            ]
        })

    monkeypatch.setattr(trich_luc.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(trich_luc.client, "chat", fake_chat)

    res = await trich_luc.plan_trich_luc_attachments(
        [_file("gks.pdf"), _file("ket-hon.pdf"), _file("khai-tu.pdf")],
        {},
        _session(),
    )
    items = res["attachments"]

    assert items[0]["target"] == "new"
    assert items[0]["componentName"] == "Giấy khai sinh"
    assert items[1]["target"] == "new"
    assert items[1]["componentName"] == "Giấy đăng ký kết hôn"
    assert items[1]["documentName"] == "Giấy đăng ký kết hôn"
    assert items[2]["target"] == "new"
    assert items[2]["componentName"] == "Trích lục khai tử"


async def test_trich_luc_attachment_plan_routes_default_existing_rows(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "uy-quyen.pdf", "text": "VĂN BẢN ỦY QUYỀN"},
            {"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN"},
            {"name": "cu-tru.pdf", "text": "GIẤY XÁC NHẬN THÔNG TIN VỀ CƯ TRÚ"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "authorization", "title": "Văn bản ủy quyền"},
                {"index": 1, "type": "identity", "title": "Căn cước công dân"},
                {"index": 2, "type": "residence_proof", "title": "Giấy tờ chứng minh cư trú"},
            ]
        })

    monkeypatch.setattr(trich_luc.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(trich_luc.client, "chat", fake_chat)

    res = await trich_luc.plan_trich_luc_attachments(
        [_file("uy-quyen.pdf"), _file("cccd.pdf"), _file("cu-tru.pdf")],
        {},
        _session(),
    )
    items = res["attachments"]

    assert items[0]["target"] == "existing"
    assert items[0]["componentIndex"] == 2
    assert "Văn bản ủy quyền" in items[0]["componentName"]
    assert items[1]["target"] == "existing"
    assert items[1]["componentIndex"] == 3
    assert "Thẻ căn cước công dân" in items[1]["componentName"]
    assert items[2]["target"] == "existing"
    assert items[2]["componentIndex"] == 4
    assert "chứng minh thông tin về cư trú" in items[2]["componentName"]


def test_trich_luc_procedure_has_attachment_step():
    proc = get_procedure("trich-luc-ks")

    assert proc["hasAttachmentStep"] is True
    assert "Trích lục hộ tịch" in proc["label"]


def test_trich_luc_attachment_prompt_uses_ocr_text_only():
    assert "civil_status_marriage" in SYSTEM_PROMPT
    assert "identity" in SYSTEM_PROMPT
    assert "Không dùng tên file" in SYSTEM_PROMPT

    prompt = build_user_prompt([
        {
            "index": 0,
            "fileName": "chung-nhan-ket-hon.pdf",
            "text": "GIẤY CHỨNG NHẬN KẾT HÔN",
        }
    ])

    assert "ocrText" in prompt
    assert "GIẤY CHỨNG NHẬN KẾT HÔN" in prompt
    assert "chung-nhan-ket-hon.pdf" not in prompt
    assert "fileName" not in prompt

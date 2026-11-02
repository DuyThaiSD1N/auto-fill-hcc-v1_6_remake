import json

from app.pipelines.xet_tuyen_vien_chuc.attach import planner as xet_tuyen_attach
from app.process.schemas import FileItem
from app.services import ocr  # planner import ocr cục bộ trong plan()


def _file(name: str) -> FileItem:
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


async def test_xet_tuyen_vien_chuc_attach_maps_phieu_to_fixed_slot_and_cccd_shares_phieu_slot(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {
                "name": "phieu.pdf",
                "text": "PHIẾU ĐĂNG KÝ DỰ TUYỂN\nMẫu số 01\nNghị định số 85/2023/NĐ-CP\nDự tuyển viên chức",
            },
            {
                "name": "cccd.pdf",
                "text": "CĂN CƯỚC CÔNG DÂN\nSố: 001000000001",
            },
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "phieu_dang_ky_du_tuyen", "title": "Phiếu đăng ký dự tuyển"},
                {"index": 1, "type": "other", "title": "Căn cước công dân"},
            ]
        }, ensure_ascii=False)

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(xet_tuyen_attach.client, "chat", fake_chat)

    res = await xet_tuyen_attach.plan([_file("phieu.pdf"), _file("cccd.pdf")], {}, None)

    items = res["attachments"]
    assert len(items) == 2
    item = items[0]
    assert item["fileName"] == "phieu.pdf"
    assert item["target"] == "fixed-slot"
    assert item["slotIndex"] == 0
    assert item["slotKey"] == "phieu_dang_ky_du_tuyen"
    assert "Phiếu đăng ký dự tuyển" in item["slotName"]
    cccd = items[1]
    assert cccd["fileName"] == "cccd.pdf"
    assert cccd["target"] == "fixed-slot"
    assert cccd["slotIndex"] == 0
    assert cccd["documentName"] == "cccd.pdf"
    assert cccd["detectedType"] == "other"
    assert any("đã đính chung dòng" in err and "cccd.pdf" in err for err in res["errors"])


async def test_xet_tuyen_vien_chuc_attach_rule_fallback_when_llm_fails(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {
                "name": "phieu.pdf",
                "text": "PHIẾU ĐĂNG KÝ DỰ TUYỂN\nMẫu số 01\nDự tuyển viên chức",
            },
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        raise RuntimeError("llm down")

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(xet_tuyen_attach.client, "chat", fake_chat)

    res = await xet_tuyen_attach.plan([_file("phieu.pdf")], {}, None)

    assert len(res["attachments"]) == 1
    assert res["attachments"][0]["slotIndex"] == 0
    assert not any("attachment_agent" in err for err in res["errors"])

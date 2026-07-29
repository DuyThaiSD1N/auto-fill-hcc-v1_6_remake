import json

from app.pipelines.dieu_chinh_huu_tri_xa_hoi.attach import planner
from app.process.schemas import FileItem


def _file(name: str) -> FileItem:
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


async def test_dieu_chinh_huu_tri_attach_maps_van_ban_and_skips_cccd(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {
                "name": "van-ban.pdf",
                "text": (
                    "VĂN BẢN ĐỀ NGHỊ HƯỞNG TRỢ CẤP HƯU TRÍ XÃ HỘI\n"
                    "I. Thông tin người đề nghị trợ cấp hưu trí xã hội"
                ),
            },
            {
                "name": "cccd.pdf",
                "text": "CĂN CƯỚC CÔNG DÂN\nCitizen Identity Card\nSố: 031071000001",
            },
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps(
            {
                "documents": [
                    {"index": 0, "type": "van_ban_de_nghi_huu_tri", "title": "Văn bản đề nghị trợ cấp hưu trí xã hội"},
                    {"index": 1, "type": "other", "title": "Căn cước công dân"},
                ]
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("van-ban.pdf"), _file("cccd.pdf")], {}, None)

    assert len(res["attachments"]) == 1
    item = res["attachments"][0]
    assert item["fileName"] == "van-ban.pdf"
    assert item["target"] == "fixed-slot"
    assert item["slotIndex"] == 0
    assert item["slotKey"] == "van_ban_de_nghi_huu_tri"
    assert "Văn bản đề nghị" in item["slotName"]
    assert any("giấy tờ tùy thân" in err for err in res["errors"])


async def test_dieu_chinh_huu_tri_attach_rule_fallback_when_llm_fails(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {
                "name": "van-ban.pdf",
                "text": (
                    "VĂN BẢN ĐỀ NGHỊ HƯỞNG TRỢ CẤP HƯU TRÍ XÃ HỘI\n"
                    "Mẫu số 01\n"
                    "I. Thông tin người đề nghị trợ cấp hưu trí xã hội"
                ),
            },
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        raise RuntimeError("llm down")

    monkeypatch.setattr("app.services.ocr.ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("van-ban.pdf")], {}, None)

    assert len(res["attachments"]) == 1
    assert res["attachments"][0]["slotKey"] == "van_ban_de_nghi_huu_tri"
    assert any("attachment_agent" in err for err in res["errors"])


def test_dieu_chinh_huu_tri_rule_rejects_explicit_mau_02():
    text = (
        "VĂN BẢN ĐỀ NGHỊ HƯỞNG TRỢ CẤP HƯU TRÍ XÃ HỘI\n"
        "Mẫu số 02\n"
        "I. Thông tin người đề nghị trợ cấp hưu trí xã hội"
    )

    assert planner.detect_slot_key(text) == ""

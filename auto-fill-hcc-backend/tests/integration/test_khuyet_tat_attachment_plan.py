import json

from app.pipelines.khuyet_tat.attach import planner as khuyet_tat_attach
from app.process.schemas import FileItem


def _file(name: str) -> FileItem:
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


async def test_khuyet_tat_attach_maps_three_fixed_slots_and_skips_cccd(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "don.pdf", "text": "ĐƠN ĐỀ NGHỊ XÁC ĐỊNH MỨC ĐỘ KHUYẾT TẬT VÀ CẤP GIẤY XÁC NHẬN KHUYẾT TẬT\nMẫu số 01"},
            {"name": "benh-an.pdf", "text": "TÓM TẮT BỆNH ÁN\nBệnh viện đa khoa\nChẩn đoán và điều trị"},
            {"name": "ket-luan.pdf", "text": "KẾT LUẬN CỦA HỘI ĐỒNG GIÁM ĐỊNH Y KHOA\nKhả năng tự phục vụ, suy giảm khả năng lao động"},
            {"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN\nSố: 012084000160"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "docType": "disability_application_form", "title": "Đơn đề nghị xác định mức độ khuyết tật"},
                {"index": 1, "docType": "disability_related_docs", "title": "Tóm tắt bệnh án"},
                {"index": 2, "docType": "medical_assessment_conclusion", "title": "Kết luận giám định y khoa"},
                {"index": 3, "docType": "other", "title": "Căn cước công dân"},
            ]
        }, ensure_ascii=False)

    monkeypatch.setattr(khuyet_tat_attach.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khuyet_tat_attach.client, "chat", fake_chat)

    res = await khuyet_tat_attach.plan(
        [_file("don.pdf"), _file("benh-an.pdf"), _file("ket-luan.pdf"), _file("cccd.pdf")],
        {},
        {"procedure": "xac-dinh-muc-do-khuyet-tat"},
    )

    items = res["attachments"]
    assert len(items) == 3
    by_file = {item["fileName"]: item for item in items}
    assert by_file["benh-an.pdf"]["target"] == "fixed-slot"
    assert by_file["benh-an.pdf"]["slotIndex"] == 0
    assert by_file["benh-an.pdf"]["slotKey"] == "disability_related_docs"
    assert by_file["ket-luan.pdf"]["slotIndex"] == 1
    assert by_file["ket-luan.pdf"]["slotKey"] == "medical_assessment_conclusion"
    assert by_file["don.pdf"]["slotIndex"] == 3
    assert by_file["don.pdf"]["slotKey"] == "disability_application_form"
    assert "cccd.pdf" not in by_file
    assert any("giấy tờ tùy thân" in err for err in res["errors"])


async def test_khuyet_tat_attach_rule_fallback_when_llm_fails(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "don.pdf", "text": "ĐƠN ĐỀ NGHỊ XÁC ĐỊNH, XÁC ĐỊNH LẠI MỨC ĐỘ KHUYẾT TẬT\nThông tư số 01/2019/TT-BLĐTBXH"},
            {"name": "ra-vien.pdf", "text": "GIẤY RA VIỆN\nBệnh viện\nChẩn đoán, điều trị"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        raise RuntimeError("llm down")

    monkeypatch.setattr(khuyet_tat_attach.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(khuyet_tat_attach.client, "chat", fake_chat)

    res = await khuyet_tat_attach.plan([_file("don.pdf"), _file("ra-vien.pdf")], {}, None)
    by_file = {item["fileName"]: item for item in res["attachments"]}

    assert by_file["don.pdf"]["slotIndex"] == 3
    assert by_file["ra-vien.pdf"]["slotIndex"] == 0
    assert any("attachment_agent" in err for err in res["errors"])

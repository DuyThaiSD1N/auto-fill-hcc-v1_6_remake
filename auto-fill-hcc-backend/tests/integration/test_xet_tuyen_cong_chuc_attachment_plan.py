import json

from app.pipelines.xet_tuyen_cong_chuc.attach import planner as xet_tuyen_attach
from app.process.schemas import FileItem


def _file(name: str) -> FileItem:
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


async def test_xet_tuyen_cong_chuc_attach_maps_phieu_to_fixed_slot_and_skips_cccd(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {
                "name": "mau cong chuc.pdf",
                "text": "PHIẾU ĐĂNG KÝ DỰ TUYỂN\nMẫu số 01\nNghị định số 170/2025/NĐ-CP\nVị trí việc làm dự tuyển",
            },
            {
                "name": "cccd.pdf",
                "text": "CĂN CƯỚC CÔNG DÂN\nSố: 012194003716",
            },
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": []}, ensure_ascii=False)

    monkeypatch.setattr(xet_tuyen_attach.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(xet_tuyen_attach.client, "chat", fake_chat)

    res = await xet_tuyen_attach.plan([_file("mau cong chuc.pdf"), _file("cccd.pdf")], {}, None)

    assert len(res["attachments"]) == 1
    item = res["attachments"][0]
    assert item["fileName"] == "mau cong chuc.pdf"
    assert item["target"] == "fixed-slot"
    assert item["slotKey"] == "phieu_dang_ky_du_tuyen"
    assert item["slotIndex"] == 0
    assert any("tài liệu khác" in err for err in res["errors"])

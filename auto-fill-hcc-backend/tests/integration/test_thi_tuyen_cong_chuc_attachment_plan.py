import json

from app.pipelines.thi_tuyen_cong_chuc.attach import planner as thi_tuyen_attach
from app.process.schemas import FileItem


def _file(name: str) -> FileItem:
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


async def test_thi_tuyen_cong_chuc_attach_maps_phieu_to_fixed_slot_and_cccd_shares_phieu_slot(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {
                "name": "mau cong chuc.pdf",
                "text": "PHIẾU ĐĂNG KÝ THI TUYỂN CÔNG CHỨC\nMẫu số 02\nVị trí việc làm dự tuyển\nCơ quan, tổ chức, đơn vị dự tuyển",
            },
            {
                "name": "cccd.pdf",
                "text": "CĂN CƯỚC CÔNG DÂN\nSố: 001000000001",
            },
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": []}, ensure_ascii=False)

    monkeypatch.setattr(thi_tuyen_attach.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(thi_tuyen_attach.client, "chat", fake_chat)

    res = await thi_tuyen_attach.plan([_file("mau cong chuc.pdf"), _file("cccd.pdf")], {}, None)

    assert len(res["attachments"]) == 2
    item = res["attachments"][0]
    assert item["fileName"] == "mau cong chuc.pdf"
    assert item["target"] == "fixed-slot"
    assert item["slotKey"] == "phieu_dang_ky_du_tuyen"
    assert item["slotIndex"] == 0
    cccd = res["attachments"][1]
    assert cccd["fileName"] == "cccd.pdf"
    assert cccd["target"] == "fixed-slot"
    assert cccd["slotIndex"] == 0
    assert cccd["documentName"] == "cccd.pdf"
    assert cccd["detectedType"] == "other"
    assert any("đã đính chung dòng" in err and "cccd.pdf" in err for err in res["errors"])

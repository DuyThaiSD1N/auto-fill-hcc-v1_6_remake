import json

from app.pipelines.ket_hon_lai.attach import planner as ket_hon_lai
from app.process.schemas import FileItem


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


def _session():
    return {
        "request_id": "req_test",
        "procedure": "dang-ky-lai-ket-hon",
        "fields": [
            {"name": "SoDinhDanh_BenNam", "value": "012086005221"},
            {"name": "SoDinhDanh_BenNu", "value": "012189003303"},
        ],
    }


async def test_ket_hon_lai_attachment_plan_uses_existing_certificate_slot(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "gcn.pdf", "text": "GIẤY CHỨNG NHẬN KẾT HÔN Số: 40/2026"},
            {"name": "nam.pdf", "text": "CĂN CƯỚC CÔNG DÂN Giới tính Sex Nam 012086005221"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 0, "type": "marriage_certificate"},
            {"index": 1, "type": "identity", "side": "nam", "face": "ca_hai"},
        ]})

    monkeypatch.setattr(ket_hon_lai.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(ket_hon_lai.client, "chat", fake_chat)

    res = await ket_hon_lai.plan_ket_hon_lai_attachments(
        [_file("gcn.pdf"), _file("nam.pdf")],
        {},
        _session(),
    )

    cert, cccd = res["attachments"]
    assert cert["target"] == "existing"
    assert cert["componentIndex"] == 2
    assert cert["componentName"] == "Bản sao Giấy chứng nhận kết hôn"
    assert cccd["target"] == "new"
    assert cccd["componentName"] == "CCCD bên nam"


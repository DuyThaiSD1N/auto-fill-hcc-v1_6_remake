import json

from app.pipelines.xac_nhan_tthn.attach import planner as xac_nhan_tthn
from app.process.schemas import FileItem


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


async def test_tthn_attachment_plan_routes_identity_to_new_component(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{"index": 0, "type": "identity", "title": "Căn cước công dân"}]})

    monkeypatch.setattr(xac_nhan_tthn.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(xac_nhan_tthn.client, "chat", fake_chat)

    res = await xac_nhan_tthn.plan_xac_nhan_tthn_attachments([_file("cccd.pdf")], {}, None)
    item = res["attachments"][0]

    assert item["target"] == "new"
    assert item["componentName"] == "Căn cước công dân"
    assert item["documentName"] == "Căn cước công dân"
    assert res["stats"]["llm_latency_ms"] >= 0


async def test_tthn_attachment_plan_routes_condition_documents_to_existing_rows(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "ly-hon.pdf", "text": "Quyết định ly hôn"},
            {"name": "ghi-chu.pdf", "text": "Trích lục ghi chú ly hôn"},
            {"name": "uy-quyen.pdf", "text": "Văn bản ủy quyền"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "divorce_or_death_proof", "title": "Quyết định ly hôn"},
                {"index": 1, "type": "foreign_divorce_note", "title": "Trích lục ghi chú ly hôn"},
                # Cổng mới tách "Văn bản ủy quyền" ra hàng 5 riêng → type authorization.
                {"index": 2, "type": "authorization", "title": "Văn bản ủy quyền"},
            ]
        })

    monkeypatch.setattr(xac_nhan_tthn.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(xac_nhan_tthn.client, "chat", fake_chat)

    res = await xac_nhan_tthn.plan_xac_nhan_tthn_attachments(
        [_file("ly-hon.pdf"), _file("ghi-chu.pdf"), _file("uy-quyen.pdf")],
        {},
        None,
    )
    items = res["attachments"]

    assert items[0]["target"] == "existing"
    assert items[0]["componentIndex"] == 2
    assert "đã có vợ hoặc chồng" in items[0]["componentName"]
    assert items[1]["componentIndex"] == 3
    assert "kết hôn ở nước ngoài" in items[1]["componentName"]
    assert items[2]["componentIndex"] == 5
    assert "Văn bản ủy quyền" in items[2]["componentName"]

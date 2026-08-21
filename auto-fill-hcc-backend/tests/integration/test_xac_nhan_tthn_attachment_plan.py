import json

from app.pipelines.xac_nhan_tthn.attach import planner as xac_nhan_tthn
from app.pipelines.xac_nhan_tthn.attach import prompt
from app.process.schemas import FileItem


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


async def test_tthn_attachment_plan_routes_identity_to_new_component(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        assert json.loads(messages[1]["content"])["ocrText"] == "CĂN CƯỚC CÔNG DÂN"
        return json.dumps({"type": "identity", "title": "Căn cước công dân"})

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
        text = json.loads(messages[1]["content"])["ocrText"]
        if "Quyết định" in text:
            return json.dumps({"type": "divorce_or_death_proof", "title": "Quyết định ly hôn"})
        if "ghi chú" in text:
            return json.dumps({"type": "foreign_divorce_note", "title": "Trích lục ghi chú ly hôn"})
        return json.dumps({
            "type": "previous_marital_status_certificate_or_authorization",
            "title": "Văn bản ủy quyền",
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
    assert items[2]["componentIndex"] == 4
    assert "cấp lại Giấy xác nhận tình trạng hôn nhân" in items[2]["componentName"]


def test_tthn_attachment_prompt_contains_one_ocr_and_no_file_name():
    user_prompt = prompt.build_user_prompt({
        "index": 0,
        "fileName": "image.pdf",
        "text": "TỜ KHAI CẤP GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN",
    })
    payload = json.loads(user_prompt)

    assert payload == {"ocrText": "TỜ KHAI CẤP GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN"}
    assert "fileName" not in user_prompt
    assert "không dùng tên file" in prompt.SYSTEM_PROMPT.lower()


async def test_tthn_duplicate_names_keep_ocr_by_index_and_merge_cccd(monkeypatch):
    declaration_text = """
    TỜ KHAI CẤP GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN
    Giấy tờ tùy thân CCCD số 051205007090
    """
    front_text = """
    CĂN CƯỚC CÔNG DÂN Citizen Identity Card
    Số 051205007090 Họ và tên LÊ HOÀNG QUÝ Ngày sinh 07/07/2005
    """
    back_text = """
    Đặc điểm nhận dạng Personal identification
    IDVNM2050070903051205007090<<9
    """
    prompts: list[str] = []

    async def fake_ocr_per_file(_files):
        return [
            {"name": "image.pdf", "text": declaration_text},
            {"name": "image.pdf", "text": front_text},
            {"name": "image.pdf", "text": back_text},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        text = json.loads(messages[1]["content"])["ocrText"]
        prompts.append(text)
        if "TỜ KHAI" in text:
            return json.dumps({
                "type": "other",
                "title": "Tờ khai bản giấy",
                "documentName": "Tờ khai bản giấy",
            })
        return json.dumps({
            "type": "identity",
            "title": "Căn cước công dân",
            "documentName": "Căn cước công dân",
        })

    monkeypatch.setattr(xac_nhan_tthn.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(xac_nhan_tthn.client, "chat", fake_chat)

    result = await xac_nhan_tthn.plan_xac_nhan_tthn_attachments(
        [_file("image.pdf"), _file("image.pdf"), _file("image.pdf")], {}, None,
    )

    assert len(prompts) == 3
    assert prompts == [
        prompt._truncate_text(declaration_text),
        prompt._truncate_text(front_text),
        prompt._truncate_text(back_text),
    ]
    assert all(sum(marker in text for marker in ("TỜ KHAI", "Citizen Identity", "IDVNM")) == 1
               for text in prompts)

    attachments = result["attachments"]
    assert len(attachments) == 2
    declaration = next(item for item in attachments if not item.get("sourceFileIndexes"))
    identity = next(item for item in attachments if item.get("sourceFileIndexes"))

    assert declaration["fileIndex"] == 0
    assert declaration["documentName"] == "Tờ khai bản giấy"
    assert declaration["target"] == "new"
    assert identity["fileIndex"] == 1
    assert identity["sourceFileIndexes"] == [1, 2]
    assert identity["documentName"] == "Căn cước công dân"
    assert identity["target"] == "new"
    assert [item["fileIndex"] for item in result["extracted"]["classified"]] == [0, 1, 2]


async def test_tthn_one_llm_failure_does_not_drop_other_files(monkeypatch):
    async def fake_ocr_per_file(_files):
        return [
            {"name": "image.pdf", "text": "QUYẾT ĐỊNH LY HÔN"},
            {"name": "image.pdf", "text": "OCR LỖI LLM"},
            {"name": "image.pdf", "text": "VĂN BẢN ỦY QUYỀN"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        text = json.loads(messages[1]["content"])["ocrText"]
        if "LỖI LLM" in text:
            raise RuntimeError("provider timeout")
        if "LY HÔN" in text:
            return json.dumps({"type": "divorce_or_death_proof", "title": "Quyết định ly hôn"})
        return json.dumps({
            "type": "previous_marital_status_certificate_or_authorization",
            "title": "Văn bản ủy quyền",
        })

    monkeypatch.setattr(xac_nhan_tthn.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(xac_nhan_tthn.client, "chat", fake_chat)

    result = await xac_nhan_tthn.plan_xac_nhan_tthn_attachments(
        [_file("image.pdf"), _file("image.pdf"), _file("image.pdf")], {}, None,
    )

    assert [item["type"] for item in result["extracted"]["classified"]] == [
        "divorce_or_death_proof", "other",
        "previous_marital_status_certificate_or_authorization",
    ]
    assert len(result["attachments"]) == 3
    assert any("fileIndex=1" in error and "provider timeout" in error for error in result["errors"])

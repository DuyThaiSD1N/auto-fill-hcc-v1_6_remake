import json

from app.pipelines.trich_luc.attach import planner as trich_luc
from app.pipelines.trich_luc.attach.prompt import SYSTEM_PROMPT, build_user_prompt
from app.process.schemas import FileItem
from app.channels.handfree.procedure_registry import get_procedure


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
        documents = json.loads(messages[1]["content"])["documents"]
        types = [
            ("civil_status_birth", "Giấy khai sinh"),
            ("civil_status_marriage", "Giấy chứng nhận kết hôn"),
            ("civil_status_death", "Trích lục khai tử"),
        ]
        return json.dumps({"documents": [
            {"index": doc["index"], "type": typ, "title": title}
            for doc, (typ, title) in zip(documents, types)
        ]})

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
        documents = json.loads(messages[1]["content"])["documents"]
        types = [
            ("authorization", "Văn bản ủy quyền"),
            ("identity", "Căn cước công dân"),
            ("residence_proof", "Giấy tờ chứng minh cư trú"),
        ]
        return json.dumps({"documents": [
            {"index": doc["index"], "type": typ, "title": title}
            for doc, (typ, title) in zip(documents, types)
        ]})

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

    prompt = build_user_prompt([{
        "index": 0,
        "fileName": "chung-nhan-ket-hon.pdf",
        "text": "GIẤY CHỨNG NHẬN KẾT HÔN",
    }])

    assert "ocrText" in prompt
    assert "GIẤY CHỨNG NHẬN KẾT HÔN" in prompt
    assert "chung-nhan-ket-hon.pdf" not in prompt
    assert "fileName" not in prompt


async def test_duplicate_file_names_keep_ocr_by_index_and_merge_same_person_cccd(monkeypatch):
    front_text = """
    CĂN CƯỚC CÔNG DÂN Citizen Identity Card
    Số 051092008682 Họ và tên PHẠM VĂN HIỂN Ngày sinh 08/08/1992
    """
    back_text = """
    Đặc điểm nhận dạng Personal identification
    IDVNM0920086825051092008682<<1
    """
    declaration_text = "TỜ KHAI CẤP BẢN SAO TRÍCH LỤC HỘ TỊCH"
    prompts: list[list[dict]] = []

    async def fake_ocr_per_file(_files):
        return [
            {"name": "image.jpg", "text": front_text},
            {"name": "image.jpg", "text": back_text},
            {"name": "image.jpg", "text": declaration_text},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        documents = json.loads(messages[1]["content"])["documents"]
        prompts.append(documents)
        classified = []
        for doc in documents:
            if "TỜ KHAI" in doc["ocrText"]:
                classified.append({
                    "index": doc["index"],
                    "type": "paper_declaration",
                    "title": "Tờ khai cấp bản sao trích lục hộ tịch",
                    "documentName": "Tờ khai cấp bản sao trích lục hộ tịch",
                })
            else:
                classified.append({
                    "index": doc["index"],
                    "type": "identity",
                    "title": "Căn cước công dân",
                    "documentName": "Căn cước công dân",
                })
        return json.dumps({"documents": classified})

    monkeypatch.setattr(trich_luc.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(trich_luc.client, "chat", fake_chat)

    result = await trich_luc.plan_trich_luc_attachments(
        [_file("image.jpg"), _file("image.jpg"), _file("image.jpg")],
        {},
        _session(),
    )

    assert len(prompts) == 1
    assert [doc["ocrText"] for doc in prompts[0]] == [
        trich_luc._truncate_text(front_text),
        trich_luc._truncate_text(back_text),
        declaration_text,
    ]
    assert [doc["index"] for doc in prompts[0]] == [0, 1, 2]

    attachments = result["attachments"]
    assert len(attachments) == 2
    identity = next(item for item in attachments if item.get("sourceFileIndexes"))
    declaration = next(item for item in attachments if not item.get("sourceFileIndexes"))

    assert identity["fileIndex"] == 0
    assert identity["sourceFileIndexes"] == [0, 1]
    assert identity["documentName"] == "Căn cước công dân"
    assert identity["target"] == "existing"
    assert identity["componentIndex"] == 3
    assert declaration["fileIndex"] == 2
    assert declaration["documentName"] == "Tờ khai cấp bản sao trích lục hộ tịch"
    assert declaration["target"] == "new"
    assert [item["fileIndex"] for item in result["extracted"]["classified"]] == [0, 1, 2]


async def test_one_attachment_llm_failure_falls_back_all_files_without_retry(monkeypatch):
    async def fake_ocr_per_file(_files):
        return [
            {"name": "image.jpg", "text": "GIẤY KHAI SINH"},
            {"name": "image.jpg", "text": "OCR LỖI LLM"},
            {"name": "image.jpg", "text": "TỜ KHAI CẤP BẢN SAO TRÍCH LỤC HỘ TỊCH"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        documents = json.loads(messages[1]["content"])["documents"]
        assert len(documents) == 3
        raise RuntimeError("provider timeout")

    monkeypatch.setattr(trich_luc.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(trich_luc.client, "chat", fake_chat)

    result = await trich_luc.plan_trich_luc_attachments(
        [_file("image.jpg"), _file("image.jpg"), _file("image.jpg")], {}, _session(),
    )

    assert [item["type"] for item in result["extracted"]["classified"]] == [
        "other", "other", "other",
    ]
    assert len(result["attachments"]) == 3
    assert result["errors"] == ["attachment_agent: provider timeout"]

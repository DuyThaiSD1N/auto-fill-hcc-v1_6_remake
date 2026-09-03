import json

from app.attachments.schemas import AttachmentPlanResp
from app.pipelines.xac_nhan_tthn.attach import planner_v2 as xac_nhan_tthn
from app.pipelines.xac_nhan_tthn.attach import prompt_v2 as prompt
from app.process.schemas import FileItem


def _file(name: str) -> FileItem:
    return FileItem(
        name=name,
        type="application/pdf",
        dataUrl="data:application/pdf;base64,AAA",
        role="doc",
    )


async def test_tthn_classifies_all_files_with_one_llm_request(monkeypatch):
    calls: list[str] = []

    async def fake_ocr_per_file(_files):
        return [
            {"name": "image.pdf", "text": "CĂN CƯỚC CÔNG DÂN Citizen Identity"},
            {"name": "image.pdf", "text": "VĂN BẢN ỦY QUYỀN"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        calls.append(messages[1]["content"])
        return json.dumps({
            "documents": [
                {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "identity"},
                {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "authorization"},
            ]
        })

    monkeypatch.setattr(xac_nhan_tthn.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(xac_nhan_tthn.client, "chat", fake_chat)

    result = await xac_nhan_tthn.plan_xac_nhan_tthn_attachments(
        [_file("image.pdf"), _file("image.pdf")], {}, None,
    )

    assert len(calls) == 1
    assert "CĂN CƯỚC CÔNG DÂN" in calls[0]
    assert "VĂN BẢN ỦY QUYỀN" in calls[0]
    assert "image.pdf" not in calls[0]
    assert result["attachments"][0]["target"] == "new"
    assert result["attachments"][0]["componentName"] == "Căn cước công dân"
    assert result["attachments"][1]["componentIndex"] == 5


async def test_tthn_routes_condition_documents_to_rows_two_through_five(monkeypatch):
    async def fake_ocr_per_file(_files):
        return [
            {"name": "ly-hon.pdf", "text": "QUYẾT ĐỊNH CÔNG NHẬN THUẬN TÌNH LY HÔN"},
            {"name": "ghi-chu.pdf", "text": "TRÍCH LỤC GHI CHÚ LY HÔN Ở NƯỚC NGOÀI"},
            {"name": "giay-cu.pdf", "text": "GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN ĐÃ CẤP"},
            {"name": "uy-quyen.pdf", "text": "VĂN BẢN ỦY QUYỀN"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {
                    "fileIndex": 0, "pageFrom": 1, "pageTo": 1,
                    "type": "divorce_or_death_proof", "documentName": "Quyết định ly hôn",
                },
                {
                    "fileIndex": 1, "pageFrom": 1, "pageTo": 1,
                    "type": "foreign_divorce_note", "documentName": "Trích lục ghi chú ly hôn",
                },
                {
                    "fileIndex": 2, "pageFrom": 1, "pageTo": 1,
                    "type": "previous_marital_status_certificate",
                    "documentName": "Giấy xác nhận tình trạng hôn nhân đã cấp",
                },
                {
                    "fileIndex": 3, "pageFrom": 1, "pageTo": 1,
                    "type": "authorization", "documentName": "Văn bản ủy quyền",
                },
            ]
        })

    monkeypatch.setattr(xac_nhan_tthn.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(xac_nhan_tthn.client, "chat", fake_chat)

    result = await xac_nhan_tthn.plan_xac_nhan_tthn_attachments(
        [_file("ly-hon.pdf"), _file("ghi-chu.pdf"), _file("giay-cu.pdf"), _file("uy-quyen.pdf")],
        {},
        None,
    )
    items = result["attachments"]

    assert [item["componentIndex"] for item in items] == [2, 3, 4, 5]
    assert all(item["target"] == "existing" for item in items)
    assert all(item["componentIndex"] != 1 for item in items)
    assert "đã ly hôn hoặc người vợ/chồng đã chết" in items[0]["componentName"]
    assert "cấp lại Giấy xác nhận tình trạng hôn nhân" in items[2]["componentName"]
    assert "Văn bản ủy quyền" in items[3]["componentName"]


async def test_tthn_routes_death_event_proof_to_row_two(monkeypatch):
    async def fake_ocr_per_file(_files):
        return [{"name": "khai-tu.pdf", "text": "TRÍCH LỤC KHAI TỬ\nĐã chết ngày 01/01/2026"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [{
                "fileIndex": 0,
                "pageFrom": 1,
                "pageTo": 1,
                "type": "divorce_or_death_proof",
                "documentName": "Trích lục khai tử",
            }]
        })

    monkeypatch.setattr(xac_nhan_tthn.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(xac_nhan_tthn.client, "chat", fake_chat)

    result = await xac_nhan_tthn.plan_xac_nhan_tthn_attachments([_file("khai-tu.pdf")], {}, None)

    assert result["attachments"][0]["componentIndex"] == 2
    assert result["attachments"][0]["documentName"] == "Trích lục khai tử"


async def test_tthn_merges_all_identity_files_and_keeps_paper_declaration_new(monkeypatch):
    declaration_text = "TỜ KHAI CẤP GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN"
    back_one = "Đặc điểm nhận dạng IDVNM2050070903051205007090<<9"
    front_one = "CĂN CƯỚC CÔNG DÂN Citizen Identity Số 051205007090 Họ tên NGUYỄN A"
    front_two = "CĂN CƯỚC CÔNG DÂN Citizen Identity Số 068190002468 Họ tên NGUYỄN B"

    async def fake_ocr_per_file(_files):
        return [
            {"name": "image.pdf", "text": declaration_text},
            {"name": "image.pdf", "text": back_one},
            {"name": "image.pdf", "text": front_one},
            {"name": "image.pdf", "text": front_two},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {
                    "fileIndex": 0, "pageFrom": 1, "pageTo": 1,
                    "type": "paper_declaration", "documentName": "Tờ khai bản giấy",
                },
                {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "identity"},
                {"fileIndex": 2, "pageFrom": 1, "pageTo": 1, "type": "identity"},
                {"fileIndex": 3, "pageFrom": 1, "pageTo": 1, "type": "identity"},
            ]
        })

    monkeypatch.setattr(xac_nhan_tthn.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(xac_nhan_tthn.client, "chat", fake_chat)

    result = await xac_nhan_tthn.plan_xac_nhan_tthn_attachments(
        [_file("image.pdf") for _ in range(4)], {}, None,
    )

    assert len(result["attachments"]) == 3
    declaration, identity, second_identity = result["attachments"]
    assert declaration["documentName"] == "Tờ khai bản giấy"
    assert declaration["target"] == "new"
    assert identity["documentName"] == "Căn cước công dân"
    assert identity["target"] == "new"
    assert identity["sourceSegments"] == [
        {"fileIndex": 2, "pageIndexes": None},
        {"fileIndex": 1, "pageIndexes": None},
    ]
    assert second_identity["fileIndex"] == 3
    assert second_identity["target"] == "new"
    assert "fileIndex=0 · image.pdf" in result["ocr_text"]
    assert "fileIndex=3 · image.pdf" in result["ocr_text"]


async def test_tthn_splits_mixed_pdf_and_merges_identity_pages(monkeypatch):
    async def fake_ocr_per_file(_files):
        return [{
            "name": "mixed.pdf",
            "text": (
                "───── Trang 1/4 ─────\nTỜ KHAI CẤP GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN\n"
                "───── Trang 2/4 ─────\nCĂN CƯỚC CÔNG DÂN Citizen Identity Số 051205007090\n"
                "───── Trang 3/4 ─────\nĐặc điểm nhận dạng IDVNM2050070903051205007090<<9\n"
                "───── Trang 4/4 ─────\nTRÍCH LỤC KHAI TỬ"
            ),
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {
                    "fileIndex": 0, "pageFrom": 1, "pageTo": 1,
                    "type": "paper_declaration", "documentName": "Tờ khai bản giấy",
                },
                {"fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "identity"},
                {"fileIndex": 0, "pageFrom": 3, "pageTo": 3, "type": "identity"},
                {
                    "fileIndex": 0, "pageFrom": 4, "pageTo": 4,
                    "type": "divorce_or_death_proof", "documentName": "Trích lục khai tử",
                },
            ]
        })

    monkeypatch.setattr(xac_nhan_tthn.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(xac_nhan_tthn.client, "chat", fake_chat)

    result = await xac_nhan_tthn.plan_xac_nhan_tthn_attachments([_file("mixed.pdf")], {}, None)
    serialized = AttachmentPlanResp.model_validate(result).model_dump(mode="json")

    assert len(serialized["attachments"]) == 3
    declaration, identity, death = serialized["attachments"]
    assert declaration["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0]}]
    assert identity["sourceSegments"] == [
        {"fileIndex": 0, "pageIndexes": [1]},
        {"fileIndex": 0, "pageIndexes": [2]},
    ]
    assert death["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [3]}]
    assert death["componentIndex"] == 2
    assert [(item["pageFrom"], item["pageTo"]) for item in result["extracted"]["classified"]] == [
        (1, 1), (2, 2), (3, 3), (4, 4),
    ]


async def test_tthn_splits_cccd_from_citizen_information_check_result(monkeypatch):
    async def fake_ocr_per_file(_files):
        return [{
            "name": "mixed.pdf",
            "text": (
                "───── Trang 1/3 ─────\nCĂN CƯỚC CÔNG DÂN\nCitizen Identity Card\n"
                "Số 024151003879\n"
                "───── Trang 2/3 ─────\nKẾT QUẢ KIỂM TRA THÔNG TIN CÔNG DÂN\n"
                "II. Thông tin khai thác cơ sở dữ liệu quốc gia về dân cư\n"
                "───── Trang 3/3 ─────\n13. Địa chỉ thường trú của công dân\n"
                "19. Thông tin chủ hộ của công dân"
            ),
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        assert "KẾT QUẢ KIỂM TRA THÔNG TIN CÔNG DÂN" in messages[1]["content"]
        return json.dumps({
            "documents": [
                {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "identity"},
                {
                    "fileIndex": 0,
                    "pageFrom": 2,
                    "pageTo": 3,
                    "type": "other",
                    "title": "Kết quả kiểm tra thông tin công dân",
                    "documentName": "Kết quả kiểm tra thông tin công dân",
                },
            ]
        })

    monkeypatch.setattr(xac_nhan_tthn.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(xac_nhan_tthn.client, "chat", fake_chat)

    result = await xac_nhan_tthn.plan_xac_nhan_tthn_attachments([_file("mixed.pdf")], {}, None)
    serialized = AttachmentPlanResp.model_validate(result).model_dump(mode="json")

    assert len(serialized["attachments"]) == 2
    identity, citizen_result = serialized["attachments"]
    assert identity["documentName"] == "Căn cước công dân"
    assert identity["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0]}]
    assert citizen_result["documentName"] == "Kết quả kiểm tra thông tin công dân"
    assert citizen_result["componentName"] == "Kết quả kiểm tra thông tin công dân"
    assert citizen_result["target"] == "new"
    assert citizen_result["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [1, 2]}]


async def test_tthn_batch_llm_failure_keeps_every_file_as_new_component(monkeypatch):
    async def fake_ocr_per_file(_files):
        return [
            {"name": "image.pdf", "text": "OCR FILE 1"},
            {"name": "image.pdf", "text": "OCR FILE 2"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        raise RuntimeError("provider timeout")

    monkeypatch.setattr(xac_nhan_tthn.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(xac_nhan_tthn.client, "chat", fake_chat)

    result = await xac_nhan_tthn.plan_xac_nhan_tthn_attachments(
        [_file("image.pdf"), _file("image.pdf")], {}, None,
    )

    assert len(result["attachments"]) == 2
    assert all(item["target"] == "new" for item in result["attachments"])
    assert [item["type"] for item in result["extracted"]["classified"]] == ["other", "other"]
    assert any("provider timeout" in error for error in result["errors"])


def test_tthn_prompt_contains_all_ocr_and_excludes_file_names():
    user_prompt = prompt.build_user_prompt([
        {
            "fileIndex": 0,
            "fileName": "cccd-mat-truoc.pdf",
            "pages": [{"pageNumber": 1, "ocrText": "CĂN CƯỚC CÔNG DÂN"}],
        },
        {
            "fileIndex": 1,
            "fileName": "uy-quyen.pdf",
            "pages": [{"pageNumber": 1, "ocrText": "VĂN BẢN ỦY QUYỀN"}],
        },
    ])

    assert "CĂN CƯỚC CÔNG DÂN" in user_prompt
    assert "VĂN BẢN ỦY QUYỀN" in user_prompt
    assert "cccd-mat-truoc.pdf" not in user_prompt
    assert "uy-quyen.pdf" not in user_prompt
    assert "previous_marital_status_certificate" in prompt.SYSTEM_PROMPT
    assert "paper_declaration" in prompt.SYSTEM_PROMPT
    assert "tiêu đề chính rõ ràng" in prompt.SYSTEM_PROMPT
    assert "KẾT QUẢ KIỂM TRA THÔNG TIN CÔNG DÂN" not in prompt.SYSTEM_PROMPT

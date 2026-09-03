import json

from app.attachments.schemas import AttachmentPlanResp
from app.pipelines.xac_nhan_tthn.attach import planner as dispatcher
from app.pipelines.xac_nhan_tthn.attach.dinh_kem_khong_tach import planner as preserve_planner
from app.pipelines.xac_nhan_tthn.attach.dinh_kem_khong_tach import prompt as preserve_prompt
from app.pipelines.xac_nhan_tthn.attach.dinh_kem_tach import planner as xac_nhan_tthn
from app.pipelines.xac_nhan_tthn.attach.dinh_kem_tach import prompt
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


async def test_tthn_dispatcher_defaults_to_preserve_and_only_boolean_true_splits(monkeypatch):
    calls: list[str] = []

    async def fake_preserve(files, options, session=None):
        calls.append("preserve")
        return {"attachments": []}

    async def fake_split(files, options, session=None):
        calls.append("split")
        return {"attachments": []}

    monkeypatch.setattr(dispatcher, "plan_without_split", fake_preserve)
    monkeypatch.setattr(dispatcher, "plan_with_split", fake_split)

    await dispatcher.plan([_file("a.pdf")], {}, {})
    await dispatcher.plan([_file("a.pdf")], {"splitDocuments": False}, {})
    await dispatcher.plan([_file("a.pdf")], {"splitDocuments": "true"}, {})
    await dispatcher.plan([_file("a.pdf")], {"splitDocuments": True}, {})

    assert calls == ["preserve", "preserve", "preserve", "split"]


async def test_tthn_preserve_mode_keeps_mixed_pdf_as_one_attachment(monkeypatch):
    async def fake_ocr_per_file(_files):
        return [{
            "name": "mixed.pdf",
            "text": (
                "TỜ KHAI CẤP GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN\n"
                "TRÍCH LỤC KHAI TỬ"
            ),
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        assert "mixed.pdf" not in messages[1]["content"]
        return json.dumps({
            "documents": [{
                "fileIndex": 0,
                "type": "divorce_or_death_proof",
                "documentName": "Tờ khai bản giấy và Trích lục khai tử",
                "subjectName": "",
            }]
        })

    monkeypatch.setattr(preserve_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(preserve_planner.client, "chat", fake_chat)

    result = await dispatcher.plan([_file("mixed.pdf")], {"splitDocuments": False}, {})
    item = result["attachments"][0]

    assert len(result["attachments"]) == 1
    assert item["componentIndex"] == 2
    assert item["documentName"] == "Hồ sơ xác nhận tình trạng hôn nhân"
    assert "sourceSegments" not in item
    assert "sourceFileIndexes" not in item
    assert result["extracted"]["attachmentMode"] == "preserve_files"


async def test_tthn_preserve_mode_uses_short_general_name_for_mixed_other_file(monkeypatch):
    async def fake_ocr_per_file(_files):
        return [{
            "name": "mixed.pdf",
            "text": (
                "───── Trang 1/3 ─────\n"
                "TỜ KHAI CẤP GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN\n"
                "───── Trang 2/3 ─────\n"
                "CĂN CƯỚC CÔNG DÂN\nCitizen Identity Card\n"
                "───── Trang 3/3 ─────\nGIẤY CHỨNG NHẬN KẾT HÔN"
            ),
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [{
                "fileIndex": 0,
                # Tái hiện provider chỉ nhìn trang đầu và nhận nhầm cả bộ hồ sơ là một Tờ khai.
                "type": "paper_declaration",
                "documentName": "Tờ khai bản giấy",
                "subjectName": "",
            }]
        })

    monkeypatch.setattr(preserve_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(preserve_planner.client, "chat", fake_chat)

    result = await dispatcher.plan([_file("mixed.pdf")], {}, {})

    assert result["attachments"][0]["documentName"] == "Hồ sơ xác nhận tình trạng hôn nhân"
    assert result["attachments"][0]["componentName"] == "Hồ sơ xác nhận tình trạng hôn nhân"
    assert result["extracted"]["classified"][0]["type"] == "other"
    assert "Hồ sơ xác nhận tình trạng hôn nhân" in preserve_prompt.SYSTEM_PROMPT
    assert "ghép tối đa ba tiêu đề" not in preserve_prompt.SYSTEM_PROMPT


async def test_tthn_preserve_mode_does_not_treat_declaration_notes_as_separate_document(monkeypatch):
    async def fake_ocr_per_file(_files):
        return [{
            "name": "declaration.pdf",
            "text": (
                "───── Trang 1/2 ─────\n"
                "TỜ KHAI CẤP GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN\n"
                "───── Trang 2/2 ─────\nCHÚ THÍCH\n"
                "Ghi số căn cước công dân. Nếu đang có vợ chồng thì ghi Giấy chứng nhận kết hôn số."
            ),
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [{
                "fileIndex": 0,
                "type": "paper_declaration",
                "documentName": "Tờ khai bản giấy",
                "subjectName": "",
            }]
        })

    monkeypatch.setattr(preserve_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(preserve_planner.client, "chat", fake_chat)

    result = await dispatcher.plan([_file("declaration.pdf")], {}, {})

    assert result["attachments"][0]["documentName"] == "Tờ khai bản giấy"
    assert result["extracted"]["classified"][0]["type"] == "paper_declaration"


async def test_tthn_preserve_mode_merges_only_same_subject_cccd_faces(monkeypatch):
    async def fake_ocr_per_file(_files):
        return [
            {
                "name": "front.pdf",
                "text": "CĂN CƯỚC CÔNG DÂN Citizen Identity Số 051205007090 Họ tên NGUYỄN VĂN A",
            },
            {
                "name": "back.pdf",
                "text": "Đặc điểm nhận dạng IDVNM2050070903051205007090<<9",
            },
            {
                "name": "other.pdf",
                "text": "CĂN CƯỚC CÔNG DÂN Citizen Identity Số 068190002468 Họ tên TRẦN THỊ B",
            },
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {
                    "fileIndex": 0, "type": "identity",
                    "documentName": "Căn cước công dân", "subjectName": "NGUYỄN VĂN A",
                },
                {
                    "fileIndex": 1, "type": "identity",
                    "documentName": "Căn cước công dân", "subjectName": "",
                },
                {
                    "fileIndex": 2, "type": "identity",
                    "documentName": "Căn cước công dân", "subjectName": "TRẦN THỊ B",
                },
            ]
        })

    monkeypatch.setattr(preserve_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(preserve_planner.client, "chat", fake_chat)

    result = await dispatcher.plan(
        [_file("front.pdf"), _file("back.pdf"), _file("other.pdf")],
        {},
        {},
    )

    assert len(result["attachments"]) == 2
    first, second = result["attachments"]
    assert first["sourceFileIndexes"] == [0, 1]
    assert first["documentName"] == "CCCD NGUYỄN VĂN A"
    assert second["fileIndex"] == 2
    assert second["documentName"] == "CCCD TRẦN THỊ B"


async def test_tthn_preserve_mode_keeps_multiple_cccds_inside_one_original_file(monkeypatch):
    async def fake_ocr_per_file(_files):
        return [{
            "name": "identities.pdf",
            "text": (
                "CĂN CƯỚC CÔNG DÂN Số 051205007090 Họ tên NGUYỄN VĂN A\n"
                "CĂN CƯỚC CÔNG DÂN Số 068190002468 Họ tên TRẦN THỊ B"
            ),
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [{
                "fileIndex": 0,
                "type": "identity",
                "documentName": "Căn cước công dân",
                # Dù provider chọn nhầm một tên, planner phải thấy nhiều số định danh và giữ tên chung.
                "subjectName": "NGUYỄN VĂN A",
            }]
        })

    monkeypatch.setattr(preserve_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(preserve_planner.client, "chat", fake_chat)

    result = await dispatcher.plan([_file("identities.pdf")], {}, {})

    assert len(result["attachments"]) == 1
    assert result["attachments"][0]["documentName"] == "Căn cước công dân"
    assert "sourceSegments" not in result["attachments"][0]
    assert "sourceFileIndexes" not in result["attachments"][0]


async def test_tthn_split_mode_ignores_blank_page_and_names_cccd_subject(monkeypatch):
    async def fake_ocr_per_file(_files):
        return [{
            "name": "mixed.pdf",
            "text": (
                "───── Trang 1/4 ─────\nCĂN CƯỚC CÔNG DÂN Số 051205007090\n"
                "───── Trang 2/4 ─────\nĐặc điểm nhận dạng IDVNM2050070903051205007090<<9\n"
                "───── Trang 3/4 ─────\n\n"
                "───── Trang 4/4 ─────\nTRÍCH LỤC KHAI TỬ"
            ),
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {
                    "fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "identity",
                    "documentName": "Căn cước công dân", "subjectName": "NGUYỄN VĂN A",
                },
                {
                    "fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "identity",
                    "documentName": "Căn cước công dân", "subjectName": "",
                },
                {
                    "fileIndex": 0, "pageFrom": 3, "pageTo": 3, "type": "blank_page",
                    "documentName": "Trang trắng", "subjectName": "",
                },
                {
                    "fileIndex": 0, "pageFrom": 4, "pageTo": 4,
                    "type": "divorce_or_death_proof", "documentName": "Trích lục khai tử",
                    "subjectName": "",
                },
            ]
        })

    monkeypatch.setattr(xac_nhan_tthn.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(xac_nhan_tthn.client, "chat", fake_chat)

    result = await dispatcher.plan([_file("mixed.pdf")], {"splitDocuments": True}, {})
    serialized = AttachmentPlanResp.model_validate(result).model_dump(mode="json")

    assert len(serialized["attachments"]) == 2
    identity, death = serialized["attachments"]
    assert identity["documentName"] == "CCCD NGUYỄN VĂN A"
    assert identity["sourceSegments"] == [
        {"fileIndex": 0, "pageIndexes": [0]},
        {"fileIndex": 0, "pageIndexes": [1]},
    ]
    assert death["componentIndex"] == 2
    assert result["extracted"]["attachmentMode"] == "split_documents"
    assert any(item["type"] == "blank_page" and item["target"] == "ignored" for item in result["extracted"]["classified"])


def test_tthn_prompts_lock_file_indexes_pages_and_document_boundaries():
    preserve_user_prompt = preserve_prompt.build_user_prompt([
        {"fileIndex": 4, "ocrText": "TỜ KHAI CẤP GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN"},
        {"fileIndex": 7, "ocrText": "CĂN CƯỚC CÔNG DÂN"},
    ])
    assert "FILE_INDEX BẮT BUỘC: [4, 7]" in preserve_user_prompt
    assert "GIỐNG HỆT tập fileIndex đầu vào" in preserve_prompt.SYSTEM_PROMPT
    assert "không mượn loại, tên hoặc chủ thể" in preserve_prompt.SYSTEM_PROMPT
    assert "giấy tờ chỉ được kể" in preserve_prompt.SYSTEM_PROMPT
    assert '"Đặc điểm nhận dạng" không đủ' in preserve_prompt.SYSTEM_PROMPT
    assert "Tài liệu xác nhận tình trạng hôn nhân" in preserve_prompt.SYSTEM_PROMPT

    split_user_prompt = prompt.build_user_prompt([{
        "fileIndex": 4,
        "pageCount": 2,
        "pageBoundariesAvailable": True,
        "pages": [
            {"pageNumber": 1, "ocrText": "QUYẾT ĐỊNH LY HÔN"},
            {"pageNumber": 2, "ocrText": "Trang tiếp nối"},
        ],
    }])
    assert 'FILE_INDEX VÀ TRANG BẮT BUỘC: [{"fileIndex": 4, "pages": [1, 2]}]' in split_user_prompt
    assert "trang nội dung tiếp nối" in prompt.SYSTEM_PROMPT
    assert "KHÔNG tạo thành tài liệu mới" in prompt.SYSTEM_PROMPT
    assert 'Riêng cụm "Đặc điểm nhận dạng" không đủ' in prompt.SYSTEM_PROMPT
    assert "Tài liệu xác nhận tình trạng hôn nhân" in prompt.SYSTEM_PROMPT


def test_tthn_preserve_identity_fallback_requires_strong_back_evidence():
    assert preserve_planner._has_identity_evidence("Đặc điểm nhận dạng: sẹo nhỏ") is False
    assert preserve_planner._rule_doc_type("Đặc điểm nhận dạng: sẹo nhỏ") == "other"

    strong_back = "Đặc điểm nhận dạng; Ngón trỏ trái; CỤC TRƯỞNG CỤC CẢNH SÁT"
    assert preserve_planner._has_identity_evidence(strong_back) is True
    assert preserve_planner._rule_doc_type(strong_back) == "identity"
    assert preserve_planner._has_identity_evidence("IDVNM0680063689") is True


def test_tthn_preserve_declaration_references_are_not_independent_documents():
    text = (
        "TỜ KHAI CẤP GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN\n"
        "Giấy tờ tùy thân: Căn cước công dân số 012345678901\n"
        "Tình trạng hôn nhân: chồng đã chết theo Trích lục khai tử số 01"
    )

    assert preserve_planner._rule_doc_type(text) == "paper_declaration"
    assert preserve_planner._is_declaration_bundle(text) is False


async def test_tthn_does_not_reuse_one_existing_component_for_two_documents(monkeypatch):
    async def fake_ocr_per_file(_files):
        return [
            {"name": "ly-hon.pdf", "text": "QUYẾT ĐỊNH LY HÔN"},
            {"name": "khai-tu.pdf", "text": "TRÍCH LỤC KHAI TỬ"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {
                "fileIndex": 0, "pageFrom": 1, "pageTo": 1,
                "type": "divorce_or_death_proof", "documentName": "Quyết định ly hôn",
            },
            {
                "fileIndex": 1, "pageFrom": 1, "pageTo": 1,
                "type": "divorce_or_death_proof", "documentName": "Trích lục khai tử",
            },
        ]})

    monkeypatch.setattr(xac_nhan_tthn.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(xac_nhan_tthn.client, "chat", fake_chat)

    result = await dispatcher.plan(
        [_file("ly-hon.pdf"), _file("khai-tu.pdf")], {"splitDocuments": True}, {},
    )
    first, second = result["attachments"]

    assert first["target"] == "existing"
    assert first["componentIndex"] == 2
    assert second["target"] == "new"
    assert second["componentIndex"] is None
    assert second["componentName"] == "Trích lục khai tử"

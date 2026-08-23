import json

from app.pipelines.khai_sinh_dang_ky_lai.attach import planner as dang_ky_lai_khai_sinh
from app.pipelines.khai_sinh_dang_ky_lai.attach.prompt import SYSTEM_PROMPT, build_user_prompt
from app.process.schemas import FileItem
from app.procedures.registry import get_procedure


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


def _session():
    return {
        "request_id": "req_dang_ky_lai_ks_test",
        "procedure": "khai-sinh-dang-ky-lai",
        "fields": [
            {"name": "HoTenKS", "value": "VÀNG A PHỈNH"},
            {"name": "SoDinhDanhCha", "value": "040203015844"},
            {"name": "SoDinhDanhMe", "value": "012193000851"},
        ],
    }


async def test_dang_ky_lai_khai_sinh_attachment_plan_routes_default_components(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "gks-ban-sao.pdf", "text": "BẢN SAO GIẤY KHAI SINH"},
            {"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN"},
            {"name": "uy-quyen.pdf", "text": "VĂN BẢN ỦY QUYỀN"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "birth_certificate_copy", "title": "Giấy khai sinh bản sao"},
                {"index": 1, "type": "personal_supporting_document", "title": "Căn cước công dân"},
                {"index": 2, "type": "authorization", "title": "Văn bản ủy quyền"},
            ]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    res = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("gks-ban-sao.pdf"), _file("cccd.pdf"), _file("uy-quyen.pdf")],
        {},
        _session(),
    )
    items = res["attachments"]

    assert items[0]["target"] == "existing"
    assert items[0]["componentIndex"] == 2
    assert "Bản sao Giấy khai sinh" in items[0]["componentName"]

    assert items[1]["target"] == "existing"
    assert items[1]["componentIndex"] == 3
    assert "Thẻ căn cước công dân" in items[1]["componentName"]

    assert items[2]["target"] == "existing"
    assert items[2]["componentIndex"] == 5
    assert "Văn bản ủy quyền" in items[2]["componentName"]


async def test_dang_ky_lai_khai_sinh_attachment_plan_adds_extra_personal_documents(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN"},
            {"name": "hoc-ba.pdf", "text": "HỌC BẠ"},
            {"name": "bang-tot-nghiep.pdf", "text": "BẰNG TỐT NGHIỆP"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "personal_supporting_document", "title": "Căn cước công dân"},
                {"index": 1, "type": "personal_supporting_document", "title": "Học bạ"},
                {"index": 2, "type": "personal_supporting_document", "title": "Bằng tốt nghiệp"},
            ]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    res = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("cccd.pdf"), _file("hoc-ba.pdf"), _file("bang-tot-nghiep.pdf")],
        {},
        _session(),
    )
    items = res["attachments"]

    assert items[0]["target"] == "existing"
    assert items[0]["componentIndex"] == 3

    assert items[1]["target"] == "new"
    assert items[1]["componentIndex"] is None
    assert items[1]["componentName"] == "Học bạ"

    assert items[2]["target"] == "new"
    assert items[2]["componentIndex"] is None
    assert items[2]["componentName"] == "Bằng tốt nghiệp"


async def test_dang_ky_lai_khai_sinh_attachment_plan_adds_paper_declaration(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": "to-khai-giay.pdf", "text": "TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "paper_declaration", "title": "Tờ khai đăng ký lại khai sinh"},
            ]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    res = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("to-khai-giay.pdf")],
        {},
        _session(),
    )
    item = res["attachments"][0]

    assert item["target"] == "new"
    assert item["componentIndex"] is None
    assert item["documentName"] == "Tờ khai bản giấy"
    assert item["componentName"] == "Tờ khai bản giấy"


async def test_dang_ky_lai_khai_sinh_attachment_plan_adds_commitment_statement(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "gks-ban-sao.pdf", "text": "BẢN SAO GIẤY KHAI SINH"},
            {
                "name": "ban-cam-doan.pdf",
                "text": "BẢN CAM ĐOAN Tôi cam đoan giấy khai sinh bản chính đã bị mất",
            },
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "birth_certificate_copy", "title": "Giấy khai sinh bản sao"},
                {"index": 1, "type": "commitment_statement", "title": "Bản cam đoan"},
            ]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    res = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("gks-ban-sao.pdf"), _file("ban-cam-doan.pdf")],
        {},
        _session(),
    )
    items = res["attachments"]

    assert items[0]["target"] == "existing"
    assert items[0]["componentIndex"] == 2
    assert "Bản sao Giấy khai sinh" in items[0]["componentName"]

    assert items[1]["target"] == "new"
    assert items[1]["componentIndex"] is None
    assert items[1]["needsAddComponent"] is True
    assert items[1]["documentName"] == "Bản cam đoan"
    assert items[1]["componentName"] == "Bản cam đoan"
    assert items[1]["detectedType"] == "Bản cam đoan"


def test_dang_ky_lai_khai_sinh_procedure_has_attachment_step():
    proc = get_procedure("khai-sinh-dang-ky-lai")

    assert proc["hasAttachmentStep"] is True


def test_dang_ky_lai_khai_sinh_attachment_prompt_requires_llm_enum():
    assert "commitment_statement" in SYSTEM_PROMPT
    assert "Bản cam đoan" in SYSTEM_PROMPT
    assert 'type":"commitment_statement"' in SYSTEM_PROMPT
    assert 'type":"birth_certificate_copy","title":"Bản cam đoan"' in SYSTEM_PROMPT
    assert "Chỉ phân loại theo OCR_TEXT" in SYSTEM_PROMPT
    assert "Không dùng tên file" in SYSTEM_PROMPT
    assert "Trích lục khai tử" in SYSTEM_PROMPT
    assert "KHÔNG phải giấy tờ thay thế" in SYSTEM_PROMPT
    assert "Ví dụ sai" in SYSTEM_PROMPT


async def test_dang_ky_lai_khai_sinh_death_extract_never_uses_birth_component(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "trich-luc.pdf",
            "text": (
                "THÀNH PHỐ ĐÀ NẴNG\nTRÍCH LỤC KHAI TỬ (BẢN SAO)\n"
                "Họ, chữ đệm, tên: HÀ VĂN SẮT\nĐã chết ngày 02/02/2022"
            ),
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [{
                "fileIndex": 0,
                "pageFrom": 1,
                "pageTo": 1,
                "type": "birth_certificate_copy",
                "title": "Trích lục khai tử",
                "documentName": "Trích lục khai tử",
            }]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    res = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("trich-luc.pdf")],
        {},
        _session(),
    )

    item = res["attachments"][0]
    classified = res["extracted"]["classified"][0]
    assert item["documentName"] == "Trích lục khai tử"
    assert item["target"] == "new"
    assert item["componentIndex"] is None
    assert item["needsAddComponent"] is True
    assert classified["type"] == "other"


def test_dang_ky_lai_khai_sinh_attachment_user_prompt_uses_ocr_text_only():
    prompt = build_user_prompt([
        {
            "index": 0,
            "fileName": "ban-cam-doan.pdf",
            "text": "BẢN CAM ĐOAN Tôi cam đoan giấy khai sinh bản chính đã bị mất",
        }
    ])

    assert "ocrText" in prompt
    assert "BẢN CAM ĐOAN" in prompt
    assert "ban-cam-doan.pdf" not in prompt
    assert "fileName" not in prompt


async def test_dang_ky_lai_khai_sinh_duplicate_file_names_keep_separate_ocr(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {
                "name": "image.pdf",
                "text": "CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số 012345678901",
            },
            {
                "name": "image.pdf",
                "text": "BẢN CAM ĐOAN Tôi cam đoan thông tin đăng ký lại khai sinh là đúng",
            },
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        user_prompt = messages[-1]["content"]
        assert "012345678901" in user_prompt
        assert "BẢN CAM ĐOAN" in user_prompt
        assert user_prompt.index("012345678901") < user_prompt.index("BẢN CAM ĐOAN")
        return json.dumps({
            "documents": [
                {
                    "fileIndex": 0,
                    "pageFrom": 1,
                    "pageTo": 1,
                    "type": "identity",
                    "documentName": "Căn cước công dân",
                },
                {
                    "fileIndex": 1,
                    "pageFrom": 1,
                    "pageTo": 1,
                    "type": "commitment_statement",
                    "documentName": "Bản cam đoan",
                },
            ]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    result = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("image.pdf"), _file("image.pdf")], {}, _session()
    )

    assert [item["fileIndex"] for item in result["extracted"]["classified"]] == [0, 1]
    assert result["extracted"]["classified"][0]["type"] == "identity"
    assert result["extracted"]["classified"][1]["type"] == "commitment_statement"
    assert "fileIndex=0 · image.pdf" in result["ocr_text"]
    assert "fileIndex=1 · image.pdf" in result["ocr_text"]


async def test_dang_ky_lai_khai_sinh_splits_mixed_pdf_by_page(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "ho-so-gop.pdf",
            "text": """
───── Trang 1/3 ─────
CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số 012345678901
───── Trang 2/3 ─────
GIẤY KHAI SINH Họ và tên NGUYỄN VĂN A
───── Trang 3/3 ─────
PHẦN GHI CHÚ NHỮNG THÔNG TIN THAY ĐỔI SAU NÀY
""",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {
                    "fileIndex": 0,
                    "pageFrom": 1,
                    "pageTo": 1,
                    "type": "identity",
                    "documentName": "Căn cước công dân",
                },
                {
                    "fileIndex": 0,
                    "pageFrom": 2,
                    "pageTo": 3,
                    "type": "birth_certificate_copy",
                    "documentName": "Giấy khai sinh",
                },
            ]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    result = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("ho-so-gop.pdf")], {}, _session()
    )
    by_index = {item["componentIndex"]: item for item in result["attachments"]}

    assert by_index[3]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0]}]
    assert by_index[2]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [1, 2]}]
    assert [(item["pageFrom"], item["pageTo"]) for item in result["extracted"]["classified"]] == [
        (1, 1),
        (2, 3),
    ]


async def test_dang_ky_lai_khai_sinh_merges_all_cccds_without_mixing_faces(monkeypatch):
    cccd_a = "012345678901"
    cccd_b = "109876543210"

    async def fake_ocr_per_file(files):
        return [
            {"name": "image.pdf", "text": f"Citizen Identity Card Số {cccd_a} Họ và tên NGUYỄN A"},
            {"name": "image.pdf", "text": f"Citizen Identity Card Số {cccd_b} Họ và tên NGUYỄN B"},
            {"name": "image.pdf", "text": f"Đặc điểm nhận dạng IDVNM{cccd_a}"},
            {"name": "image.pdf", "text": f"Đặc điểm nhận dạng IDVNM{cccd_b}"},
        ]

    calls = 0

    async def fake_chat(messages, max_tokens, enable_thinking):
        nonlocal calls
        calls += 1
        return json.dumps({
            "documents": [
                {
                    "fileIndex": index,
                    "pageFrom": 1,
                    "pageTo": 1,
                    "type": "identity",
                    "documentName": "Căn cước công dân",
                }
                for index in range(4)
            ]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    result = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("image.pdf") for _ in range(4)], {}, _session()
    )

    assert calls == 1
    assert len(result["attachments"]) == 1
    merged = result["attachments"][0]
    assert merged["componentIndex"] == 3
    assert merged["documentName"] == "Căn cước công dân"
    assert [segment["fileIndex"] for segment in merged["sourceSegments"]] == [0, 2, 1, 3]


async def test_dang_ky_lai_khai_sinh_cccd_has_priority_over_earlier_supporting_document(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "hoc-ba.pdf", "text": "HỌC BẠ Họ tên NGUYỄN VĂN A"},
            {
                "name": "cccd.pdf",
                "text": "CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số 012345678901",
            },
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {
                    "fileIndex": 0,
                    "pageFrom": 1,
                    "pageTo": 1,
                    "type": "personal_supporting_document",
                    "documentName": "Học bạ",
                },
                {
                    "fileIndex": 1,
                    "pageFrom": 1,
                    "pageTo": 1,
                    "type": "identity",
                    "documentName": "Căn cước công dân",
                },
            ]
        })

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    result = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("hoc-ba.pdf"), _file("cccd.pdf")], {}, _session()
    )

    hoc_ba = next(item for item in result["attachments"] if item["documentName"] == "Học bạ")
    cccd = next(item for item in result["attachments"] if item["documentName"] == "Căn cước công dân")
    assert hoc_ba["target"] == "new"
    assert cccd["target"] == "existing"
    assert cccd["componentIndex"] == 3


async def test_dang_ky_lai_khai_sinh_llm_failure_keeps_every_file(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "image.pdf", "text": "Nội dung chưa xác định A"},
            {"name": "image.pdf", "text": "Nội dung chưa xác định B"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(dang_ky_lai_khai_sinh.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(dang_ky_lai_khai_sinh.client, "chat", fake_chat)

    result = await dang_ky_lai_khai_sinh.plan_dang_ky_lai_khai_sinh_attachments(
        [_file("image.pdf"), _file("image.pdf")], {}, _session()
    )

    assert len(result["attachments"]) == 2
    assert len(result["extracted"]["classified"]) == 2
    assert any("attachment_agent" in error for error in result["errors"])

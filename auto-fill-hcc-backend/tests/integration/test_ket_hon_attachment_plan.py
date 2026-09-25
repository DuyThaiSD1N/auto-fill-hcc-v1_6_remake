import base64
import json

import fitz

from app.pipelines.ket_hon.attach import planner as ket_hon_dispatcher
from app.pipelines.ket_hon.attach.dinh_kem_khong_tach import planner as ket_hon_preserve
from app.pipelines.ket_hon.attach.dinh_kem_tach import planner as ket_hon
from app.pipelines.xac_nhan_tthn.attach.nghia_hung import with_account_attach_options
from app.process.schemas import FileItem


def _file(name: str, mime: str = "application/pdf", data_url: str | None = None) -> FileItem:
    return FileItem(
        name=name,
        type=mime,
        dataUrl=data_url or f"data:{mime};base64,AAA",
        role="doc",
    )


def _pdf_file(name: str, pages: int) -> FileItem:
    document = fitz.open()
    try:
        for _ in range(pages):
            document.new_page(width=595, height=842)
        payload = base64.b64encode(document.tobytes()).decode("ascii")
    finally:
        document.close()
    return _file(name, data_url=f"data:application/pdf;base64,{payload}")


def _attachment_context(index: int = 2, name: str = "Giấy tờ tùy thân của hai bên") -> dict:
    return {
        "attachmentContext": {
            "components": [
                {"index": 1, "componentName": "Mẫu hộ tịch điện tử", "hasFile": False},
                {"index": index, "componentName": name, "hasFile": False},
            ]
        }
    }


def test_ket_hon_prompts_lock_file_indexes_pages_and_document_boundaries():
    preserve_system = ket_hon_preserve.SYSTEM_PROMPT
    split_system = ket_hon.SYSTEM_PROMPT

    for prompt in (preserve_system, split_system):
        assert "tập fileIndex output" in prompt
        assert "không dịch kết quả của file sau lên" in prompt
        assert "chỉ được nhắc trong" in prompt
        assert "không tự trở thành identity" in prompt
        assert '"Tài liệu đính kèm"' in prompt

    assert '"Hồ sơ đăng ký kết hôn"' in preserve_system
    assert '"Tờ khai và bản cam đoan"' in preserve_system
    assert "OCR rác không đủ để kết luận identity" in preserve_system

    preserve_user = ket_hon_preserve.build_user_prompt([
        {"fileIndex": 0, "ocrText": "TỜ KHAI ĐĂNG KÝ KẾT HÔN"},
        {"fileIndex": 1, "ocrText": "BẢN CAM ĐOAN"},
    ])
    assert "FILE_INDEX BẮT BUỘC TRẢ ĐỦ, KHÔNG LỆCH: [0, 1]" in preserve_user

    split_user = ket_hon.build_user_prompt([
        {
            "fileIndex": 0,
            "pageCount": 2,
            "pages": [
                {"pageNumber": 1, "ocrText": "Mặt trước CCCD"},
                {"pageNumber": 2, "ocrText": "Mặt sau CCCD"},
            ],
        },
        {"fileIndex": 1, "pageCount": 1, "pages": [{"pageNumber": 1, "ocrText": "Tờ khai"}]},
    ])
    assert "FILE_INDEX BẮT BUỘC TRẢ ĐỦ, KHÔNG LỆCH: [0, 1]" in split_user
    assert '"fileIndex": 0, "pageNumbers": [1, 2]' in split_user
    assert '"fileIndex": 1, "pageNumbers": [1]' in split_user


async def test_ket_hon_uses_one_batch_prompt_and_keeps_duplicate_file_names_by_index(monkeypatch):
    calls = []

    async def fake_ocr_per_file(files):
        return [
            {"name": "image.pdf", "text": "CĂN CƯỚC CÔNG DÂN NAM-ID 040203015844"},
            {"name": "image.pdf", "text": "CĂN CƯỚC CÔNG DÂN NU-ID 012193000851"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        calls.append(messages)
        prompt = messages[1]["content"]
        assert "NAM-ID" in prompt
        assert "NU-ID" in prompt
        assert "image.pdf" not in prompt
        return json.dumps({"documents": [
            {
                "fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "identity",
                "subjectName": "VŨ ĐÌNH THIẾT",
            },
            {
                "fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "identity",
                "subjectName": "PHẠM NGỌC THỦY",
            },
        ]})

    monkeypatch.setattr(ket_hon.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(ket_hon.client, "chat", fake_chat)

    options = _attachment_context(4, "Hộ chiếu hoặc Thẻ căn cước của hai bên")
    result = await ket_hon.plan_ket_hon_attachments(
        [_file("image.pdf"), _file("image.pdf")], options, {"request_id": "req_test"},
    )

    assert len(calls) == 1
    assert len(result["attachments"]) == 2
    item = result["attachments"][0]
    assert item["documentName"] == "CCCD VŨ ĐÌNH THIẾT"
    assert item["target"] == "existing"
    assert item["componentIndex"] == 4
    assert item["componentName"] == "Hộ chiếu hoặc Thẻ căn cước của hai bên"
    assert "sourceSegments" not in item
    assert result["attachments"][1]["target"] == "new"
    assert result["attachments"][1]["fileIndex"] == 1
    assert result["attachments"][1]["documentName"] == "CCCD PHẠM NGỌC THỦY"
    assert result["attachments"][1]["componentName"] == "CCCD PHẠM NGỌC THỦY"


async def test_ket_hon_merges_four_identity_faces_by_person_and_front_before_back(monkeypatch):
    ocr_texts = [
        "ĐẶC ĐIỂM NHẬN DẠNG IDVNM 040203015844",
        "CĂN CƯỚC CÔNG DÂN Số 012193000851",
        "CĂN CƯỚC CÔNG DÂN Số 040203015844",
        "ĐẶC ĐIỂM NHẬN DẠNG IDVNM 012193000851",
    ]

    async def fake_ocr_per_file(files):
        return [{"name": file["name"], "text": ocr_texts[index]} for index, file in enumerate(files)]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "identity", "subjectName": ""},
            {
                "fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "identity",
                "subjectName": "PHẠM NGỌC THỦY",
            },
            {
                "fileIndex": 2, "pageFrom": 1, "pageTo": 1, "type": "identity",
                "subjectName": "VŨ ĐÌNH THIẾT",
            },
            {"fileIndex": 3, "pageFrom": 1, "pageTo": 1, "type": "identity", "subjectName": ""},
        ]})

    monkeypatch.setattr(ket_hon.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(ket_hon.client, "chat", fake_chat)

    result = await ket_hon.plan_ket_hon_attachments(
        [
            _file("nam-sau.jpg", "image/jpeg"),
            _file("nu-truoc.jpg", "image/jpeg"),
            _file("nam-truoc.jpg", "image/jpeg"),
            _file("nu-sau.jpg", "image/jpeg"),
        ],
        _attachment_context(),
        {},
    )

    assert len(result["attachments"]) == 2
    assert result["attachments"][0]["sourceSegments"] == [
        {"fileIndex": 2, "pageIndexes": None},
        {"fileIndex": 0, "pageIndexes": None},
    ]
    assert result["attachments"][1]["sourceSegments"] == [
        {"fileIndex": 1, "pageIndexes": None},
        {"fileIndex": 3, "pageIndexes": None},
    ]
    assert result["attachments"][0]["target"] == "existing"
    assert result["attachments"][1]["target"] == "new"
    assert [item["documentName"] for item in result["attachments"]] == [
        "CCCD VŨ ĐÌNH THIẾT",
        "CCCD PHẠM NGỌC THỦY",
    ]


async def test_ket_hon_splits_mixed_pdf_and_routes_non_identity_as_new_components(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "mixed.pdf",
            "text": """
───── Trang 1/3 ─────
CĂN CƯỚC CÔNG DÂN Số 040203015844
───── Trang 2/3 ─────
TỜ KHAI ĐĂNG KÝ KẾT HÔN
───── Trang 3/3 ─────
BẢN CAM ĐOAN
""",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {
                "fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "identity",
                "subjectName": "VŨ ĐÌNH THIẾT",
            },
            {"fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "marriage_declaration"},
            {"fileIndex": 0, "pageFrom": 3, "pageTo": 3, "type": "commitment"},
        ]})

    monkeypatch.setattr(ket_hon.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(ket_hon.client, "chat", fake_chat)

    result = await ket_hon.plan_ket_hon_attachments(
        [_pdf_file("mixed.pdf", 3)], _attachment_context(), {},
    )

    assert [item["documentName"] for item in result["attachments"]] == [
        "CCCD VŨ ĐÌNH THIẾT",
        "Tờ khai đăng ký kết hôn",
        "Bản cam đoan",
    ]
    assert result["attachments"][0]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0]}]
    assert result["attachments"][1]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [1]}]
    assert result["attachments"][2]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [2]}]
    assert result["attachments"][0]["target"] == "existing"
    assert all(item["target"] == "new" for item in result["attachments"][1:])


async def test_ket_hon_keeps_specific_other_names_and_deduplicates(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "a.pdf", "text": "QUYẾT ĐỊNH LY HÔN"},
            {"name": "b.pdf", "text": "QUYẾT ĐỊNH LY HÔN"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {
                "fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "other",
                "documentName": "Quyết định ly hôn",
            },
            {
                "fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "other",
                "documentName": "Quyết định ly hôn",
            },
        ]})

    monkeypatch.setattr(ket_hon.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(ket_hon.client, "chat", fake_chat)

    result = await ket_hon.plan_ket_hon_attachments([_file("a.pdf"), _file("b.pdf")], {}, {})

    assert [item["documentName"] for item in result["attachments"]] == [
        "Quyết định ly hôn",
        "Quyết định ly hôn 2",
    ]
    assert all(item["target"] == "new" for item in result["attachments"])


async def test_ket_hon_llm_failure_does_not_turn_divorce_document_into_identity(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": "ly-hon.pdf", "text": "QUYẾT ĐỊNH LY HÔN"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(ket_hon.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(ket_hon.client, "chat", fake_chat)

    result = await ket_hon.plan_ket_hon_attachments([_file("ly-hon.pdf")], {}, {})

    assert len(result["attachments"]) == 1
    assert result["attachments"][0]["documentName"] == "Quyết định ly hôn"
    assert result["attachments"][0]["target"] == "new"
    assert result["attachments"][0]["componentIndex"] is None
    assert any("attachment_agent" in error for error in result["errors"])


async def test_ket_hon_preserve_ocr_noise_is_not_identity(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "scan.pdf",
            "text": "Đặc điểm nhận dạng: 3D 7cm 12cm 18cm 24cm 30cm 36cm",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(ket_hon_preserve.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(ket_hon_preserve.client, "chat", fake_chat)

    result = await ket_hon_dispatcher.plan([_file("scan.pdf")], {}, {})

    item = result["attachments"][0]
    assert item["documentName"] == "Tài liệu đính kèm"
    assert item["target"] == "new"
    assert item["componentIndex"] is None
    assert result["extracted"]["classified"][0]["type"] == "other"


async def test_ket_hon_preserve_uses_common_name_for_mixed_marriage_dossier(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "ho-so.pdf",
            "text": "TỜ KHAI ĐĂNG KÝ KẾT HÔN\nGIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{
            "fileIndex": 0,
            "type": "other",
            "documentName": "Hồ sơ đăng ký kết hôn",
            "subjectName": "",
        }]})

    monkeypatch.setattr(ket_hon_preserve.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(ket_hon_preserve.client, "chat", fake_chat)

    result = await ket_hon_dispatcher.plan([_file("ho-so.pdf")], {}, {})

    item = result["attachments"][0]
    assert item["documentName"] == "Hồ sơ đăng ký kết hôn"
    assert item["componentName"] == "Hồ sơ đăng ký kết hôn"
    assert item["target"] == "new"


async def test_ket_hon_defaults_to_preserve_and_only_true_enables_split(monkeypatch):
    calls = []

    async def fake_preserve(files, options, session=None):
        calls.append(("preserve", options))
        return {"attachments": [], "extracted": {}, "stats": {}, "errors": []}

    async def fake_split(files, options, session=None):
        calls.append(("split", options))
        return {"attachments": [], "extracted": {}, "stats": {}, "errors": []}

    monkeypatch.setattr(ket_hon_dispatcher, "plan_without_split", fake_preserve)
    monkeypatch.setattr(ket_hon_dispatcher, "plan_with_split", fake_split)

    await ket_hon_dispatcher.plan([_file("a.pdf")], {}, {})
    await ket_hon_dispatcher.plan([_file("a.pdf")], {"splitDocuments": False}, {})
    await ket_hon_dispatcher.plan([_file("a.pdf")], {"splitDocuments": "true"}, {})
    await ket_hon_dispatcher.plan([_file("a.pdf")], {"splitDocuments": True}, {})

    assert [name for name, _ in calls] == ["preserve", "preserve", "preserve", "split"]


async def test_ket_hon_preserve_classifies_whole_mixed_pdf_as_one_attachment(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "mixed.pdf",
            "text": """
───── Trang 1/3 ─────
TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH
───── Trang 2/3 ─────
GIẤY CAM ĐOAN
───── Trang 3/3 ─────
Nội dung tiếp theo của giấy cam đoan
""",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        prompt = messages[1]["content"]
        assert "pageFrom" not in prompt
        assert "mixed.pdf" not in prompt
        system_prompt = messages[0]["content"]
        assert "Tiêu đề OCR là nguồn duy nhất của documentName" in system_prompt
        assert "Tờ khai đăng ký lại khai sinh và Giấy cam đoan" not in system_prompt
        return json.dumps({"documents": [{
            "fileIndex": 0,
            "type": "other",
            "documentName": "Tờ khai đăng ký lại khai sinh và Giấy cam đoan",
        }]})

    monkeypatch.setattr(ket_hon_preserve.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(ket_hon_preserve.client, "chat", fake_chat)

    result = await ket_hon_dispatcher.plan([_pdf_file("mixed.pdf", 3)], {}, {})

    assert result["extracted"]["attachmentMode"] == "preserve_files"
    assert len(result["attachments"]) == 1
    assert result["attachments"][0]["fileIndex"] == 0
    assert result["attachments"][0]["documentName"] == "Tờ khai đăng ký lại khai sinh và Giấy cam đoan"
    assert "sourceSegments" not in result["attachments"][0]
    assert "sourceFileIndexes" not in result["attachments"][0]


async def test_ket_hon_preserve_merges_only_same_subject_identity_faces(monkeypatch):
    ocr_texts = [
        "CĂN CƯỚC CÔNG DÂN Số 040203015844",
        "ĐẶC ĐIỂM NHẬN DẠNG IDVNM 040203015844",
        "CĂN CƯỚC CÔNG DÂN Số 012193000851",
        "ĐẶC ĐIỂM NHẬN DẠNG IDVNM 012193000851",
    ]

    async def fake_ocr_per_file(files):
        return [{"name": file["name"], "text": ocr_texts[index]} for index, file in enumerate(files)]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {
                "fileIndex": 0, "type": "identity", "documentName": "Căn cước công dân",
                "subjectName": "VŨ ĐÌNH THIẾT",
            },
            {
                "fileIndex": 1, "type": "identity", "documentName": "Căn cước công dân",
                "subjectName": "",
            },
            {
                "fileIndex": 2, "type": "identity", "documentName": "Căn cước công dân",
                "subjectName": "PHẠM NGỌC THỦY",
            },
            {
                "fileIndex": 3, "type": "identity", "documentName": "Căn cước công dân",
                "subjectName": "",
            },
        ]})

    monkeypatch.setattr(ket_hon_preserve.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(ket_hon_preserve.client, "chat", fake_chat)

    result = await ket_hon_dispatcher.plan(
        [_file("a.jpg", "image/jpeg"), _file("b.jpg", "image/jpeg"),
         _file("c.jpg", "image/jpeg"), _file("d.jpg", "image/jpeg")],
        {"splitDocuments": False, **_attachment_context()},
        {},
    )

    assert len(result["attachments"]) == 2
    assert result["attachments"][0]["sourceFileIndexes"] == [0, 1]
    assert result["attachments"][1]["sourceFileIndexes"] == [2, 3]
    assert [item["documentName"] for item in result["attachments"]] == [
        "CCCD VŨ ĐÌNH THIẾT",
        "CCCD PHẠM NGỌC THỦY",
    ]
    assert result["attachments"][0]["target"] == "existing"
    assert result["attachments"][1]["target"] == "new"


async def test_ket_hon_preserve_keeps_generic_name_for_many_cccds_in_one_original_file(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "danh-sach-cccd.pdf",
            "text": """
CĂN CƯỚC CÔNG DÂN Số 037162011511 Họ và tên NGÔ THỊ HỒNG THÊU
CĂN CƯỚC CÔNG DÂN Số 037058009458 Họ và tên VŨ HUY HOÀN
CĂN CƯỚC CÔNG DÂN Số 037091015133 Họ và tên VŨ HUY HÒA
""",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        # Dù model lỡ trả tên người đầu tiên, một file nguyên bản có nhiều số CCCD vẫn phải giữ tên chung.
        assert "Nhiều CCCD của" in messages[0]["content"]
        return json.dumps({"documents": [{
            "fileIndex": 0,
            "type": "identity",
            "documentName": "Căn cước công dân",
            "subjectName": "NGÔ THỊ HỒNG THÊU",
        }]})

    monkeypatch.setattr(ket_hon_preserve.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(ket_hon_preserve.client, "chat", fake_chat)

    result = await ket_hon_dispatcher.plan(
        [_pdf_file("danh-sach-cccd.pdf", 6)],
        {"splitDocuments": False, **_attachment_context()},
        {},
    )

    assert len(result["attachments"]) == 1
    assert result["attachments"][0]["documentName"] == "Căn cước công dân"
    assert result["attachments"][0]["target"] == "existing"
    assert result["attachments"][0]["componentIndex"] == 2
    assert result["extracted"]["classified"][0]["type"] == "identity"
    assert "sourceSegments" not in result["attachments"][0]


async def test_ket_hon_split_names_each_cccd_subject_in_one_original_file(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "hai-cccd.pdf",
            "text": """
───── Trang 1/4 ─────
CĂN CƯỚC CÔNG DÂN Số 040203015844 Họ và tên VŨ ĐÌNH THIẾT
───── Trang 2/4 ─────
ĐẶC ĐIỂM NHẬN DẠNG IDVNM 040203015844
───── Trang 3/4 ─────
CĂN CƯỚC CÔNG DÂN Số 012193000851 Họ và tên PHẠM NGỌC THỦY
───── Trang 4/4 ─────
ĐẶC ĐIỂM NHẬN DẠNG IDVNM 012193000851
""",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {
                "fileIndex": 0, "pageFrom": 1, "pageTo": 2, "type": "identity",
                "documentName": "Căn cước công dân", "subjectName": "VŨ ĐÌNH THIẾT",
            },
            {
                "fileIndex": 0, "pageFrom": 3, "pageTo": 4, "type": "identity",
                "documentName": "Căn cước công dân", "subjectName": "PHẠM NGỌC THỦY",
            },
        ]})

    monkeypatch.setattr(ket_hon.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(ket_hon.client, "chat", fake_chat)

    result = await ket_hon_dispatcher.plan(
        [_pdf_file("hai-cccd.pdf", 4)],
        {"splitDocuments": True, **_attachment_context()},
        {},
    )

    assert [item["documentName"] for item in result["attachments"]] == [
        "CCCD VŨ ĐÌNH THIẾT",
        "CCCD PHẠM NGỌC THỦY",
    ]
    assert result["attachments"][0]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0, 1]}]
    assert result["attachments"][1]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [2, 3]}]


async def test_ket_hon_split_drops_only_llm_blank_page(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "mixed.pdf",
            "text": """
───── Trang 1/3 ─────
CĂN CƯỚC CÔNG DÂN Số 040203015844
───── Trang 2/3 ─────

───── Trang 3/3 ─────
TỜ KHAI ĐĂNG KÝ KẾT HÔN
""",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "identity"},
            {"fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "blank_page"},
            {"fileIndex": 0, "pageFrom": 3, "pageTo": 3, "type": "marriage_declaration"},
        ]})

    monkeypatch.setattr(ket_hon.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(ket_hon.client, "chat", fake_chat)

    result = await ket_hon_dispatcher.plan(
        [_pdf_file("mixed.pdf", 3)], {"splitDocuments": True, **_attachment_context()}, {},
    )

    assert result["extracted"]["attachmentMode"] == "split_documents"
    assert [item["documentName"] for item in result["attachments"]] == [
        "Căn cước công dân",
        "Tờ khai đăng ký kết hôn",
    ]
    blank = next(item for item in result["extracted"]["classified"] if item["type"] == "blank_page")
    assert blank["target"] == "ignored"


_NGHIA_HUNG_USER = {"tinh": "Tỉnh Ninh Bình", "xa": "Xã Nghĩa Hưng"}


def test_ket_hon_nghia_hung_flag_is_set_by_account_only():
    options = with_account_attach_options({}, _NGHIA_HUNG_USER, "ket-hon")
    assert options["omitPaperDeclaration"] is True
    # Client không tự bật được cho xã khác; thủ tục kết hôn khác chưa áp dụng.
    other_ward = {"tinh": "Tỉnh Ninh Bình", "xa": "Xã Nghĩa Hưng Đông"}
    assert "omitPaperDeclaration" not in with_account_attach_options(
        {"omitPaperDeclaration": True}, other_ward, "ket-hon",
    )
    assert "omitPaperDeclaration" not in with_account_attach_options(
        {}, _NGHIA_HUNG_USER, "ket-hon-nuoc-ngoai",
    )


async def test_ket_hon_preserve_nghia_hung_drops_declaration_and_trims_bundle(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "to-khai.pdf", "text": "TỜ KHAI ĐĂNG KÝ KẾT HÔN\nBên nữ Bên nam"},
            {
                "name": "ho-so.pdf",
                "text": """
───── Trang 1/3 ─────
TỜ KHAI ĐĂNG KÝ KẾT HÔN
Kính gửi: UBND xã
───── Trang 2/3 ─────
Chúng tôi cam đoan những lời khai trên đây là đúng sự thật
Làm tại xã, ngày 01 tháng 01 năm 2026
Bên nữ Bên nam
───── Trang 3/3 ─────
GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN
""",
            },
            {"name": "cccd.jpg", "text": "CĂN CƯỚC CÔNG DÂN\nSố 001234567890\nHọ và tên NGUYỄN VĂN A"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"fileIndex": 0, "type": "marriage_declaration", "documentName": "Tờ khai đăng ký kết hôn"},
            {"fileIndex": 1, "type": "other", "documentName": "Hồ sơ đăng ký kết hôn"},
            {"fileIndex": 2, "type": "identity", "subjectName": "NGUYỄN VĂN A"},
        ]})

    monkeypatch.setattr(ket_hon_preserve.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(ket_hon_preserve.client, "chat", fake_chat)
    files = [_file("to-khai.pdf"), _pdf_file("ho-so.pdf", 3), _file("cccd.jpg", "image/jpeg")]

    result = await ket_hon_dispatcher.plan(
        files, with_account_attach_options(_attachment_context(), _NGHIA_HUNG_USER, "ket-hon"), {},
    )

    by_file = {item["fileIndex"]: item for item in result["attachments"]}
    assert set(by_file) == {1, 2}
    assert by_file[1]["documentName"] == "Giấy tờ đăng ký kết hôn"
    assert by_file[1]["sourceSegments"] == [{"fileIndex": 1, "pageIndexes": [2]}]
    assert by_file[2]["target"] == "existing"
    ignored = [item for item in result["extracted"]["classified"] if item["target"] == "ignored"]
    assert [item["fileIndex"] for item in ignored] == [0]
    assert any("bỏ trang 1, 2 của ho-so.pdf" in error for error in result["errors"])

    # Tài khoản khác: giữ nguyên hành vi cũ, Tờ khai vẫn đính.
    result = await ket_hon_dispatcher.plan(files, _attachment_context(), {})
    assert [item["fileIndex"] for item in result["attachments"]] == [0, 1, 2]
    assert all("sourceSegments" not in item for item in result["attachments"])


async def test_ket_hon_split_nghia_hung_drops_only_declaration_segment(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "mixed.pdf",
            "text": """
───── Trang 1/3 ─────
CĂN CƯỚC CÔNG DÂN Số 001234567890
───── Trang 2/3 ─────
TỜ KHAI ĐĂNG KÝ KẾT HÔN
───── Trang 3/3 ─────
BẢN CAM ĐOAN
""",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "identity", "subjectName": "NGUYỄN VĂN A"},
            {"fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "marriage_declaration"},
            {"fileIndex": 0, "pageFrom": 3, "pageTo": 3, "type": "commitment"},
        ]})

    monkeypatch.setattr(ket_hon.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(ket_hon.client, "chat", fake_chat)
    options = with_account_attach_options(
        {**_attachment_context(), "splitDocuments": True}, _NGHIA_HUNG_USER, "ket-hon",
    )

    result = await ket_hon_dispatcher.plan([_pdf_file("mixed.pdf", 3)], options, {})

    assert [item["documentName"] for item in result["attachments"]] == [
        "CCCD NGUYỄN VĂN A",
        "Bản cam đoan",
    ]
    ignored = [item for item in result["extracted"]["classified"] if item["target"] == "ignored"]
    assert [(item["pageFrom"], item["type"]) for item in ignored] == [(2, "marriage_declaration")]

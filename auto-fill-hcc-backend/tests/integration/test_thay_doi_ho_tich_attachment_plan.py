"""Plan đính kèm bước 3 cho thủ tục thay đổi/cải chính hộ tịch."""

import base64
import json

import fitz

from app.pipelines.thay_doi_ho_tich.attach import planner
from app.pipelines.thay_doi_ho_tich.attach.dinh_kem_khong_tach import planner as preserve_planner
from app.pipelines.thay_doi_ho_tich.attach.dinh_kem_tach import planner as split_planner
from app.process.schemas import FileItem
from app.procedures.registry import get_procedure


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


def _context() -> dict:
    return {
        "attachmentContext": {
            "components": [
                {"index": 1, "componentName": "Mẫu hộ tịch điện tử", "hasFile": True},
                {
                    "index": 4,
                    "componentName": (
                        "Giấy tờ liên quan đến việc thay đổi, cải chính, bổ sung thông tin hộ tịch, "
                        "xác định lại dân tộc"
                    ),
                    "hasFile": False,
                },
                {"index": 6, "componentName": "Văn bản ủy quyền theo quy định", "hasFile": False},
            ]
        }
    }


def _split_context() -> dict:
    return {**_context(), "splitDocuments": True}


async def test_routes_supporting_evidence_authorization_and_identity(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "tlkh.pdf", "text": "TRÍCH LỤC GHI CHÚ KẾT HÔN"},
            {"name": "uyquyen.pdf", "text": "GIẤY ỦY QUYỀN"},
            {"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN\nCITIZEN IDENTITY CARD"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "supporting_evidence", "documentName": "Trích lục kết hôn"},
            {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "authorization", "documentName": "Văn bản ủy quyền"},
            {"fileIndex": 2, "pageFrom": 1, "pageTo": 1, "type": "identity", "documentName": "Căn cước công dân"},
        ]})

    monkeypatch.setattr(split_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(split_planner.client, "chat", fake_chat)

    result = await planner.plan_thay_doi_ho_tich_attachments(
        [_file("tlkh.pdf"), _file("uyquyen.pdf"), _file("cccd.pdf")], _split_context(), {"request_id": "r1"},
    )

    assert [item["componentIndex"] for item in result["attachments"]] == [4, 6, None]
    assert [item["target"] for item in result["attachments"]] == ["existing", "existing", "new"]
    assert result["attachments"][0]["componentName"].startswith("Giấy tờ liên quan")
    assert result["attachments"][2]["documentName"] == "Căn cước công dân"


async def test_uses_one_batch_and_preserves_duplicate_filenames_by_index(monkeypatch):
    calls = []

    async def fake_ocr_per_file(files):
        return [
            {"name": "image.pdf", "text": "GIẤY KHAI SINH SỐ 01"},
            {"name": "image.pdf", "text": "HỌC BẠ SỐ 02"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        calls.append(messages)
        prompt = messages[1]["content"]
        assert "GIẤY KHAI SINH SỐ 01" in prompt
        assert "HỌC BẠ SỐ 02" in prompt
        assert "image.pdf" not in prompt
        return json.dumps({"documents": [
            {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "supporting_evidence", "documentName": "Giấy khai sinh"},
            {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "supporting_evidence", "documentName": "Học bạ"},
        ]})

    monkeypatch.setattr(split_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(split_planner.client, "chat", fake_chat)

    result = await planner.plan_thay_doi_ho_tich_attachments(
        [_file("image.pdf"), _file("image.pdf")], _split_context(), {},
    )

    assert len(calls) == 1
    assert [item["documentName"] for item in result["attachments"]] == ["Giấy khai sinh", "Học bạ"]
    assert [item["fileIndex"] for item in result["attachments"]] == [0, 1]
    assert [item["target"] for item in result["attachments"]] == ["existing", "new"]
    assert [item["componentIndex"] for item in result["attachments"]] == [4, None]


async def test_merges_all_identity_people_and_keeps_front_back_order(monkeypatch):
    texts = [
        "ĐẶC ĐIỂM NHẬN DẠNG IDVNM 040203015844",
        "CĂN CƯỚC CÔNG DÂN Số 012193000851",
        "CĂN CƯỚC CÔNG DÂN Số 040203015844",
        "ĐẶC ĐIỂM NHẬN DẠNG IDVNM 012193000851",
    ]

    async def fake_ocr_per_file(files):
        return [{"name": file["name"], "text": texts[index]} for index, file in enumerate(files)]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"fileIndex": index, "pageFrom": 1, "pageTo": 1, "type": "identity"}
            for index in range(4)
        ]})

    monkeypatch.setattr(split_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(split_planner.client, "chat", fake_chat)

    result = await planner.plan_thay_doi_ho_tich_attachments(
        [
            _file("a-sau.jpg", "image/jpeg"),
            _file("b-truoc.jpg", "image/jpeg"),
            _file("a-truoc.jpg", "image/jpeg"),
            _file("b-sau.jpg", "image/jpeg"),
        ],
        {"splitDocuments": True},
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


async def test_splits_mixed_pdf_and_does_not_use_eform_row_for_paper_declaration(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "mixed.pdf",
            "text": """
───── Trang 1/4 ─────
CĂN CƯỚC CÔNG DÂN Số 040203015844
───── Trang 2/4 ─────
TỜ KHAI THAY ĐỔI CẢI CHÍNH HỘ TỊCH
───── Trang 3/4 ─────
GIẤY KHAI SINH
───── Trang 4/4 ─────
VĂN BẢN ỦY QUYỀN
""",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "identity"},
            {"fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "paper_declaration"},
            {"fileIndex": 0, "pageFrom": 3, "pageTo": 3, "type": "supporting_evidence", "documentName": "Giấy khai sinh"},
            {"fileIndex": 0, "pageFrom": 4, "pageTo": 4, "type": "authorization", "documentName": "Văn bản ủy quyền"},
        ]})

    monkeypatch.setattr(split_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(split_planner.client, "chat", fake_chat)

    result = await planner.plan_thay_doi_ho_tich_attachments(
        [_pdf_file("mixed.pdf", 4)], _split_context(), {},
    )

    assert [item["documentName"] for item in result["attachments"]] == [
        "Căn cước công dân",
        "Tờ khai cải chính hộ tịch bản giấy",
        "Giấy khai sinh",
        "Văn bản ủy quyền",
    ]
    assert [item["sourceSegments"] for item in result["attachments"]] == [
        [{"fileIndex": 0, "pageIndexes": [0]}],
        [{"fileIndex": 0, "pageIndexes": [1]}],
        [{"fileIndex": 0, "pageIndexes": [2]}],
        [{"fileIndex": 0, "pageIndexes": [3]}],
    ]
    assert [item["target"] for item in result["attachments"]] == [
        "new", "new", "existing", "existing",
    ]


async def test_llm_failure_keeps_documents_without_semantic_keyword_fallback(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "khai-sinh.pdf", "text": "GIẤY KHAI SINH"},
            {"name": "uy-quyen.pdf", "text": "VĂN BẢN ỦY QUYỀN"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(split_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(split_planner.client, "chat", fake_chat)

    result = await planner.plan_thay_doi_ho_tich_attachments(
        [_file("khai-sinh.pdf"), _file("uy-quyen.pdf")], _split_context(), {},
    )

    assert [item["componentIndex"] for item in result["attachments"]] == [None, None]
    assert [item["target"] for item in result["attachments"]] == ["new", "new"]
    assert [item["documentName"] for item in result["attachments"]] == [
        "Tài liệu kèm theo", "Tài liệu kèm theo 2",
    ]
    assert any("attachment_agent" in error for error in result["errors"])


async def test_does_not_guess_split_when_multi_page_ocr_has_no_page_boundaries(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": "mixed.pdf", "text": "CCCD rồi đến GIẤY KHAI SINH"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "identity"},
            {"fileIndex": 0, "pageFrom": 2, "pageTo": 3, "type": "supporting_evidence"},
        ]})

    monkeypatch.setattr(split_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(split_planner.client, "chat", fake_chat)

    result = await planner.plan_thay_doi_ho_tich_attachments(
        [_pdf_file("mixed.pdf", 3)], {"splitDocuments": True}, {},
    )

    assert result["extracted"]["attachmentMode"] == "split_documents"
    assert len(result["attachments"]) == 1
    assert "sourceSegments" not in result["attachments"][0]
    assert any("Không có mốc trang" in error for error in result["errors"])


async def test_default_mode_preserves_mixed_file_as_one_bundle(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "mixed.pdf",
            "text": "TỜ KHAI THAY ĐỔI CẢI CHÍNH HỘ TỊCH\nCĂN CƯỚC CÔNG DÂN\nGIẤY KHAI SINH",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        assert "pageFrom" not in messages[1]["content"]
        return json.dumps({"documents": [{
            "fileIndex": 0,
            "type": "other",
            "documentName": "Hồ sơ cải chính hộ tịch",
            "subjectName": "",
        }]})

    monkeypatch.setattr(preserve_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(preserve_planner.client, "chat", fake_chat)

    result = await planner.plan_thay_doi_ho_tich_attachments([_pdf_file("mixed.pdf", 3)], {}, {})

    assert result["extracted"]["attachmentMode"] == "preserve_files"
    assert len(result["attachments"]) == 1
    assert result["attachments"][0]["documentName"] == "Hồ sơ cải chính hộ tịch"
    assert result["attachments"][0]["target"] == "new"
    assert "sourceSegments" not in result["attachments"][0]
    assert "sourceFileIndexes" not in result["attachments"][0]


async def test_preserve_mode_routes_single_evidence_and_authorization(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "birth.pdf", "text": "GIẤY KHAI SINH"},
            {"name": "authorization.pdf", "text": "VĂN BẢN ỦY QUYỀN"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {
                "fileIndex": 0,
                "type": "supporting_evidence",
                "documentName": "Giấy khai sinh",
                "subjectName": "",
            },
            {
                "fileIndex": 1,
                "type": "authorization",
                "documentName": "Văn bản ủy quyền",
                "subjectName": "",
            },
        ]})

    monkeypatch.setattr(preserve_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(preserve_planner.client, "chat", fake_chat)

    result = await planner.plan_thay_doi_ho_tich_attachments(
        [_file("birth.pdf"), _file("authorization.pdf")], _context(), {},
    )

    assert [item["documentName"] for item in result["attachments"]] == [
        "Giấy khai sinh", "Văn bản ủy quyền",
    ]
    assert [item["componentIndex"] for item in result["attachments"]] == [4, 6]
    assert all(item["target"] == "existing" for item in result["attachments"])


async def test_preserve_mode_claims_each_existing_component_once(monkeypatch):
    evidence_names = [
        "Trích lục cải chính hộ tịch",
        "Giấy khai sinh",
        "Trích lục khai tử",
        "Giấy khai sinh",
        "Giấy chứng tử",
    ]

    async def fake_ocr_per_file(files):
        return [{"name": file["name"], "text": evidence_names[index]} for index, file in enumerate(files)]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {
                "fileIndex": index,
                "titleText": name.upper(),
                "type": "supporting_evidence",
                "identityType": "",
                "documentName": name,
                "subjectName": "",
            }
            for index, name in enumerate(evidence_names)
        ]})

    monkeypatch.setattr(preserve_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(preserve_planner.client, "chat", fake_chat)

    result = await planner.plan_thay_doi_ho_tich_attachments(
        [_file(f"evidence-{index}.pdf") for index in range(len(evidence_names))],
        _context(),
        {},
    )

    assert [item["target"] for item in result["attachments"]] == [
        "existing", "new", "new", "new", "new",
    ]
    assert [item["componentIndex"] for item in result["attachments"]] == [4, None, None, None, None]
    assert [item["componentName"] for item in result["attachments"]] == [
        "Giấy tờ liên quan đến việc thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc",
        "Giấy khai sinh",
        "Trích lục khai tử",
        "Giấy khai sinh 2",
        "Giấy chứng tử",
    ]
    assert all("Tên Hồ Sơ" not in item["componentName"] for item in result["attachments"])


async def test_preserve_mode_routes_production_eleven_file_contract(monkeypatch):
    llm_documents = [
        ("TỜ KHAI CẢI CHÍNH HỘ TỊCH", "paper_declaration", "", "Tờ khai cải chính hộ tịch bản giấy", ""),
        ("TRÍCH LỤC CẢI CHÍNH HỘ TỊCH", "supporting_evidence", "", "Trích lục cải chính hộ tịch", ""),
        ("GIẤY CHỨNG NHẬN DÂN", "identity", "cmnd", "Chứng minh nhân dân", "NGUYỄN THỊ Á"),
        ("GIẤY ỦY QUYỀN", "authorization", "", "Giấy ủy quyền", ""),
        ("GIẤY KHAI SINH", "supporting_evidence", "", "Giấy khai sinh", ""),
        ("GIẤY CHỨNG MINH NHÂN DÂN", "identity", "cmnd", "Chứng minh nhân dân", "NGUYỄN HOÀI"),
        ("TRÍCH LỤC KHAI TỬ", "supporting_evidence", "", "Trích lục khai tử", ""),
        ("GIẤY KHAI SINH", "supporting_evidence", "", "Giấy khai sinh", ""),
        ("GIẤY CHỨNG TỬ", "supporting_evidence", "", "Giấy chứng tử", ""),
        ("CĂN CƯỚC CÔNG DÂN", "identity", "cccd", "Căn cước công dân", "NGUYỄN THỊ THÂN"),
        ("CĂN CƯỚC CÔNG DÂN", "identity", "cccd", "Căn cước công dân", "QUÁCH MẪN TRUNG"),
    ]

    async def fake_ocr_per_file(files):
        return [{"name": file["name"], "text": llm_documents[index][0]} for index, file in enumerate(files)]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {
                "fileIndex": index,
                "titleText": title,
                "type": doc_type,
                "identityType": identity_type,
                "documentName": document_name,
                "subjectName": subject_name,
            }
            for index, (title, doc_type, identity_type, document_name, subject_name)
            in enumerate(llm_documents)
        ]})

    context = {
        "attachmentContext": {
            "components": [
                {
                    "index": 1,
                    "componentName": (
                        "- Giấy tờ liên quan đến việc thay đổi, cải chính, bổ sung thông tin hộ tịch, "
                        "xác định lại dân tộc;Tên Hồ Sơ: - Giấy tờ liên quan đến việc thay đổi, cải chính, "
                        "bổ sung thông tin hộ tịch, xác định lại dân tộc;"
                    ),
                    "hasFile": False,
                },
                {
                    "index": 2,
                    "componentName": (
                        "- Văn bản ủy quyền (được chứng thực) theo quy định của pháp luật;"
                        "Tên Hồ Sơ: - Văn bản ủy quyền"
                    ),
                    "hasFile": False,
                },
            ],
        },
    }
    monkeypatch.setattr(preserve_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(preserve_planner.client, "chat", fake_chat)

    result = await planner.plan_thay_doi_ho_tich_attachments(
        [_file(f"scan-{index}.pdf") for index in range(len(llm_documents))],
        context,
        {},
    )

    assert [item["documentName"] for item in result["attachments"]] == [
        "Tờ khai cải chính hộ tịch bản giấy",
        "Trích lục cải chính hộ tịch",
        "CMND NGUYỄN THỊ Á",
        "Giấy ủy quyền",
        "Giấy khai sinh",
        "CMND NGUYỄN HOÀI",
        "Trích lục khai tử",
        "Giấy khai sinh 2",
        "Giấy chứng tử",
        "CCCD NGUYỄN THỊ THÂN",
        "CCCD QUÁCH MẪN TRUNG",
    ]
    assert [item["componentIndex"] for item in result["attachments"]] == [
        None, 1, None, 2, None, None, None, None, None, None, None,
    ]
    assert [item["target"] for item in result["attachments"]] == [
        "new", "existing", "new", "existing", "new", "new", "new", "new", "new", "new", "new",
    ]
    assert result["attachments"][4]["componentName"] == "Giấy khai sinh"
    assert result["attachments"][7]["componentName"] == "Giấy khai sinh 2"
    assert all("Tên Hồ Sơ" not in item["componentName"] for item in result["attachments"])


async def test_preserve_mode_merges_only_same_subject_identity_faces(monkeypatch):
    texts = [
        "CĂN CƯỚC CÔNG DÂN Số 040203015844 Họ và tên NGUYỄN VĂN A",
        "ĐẶC ĐIỂM NHẬN DẠNG IDVNM 040203015844",
        "CĂN CƯỚC CÔNG DÂN Số 012193000851 Họ và tên TRẦN THỊ B",
    ]

    async def fake_ocr_per_file(files):
        return [{"name": file["name"], "text": texts[index]} for index, file in enumerate(files)]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"fileIndex": 0, "type": "identity", "documentName": "Căn cước công dân", "subjectName": "NGUYỄN VĂN A"},
            {"fileIndex": 1, "type": "identity", "documentName": "Căn cước công dân", "subjectName": ""},
            {"fileIndex": 2, "type": "identity", "documentName": "Căn cước công dân", "subjectName": "TRẦN THỊ B"},
        ]})

    monkeypatch.setattr(preserve_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(preserve_planner.client, "chat", fake_chat)

    result = await planner.plan_thay_doi_ho_tich_attachments(
        [_file("a-front.jpg", "image/jpeg"), _file("a-back.jpg", "image/jpeg"), _file("b.jpg", "image/jpeg")],
        {},
        {},
    )

    assert len(result["attachments"]) == 2
    assert result["attachments"][0]["sourceFileIndexes"] == [0, 1]
    assert "sourceFileIndexes" not in result["attachments"][1]
    assert [item["documentName"] for item in result["attachments"]] == [
        "CCCD NGUYỄN VĂN A", "CCCD TRẦN THỊ B",
    ]


async def test_preserve_mode_keeps_multi_person_identity_pdf_whole_and_generic(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "identities.pdf",
            "text": "CĂN CƯỚC CÔNG DÂN Số 040203015844\nCĂN CƯỚC CÔNG DÂN Số 012193000851",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{
            "fileIndex": 0,
            "type": "identity",
            "documentName": "Căn cước công dân",
            "subjectName": "",
        }]})

    monkeypatch.setattr(preserve_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(preserve_planner.client, "chat", fake_chat)

    result = await planner.plan_thay_doi_ho_tich_attachments([_pdf_file("identities.pdf", 4)], None, {})

    assert len(result["attachments"]) == 1
    assert result["attachments"][0]["documentName"] == "Căn cước công dân"
    assert "sourceSegments" not in result["attachments"][0]


async def test_split_mode_ignores_blank_page_and_names_identity_subject(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "mixed.pdf",
            "text": """
───── Trang 1/3 ─────
CĂN CƯỚC CÔNG DÂN Số 040203015844 Họ và tên NGUYỄN VĂN A
───── Trang 2/3 ─────
ĐẶC ĐIỂM NHẬN DẠNG IDVNM 040203015844
───── Trang 3/3 ─────
""",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {
                "fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "identity",
                "documentName": "CCCD NGUYỄN VĂN A", "subjectName": "NGUYỄN VĂN A",
            },
            {
                "fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "identity",
                "documentName": "Căn cước công dân", "subjectName": "",
            },
            {
                "fileIndex": 0, "pageFrom": 3, "pageTo": 3, "type": "blank_page",
                "documentName": "Trang trắng", "subjectName": "",
            },
        ]})

    monkeypatch.setattr(split_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(split_planner.client, "chat", fake_chat)

    result = await planner.plan_thay_doi_ho_tich_attachments(
        [_pdf_file("mixed.pdf", 3)], {"splitDocuments": True}, {},
    )

    assert len(result["attachments"]) == 1
    assert result["attachments"][0]["documentName"] == "CCCD NGUYỄN VĂN A"
    assert result["attachments"][0]["sourceSegments"] == [
        {"fileIndex": 0, "pageIndexes": [0]},
        {"fileIndex": 0, "pageIndexes": [1]},
    ]
    assert result["extracted"]["classified"][-1]["target"] == "ignored"


async def test_split_mode_claims_existing_evidence_row_once_and_keeps_identity_type(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "mixed.pdf",
            "text": """
───── Trang 1/3 ─────
GIẤY KHAI SINH
───── Trang 2/3 ─────
TRÍCH LỤC KHAI TỬ
───── Trang 3/3 ─────
GIẤY CHỨNG MINH NHÂN DÂN
Họ tên: NGUYỄN XUÂN TRỢ
""",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {
                "fileIndex": 0, "pageFrom": 1, "pageTo": 1,
                "type": "supporting_evidence", "documentName": "Giấy khai sinh",
            },
            {
                "fileIndex": 0, "pageFrom": 2, "pageTo": 2,
                "type": "supporting_evidence", "documentName": "Trích lục khai tử",
            },
            {
                "fileIndex": 0, "pageFrom": 3, "pageTo": 3, "type": "identity",
                "documentName": "Chứng minh nhân dân", "subjectName": "NGUYỄN XUÂN TRỢ",
            },
        ]})

    context = {
        "splitDocuments": True,
        "attachmentContext": {
            "components": [{
                "index": 1,
                "componentName": (
                    "- Giấy tờ liên quan đến việc thay đổi, cải chính, bổ sung thông tin hộ tịch, "
                    "xác định lại dân tộc;Tên Hồ Sơ: - Giấy tờ liên quan đến việc thay đổi, "
                    "cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc;"
                ),
                "hasFile": False,
            }],
        },
    }
    monkeypatch.setattr(split_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(split_planner.client, "chat", fake_chat)

    result = await planner.plan_thay_doi_ho_tich_attachments(
        [_pdf_file("mixed.pdf", 3)], context, {},
    )

    assert [item["documentName"] for item in result["attachments"]] == [
        "Giấy khai sinh", "Trích lục khai tử", "CMND NGUYỄN XUÂN TRỢ",
    ]
    assert [item["target"] for item in result["attachments"]] == [
        "existing", "new", "new",
    ]
    assert [item["componentIndex"] for item in result["attachments"]] == [1, None, None]
    assert result["attachments"][0]["componentName"] == (
        "Giấy tờ liên quan đến việc thay đổi, cải chính, bổ sung thông tin hộ tịch, "
        "xác định lại dân tộc"
    )
    assert "Tên Hồ Sơ" not in result["attachments"][0]["componentName"]


async def test_split_mode_uses_llm_title_classification_and_unique_slots(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {
                "name": "cai-chinh.pdf",
                "text": """
TRÍCH LỤC
CẢI CHÍNH HỘ TỊCH
(BẢN SAO)
Đã đăng ký việc: Cải chính chữ đệm của người được khai tử
Trong: Sổ đăng ký khai tử và Trích lục khai tử
""",
            },
            {
                "name": "khai-tu.pdf",
                "text": "TRÍCH LỤC KHAI TỬ\nĐã chết vào lúc 05 giờ 00 phút",
            },
            {
                "name": "chung-tu.pdf",
                "text": """
GIẤY CHỨNG TỬ
(BẢN SAO)
Số Giấy CMND/Hộ chiếu/Giấy tờ hợp lệ thay thế:
Đã chết vào lúc 15 giờ 30 phút
""",
            },
            {
                "name": "passport.pdf",
                "text": "HỘ CHIẾU\nPASSPORT\nP<VNMNGUYEN<VAN<A",
            },
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {
                "fileIndex": 0, "pageFrom": 1, "pageTo": 1,
                "titleText": "TRÍCH LỤC CẢI CHÍNH HỘ TỊCH",
                "type": "supporting_evidence", "identityType": "",
                "documentName": "Trích lục cải chính hộ tịch",
            },
            {
                "fileIndex": 1, "pageFrom": 1, "pageTo": 1,
                "titleText": "TRÍCH LỤC KHAI TỬ",
                "type": "supporting_evidence", "identityType": "",
                "documentName": "Trích lục khai tử",
            },
            {
                "fileIndex": 2, "pageFrom": 1, "pageTo": 1,
                "titleText": "GIẤY CHỨNG TỬ",
                "type": "supporting_evidence", "identityType": "",
                "documentName": "Giấy chứng tử", "subjectName": "",
            },
            {
                "fileIndex": 3, "pageFrom": 1, "pageTo": 1,
                "titleText": "HỘ CHIẾU", "type": "identity", "identityType": "passport",
                "documentName": "Hộ chiếu", "subjectName": "NGUYỄN VĂN A",
            },
        ]})

    monkeypatch.setattr(split_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(split_planner.client, "chat", fake_chat)

    result = await planner.plan_thay_doi_ho_tich_attachments(
        [_file("a.pdf"), _file("b.pdf"), _file("c.pdf"), _file("d.pdf")],
        _split_context(),
        {},
    )

    assert [item["documentName"] for item in result["attachments"]] == [
        "Trích lục cải chính hộ tịch",
        "Trích lục khai tử",
        "Giấy chứng tử",
        "Hộ chiếu NGUYỄN VĂN A",
    ]
    assert [item["type"] for item in result["extracted"]["classified"]] == [
        "supporting_evidence",
        "supporting_evidence",
        "supporting_evidence",
        "identity",
    ]
    assert result["attachments"][0]["target"] == "existing"
    assert all(item["target"] == "new" for item in result["attachments"][1:])
    assert "Trích lục khai tử 2" not in {
        item["documentName"] for item in result["attachments"]
    }


async def test_preserve_mode_uses_llm_title_for_death_certificate(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "chung-tu.pdf",
            "text": """
GIẤY CHỨNG TỬ
(BẢN SAO)
Số Giấy CMND/Hộ chiếu/Giấy tờ hợp lệ thay thế:
Đã chết vào lúc 15 giờ 30 phút
""",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{
            "fileIndex": 0,
            "titleText": "GIẤY CHỨNG TỬ",
            "type": "supporting_evidence",
            "identityType": "",
            "documentName": "Giấy chứng tử",
            "subjectName": "",
        }]})

    monkeypatch.setattr(preserve_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(preserve_planner.client, "chat", fake_chat)

    result = await planner.plan_thay_doi_ho_tich_attachments(
        [_file("chung-tu.pdf")], _context(), {},
    )

    attachment = result["attachments"][0]
    assert attachment["documentName"] == "Giấy chứng tử"
    assert attachment["target"] == "existing"
    assert "sourceSegments" not in attachment
    assert result["extracted"]["classified"][0]["type"] == "supporting_evidence"


async def test_preserve_mode_uses_llm_identity_type_for_legacy_cmnd(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "cmnd-cu.pdf",
            "text": "GIẤY CHỨNG NHẬN DÂN\nHọ tên: NGUYỄN THỊ Á\nNGÓN TRỎ TRÁI",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{
            "fileIndex": 0,
            "titleText": "GIẤY CHỨNG NHẬN DÂN",
            "type": "identity",
            "identityType": "cmnd",
            "documentName": "Chứng minh nhân dân",
            "subjectName": "NGUYỄN THỊ Á",
        }]})

    monkeypatch.setattr(preserve_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(preserve_planner.client, "chat", fake_chat)

    result = await planner.plan_thay_doi_ho_tich_attachments(
        [_file("cmnd-cu.pdf")], {}, {},
    )

    assert result["attachments"][0]["documentName"] == "CMND NGUYỄN THỊ Á"
    assert result["attachments"][0]["target"] == "new"
    assert result["extracted"]["classified"][0]["type"] == "identity"


async def test_split_mode_keeps_llm_page_boundaries_without_semantic_override(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{
            "name": "mixed.pdf",
            "text": """
───── Trang 1/3 ─────
TỜ KHAI ĐĂNG KÝ VIỆC THAY ĐỔI, CẢI CHÍNH,
BỔ SUNG THÔNG TIN HỘ TỊCH, XÁC ĐỊNH LẠI DÂN TỘC
Giấy tờ tùy thân: CCCD số 024078019726
───── Trang 2/3 ─────
Đề nghị cấp bản sao; Người yêu cầu ký tên
───── Trang 3/3 ─────
CĂN CƯỚC CÔNG DÂN
Citizen Identity Card
Họ và tên: NGUYỄN VĂN QUỲNH
Số: 024078019726
""",
        }]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {
                "fileIndex": 0, "pageFrom": 1, "pageTo": 2,
                "titleText": "TỜ KHAI ĐĂNG KÝ VIỆC THAY ĐỔI, CẢI CHÍNH HỘ TỊCH",
                "type": "paper_declaration", "identityType": "",
                "documentName": "Tờ khai cải chính hộ tịch bản giấy", "subjectName": "",
            },
            {
                "fileIndex": 0, "pageFrom": 3, "pageTo": 3,
                "titleText": "CĂN CƯỚC CÔNG DÂN", "type": "identity", "identityType": "cccd",
                "documentName": "Căn cước công dân", "subjectName": "NGUYỄN VĂN QUỲNH",
            },
        ]})

    monkeypatch.setattr(split_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(split_planner.client, "chat", fake_chat)

    result = await planner.plan_thay_doi_ho_tich_attachments(
        [_pdf_file("mixed.pdf", 3)], {"splitDocuments": True}, {},
    )

    assert [item["documentName"] for item in result["attachments"]] == [
        "Tờ khai cải chính hộ tịch bản giấy",
        "CCCD NGUYỄN VĂN QUỲNH",
    ]
    assert [item["sourceSegments"] for item in result["attachments"]] == [
        [{"fileIndex": 0, "pageIndexes": [0, 1]}],
        [{"fileIndex": 0, "pageIndexes": [2]}],
    ]
    assert len({item["componentName"] for item in result["attachments"]}) == 2
    assert not any("tách lại" in error.lower() for error in result["errors"])


async def test_split_mode_uses_matching_evidence_row_despite_unreliable_has_file(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": "birth.pdf", "text": "GIẤY KHAI SINH"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{
            "fileIndex": 0, "pageFrom": 1, "pageTo": 1,
            "type": "supporting_evidence", "documentName": "Giấy khai sinh",
        }]})

    context = _split_context()
    context["attachmentContext"]["components"][1]["hasFile"] = True
    monkeypatch.setattr(split_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(split_planner.client, "chat", fake_chat)

    result = await planner.plan_thay_doi_ho_tich_attachments(
        [_file("birth.pdf")], context, {},
    )

    assert result["attachments"][0]["target"] == "existing"
    assert result["attachments"][0]["componentIndex"] == 4
    assert result["attachments"][0]["componentName"] == (
        "Giấy tờ liên quan đến việc thay đổi, cải chính, bổ sung thông tin hộ tịch, "
        "xác định lại dân tộc"
    )


def test_procedure_has_attachment_step():
    procedure = get_procedure("thay-doi-cai-chinh-ho-tich")

    assert procedure["hasAttachmentStep"] is True
    assert procedure["supportsSplitDocuments"] is True


def test_attachment_prompts_prioritize_real_titles_and_strong_identity_evidence():
    assert "Khối tiêu đề thật > cấu trúc đặc trưng" in split_planner.SYSTEM_PROMPT
    assert "Số CMND/Hộ chiếu/Giấy tờ hợp lệ thay thế" in split_planner.SYSTEM_PROMPT
    assert "Khối tiêu đề thật > cấu trúc đặc trưng" in preserve_planner.SYSTEM_PROMPT
    assert "titleText" in split_planner.SYSTEM_PROMPT
    assert "identityType" in preserve_planner.SYSTEM_PROMPT
    assert "\n" in split_planner._truncate_text("GIẤY CHỨNG TỬ\nSố CMND/Hộ chiếu")

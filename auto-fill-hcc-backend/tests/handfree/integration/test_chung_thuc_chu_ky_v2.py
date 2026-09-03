import pytest

from app.pipelines.chung_thuc_chu_ky.attach import planner_v2 as planner, preserve_prompt_v2
from app.pipelines.chung_thuc_chu_ky.attach.planner_v2 import (
    IDENTITY_COMPONENT,
    SIGNATURE_DOC_COMPONENT,
    build_plan_items,
    build_segment_plan_items,
)
from app.process.schemas import FileItem


def _file(name: str) -> dict:
    return {
        "name": name,
        "type": "application/pdf",
        "dataUrl": "data:application/pdf;base64,AA==",
    }


def _meta(count: int, pages: int = 1) -> dict[int, dict]:
    return {
        index: {"pageCount": pages, "pageBoundariesAvailable": True}
        for index in range(count)
    }


def test_preserve_prompt_keeps_whole_file_and_omits_person_name():
    assert "Mỗi fileIndex phải trả ĐÚNG MỘT object" in preserve_prompt_v2.SYSTEM_PROMPT
    assert "không thêm họ tên" in preserve_prompt_v2.SYSTEM_PROMPT
    assert "Hồ sơ chứng thực chữ ký" in preserve_prompt_v2.SYSTEM_PROMPT


def test_duplicate_file_names_keep_positional_ocr_results():
    files = [_file("image.pdf"), _file("image.pdf")]
    ocr_results = [
        {"name": "image.pdf", "text": "GIẤY CAM ĐOAN"},
        {"name": "image.pdf", "text": "CĂN CƯỚC CÔNG DÂN"},
    ]

    items = build_plan_items(files, ocr_results)

    assert [(item["componentIndex"], item["detectedType"]) for item in items] == [
        (1, "Tài liệu chứng thực"),
        (2, "Căn cước công dân"),
    ]


def test_llm_type_wins_over_identity_keyword_rule():
    files = [_file("cam-doan.pdf")]
    ocr_results = [{"name": "cam-doan.pdf", "text": "GIẤY CAM ĐOAN\nCCCD số 012345678901"}]

    items = build_plan_items(
        files,
        ocr_results,
        {0: {"detectedType": "Giấy cam đoan", "documentName": "Giấy cam đoan"}},
    )

    assert items[0]["componentIndex"] == 1
    assert items[0]["detectedType"] == "Giấy cam đoan"
    assert items[0]["documentName"] == "Giấy cam đoan"


def test_llm_document_name_also_wins_when_detected_type_is_empty():
    files = [_file("cam-doan.pdf")]
    segments = [{
        "fileIndex": 0,
        "pageFrom": 1,
        "pageTo": 1,
        "detectedType": "",
        "documentName": "Giấy cam đoan",
        "logicalKey": "cam-doan-1",
    }]

    attachments, _ = build_segment_plan_items(
        files,
        segments,
        _meta(1),
        {0: {1: "GIẤY CAM ĐOAN\nCCCD số 012345678901"}},
        {},
    )

    assert attachments[0]["componentIndex"] == 1
    assert attachments[0]["detectedType"] == "Giấy cam đoan"


def test_mixed_pdf_is_split_between_signature_document_and_identity_slot():
    files = [_file("mixed.pdf")]
    segments = [
        {
            "fileIndex": 0,
            "pageFrom": 1,
            "pageTo": 2,
            "detectedType": "Giấy cam đoan",
            "documentName": "Giấy cam đoan",
            "logicalKey": "giay-cam-doan-1",
        },
        {
            "fileIndex": 0,
            "pageFrom": 3,
            "pageTo": 4,
            "detectedType": "Căn cước công dân",
            "documentName": "Căn cước công dân",
            "logicalKey": "cccd-1",
        },
    ]
    pages = {
        0: {
            1: "GIẤY CAM ĐOAN",
            2: "Nội dung cam đoan có nhắc CCCD 012345678901",
            3: "CĂN CƯỚC CÔNG DÂN",
            4: "ĐẶC ĐIỂM NHẬN DẠNG IDVNM",
        }
    }

    attachments, classified = build_segment_plan_items(
        files,
        segments,
        {0: {"pageCount": 4, "pageBoundariesAvailable": True}},
        pages,
        {},
    )

    assert [(item["componentIndex"], item["componentName"]) for item in attachments] == [
        (1, SIGNATURE_DOC_COMPONENT),
        (2, IDENTITY_COMPONENT),
    ]
    assert attachments[0]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0, 1]}]
    assert attachments[1]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [2, 3]}]
    assert [item["detectedType"] for item in classified] == [
        "Giấy cam đoan",
        "Căn cước công dân",
    ]


def test_all_identity_sources_are_merged_once_in_original_order():
    files = [_file(name) for name in ["a-front.pdf", "a-back.pdf", "passport.pdf"]]
    segments = [
        {
            "fileIndex": 0,
            "pageFrom": 1,
            "pageTo": 1,
            "detectedType": "Căn cước công dân",
            "documentName": "Căn cước công dân",
            "logicalKey": "cccd-a",
        },
        {
            "fileIndex": 1,
            "pageFrom": 1,
            "pageTo": 1,
            "detectedType": "Căn cước công dân",
            "documentName": "Căn cước công dân",
            "logicalKey": "cccd-a",
        },
        {
            "fileIndex": 2,
            "pageFrom": 1,
            "pageTo": 1,
            "detectedType": "Hộ chiếu",
            "documentName": "Hộ chiếu",
            "logicalKey": "passport-b",
        },
    ]

    attachments, classified = build_segment_plan_items(
        files,
        segments,
        _meta(len(files)),
        {
            0: {1: "CĂN CƯỚC CÔNG DÂN Số 012345678901"},
            1: {1: "ĐẶC ĐIỂM NHẬN DẠNG IDVNM012345678901"},
            2: {1: "HỘ CHIẾU PASSPORT"},
        },
        {},
    )

    assert len(attachments) == 2
    assert attachments[0]["componentIndex"] == 2
    assert attachments[0]["documentName"] == "Căn cước công dân"
    assert [segment["fileIndex"] for segment in attachments[0]["sourceSegments"]] == [0, 1]
    assert attachments[1]["documentName"] == "Hộ chiếu"
    assert attachments[1]["target"] == "new"
    assert len({item["logicalGroup"] for item in classified}) == 2


def test_parts_with_same_logical_key_become_one_signature_document():
    files = [_file("don-1.pdf"), _file("don-2.pdf")]
    segments = [
        {
            "fileIndex": index,
            "pageFrom": 1,
            "pageTo": 1,
            "detectedType": "Đơn xin xác nhận",
            "documentName": "Đơn xin xác nhận",
            "logicalKey": "don-xin-xac-nhan-1",
        }
        for index in range(2)
    ]

    attachments, _ = build_segment_plan_items(
        files,
        segments,
        _meta(len(files)),
        {0: {1: "ĐƠN XIN XÁC NHẬN"}, 1: {1: "NỘI DUNG TIẾP THEO"}},
        {},
    )

    assert len(attachments) == 1
    assert attachments[0]["componentIndex"] == 1
    assert attachments[0]["documentName"] == "Đơn xin xác nhận"
    assert [segment["fileIndex"] for segment in attachments[0]["sourceSegments"]] == [0, 1]


@pytest.mark.asyncio
async def test_plan_uses_one_batch_ocr_and_one_llm_request_for_duplicate_names(monkeypatch):
    calls = {"ocr": 0, "llm": 0}

    async def fake_ocr_per_file(files):
        calls["ocr"] += 1
        assert len(files) == 2
        return [
            {"name": "image.pdf", "text": "GIẤY CAM ĐOAN"},
            {"name": "image.pdf", "text": "HỘ CHIẾU PASSPORT"},
        ]

    async def fake_classify(documents):
        calls["llm"] += 1
        assert [item["fileIndex"] for item in documents] == [0, 1]
        return [
            {
                "fileIndex": 0,
                "pageFrom": 1,
                "pageTo": 1,
                "detectedType": "Giấy cam đoan",
                "documentName": "Giấy cam đoan",
                "logicalKey": "cam-doan-1",
            },
            {
                "fileIndex": 1,
                "pageFrom": 1,
                "pageTo": 1,
                "detectedType": "Hộ chiếu",
                "documentName": "Hộ chiếu",
                "logicalKey": "passport-1",
            },
        ]

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner, "_classify_documents_with_llm", fake_classify)
    result = await planner.plan([
        FileItem(name="image.pdf", type="application/pdf", dataUrl="data:application/pdf;base64,AA==", role="doc"),
        FileItem(name="image.pdf", type="application/pdf", dataUrl="data:application/pdf;base64,AA==", role="doc"),
    ], options={"splitDocuments": True})

    assert calls == {"ocr": 1, "llm": 1}
    assert [(item["componentIndex"], item["documentName"]) for item in result["attachments"]] == [
        (1, "Giấy cam đoan"),
        (2, "Hộ chiếu"),
    ]
    assert "fileIndex=0 · image.pdf" in result["ocr_text"]
    assert "fileIndex=1 · image.pdf" in result["ocr_text"]


@pytest.mark.asyncio
async def test_plan_defaults_to_preserve_prompt_and_only_explicitly_splits_documents(monkeypatch):
    calls = {"preserve": 0, "split": 0}

    async def fake_ocr_per_file(_files):
        return [{
            "name": "mixed.pdf",
            "text": "───── Trang 1/4 ─────\nGIẤY CAM ĐOAN\n"
                    "───── Trang 2/4 ─────\nNỘI DUNG CAM ĐOAN\n"
                    "───── Trang 3/4 ─────\nCĂN CƯỚC CÔNG DÂN\n"
                    "───── Trang 4/4 ─────\nĐẶC ĐIỂM NHẬN DẠNG",
        }]

    async def fake_preserve(_documents):
        calls["preserve"] += 1
        return [{
            "fileIndex": 0, "pageFrom": 1, "pageTo": 4,
            "detectedType": "Giấy cam đoan", "documentName": "Hồ sơ chứng thực chữ ký",
            "logicalKey": "",
        }]

    async def fake_split(_documents):
        calls["split"] += 1
        return [
            {"fileIndex": 0, "pageFrom": 1, "pageTo": 2,
             "detectedType": "Giấy cam đoan", "documentName": "Giấy cam đoan", "logicalKey": "cam-doan"},
            {"fileIndex": 0, "pageFrom": 3, "pageTo": 4,
             "detectedType": "Căn cước công dân", "documentName": "Căn cước công dân", "logicalKey": "cccd"},
        ]

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner, "_classify_source_files_with_llm", fake_preserve)
    monkeypatch.setattr(planner, "_classify_documents_with_llm", fake_split)
    monkeypatch.setattr(planner, "_pdf_page_count", lambda _file: 4)
    files = [FileItem(name="mixed.pdf", type="application/pdf",
                      dataUrl="data:application/pdf;base64,AA==", role="doc")]

    preserved = await planner.plan(files, options={"splitMode": True})
    split = await planner.plan(files, options={"splitDocuments": True})

    assert calls == {"preserve": 1, "split": 1}
    assert preserved["extracted"]["documentPromptMode"] == "preserve"
    assert preserved["extracted"]["documentSplitEnabled"] is False
    assert len(preserved["attachments"]) == 1
    assert preserved["attachments"][0]["componentIndex"] == 1
    assert preserved["attachments"][0]["documentName"] == "Hồ sơ chứng thực chữ ký"
    assert "sourceSegments" not in preserved["attachments"][0]
    assert split["extracted"]["documentPromptMode"] == "split"
    assert split["extracted"]["documentSplitEnabled"] is True
    assert [item["componentIndex"] for item in split["attachments"]] == [1, 2]


def test_segment_plan_uses_live_signature_slots_from_attachment_context():
    files = [_file("don.pdf"), _file("cccd.pdf")]
    segments = [
        {
            "fileIndex": 0, "pageFrom": 1, "pageTo": 1,
            "detectedType": "Đơn đề nghị", "documentName": "Đơn đề nghị", "logicalKey": "don-1",
        },
        {
            "fileIndex": 1, "pageFrom": 1, "pageTo": 1,
            "detectedType": "Căn cước công dân", "documentName": "Căn cước công dân",
            "logicalKey": "cccd-1",
        },
    ]
    options = {"attachmentContext": {"components": [
        {"index": 6, "componentName": SIGNATURE_DOC_COMPONENT},
        {"index": 9, "componentName": IDENTITY_COMPONENT},
    ]}}

    attachments, _ = build_segment_plan_items(
        files, segments, _meta(2),
        {0: {1: "ĐƠN ĐỀ NGHỊ"}, 1: {1: "CĂN CƯỚC CÔNG DÂN"}}, {}, options,
    )

    assert [item["componentIndex"] for item in attachments] == [6, 9]

import pytest

from app.attachments.schemas import AttachmentPlanResp
from app.pipelines.chung_thuc_chu_ky.attach import planner, preserve_prompt
from app.pipelines.chung_thuc_chu_ky.attach.planner import (
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
    assert "Mỗi fileIndex phải trả ĐÚNG MỘT object" in preserve_prompt.SYSTEM_PROMPT
    assert "không thêm họ tên" in preserve_prompt.SYSTEM_PROMPT
    assert "Hồ sơ chứng thực chữ ký" in preserve_prompt.SYSTEM_PROMPT
    assert "signerIdentityNumber" in preserve_prompt.SYSTEM_PROMPT
    assert "identityHolders" in preserve_prompt.SYSTEM_PROMPT


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


@pytest.mark.asyncio
async def test_plan_preserves_mixed_source_by_default_and_splits_only_when_enabled(monkeypatch):
    async def fake_ocr_per_file(_files):
        return [{
            "name": "mixed.pdf",
            "text": (
                "───── Trang 1/4 ─────\nGIẤY CAM ĐOAN\n"
                "───── Trang 2/4 ─────\nNội dung cam đoan\n"
                "───── Trang 3/4 ─────\nCĂN CƯỚC CÔNG DÂN\n"
                "───── Trang 4/4 ─────\nĐẶC ĐIỂM NHẬN DẠNG IDVNM"
            ),
        }]

    async def fake_classify(_documents):
        return [
            {
                "fileIndex": 0,
                "pageFrom": 1,
                "pageTo": 2,
                "detectedType": "Giấy cam đoan",
                "documentName": "Giấy cam đoan",
                "logicalKey": "cam-doan-a",
            },
            {
                "fileIndex": 0,
                "pageFrom": 3,
                "pageTo": 4,
                "detectedType": "Căn cước công dân",
                "documentName": "Căn cước công dân",
                "logicalKey": "cccd-a",
            },
        ]

    async def fake_preserve(_documents):
        return [{
            "fileIndex": 0,
            "pageFrom": 1,
            "pageTo": 4,
            "detectedType": "Giấy cam đoan",
            "documentName": "Hồ sơ chứng thực chữ ký",
            "logicalKey": "",
        }]

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner, "_classify_documents_with_llm", fake_classify)
    monkeypatch.setattr(planner, "_classify_source_files_with_llm", fake_preserve)
    monkeypatch.setattr(planner, "_pdf_page_count", lambda _file: 4)
    files = [FileItem(
        name="mixed.pdf",
        type="application/pdf",
        dataUrl="data:application/pdf;base64,AA==",
        role="doc",
    )]

    # splitMode là tách hồ sơ/tab ở FE, không được hiểu nhầm thành tách giấy tờ trong PDF.
    preserved = await planner.plan(files, options={"splitMode": True})
    split = await planner.plan(files, options={"splitDocuments": True})

    assert preserved["extracted"]["documentSplitEnabled"] is False
    assert preserved["extracted"]["documentPromptMode"] == "preserve"
    assert len(preserved["attachments"]) == 1
    assert preserved["attachments"][0]["componentIndex"] == 1
    assert preserved["attachments"][0]["documentName"] == "Hồ sơ chứng thực chữ ký"
    assert "sourceSegments" not in preserved["attachments"][0]

    assert split["extracted"]["documentSplitEnabled"] is True
    assert split["extracted"]["documentPromptMode"] == "split"
    assert [item["componentIndex"] for item in split["attachments"]] == [1, 2]
    assert all("sourceSegments" in item for item in split["attachments"])


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
    monkeypatch.setattr(planner, "_classify_source_files_with_llm", fake_classify)
    result = await planner.plan([
        FileItem(name="image.pdf", type="application/pdf", dataUrl="data:application/pdf;base64,AA==", role="doc"),
        FileItem(name="image.pdf", type="application/pdf", dataUrl="data:application/pdf;base64,AA==", role="doc"),
    ])

    assert calls == {"ocr": 1, "llm": 1}
    assert [(item["componentIndex"], item["documentName"]) for item in result["attachments"]] == [
        (1, "Giấy cam đoan"),
        (2, "Hộ chiếu"),
    ]
    assert "fileIndex=0 · image.pdf" in result["ocr_text"]
    assert "fileIndex=1 · image.pdf" in result["ocr_text"]


def _signature_segment(
    file_index: int,
    signer_name: str,
    signer_number: str,
    related_numbers: list[str] | None = None,
) -> dict:
    return {
        "fileIndex": file_index,
        "pageFrom": 1,
        "pageTo": 1,
        "detectedType": "Văn bản ủy quyền",
        "documentName": "Văn bản ủy quyền",
        "logicalKey": f"uy-quyen-{file_index}",
        "signerName": signer_name,
        "signerIdentityNumber": signer_number,
        "relatedIdentityNumbers": related_numbers or [signer_number],
        "identityHolders": [],
    }


def _identity_segment(file_index: int, holders: list[tuple[str, str, str]]) -> dict:
    return {
        "fileIndex": file_index,
        "pageFrom": 1,
        "pageTo": 1,
        "detectedType": "Giấy tờ tùy thân",
        "documentName": "Giấy tờ tùy thân",
        "logicalKey": "",
        "signerName": "",
        "signerIdentityNumber": "",
        "relatedIdentityNumbers": [],
        "identityHolders": [
            {"name": name, "identityNumber": number, "documentType": document_type}
            for name, number, document_type in holders
        ],
    }


def test_split_mode_reuses_one_shared_identity_only_in_first_bundle():
    signer_name = "NGUYỄN VĂN A"
    signer_number = "012345678901"
    files = [_file(f"giay-to-{index}.pdf") for index in range(1, 4)] + [_file("cccd.pdf")]
    segments = [
        _signature_segment(index, signer_name, signer_number)
        for index in range(3)
    ] + [
        _identity_segment(3, [(signer_name, signer_number, "CCCD")])
    ]
    pages = {
        0: {1: f"VĂN BẢN ỦY QUYỀN Người ủy quyền {signer_name} CCCD {signer_number}"},
        1: {1: f"VĂN BẢN ỦY QUYỀN Người ủy quyền {signer_name} CCCD {signer_number}"},
        2: {1: f"VĂN BẢN ỦY QUYỀN Người ủy quyền {signer_name} CCCD {signer_number}"},
        3: {1: f"CĂN CƯỚC CÔNG DÂN Họ và tên {signer_name} Số {signer_number}"},
    }
    errors: list[str] = []

    attachments, _ = build_segment_plan_items(
        files,
        segments,
        _meta(len(files)),
        pages,
        {},
        split_mode=True,
        errors=errors,
    )

    assert errors == []
    assert [(item["fileIndex"], item["bundleId"], item["bundleRole"]) for item in attachments] == [
        (0, "signature-1", "signature_document"),
        (3, "signature-1", "identity"),
        (1, "signature-2", "signature_document"),
        (2, "signature-3", "signature_document"),
    ]
    assert attachments[1]["identityScope"] == "shared"


def test_split_mode_treats_one_multi_person_identity_pdf_as_shared_first_bundle():
    files = [
        _file("can-cuoc-cong-dan.pdf"),
        _file("ban-cam-doan.pdf"),
        _file("giay-chung-nhan-quyen-su-dung-dat.pdf"),
        _file("giay-khai-sinh.pdf"),
    ]
    holders = [
        ("TẨN SỦ MẨY", "012181000685", "CCCD"),
        ("HOÀNG MÍ PHÚ", "01230000558", "CCCD"),
        ("CHẺO TON SƠN", "012099002088", "CCCD"),
    ]
    segments = [
        _identity_segment(0, holders),
        _signature_segment(1, "HOÀNG A TOAN", "01208100601"),
        _signature_segment(2, "HOÀNG A TOAN", "045004829"),
        _signature_segment(3, "CHẺO YẾN NHI", ""),
    ]
    pages = {
        0: {
            1: " ".join(
                f"CĂN CƯỚC CÔNG DÂN {name} Số {number}"
                for name, number, _document_type in holders
            )
        },
        1: {1: "BẢN CAM ĐOAN HOÀNG A TOAN CCCD 01208100601"},
        2: {1: "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT HOÀNG A TOAN CMND 045004829"},
        3: {1: "GIẤY KHAI SINH CHẺO YẾN NHI"},
    }
    errors: list[str] = []

    attachments, _ = build_segment_plan_items(
        files,
        segments,
        _meta(len(files)),
        pages,
        {},
        split_mode=True,
        errors=errors,
    )

    assert errors == []
    assert [(item["fileIndex"], item["bundleId"], item["bundleRole"]) for item in attachments] == [
        (1, "signature-1", "signature_document"),
        (0, "signature-1", "identity"),
        (2, "signature-2", "signature_document"),
        (3, "signature-3", "signature_document"),
    ]
    assert attachments[1]["identityScope"] == "shared"
    assert attachments[1]["target"] == "existing"
    assert attachments[1]["componentIndex"] == 2


@pytest.mark.asyncio
async def test_plan_preserves_relationship_metadata_through_shared_segment_validation(monkeypatch):
    signer_name = "NGUYỄN VĂN A"
    signer_number = "012345678901"

    async def fake_ocr_per_file(_files):
        return [
            {
                "name": f"file-{index}.pdf",
                "text": (
                    f"VĂN BẢN ỦY QUYỀN Người ủy quyền {signer_name} CCCD {signer_number}"
                    if index < 2
                    else f"CĂN CƯỚC CÔNG DÂN {signer_name} Số {signer_number}"
                ),
            }
            for index in range(3)
        ]

    async def fake_preserve(_documents):
        return [
            _signature_segment(0, signer_name, signer_number),
            _signature_segment(1, signer_name, signer_number),
            _identity_segment(2, [(signer_name, signer_number, "CCCD")]),
        ]

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner, "_classify_source_files_with_llm", fake_preserve)
    monkeypatch.setattr(planner, "_pdf_page_count", lambda _file: 1)

    result = await planner.plan(
        [
            FileItem(
                name=f"file-{index}.pdf",
                type="application/pdf",
                dataUrl="data:application/pdf;base64,AA==",
                role="doc",
            )
            for index in range(3)
        ],
        options={"splitMode": True},
    )

    assert result["errors"] == []
    assert result["extracted"]["multiDossierBundleEnabled"] is True
    assert [(item["fileIndex"], item["bundleId"]) for item in result["attachments"]] == [
        (0, "signature-1"),
        (2, "signature-1"),
        (1, "signature-2"),
    ]
    assert result["attachments"][1]["identityScope"] == "shared"
    serialized = AttachmentPlanResp.model_validate(result).model_dump(mode="json")
    assert serialized["attachments"][1]["bundleId"] == "signature-1"
    assert serialized["attachments"][1]["identityScope"] == "shared"


def test_split_mode_matches_each_mixed_identity_package_to_its_signer():
    common_name = "NGUYỄN THÙY TRANG"
    common_number = "027304004508"
    signers = [
        ("ZHOU YANG", "EG9297842"),
        ("HSIEH TSEYU", "362918867"),
        ("YI TING KUN", "EH6997622"),
    ]
    files = [_file(f"uy-quyen-{index}.pdf") for index in range(3)] + [
        _file(f"identity-{index}.pdf") for index in range(3)
    ]
    segments = [
        _signature_segment(index, name, number, [number, common_number])
        for index, (name, number) in enumerate(signers)
    ] + [
        _identity_segment(
            index + 3,
            [(common_name, common_number, "CCCD"), (name, number, "Hộ chiếu")],
        )
        for index, (name, number) in enumerate(signers)
    ]
    pages = {
        index: {
            1: (
                f"VĂN BẢN ỦY QUYỀN Người ủy quyền {name} Hộ chiếu {number} "
                f"Người được ủy quyền {common_name} CCCD {common_number}"
            )
        }
        for index, (name, number) in enumerate(signers)
    }
    pages.update({
        index + 3: {
            1: (
                f"CĂN CƯỚC CÔNG DÂN {common_name} {common_number} "
                f"PASSPORT {name} {number}"
            )
        }
        for index, (name, number) in enumerate(signers)
    })
    errors: list[str] = []

    attachments, _ = build_segment_plan_items(
        files,
        segments,
        _meta(len(files)),
        pages,
        {},
        split_mode=True,
        errors=errors,
    )

    assert errors == []
    assert [(item["fileIndex"], item["bundleId"]) for item in attachments] == [
        (0, "signature-1"),
        (3, "signature-1"),
        (1, "signature-2"),
        (4, "signature-2"),
        (2, "signature-3"),
        (5, "signature-3"),
    ]
    identities = [item for item in attachments if item["bundleRole"] == "identity"]
    assert [item["identityScope"] for item in identities] == ["matched", "matched", "matched"]
    assert all("sourceSegments" not in item for item in identities)


def test_split_mode_combines_common_identity_once_with_first_matched_passport():
    common_name = "NGUYỄN THÙY TRANG"
    common_number = "027304004508"
    signers = [
        ("ZHOU YANG", "EG9297842"),
        ("HSIEH TSEYU", "362918867"),
        ("YI TING KUN", "EH6997622"),
    ]
    files = [_file(f"uy-quyen-{index}.pdf") for index in range(3)] + [
        _file("cccd-chung.pdf"),
        _file("passport-zhou.pdf"),
        _file("passport-hsieh.pdf"),
        _file("passport-yi.pdf"),
    ]
    segments = [
        _signature_segment(index, name, number, [number, common_number])
        for index, (name, number) in enumerate(signers)
    ]
    segments.append(_identity_segment(3, [(common_name, common_number, "CCCD")]))
    segments.extend(
        _identity_segment(index + 4, [(name, number, "Hộ chiếu")])
        for index, (name, number) in enumerate(signers)
    )
    pages = {
        index: {
            1: (
                f"VĂN BẢN ỦY QUYỀN Người ủy quyền {name} Hộ chiếu {number} "
                f"Người được ủy quyền {common_name} CCCD {common_number}"
            )
        }
        for index, (name, number) in enumerate(signers)
    }
    pages[3] = {1: f"CĂN CƯỚC CÔNG DÂN {common_name} {common_number}"}
    pages.update({
        index + 4: {1: f"PASSPORT {name} {number}"}
        for index, (name, number) in enumerate(signers)
    })

    attachments, _ = build_segment_plan_items(
        files,
        segments,
        _meta(len(files)),
        pages,
        {},
        split_mode=True,
        errors=[],
    )

    identities = [item for item in attachments if item["bundleRole"] == "identity"]
    assert [item["bundleId"] for item in identities] == ["signature-1", "signature-2", "signature-3"]
    assert identities[0]["sourceSegments"] == [
        {"fileIndex": 3, "pageIndexes": None},
        {"fileIndex": 4, "pageIndexes": None},
    ]
    assert identities[1]["fileIndex"] == 5
    assert identities[2]["fileIndex"] == 6


def test_split_mode_rejects_hallucinated_relationship_keys():
    files = [_file("uy-quyen-a.pdf"), _file("uy-quyen-b.pdf"), _file("cccd.pdf")]
    segments = [
        _signature_segment(0, "NGUYỄN VĂN A", "012345678901"),
        _signature_segment(1, "TRẦN VĂN B", "012345678902"),
        _identity_segment(2, [("NGUYỄN VĂN A", "999999999999", "CCCD")]),
    ]
    pages = {
        0: {1: "VĂN BẢN ỦY QUYỀN NGUYỄN VĂN A CCCD 012345678901"},
        1: {1: "VĂN BẢN ỦY QUYỀN TRẦN VĂN B CCCD 012345678902"},
        # Số LLM bịa không có trong OCR nên holder chỉ còn tên và không được ghép bằng số.
        2: {1: "CĂN CƯỚC CÔNG DÂN NGUYỄN VĂN A Số 012345678901"},
    }
    errors: list[str] = []

    attachments, _ = build_segment_plan_items(
        files,
        segments,
        _meta(len(files)),
        pages,
        {},
        split_mode=True,
        errors=errors,
    )

    # Tên vẫn là khóa phụ hợp lệ và chỉ khớp đúng một người; số bịa không xuất hiện trong plan.
    identity = next(item for item in attachments if item["bundleRole"] == "identity")
    assert identity["bundleId"] == "signature-1"
    assert errors == []


def test_split_mode_bo_giay_tuy_than_khong_khop_ai_thay_vi_de_dong_moi():
    """Sự cố Nghĩa Hưng 21/09/2026: 2 văn bản + 1 căn cước LẠC (không khớp người ký nào).

    Dòng "Thêm thành phần" sinh ra cho tệp lạc là vô dụng ở chế độ tách (mỗi tab chỉ có STT1/STT2),
    mà extension thấy tệp KHÔNG có bundleId thì bỏ NGUYÊN lượt đính kèm → mất cả 3 tệp lành.
    """
    files = [
        _file("van-ban-1.pdf"), _file("van-ban-2.pdf"),
        _file("cccd-nguoi-ky-2.pdf"), _file("cccd-nguoi-la.pdf"),
    ]
    segments = [
        _signature_segment(0, "PHẠM ĐỨC HIỆP", "036043000537"),
        _signature_segment(1, "NGUYỄN XUÂN BAN", "036057012421"),
        _identity_segment(2, [("NGUYỄN XUÂN BAN", "036057012421", "CCCD")]),
        _identity_segment(3, [("TRẦN VĂN HẠNH", "036065008181", "CCCD")]),
    ]
    pages = {
        0: {1: "TRÍCH LỤC KHAI TỬ Người ký PHẠM ĐỨC HIỆP 036043000537"},
        1: {1: "GIẤY CAM KẾT BẢO LÃNH NHÂN SỰ NGUYỄN XUÂN BAN 036057012421"},
        2: {1: "CĂN CƯỚC CÔNG DÂN NGUYỄN XUÂN BAN 036057012421"},
        3: {1: "CĂN CƯỚC CÔNG DÂN TRẦN VĂN HẠNH 036065008181"},
    }
    errors: list[str] = []

    attachments, classified = build_segment_plan_items(
        files, segments, _meta(len(files)), pages, {}, split_mode=True, errors=errors,
    )

    # Tệp lạc KHÔNG nằm trong kế hoạch, và không tệp nào thiếu bundleId.
    assert 3 not in [item["fileIndex"] for item in attachments]
    assert all(item.get("bundleId") for item in attachments)
    assert [(item["fileIndex"], item["bundleId"], item["bundleRole"]) for item in attachments] == [
        (0, "signature-1", "signature_document"),
        (1, "signature-2", "signature_document"),
        (2, "signature-2", "identity"),
    ]
    # Lý do phải nêu TÊN TỆP để câu báo cho cán bộ dùng được luôn.
    assert errors == ["Giấy tờ tùy thân cccd-nguoi-la.pdf không khớp người ký của văn bản nào."]
    # Vẫn ghi vào classified để trang quản trị thấy tệp đã đọc ra gì và vì sao bị bỏ.
    skipped = [row for row in classified if row["target"] == "skipped"]
    assert [(row["fileIndex"], row["bundleId"]) for row in skipped] == [(3, None)]

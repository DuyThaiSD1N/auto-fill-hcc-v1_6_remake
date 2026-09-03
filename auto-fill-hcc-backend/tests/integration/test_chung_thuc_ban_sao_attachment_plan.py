import pytest

from app.attachments.planner import (
    DEFAULT_COPY_CERTIFICATION_COMPONENT,
    build_plan_items,
    canonical_document_type,
    detect_document_type,
    normalize_document_name,
)
from app.pipelines.chung_thuc_ban_sao.attach import planner, preserve_prompt
from app.pipelines.chung_thuc_ban_sao.attach.planner import _unique_document_name, build_segment_plan_items
from app.process.schemas import FileItem


def test_document_name_normalizes_decomposed_vietnamese():
    raw = "Gia\u0302\u0301y CNQSD đa\u0302\u0301t 2.pdf"

    assert normalize_document_name(raw, "Giấy chứng nhận quyền sử dụng đất") == "Giấy CNQSD đất 2"


def test_preserve_prompt_returns_one_name_for_each_whole_file():
    assert "Mỗi fileIndex phải trả ĐÚNG MỘT object" in preserve_prompt.SYSTEM_PROMPT
    assert "không được tách file" in preserve_prompt.SYSTEM_PROMPT
    user_prompt = preserve_prompt.build_user_prompt([{
        "fileIndex": 7,
        "pageCount": 2,
        "pages": [{"pageNumber": 1, "ocrText": "A"}, {"pageNumber": 2, "ocrText": "B"}],
    }])
    assert '"fileIndex": 7' in user_prompt
    assert '"pageCount": 2' in user_prompt


def test_preserve_mode_replaces_overlong_document_name():
    preserved = planner._preserve_source_file_segments(
        [{
            "fileIndex": 0,
            "pageFrom": 1,
            "pageTo": 1,
            "detectedType": "Hồ sơ tổng hợp",
            "documentName": "Đơn đăng ký biến động đất và Giấy chứng nhận quyền sử dụng đất",
            "logicalKey": "",
        }],
        [{"name": "hoso.pdf"}],
        {0: {"pageCount": 1}},
        is_identity_segment=lambda _segment: False,
        long_name_fallback="Hồ sơ chứng thực",
    )

    assert preserved[0]["documentName"] == "Hồ sơ chứng thực"


def test_long_document_name_is_cut_at_word_boundary():
    name = _unique_document_name(
        "Giấy chứng nhận kết quả thi THPT 2026 - Nguyễn Quốc Việt",
        set(),
        "Giấy chứng nhận kết quả thi",
    )

    assert len(name) <= 50
    assert not name.endswith("Quố")


def test_detect_document_type_from_common_ocr_text():
    assert detect_document_type("CĂN CƯỚC CÔNG DÂN\nSố định danh cá nhân: 040203015844") == "Căn cước công dân"
    assert detect_document_type(
        "Đặc điểm nhận dạng / Personal identification\n"
        "Ngón trỏ trái / Left index finger\n"
        "IDVNM1930052419036193005241<<4"
    ) == "Căn cước công dân"
    assert detect_document_type("Số định danh cá nhân: 040203015844") == ""
    assert detect_document_type("GIẤY KHAI SINH\nHọ, chữ đệm, tên: VÀNG A PHỈNH") == "Giấy khai sinh"
    assert detect_document_type("GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT\nSố vào sổ cấp GCN") == (
        "Giấy chứng nhận quyền sử dụng đất"
    )
    assert detect_document_type(
        "GIẤY CHỨNG NHẬN KẾT HÔN\nChồng: VŨ ĐÌNH THIẾT\n"
        "Số định danh cá nhân: 040203015844\nVợ: PHẠM NGỌC THỦY"
    ) == "Giấy chứng nhận kết hôn"
    assert detect_document_type("QUYẾT ĐỊNH\nSố: 12/QĐ-UBND\nVề việc giao đất") == "Quyết định"
    assert detect_document_type("CÔNG VĂN\nV/v xác minh hồ sơ chứng thực") == "Công văn"
    assert detect_document_type("", "Giấy CNQSD đất.pdf") == "Giấy chứng nhận quyền sử dụng đất"


def test_canonical_document_type_normalizes_llm_labels():
    assert canonical_document_type("Giấy chứng nhận đăng ký kết hôn") == "Giấy chứng nhận kết hôn"
    assert canonical_document_type("Thẻ căn cước công dân") == "Căn cước công dân"
    assert canonical_document_type("Quyết định giao đất") == "Quyết định"


def test_first_file_existing_component_next_files_are_new_components():
    files = [
        {"name": "ban-chinh.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AA=="},
        {"name": "cccd-mat-truoc.jpg", "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,AA=="},
        {"name": "giay-khai-sinh.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AA=="},
    ]
    ocr_results = [
        {"name": "ban-chinh.pdf", "text": "Bản chính giấy tờ văn bản"},
        {"name": "cccd-mat-truoc.jpg", "text": "CĂN CƯỚC CÔNG DÂN Số định danh cá nhân"},
        {"name": "giay-khai-sinh.pdf", "text": "GIẤY KHAI SINH"},
    ]

    items = build_plan_items(files, ocr_results)

    assert items[0]["target"] == "existing"
    assert items[0]["needsAddComponent"] is False
    assert items[0]["componentIndex"] == 1
    assert items[0]["componentName"] == DEFAULT_COPY_CERTIFICATION_COMPONENT
    assert items[1]["target"] == "new"
    assert items[1]["needsAddComponent"] is True
    assert items[1]["componentName"] == "Căn cước công dân"
    assert items[2]["target"] == "new"
    assert items[2]["componentName"] == "Giấy khai sinh"


def test_identity_file_does_not_take_default_component_when_land_doc_exists():
    files = [
        {"name": "1.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AA=="},
        {"name": "Giấy CNQSD đất 2.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AA=="},
    ]
    ocr_results = [
        {"name": "1.pdf", "text": "CĂN CƯỚC CÔNG DÂN Số định danh cá nhân"},
        {"name": "Giấy CNQSD đất 2.pdf", "text": "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT"},
    ]

    items = build_plan_items(files, ocr_results)

    assert items[0]["fileIndex"] == 1
    assert items[0]["target"] == "existing"
    assert items[0]["documentName"] == "Giấy CNQSD đất 2"
    assert items[1]["fileIndex"] == 0
    assert items[1]["target"] == "new"
    assert items[1]["componentName"] == "Căn cước công dân"
    assert items[1]["documentName"] == "Căn cước công dân"


def test_generic_photo_name_uses_detected_type_as_document_name():
    files = [
        {"name": "photo_1_2026-06-17_10-39-55.jpg", "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,AA=="}
    ]
    ocr_results = [
        {
            "name": "photo_1_2026-06-17_10-39-55.jpg",
            "text": "GIẤY CHỨNG NHẬN KẾT HÔN\nChồng: A\nVợ: B\nSố định danh cá nhân: 012345678901",
        }
    ]

    items = build_plan_items(files, ocr_results)

    assert items[0]["detectedType"] == "Giấy chứng nhận kết hôn"
    assert items[0]["documentName"] == "Giấy chứng nhận kết hôn"


def test_build_plan_prefers_llm_detection_from_ocr():
    files = [
        {"name": "photo_1_2026-06-17_10-39-55.jpg", "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,AA=="}
    ]
    ocr_results = [
        {
            "name": "photo_1_2026-06-17_10-39-55.jpg",
            "text": "Số định danh cá nhân: 012345678901\nChồng: A\nVợ: B",
        }
    ]

    items = build_plan_items(files, ocr_results, {0: "Giấy chứng nhận đăng ký kết hôn"})

    assert items[0]["detectedType"] == "Giấy chứng nhận kết hôn"
    assert items[0]["documentName"] == "Giấy chứng nhận kết hôn"


def test_build_plan_uses_llm_document_name_for_new_component():
    files = [
        {"name": "Giấy CNQSD đất.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AA=="},
        {"name": "1.JPG", "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,AA=="},
    ]
    ocr_results = [
        {"name": "Giấy CNQSD đất.pdf", "text": "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT"},
        {"name": "1.JPG", "text": "CĂN CƯỚC CÔNG DÂN\nHọ và tên: VŨ ĐÌNH THIẾT"},
    ]

    items = build_plan_items(
        files,
        ocr_results,
        {1: {"detectedType": "Căn cước công dân", "documentName": "Căn cước công dân Vũ Đình Thiết"}},
    )

    assert items[1]["target"] == "new"
    assert items[1]["detectedType"] == "Căn cước công dân"
    assert items[1]["documentName"] == "Căn cước công dân Vũ Đình Thiết"
    assert items[1]["componentName"] == "Căn cước công dân Vũ Đình Thiết"


def test_build_plan_dedupes_repeated_new_component_names():
    files = [
        {"name": "Giấy CNQSD đất.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AA=="},
        {"name": "photo_1_2026-06-17_10-39-55.jpg", "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,AA=="},
        {"name": "photo_2_2026-06-17_10-39-55.jpg", "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,AA=="},
    ]
    ocr_results = [
        {"name": "Giấy CNQSD đất.pdf", "text": "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT"},
        {"name": "photo_1_2026-06-17_10-39-55.jpg", "text": "CĂN CƯỚC CÔNG DÂN"},
        {"name": "photo_2_2026-06-17_10-39-55.jpg", "text": "CĂN CƯỚC CÔNG DÂN"},
    ]

    items = build_plan_items(files, ocr_results)

    assert [item["componentName"] for item in items[1:]] == ["Căn cước công dân", "Căn cước công dân 2"]
    assert [item["documentName"] for item in items[1:]] == ["Căn cước công dân", "Căn cước công dân 2"]


def test_decision_file_does_not_fall_back_to_generic_certification_name():
    files = [
        {"name": "photo_1_2026-06-17_10-39-55.jpg", "type": "image/jpeg", "dataUrl": "data:image/jpeg;base64,AA=="}
    ]
    ocr_results = [
        {"name": "photo_1_2026-06-17_10-39-55.jpg", "text": "QUYẾT ĐỊNH\nSố 123/QĐ-UBND\nVề việc giao đất"}
    ]

    items = build_plan_items(files, ocr_results)

    assert items[0]["detectedType"] == "Quyết định"
    assert items[0]["documentName"] == "Quyết định"


def test_duplicate_file_names_keep_positional_ocr_results():
    files = [
        {"name": "image.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AA=="},
        {"name": "image.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AA=="},
    ]
    ocr_results = [
        {"name": "image.pdf", "text": "GIẤY KHAI SINH"},
        {"name": "image.pdf", "text": "QUYẾT ĐỊNH\nSố 12/QĐ-UBND"},
    ]

    items = build_plan_items(files, ocr_results)

    assert [item["detectedType"] for item in items] == ["Giấy khai sinh", "Quyết định"]


def _segment_file_meta(count: int, *, pages: int = 1) -> dict[int, dict]:
    return {
        index: {"pageCount": pages, "pageBoundariesAvailable": True}
        for index in range(count)
    }


def test_mixed_pdf_is_split_into_logical_documents():
    files = [{"name": "mixed.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AA=="}]
    segments = [
        {
            "fileIndex": 0,
            "pageFrom": 1,
            "pageTo": 1,
            "detectedType": "Căn cước công dân",
            "documentName": "CCCD Nguyễn Quốc Việt",
            "subjectName": "Nguyễn Quốc Việt",
            "identityNumber": "068208012986",
            "logicalKey": "cccd-068208012986",
        },
        {
            "fileIndex": 0,
            "pageFrom": 2,
            "pageTo": 3,
            "detectedType": "Giấy khai sinh",
            "documentName": "Giấy khai sinh Nguyễn Quốc Việt",
            "subjectName": "Nguyễn Quốc Việt",
            "identityNumber": "",
            "logicalKey": "giay-khai-sinh-nguyen-quoc-viet",
        },
    ]
    file_meta = {0: {"pageCount": 3, "pageBoundariesAvailable": True}}
    pages = {
        0: {
            1: "CĂN CƯỚC CÔNG DÂN Số 068208012986 Họ và tên NGUYỄN QUỐC VIỆT",
            2: "GIẤY KHAI SINH NGUYỄN QUỐC VIỆT",
            3: "PHẦN GHI CHÚ GIẤY KHAI SINH",
        }
    }

    attachments, _ = build_segment_plan_items(files, segments, file_meta, pages, {})

    assert [item["documentName"] for item in attachments] == [
        "Giấy khai sinh Nguyễn Quốc Việt",
        "CCCD Nguyễn Quốc Việt",
    ]
    assert attachments[0]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [1, 2]}]
    assert attachments[1]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0]}]


@pytest.mark.asyncio
async def test_plan_preserves_mixed_source_by_default_and_splits_only_when_enabled(monkeypatch):
    async def fake_ocr_per_file(_files):
        return [{
            "name": "mixed.pdf",
            "text": (
                "───── Trang 1/3 ─────\nCĂN CƯỚC CÔNG DÂN\n"
                "───── Trang 2/3 ─────\nGIẤY KHAI SINH\n"
                "───── Trang 3/3 ─────\nPHẦN GHI CHÚ GIẤY KHAI SINH"
            ),
        }]

    async def fake_classify(_documents):
        return [
            {
                "fileIndex": 0,
                "pageFrom": 1,
                "pageTo": 1,
                "detectedType": "Căn cước công dân",
                "documentName": "CCCD Nguyễn Văn A",
                "identityNumber": "012345678901",
                "logicalKey": "cccd-a",
            },
            {
                "fileIndex": 0,
                "pageFrom": 2,
                "pageTo": 3,
                "detectedType": "Giấy khai sinh",
                "documentName": "Giấy khai sinh Nguyễn Văn A",
                "logicalKey": "khai-sinh-a",
            },
        ]

    async def fake_preserve(_documents):
        return [{
            "fileIndex": 0,
            "pageFrom": 1,
            "pageTo": 3,
            "detectedType": "Hồ sơ tổng hợp",
            "documentName": "Hồ sơ đăng ký khai sinh",
            "subjectName": "",
            "identityNumber": "",
            "logicalKey": "",
        }]

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner, "_classify_documents_with_llm", fake_classify)
    monkeypatch.setattr(planner, "_classify_source_files_with_llm", fake_preserve)
    monkeypatch.setattr(planner, "_pdf_page_count", lambda _file: 3)
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
    assert preserved["attachments"][0]["documentName"] == "Hồ sơ đăng ký khai sinh"
    assert "sourceSegments" not in preserved["attachments"][0]
    assert preserved["extracted"]["classified"][0]["pageFrom"] == 1
    assert preserved["extracted"]["classified"][0]["pageTo"] == 3

    assert split["extracted"]["documentSplitEnabled"] is True
    assert split["extracted"]["documentPromptMode"] == "split"
    assert len(split["attachments"]) == 2
    assert all("sourceSegments" in item for item in split["attachments"])


@pytest.mark.asyncio
async def test_split_dossier_mode_merges_front_and_back_of_same_identity(monkeypatch):
    async def fake_ocr_per_file(_files):
        return [
            {
                "name": "cccd-mat-truoc.jpg",
                "text": (
                    "CĂN CƯỚC CÔNG DÂN\nSố: 036193005241\n"
                    "Họ và tên: NGUYỄN THỊ BÍCH NHUNG"
                ),
            },
            {
                "name": "cccd-mat-sau.jpg",
                "text": (
                    "Đặc điểm nhận dạng / Personal identification\n"
                    "Ngón trỏ trái / Left index finger\n"
                    "IDVNM1930052419036193005241<<4"
                ),
            },
        ]

    async def fake_preserve(_documents):
        # Provider đôi khi chỉ nhận ra rõ mặt trước. Planner phải dùng OCR mặt sau làm fallback,
        # không được vì nhãn rỗng mà tách hai mặt thành hai hồ sơ/tab.
        return [
            {
                "fileIndex": 0,
                "pageFrom": 1,
                "pageTo": 1,
                "detectedType": "Căn cước công dân",
                "documentName": "CCCD Nguyễn Thị Bích Nhung",
                "subjectName": "Nguyễn Thị Bích Nhung",
                "identityNumber": "036193005241",
                "logicalKey": "cccd-036193005241",
            },
            {
                "fileIndex": 1,
                "pageFrom": 1,
                "pageTo": 1,
                "detectedType": "",
                "documentName": "",
                "subjectName": "",
                "identityNumber": "",
                "logicalKey": "",
            },
        ]

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner, "_classify_source_files_with_llm", fake_preserve)
    monkeypatch.setattr(planner, "_pdf_page_count", lambda _file: 1)
    files = [
        FileItem(
            name="cccd-mat-truoc.jpg",
            type="image/jpeg",
            dataUrl="data:image/jpeg;base64,AA==",
            role="doc",
        ),
        FileItem(
            name="cccd-mat-sau.jpg",
            type="image/jpeg",
            dataUrl="data:image/jpeg;base64,AA==",
            role="doc",
        ),
    ]

    result = await planner.plan(files, options={"splitMode": True})

    assert result["extracted"]["documentSplitEnabled"] is False
    assert len(result["attachments"]) == 1
    assert result["attachments"][0]["documentName"] == "CCCD Nguyễn Thị Bích Nhung"
    assert result["attachments"][0]["sourceSegments"] == [
        {"fileIndex": 0, "pageIndexes": None},
        {"fileIndex": 1, "pageIndexes": None},
    ]


def test_four_identity_faces_are_grouped_by_person_not_document_type():
    files = [
        {"name": "viet-front.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AA=="},
        {"name": "viet-back.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AA=="},
        {"name": "han-front.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AA=="},
        {"name": "han-back.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AA=="},
        {"name": "ket-qua-thi.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AA=="},
    ]
    people = [
        ("Nguyễn Quốc Việt", "068208012986"),
        ("Nguyễn Quốc Việt", "068208012986"),
        ("Dương Phạm Khánh Hàn", "068308001513"),
        ("Dương Phạm Khánh Hàn", "068308001513"),
    ]
    segments = []
    for index, (subject, number) in enumerate(people):
        is_back = index % 2 == 1
        segments.append({
            "fileIndex": index,
            "pageFrom": 1,
            "pageTo": 1,
            # Giả lập LLM không nhận ra metadata ở cả hai mặt sau. Planner vẫn phải dựa vào OCR
            # MRZ để ghép với đúng mặt trước, đồng thời tuyệt đối không gộp chéo hai chủ thể.
            "detectedType": "" if is_back else "Căn cước công dân",
            "documentName": "" if is_back else f"CCCD {subject}",
            "subjectName": "" if is_back else subject,
            "identityNumber": "" if is_back else number,
            "logicalKey": "" if is_back else f"cccd-{number}",
        })
    segments.append({
        "fileIndex": 4,
        "pageFrom": 1,
        "pageTo": 1,
        "detectedType": "Giấy chứng nhận kết quả thi",
        "documentName": "Giấy chứng nhận kết quả thi Nguyễn Quốc Việt",
        "subjectName": "Nguyễn Quốc Việt",
        "identityNumber": "",
        "logicalKey": "ket-qua-thi-68001713",
    })
    page_texts = {
        0: {1: "CĂN CƯỚC CÔNG DÂN 068208012986 NGUYỄN QUỐC VIỆT"},
        1: {1: "ĐẶC ĐIỂM NHẬN DẠNG IDVNM2080129860068208012986"},
        2: {1: "CĂN CƯỚC CÔNG DÂN 068308001513 DƯƠNG PHẠM KHÁNH HÀN"},
        3: {1: "ĐẶC ĐIỂM NHẬN DẠNG IDVNM3080015131068308001513"},
        4: {1: "GIẤY CHỨNG NHẬN KẾT QUẢ THI NGUYỄN QUỐC VIỆT"},
    }

    attachments, _ = build_segment_plan_items(
        files,
        segments,
        _segment_file_meta(len(files)),
        page_texts,
        {},
    )

    assert len(attachments) == 3
    identity_items = [item for item in attachments if item["detectedType"] == "Căn cước công dân"]
    assert [item["documentName"] for item in identity_items] == [
        "CCCD Nguyễn Quốc Việt",
        "CCCD Dương Phạm Khánh Hàn",
    ]
    assert [[source["fileIndex"] for source in item["sourceSegments"]] for item in identity_items] == [
        [0, 1],
        [2, 3],
    ]


def test_three_school_record_files_become_one_logical_attachment():
    files = [
        {"name": f"hoc-ba-{index}.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AA=="}
        for index in range(1, 4)
    ]
    segments = [
        {
            "fileIndex": index,
            "pageFrom": 1,
            "pageTo": 1,
            "detectedType": "Học bạ",
            "documentName": "Học bạ THPT Nguyễn Quốc Việt",
            "subjectName": "Nguyễn Quốc Việt",
            "identityNumber": "",
            "logicalKey": "hoc-ba-thpt-nguyen-quoc-viet-273-2023",
        }
        for index in range(3)
    ]

    attachments, _ = build_segment_plan_items(
        files,
        segments,
        _segment_file_meta(len(files)),
        {index: {1: "HỌC BẠ THPT NGUYỄN QUỐC VIỆT"} for index in range(3)},
        {},
    )

    assert len(attachments) == 1
    assert attachments[0]["documentName"] == "Học bạ THPT Nguyễn Quốc Việt"
    assert [source["fileIndex"] for source in attachments[0]["sourceSegments"]] == [0, 1, 2]


def test_llm_document_type_is_not_overridden_by_cccd_mentions_inside_document():
    files = [
        {"name": "cam-doan.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AA=="},
        {"name": "danh-sach-dat.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AA=="},
    ]
    segments = [
        {
            "fileIndex": 0,
            "pageFrom": 1,
            "pageTo": 1,
            "detectedType": "Giấy cam đoan",
            "documentName": "Giấy cam đoan Nguyễn Văn A",
            "subjectName": "Nguyễn Văn A",
            "identityNumber": "",
            "logicalKey": "giay-cam-doan-nguyen-van-a",
        },
        {
            "fileIndex": 1,
            "pageFrom": 1,
            "pageTo": 1,
            "detectedType": "Danh sách người sử dụng chung thửa đất",
            "documentName": "Danh sách người sử dụng chung thửa đất",
            "subjectName": "",
            "identityNumber": "",
            "logicalKey": "danh-sach-nguoi-su-dung-dat",
        },
    ]
    page_texts = {
        0: {1: "GIẤY CAM ĐOAN\nCCCD số 012345678901"},
        1: {1: "DANH SÁCH NGƯỜI SỬ DỤNG CHUNG THỬA ĐẤT\nCCCD 012345678901"},
    }

    attachments, classified = build_segment_plan_items(
        files,
        segments,
        _segment_file_meta(len(files)),
        page_texts,
        {},
    )

    assert [item["detectedType"] for item in attachments] == [
        "Giấy cam đoan",
        "Danh sách người sử dụng chung thửa đất",
    ]
    assert all(item["logicalGroup"] and not item["logicalGroup"].startswith("id:") for item in classified)


@pytest.mark.asyncio
async def test_plan_uses_one_batch_ocr_and_one_llm_request_for_duplicate_names(monkeypatch):
    calls = {"ocr": 0, "llm": 0}

    async def fake_ocr_per_file(files):
        calls["ocr"] += 1
        assert len(files) == 2
        return [
            {"name": "image.pdf", "text": "GIẤY KHAI SINH"},
            {"name": "image.pdf", "text": "QUYẾT ĐỊNH Số 12/QĐ-UBND"},
        ]

    async def fake_classify(documents):
        calls["llm"] += 1
        assert [item["fileIndex"] for item in documents] == [0, 1]
        return [
            {
                "fileIndex": 0,
                "pageFrom": 1,
                "pageTo": 1,
                "detectedType": "Giấy khai sinh",
                "documentName": "Giấy khai sinh Nguyễn Văn A",
                "subjectName": "Nguyễn Văn A",
                "logicalKey": "khai-sinh-a",
            },
            {
                "fileIndex": 1,
                "pageFrom": 1,
                "pageTo": 1,
                "detectedType": "Quyết định",
                "documentName": "Quyết định số 12",
                "subjectName": "",
                "logicalKey": "quyet-dinh-12",
            },
        ]

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner, "_classify_source_files_with_llm", fake_classify)
    result = await planner.plan([
        FileItem(name="image.pdf", type="application/pdf", dataUrl="data:application/pdf;base64,AA==", role="doc"),
        FileItem(name="image.pdf", type="application/pdf", dataUrl="data:application/pdf;base64,AA==", role="doc"),
    ])

    assert calls == {"ocr": 1, "llm": 1}
    assert [item["documentName"] for item in result["attachments"]] == [
        "Giấy khai sinh Nguyễn Văn A",
        "Quyết định số 12",
    ]
    assert "fileIndex=0 · image.pdf" in result["ocr_text"]
    assert "fileIndex=1 · image.pdf" in result["ocr_text"]

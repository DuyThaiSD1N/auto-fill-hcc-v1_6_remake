from app.attachments.planner import (
    DEFAULT_COPY_CERTIFICATION_COMPONENT,
    build_plan_items,
    canonical_document_type,
    detect_document_type,
    normalize_document_name,
)


def test_document_name_normalizes_decomposed_vietnamese():
    raw = "Gia\u0302\u0301y CNQSD đa\u0302\u0301t 2.pdf"

    assert normalize_document_name(raw, "Giấy chứng nhận quyền sử dụng đất") == "Giấy CNQSD đất 2"


def test_detect_document_type_from_common_ocr_text():
    assert detect_document_type("CĂN CƯỚC CÔNG DÂN\nSố định danh cá nhân: 040203015844") == "Căn cước công dân"
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

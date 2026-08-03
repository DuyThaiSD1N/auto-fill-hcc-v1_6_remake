"""Attachment routing tests cho cấp GCN ATTP nông, lâm, thủy sản."""

from app.pipelines.cap_gcn_attp_nong_lam_thuy_san.attach import planner


def _raw(name: str) -> dict:
    return {"name": name, "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AAA"}


def test_attachment_plan_routes_two_rows_adds_cccd_and_skips_business_registration():
    files = [
        _raw("file-1.pdf"),
        _raw("file-2.pdf"),
        _raw("file-3.pdf"),
        _raw("file-4.pdf"),
    ]
    ocr_results = [
        {
            "name": "file-1.pdf",
            "text": "ĐƠN ĐỀ NGHỊ CẤP GIẤY CHỨNG NHẬN CƠ SỞ ĐỦ ĐIỀU KIỆN AN TOÀN THỰC PHẨM Tên cơ sở Mặt hàng sản xuất",
        },
        {
            "name": "file-2.pdf",
            "text": "BẢN THUYẾT MINH Điều kiện bảo đảm an toàn thực phẩm I. THÔNG TIN CHUNG II. MÔ TẢ VỀ SẢN PHẨM",
        },
        {"name": "file-3.pdf", "text": "CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số 048075012345"},
        {"name": "file-4.pdf", "text": "GIẤY CHỨNG NHẬN ĐĂNG KÝ HỘ KINH DOANH Mã số doanh nghiệp"},
    ]

    attachments, warnings, classified = planner.build_plan_items(files, ocr_results)

    assert warnings == []
    assert [item["fileIndex"] for item in attachments] == [0, 1, 2]
    assert [item["detectedType"] for item in attachments] == ["don_de_nghi", "thuyet_minh", "cccd"]
    assert all(item["target"] == "attp-row" for item in attachments[:2])
    assert all(item["needsAddComponent"] is False for item in attachments[:2])
    assert all(item["loaiBan"] == "Bản chính" for item in attachments)
    assert "Phụ lục I" in attachments[0]["componentName"]
    assert "Bản thuyết minh về cơ sở vật chất" in attachments[1]["componentName"]
    assert attachments[2]["target"] == "add-document-dialog"
    assert attachments[2]["needsAddComponent"] is True
    assert attachments[2]["quantity"] == 1
    assert "Trường hợp nộp trực tiếp" in attachments[2]["componentName"]
    assert attachments[2]["documentName"] == "Căn cước công dân_File 3"
    assert classified[2]["documentName"] == "Căn cước công dân_File 3"
    assert classified[3]["skipped"] is True


def test_cccd_attachment_uses_holder_name_from_ocr():
    files = [_raw("cccd_thiet.pdf")]
    ocr_results = [{
        "name": "cccd_thiet.pdf",
        "text": "CĂN CƯỚC CÔNG DÂN\nHọ và tên / Full name:\nVŨ ĐÌNH THIẾT\nSố / No.: 040203015844",
    }]

    attachments, warnings, classified = planner.build_plan_items(files, ocr_results)

    assert warnings == []
    assert attachments == [{
        "fileIndex": 0,
        "fileName": "cccd_thiet.pdf",
        "documentName": "Căn cước công dân_Vũ Đình Thiết",
        "componentName": planner._CCCD_COMPONENT,
        "loaiBan": "Bản chính",
        "quantity": 1,
        "target": "add-document-dialog",
        "needsAddComponent": True,
        "detectedType": "cccd",
    }]
    assert classified[0]["documentName"] == "Căn cước công dân_Vũ Đình Thiết"


def test_attachment_plan_uses_llm_result_for_every_rule_other():
    files = [_raw("scan-kho-doc.pdf")]
    ocr_results = [{"name": "scan-kho-doc.pdf", "text": "Tài liệu bị OCR mất tiêu đề nhưng còn nội dung mô tả cơ sở."}]

    attachments, warnings, classified = planner.build_plan_items(
        files,
        ocr_results,
        {0: "thuyet_minh"},
    )

    assert warnings == []
    assert attachments[0]["detectedType"] == "thuyet_minh"
    assert classified == [{"fileName": "scan-kho-doc.pdf", "docType": "thuyet_minh", "source": "llm"}]


def test_attachment_plan_warns_when_llm_still_returns_other():
    files = [_raw("tai-lieu-khac.pdf")]
    ocr_results = [{"name": "tai-lieu-khac.pdf", "text": "Nội dung không đủ xác định."}]

    attachments, warnings, classified = planner.build_plan_items(files, ocr_results, {0: "other"})

    assert attachments == []
    assert warnings == [
        "Không xác định được loại giấy tờ cho file 'tai-lieu-khac.pdf' — vui lòng đính kèm thủ công."
    ]
    assert classified[0]["docType"] == "other"

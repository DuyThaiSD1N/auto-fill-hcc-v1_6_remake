"""Attachment routing tests cho cấp GCN ATTP nông, lâm, thủy sản."""

from app.pipelines.cap_gcn_attp_nong_lam_thuy_san.attach import planner


def _raw(name: str) -> dict:
    return {"name": name, "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AAA"}


def test_attachment_plan_routes_two_rows_adds_cccd_and_business_registration_to_don_row():
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
    # Giấy ĐKKD không bị bỏ: đính chung dòng Đơn (Phụ lục I); CCCD (modal) xếp cuối.
    assert [item["fileIndex"] for item in attachments] == [0, 1, 3, 2]
    assert [item["detectedType"] for item in attachments] == ["don_de_nghi", "thuyet_minh", "gcn_dkkd", "cccd"]
    attachments = [attachments[0], attachments[1], attachments[3], attachments[2]]
    assert attachments[3]["componentName"] == attachments[0]["componentName"]
    assert all(item["target"] == "attp-row" for item in attachments[:2])
    assert all(item["needsAddComponent"] is False for item in attachments[:2])
    assert all(item["loaiBan"] == "Bản chính" for item in attachments)
    assert "Phụ lục I" in attachments[0]["componentName"]
    assert "Bản thuyết minh về cơ sở vật chất" in attachments[1]["componentName"]
    assert attachments[2]["target"] == "add-document-dialog"
    assert attachments[2]["needsAddComponent"] is True
    assert attachments[2]["quantity"] == 1
    assert "Trường hợp nộp trực tiếp" in attachments[2]["componentName"]
    assert attachments[2]["documentName"] == "Căn cước công dân"
    assert classified[2]["docType"] == "cccd"
    assert classified[3]["routedTo"] == "don_de_nghi"


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

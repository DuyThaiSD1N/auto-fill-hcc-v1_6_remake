"""Attachment classification/route tests cho thủ tục xóa đăng ký tàu cá."""

from app.attachments.schemas import AttachmentPlanResp
from app.pipelines.xoa_dang_ky_tau_ca.attach import planner


def _file(name: str) -> dict:
    return {"name": name, "type": "application/pdf", "dataUrl": "data:application/pdf;base64,AAA"}


def _ocr(name: str, text: str) -> dict:
    return {"name": name, "text": text}


def test_combined_sample_pdf_routes_whole_file_to_mau_10_row():
    name = "ho-so-gop.pdf"
    files = [_file(name)]
    ocr = [_ocr(
        name,
        "TỜ KHAI XÓA ĐĂNG KÝ TÀU CÁ Mẫu số 10.ĐKT HỢP ĐỒNG MUA BÁN TÀU CÁ "
        "GIẤY CHỨNG NHẬN ĐĂNG KÝ TÀU CÁ CĂN CƯỚC CÔNG DÂN",
    )]

    items, warnings, classified = planner.build_plan_items(files, ocr, {})

    assert warnings == []
    assert len(items) == 1
    assert items[0]["target"] == "attp-row"
    assert items[0]["loaiBan"] == "Bản chính"
    assert items[0]["detectedType"] == "to_khai_10"
    assert "Tờ khai xóa đăng ký tàu cá theo Mẫu số 10.ĐKT" in items[0]["componentName"]
    assert classified[0]["docType"] == "to_khai_10"


def test_two_file_sample_returns_fixed_row_then_dynamic_cccd_without_warning():
    files = [_file("ho-so-gop.pdf"), _file("cccd_thiet.pdf")]
    ocr = [
        _ocr(
            "ho-so-gop.pdf",
            "TỜ KHAI XÓA ĐĂNG KÝ TÀU CÁ Mẫu số 10.ĐKT HỢP ĐỒNG MUA BÁN TÀU CÁ "
            "GIẤY CHỨNG NHẬN ĐĂNG KÝ TÀU CÁ",
        ),
        _ocr("cccd_thiet.pdf", "CĂN CƯỚC CÔNG DÂN Số 040203015844 Họ tên VŨ ĐÌNH THIẾT"),
    ]

    items, warnings, _ = planner.build_plan_items(files, ocr, {})

    assert warnings == []
    assert [(item["fileIndex"], item["target"]) for item in items] == [
        (0, "attp-row"),
        (1, "add-document-dialog"),
    ]
    assert items[1]["loaiBan"] == "Bản chính"
    assert items[1]["quantity"] == 1
    assert items[1]["documentName"] == "Căn cước công dân_Vũ Đình Thiết"
    response = AttachmentPlanResp(attachments=items)
    assert response.attachments[1].target == "add-document-dialog"
    assert response.attachments[1].quantity == 1


def test_routes_all_four_fixed_rows_by_exact_component_text():
    files = [_file("13.pdf"), _file("12.pdf"), _file("11.pdf"), _file("10.pdf")]
    ocr = [
        _ocr("13.pdf", "GIẤY CHỨNG NHẬN XÓA ĐĂNG KÝ Mẫu số 13.ĐKT"),
        _ocr("12.pdf", "BIÊN BẢN XÁC NHẬN TÌNH TRẠNG CỦA TÀU Mẫu số 12.ĐKT"),
        _ocr("11.pdf", "BIÊN BẢN XÁC MINH TÌNH TRẠNG CỦA TÀU Mẫu số 11.ĐKT"),
        _ocr("10.pdf", "TỜ KHAI XÓA ĐĂNG KÝ TÀU CÁ Mẫu số 10.ĐKT"),
    ]

    items, warnings, _ = planner.build_plan_items(files, ocr, {})

    assert warnings == []
    assert {item["detectedType"] for item in items} == {
        "mau_13_xoa_dang_ky",
        "mau_12_xac_nhan_tinh_trang",
        "mau_11_xac_minh_tinh_trang",
        "to_khai_10",
    }
    assert all(item["target"] == "attp-row" for item in items)
    assert all(item["needsAddComponent"] is False for item in items)


def test_supporting_docs_fall_back_to_mau_10_while_cccd_uses_add_document_dialog():
    files = [_file("contract.pdf"), _file("loi_chung.pdf"), _file("registration.pdf"), _file("identity.pdf")]
    ocr = [
        _ocr("contract.pdf", "HỢP ĐỒNG MUA BÁN TÀU CÁ BÊN BÁN BÊN MUA"),
        _ocr("loi_chung.pdf", "LỜI CHỨNG CỦA CÔNG CHỨNG VIÊN"),
        _ocr("registration.pdf", "GIẤY CHỨNG NHẬN ĐĂNG KÝ TÀU CÁ Số đăng ký Chủ tàu Cơ quan đăng ký"),
        _ocr("identity.pdf", "CĂN CƯỚC CÔNG DÂN"),
    ]

    items, warnings, classified = planner.build_plan_items(files, ocr, {})

    assert warnings == []
    assert len(items) == 4
    supporting = items[:3]
    assert all(item["target"] == "attp-row" for item in supporting)
    assert all("Tờ khai xóa đăng ký tàu cá theo Mẫu số 10.ĐKT" in item["componentName"] for item in supporting)
    assert [item["documentName"] for item in supporting] == [
        "Hợp đồng mua bán tàu cá đã công chứng",
        "Lời chứng của công chứng viên",
        "Giấy chứng nhận đăng ký tàu cá cũ",
    ]
    cccd = items[3]
    assert cccd["fileIndex"] == 3
    assert cccd["target"] == "add-document-dialog"
    assert cccd["loaiBan"] == "Bản chính"
    assert cccd["quantity"] == 1
    assert cccd["needsAddComponent"] is True
    assert "Trường hợp nộp trực tiếp" in cccd["componentName"]
    assert "giấy chứng minh nhân dân hoặc hộ chiếu" in cccd["componentName"]
    assert {item["docType"] for item in classified} == {
        "hop_dong_mua_ban",
        "gcn_dang_ky_tau_ca",
        "cccd",
    }
    fallback = [item for item in classified if item.get("fallbackComponent")]
    assert len(fallback) == 3
    assert all(item["fallbackComponent"] == "to_khai_10" for item in fallback)


def test_cccd_files_use_holder_names_instead_of_duplicate_generic_names():
    files = [_file("5_CCCD_HuynhThiHong.pdf"), _file("cccd_thiet.pdf")]
    ocr = [
        _ocr(
            "5_CCCD_HuynhThiHong.pdf",
            "CĂN CƯỚC CÔNG DÂN\nHọ và tên / Full name:\nHUỲNH THỊ HỒNG\nNgày sinh: 26/09/1970",
        ),
        _ocr(
            "cccd_thiet.pdf",
            "CĂN CƯỚC CÔNG DÂN\nHọ và tên / Full name:\nVŨ ĐÌNH THIẾT\nNgày sinh: 26/04/2003",
        ),
    ]

    items, warnings, _ = planner.build_plan_items(files, ocr, {})

    assert warnings == []
    assert [item["documentName"] for item in items] == [
        "Căn cước công dân_Huỳnh Thị Hồng",
        "Căn cước công dân_Vũ Đình Thiết",
    ]
    assert all(item["componentName"] == planner._CCCD_COMPONENT for item in items)


def test_six_file_dossier_routes_all_files_without_manual_warning():
    files = [
        _file("1_ToKhaiXoaDangKyTau.pdf"),
        _file("2_HopDongMuaBanTauCa.pdf"),
        _file("3_LoiChungCongChungVien.pdf"),
        _file("4_GiayChungNhanDangKyTauCa.pdf"),
        _file("5_CCCD_HuynhThiHong.pdf"),
        _file("cccd_thiet.pdf"),
    ]
    ocr = [
        _ocr(files[0]["name"], "TỜ KHAI XÓA ĐĂNG KÝ TÀU CÁ Mẫu số 10.ĐKT"),
        _ocr(files[1]["name"], "HỢP ĐỒNG MUA BÁN TÀU CÁ BÊN BÁN BÊN MUA"),
        _ocr(files[2]["name"], "LỜI CHỨNG CỦA CÔNG CHỨNG VIÊN"),
        _ocr(files[3]["name"], "GIẤY CHỨNG NHẬN ĐĂNG KÝ TÀU CÁ Số đăng ký Chủ tàu"),
        _ocr(files[4]["name"], "CĂN CƯỚC CÔNG DÂN\nHọ và tên:\nHUỲNH THỊ HỒNG"),
        _ocr(files[5]["name"], "CĂN CƯỚC CÔNG DÂN\nHọ và tên:\nVŨ ĐÌNH THIẾT"),
    ]

    items, warnings, _ = planner.build_plan_items(files, ocr, {})

    assert warnings == []
    assert len(items) == 6
    assert all(item["target"] == "attp-row" for item in items[:4])
    assert len({item["componentName"] for item in items[:4]}) == 1
    assert "Mẫu số 10.ĐKT" in items[0]["componentName"]
    assert all(item["target"] == "add-document-dialog" for item in items[4:])
    assert [item["documentName"] for item in items[4:]] == [
        "Căn cước công dân_Huỳnh Thị Hồng",
        "Căn cước công dân_Vũ Đình Thiết",
    ]


def test_llm_specific_type_wins_over_rule_fallback():
    files = [_file("scan.pdf")]
    ocr = [_ocr("scan.pdf", "văn bản OCR mờ có chữ tàu cá")]

    items, warnings, classified = planner.build_plan_items(files, ocr, {0: "mau_12_xac_nhan_tinh_trang"})

    assert warnings == []
    assert items[0]["detectedType"] == "mau_12_xac_nhan_tinh_trang"
    assert classified[0]["source"] == "llm"

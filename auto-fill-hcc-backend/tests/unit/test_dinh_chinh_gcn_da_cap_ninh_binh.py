from app.pipelines.dinh_chinh_gcn_da_cap_ninh_binh.attach import planner
from app.pipelines.dinh_chinh_gcn_da_cap_ninh_binh.process import mapper
from app.pipelines.dinh_chinh_gcn_da_cap_ninh_binh.process.prompt import EXTRA_RULES
from app.pipelines.dinh_chinh_gcn_da_cap_ninh_binh.process.schema import FIELDS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


def test_mapper_self_filing_uses_complete_owner_facts_for_applicant_and_receiver():
    source = [
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "ChuHoSo_NgaySinh", "value": "09/04/1965"},
        {"name": "ChuHoSo_GioiTinh", "value": "Nam"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "034 065 010 368"},
        {"name": "ChuHoSo_NgayCap", "value": "31/05/2023"},
        {"name": "ChuHoSo_NoiCap", "value": "Cục CS QLHC về TTXH"},
        {
            "name": "ChuHoSo_NoiCuTru",
            "value": {"quocGia": "Việt Nam", "tinh": "Lâm Đồng", "xa": "Phường 9", "diaChi": "10 Ngõ Văn Sở"},
        },
        {"name": "ChuHoSo_DienThoai", "value": "0982 094 963"},
        {"name": "Don_NoiDungDeNghi", "value": "Đính chính năm sinh trên Giấy chứng nhận"},
    ]

    fields, errors = mapper.enrich(source)
    values = _values(fields)

    assert errors == []
    assert values["data[ownerFullname]"] == "NGUYỄN VĂN A"
    assert values["data[isOwnerDossier]"] is True
    assert values["data[fullname]"] == "NGUYỄN VĂN A"
    assert values["data[birthday]"] == "09/04/1965"
    assert values["data[identityNumber]"] == "034065010368"
    assert values["data[province]"] == "Tỉnh Lâm Đồng"
    assert values["data[district]"] == "Phường Lâm Viên - Đà Lạt"
    assert values["data[address]"] == "10 Ngõ Văn Sở"
    assert values["data[hoTen]"] == "NGUYỄN VĂN A"
    assert values["data[soCCCD]"] == "034065010368"
    assert values["data[diaChi]"] == "10 Ngõ Văn Sở, Phường Lâm Viên - Đà Lạt, Lâm Đồng"
    assert "data[organization]" not in values


def test_mapper_authorized_applicant_does_not_replace_owner():
    source = [
        {"name": "ChuHoSo_HoTen", "value": "NGƯỜI ỦY QUYỀN"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "001111111111"},
        {"name": "NguoiNop_HoTen", "value": "NGƯỜI ĐƯỢC ỦY QUYỀN"},
        {"name": "NguoiNop_NgaySinh", "value": "01/02/1980"},
        {"name": "NguoiNop_GioiTinh", "value": "Nam"},
        {"name": "NguoiNop_SoDinhDanh", "value": "002222222222"},
        {"name": "NguoiNop_NgayCap", "value": "03/04/2022"},
        {
            "name": "NguoiNop_NoiCuTru",
            "value": {"quocGia": "Việt Nam", "tinh": "Ninh Bình", "xa": "Xã Nghĩa Hưng", "diaChi": "Thôn Nam Phú"},
        },
    ]

    fields, _ = mapper.enrich(source)
    values = _values(fields)

    assert values["data[ownerFullname]"] == "NGƯỜI ỦY QUYỀN"
    assert values["data[isOwnerDossier]"] is False
    assert values["data[fullname]"] == "NGƯỜI ĐƯỢC ỦY QUYỀN"
    assert values["data[identityNumber]"] == "002222222222"
    assert values["data[address]"] == "Thôn Nam Phú"


def test_attachment_routes_match_real_html_order_without_duplicate_files():
    files = [
        {"name": "don.pdf", "type": "application/pdf"},
        {"name": "uy-quyen.pdf", "type": "application/pdf"},
        {"name": "khai-sinh.pdf", "type": "application/pdf"},
        {"name": "gcn.pdf", "type": "application/pdf"},
    ]
    ocr = [{"name": item["name"], "text": "ocr"} for item in files]

    attachments, warnings, classified = planner.build_plan_items(
        files,
        ocr,
        {0: "application", 1: "authorization", 2: "error_proof", 3: "land_certificate"},
    )

    assert warnings == []
    assert len(attachments) == len(files)
    assert [item["fileIndex"] for item in attachments] == [0, 1, 2, 3]
    assert [item["componentIndex"] for item in attachments] == [0, 1, 2, 3]
    assert all(item["target"] == "attp-row" for item in attachments)
    assert all(item["loaiBan"] == "Bản chính" for item in attachments)
    assert [item["docType"] for item in classified] == [
        "application",
        "authorization",
        "error_proof",
        "land_certificate",
    ]


def test_identity_is_attached_once_with_application_component():
    files = [{"name": "cccd.pdf", "type": "application/pdf"}]
    ocr = [{"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN Citizen Identity Card"}]

    attachments, warnings, _ = planner.build_plan_items(files, ocr, {0: "identity"})

    assert warnings == []
    assert len(attachments) == 1
    assert attachments[0]["componentIndex"] == 0
    assert "Đơn đăng ký biến động" in attachments[0]["componentName"]


def test_llm_classification_is_used_before_rule_fallback():
    files = [{"name": "tai-lieu.pdf", "type": "application/pdf"}]
    ocr = [{"name": "tai-lieu.pdf", "text": "GIẤY KHAI SINH"}]

    attachments, _, classified = planner.build_plan_items(files, ocr, {0: "authorization"})

    assert attachments[0]["componentIndex"] == 1
    assert classified[0]["source"] == "llm"


def test_rules_cover_the_four_sample_document_families():
    assert planner._rule_doc_type("Mẫu số 18 ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI") == "application"
    assert planner._rule_doc_type("GIẤY ỦY QUYỀN BÊN ĐƯỢC ỦY QUYỀN") == "authorization"
    assert planner._rule_doc_type("GIẤY KHAI SINH") == "error_proof"
    assert planner._rule_doc_type("GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT Thửa đất số 10") == "land_certificate"


def test_schema_and_prompt_define_owner_applicant_and_mau_18_content():
    names = {field["name"] for field in FIELDS}
    assert "ChuHoSo_HoTen" in names
    assert "NguoiNop_HoTen" in names
    assert "Don_NoiDungDeNghi" in names
    assert "BÊN ĐƯỢC ỦY QUYỀN" in EXTRA_RULES
    assert "Nội dung biến động" in EXTRA_RULES
    assert "DỪNG TRƯỚC" in EXTRA_RULES


def test_registry_has_scoped_ninh_binh_procedure_and_both_pipelines():
    key = "dinh-chinh-gcn-da-cap-ninh-binh"
    procedure = get_procedure(key)

    assert procedure is not None
    assert procedure["label"].startswith("[Tỉnh Ninh Bình]")
    assert procedure["mode"] == "agent"
    assert procedure["hasAttachmentStep"] is True
    assert procedure["detect"]["urlScope"] == ["dichvucong.ninhbinh.gov.vn"]
    assert procedure["detect"]["textIncludes"] == ["Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót"]
    assert get_pipeline(key) is not None
    assert get_attach_pipeline(key) is not None

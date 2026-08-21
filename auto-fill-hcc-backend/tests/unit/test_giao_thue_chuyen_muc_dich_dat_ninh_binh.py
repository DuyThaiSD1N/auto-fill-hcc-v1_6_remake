from app.pipelines.giao_thue_chuyen_muc_dich_dat_ninh_binh.attach import planner
from app.pipelines.giao_thue_chuyen_muc_dich_dat_ninh_binh.process import mapper
from app.pipelines.giao_thue_chuyen_muc_dich_dat_ninh_binh.process.prompt import EXTRA_RULES
from app.pipelines.giao_thue_chuyen_muc_dich_dat_ninh_binh.process.schema import FIELDS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


def _values(fields):
    return {item["name"]: item["value"] for item in fields}


def test_authorized_applicant_is_separate_from_land_owner_and_year_only_birth_is_omitted():
    fields = [
        {"name": "ChuHoSo_HoTen", "value": "HOÀNG VĂN KHOA"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "036067012107"},
        {"name": "ChuHoSo_DienThoai", "value": "0912099483"},
        {"name": "ChuHoSo_NoiCuTru", "value": {"quocGia": "Việt Nam", "tinh": "Ninh Bình", "xa": "Xã Nghĩa Hưng", "diaChi": "Thôn Nam Phú"}},
        {"name": "NguoiNop_HoTen", "value": "PHẠM THỊ HÒA"},
        {"name": "NguoiNop_NgaySinh", "value": "1985"},
        {"name": "NguoiNop_GioiTinh", "value": "Nữ"},
        {"name": "NguoiNop_SoDinhDanh", "value": "036 185 022 192"},
        {"name": "NguoiNop_NgayCap", "value": "31/03/2025"},
        {"name": "NguoiNop_NoiCap", "value": "Bộ Công an"},
        {"name": "NguoiNop_NoiCuTru", "value": {"quocGia": "Việt Nam", "tinh": "Ninh Bình", "xa": "Xã Nghĩa Hưng", "diaChi": "Thôn Nghĩa Hiệp"}},
        {"name": "Don_NoiDungDeNghi", "value": "Gia hạn thời hạn sử dụng đất"},
    ]

    out, warnings = mapper.enrich(fields)
    values = _values(out)

    assert values["data[ownerFullname]"] == "HOÀNG VĂN KHOA"
    assert values["data[isOwnerDossier]"] is False
    assert values["data[fullname]"] == "PHẠM THỊ HÒA"
    assert values["data[gender]"] == "Nữ"
    assert values["data[identityNumber]"] == "036185022192"
    assert values["data[identityDate]"] == "31/03/2025"
    assert values["data[identityAgency]"] == "Bộ Công an"
    assert values["data[province]"] == "Tỉnh Ninh Bình"
    assert values["data[district]"] == "Xã Nghĩa Hưng"
    assert values["data[address]"] == "Thôn Nghĩa Hiệp"
    assert values["data[hoTen]"] == "PHẠM THỊ HÒA"
    assert values["data[soCCCD]"] == "036185022192"
    assert "Thôn Nghĩa Hiệp" in values["data[diaChi]"]
    assert "data[birthday]" not in values
    assert "data[phoneNumber]" not in values
    assert "data[organization]" not in values
    assert warnings == []


def test_no_authorization_copies_owner_facts_to_applicant_and_checks_owner_box():
    fields = [
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "ChuHoSo_NgaySinh", "value": "02/03/1980"},
        {"name": "ChuHoSo_GioiTinh", "value": "Nam"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "123456789012"},
        {"name": "ChuHoSo_NgayCap", "value": "04/05/2022"},
        {"name": "ChuHoSo_NoiCap", "value": "Cục CS QLHC về TTXH"},
        {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Ninh Bình", "xa": "Xã Nghĩa Hưng", "diaChi": "Thôn A"}},
        {"name": "ChuHoSo_DienThoai", "value": "0912345678"},
    ]

    out, warnings = mapper.enrich(fields)
    values = _values(out)

    assert values["data[isOwnerDossier]"] is True
    assert values["data[fullname]"] == "NGUYỄN VĂN A"
    assert values["data[birthday]"] == "02/03/1980"
    assert values["data[identityNumber]"] == "123456789012"
    assert values["data[phoneNumber]"] == "0912345678"
    assert values["data[hoTen]"] == "NGUYỄN VĂN A"
    assert warnings == []


def test_address_prompt_prioritizes_numbered_address_over_shortened_certificate_address():
    descriptions = {field["name"]: field["desc"] for field in FIELDS}

    assert "dòng đánh số '2. Địa chỉ:'" in descriptions["ChuHoSo_NoiCuTru"]
    assert "GCN rút gọn không được ghi đè" in descriptions["ChuHoSo_NoiCuTru"]
    assert "giống NGUYÊN VẸN ChuHoSo_NoiCuTru" in EXTRA_RULES
    assert 'Dòng "3. Địa chỉ liên hệ:" là thông tin liên hệ riêng' in EXTRA_RULES


def test_attachment_gcn_uses_only_renewal_row_when_dossier_has_mau_04():
    files = [
        {"name": "gcn.pdf", "type": "application/pdf"},
        {"name": "don.pdf", "type": "application/pdf"},
        {"name": "uy-quyen.pdf", "type": "application/pdf"},
        {"name": "cccd.pdf", "type": "application/pdf"},
        {"name": "khac.pdf", "type": "application/pdf"},
    ]
    ocr = [{"name": item["name"], "text": "ocr"} for item in files]
    attachments, warnings, classified = planner.build_plan_items(
        files,
        ocr,
        {0: "gcn", 1: "don_mau_04", 2: "uy_quyen", 3: "cccd", 4: "other"},
    )

    assert [(item["fileIndex"], item["componentIndex"]) for item in attachments] == [
        (0, 14), (1, 15), (2, 16)
    ]
    assert all(item["target"] == "attp-row" for item in attachments)
    assert all(item["loaiBan"] == "Bản chính" for item in attachments)
    assert all(item["needsAddComponent"] is False for item in attachments)
    assert len(warnings) == 1
    assert "khac.pdf" in warnings[0]
    assert next(item for item in classified if item["fileName"] == "cccd.pdf")["skipped"] is True


def test_attachment_change_purpose_dossier_has_three_files_and_three_plan_items():
    files = [
        {"name": "don.pdf", "type": "application/pdf"},
        {"name": "gcn.pdf", "type": "application/pdf"},
        {"name": "uy-quyen.pdf", "type": "application/pdf"},
    ]
    ocr = [{"name": item["name"], "text": "ocr"} for item in files]

    attachments, warnings, classified = planner.build_plan_items(
        files,
        ocr,
        {0: "don_mau_01", 1: "gcn", 2: "uy_quyen"},
    )

    assert [(item["fileIndex"], item["componentIndex"]) for item in attachments] == [
        (0, 2), (1, 4), (2, 16)
    ]
    assert next(item for item in classified if item["docType"] == "gcn")["componentIndexes"] == [4]
    assert warnings == []


def test_attachment_gcn_is_not_forced_when_application_branch_is_unknown():
    files = [{"name": "gcn.pdf", "type": "application/pdf"}]
    ocr = [{"name": "gcn.pdf", "text": "ocr"}]

    attachments, warnings, classified = planner.build_plan_items(files, ocr, {0: "gcn"})

    assert attachments == []
    assert len(warnings) == 1
    assert "không xác định được nhánh" in warnings[0]
    assert classified[0]["skipped"] is True
    assert classified[0]["reason"] == "unresolved_branch"


def test_change_purpose_application_title_is_a_confident_mau_01_rule():
    assert planner._rule_doc_type("ĐƠN ĐỀ NGHỊ CHO PHÉP CHUYỂN MỤC ĐÍCH SỬ DỤNG ĐẤT") == "don_mau_01"


def test_registry_has_scoped_ninh_binh_process_and_attachment_pipeline():
    key = "giao-thue-chuyen-muc-dich-dat-ninh-binh"
    procedure = get_procedure(key)

    assert procedure is not None
    assert procedure["mode"] == "agent"
    assert procedure["hasAttachmentStep"] is True
    assert procedure["detect"]["urlScope"] == ["dichvucong.ninhbinh.gov.vn"]
    assert len(procedure["detect"]["textIncludes"]) == 2
    assert get_pipeline(key) is not None
    assert get_attach_pipeline(key) is not None

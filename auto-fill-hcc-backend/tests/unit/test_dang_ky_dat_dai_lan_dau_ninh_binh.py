from app.pipelines.dang_ky_dat_dai_lan_dau_ninh_binh.attach import planner
from app.pipelines.dang_ky_dat_dai_lan_dau_ninh_binh.process import mapper
from app.pipelines.dang_ky_dat_dai_lan_dau_ninh_binh.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_dat_dai_lan_dau_ninh_binh.process.schema import FIELDS, UI_COMP_BY_NAME
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


def test_mapper_self_filing_uses_owner_facts_and_fixed_note():
    source = [
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "ChuHoSo_NgaySinh", "value": "09/04/1965"},
        {"name": "ChuHoSo_GioiTinh", "value": "Nam"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "034 065 010 368"},
        {"name": "ChuHoSo_NgayCap", "value": "31/05/2023"},
        {"name": "ChuHoSo_NoiCap", "value": "Cục CS QLHC về TTXH"},
        {
            "name": "ChuHoSo_NoiCuTru",
            "value": {"quocGia": "Việt Nam", "tinh": "Ninh Bình", "xa": "Xã Nghĩa Hưng", "diaChi": "Thôn Nam Phú"},
        },
        {"name": "ChuHoSo_DienThoai", "value": "0982 094 963"},
        {"name": "Don_NoiDungDangKy", "value": "Đề nghị cấp Giấy chứng nhận quyền sử dụng đất lần đầu"},
    ]

    fields, errors = mapper.enrich(source)
    values = _values(fields)

    assert errors == []
    assert values["data[ownerFullname]"] == "NGUYỄN VĂN A"
    assert values["data[isOwnerDossier]"] is True
    assert values["data[fullname]"] == "NGUYỄN VĂN A"
    assert values["data[birthday]"] == "09/04/1965"
    assert values["data[identityNumber]"] == "034065010368"
    assert values["data[noidungyeucaugiaiquyet]"] == "Đề nghị cấp Giấy chứng nhận quyền sử dụng đất lần đầu"
    # Ghi chú cố định luôn được điền (đặc thù form không có dòng CCCD riêng).
    assert values["data[note]"].startswith("CCCD/Căn cước của (các) người liên quan")
    assert values["data[hoTen]"] == "NGUYỄN VĂN A"
    assert values["data[soCCCD]"] == "034065010368"


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


def test_attachment_routes_match_real_html_row_indexes():
    files = [
        {"name": "don.pdf", "type": "application/pdf"},
        {"name": "chung-tu.pdf", "type": "application/pdf"},
        {"name": "thua-ke.pdf", "type": "application/pdf"},
        {"name": "trich-do.pdf", "type": "application/pdf"},
        {"name": "thoa-thuan.pdf", "type": "application/pdf"},
        {"name": "dieu-137.pdf", "type": "application/pdf"},
    ]
    ocr = [{"name": item["name"], "text": "ocr"} for item in files]
    llm_types = {
        0: "don_dang_ky",
        1: "chung_tu_tai_chinh",
        2: "thua_ke_qsdd",
        3: "manh_trich_do",
        4: "thoa_thuan_cap_chung",
        5: "giay_to_dieu_137",
    }

    attachments, warnings, classified = planner.build_plan_items(files, ocr, llm_types)

    assert warnings == []
    assert len(attachments) == len(files)
    assert [item["fileIndex"] for item in attachments] == [0, 1, 2, 3, 4, 5]
    assert [item["componentIndex"] for item in attachments] == [19, 0, 5, 9, 12, 10]
    assert all(item["target"] == "attp-row" for item in attachments)
    assert all(item["needsAddComponent"] is False for item in attachments)
    # BỎ HẲN loaiBan: cán bộ tự chọn Bản chính/Bản sao.
    assert all("loaiBan" not in item for item in attachments)
    assert [item["docType"] for item in classified] == list(llm_types.values())


def test_identity_shares_don_dang_ky_row():
    files = [{"name": "cccd.pdf", "type": "application/pdf"}]
    ocr = [{"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN"}]

    attachments, warnings, _ = planner.build_plan_items(files, ocr, {0: "identity"})

    assert warnings == []
    assert len(attachments) == 1
    assert attachments[0]["componentIndex"] == 19
    assert "Đơn đăng ký đất đai" in attachments[0]["componentName"]
    assert "loaiBan" not in attachments[0]


def test_other_is_skipped_with_warning_and_no_item():
    files = [
        {"name": "don.pdf", "type": "application/pdf"},
        {"name": "la.pdf", "type": "application/pdf"},
    ]
    ocr = [{"name": item["name"], "text": "ocr"} for item in files]

    attachments, warnings, classified = planner.build_plan_items(files, ocr, {0: "don_dang_ky", 1: "other"})

    assert len(attachments) == 1
    assert attachments[0]["fileIndex"] == 0
    assert len(warnings) == 1
    assert "la.pdf" in warnings[0]
    assert classified[1]["skipped"] is True
    assert classified[1]["docType"] == "other"


def test_unknown_llm_type_falls_back_to_other():
    files = [{"name": "x.pdf", "type": "application/pdf"}]
    ocr = [{"name": "x.pdf", "text": "ocr"}]

    attachments, warnings, classified = planner.build_plan_items(files, ocr, {})

    assert attachments == []
    assert len(warnings) == 1
    assert classified[0]["docType"] == "other"
    assert classified[0]["source"] == "unknown"


def test_no_rule_fallback_helpers_exist():
    # LLM-first tuyệt đối: không còn hàm rule nào trong planner.
    assert not hasattr(planner, "_rule_doc_type")
    assert not hasattr(planner, "_LOAI_BAN")


def test_schema_and_prompt_reflect_first_time_registration():
    names = {field["name"] for field in FIELDS}
    assert "ChuHoSo_HoTen" in names
    assert "NguoiNop_HoTen" in names
    assert "Don_NoiDungDangKy" in names
    assert "data[note]" in UI_COMP_BY_NAME
    assert "data[noidungyeucaugiaiquyet]" in UI_COMP_BY_NAME
    assert "Mẫu số 15" in EXTRA_RULES
    assert "BÊN ĐƯỢC ỦY QUYỀN" in EXTRA_RULES


def test_registry_has_scoped_procedure_and_both_pipelines():
    key = "dang-ky-dat-dai-lan-dau-ninh-binh"
    procedure = get_procedure(key)

    assert procedure is not None
    assert procedure["label"].startswith("[Tỉnh Ninh Bình]")
    assert procedure["mode"] == "agent"
    assert procedure["hasAttachmentStep"] is True
    assert procedure["roles"] == []
    assert procedure["detect"]["urlScope"] == ["dichvucong.ninhbinh.gov.vn"]
    assert callable(get_pipeline(key))
    assert callable(get_attach_pipeline(key))

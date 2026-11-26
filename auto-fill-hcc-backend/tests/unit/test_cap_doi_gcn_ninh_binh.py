from app.pipelines.cap_doi_gcn_ninh_binh.attach import planner
from app.pipelines.cap_doi_gcn_ninh_binh.process import mapper
from app.pipelines.cap_doi_gcn_ninh_binh.process.prompt import EXTRA_RULES
from app.pipelines.cap_doi_gcn_ninh_binh.process.schema import FIELDS, UI_COMP_BY_NAME
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


def test_manh_trich_do_routes_to_row_one_others_to_row_two():
    files = [
        {"name": "trich-do.pdf", "type": "application/pdf"},
        {"name": "don.pdf", "type": "application/pdf"},
        {"name": "gcn.pdf", "type": "application/pdf"},
        {"name": "uy-quyen.pdf", "type": "application/pdf"},
        {"name": "cccd.pdf", "type": "application/pdf"},
    ]
    ocr = [{"name": item["name"], "text": "ocr"} for item in files]
    llm_types = {
        0: "manh_trich_do",
        1: "don_bien_dong",
        2: "land_certificate",
        3: "authorization",
        4: "identity",
    }

    attachments, warnings, classified = planner.build_plan_items(files, ocr, llm_types)

    assert warnings == []
    assert len(attachments) == len(files)
    assert [item["fileIndex"] for item in attachments] == [0, 1, 2, 3, 4]
    # Mảnh trích đo -> dòng 1 (index 0); Đơn/GCN/ủy quyền/CCCD -> dòng 2 (index 1).
    assert [item["componentIndex"] for item in attachments] == [0, 1, 1, 1, 1]
    assert all(item["target"] == "attp-row" for item in attachments)
    assert all(item["needsAddComponent"] is False for item in attachments)
    # BỎ HẲN loaiBan: cán bộ tự chọn Bản chính/Bản sao.
    assert all("loaiBan" not in item for item in attachments)
    assert [item["docType"] for item in classified] == list(llm_types.values())
    # Bốn docType của dòng 2 trỏ đúng componentName Đơn Mẫu 11 verbatim.
    for item in attachments[1:]:
        assert item["componentName"] == "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 11"
    assert attachments[0]["componentName"] == "Mảnh trích đo bản đồ địa chính thửa đất"


def test_two_manh_trich_do_share_row_one():
    files = [
        {"name": "trich-do-1.pdf", "type": "application/pdf"},
        {"name": "trich-do-2.pdf", "type": "application/pdf"},
    ]
    ocr = [{"name": item["name"], "text": "ocr"} for item in files]

    attachments, warnings, _ = planner.build_plan_items(files, ocr, {0: "manh_trich_do", 1: "manh_trich_do"})

    assert warnings == []
    assert len(attachments) == 2
    # Hai file cùng loại -> cùng componentName + componentIndex 0 (gom chung dòng 1).
    assert {item["componentIndex"] for item in attachments} == {0}
    assert {item["componentName"] for item in attachments} == {"Mảnh trích đo bản đồ địa chính thửa đất"}


def test_don_and_identity_share_row_two():
    files = [
        {"name": "don.pdf", "type": "application/pdf"},
        {"name": "cccd.pdf", "type": "application/pdf"},
    ]
    ocr = [{"name": item["name"], "text": "ocr"} for item in files]

    attachments, warnings, _ = planner.build_plan_items(files, ocr, {0: "don_bien_dong", 1: "identity"})

    assert warnings == []
    assert len(attachments) == 2
    assert {item["componentIndex"] for item in attachments} == {1}
    assert {item["componentName"] for item in attachments} == {
        "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 11"
    }
    # documentName phân biệt để cán bộ đối chiếu dù đính chung một dòng.
    assert {item["documentName"] for item in attachments} == {
        "Đơn đăng ký biến động (Mẫu số 11/ĐK)",
        "Căn cước công dân",
    }


def test_other_is_routed_to_don_row_not_skipped():
    """File 'other' KHÔNG bị bỏ: form không có dòng 'Giấy tờ khác' → đính CHUNG vào dòng Đơn đăng ký
    (index 1), giữ tên file gốc; vẫn cảnh báo để cán bộ soát (yêu cầu user)."""
    files = [
        {"name": "don.pdf", "type": "application/pdf"},
        {"name": "la.pdf", "type": "application/pdf"},
    ]
    ocr = [{"name": item["name"], "text": "ocr"} for item in files]

    attachments, warnings, classified = planner.build_plan_items(files, ocr, {0: "don_bien_dong", 1: "other"})

    assert len(attachments) == 2  # KHÔNG rớt file nào
    other_item = next(it for it in attachments if it["fileIndex"] == 1)
    assert other_item["componentIndex"] == 1  # dòng Đơn đăng ký biến động
    assert other_item["detectedType"] == "other"
    assert other_item["documentName"] == "la.pdf"  # giữ tên gốc
    assert len(warnings) == 1 and "la.pdf" in warnings[0]
    assert classified[1]["docType"] == "other"
    assert classified[1].get("routedTo") == 1
    assert "skipped" not in classified[1]


def test_unknown_llm_type_routed_to_don_row():
    files = [{"name": "x.pdf", "type": "application/pdf"}]
    ocr = [{"name": "x.pdf", "text": "ocr"}]

    attachments, warnings, classified = planner.build_plan_items(files, ocr, {})

    assert len(attachments) == 1
    assert attachments[0]["componentIndex"] == 1
    assert len(warnings) == 1
    assert classified[0]["docType"] == "other"
    assert classified[0]["source"] == "unknown"
    assert classified[0].get("routedTo") == 1


def test_no_rule_fallback_helpers_exist():
    # LLM-first tuyệt đối: không còn hàm rule nào trong planner.
    assert not hasattr(planner, "_rule_doc_type")
    assert not hasattr(planner, "_LOAI_BAN")


def test_mapper_two_roles_and_note():
    source = [
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "ChuHoSo_NgaySinh", "value": "09/04/1965"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "034 065 010 368"},
        {
            "name": "ChuHoSo_NoiCuTru",
            "value": {"quocGia": "Việt Nam", "tinh": "Ninh Bình", "xa": "Xã Nghĩa Hưng", "diaChi": "Thôn Nam Phú"},
        },
        {"name": "Don_NoiDungCapDoi", "value": "Đề nghị cấp đổi Giấy chứng nhận quyền sử dụng đất"},
    ]

    fields, errors = mapper.enrich(source)
    values = _values(fields)

    assert errors == []
    assert values["data[ownerFullname]"] == "NGUYỄN VĂN A"
    assert values["data[isOwnerDossier]"] is True
    assert values["data[fullname]"] == "NGUYỄN VĂN A"
    assert values["data[identityNumber]"] == "034065010368"
    assert values["data[noidungyeucaugiaiquyet]"] == "Đề nghị cấp đổi Giấy chứng nhận quyền sử dụng đất"
    # Form cấp đổi CÓ data[note] -> mapper phát câu ghi chú (default=True) về cách đính kèm dòng 2.
    assert "data[note]" in values
    assert "đính kèm chung" in values["data[note]"]
    assert "data[note]" in UI_COMP_BY_NAME


def test_schema_and_prompt_reflect_cap_doi_context():
    names = {field["name"] for field in FIELDS}
    assert "ChuHoSo_HoTen" in names
    assert "NguoiNop_HoTen" in names
    assert "Don_NoiDungCapDoi" in names
    assert "Mẫu số 11" in EXTRA_RULES
    assert "BÊN ĐƯỢC ỦY QUYỀN" in EXTRA_RULES


def test_registry_has_scoped_procedure_and_both_pipelines():
    key = "cap-doi-gcn-ninh-binh"
    procedure = get_procedure(key)

    assert procedure is not None
    assert procedure["label"].startswith("[Tỉnh Ninh Bình]")
    assert procedure["mode"] == "agent"
    assert procedure["hasAttachmentStep"] is True
    assert procedure["roles"] == []
    assert procedure["detect"]["urlScope"] == ["dichvucong.ninhbinh.gov.vn"]
    assert callable(get_pipeline(key))
    assert callable(get_attach_pipeline(key))


def test_province_label_uses_thanh_pho_for_central_cities():
    """Bug: thành phố trực thuộc TW (Đà Nẵng, Hà Nội…) bị gắn 'Tỉnh' → select trên form trượt option
    'Thành phố …'. Nay dùng nhãn đúng loại đơn vị."""
    out, _ = mapper.enrich([
        {"name": "ChuHoSo_HoTen", "value": "CÔNG TY TNHH MTV DU LỊCH THANH VÂN"},
        {"name": "NguoiNop_HoTen", "value": "LƯƠNG HOÀNG TRUNG"},
        {"name": "NguoiNop_NoiCuTru", "value": {
            "quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "Hội An Tây", "diaChi": "TDP Cẩm Hà"}},
    ])
    values = _values(out)
    assert values["data[province]"] == "Thành phố Đà Nẵng"


def test_province_label_keeps_tinh_for_regular_provinces():
    out, _ = mapper.enrich([
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "ChuHoSo_NoiCuTru", "value": {
            "quocGia": "Việt Nam", "tinh": "Ninh Bình", "xa": "Phường Nam Định", "diaChi": "Số 1"}},
    ])
    values = _values(out)
    assert values["data[province]"] == "Tỉnh Ninh Bình"


def test_org_owner_fills_organization_field():
    """Chủ hồ sơ là TỔ CHỨC + người nộp được ủy quyền: điền ô 'Cơ quan/Tổ chức' (data[organization])
    = tên công ty (option b), KHÔNG để trống; isOwnerDossier=False (chủ ≠ người nộp)."""
    out, _ = mapper.enrich([
        {"name": "ChuHoSo_HoTen", "value": "CÔNG TY TNHH MTV DU LỊCH THANH VÂN"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "4000377726"},
        {"name": "NguoiNop_HoTen", "value": "LƯƠNG HOÀNG TRUNG"},
        {"name": "NguoiNop_SoDinhDanh", "value": "049087017746"},
    ])
    values = _values(out)
    assert values["data[organization]"] == "CÔNG TY TNHH MTV DU LỊCH THANH VÂN"
    assert values["data[ownerFullname]"] == "CÔNG TY TNHH MTV DU LỊCH THANH VÂN"
    assert values["data[fullname]"] == "LƯƠNG HOÀNG TRUNG"
    assert values["data[isOwnerDossier]"] is False


def test_individual_owner_does_not_fill_organization():
    out, _ = mapper.enrich([
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "038081022531"},
    ])
    values = _values(out)
    assert "data[organization]" not in values
    assert values["data[ownerFullname]"] == "NGUYỄN VĂN A"


def test_tro_ly_chi_tai_khoan_ninh_binh_dung_pipeline_loi():
    """26/11/2026: thủ tục đưa lên trợ lý người dân, cùng key với lõi, chỉ tài khoản Ninh Bình thấy."""
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.field_review import registry as field_review_registry
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS
    from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG
    from app.procedures.ke_khai_links import KE_KHAI_LINKS

    key = "cap-doi-gcn-ninh-binh"
    procedure = handfree.get_procedure(key)
    core = get_procedure(key)
    link = next(link for link in KE_KHAI_LINKS if link["key"] == key)
    assert "[Tỉnh Ninh Bình] " + procedure["label"] == core["label"] == link["label"]
    assert "Ninh Bình" not in procedure["shortLabel"]
    assert procedure["detect"] == core["detect"]
    assert procedure["keKhaiUrl"] == link["url"] and link["code"] == "1.012783"
    assert handfree.procedure_code(procedure) == "1.012783"
    assert procedure["flowProfile"] == "xay-dung" and procedure["maePortal"] is True
    assert procedure["bxdFlow"]["capability"] == "supportsBxdFlowNinhBinh"
    assert procedure["agencyProvince"] == "Ninh Bình"
    assert procedure["agencyProvinceOnly"] is True and link["provinceOnlyAgency"] is True
    assert field_review_registry.get(key)["required"] == ()
    assert "district" not in field_review_registry.get(key)["noAsk"]
    assert handfree.is_allowed_in_province(procedure, "ninhbinh")
    assert not handfree.is_allowed_in_province(procedure, "khanhhoa")
    assert handfree.get_pipeline(key) is get_pipeline(key)
    assert handfree.get_attach_pipeline(key) is get_attach_pipeline(key)
    assert PROCEDURE_HMONG[key] and PROCEDURE_HINTS[key]

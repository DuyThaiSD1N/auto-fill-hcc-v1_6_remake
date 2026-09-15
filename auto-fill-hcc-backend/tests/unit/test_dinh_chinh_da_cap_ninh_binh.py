from app.pipelines.dinh_chinh_da_cap_ninh_binh.attach import planner
from app.pipelines.dinh_chinh_da_cap_ninh_binh.process import mapper
from app.pipelines.dinh_chinh_da_cap_ninh_binh.process.prompt import EXTRA_RULES
from app.pipelines.dinh_chinh_da_cap_ninh_binh.process.schema import FIELDS, UI_COMP_BY_NAME
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

_DON_NAME = "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 11/ĐK"


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


def test_each_doc_type_routes_to_its_own_row():
    """4 dòng riêng (STT1..4 -> index 0..3); CCCD đi CHUNG dòng Đơn Mẫu 11 (index 3)."""
    files = [
        {"name": "gcn.pdf", "type": "application/pdf"},
        {"name": "sai-sot.pdf", "type": "application/pdf"},
        {"name": "uy-quyen.pdf", "type": "application/pdf"},
        {"name": "don.pdf", "type": "application/pdf"},
        {"name": "cccd.pdf", "type": "application/pdf"},
    ]
    ocr = [{"name": item["name"], "text": "ocr"} for item in files]
    llm_types = {
        0: "land_certificate",
        1: "error_proof",
        2: "authorization",
        3: "don_bien_dong",
        4: "identity",
    }

    attachments, warnings, classified = planner.build_plan_items(files, ocr, llm_types)

    assert warnings == []
    assert len(attachments) == len(files)
    assert [item["fileIndex"] for item in attachments] == [0, 1, 2, 3, 4]
    # GCN->0, sai sót->1, ủy quyền->2, Đơn Mẫu 11->3, CCCD->3 (chung dòng đơn).
    assert [item["componentIndex"] for item in attachments] == [0, 1, 2, 3, 3]
    assert all(item["target"] == "attp-row" for item in attachments)
    assert all(item["needsAddComponent"] is False for item in attachments)
    # BỎ HẲN loaiBan: cán bộ tự chọn Bản chính/Bản sao (pattern NB).
    assert all("loaiBan" not in item for item in attachments)
    assert [item["docType"] for item in classified] == list(llm_types.values())
    # componentName verbatim theo cột "Tên giấy tờ" của HTML thật.
    assert attachments[0]["componentName"] == "Bản gốc Giấy chứng nhận đã cấp"
    assert attachments[1]["componentName"] == (
        "Giấy tờ chứng minh sai sót thông tin của người được cấp Giấy chứng nhận"
    )
    assert attachments[2]["componentName"] == (
        "văn bản về việc ủy quyền theo quy định của pháp luật về dân sự"
    )
    assert attachments[3]["componentName"] == _DON_NAME
    assert attachments[4]["componentName"] == _DON_NAME


def test_don_and_identity_share_don_row():
    files = [
        {"name": "don.pdf", "type": "application/pdf"},
        {"name": "cccd.pdf", "type": "application/pdf"},
    ]
    ocr = [{"name": item["name"], "text": "ocr"} for item in files]

    attachments, warnings, _ = planner.build_plan_items(files, ocr, {0: "don_bien_dong", 1: "identity"})

    assert warnings == []
    assert len(attachments) == 2
    assert {item["componentIndex"] for item in attachments} == {3}
    assert {item["componentName"] for item in attachments} == {_DON_NAME}
    # documentName phân biệt để cán bộ đối chiếu dù đính chung một dòng.
    assert {item["documentName"] for item in attachments} == {
        "Đơn đăng ký biến động (Mẫu số 11/ĐK)",
        "Căn cước công dân",
    }


def test_other_is_routed_to_don_row_not_skipped():
    """File 'other' KHÔNG bị bỏ: form không có dòng 'Giấy tờ khác' → đính CHUNG vào dòng Đơn Mẫu 11
    (index 3), giữ tên file gốc; vẫn cảnh báo để cán bộ soát."""
    files = [
        {"name": "gcn.pdf", "type": "application/pdf"},
        {"name": "la.pdf", "type": "application/pdf"},
    ]
    ocr = [{"name": item["name"], "text": "ocr"} for item in files]

    attachments, warnings, classified = planner.build_plan_items(files, ocr, {0: "land_certificate", 1: "other"})

    assert len(attachments) == 2  # KHÔNG rớt file nào
    other_item = next(it for it in attachments if it["fileIndex"] == 1)
    assert other_item["componentIndex"] == 3  # dòng Đơn Mẫu 11
    assert other_item["detectedType"] == "other"
    assert other_item["documentName"] == "la.pdf"  # giữ tên gốc
    assert len(warnings) == 1 and "la.pdf" in warnings[0]
    assert classified[1]["docType"] == "other"
    assert classified[1].get("routedTo") == 3
    assert "skipped" not in classified[1]


def test_unknown_llm_type_routed_to_don_row():
    files = [{"name": "x.pdf", "type": "application/pdf"}]
    ocr = [{"name": "x.pdf", "text": "ocr"}]

    attachments, warnings, classified = planner.build_plan_items(files, ocr, {})

    assert len(attachments) == 1
    assert attachments[0]["componentIndex"] == 3
    assert len(warnings) == 1
    assert classified[0]["docType"] == "other"
    assert classified[0]["source"] == "unknown"
    assert classified[0].get("routedTo") == 3


def test_no_rule_fallback_helpers_exist():
    # LLM-first tuyệt đối: không còn hàm rule nào trong planner.
    assert not hasattr(planner, "_rule_doc_type")
    assert not hasattr(planner, "_LOAI_BAN")


def test_mapper_owner_self_submits_has_note_and_content():
    """Chủ hồ sơ tự nộp (không ủy quyền): isOwnerDossier=True, người nộp = chủ hồ sơ, có data[note],
    noidungyeucaugiaiquyet lấy NGUYÊN VĂN từ Đơn Mẫu 11."""
    source = [
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "ChuHoSo_NgaySinh", "value": "09/04/1965"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "034 065 010 368"},
        {
            "name": "ChuHoSo_NoiCuTru",
            "value": {"quocGia": "Việt Nam", "tinh": "Ninh Bình", "xa": "Xã Nghĩa Hưng", "diaChi": "Thôn Nam Phú"},
        },
        {"name": "Don_NoiDungDeNghi", "value": "Đề nghị đính chính thông tin trên Giấy chứng nhận đã cấp"},
    ]

    fields, errors = mapper.enrich(source)
    values = _values(fields)

    assert errors == []
    assert values["data[ownerFullname]"] == "NGUYỄN VĂN A"
    assert values["data[isOwnerDossier]"] is True
    assert values["data[fullname]"] == "NGUYỄN VĂN A"
    assert values["data[identityNumber]"] == "034065010368"
    assert values["data[noidungyeucaugiaiquyet]"] == "Đề nghị đính chính thông tin trên Giấy chứng nhận đã cấp"
    # Form đính chính đã cấp CÓ data[note] -> mapper phát câu ghi chú (default=True) về cách đính CCCD.
    assert "data[note]" in values
    assert "đính kèm chung" in values["data[note]"]
    assert "data[note]" in UI_COMP_BY_NAME


def test_mapper_authorized_uses_submitter_facts():
    """Có ủy quyền: chủ hồ sơ ≠ người nộp -> isOwnerDossier=False, khối định danh dùng fact NGƯỜI NỘP."""
    source = [
        {"name": "ChuHoSo_HoTen", "value": "TRẦN THỊ B"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "037065000111"},
        {"name": "NguoiNop_HoTen", "value": "LÊ VĂN C"},
        {"name": "NguoiNop_SoDinhDanh", "value": "049087017746"},
        {
            "name": "NguoiNop_NoiCuTru",
            "value": {"quocGia": "Việt Nam", "tinh": "Ninh Bình", "xa": "Phường Nam Định", "diaChi": "Số 5"},
        },
        {"name": "Don_NoiDungDeNghi", "value": "Đề nghị đính chính diện tích thửa đất"},
    ]

    fields, _ = mapper.enrich(source)
    values = _values(fields)

    assert values["data[ownerFullname]"] == "TRẦN THỊ B"
    assert values["data[isOwnerDossier]"] is False
    assert values["data[fullname]"] == "LÊ VĂN C"
    # Định danh, địa chỉ theo NGƯỜI NỘP (bên được ủy quyền).
    assert values["data[identityNumber]"] == "049087017746"
    assert values["data[soCCCD]"] == "049087017746"
    assert values["data[address]"] == "Số 5"


def test_loai_van_ban_and_hinh_thuc_not_emitted():
    """data[loaiVanBan]/data[hinhThucNopHs] đã được portal default sẵn, KHÔNG lấy từ giấy tờ →
    KHÔNG emit (không bịa option), không khai trong UI_COMP_BY_NAME."""
    assert "data[loaiVanBan]" not in UI_COMP_BY_NAME
    assert "data[hinhThucNopHs]" not in UI_COMP_BY_NAME


def test_schema_and_prompt_reflect_dinh_chinh_da_cap_context():
    names = {field["name"] for field in FIELDS}
    assert "ChuHoSo_HoTen" in names
    assert "NguoiNop_HoTen" in names
    assert "Don_NoiDungDeNghi" in names
    # Dùng đơn Mẫu số 11/ĐK (KHÁC bản sai sót dùng Mẫu số 18).
    assert "Mẫu số 11/ĐK" in EXTRA_RULES
    assert "Mẫu số 18" not in EXTRA_RULES
    assert "ĐÍNH CHÍNH" in EXTRA_RULES
    assert "BÊN ĐƯỢC ỦY QUYỀN" in EXTRA_RULES


def test_registry_has_scoped_procedure_and_both_pipelines():
    key = "dinh-chinh-da-cap-ninh-binh"
    procedure = get_procedure(key)

    assert procedure is not None
    assert procedure["label"] == "[Tỉnh Ninh Bình] Đính chính Giấy chứng nhận đã cấp"
    assert procedure["mode"] == "agent"
    assert procedure["hasAttachmentStep"] is True
    assert procedure["roles"] == []
    assert procedure["detect"]["urlScope"] == ["dichvucong.ninhbinh.gov.vn"]
    assert procedure["detect"]["textIncludes"] == ["Đính chính Giấy chứng nhận đã cấp"]
    assert callable(get_pipeline(key))
    assert callable(get_attach_pipeline(key))


def test_detect_distinct_from_sai_sot_variant():
    """Bản mới (chuỗi ngắn) và bản sai sót (chuỗi dài hơn) khác textIncludes để không nhận nhầm nhau."""
    da_cap = get_procedure("dinh-chinh-da-cap-ninh-binh")
    sai_sot = get_procedure("dinh-chinh-gcn-da-cap-ninh-binh")

    assert da_cap["detect"]["textIncludes"] == ["Đính chính Giấy chứng nhận đã cấp"]
    assert sai_sot["detect"]["textIncludes"] == ["Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót"]
    # Bản sai sót là superstring của bản mới → trên trang sai sót nó thắng; trên trang đã-cấp nó bị loại.
    assert da_cap["detect"]["textIncludes"][0] in sai_sot["detect"]["textIncludes"][0]


def test_org_owner_fills_organization_field():
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

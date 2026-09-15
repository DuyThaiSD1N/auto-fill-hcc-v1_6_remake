from app.pipelines.dang_ky_bien_dong_dat_dai_ninh_binh.attach import planner
from app.pipelines.dang_ky_bien_dong_dat_dai_ninh_binh.attach.prompt import SYSTEM_PROMPT
from app.pipelines.dang_ky_bien_dong_dat_dai_ninh_binh.process import mapper
from app.pipelines.dang_ky_bien_dong_dat_dai_ninh_binh.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_bien_dong_dat_dai_ninh_binh.process.schema import FIELDS, UI_COMP_BY_NAME
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

_DON_NAME = "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18"


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


def test_core_doc_types_route_to_their_own_rows():
    """Các loại chính route đúng dòng; CCCD đi CHUNG dòng Đơn Mẫu 18 (index 10)."""
    files = [
        {"name": "uy-quyen.pdf", "type": "application/pdf"},
        {"name": "gcn.pdf", "type": "application/pdf"},
        {"name": "hop-dong.pdf", "type": "application/pdf"},
        {"name": "don.pdf", "type": "application/pdf"},
        {"name": "cccd.pdf", "type": "application/pdf"},
    ]
    ocr = [{"name": item["name"], "text": "ocr"} for item in files]
    llm_types = {
        0: "authorization",
        1: "land_certificate",
        2: "hop_dong_chuyen_quyen",
        3: "don_bien_dong",
        4: "identity",
    }

    attachments, warnings, classified = planner.build_plan_items(files, ocr, llm_types)

    assert warnings == []
    assert len(attachments) == len(files)
    assert [item["fileIndex"] for item in attachments] == [0, 1, 2, 3, 4]
    # ủy quyền->0, GCN->1, hợp đồng chuyển quyền->4, Đơn Mẫu 18->10, CCCD->10 (chung dòng đơn).
    assert [item["componentIndex"] for item in attachments] == [0, 1, 4, 10, 10]
    assert all(item["target"] == "attp-row" for item in attachments)
    assert all(item["needsAddComponent"] is False for item in attachments)
    # BỎ HẲN loaiBan: cán bộ tự chọn Bản chính/Bản sao (pattern NB).
    assert all("loaiBan" not in item for item in attachments)
    assert [item["docType"] for item in classified] == list(llm_types.values())
    # componentName verbatim theo cột "Tên giấy tờ" của HTML thật.
    assert attachments[0]["componentName"] == "Văn bản về việc đại diện theo quy định của pháp luật về dân sự"
    assert attachments[1]["componentName"] == "Bản gốc Giấy chứng nhận đã cấp"
    assert attachments[2]["componentName"] == (
        "Hợp đồng hoặc văn bản về việc chuyển quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất"
    )
    assert attachments[3]["componentName"] == _DON_NAME
    assert attachments[4]["componentName"] == _DON_NAME


def test_every_dedicated_row_reachable_and_verbatim():
    """13 dòng đính kèm đều có route riêng với componentIndex đúng STT-1."""
    expected = {
        "authorization": 0,
        "land_certificate": 1,
        "ban_ve_tach_thua": 2,
        "hop_dong_tai_san": 3,
        "hop_dong_chuyen_quyen": 4,
        "trich_do": 5,
        "van_ban_the_chap": 6,
        "van_ban_dong_y_su_dung_dat": 7,
        "thoa_thuan_cap_chung": 8,
        "van_ban_cho_thue": 9,
        "don_bien_dong": 10,
        "bien_ban_hop_ubnd": 11,
        "van_ban_tang_cho": 12,
    }
    files = [{"name": f"{name}.pdf", "type": "application/pdf"} for name in expected]
    ocr = [{"name": item["name"], "text": "ocr"} for item in files]
    llm_types = {index: name for index, name in enumerate(expected)}

    attachments, warnings, _ = planner.build_plan_items(files, ocr, llm_types)

    assert warnings == []
    assert len(attachments) == len(expected)
    for item, (doc_type, idx) in zip(attachments, expected.items()):
        assert item["detectedType"] == doc_type
        assert item["componentIndex"] == idx


def test_gift_contract_goes_to_contract_row_not_tang_cho_row():
    """BÀI HỌC NGHIỆP VỤ: HỢP ĐỒNG TẶNG CHO QSDĐ công chứng -> dòng HỢP ĐỒNG CHUYỂN QUYỀN (index 4),
    KHÔNG vào dòng 'văn bản tặng cho' (index 12)."""
    files = [{"name": "hop-dong-tang-cho.pdf", "type": "application/pdf"}]
    ocr = [{"name": "hop-dong-tang-cho.pdf", "text": "ocr"}]

    attachments, _, _ = planner.build_plan_items(files, ocr, {0: "hop_dong_chuyen_quyen"})

    assert attachments[0]["componentIndex"] == 4
    assert attachments[0]["componentIndex"] != 12


def test_tax_and_hotich_merge_into_don_row():
    """Tờ khai thuế + giấy tờ hộ tịch không có dòng riêng -> gom CHUNG dòng Đơn Mẫu 18 (index 10)."""
    files = [
        {"name": "khai-thue.pdf", "type": "application/pdf"},
        {"name": "ho-tich.pdf", "type": "application/pdf"},
    ]
    ocr = [{"name": item["name"], "text": "ocr"} for item in files]

    attachments, warnings, _ = planner.build_plan_items(files, ocr, {0: "to_khai_thue", 1: "ho_tich"})

    assert warnings == []
    assert {item["componentIndex"] for item in attachments} == {10}
    assert {item["componentName"] for item in attachments} == {_DON_NAME}
    # documentName phân biệt để cán bộ đối chiếu dù đính chung một dòng.
    assert {item["documentName"] for item in attachments} == {"Tờ khai thuế/lệ phí", "Giấy tờ hộ tịch"}


def test_don_and_identity_share_don_row():
    files = [
        {"name": "don.pdf", "type": "application/pdf"},
        {"name": "cccd.pdf", "type": "application/pdf"},
    ]
    ocr = [{"name": item["name"], "text": "ocr"} for item in files]

    attachments, warnings, _ = planner.build_plan_items(files, ocr, {0: "don_bien_dong", 1: "identity"})

    assert warnings == []
    assert {item["componentIndex"] for item in attachments} == {10}
    assert {item["componentName"] for item in attachments} == {_DON_NAME}
    assert {item["documentName"] for item in attachments} == {
        "Đơn đăng ký biến động (Mẫu số 18)",
        "Căn cước công dân",
    }


def test_other_is_routed_to_don_row_not_skipped():
    """File 'other' (vd biên bản bàn giao) KHÔNG bị bỏ: form không có dòng 'Giấy tờ khác' -> đính CHUNG
    vào dòng Đơn Mẫu 18 (index 10), giữ tên file gốc; vẫn cảnh báo để cán bộ soát."""
    files = [
        {"name": "gcn.pdf", "type": "application/pdf"},
        {"name": "bien-ban-ban-giao.pdf", "type": "application/pdf"},
    ]
    ocr = [{"name": item["name"], "text": "ocr"} for item in files]

    attachments, warnings, classified = planner.build_plan_items(
        files, ocr, {0: "land_certificate", 1: "other"}
    )

    assert len(attachments) == 2  # KHÔNG rớt file nào
    other_item = next(it for it in attachments if it["fileIndex"] == 1)
    assert other_item["componentIndex"] == 10  # dòng Đơn Mẫu 18
    assert other_item["detectedType"] == "other"
    assert other_item["documentName"] == "bien-ban-ban-giao.pdf"  # giữ tên gốc
    assert len(warnings) == 1 and "bien-ban-ban-giao.pdf" in warnings[0]
    assert classified[1]["docType"] == "other"
    assert classified[1].get("routedTo") == 10
    assert "skipped" not in classified[1]


def test_unknown_llm_type_routed_to_don_row():
    files = [{"name": "x.pdf", "type": "application/pdf"}]
    ocr = [{"name": "x.pdf", "text": "ocr"}]

    attachments, warnings, classified = planner.build_plan_items(files, ocr, {})

    assert len(attachments) == 1
    assert attachments[0]["componentIndex"] == 10
    assert len(warnings) == 1
    assert classified[0]["docType"] == "other"
    assert classified[0]["source"] == "unknown"
    assert classified[0].get("routedTo") == 10


def test_no_rule_fallback_helpers_exist():
    # LLM-first tuyệt đối: không còn hàm rule nào trong planner.
    assert not hasattr(planner, "_rule_doc_type")
    assert not hasattr(planner, "_LOAI_BAN")


def test_prompt_lists_specific_doc_types():
    # Prompt phải liệt kê rõ các loại đặc thù để LLM chọn đúng dòng.
    for token in (
        "hop_dong_chuyen_quyen",
        "to_khai_thue",
        "ho_tich",
        "authorization",
        "identity",
        "HỢP ĐỒNG TẶNG CHO",
    ):
        assert token in SYSTEM_PROMPT


def test_mapper_owner_self_submits_has_note_and_content():
    """Chủ hồ sơ tự nộp (không ủy quyền): isOwnerDossier=True, người nộp = chủ hồ sơ, có data[note],
    noidungyeucaugiaiquyet lấy NGUYÊN VĂN từ Đơn Mẫu 18."""
    source = [
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "ChuHoSo_NgaySinh", "value": "09/04/1965"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "034 065 010 368"},
        {
            "name": "ChuHoSo_NoiCuTru",
            "value": {"quocGia": "Việt Nam", "tinh": "Ninh Bình", "xa": "Xã Nghĩa Hưng", "diaChi": "Thôn Nam Phú"},
        },
        {"name": "Don_NoiDungDeNghi", "value": "Đề nghị đăng ký biến động do nhận tặng cho quyền sử dụng đất thửa 133"},
    ]

    fields, errors = mapper.enrich(source)
    values = _values(fields)

    assert errors == []
    assert values["data[ownerFullname]"] == "NGUYỄN VĂN A"
    assert values["data[isOwnerDossier]"] is True
    assert values["data[fullname]"] == "NGUYỄN VĂN A"
    assert values["data[identityNumber]"] == "034065010368"
    assert values["data[noidungyeucaugiaiquyet]"] == (
        "Đề nghị đăng ký biến động do nhận tặng cho quyền sử dụng đất thửa 133"
    )
    # Form biến động CÓ data[note] -> mapper phát câu ghi chú (default=True) về cách đính CCCD/tờ khai.
    assert "data[note]" in values
    assert "đính kèm" in values["data[note]"]
    assert "Mẫu số 18" in values["data[note]"]
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
            "value": {"quocGia": "Việt Nam", "tinh": "Ninh Bình", "xa": "Phường Nam Sơn", "diaChi": "Số 5"},
        },
        {"name": "Don_NoiDungDeNghi", "value": "Đề nghị đăng ký biến động do chuyển nhượng quyền sử dụng đất"},
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


def test_schema_and_prompt_reflect_bien_dong_mau_18_context():
    names = {field["name"] for field in FIELDS}
    assert "ChuHoSo_HoTen" in names
    assert "NguoiNop_HoTen" in names
    assert "Don_NoiDungDeNghi" in names
    # Dùng đơn Mẫu số 18 (KHÁC bản đính chính dùng Mẫu số 11/ĐK).
    assert "Mẫu số 18" in EXTRA_RULES
    assert "Mẫu số 11" not in EXTRA_RULES
    assert "BIẾN ĐỘNG" in EXTRA_RULES
    assert "BÊN ĐƯỢC ỦY QUYỀN" in EXTRA_RULES
    # KHÔNG phải nội dung đính chính.
    assert "đính chính" in EXTRA_RULES  # xuất hiện trong câu loại trừ "KHÔNG phải nội dung đính chính"


def test_prompt_allows_notarization_block_as_submitter_attribute_source():
    """Bug thật: bên được ủy quyền chỉ có tên ở mục 'BÊN ĐƯỢC ỦY QUYỀN', còn danh xưng (Ông/Bà) nằm
    trong LỜI CHỨNG THỰC cuối văn bản ủy quyền → LLM né khối đó (tưởng bị cấm) nên bỏ sót giới tính.
    Prompt phải tách bạch: cấm lấy cán bộ chứng thực làm VAI người nộp, nhưng khối chứng thực VẪN là
    nguồn hợp lệ để gom THUỘC TÍNH của người nộp đã xác định."""
    assert "LỜI CHỨNG THỰC" in EXTRA_RULES
    assert "cán bộ thực hiện chứng thực" in EXTRA_RULES  # cấm theo VAI, không cấm đọc
    assert "danh sách người ký trong lời chứng" in EXTRA_RULES  # nguồn danh xưng cho giới tính
    # Quét lại toàn bộ tài liệu để gom đủ thuộc tính đúng người nộp.
    assert "quét lại TOÀN BỘ tài liệu" in EXTRA_RULES
    # Vẫn giữ chốt chống bịa: thiếu thì bỏ trống, không mượn của người khác.
    assert "không mượn của người khác" in EXTRA_RULES

    gioi_tinh = next(f for f in FIELDS if f["name"] == "NguoiNop_GioiTinh")
    assert "LỜI CHỨNG THỰC" in gioi_tinh["desc"]


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


def test_registry_has_scoped_procedure_and_both_pipelines():
    key = "dang-ky-bien-dong-dat-dai-ninh-binh"
    procedure = get_procedure(key)

    assert procedure is not None
    assert procedure["label"].startswith(
        "[Tỉnh Ninh Bình] Đăng ký biến động quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất "
        "trong các trường hợp chuyển đổi"
    )
    assert procedure["mode"] == "agent"
    assert procedure["hasAttachmentStep"] is True
    assert procedure["roles"] == []
    assert procedure["useDangKyBy"] is False
    assert procedure["detect"]["urlScope"] == ["dichvucong.ninhbinh.gov.vn"]
    assert callable(get_pipeline(key))
    assert callable(get_attach_pipeline(key))

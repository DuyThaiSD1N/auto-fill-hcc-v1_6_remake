"""Mapper TTHN: thẻ người được cấp (NguoiDuocCap_*) và thẻ người đi nộp (NguoiYeuCau_*)."""

from app.pipelines.xac_nhan_tthn.process.mapper import enrich

SUBJECT_ID = "001190000001"
AGENT_ID = "001085000002"


def _fields(values: dict) -> list[dict]:
    return [{"name": k, "comp": "x-input", "value": v} for k, v in values.items()]


def _ui(values: dict, options: dict | None = None) -> dict:
    return {f["name"]: f["value"] for f in enrich(_fields(values), options)}


def _poa(**extra) -> dict:
    return {
        "PoA_SubjectName": "Nguyễn Thị Được",
        "PoA_SubjectIdNumber": SUBJECT_ID,
        **extra,
    }


def test_poa_agent_card_fills_section_one_and_subject_card_section_two():
    ui = _ui(_poa(
        NguoiDuocCap_HoTen="NGUYỄN THỊ ĐƯỢC", NguoiDuocCap_SoDinhDanh=SUBJECT_ID,
        NguoiYeuCau_HoTen="TRẦN VĂN NỘP", NguoiYeuCau_SoDinhDanh=AGENT_ID,
    ))
    assert ui["HoVaTenC"] == "TRẦN VĂN NỘP"
    assert ui["SoDinhDanhC"] == AGENT_ID
    assert ui["quanhevoinguoiduocxacminh"] == "2"
    assert ui["HoVaTenC1"] == "NGUYỄN THỊ ĐƯỢC"
    assert ui["SoDinhDanhC1"] == SUBJECT_ID


def test_poa_agent_card_misplaced_as_subject_is_routed_by_id():
    # Thẻ duy nhất mang số KHÁC số người ủy quyền → là thẻ người đi nộp, không phải người được cấp.
    ui = _ui(_poa(NguoiDuocCap_HoTen="TRẦN VĂN NỘP", NguoiDuocCap_SoDinhDanh=AGENT_ID))
    assert ui["HoVaTenC"] == "TRẦN VĂN NỘP"
    assert ui["SoDinhDanhC1"] == SUBJECT_ID
    assert ui["HoVaTenC1"] == "NGUYỄN THỊ ĐƯỢC"


def test_single_card_misplaced_as_requester_becomes_subject():
    ui = _ui({"NguoiYeuCau_HoTen": "LÊ VĂN MỘT", "NguoiYeuCau_SoDinhDanh": SUBJECT_ID})
    assert ui["HoVaTenC1"] == "LÊ VĂN MỘT"
    assert ui["HoVaTenC"] == "LÊ VĂN MỘT"
    assert ui["quanhevoinguoiduocxacminh"] == "1"


def test_relative_declares_with_own_card_uses_printed_name_for_section_one():
    ui = _ui({
        "ToKhaiYeuCau_HoTen": "Trần Văn Nop", "ToKhaiYeuCau_SoDinhDanh": AGENT_ID,
        "ToKhaiYeuCau_QuanHe": "là con đẻ",
        "ToKhai_HoTen": "Nguyễn Thị Duoc", "ToKhai_SoDinhDanh": SUBJECT_ID,
        "NguoiYeuCau_HoTen": "TRẦN VĂN NỘP", "NguoiYeuCau_SoDinhDanh": AGENT_ID,
        "NguoiDuocCap_HoTen": "NGUYỄN THỊ ĐƯỢC", "NguoiDuocCap_SoDinhDanh": SUBJECT_ID,
    })
    assert ui["HoVaTenC"] == "TRẦN VĂN NỘP"
    assert ui["HoVaTenC1"] == "NGUYỄN THỊ ĐƯỢC"
    assert ui["quanhevoinguoiduocxacminh"] == "2"
    assert ui["quanhekhac"] == "Con đẻ"


def test_ethnicity_from_printed_paper_when_no_declaration():
    ui = _ui({
        "NguoiDuocCap_HoTen": "LÒ THỊ HAI", "NguoiDuocCap_SoDinhDanh": SUBJECT_ID,
        "NguoiDuocCap_DanToc": "Thái",
    })
    assert ui["DanTocC1"] == "Thái"


def test_declared_ethnicity_wins_over_printed_paper():
    ui = _ui({
        "ToKhai_HoTen": "Lò Thị Hai", "ToKhai_SoDinhDanh": SUBJECT_ID, "ToKhai_DanToc": "Tày",
        "NguoiDuocCap_HoTen": "LÒ THỊ HAI", "NguoiDuocCap_SoDinhDanh": SUBJECT_ID,
        "NguoiDuocCap_DanToc": "Thái",
    })
    assert ui["DanTocC1"] == "Tày"


def test_swapped_cards_are_fixed_by_grantor_name_when_poa_has_no_id():
    ui = _ui({
        "PoA_SubjectName": "Phan Thị Được",
        "NguoiDuocCap_HoTen": "TRẦN VĂN NỘP", "NguoiDuocCap_SoDinhDanh": AGENT_ID,
        "NguoiYeuCau_HoTen": "PHẠM THỊ ĐƯỢC", "NguoiYeuCau_SoDinhDanh": SUBJECT_ID,
    })
    assert ui["HoVaTenC"] == "TRẦN VĂN NỘP"
    assert ui["HoVaTenC1"] == "PHẠM THỊ ĐƯỢC"
    assert ui["SoDinhDanhC1"] == SUBJECT_ID


def test_issuer_abbreviation_and_old_card_date_are_normalized():
    ui = _ui({
        "NguoiDuocCap_HoTen": "LÊ VĂN MỘT", "NguoiDuocCap_SoDinhDanh": SUBJECT_ID,
        "NguoiDuocCap_NgayCap": "09/01/2022", "NguoiDuocCap_NoiCap": "Bộ Công an",
    })
    assert ui["NoiCapDDC1"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    ui = _ui({
        "NguoiDuocCap_HoTen": "LÊ VĂN MỘT", "NguoiDuocCap_SoDinhDanh": SUBJECT_ID,
        "NguoiDuocCap_NgayCap": "09/01/2021", "NguoiDuocCap_NoiCap": "CCSQLHC.V.TTXH",
    })
    assert ui["NoiCapDDC1"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"


def test_self_declared_requester_block_with_other_name_and_no_id_is_ignored():
    ui = _ui({
        "ToKhaiYeuCau_HoTen": "Nguyễn Thị Cán Bộ", "ToKhaiYeuCau_QuanHe": "Bản thân",
        "ToKhai_HoTen": "TRẦN THỊ HAI", "ToKhai_SoDinhDanh": SUBJECT_ID,
        "NguoiDuocCap_HoTen": "TRẦN THỊ HAI", "NguoiDuocCap_SoDinhDanh": SUBJECT_ID,
    })
    assert ui["HoVaTenC"] == "TRẦN THỊ HAI"
    assert ui["quanhevoinguoiduocxacminh"] == "1"


def test_ethnicity_from_other_document_when_card_and_declaration_have_none():
    ui = _ui({
        "NguoiDuocCap_HoTen": "VŨ VĂN BA", "NguoiDuocCap_SoDinhDanh": SUBJECT_ID,
        "GiayToKhac_DanToc": "Tày",
    })
    assert ui["DanTocC1"] == "Tày"
    ui = _ui({
        "NguoiDuocCap_HoTen": "VŨ VĂN BA", "NguoiDuocCap_SoDinhDanh": SUBJECT_ID,
        "NguoiDuocCap_DanToc": "Thái", "GiayToKhac_DanToc": "Tày",
    })
    assert ui["DanTocC1"] == "Thái"


def test_ethnicity_fallback_reads_line_under_subject_name_only_when_llm_returns_none():
    from app.pipelines.xac_nhan_tthn.process.runner import _compact_field_fallback

    old_certificate = (
        "Xét đề nghị của ông/bà: Cán Bộ A, là công chức tư pháp hộ tịch\n"
        "XÁC NHẬN:\nHọ, chữ đệm, tên: LÒ THỊ HAI\nNgày, tháng, năm sinh: 01/02/1980\n"
        "Giới tính: Nữ Dân tộc: Thái Quốc tịch: Việt Nam\n"
    )
    docs = [{"text": old_certificate}]
    out = _compact_field_fallback({"NguoiDuocCap_HoTen": "Lò Thị Hai"}, docs)
    assert out["GiayToKhac_DanToc"] == "Thái"
    out = _compact_field_fallback({"NguoiDuocCap_HoTen": "Lò Thị Hai", "ToKhai_DanToc": "Tày"}, docs)
    assert "GiayToKhac_DanToc" not in out
    out = _compact_field_fallback({"NguoiDuocCap_HoTen": "Người Khác"}, docs)
    assert "GiayToKhac_DanToc" not in out
    two_columns = "Họ, chữ đệm, tên vợ: Họ, chữ đệm, tên chồng:\nLÒ THỊ HAI VŨ VĂN BA\nDân tộc: Thái Dân tộc: Kinh\n"
    out = _compact_field_fallback({"NguoiDuocCap_HoTen": "LÒ THỊ HAI"}, [{"text": two_columns}])
    assert "GiayToKhac_DanToc" not in out


def test_card_residence_old_ward_resolved_by_district_in_ocr():
    # LLM bỏ mất "TP Đà Lạt" → "Phường 1" trùng tên ở Bảo Lộc. Lấy huyện in ngay sau tên xã trên thẻ;
    # bản án ghi thêm địa chỉ người khác ở Bảo Lộc thì chọn chỗ cùng số nhà/đường.
    from app.pipelines.xac_nhan_tthn.process.runner import _compact_field_fallback

    area = {"quocGia": "Việt Nam", "tinh": "Lâm Đồng", "xa": "Phường 1", "diaChi": "5 Hoa Sen"}
    docs = [
        {"text": "Nơi thường trú / Place of residence: 5 Hoa Sen, Phường 1, TP Đà Lạt, Lâm Đồng.\n"},
        {"text": "Bị đơn: Ông Trần Văn Bịa, địa chỉ: số 9, Lê Lợi, Phường 1, thành phố Bảo Lộc, tỉnh Lâm Đồng.\n"},
    ]
    out = _compact_field_fallback({"NguoiDuocCap_NoiCuTru": dict(area), "ToKhai_NoiCuTru": dict(area)}, docs)
    assert out["NguoiDuocCap_NoiCuTru"]["xa"] == "Phường Xuân Hương - Đà Lạt"
    assert out["ToKhai_NoiCuTru"]["xa"] == "Phường Xuân Hương - Đà Lạt"
    # Không neo được số nhà mà hai chỗ ghi chỉ về hai huyện khác nhau → không đoán.
    out = _compact_field_fallback({"ToKhai_NoiCuTru": {**area, "diaChi": ""}}, docs)
    assert out["ToKhai_NoiCuTru"]["xa"] == "Phường 1"

from app.pipelines.trich_luc.process.mapper import enrich


def _by_name(fields: list[dict]) -> dict[str, dict]:
    return {field["name"]: field for field in fields}


def test_trich_luc_maps_declaration_relationship_to_radio_label():
    result = _by_name(enrich([
        {"name": "ToKhai_LoaiSuKien", "value": "birth"},
        {"name": "ToKhai_HoTenNguoiDuocCap", "value": "TRẦN VĂN TRUNG"},
        {"name": "CopyRequest_QuanHe", "value": "Con đẻ"},
    ]))

    assert result["NYC_QuanHe"]["comp"] == "x-radio"
    assert result["NYC_QuanHe"]["value"] == "Con Đẻ"


def test_trich_luc_does_not_guess_ambiguous_ba_relationship():
    result = _by_name(enrich([
        {"name": "ToKhai_LoaiSuKien", "value": "birth"},
        {"name": "ToKhai_HoTenNguoiDuocCap", "value": "TRẦN VĂN TRUNG"},
        {"name": "CopyRequest_QuanHe", "value": "Ba"},
    ]))

    assert "NYC_QuanHe" not in result


def test_trich_luc_ticks_relationship_before_filling_requester_block():
    """eForm dựng lại mục I + mục II mỗi lần đổi ô tích (5) → radio phải đứng trước nhân thân."""
    names = [field["name"] for field in enrich([
        {"name": "TkNyc_HoTen", "value": "LIỄU THỊ PHỤNG"},
        {"name": "TkNyc_SoGiayToTuyThan", "value": "024167001234"},
        {"name": "CopyRequest_QuanHe", "value": "Vợ"},
        {"name": "ToKhai_LoaiSuKien", "value": "death"},
        {"name": "ToKhai_HoTenNguoiDuocCap", "value": "LƯƠNG VĂN NGHỊ"},
        {"name": "ToKhai_CoQuanDangKy", "value": "UBND xã Đồng Khởi"},
    ])]

    assert names.index("NYC_QuanHe") < names.index("HoVaTenC")
    assert names.index("NYC_QuanHe") < names.index("NDK_HoVaTen")


def test_trich_luc_declaration_relationship_beats_identity_comparison():
    """Tờ khai ghi rõ quan hệ thì dùng nguyên văn, không suy lại từ việc trùng/khác người."""
    result = _by_name(enrich([
        {"name": "TkNyc_HoTen", "value": "TRẦN VĂN TRUNG"},
        {"name": "CopyRequest_QuanHe", "value": "Con đẻ"},
        {"name": "ToKhai_LoaiSuKien", "value": "birth"},
        {"name": "ToKhai_HoTenNguoiDuocCap", "value": "TRẦN VĂN TRUNG"},
    ]))

    assert result["NYC_QuanHe"]["value"] == "Con Đẻ"
    assert "default" not in result["NYC_QuanHe"]


def test_trich_luc_infers_ban_than_from_matching_personal_id():
    result = _by_name(enrich([
        {"name": "TkNyc_SoGiayToTuyThan", "value": "012086005221"},
        {"name": "TkNyc_HoTen", "value": "SÙNG A CO"},
        {"name": "ToKhai_LoaiSuKien", "value": "birth"},
        {"name": "ToKhai_HoTenNguoiDuocCap", "value": "SÙNG A CO"},
        {"name": "ToKhai_SoDinhDanh", "value": "012086005221"},
    ]))

    assert result["NYC_QuanHe"]["value"] == "Bản thân"
    assert "default" not in result["NYC_QuanHe"]


def test_trich_luc_infers_khac_when_requester_differs_from_subject():
    result = _by_name(enrich([
        {"name": "Nyc_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "Nyc_SoDinhDanh", "value": "012345678901"},
        {"name": "HoTich_LoaiSuKien", "value": "birth"},
        {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "TRẦN BÉ"},
    ]))

    assert result["NYC_QuanHe"]["value"] == "Khác"
    assert result["NYC_QuanHe"]["default"] is True


def test_trich_luc_does_not_tick_relationship_without_any_source():
    result = _by_name(enrich([
        {"name": "HoTich_LoaiSuKien", "value": "birth"},
        {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "TRẦN BÉ"},
    ]))

    assert "NYC_QuanHe" not in result


def test_trich_luc_cmnd_and_personal_id_lengths_do_not_force_khac():
    """CMND 9 số của người yêu cầu vs định danh 12 số của chủ thể: so tên, không so số."""
    result = _by_name(enrich([
        {"name": "TkNyc_SoGiayToTuyThan", "value": "123456789"},
        {"name": "TkNyc_HoTen", "value": "SÙNG A CO"},
        {"name": "ToKhai_LoaiSuKien", "value": "birth"},
        {"name": "ToKhai_HoTenNguoiDuocCap", "value": "SÙNG A CO"},
        {"name": "ToKhai_SoDinhDanh", "value": "012086005221"},
    ]))

    assert result["NYC_QuanHe"]["value"] == "Bản thân"

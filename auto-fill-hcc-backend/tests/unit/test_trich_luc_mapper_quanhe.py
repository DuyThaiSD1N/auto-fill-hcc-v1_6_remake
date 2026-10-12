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


def test_trich_luc_ambiguous_ba_relationship_ticks_khac_with_default():
    result = _by_name(enrich([
        {"name": "ToKhai_LoaiSuKien", "value": "birth"},
        {"name": "ToKhai_HoTenNguoiDuocCap", "value": "TRẦN VĂN TRUNG"},
        {"name": "CopyRequest_QuanHe", "value": "Ba"},
    ]))

    # "Ba" nhập nhằng (bố Nam bộ vs Bà) → không đoán vai, chỉ tick "Khác" kèm viền vàng.
    assert result["NYC_QuanHe"]["value"] == "Khác"
    assert result["NYC_QuanHe"].get("default") is True

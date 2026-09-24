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


def _card_with_address(area: dict) -> list[dict]:
    return [
        {"name": "Nyc_HoTen", "value": "LÊ VĂN AN"},
        {"name": "Nyc_SoDinhDanh", "value": "001090012345"},
        {"name": "Nyc_NoiCuTru", "value": {"quocGia": "Việt Nam", **area}},
    ]


_OTHER_LOGIN = {"formContext": {"applicantFullname": "PHẠM THỊ BÌNH"}}


def test_trich_luc_keeps_merged_old_ward_in_address_detail():
    # Xã cũ đã sáp nhập sang phường mới khác tên → tên cũ phải còn trong địa chỉ chi tiết.
    result = _by_name(enrich(
        _card_with_address({"tinh": "Nghệ An", "xa": "Nghi Hoa", "diaChi": "Xóm 3, Thôn Đông"}),
        _OTHER_LOGIN,
    ))

    area = result["NDK_NoiCuTru_TrongNuoc"]["value"]
    assert area["xa"] == "Phường Cửa Lò"
    assert area["diaChi"] == "Xóm 3, Thôn Đông, Nghi Hoa"


def test_trich_luc_does_not_repeat_current_ward_in_address_detail():
    result = _by_name(enrich(
        _card_with_address({"tinh": "Thanh Hóa", "xa": "Hàm Rồng", "diaChi": "Số 5"}),
        _OTHER_LOGIN,
    ))

    assert result["NDK_NoiCuTru_TrongNuoc"]["value"]["diaChi"] == "Số 5"

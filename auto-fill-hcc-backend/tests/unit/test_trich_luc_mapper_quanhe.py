from app.pipelines.trich_luc.process.mapper import _area, enrich


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


def test_trich_luc_phuong_trung_ten_dung_huyen_de_quy_doi():
    # "Phường 1" có ở cả TP Đông Hà lẫn TX Quảng Trị cũ: phải nhờ cấp huyện mới chọn đúng.
    def area(huyen):
        value = {"quocGia": "Việt Nam", "tinh": "Quảng Trị", "xa": "Phường 1", "diaChi": "Khu Phố 7"}
        if huyen:
            value["huyen"] = huyen
        return _area(value)

    dong_ha = area("Thành phố Đông Hà")
    assert dong_ha["xa"] == "Phường Đông Hà"
    assert "huyen" not in dong_ha
    assert area("Thị xã Quảng Trị")["xa"] == "Phường Quảng Trị"
    # Không biết huyện thì không được đoán sang Phường Quảng Trị.
    assert area(None)["xa"] != "Phường Quảng Trị"

from app.pipelines._shared import area_remap


def test_numeric_house_token_is_not_remapped_to_commune(monkeypatch):
    monkeypatch.setitem(
        area_remap._REMAP,
        ("lam dong", "1"),
        {"tinh": "Lâm Đồng", "xa": "Phường 1 Bảo Lộc"},
    )

    result = area_remap.remap_area({
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Phường Xuân Hương",
        "diaChi": "Cò/1 Đồng Tâm",
    })

    assert result == {
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Phường Xuân Hương",
        "diaChi": "Cò/1 Đồng Tâm",
    }


def test_explicit_commune_number_still_remaps(monkeypatch):
    monkeypatch.setitem(
        area_remap._REMAP,
        ("lam dong", "1"),
        {"tinh": "Lâm Đồng", "xa": "Phường 1 Bảo Lộc"},
    )

    result = area_remap.remap_area({
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Phường 1",
        "diaChi": "Đồng Tâm",
    })

    assert result["xa"] == "Phường 1 Bảo Lộc"
    assert result["diaChi"] == "Đồng Tâm"


def test_explicit_commune_does_not_scan_street_name(monkeypatch):
    monkeypatch.setitem(
        area_remap._REMAP,
        ("lam dong", "bui thi xuan"),
        {"tinh": "Lâm Đồng", "xa": "Phường Lang Biang - Đà Lạt"},
    )

    result = area_remap.remap_area({
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Phường Xuân Hương - Đà Lạt",
        "diaChi": "216 Bùi Thị Xuân",
    })

    assert result == {
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Phường Xuân Hương - Đà Lạt",
        "diaChi": "216 Bùi Thị Xuân",
    }


def test_province_written_with_unit_prefix_is_brought_back_to_catalog_name():
    # req_dd367e1e8712: tờ khai ghi "TP Hồ Chí Minh". Dropdown trên cổng chỉ có một nhãn, mà cụm này
    # vừa không nằm trong nhãn vừa không chứa nhãn → extension trượt cả hai chiều, ô tỉnh bỏ trống.
    for viet in ("TP Hồ Chí Minh", "TP.Hồ Chí Minh", "TP.HCM", "TPHCM", "HCM"):
        assert area_remap.canonical_province(viet) == "Hồ Chí Minh", viet
    assert area_remap.canonical_province("Tỉnh Bắc Ninh") == "Bắc Ninh"
    assert area_remap.canonical_province("Tokyo") is None


def test_catalog_spellings_are_left_untouched():
    # Cả nhãn đầy đủ lẫn tên trần đều là cách viết hợp lệ. ket_hon/trich_luc đã chốt nhãn đầy đủ và
    # có test khóa; Đà Nẵng/Hà Nội thì đang chạy tên trần — không được đổi bên nào sang bên kia.
    for viet in ("Thành phố Hồ Chí Minh", "Hồ Chí Minh", "Đà Nẵng", "Thành phố Đà Nẵng", "Tỉnh Bắc Ninh"):
        assert area_remap._canonical_tinh(viet) == viet, viet


def test_bare_ward_name_is_expanded_to_full_catalog_label():
    # "Vĩnh Lộc" nằm trọn trong CẢ "Xã Vĩnh Lộc" lẫn "Xã Tân Vĩnh Lộc" → extension thấy 2 option khớp
    # lỏng và bỏ qua (không đoán bừa), ô Phường/Xã bỏ trống. Tên đầy đủ thì khớp chính xác một option.
    result = area_remap.remap_area({
        "quocGia": "Việt Nam",
        "tinh": "TP Hồ Chí Minh",
        "xa": "Vĩnh Lộc",
        "diaChi": "tại nhà không số ấp 53",
    })

    assert result["tinh"] == "Hồ Chí Minh"
    assert result["xa"] == "Xã Vĩnh Lộc"
    assert result["diaChi"] == "tại nhà không số ấp 53"


def test_ward_that_already_has_unit_label_is_not_relabelled():
    # Tên đã có nhãn là đúng nguyên văn option trên cổng rồi; nối thêm hậu tố sẽ làm trượt.
    result = area_remap.remap_area({
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Phường Xuân Hương",
        "diaChi": "13 Trần Hưng Đạo",
    })

    assert result["xa"] == "Phường Xuân Hương"

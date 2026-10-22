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


def _ha_noi(xa, dia_chi="Số 1 ngõ 2", **kwargs):
    return area_remap.remap_area({"quocGia": "Việt Nam", "tinh": "Hà Nội", "xa": xa, "diaChi": dia_chi}, **kwargs)


def test_ha_noi_split_ward_uses_remaining_part_destination():
    # NQ 1656: Phú La một phần vào Dương Nội, phần còn lại vào Kiến Hưng.
    assert _ha_noi("Phú La")["xa"] == "Phường Kiến Hưng"
    assert _ha_noi("Phường Phú La")["xa"] == "Phường Kiến Hưng"
    assert _ha_noi("Hà Cầu")["xa"] == "Phường Kiến Hưng"


def test_ha_noi_same_fold_key_units_resolve_by_label_and_accent():
    assert _ha_noi("Phường Vạn Phúc")["xa"] == "Phường Hà Đông"
    assert _ha_noi("Xã Vạn Phúc")["xa"] == "Xã Nam Phù"
    assert _ha_noi("Xã Vân Phúc")["xa"] == "Xã Phúc Lộc"
    assert _ha_noi("Xã Quang Trung")["xa"] == "Xã Kiều Phú"


def test_ha_noi_ward_in_two_districts_needs_district():
    assert _ha_noi("Quang Trung")["xa"] == ""
    assert _ha_noi("Quang Trung", huyen_hint="Hà Đông")["xa"] == "Phường Kiến Hưng"
    assert _ha_noi("Quang Trung", dia_chi="Số 1, quận Đống Đa")["xa"] == "Phường Kim Liên"


def test_ha_noi_ward_split_three_ways_is_not_guessed():
    assert _ha_noi("Phường Nhân Chính")["xa"] == "Phường Nhân Chính"


def test_ha_noi_bare_current_name_is_not_taken_as_old_ward():
    # "Phường Thanh Trì" (Hoàng Mai cũ) đi Vĩnh Hưng, nhưng tên trần là xã Thanh Trì hiện hành.
    assert _ha_noi("Thanh Trì")["xa"] == "Xã Thanh Trì"
    assert _ha_noi("Phường Thanh Trì")["xa"] == "Phường Vĩnh Hưng"


def test_commune_name_starting_like_village_is_kept():
    assert _ha_noi("Sóc Sơn") == {"quocGia": "Việt Nam", "tinh": "Hà Nội", "xa": "Xã Sóc Sơn", "diaChi": "Số 1 ngõ 2"}
    assert _ha_noi("Xã Tô Hiệu")["xa"] == "Xã Phú Xuyên"
    assert _ha_noi("Tổ 3", dia_chi="") == {"quocGia": "Việt Nam", "tinh": "Hà Nội", "xa": "", "diaChi": "Tổ 3"}

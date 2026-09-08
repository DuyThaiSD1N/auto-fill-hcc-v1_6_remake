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


# --------------------------------------------------------------------------------------
# Giấy tờ mang TỈNH MỚI nhưng dòng địa chỉ còn tên XÃ CŨ (sáp nhập 2025).
#
# Ca thật (liên thông khai sinh): CCCD của cha in "Thôn 5 Nghĩa Trung / Nghĩa Hưng, Ninh Bình".
# Tỉnh đã là tên MỚI ("Ninh Bình"), còn "Nghĩa Trung" là xã CŨ thuộc tỉnh cũ Nam Định. Bảng _REMAP
# key theo (tỉnh CŨ, xã cũ) nên cặp này trượt hết mọi bước, rơi xuống pass-through và trả về một tên
# xã KHÔNG CÒN trong danh mục → dropdown Phường/Xã trên cổng bỏ trống (mẹ cùng hồ sơ thì điền được
# vì giấy chứng sinh đã ghi sẵn tên xã mới).
# --------------------------------------------------------------------------------------

def test_new_province_with_old_commune_is_remapped():
    result = area_remap.remap_area({
        "quocGia": "Việt Nam",
        "tinh": "Ninh Bình",      # tên MỚI
        "xa": "Nghĩa Trung",      # tên CŨ (tỉnh cũ Nam Định)
        "diaChi": "Thôn 5",
    })

    assert result["tinh"] == "Ninh Bình"
    assert result["xa"] == "Xã Nghĩa Hưng"
    assert result["diaChi"] == "Thôn 5"
    assert area_remap.is_current_area(result["tinh"], result["xa"])


def test_new_province_with_old_commune_handles_admin_label():
    """Có nhãn "Xã" vẫn phải remap: nhánh mới nằm TRƯỚC lối thoát sớm xa_has_admin_label."""
    result = area_remap.remap_area({"tinh": "Ninh Bình", "xa": "Xã Nghĩa Trung", "diaChi": "Thôn 5"})
    assert result["xa"] == "Xã Nghĩa Hưng"


def test_old_province_pair_still_works():
    """Đường cũ (ghi tỉnh CŨ) không được đổi hành vi."""
    result = area_remap.remap_area({"tinh": "Nam Định", "xa": "Nghĩa Trung", "diaChi": "Thôn 5"})
    assert (result["tinh"], result["xa"]) == ("Ninh Bình", "Xã Nghĩa Hưng")


def test_valid_pair_is_never_touched_by_new_province_lookup():
    """Chốt chặn của cả nhánh: địa chỉ ĐANG chọn được trên cổng thì tuyệt đối không bị đụng.

    Mẹ trong cùng hồ sơ ở "Nghĩa Hưng" — vừa là tên xã MỚI hợp lệ, vừa là tên đích của bảng remap.
    Không có gác này thì rất dễ đá một địa chỉ đang đúng sang xã khác.
    """
    result = area_remap.remap_area({"tinh": "Ninh Bình", "xa": "Nghĩa Hưng", "diaChi": "Thôn Phúc An"})
    assert result["xa"] == "Nghĩa Hưng"
    assert area_remap._remap_by_new_province("Ninh Bình", "Nghĩa Hưng") is None


def test_new_province_lookup_leaves_whole_catalog_alone():
    """Quét TOÀN BỘ danh mục hiện hành: không cặp hợp lệ nào rơi vào nhánh mới."""
    from app.locations.catalog import PROVINCES, WARDS_BY_SLUG

    touched = [
        (province["name"], ward)
        for province in PROVINCES
        for ward in (WARDS_BY_SLUG.get(province["slug"], {}).get("communes") or [])
        if area_remap._remap_by_new_province(province["name"], ward) is not None
    ]
    assert touched == []


def test_ambiguous_new_province_mapping_is_skipped():
    """Cùng tên xã cũ, cùng tỉnh mới nhưng ra HAI xã mới khác nhau → không đoán bừa."""
    key = (area_remap._fold_province("Ninh Bình"), area_remap._fold_accent("Nghĩa Trung"))
    assert key in area_remap._REMAP_BY_NEW_PROVINCE
    area_remap._REMAP_BY_NEW_PROVINCE_AMBIGUOUS.add(key)
    try:
        assert area_remap._remap_by_new_province("Ninh Bình", "Nghĩa Trung") is None
    finally:
        area_remap._REMAP_BY_NEW_PROVINCE_AMBIGUOUS.discard(key)

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


# --- correct_area: sua loi chinh ta OCR o tinh/xa (opt-in) -------------------------------------


def test_correct_area_fixes_typo_in_current_province():
    assert area_remap.correct_area("Lâm Đồnq", "") == ("Lâm Đồng", "", ("tinh",))


def test_correct_area_fixes_old_province_to_old_name_then_remap_moves_it():
    assert area_remap.correct_area("Bắc Giamg", "")[0] == "Bắc Giang"

    result = area_remap.remap_area(
        {"tinh": "Bắc Giamg", "xa": "Xã Đông Lỗ", "diaChi": ""}, correct_spelling=True
    )

    assert (result["tinh"], result["xa"]) == ("Bắc Ninh", "Phường Hiệp Hòa")


def test_correct_area_leaves_province_alone_when_two_provinces_are_equally_close():
    assert area_remap.correct_area("Hà Nom", "") == ("Hà Nom", "", ())
    assert area_remap.correct_area("Quảng Nim", "") == ("Quảng Nim", "", ())


def test_correct_area_uses_ward_to_pick_between_close_provinces():
    tinh, _, changed = area_remap.correct_area("Hà Nom", "Xã Thanh Hà")

    assert (tinh, changed) == ("Hà Nam", ("tinh",))


def test_correct_area_never_touches_known_province_spellings():
    for tinh in ("Đà Lạt", "Thừa Thiên Huế", "TP.HCM", "Tỉnh Bắc Ninh", "LD"):
        assert area_remap.correct_area(tinh, "")[2] == ()


def test_correct_area_fixes_ward_typo_within_province():
    assert area_remap.correct_area("Hà Nội", "Phường Hoàn Kiếmm") == (
        "Hà Nội", "Phường Hoàn Kiếm", ("xa",)
    )
    # Xa cu cua tinh cu doc lech mot chu -> sua ve TEN CU, remap_area doi sang xa moi.
    assert area_remap.correct_area("Bắc Giang", "Xã Đông Lê")[1:] == ("Đông Lỗ", ("xa",))
    result = area_remap.remap_area(
        {"tinh": "Bắc Giang", "xa": "Xã Đông Lê", "diaChi": ""}, correct_spelling=True
    )
    assert (result["tinh"], result["xa"]) == ("Bắc Ninh", "Phường Hiệp Hòa")


def test_correct_area_does_not_remap_twice_when_new_name_is_also_an_old_name():
    # "Phú Nghĩa" (Hòa Bình cu) nhap vao "An Nghĩa"; ma "An Nghĩa" cung la ten mot xa cu KHAC cua Hòa
    # Bình. Tra thang ten xa moi thi remap doi them lan nua ra xa sai.
    result = area_remap.remap_area(
        {"tinh": "Hòa Bình", "xa": "Phú Nghĩaa", "diaChi": ""}, correct_spelling=True
    )
    expected = area_remap.remap_area({"tinh": "Hòa Bình", "xa": "Phú Nghĩa", "diaChi": ""})
    assert result["xa"] == expected["xa"]


def test_correct_area_fixes_wrong_tone_mark_on_current_ward():
    assert area_remap.correct_area("Bắc Ninh", "Xã Hiệp Hoá")[1] == "Phường Hiệp Hòa"


def test_correct_area_leaves_exact_ward_and_numbered_ward_alone():
    assert area_remap.correct_area("Bắc Ninh", "Xã Hiệp Hòa")[2] == ()
    assert area_remap.correct_area("Lâm Đồng", "Phường 2 Bảo Lộc")[1] == "Phường 2 Bảo Lộc"
    assert area_remap.correct_area("Lâm Đồng", "Thôn Lạc Xuânn")[2] == ()


def test_remap_area_corrects_spelling_by_default_and_can_be_turned_off():
    area = {"tinh": "Lâm Đồnq", "xa": "", "diaChi": ""}

    assert area_remap.remap_area(dict(area))["tinh"] == "Lâm Đồng"
    assert area_remap.remap_area(dict(area), correct_spelling=False)["tinh"] == "Lâm Đồnq"


def test_correct_area_handles_garbled_unit_label_and_rn_for_m():
    # OCR doc hong chinh chu "Phường"/"Xã" -> nhan khong cat duoc, nhung van chi la mot loi.
    assert area_remap.correct_area("Đồng Tháp", "Phườnq Cao Lãnh")[1] == "Phường Cao Lãnh"
    result = area_remap.remap_area(
        {"tinh": "Tây Ninh", "xa": "XXã Tân Trụ", "diaChi": ""}, correct_spelling=True
    )
    assert result["xa"] == "Xã Tân Trụ"
    # "m" doc thanh "rn" la hai loi theo khoang cach chu, gop lai thi chi con mot.
    assert area_remap.correct_area("Hà Nội", "Phường Hoàn Kiếrn")[1] == "Phường Hoàn Kiếm"


def test_remap_area_old_province_ignores_dash_spelling():
    # CMND cũ ghi "Thừa Thiên - Huế", bảng sáp nhập ghi "Thừa Thiên Huế"; ngược lại với Bà Rịa - Vũng Tàu.
    area = area_remap.remap_area({"tinh": "Thừa Thiên - Huế", "xa": "Thị trấn Khe Tre", "diaChi": ""})
    assert (area["tinh"], area["xa"]) == ("Huế", "Xã Khe Tre")
    area = area_remap.remap_area({"tinh": "Bà Rịa Vũng Tàu", "xa": "Xã Long Sơn", "diaChi": ""})
    assert area["tinh"] == area_remap.remap_area(
        {"tinh": "Bà Rịa - Vũng Tàu", "xa": "Xã Long Sơn", "diaChi": ""}
    )["tinh"]


def test_remap_area_fixes_extra_tone_mark_on_old_ward_of_renamed_province():
    # "Khê Tre" (OCR thêm dấu) với tỉnh cũ đã đổi tên: phải tra bảng theo tỉnh cũ như giấy ghi.
    for tinh in ("Thừa Thiên Huế", "Thừa Thiên - Huế", "Thành phố Huế"):
        area = area_remap.remap_area({"tinh": tinh, "xa": "xã Khê Tre", "diaChi": ""})
        assert (area["tinh"], area["xa"]) == ("Huế", "Xã Khe Tre"), tinh

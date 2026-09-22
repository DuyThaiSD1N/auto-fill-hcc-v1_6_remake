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


def test_glued_ward_name_behind_admin_label_still_resolves():
    """"Phường Langbiang" -- nhan don vi + ten dinh lien -- van ra ten day du trong danh muc.

    Dem khoang trang tren chuoi tho thi khoang trang cua nhan "Phường" lam ten nay bi cham la
    "da co khoang trang dung" -> truot bang tra nospace va tra ve mot ten khong co trong danh
    muc, dropdown Phuong/Xa tren cong bo trong (req_7cb5e862f6a4, thu tuc dang ky ket hon).
    """
    result = area_remap.remap_area({
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Phường Langbiang",
        "diaChi": "37B- Đa Phú - Tổ dân phố Lâm Phú",
    })

    assert result == {
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Phường Lang Biang - Đà Lạt",
        "diaChi": "37B- Đa Phú - Tổ dân phố Lâm Phú",
    }


def test_properly_spaced_ward_name_is_left_alone():
    """Ten da co khoang trang THAT khong duoc dong qua "core" cua phuong khac."""
    result = area_remap.remap_area({
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Phường Xuân Hương",
        "diaChi": "21 An Dương Vương",
    })

    assert result["xa"] == "Phường Xuân Hương"


def test_dash_suffix_ward_matches_catalog_written_without_dash():
    """To khai ghi "Tân Hà - Lâm Hà", danh muc ghi "Xã Tân Hà Lâm Hà" -- phai ra cung mot xa.

    Danh muc dung CA HAI kieu viet hau to cap huyen (co gach "Phường Cam Ly - Đà Lạt", lien
    khong gach "Xã Tân Hà Lâm Hà") trong khi to khai luon co gach, nen cap nay truot sach moi
    bang tra roi bi cham la ten chet -> o Phuong/Xa bo trong (req_9a2497c5d578).
    """
    for xa in ("Tân Hà - Lâm Hà", "Xã Tân Hà - Lâm Hà", "Tân Hà-Lâm Hà", "Tân Hà – Lâm Hà"):
        result = area_remap.remap_area({
            "quocGia": "Việt Nam",
            "tinh": "Lâm Đồng",
            "xa": xa,
            "diaChi": "Thôn Đức Long",
        })
        assert result["xa"] == "Xã Tân Hà Lâm Hà", xa
        assert area_remap.is_current_area(result["tinh"], result["xa"])


def test_ward_written_without_dash_matches_catalog_that_has_one():
    """Chieu nguoc lai: to khai viet lien, danh muc co gach."""
    result = area_remap.remap_area({
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Cam Ly Đà Lạt",
        "diaChi": "Số nhà 29/48/3/6 đường Kim Đồng",
    })

    assert result["xa"] == "Phường Cam Ly - Đà Lạt"


def test_dash_fallback_does_not_add_district_suffix_to_bare_ward_name():
    """Ten khong co hau to van de yen -- khong muon "Phường Xuân Hương" bi noi them "- Đà Lạt"."""
    result = area_remap.remap_area({
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Phường Xuân Hương",
        "diaChi": "21 An Dương Vương",
    })

    assert result["xa"] == "Phường Xuân Hương"

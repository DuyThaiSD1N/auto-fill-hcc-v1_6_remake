from app.pipelines._shared.area_remap import remap_area


def test_remap_area_extracts_commune_when_xa_empty_from_two_part_address():
    area = {
        "quocGia": "Việt Nam",
        "tinh": "Bắc Ninh",
        "xa": "",
        "diaChi": "Hà Mân, Thuận Thành",
    }

    out = remap_area(area)

    assert out["tinh"] == "Bắc Ninh"
    # Rmap BOC xa tu diaChi ma KHONG remap (de mapper pipeline xu ly)
    # -> tra ten xa ban dau "Ha Man", khong tra "Phuong Song Lieu" (ten sau sap nhap)
    assert out["xa"] == "Hà Mân"
    assert out["diaChi"] == ""


def test_remap_area_extracts_commune_and_detail_from_three_part_address():
    area = {
        "quocGia": "Việt Nam",
        "tinh": "Bắc Ninh",
        "xa": "",
        "diaChi": "Mán Xá Đông, Hà Mân, Thuận Thành",
    }

    out = remap_area(area)

    assert out["tinh"] == "Bắc Ninh"
    # Giu ten xa ban dau, khong remap
    assert out["xa"] == "Hà Mân"
    assert out["diaChi"] == "Mán Xá Đông"


def test_remap_area_treats_whitespace_xa_as_empty_and_still_extracts_from_diachi():
    area = {
        "quocGia": "Việt Nam",
        "tinh": "Bắc Ninh",
        "xa": "   ",
        "diaChi": "Hà Mân, Thuận Thành",
    }

    out = remap_area(area)

    # Giu ten xa ban dau khong remap
    assert out["xa"] == "Hà Mân"

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


def test_current_ward_without_admin_label_is_not_overridden_by_diachi_scan():
    """Xã ĐÃ LÀ tên hiện hành nhưng thiếu nhãn "Phường" thì fallback diaChi không được đá sang xã khác.

    Đơn viết tay ghi "Tổ Mỹ An phường An Hải TP Đà Nẵng" → LLM trả xa="An Hải" (không nhãn),
    diaChi="Tổ Mỹ An". "Mỹ An" là phường CŨ của Ngũ Hành Sơn nên fallback scan diaChi từng trả về
    xa="Phường Ngũ Hành Sơn" và đẩy "An Hải" xuống diaChi — sai cả hai ô.
    """
    result = area_remap.remap_area(
        {"quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "An Hải", "diaChi": "Tổ Mỹ An"},
        allow_diachi_fallback=True,
    )

    assert result == {
        "quocGia": "Việt Nam",
        "tinh": "Đà Nẵng",
        "xa": "Phường An Hải",
        "diaChi": "Tổ Mỹ An",
    }


def test_genuine_old_ward_still_remaps_even_when_detail_mentions_it():
    """Chốt rằng Bước 2d không vô hiệu hóa remap thật: "Mỹ An" là phường CŨ → vẫn ra Ngũ Hành Sơn."""
    result = area_remap.remap_area(
        {"quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "Mỹ An", "diaChi": "Tổ 5"},
        allow_diachi_fallback=True,
    )

    assert result["xa"] == "Phường Ngũ Hành Sơn"
    assert result["diaChi"] == "Tổ 5"

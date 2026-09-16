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


def test_ward_level_shift_repaired_when_catalogue_proves_it():
    """Tờ khai 2 cấp bị đọc theo nếp 3 cấp: thôn rơi vào ô xã, xã thật bị đẩy sang "huyen"."""
    out = area_remap.remap_area({
        "quocGia": "Việt Nam",
        "tinh": "Lào Cai",
        "xa": "Việt Thành 3",   # thực ra là tên THÔN
        "huyen": "Trấn Yên",    # thực ra là XÃ hiện hành của Lào Cai
        "diaChi": "",
    })

    assert out["xa"] == "Xã Trấn Yên"
    assert out["diaChi"] == "Việt Thành 3"
    assert out["tinh"] == "Lào Cai"
    assert "huyen" not in out


def test_old_three_level_address_is_left_alone():
    """Địa chỉ CŨ 3 cấp hợp lệ không được đảo: ô xã remap ra được nên không phải lỗi lệch cấp."""
    out = area_remap.remap_area({
        "quocGia": "Việt Nam",
        "tinh": "Bình Thuận",
        "xa": "Hàm Kiệm",
        "huyen": "Hàm Thuận Nam",
        "diaChi": "Tổ 3",
    })

    assert out["xa"] == "Xã Hàm Kiệm"
    assert out["diaChi"] == "Tổ 3"


def test_ward_level_shift_needs_catalogue_evidence():
    """Gợi ý cấp huyện KHÔNG phải xã hiện hành của tỉnh đó → không đảo, tránh đoán bừa."""
    out = area_remap.remap_area({
        "quocGia": "Việt Nam",
        "tinh": "Lào Cai",
        "xa": "Việt Thành 3",
        "huyen": "Một Huyện Không Có Thật",
        "diaChi": "",
    })

    assert out["xa"] == "Việt Thành 3"
    assert out["diaChi"] == ""

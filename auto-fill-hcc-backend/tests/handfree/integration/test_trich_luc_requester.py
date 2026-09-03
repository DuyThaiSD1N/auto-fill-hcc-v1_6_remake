"""Chọn đúng người yêu cầu cho trich-luc-ks khi upload nhiều CCCD (mẹ làm bản sao cho con)."""

from app.pipelines.trich_luc.process import mapper

# Chủ thể hộ tịch = con (Đoàn Tiến Mạnh); người yêu cầu thực = mẹ (Nguyễn Thị Thanh Nga).
_SON = {
    "Nyc_HoTen": "ĐOÀN TIẾN MẠNH",
    "Nyc_SoDinhDanh": "012213008048",
    "Nyc_NgayCap": "03/09/2024",
    "Nyc_NoiCap": "Bộ Công an",
}
_MOTHER = {
    "Nyc_HoTen": "NGUYỄN THỊ THANH NGA",
    "Nyc_SoDinhDanh": "001181030693",
    "Nyc_NgayCap": "25/05/2026",
    "Nyc_NoiCap": "Bộ Công an",
}
_HOTICH = {
    "HoTich_LoaiSuKien": "birth",
    "HoTich_TenGiayTo": "Giấy khai sinh",
    "HoTich_HoTenNguoiDuocDangKy": "ĐOÀN TIẾN MẠNH",
    "HoTich_SoDinhDanh": "012213008048",
    "HoTich_So": "200",
}


def _fields(*dicts) -> list[dict]:
    merged = {}
    for d in dicts:
        merged.update(d)
    return [{"name": k, "value": v} for k, v in merged.items()]


def _by_name(out):
    return {f["name"]: f for f in out}


def test_form_context_match_fills_mother_as_requester():
    """Mẹ đăng nhập (VNeID) + LLM lấy đúng CCCD mẹ → người yêu cầu = mẹ."""
    out = _by_name(mapper.enrich(
        _fields(_MOTHER, _HOTICH),
        options={"formContext": {"applicantFullname": "Nguyễn Thị Thanh Nga",
                                 "applicantIdentityNumber": "001181030693"}},
    ))
    assert out["HoVaTenC"]["value"] == "NGUYỄN THỊ THANH NGA"
    assert out["SoDinhDanhC"]["value"] == "001181030693"
    # Chủ thể (con) vẫn ra ở NDK_*.
    assert out["NDK_HoVaTen"]["value"] == "ĐOÀN TIẾN MẠNH"


def test_form_context_mismatch_does_not_overwrite_requester():
    """Mẹ đăng nhập nhưng LLM lỡ lấy CCCD CON → KHÔNG ghi đè người yêu cầu (giữ cổng điền)."""
    out = _by_name(mapper.enrich(
        _fields(_SON, _HOTICH),
        options={"formContext": {"applicantFullname": "Nguyễn Thị Thanh Nga",
                                 "applicantIdentityNumber": "001181030693"}},
    ))
    assert "HoVaTenC" not in out
    assert "SoDinhDanhC" not in out
    # Vẫn điền chủ thể + hồ sơ.
    assert out["NDK_HoVaTen"]["value"] == "ĐOÀN TIẾN MẠNH"
    assert out["HoSo_So"]["value"] == "200"


def test_no_context_cccd_is_subject_not_requester():
    """Không mỏ neo, CCCD trùng chủ thể (con) → KHÔNG coi là người yêu cầu (không ghi đè)."""
    out = _by_name(mapper.enrich(_fields(_SON, _HOTICH)))
    assert "HoVaTenC" not in out


def test_no_context_cccd_not_subject_is_requester():
    """Không mỏ neo, CCCD KHÁC chủ thể (mẹ) → là người yêu cầu."""
    out = _by_name(mapper.enrich(_fields(_MOTHER, _HOTICH)))
    assert out["HoVaTenC"]["value"] == "NGUYỄN THỊ THANH NGA"


# Chỉ up 1 CCCD (không có giấy hộ tịch): prompt phân vai vào đúng một trong hai nhóm.
_SUBJECT_ONLY = {
    "ChuThe_HoTen": "NGUYỄN ĐỨC TOÀN",
    "ChuThe_SoDinhDanh": "034072010036",
    "ChuThe_NgaySinh": "20/03/1972",
    "ChuThe_GioiTinh": "Nam",
    "ChuThe_NgayCap": "28/04/2023",
    "ChuThe_NoiCuTru": {
        "quocGia": "Việt Nam",
        "tinh": "Lai Châu",
        "xa": "Đoàn Kết",
        "diaChi": "Tổ 10",
    },
}
_REQUESTER_ONLY = {
    "Nyc_HoTen": "NGUYỄN ĐỨC TOÀN",
    "Nyc_SoDinhDanh": "034072010036",
    "Nyc_NgaySinh": "20/03/1972",
    "Nyc_GioiTinh": "Nam",
    "Nyc_NgayCap": "28/04/2023",
}


def test_only_cccd_no_context_fills_ndk_not_requester():
    """Chỉ 1 CCCD, không giấy hộ tịch, không mỏ neo → điền HẾT NGƯỜI ĐƯỢC ĐĂNG KÝ (II), KHÔNG điền người yêu cầu."""
    out = _by_name(mapper.enrich(_fields(_SUBJECT_ONLY)))
    assert "HoVaTenC" not in out
    assert out["NDK_HoVaTen"]["value"] == "NGUYỄN ĐỨC TOÀN"
    assert out["NDK_NgaySinh"]["value"] == "20/03/1972"
    assert out["NDK_GioiTinh"]["value"] == "Nam"
    assert out["NDK_SoDinhDanh"]["value"] == "034072010036"
    # remap_area (tro-ly) chuẩn hóa ward về tên hiện hành đầy đủ tiền tố.
    assert out["NDK_NoiCuTru_TrongNuoc"]["value"]["xa"] == "Phường Đoàn Kết"


def test_only_cccd_matches_formcontext_fills_requester_and_subject():
    """Chỉ 1 CCCD khớp người đăng nhập → người yêu cầu tự xin cho chính mình, điền cả hai khối."""
    out = _by_name(mapper.enrich(
        _fields(_REQUESTER_ONLY),
        options={"formContext": {"applicantFullname": "Nguyễn Đức Toàn",
                                 "applicantIdentityNumber": "034072010036"}},
    ))
    assert out["HoVaTenC"]["value"] == "NGUYỄN ĐỨC TOÀN"
    assert out["SoDinhDanhC"]["value"] == "034072010036"
    assert out["NDK_HoVaTen"]["value"] == "NGUYỄN ĐỨC TOÀN"
    assert out["NDK_SoDinhDanh"]["value"] == "034072010036"


def test_only_cccd_formcontext_mismatch_fills_ndk_only():
    """Chỉ 1 CCCD (người mất) nhưng người đăng nhập là người khác → chỉ điền mục II, không điền người yêu cầu."""
    out = _by_name(mapper.enrich(
        _fields(_SUBJECT_ONLY),
        options={"formContext": {"applicantFullname": "Trần Thị B",
                                 "applicantIdentityNumber": "099999999999"}},
    ))
    assert out["NDK_HoVaTen"]["value"] == "NGUYỄN ĐỨC TOÀN"
    assert "HoVaTenC" not in out


def test_two_cccd_match_requester_and_fill_remaining_card_as_subject():
    """Một thẻ khớp formContext, thẻ còn lại phải điền đầy đủ người được đăng ký."""
    requester = {
        "Nyc_HoTen": "BÙI THỊ THANH MAI",
        "Nyc_SoDinhDanh": "025199000635",
        "Nyc_NgaySinh": "27/09/1999",
        "Nyc_GioiTinh": "Nữ",
        "Nyc_NgayCap": "20/09/2024",
        "Nyc_NoiCap": "Bộ Công an",
        "Nyc_NoiCuTru": {
            "quocGia": "Việt Nam",
            "tinh": "Phú Thọ",
            "xa": "Lâm Thao",
            "diaChi": "Khu Phương Lai",
        },
    }
    subject = {
        "ChuThe_HoTen": "NGUYỄN THỊ HƯƠNG",
        "ChuThe_SoDinhDanh": "025173001841",
        "ChuThe_NgaySinh": "20/08/1973",
        "ChuThe_GioiTinh": "Nữ",
        "ChuThe_QuocTich": "Việt Nam",
        "ChuThe_LoaiGiayTo": "Căn cước công dân",
        "ChuThe_NgayCap": "13/04/2021",
        "ChuThe_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        "ChuThe_NoiCuTru": {
            "quocGia": "Việt Nam",
            "tinh": "Phú Thọ",
            "xa": "Lâm Thao",
            "diaChi": "Khu Phương Lai",
        },
    }

    out = _by_name(mapper.enrich(
        _fields(requester, subject),
        options={"formContext": {
            "applicantFullname": "BÙI THỊ THANH MAI",
            "applicantIdentityNumber": "025199000635",
        }},
    ))

    assert out["HoVaTenC"]["value"] == "BÙI THỊ THANH MAI"
    assert out["SoDinhDanhC"]["value"] == "025199000635"
    assert out["NDK_HoVaTen"]["value"] == "NGUYỄN THỊ HƯƠNG"
    assert out["NDK_SoDinhDanh"]["value"] == "025173001841"
    assert out["NDK_NgayCap"]["value"] == "13/04/2021"
    assert out["NDK_NoiCap"]["value"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert out["NDK_NoiCuTru_TrongNuoc"]["value"]["diaChi"] == "Khu Phương Lai"

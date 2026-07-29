"""Unit tests for mai táng phí dân công hỏa tuyến mapper."""

from app.pipelines.mai_tang_dan_cong.process import mapper


def _flds(d: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in d.items()]


def _run(vals: dict, ctx: dict | None = None):
    fields, warnings = mapper.enrich(_flds(vals), ctx or {})
    return {f["name"]: f["value"] for f in fields}, warnings


def test_declaration_and_cccd_same_owner_uses_source_priority():
    d, w = _run(
        {
            "ToKhai_ThanNhanHoTen": "Vũ Đình Thiết",
            "ToKhai_ThanNhanNgaySinh": "26/04/2003",
            "ToKhai_ThanNhanSoDienThoai": "0976134251",
            "ToKhai_ThanNhanTruQuan": {
                "quocGia": "Việt Nam",
                "tinh": "Lai Châu",
                "xa": "Tân Phong",
                "diaChi": "Tổ dân phố Tả Làn Than",
            },
            "Person1_HoTen": "VŨ ĐÌNH THIẾT",
            "Person1_SoDinhDanh": "040203015844",
            "Person1_NgaySinh": "25/04/2003",
            "Person1_GioiTinh": "Nam",
            "Person1_NgayCap": "25/04/2021",
            "Person1_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "Person1_NoiCuTru": {"tinh": "Điện Biên", "xa": "Mường Lay", "diaChi": "Bản 1"},
        },
        {"formContext": {"applicantFullname": "Vũ Đình Thiết", "applicantIdentityNumber": "040203015844"}},
    )

    assert d["data[isOwnerDossierCheck]"] is True
    assert d["data[fullname]"] == "Vũ Đình Thiết"
    assert d["data[birthday]"] == "26/04/2003"
    assert d["data[phoneNumber]"] == "0976134251"
    assert d["data[province]"] == "Lai Châu"
    assert d["data[district]"] == "Tân Phong"
    assert d["data[address]"] == "Tổ dân phố Tả Làn Than"
    assert d["data[gender]"] == "Nam"
    assert d["data[identityNumber]"] == "040203015844"
    assert d["data[identityDate]"] == "25/04/2021"
    assert d["data[idIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert "data[ownerFullname]" not in d
    assert not w


def test_declaration_address_string_is_split_to_area():
    d, w = _run(
        {
            "ToKhai_ThanNhanHoTen": "Vũ Đình Thiết",
            "ToKhai_ThanNhanTruQuan": "Tổ dân phố Tả Làn Than, phường Tân Phong, tỉnh Lai Châu",
            "Person1_HoTen": "VŨ ĐÌNH THIẾT",
            "Person1_SoDinhDanh": "040203015844",
            "Person1_GioiTinh": "Nam",
        },
        {},
    )

    assert d["data[isOwnerDossierCheck]"] is True
    assert d["data[province]"] == "Lai Châu"
    assert d["data[district]"] == "Tân Phong"
    assert d["data[address]"] == "Tổ dân phố Tả Làn Than"
    assert not w


def test_different_requester_fills_owner_from_declaration():
    d, w = _run(
        {
            "ToKhai_ThanNhanHoTen": "Vũ Đình Thiết",
            "ToKhai_ThanNhanNgaySinh": "26/04/2003",
            "ToKhai_ThanNhanSoDienThoai": "0976134251",
            "ToKhai_ThanNhanTruQuan": {"tinh": "Lai Châu", "xa": "Tân Phong", "diaChi": "Tổ dân phố Tả Làn Than"},
            "Person1_HoTen": "NGUYỄN VĂN A",
            "Person1_SoDinhDanh": "001111111111",
            "Person1_GioiTinh": "Nam",
            "Person1_NoiCuTru": {"tinh": "Hà Nội", "xa": "Cầu Giấy", "diaChi": "Số 1"},
            "Person2_HoTen": "VŨ ĐÌNH THIẾT",
            "Person2_SoDinhDanh": "040203015844",
            "Person2_GioiTinh": "Nam",
            "Person2_NgayCap": "25/04/2021",
            "Person2_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        },
        {"formContext": {"applicantFullname": "Nguyễn Văn A", "applicantIdentityNumber": "001111111111"}},
    )

    assert d["data[isOwnerDossierCheck]"] is False
    assert d["data[fullname]"] == "NGUYỄN VĂN A"
    assert d["data[identityNumber]"] == "001111111111"
    assert d["data[ownerFullname]"] == "Vũ Đình Thiết"
    assert d["data[ownerBirthday]"] == "26/04/2003"
    assert d["data[ownerGender]"] == "Nam"
    assert d["data[ownerIdentityNumber]"] == "040203015844"
    assert d["data[ownerPhoneNumber]"] == "0976134251"
    assert d["data[ownerProvince]"] == "Lai Châu"
    assert not w


def test_missing_declaration_returns_warning():
    d, w = _run(
        {
            "Person1_HoTen": "VŨ ĐÌNH THIẾT",
            "Person1_SoDinhDanh": "040203015844",
        },
        {},
    )

    assert d == {}
    assert "Không đọc được bản khai thân nhân" in w[0]


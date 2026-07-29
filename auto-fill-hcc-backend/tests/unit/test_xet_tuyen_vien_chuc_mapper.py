"""Unit tests for xét tuyển viên chức mapper."""

from app.pipelines.xet_tuyen_vien_chuc.process import mapper


def _flds(d: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in d.items()]


def _run(vals: dict, ctx: dict | None = None):
    fields, warnings = mapper.enrich(_flds(vals), ctx or {})
    return {f["name"]: f["value"] for f in fields}, warnings


def test_phieu_same_as_requester_ticks_owner_check_and_uses_phieu_address():
    d, w = _run(
        {
            "Phieu_HoTen": "LÒ THỊ XUYÊN",
            "Phieu_SoDinhDanh": "012345678901",
            "Phieu_NgaySinh": "02/02/1995",
            "Phieu_GioiTinh": "Nữ",
            "Phieu_HoKhau": {"tinh": "Lai Châu", "xa": "Tân Phong", "diaChi": "Tổ 3"},
            "Phieu_DienThoai": "0987654321",
            "Phieu_Email": "xuyen@example.com",
            "Person1_HoTen": "LÒ THỊ XUYÊN",
            "Person1_SoDinhDanh": "012345678901",
            "Person1_NgayCap": "20/06/2021",
            "Person1_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "Person1_NoiCuTru": {"tinh": "Điện Biên", "xa": "Mường Lay", "diaChi": "Bản 1"},
        },
        {"formContext": {"applicantFullname": "Lò Thị Xuyên", "applicantIdentityNumber": "012345678901"}},
    )

    assert d["data[isOwnerDossierCheck]"] is True
    assert d["data[fullname]"] == "LÒ THỊ XUYÊN"
    assert d["data[identityNumber]"] == "012345678901"
    assert d["data[identityDate]"] == "20/06/2021"
    assert d["data[province]"] == "Lai Châu"
    assert d["data[district]"] == "Tân Phong"
    assert d["data[address]"] == "Tổ 3"
    assert d["data[phoneNumber]"] == "0987654321"
    assert d["data[email]"] == "xuyen@example.com"
    assert "data[ownerFullname]" not in d
    assert not w


def test_different_requester_uses_cccd_requester_and_phieu_owner():
    d, w = _run(
        {
            "Phieu_HoTen": "LÒ THỊ XUYÊN",
            "Phieu_SoDinhDanh": "012345678901",
            "Phieu_NgaySinh": "02/02/1995",
            "Phieu_GioiTinh": "Nữ",
            "Phieu_HoKhau": {"tinh": "Lai Châu", "xa": "Tân Phong", "diaChi": "Tổ 3"},
            "Person1_HoTen": "VŨ ĐÌNH THIẾT",
            "Person1_SoDinhDanh": "040203015844",
            "Person1_NgaySinh": "26/04/2003",
            "Person1_GioiTinh": "Nam",
            "Person1_NgayCap": "25/04/2021",
            "Person1_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "Person1_NoiCuTru": {"tinh": "Phú Thọ", "xa": "Hoàng Cương", "diaChi": "Khu 2"},
        },
        {"formContext": {"applicantFullname": "Vũ Đình Thiết", "applicantIdentityNumber": "040203015844"}},
    )

    assert d["data[isOwnerDossierCheck]"] is False
    assert d["data[fullname]"] == "VŨ ĐÌNH THIẾT"
    assert d["data[identityNumber]"] == "040203015844"
    assert d["data[province]"] == "Phú Thọ"
    assert d["data[ownerFullname]"] == "LÒ THỊ XUYÊN"
    assert d["data[ownerIdentityNumber]"] == "012345678901"
    assert d["data[ownerBirthday]"] == "02/02/1995"
    assert d["data[ownerGender]"] == "Nữ"
    assert d["data[ownerProvince]"] == "Lai Châu"
    assert d["data[ownerDistrict]"] == "Tân Phong"
    assert d["data[ownerAddress]"] == "Tổ 3"
    assert d["data[ownerNation]"] == "Việt Nam"
    assert not w


def test_phieu_address_falls_back_to_notification_address():
    d, w = _run(
        {
            "Phieu_HoTen": "LÒ THỊ XUYÊN",
            "Phieu_SoDinhDanh": "012345678901",
            "Phieu_DiaChiNhanThongBao": {"tinh": "Lai Châu", "xa": "Đoàn Kết", "diaChi": "Số 1"},
        },
        {"formContext": {"applicantFullname": "LÒ THỊ XUYÊN", "applicantIdentityNumber": "012345678901"}},
    )

    assert d["data[isOwnerDossierCheck]"] is True
    assert d["data[province]"] == "Lai Châu"
    assert d["data[district]"] == "Đoàn Kết"
    assert d["data[address]"] == "Số 1"
    assert not w


def test_missing_phieu_returns_warning():
    d, w = _run(
        {
            "Person1_HoTen": "VŨ ĐÌNH THIẾT",
            "Person1_SoDinhDanh": "040203015844",
        },
        {"formContext": {"applicantFullname": "Vũ Đình Thiết", "applicantIdentityNumber": "040203015844"}},
    )

    assert d == {}
    assert "Không đọc được Phiếu đăng ký dự tuyển" in w[0]

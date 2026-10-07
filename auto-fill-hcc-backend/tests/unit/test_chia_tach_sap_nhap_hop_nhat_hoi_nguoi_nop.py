"""Chia, tách, sáp nhập, hợp nhất hội (cấp tỉnh) — hai chế độ người nộp. Chủ hồ sơ = Chủ tịch dự kiến. Dữ liệu giả."""

from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.process import mapper

_OWNER = {
    "ChuHoSo_HoTen": "NGUYỄN VĂN A",
    "ChuHoSo_SoDinhDanh": "001071000001",
    "ChuHoSo_NgaySinh": "01/12/1971",
    "ChuHoSo_GioiTinh": "Nam",
    "ChuHoSo_NgayCap": "28/09/2021",
    "ChuHoSo_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "ChuHoSo_DiaChi": {"quocGia": "Việt Nam", "tinh": "Thành phố Đà Nẵng", "xa": "Phường Giả", "diaChi": "Số 1"},
    "NguoiLienHe_HoTen": "Nguyễn Văn A",
    "NguoiLienHe_DienThoai": "0900000001",
    "LoaiThuTuc": "sáp nhập",
    "HoiThamGia": ["Hội X", "Hội Y"],
    "HoiMoi": ["Hội X"],
}
_TK_KHAC = {"formContext": {"applicantFullname": "Trần Văn B", "applicantIdentityNumber": "001099000002"}}


def _run(options, extra=None):
    values = dict(_OWNER, **(extra or {}))
    out, warnings = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)
    return out, {(f["name"], f.get("occurrence")): f for f in out}, warnings


def test_to_khai_nguoi_nop_la_chu_ho_so_bo_khoa_3_o_va_ghim_phan_i():
    out, d, _ = _run({"submitterMode": "owner_as_submitter", **_TK_KHAC})
    assert d[("data[isOwnerDossierCheck]", None)]["value"] is True
    for name, value in (("data[fullname]", "NGUYỄN VĂN A"), ("data[identityNumber]", "001071000001"),
                        ("data[birthday]", "01/12/1971")):
        assert d[(name, 0)]["value"] == value and d[(name, 0)]["enableInput"] is True
    assert d[("data[district]", None)]["value"] == "Phường Giả"
    assert d[("data[phoneNumber]", None)]["value"] == "0900000001"
    assert d[("data[ownerFullname]", None)]["value"] == "NGUYỄN VĂN A"


def test_tai_khoan_khong_co_moc_khong_tich_khong_dien_phan_i():
    out, d, warnings = _run({})
    assert d[("data[isOwnerDossierCheck]", None)]["value"] is False
    assert not any(name in ("data[gender]", "data[district]", "data[phoneNumber]") for name, _ in d)
    assert not any(f.get("enableInput") for f in out)
    assert d[("data[ownerDistrict]", None)]["value"] == "Phường Giả"
    assert any("F5" in w for w in warnings)


def test_tai_khoan_la_chu_ho_so_thi_tich_khong_ghi_o_khoa():
    out, d, _ = _run({"formContext": {"applicantFullname": "Nguyễn Văn A", "applicantIdentityNumber": "001071000001"}})
    assert d[("data[isOwnerDossierCheck]", None)]["value"] is True
    assert ("data[fullname]", 0) not in d and ("data[identityNumber]", 0) not in d
    assert d[("data[gender]", None)]["value"] == "Nam"
    assert d[("data[phoneNumber]", None)]["value"] == "0900000001"


def test_tai_khoan_khop_cccd_nguoi_khac_bo_tich_phan_i_la_nguoi_do():
    _, d, _ = _run(_TK_KHAC, {"NguoiNop_HoTen": "TRẦN VĂN B", "NguoiNop_SoDinhDanh": "001099000002",
                              "NguoiNop_GioiTinh": "Nam", "NguoiNop_NgayCap": "02/03/2022"})
    assert d[("data[isOwnerDossierCheck]", None)]["value"] is False
    assert d[("data[identityDate]", None)]["value"] == "02/03/2022"
    # SĐT trên Đơn là của người liên hệ (chủ hồ sơ), không gán cho người nộp khác.
    assert ("data[phoneNumber]", None) not in d


def test_tai_khoan_khong_khop_ai_thi_de_trong_va_canh_bao():
    _, d, warnings = _run(_TK_KHAC)
    assert d[("data[isOwnerDossierCheck]", None)]["value"] is False
    assert ("data[gender]", None) not in d
    assert any("không có giấy tờ của tài khoản" in w for w in warnings)

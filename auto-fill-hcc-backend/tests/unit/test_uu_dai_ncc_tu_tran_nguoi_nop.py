"""Hưởng trợ cấp khi người có công từ trần — hai chế độ người nộp. Chủ hồ sơ = người khai. Dữ liệu giả."""

from app.pipelines.uu_dai_ncc_tu_tran.process import mapper

_KHAI = {
    "ToKhai_HoTen": "NGUYỄN VĂN A",
    "ToKhai_SoDinhDanh": "001070000001",
    "ToKhai_NgaySinh": "02/03/1970",
    "ToKhai_GioiTinh": "Nam",
    "TuTran_HoTen": "NGUYỄN VĂN B",
    "TuTran_NgaySinh": "01/01/1940",
}
_TK_KHAC = {"formContext": {"applicantFullname": "Cán Bộ Một Cửa", "applicantIdentityNumber": "001099000009"}}
_TO_KHAI = {"submitterMode": "owner_as_submitter", **_TK_KHAC}


def _run(options, extra=None):
    values = dict(_KHAI, **(extra or {}))
    out, _ = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)
    return out, {(f["name"], f.get("occurrence")): f for f in out}


def test_to_khai_nguoi_nop_la_nguoi_khai_bo_khoa_2_o():
    out, d = _run(_TO_KHAI)
    assert d[("data[isOwnerDossierCheck]", None)]["value"] is True
    assert d[("data[fullname]", 0)]["value"] == "NGUYỄN VĂN A" and d[("data[fullname]", 0)]["enableInput"] is True
    assert d[("data[identityNumber]", None)]["value"] == "001070000001"
    assert d[("data[identityNumber]", None)]["enableInput"] is True
    assert d[("data[birthday]", 0)]["value"] == "02/03/1970"
    # Người từ trần (occ1) không bị bỏ khoá.
    assert "enableInput" not in d[("data[fullname]", 1)]


def test_to_khai_thieu_ngay_sinh_du_thi_xoa_va_danh_dau():
    _, d = _run(_TO_KHAI, {"ToKhai_NgaySinh": "1970"})
    assert d[("data[birthday]", 0)]["clear"] is True and d[("data[birthday]", 0)]["markEmpty"] is True
    assert d[("data[birthday]", 0)]["value"] == ""


def test_tai_khoan_la_nguoi_khac_thi_bo_trong_phan_i():
    out, d = _run(_TK_KHAC)
    assert d[("data[isOwnerDossierCheck]", None)]["value"] is False
    assert ("data[fullname]", 0) not in d
    assert not any(f.get("enableInput") for f in out)
    assert d[("data[ownerFullname]", None)]["value"] == "NGUYỄN VĂN A"


def test_tai_khoan_trung_nguoi_khai_thi_tich_khong_bo_khoa():
    out, d = _run({"formContext": {"applicantFullname": "Nguyễn Văn A", "applicantIdentityNumber": "001070000001"}})
    assert d[("data[isOwnerDossierCheck]", None)]["value"] is True
    assert d[("data[fullname]", 0)]["value"] == "NGUYỄN VĂN A"
    assert not any(f.get("enableInput") for f in out)

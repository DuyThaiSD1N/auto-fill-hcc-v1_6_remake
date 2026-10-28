"""Cấp lại Bằng TQGC: CCCD tải kèm có thể là của người nộp KHÁC người đề nghị trong tờ khai Mẫu 16.
Chủ hồ sơ + Phần III luôn theo tờ khai; không trộn CCCD người khác vào. Dữ liệu giả."""

from app.pipelines.cap_lai_to_quoc_ghi_cong.process import mapper

_TOKHAI = {
    "ToKhai_HoTen": "NGUYỄN VĂN A",
    "ToKhai_SoDinhDanh": "001085000001",
    "ToKhai_NgaySinh": "01/01/1985",
    "ToKhai_GioiTinh": "Nam",
    "ToKhai_NgayCap": "01/09/2025",
    "ToKhai_DienThoai": "0900000001",
}
_CCCD_KHAC = {
    "Person1_HoTen": "TRẦN THỊ B",
    "Person1_SoDinhDanh": "002199000002",
    "Person1_NgaySinh": "02/02/1999",
    "Person1_GioiTinh": "Nữ",
    "Person1_NgayCap": "02/09/2024",
}


def _map(values, options=None):
    fields, _ = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options or {})
    return {(f["name"], f.get("occurrence")): f["value"] for f in fields}


def test_cccd_nguoi_khac_khong_tron_vao_chu_ho_so():
    d = _map({**_TOKHAI, **_CCCD_KHAC})
    assert d[("data[ownerFullname]", None)] == "NGUYỄN VĂN A"
    assert d[("data[ownerIdentityNumber]", None)] == "001085000001"
    assert d[("data[fullname]", 1)] == "NGUYỄN VĂN A"
    assert d[("data[identityNumber]", 1)] == "001085000001"
    # Không mốc tài khoản: CCCD người khác = người nộp, bỏ tích "người nộp là chủ hồ sơ".
    assert d[("data[isOwnerDossierCheck]", None)] is False
    assert d[("data[fullname]", 0)] == "TRẦN THỊ B"
    assert d[("data[identityNumber]", 0)] == "002199000002"


def test_cccd_cung_nguoi_thi_tron_va_tich_chu_ho_so():
    cccd = {"Person1_HoTen": "NGUYỄN VĂN A", "Person1_SoDinhDanh": "001085000001", "Person1_NgayCap": "03/03/2021"}
    d = _map({**_TOKHAI, **cccd})
    assert d[("data[isOwnerDossierCheck]", None)] is True
    assert d[("data[fullname]", 0)] == "NGUYỄN VĂN A"
    # Ngày cấp ưu tiên CCCD khi đúng người.
    assert d[("data[ownerIdentityDate]", None)] == "03/03/2021"


def test_co_moc_tai_khoan_khac_nguoi_de_nghi_thi_khong_dien_phan_i():
    ctx = {"formContext": {"applicantFullname": "TRẦN THỊ B", "applicantIdentityNumber": "002199000002"}}
    d = _map({**_TOKHAI, **_CCCD_KHAC}, ctx)
    assert d[("data[isOwnerDossierCheck]", None)] is False
    assert ("data[fullname]", 0) not in d
    assert d[("data[ownerFullname]", None)] == "NGUYỄN VĂN A"

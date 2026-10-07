"""Xác định mức độ khuyết tật — chủ hồ sơ = người ở mục I; người nộp có hai chế độ.

Theo tài khoản (mặc định): người nộp khớp mỏ neo UI. Theo tờ khai (`submitterMode`): người nộp là
người đại diện hợp pháp (mục II); mục II trống thì người khuyết tật tự nộp. Dữ liệu giả.
"""

import asyncio

from app.pipelines.khuyet_tat.process import mapper, runner

_TO_KHAI = {"submitterMode": "owner_as_submitter"}
_TK_DAI_DIEN = {"formContext": {"applicantFullname": "NGUYỄN VĂN CHA", "applicantIdentityNumber": "001080000002"}}
_TK_NKT = {"formContext": {"applicantFullname": "NGUYỄN VĂN CON", "applicantIdentityNumber": "001220000001"}}

_MUC_I = {
    "Nkt_HoTen": "Nguyễn Văn Con",
    "Nkt_SoDinhDanh": "001220000001",
    "Nkt_NgaySinh": "01/02/2020",
    "Nkt_GioiTinh": "Nam",
    "Nkt_ThuongTru": {"quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "Giả", "diaChi": "Tổ 1"},
}
_MUC_II = {
    "Ndd_HoTen": "Nguyễn Văn Cha",
    "Ndd_SoDinhDanh": "001080000002",
    "Ndd_NgaySinh": "03/04/1980",
    "Ndd_NgayCap": "05/06/2022",
    "Ndd_SoDienThoai": "0900000002",
    "Ndd_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "Giả", "diaChi": "Tổ 2"},
}


def _fields(*groups):
    values = {}
    for group in groups:
        values.update(group)
    return [{"name": k, "comp": "x-input", "value": v} for k, v in values.items()]


def _values(out):
    return {f["name"]: f["value"] for f in out}


def test_chu_ho_so_du_phong_tu_muc_i_khong_lay_nguoi_dai_dien():
    d = _values(mapper.enrich(_fields(_MUC_I, _MUC_II), {}))
    assert d["data[ownerFullname]"] == "Nguyễn Văn Con"
    assert d["data[ownerIdentityNumber]"] == "001220000001"
    assert d["data[ownerBirthday]"] == "01/02/2020"


def test_tai_khoan_nguoi_dai_dien_bo_tich_chu_ho_so_la_nguoi_khuyet_tat():
    out = mapper.enrich(_fields(_MUC_I, _MUC_II), _TK_DAI_DIEN)
    assert not any(f.get("enableInput") for f in out)
    d = _values(out)
    assert d["data[isOwnerDossierCheck]"] is False
    assert d["data[fullname]"] == "NGUYỄN VĂN CHA"
    assert d["data[ownerFullname]"] == "Nguyễn Văn Con"


def test_tai_khoan_la_nguoi_khuyet_tat_thi_tich():
    d = _values(mapper.enrich(_fields(_MUC_I), _TK_NKT))
    assert d["data[isOwnerDossierCheck]"] is True
    assert d["data[ownerFullname]"] == "Nguyễn Văn Con"


def test_to_khai_nguoi_nop_la_nguoi_dai_dien_bo_qua_tai_khoan():
    out = mapper.enrich(_fields(_MUC_I, _MUC_II), {**_TO_KHAI, **_TK_NKT})
    d = _values(out)
    assert out[0]["name"] == "data[isOwnerDossierCheck]" and out[0]["value"] is False
    assert d["data[fullname]"] == "Nguyễn Văn Cha"
    assert d["data[identityNumber]"] == "001080000002"
    assert d["data[birthday]"] == "03/04/1980"
    assert d["data[identityDate]"] == "05/06/2022"
    assert d["data[address]"] == "Tổ 2"
    assert d["data[phoneNumber]"] == "0900000002"
    locked = {f["name"]: f.get("enableInput") for f in out if f["name"] in ("data[fullname]", "data[identityNumber]")}
    assert locked == {"data[fullname]": True, "data[identityNumber]": True}
    # Mục II không ghi giới tính/nơi cấp → để trống, không bịa.
    assert "data[gender]" not in d and "data[idIssuePlace]" not in d
    assert d["data[ownerFullname]"] == "Nguyễn Văn Con"


def test_to_khai_muc_ii_trong_thi_nguoi_khuyet_tat_tu_nop():
    out = mapper.enrich(_fields(_MUC_I), _TO_KHAI)
    d = _values(out)
    assert out[0]["name"] == "data[isOwnerDossierCheck]" and out[0]["value"] is True
    assert d["data[fullname]"] == "Nguyễn Văn Con"
    assert d["data[identityNumber]"] == "001220000001"
    assert d["data[ownerFullname]"] == "Nguyễn Văn Con"


def test_to_khai_khong_dua_moc_tai_khoan_vao_prompt():
    ctx = asyncio.run(runner._owner_only_context([{"text": "CCCD 001080000002"}], {**_TO_KHAI, **_TK_DAI_DIEN}))
    assert 'result="missing_ui_anchor"' in ctx
    assert "001080000002" not in ctx and "NGUYỄN VĂN CHA" not in ctx

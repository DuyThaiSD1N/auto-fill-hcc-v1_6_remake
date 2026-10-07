"""[Đà Nẵng] Đăng ký BPBĐ — chỉ chế độ tờ khai: chủ hồ sơ = người yêu cầu đăng ký (tổ chức cử người theo Giấy giới
thiệu), người nộp = người được giới thiệu. Mốc tài khoản bị bỏ qua. Dữ liệu giả."""

import asyncio

from app.pipelines.dang_ky_bien_phap_bao_dam_qsdd.process import mapper, runner

_TK = {"formContext": {"applicantFullname": "Cán Bộ Một Cửa", "applicantIdentityNumber": "001099000009"}}


def _run(values, options=None):
    out, warnings = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options or _TK)
    return out, {f["name"]: f for f in out}, warnings


def test_ngan_hang_gioi_thieu_can_bo_di_nop():
    out, d, warnings = _run({
        "ChuThe_LoaiChuThe": "Tổ chức",
        "ChuThe_TenToChuc": "NGÂN HÀNG GIẢ - CHI NHÁNH A",
        "NguoiNop_HoTen": "NGUYỄN VĂN B",
        "NguoiNop_SoDinhDanh": "001071000002",
        "NguoiNop_NgayCap": "22/04/2021",
    })
    assert d["data[chonDoiTuong]"]["value"] == "Tổ chức"
    assert d["data[organization]"]["value"] == "NGÂN HÀNG GIẢ - CHI NHÁNH A"
    assert d["data[ownerFullname]"]["value"] == "NGÂN HÀNG GIẢ - CHI NHÁNH A"
    assert d["data[isOwnerDossier]"]["value"] is False
    assert d["data[fullname]"]["value"] == "NGUYỄN VĂN B" and d["data[fullname]"]["enableInput"] is True
    assert d["data[identityNumber]"]["value"] == "001071000002" and d["data[identityNumber]"]["enableInput"] is True
    assert d["data[identityDate]"]["value"] == "22/04/2021"
    # Giấy giới thiệu không có ngày sinh → xoá ngày sinh tài khoản cổng đổ sẵn, không bịa giới tính/nơi cấp.
    assert d["data[birthday]"]["clear"] is True and d["data[birthday]"]["markEmpty"] is True
    assert "data[gender]" not in d and "data[identityAgency]" not in d
    assert not warnings


def test_ca_nhan_tu_di_dang_ky_thi_tich_va_dien_nhan_than():
    _, d, _ = _run({
        "ChuThe_LoaiChuThe": "Cá nhân",
        "ChuThe_HoTen": "TRẦN THỊ C",
        "ChuThe_SoDinhDanh": "001190000003",
        "ChuThe_NgaySinh": "01/02/1990",
        "ChuThe_GioiTinh": "Nữ",
    })
    assert d["data[isOwnerDossier]"]["value"] is True
    assert d["data[ownerFullname]"]["value"] == "TRẦN THỊ C"
    assert d["data[fullname]"]["value"] == "TRẦN THỊ C"
    assert d["data[birthday]"]["value"] == "01/02/1990"


def test_ca_nhan_uy_quyen_nguoi_khac_di_nop():
    _, d, _ = _run({
        "ChuThe_LoaiChuThe": "Cá nhân",
        "ChuThe_HoTen": "TRẦN THỊ C",
        "ChuThe_SoDinhDanh": "001190000003",
        "NguoiNop_HoTen": "LÊ VĂN D",
        "NguoiNop_SoDinhDanh": "001085000004",
    })
    assert d["data[isOwnerDossier]"]["value"] is False
    assert d["data[ownerFullname]"]["value"] == "TRẦN THỊ C"
    assert d["data[fullname]"]["value"] == "LÊ VĂN D"


def test_runner_khong_dua_moc_tai_khoan_vao_prompt(monkeypatch):
    captured = {}

    async def fake_compact(_files_by_role, **kwargs):
        captured.update(kwargs)
        return {"fields": [], "errors": []}

    monkeypatch.setattr(runner.runner, "run", fake_compact)
    asyncio.run(runner.run({"doc": []}, _TK))
    assert captured.get("context_builder") is None

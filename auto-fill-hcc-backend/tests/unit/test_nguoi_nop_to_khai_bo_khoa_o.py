"""Chế độ người nộp theo tờ khai: họ tên + CCCD Phần I (cổng khoá theo VNeID) kèm enableInput để extension bỏ disabled.

Chỉ Phần I (occurrence rỗng/0); bản lặp ở tờ khai chi tiết (occurrence 1) và chế độ theo tài khoản không đổi.
"""

import asyncio
import importlib

import pytest

PACKAGES = [
    "dieu_chinh_huu_tri_xa_hoi",
    "tro_cap_tho_cung_liet_si",
    "ho_tro_mai_tang",
    "ho_tro_mai_tang_huu_tri_xa_hoi",
    "tro_cap_xa_hoi_hang_thang",
]

_MAPPED = [
    {"name": "data[fullname]", "comp": "dom-input", "value": "NGUYỄN VĂN A", "occurrence": 0},
    {"name": "data[identityNumber]", "comp": "dom-input", "value": "001000000001"},
    {"name": "data[birthday]", "comp": "dom-date", "value": "01/01/1950"},
    {"name": "data[fullname]", "comp": "dom-input", "value": "NGUYỄN VĂN A", "occurrence": 1},
]


def _run(monkeypatch, package, options):
    mod = importlib.import_module(f"app.pipelines.{package}.process.runner")

    async def fake_compact(_files_by_role, **_kwargs):
        return {"fields": [], "errors": []}

    monkeypatch.setattr(mod.runner, "run", fake_compact)
    monkeypatch.setattr(mod.mapper, "enrich", lambda _fields, _options: ([dict(f) for f in _MAPPED], []))
    res = asyncio.run(mod.run({"doc": []}, options))
    return {(f["name"], f.get("occurrence")): f.get("enableInput") for f in res["fields"]}


@pytest.mark.parametrize("package", PACKAGES)
def test_to_khai_bo_khoa_ho_ten_va_cccd_phan_i(monkeypatch, package):
    flags = _run(monkeypatch, package, {"submitterMode": "owner_as_submitter"})
    assert flags[("data[fullname]", 0)] is True
    assert flags[("data[identityNumber]", None)] is True
    assert flags[("data[birthday]", None)] is None
    assert flags[("data[fullname]", 1)] is None


@pytest.mark.parametrize("package", PACKAGES)
def test_theo_tai_khoan_giu_khoa(monkeypatch, package):
    flags = _run(monkeypatch, package, {})
    assert not any(flags.values())


def _quy_hoach_fields(options):
    from app.pipelines.cung_cap_thong_tin_quy_hoach.process import mapper

    facts = [
        {"name": "NguoiNop_HoTen", "value": "Trần Văn B"},
        {"name": "NguoiNop_SoDinhDanh", "value": "001000000002"},
        {"name": "NguoiNop_NgaySinh", "value": "02/03/1990"},
        {"name": "NguoiNop_ThuongTru", "value": {"tinh": "Tỉnh Quảng Ngãi", "xa": "Phường Đăk Bla", "diaChi": "Số 1"}},
    ]
    fields, _ = mapper.enrich(facts, options)
    return {(f["name"], f.get("occurrence")): f for f in fields if f["comp"] != "dom-expect"}


def test_quy_hoach_dien_ca_khoi_thong_tin_chi_tiet():
    # Khối "Thông tin người nộp hồ sơ" lặp lại ở "Thông tin chi tiết" (occurrence 1) → điền cả hai khối.
    fields = _quy_hoach_fields({})
    for occ in (0, 1):
        assert fields[("data[fullname]", occ)]["value"] == "Trần Văn B"
        assert fields[("data[identityNumber]", occ)]["value"] == "001000000002"
        assert fields[("data[birthday]", occ)]["value"] == "02/03/1990"
        assert fields[("data[district]", occ)]["value"] == "Phường Đăk Bla"
    assert not any(f.get("enableInput") for f in fields.values())


def test_quy_hoach_to_khai_bo_khoa_ho_ten_va_cccd():
    fields = _quy_hoach_fields({
        "submitterMode": "owner_as_submitter",
        "formContext": {"applicantFullname": "Lê Thị C", "applicantIdentityNumber": "001000000009"},
    })
    for occ in (0, 1):
        assert fields[("data[fullname]", occ)]["enableInput"] is True
        assert fields[("data[identityNumber]", occ)]["enableInput"] is True
        assert "enableInput" not in fields[("data[birthday]", occ)]


# ---- Lào Cai cổng iGate mới ("FORM NGUOI NOP"): helper dùng chung của mọi pipeline *_igate_lao_cai ----
def test_lao_cai_cong_moi_o_khoa_du_ba_o():
    from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process import mapper

    fields = mapper.o_khoa_theo_to_khai("Lê thị  c", "0010 9900 0009", "1990", "9/3/1990")
    assert [(f["name"], f["comp"], f["value"]) for f in fields] == [
        ("data[fullname]", "dom-input", "LÊ THỊ C"),
        ("data[identityNumber]", "dom-input", "001099000009"),
        ("data[birthday]", "dom-date", "09/03/1990"),  # bỏ "1990", lấy ngày đủ của nguồn sau
    ]
    assert all(f["enableInput"] is True and not f.get("clear") for f in fields)


def test_lao_cai_cong_moi_o_khoa_thieu_thi_xoa_va_to_do():
    from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process import mapper

    fields = {f["name"]: f for f in mapper.o_khoa_theo_to_khai("Lê Thị C", "12345", None)}
    for name in ("data[identityNumber]", "data[birthday]"):
        assert fields[name]["value"] == "" and fields[name]["clear"] is True and fields[name]["markEmpty"] is True
        assert fields[name]["enableInput"] is True
    # Không có họ tên → không đụng ô nào (ghi riêng số là ghép tên tài khoản với số người khác).
    assert mapper.o_khoa_theo_to_khai(None, "001099000009", "09/03/1990") == []


def test_lao_cai_cong_moi_o_khoa_tu_mapper_cong_cu():
    from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process import mapper

    old = [
        {"name": "CongDan_tenCongDan", "comp": "dom-input", "value": "Hà Văn E"},
        {"name": "CongDan_soCmnd", "comp": "dom-input", "value": "001099000082"},
        {"name": "CongDan_ngaySinhCongDan", "comp": "dom-input", "value": "", "clear": True, "markEmpty": True},
        {"name": "CongDan_diaChi", "comp": "dom-input", "value": "Tổ 5"},
    ]
    fields = {f["name"]: f for f in mapper.o_khoa_tu_cong_cu(old)}
    assert set(fields) == {"data[fullname]", "data[identityNumber]", "data[birthday]"}
    assert fields["data[fullname]"]["value"] == "HÀ VĂN E"
    assert fields["data[birthday]"]["clear"] is True

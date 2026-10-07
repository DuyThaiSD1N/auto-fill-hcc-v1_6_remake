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

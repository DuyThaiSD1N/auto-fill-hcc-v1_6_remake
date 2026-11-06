"""Admin toàn hệ thống lọc bảng thống kê theo một tỉnh.

`province` chỉ THU HẸP phạm vi đã phân giải từ token: admin toàn hệ thống bó về các đơn vị của
tỉnh đó; tài khoản Tỉnh / xã gửi lên thì bỏ qua (phạm vi vẫn khóa theo token).
"""
import pytest

from app.core.errors import AppError
from app.dashboard import router as dashboard_router
from app.dashboard import scope as dashboard_scope


def _unit(uid, tinh, xa):
    return {"unitId": uid, "name": f"hcc{uid}", "xa": xa, "tinh": tinh, "role": "commune", "accessDisabled": False}


_UNITS = [
    _unit("1", "Tỉnh Lai Châu", "Xã A"),
    _unit("2", "Lai Châu", "Xã B"),
    _unit("3", "Thành phố Đà Nẵng", "Phường C"),
    _unit("4", None, None),
]


def _scope(kind):
    return {
        "role": "admin" if kind != "province" else "province_admin",
        "scopeKind": kind,
        "province": None if kind == "all" else "Tỉnh Lai Châu",
        "canViewUnits": True,
        "self": _UNITS[0],
        "units": list(_UNITS) if kind == "all" else _UNITS[:2],
    }


@pytest.fixture()
def as_kind(monkeypatch):
    def use(kind):
        async def fake(_user):
            return _scope(kind)
        monkeypatch.setattr(dashboard_router, "resolve_dashboard_scope", fake)
    return use


def test_danh_sach_tinh_gop_ten_va_dem_don_vi():
    options = dashboard_scope.province_options(_UNITS)
    assert {o["name"]: o["unitCount"] for o in options} == {"Tỉnh Lai Châu": 2, "Thành phố Đà Nẵng": 1}


@pytest.mark.asyncio
async def test_scope_admin_co_danh_sach_tinh(as_kind):
    as_kind("all")
    body = await dashboard_router.scope(user={}, province=None)
    assert body["unitCount"] == 4
    assert [p["name"] for p in body["provinces"]] == ["Thành phố Đà Nẵng", "Tỉnh Lai Châu"]


@pytest.mark.asyncio
async def test_scope_admin_loc_tinh_chi_con_don_vi_cua_tinh(as_kind):
    as_kind("all")
    body = await dashboard_router.scope(user={}, province="lai chau")
    assert body["scopeKind"] == "all"
    assert body["province"] == "Tỉnh Lai Châu"
    assert [u["unitId"] for u in body["units"]] == ["1", "2"]
    assert len(body["provinces"]) == 2, "ô chọn tỉnh vẫn phải đủ mọi tỉnh khi đang lọc"


@pytest.mark.asyncio
async def test_tinh_khong_co_don_vi_bi_chan(as_kind):
    as_kind("all")
    with pytest.raises(AppError) as err:
        await dashboard_router.scope(user={}, province="Tỉnh Cao Bằng")
    assert err.value.error == "PROVINCE_OUT_OF_SCOPE"


@pytest.mark.asyncio
async def test_tai_khoan_tinh_gui_province_bi_bo_qua(as_kind):
    as_kind("province")
    body = await dashboard_router.scope(user={}, province="Đà Nẵng")
    assert body["province"] == "Tỉnh Lai Châu"
    assert [u["unitId"] for u in body["units"]] == ["1", "2"]
    assert "provinces" not in body


def test_chon_don_vi_ngoai_tinh_dang_loc_bi_chan():
    narrowed = dashboard_scope.narrow_to_province(_scope("all"), "Đà Nẵng")
    with pytest.raises(AppError) as err:
        dashboard_router._resolve_user_ids(narrowed, "1")
    assert err.value.error == "UNIT_OUT_OF_SCOPE"


@pytest.mark.asyncio
async def test_nhat_ky_chi_lay_ho_so_cua_tinh_dang_loc(as_kind, monkeypatch):
    as_kind("all")
    seen = {}

    async def no_parents():
        return {}

    async def fake_list(**kwargs):
        seen["user_ids"] = kwargs["user_ids"]
        return {"items": [], "total": 0}

    monkeypatch.setattr(dashboard_router.tdp_rollup, "load_tdp_parents", no_parents)
    monkeypatch.setattr(dashboard_router.dossiers_repo, "list_for_dashboard", fake_list)
    body = await dashboard_router.logs(
        user={}, dateFrom=None, dateTo=None, unit=None, province="Đà Nẵng",
        status="all", source="all", page=1, pageSize=15,
    )
    assert sorted(seen["user_ids"]) == ["3"]
    assert body["scope"]["province"] == "Thành phố Đà Nẵng"

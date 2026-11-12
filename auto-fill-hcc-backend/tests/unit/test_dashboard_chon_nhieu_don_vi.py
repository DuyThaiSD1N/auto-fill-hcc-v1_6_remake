"""Bảng thống kê lọc NHIỀU đơn vị cùng lúc (tick chọn vài xã).

`unit` nhận một mã (hợp đồng cũ, web quản trị cũ vẫn gửi) hoặc nhiều mã cách nhau dấu phẩy: số
liệu phần "đang chọn" là tổng các đơn vị đã tick; chọn 1 đơn vị phải ra y như trước.
"""
import io

import pytest
from openpyxl import load_workbook

from app.core.errors import AppError
from app.dashboard import export as dashboard_export
from app.dashboard import router as dashboard_router


def _unit(uid, xa):
    return {"unitId": uid, "name": f"HCC {xa}", "xa": xa, "tinh": "Tỉnh T", "role": "commune", "accessDisabled": False}


_UNITS = [_unit("1", "Xã A"), _unit("2", "Xã B"), _unit("3", "Xã C")]
_SCOPE = {"role": "province_admin", "scopeKind": "province", "province": "Tỉnh T", "canViewUnits": True,
          "self": _UNITS[0], "units": _UNITS}
# Mỗi đơn vị: (số hồ sơ Auto Fill, số hồ sơ Handfree) của cùng một thủ tục.
_COUNTS = {"1": (5, 1), "2": (3, 0), "3": (10, 4)}


@pytest.fixture()
def fake_sources(monkeypatch):
    async def resolve(_user, _province):
        return _SCOPE

    async def af_stats(user_ids, date_from, date_to, experience):
        wards = [{"userId": u, "requests": _COUNTS[u][0] * 2,
                  "procedures": [{"key": "khai_sinh", "label": "Khai sinh", "count": _COUNTS[u][0]}]} for u in user_ids]
        return {"wards": wards, "procedures": [{"key": "khai_sinh", "label": "Khai sinh",
                                                "count": sum(_COUNTS[u][0] for u in user_ids)}],
                "totalDossiers": sum(_COUNTS[u][0] for u in user_ids), "totalRequests": 0}

    async def hf_units(units, date_from, date_to, want_daily):
        by_key = {dashboard_router.unit_key(u["tinh"], u["xa"]): {"procedures": [
            {"procedureKey": "khai_sinh", "label": "Khai sinh", "count": _COUNTS[u["unitId"]][1]}]} for u in units}
        return by_key, {}, True

    async def af_daily(user_ids, date_from, date_to, experience):
        return [{"date": "2026-11-10", "count": sum(_COUNTS[u][0] for u in user_ids)}]

    async def hf_daily(units, date_from, date_to):
        return {"2026-11-10": sum(_COUNTS[u["unitId"]][1] for u in units)}

    monkeypatch.setattr(dashboard_router, "_resolve", resolve)
    monkeypatch.setattr(dashboard_router.cutover, "dossier_stats", af_stats)
    monkeypatch.setattr(dashboard_router.cutover, "daily_dossier_counts", af_daily)
    monkeypatch.setattr(dashboard_router, "fetch_handfree", hf_units)
    monkeypatch.setattr(dashboard_router, "fetch_handfree_daily", hf_daily)


def test_phan_giai_mot_nhieu_va_tat_ca():
    assert dashboard_router._resolve_user_ids(_SCOPE, "all") == (["1", "2", "3"], [])
    assert dashboard_router._resolve_user_ids(_SCOPE, "2") == (["2"], [_UNITS[1]])
    ids, chosen = dashboard_router._resolve_user_ids(_SCOPE, " 3 ,1, 3,")
    assert ids == ["3", "1"] and chosen == [_UNITS[2], _UNITS[0]]


def test_mot_ma_ngoai_pham_vi_la_chan_ca_luot():
    with pytest.raises(AppError) as err:
        dashboard_router._resolve_user_ids(_SCOPE, "1,9")
    assert err.value.error == "UNIT_OUT_OF_SCOPE"


async def _summary(unit):
    return await dashboard_router.summary(user={}, dateFrom=None, dateTo=None, unit=unit, province=None)


@pytest.mark.asyncio
async def test_chon_nhieu_don_vi_cong_dung_cac_don_vi_da_chon(fake_sources):
    body = await _summary("1,2")
    assert body["selected"] is None
    assert [u["unitId"] for u in body["selectedUnits"]] == ["1", "2"]
    assert body["kpis"]["dossiers"] == 5 + 1 + 3 + 0
    assert body["kpis"]["requests"] == (5 + 3) * 2
    assert body["byProcedure"][0]["count"] == 9
    assert body["byDay"] == [{"date": "2026-11-10", "count": 9}]
    assert len(body["units"]) == 3, "bảng đơn vị vẫn đủ phạm vi để dựng ô chọn"


@pytest.mark.asyncio
async def test_chon_mot_don_vi_giu_hop_dong_cu(fake_sources):
    body = await _summary("3")
    assert body["selected"]["unitId"] == "3"
    assert [u["unitId"] for u in body["selectedUnits"]] == ["3"]
    assert body["kpis"]["dossiers"] == 14
    all_body = await _summary(None)
    assert all_body["selected"] is None and all_body["selectedUnits"] == []
    assert all_body["kpis"]["dossiers"] == 23


@pytest.mark.asyncio
async def test_excel_chon_nhieu_chi_gom_don_vi_da_chon(fake_sources):
    data = await _summary("3,1")
    wb = load_workbook(io.BytesIO(dashboard_export.build_dashboard_workbook(data, [])))
    rows = [r[1] for r in wb["Theo đơn vị"].iter_rows(min_row=2, values_only=True) if r[1] and r[1] != "TỔNG CỘNG"]
    assert sorted(rows) == ["HCC Xã A", "HCC Xã C"]
    overview = [c for row in wb["Tổng hợp"].iter_rows(values_only=True) for c in row if c]
    assert "2 đơn vị đã chọn: Xã C, Xã A" in overview
    assert "Đơn vị phát sinh" not in [c.value for c in wb["Theo thủ tục"][1]]
    assert dashboard_export.export_filename(data).startswith("Thong ke ho so - 2-don-vi - ")


@pytest.mark.asyncio
async def test_excel_chon_mot_don_vi_van_du_bang_don_vi(fake_sources):
    data = await _summary("3")
    wb = load_workbook(io.BytesIO(dashboard_export.build_dashboard_workbook(data, [])))
    rows = [r[1] for r in wb["Theo đơn vị"].iter_rows(min_row=2, values_only=True) if r[1] and r[1] != "TỔNG CỘNG"]
    assert len(rows) == 3
    assert dashboard_export.export_filename(data).startswith("Thong ke ho so - HCC Xã C - ")

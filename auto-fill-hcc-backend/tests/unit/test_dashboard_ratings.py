"""Màn "Đánh giá công dân": phiếu đánh giá trên hồ sơ ĐÃ NỘP, chia đúng một nhóm mỗi hồ sơ."""
import pytest

from app.core.errors import AppError
from app.dashboard import ratings as dashboard_ratings
from app.dashboard import router as dashboard_router
from app.dossiers import stats as dossier_stats
from app.users import tdp_rollup

_UNITS = [
    {"unitId": "u1", "name": "HCC Xã A", "xa": "Xã A", "tinh": "Tỉnh T", "role": "commune"},
    {"unitId": "u2", "name": "HCC Phường B", "xa": "Phường B", "tinh": "Tỉnh T", "role": "commune"},
    {"unitId": "u3", "name": "HCC Xã C", "xa": "Xã C", "tinh": "Tỉnh T", "role": "commune"},
]


def _scope(can_view_units=True, units=None):
    units = units if units is not None else _UNITS
    return {
        "role": "province_admin" if can_view_units else "commune",
        "scopeKind": "province" if can_view_units else "unit",
        "province": "Tỉnh T",
        "canViewUnits": can_view_units,
        "units": units,
        "self": units[0],
    }


def _row(user_id, level, rated, count):
    return {"userId": user_id, "level": level, "rated": rated, "count": count}


@pytest.fixture
def patch_data(monkeypatch):
    def _apply(scope, rows):
        async def _resolve(_user):
            return scope

        async def _counts(**_kwargs):
            return rows

        monkeypatch.setattr(dashboard_router, "resolve_dashboard_scope", _resolve)
        monkeypatch.setattr(dossier_stats, "rating_counts", _counts)

    return _apply


async def _call(unit=None):
    return await dashboard_router.ratings(user={}, dateFrom=None, dateTo=None, unit=unit)


def test_moi_ho_so_roi_dung_mot_nhom():
    assert dashboard_ratings.bucket(5, True) == "5"
    assert dashboard_ratings.bucket(1, True) == "1"
    # Bấm bỏ qua: có phiếu nhưng không có mức — khác hẳn hồ sơ chưa từng được hỏi.
    assert dashboard_ratings.bucket(None, True) == "skipped"
    assert dashboard_ratings.bucket(None, False) == "none"
    # Mức lạ ngoài thang không được tính thành một mức thật.
    assert dashboard_ratings.bucket(9, True) == "skipped"


def test_cac_nhom_cong_du_so_ho_so_da_nop():
    summary = dashboard_ratings.summarize({"5": 6, "4": 2, "3": 1, "1": 1, "skipped": 3, "none": 7})
    assert summary["submitted"] == 20
    assert summary["rated"] == 10
    assert summary["skipped"] == 3
    assert summary["unrated"] == 7
    assert summary["rated"] + summary["skipped"] + summary["unrated"] == summary["submitted"]
    assert summary["satisfied"] == 8, "hài lòng trở lên = mức 4 và 5"
    assert summary["average"] == 4.2  # (6×5 + 2×4 + 3 + 1) / 10
    assert [lv["level"] for lv in summary["levels"]] == [5, 4, 3, 2, 1]
    assert summary["levels"][3] == {"level": 2, "label": "Chưa hài lòng", "count": 0}


def test_chua_co_phieu_nao_thi_khong_bia_diem_trung_binh():
    summary = dashboard_ratings.summarize({"none": 4})
    assert summary["average"] is None
    assert summary["submitted"] == 4


async def test_tai_khoan_tinh_co_bang_theo_don_vi(patch_data):
    patch_data(_scope(), [
        _row("u1", 5, True, 3), _row("u1", None, False, 2),
        _row("u2", 4, True, 1), _row("u2", 5, True, 4), _row("u2", None, True, 1),
    ])
    res = await _call()
    assert res["submitted"] == 11
    assert res["rated"] == 8
    assert res["skipped"] == 1
    assert res["unrated"] == 2
    # Đơn vị không có hồ sơ đã nộp (u3) không vào bảng; xếp theo số phiếu giảm dần.
    assert [u["unitId"] for u in res["units"]] == ["u2", "u1"]
    assert res["units"][0]["rated"] == 5
    assert res["units"][1]["unrated"] == 2


async def test_loc_mot_don_vi_thi_tong_theo_don_vi_do_bang_van_toan_pham_vi(patch_data):
    patch_data(_scope(), [_row("u1", 5, True, 3), _row("u2", 4, True, 2)])
    res = await _call(unit="u2")
    assert res["selected"]["unitId"] == "u2"
    assert res["submitted"] == 2
    assert res["levels"][1]["count"] == 2
    assert {u["unitId"] for u in res["units"]} == {"u1", "u2"}


async def test_tai_khoan_xa_khong_thay_don_vi_khac(patch_data):
    patch_data(_scope(can_view_units=False, units=[_UNITS[0]]), [_row("u1", 5, True, 1)])
    res = await _call()
    assert res["rated"] == 1
    assert res["units"] == []


async def test_don_vi_ngoai_pham_vi_bi_chan(patch_data):
    patch_data(_scope(can_view_units=False, units=[_UNITS[0]]), [])
    with pytest.raises(AppError):
        await _call(unit="u2")


async def test_phieu_cua_to_dan_pho_tinh_vao_xa_cha(patch_data, monkeypatch):
    async def _links():
        return {"tdp1": {"parentId": "u1", "parentName": "HCC Xã A"}}

    monkeypatch.setattr(tdp_rollup, "load_tdp_parents", _links)
    patch_data(_scope(), [_row("u1", 5, True, 1), _row("tdp1", 3, True, 2)])
    res = await _call()
    assert [u["unitId"] for u in res["units"]] == ["u1"]
    assert res["units"][0]["rated"] == 3
    assert res["units"][0]["levels"][2]["count"] == 2

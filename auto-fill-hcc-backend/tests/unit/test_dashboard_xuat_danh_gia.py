"""Xuất Excel màn "Đánh giá công dân" của bảng thống kê: đúng số của /ratings, có sheet theo đơn vị khi xem nhiều đơn vị."""
import io

import pytest
from openpyxl import load_workbook

from app.dashboard import router as dashboard_router
from app.dashboard.export import build_ratings_workbook, ratings_filename


def _levels(c5, c4, c3, c2, c1):
    labels = {5: "Rất hài lòng", 4: "Hài lòng", 3: "Bình thường", 2: "Chưa hài lòng", 1: "Rất không hài lòng"}
    return [{"level": lv, "label": labels[lv], "count": c} for lv, c in zip((5, 4, 3, 2, 1), (c5, c4, c3, c2, c1))]


def _unit(uid, xa, c5, c4, skipped, unrated):
    rated = c5 + c4
    return {"unitId": uid, "name": f"HCC {xa}", "xa": xa, "submitted": rated + skipped + unrated, "rated": rated,
            "skipped": skipped, "unrated": unrated, "satisfied": rated, "average": 4.5, "levels": _levels(c5, c4, 0, 0, 0)}


def _data(can_view_units=True, selected_units=None):
    return {
        "scope": {"canViewUnits": can_view_units, "province": "Tỉnh Lai Châu", "scopeKind": "province",
                  "self": {"name": "HCC Xã A", "xa": "Xã A"}},
        "selected": None,
        "selectedUnits": selected_units or [],
        "range": {"from": "2026-11-01", "to": "2026-11-23"},
        "submitted": 20, "rated": 12, "skipped": 3, "unrated": 5, "satisfied": 11, "average": 4.58,
        "levels": _levels(8, 3, 1, 0, 0),
        "units": [_unit("ua", "Xã A", 5, 2, 1, 2), _unit("ub", "Phường B", 3, 2, 2, 3)],
    }


def _rows(ws):
    return [tuple(c for c in row) for row in ws.iter_rows(values_only=True)]


def test_tong_hop_va_phan_bo_cong_du_ho_so_da_nop():
    wb = load_workbook(io.BytesIO(build_ratings_workbook(_data())))
    assert wb.sheetnames == ["Tổng hợp", "Theo đơn vị"]
    rows = _rows(wb["Tổng hợp"])
    by_label = {r[1]: r for r in rows if r[1]}
    assert by_label["Hồ sơ đã nộp"][2] == 20
    assert by_label["Có đánh giá (chấm mức)"][2:4] == (12, 0.6)
    assert by_label["Hài lòng (Rất hài lòng + Hài lòng)"][2] == 11
    assert abs(by_label["Hài lòng (Rất hài lòng + Hài lòng)"][3] - 11 / 12) < 1e-9
    assert by_label["Mức đánh giá trung bình (thang 5)"][2] == 4.58
    assert by_label["5 — Rất hài lòng"][2:4] == (8, 0.4)
    assert by_label["TỔNG (= hồ sơ đã nộp)"][2:4] == (20, 1)


def test_theo_don_vi_co_tong_cong():
    ws = load_workbook(io.BytesIO(build_ratings_workbook(_data())))["Theo đơn vị"]
    rows = _rows(ws)
    assert rows[0][:7] == ("STT", "Đơn vị", "Cấp", "Đã nộp", "Có đánh giá", "Mức TB", "Hài lòng")
    assert rows[1][:5] == (1, "HCC Xã A", "Xã", 10, 7) and rows[2][2] == "Phường"
    total = rows[3]
    assert total[0] == "TỔNG CỘNG" and total[3:5] == (20, 12) and total[6] == 1


def test_chon_nhieu_don_vi_chi_xuat_don_vi_da_chon():
    data = _data(selected_units=[{"unitId": "ua", "xa": "Xã A"}, {"unitId": "uc", "xa": "Xã C"}])
    rows = _rows(load_workbook(io.BytesIO(build_ratings_workbook(data)))["Theo đơn vị"])
    assert [r[1] for r in rows[1:-1]] == ["HCC Xã A"]


def test_tai_khoan_xa_chi_mot_sheet_va_ten_file():
    data = _data(can_view_units=False)
    assert load_workbook(io.BytesIO(build_ratings_workbook(data))).sheetnames == ["Tổng hợp"]
    assert ratings_filename(data).startswith("Danh gia cong dan - ")


@pytest.mark.asyncio
async def test_api_xuat_dung_du_lieu_cua_man_danh_gia(monkeypatch):
    seen = {}

    async def fake_ratings(**kw):
        seen.update(kw)
        return _data()

    monkeypatch.setattr(dashboard_router, "ratings", fake_ratings)
    res = await dashboard_router.ratings_export(user={"id": "u"}, dateFrom="2026-11-01", dateTo="2026-11-23",
                                                unit="ua,ub", province="Lai Châu")
    assert seen == {"user": {"id": "u"}, "dateFrom": "2026-11-01", "dateTo": "2026-11-23", "unit": "ua,ub",
                    "province": "Lai Châu"}
    assert "Danh%20gia%20cong%20dan" in res.headers["content-disposition"]


def test_nhan_pham_vi_khong_lap_chu_tinh():
    from app.dashboard.export import _scope_label

    assert _scope_label({"canViewUnits": True, "province": "Tỉnh Lai Châu"}) == "Toàn tỉnh Lai Châu"
    assert _scope_label({"canViewUnits": True, "province": "Thành phố Hà Nội"}) == "Toàn thành phố Hà Nội"
    assert _scope_label({"canViewUnits": True, "province": None}) == "Toàn hệ thống"
    assert _scope_label({"canViewUnits": True, "province": "Bộ Công an"}) == "Nhóm Bộ Công an"
    assert _scope_label({"canViewUnits": True, "province": "Lai Châu"}) == "Toàn tỉnh Lai Châu"


def test_moi_tab_chi_xuat_sheet_cua_tab():
    from app.dashboard.export import build_dashboard_workbook, export_filename

    data = {"scope": {"canViewUnits": True, "province": "Tỉnh Lai Châu"}, "range": {"from": "2026-11-01", "to": "2026-11-23"},
            "kpis": {"dossiers": 3}, "units": [{"unitId": "ua", "name": "HCC Xã A", "xa": "Xã A", "dossiers": 3}],
            "byProcedure": [{"label": "Kết hôn", "count": 3}], "byDay": [], "sources": {"handfree": True}}
    logs = [{"dossierId": "d1", "receivedAt": None, "submittedAt": None, "unitName": "Xã A", "procedureLabel": "Kết hôn",
             "rating": None, "experience": "autofill"}]
    sheets = {v: load_workbook(io.BytesIO(build_dashboard_workbook(data, logs, v))).sheetnames
              for v in ("overview", "units", "procedures", "logs")}
    assert sheets == {"overview": ["Tổng hợp"], "units": ["Theo đơn vị"], "procedures": ["Theo thủ tục"],
                      "logs": ["Nhật ký hồ sơ"]}
    # Web bản cũ không gửi view → đủ 4 sheet như trước.
    assert len(load_workbook(io.BytesIO(build_dashboard_workbook(data, logs))).sheetnames) == 4
    assert export_filename(data, "units").startswith("Thong ke ho so - Theo don vi - Toàn tỉnh Lai Châu - ")

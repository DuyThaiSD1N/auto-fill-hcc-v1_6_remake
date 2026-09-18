"""Đếm hồ sơ ĐÃ NỘP (cách đếm từ 14/9/2026).

Hai cam kết phải giữ bằng mọi giá:
  1. MỘT hồ sơ = MỘT, kể cả bấm nộp nhiều lần — với MỌI thủ tục trừ ba thủ tục chứng thực.
     Ngoại lệ chứng thực nằm ở test_chung_thuc_moi_lan_nop_la_mot_ho_so.py.
  2. Mốc ngày = lần nộp ĐẦU. `submit_clicked_at` bị ghi đè mỗi lần bấm nên nếu lấy nó thì một
     hồ sơ đã chốt của hôm qua nhảy sang hôm nay chỉ vì cán bộ bấm nộp lại.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.dossiers import stats as dossiers_stats

_FROM = datetime(2026, 9, 14, tzinfo=timezone.utc)
_TO = _FROM + timedelta(days=1)


class _Cursor:
    def __init__(self, rows):
        self._rows = rows

    async def to_list(self, length=None):
        return self._rows


class _Collection:
    def __init__(self, rows):
        self._rows = rows
        self.pipeline = None

    def aggregate(self, pipeline, **_kwargs):
        self.pipeline = pipeline
        return _Cursor(self._rows)


@pytest.fixture()
def dossiers(monkeypatch):
    collection = _Collection([])

    class _Db:
        dossiers = collection

    monkeypatch.setattr(dossiers_stats, "get_db", lambda: _Db())
    return collection


def _stages(pipeline, name):
    return [stage for stage in pipeline if name in stage]


async def test_dem_so_ho_so_khong_dem_so_lan_nop(dossiers):
    """Cộng theo `_count` — mỗi document tự khai mình đáng mấy hồ sơ (mặc định 1).

    Hai thứ vẫn bị cấm tuyệt đối:
      - `submit_count`: trường cộng dồn cả đời hồ sơ, lấy nó là lần nộp kỳ trước lọt vào kỳ này;
      - `$unwind submit_events`: biến MỌI thủ tục thành "mỗi lần nộp một hồ sơ", tức hồ sơ bấm
        nộp hụt rồi bấm lại bị đếm thành nhiều.
    """
    await dossiers_stats.submitted_counts(user_ids=["u1"], date_from=_FROM, date_to=_TO)
    group = _stages(dossiers.pipeline, "$group")[0]["$group"]
    assert group["count"] == {"$sum": "$_count"}
    assert "submit_count" not in str(dossiers.pipeline), "không được đếm theo số lần bấm nộp"
    assert not any("$unwind" in stage for stage in dossiers.pipeline), (
        "unwind submit_events là quay lại cách đếm mỗi lần nộp một hồ sơ cho MỌI thủ tục"
    )
    # Mặc định phải là 1: chỉ thủ tục nằm trong danh sách ngoại lệ mới được nhiều hơn.
    count_expr = _stages(dossiers.pipeline, "$set")[-1]["$set"]["_count"]
    assert count_expr["$cond"][2] == 1


async def test_moc_ngay_la_lan_nop_dau_tien(dossiers):
    await dossiers_stats.submitted_counts(user_ids=["u1"], date_from=_FROM, date_to=_TO)
    first = _stages(dossiers.pipeline, "$set")[0]["$set"]["_first_submit"]
    assert first == {"$ifNull": [{"$min": "$submit_events.at"}, "$submit_clicked_at"]}


async def test_chi_lay_ho_so_da_nop_va_dung_index(dossiers):
    """Chặn dưới đặt trên submit_clicked_at (có index) — chặn TRÊN thì không, kẻo loại oan
    hồ sơ nộp lần đầu trong khoảng rồi bấm lại sau khoảng."""
    await dossiers_stats.submitted_counts(
        user_ids=["u1", "u2"], date_from=_FROM, date_to=_TO, experience="handfree",
    )
    match = dossiers.pipeline[0]["$match"]
    assert match["submit_clicked_at"] == {"$ne": None, "$gte": _FROM}
    assert match["experience"] == "handfree"
    assert match["user_id"] == {"$in": ["u1", "u2"]}
    window = _stages(dossiers.pipeline, "$match")[1]["$match"]
    assert window == {"_first_submit": {"$gte": _FROM, "$lt": _TO}}


async def test_khong_co_don_vi_thi_khong_truy_van(dossiers):
    assert await dossiers_stats.submitted_counts(user_ids=[], date_from=_FROM, date_to=_TO) == []
    assert dossiers.pipeline is None


async def test_gom_theo_ngay_dung_mui_gio_viet_nam(dossiers):
    await dossiers_stats.submitted_daily_counts(user_ids=["u1"], date_from=_FROM, date_to=_TO)
    group = _stages(dossiers.pipeline, "$group")[0]["$group"]
    assert group["_id"]["day"]["$dateToString"]["timezone"] == "+07:00"
    assert group["_id"]["day"]["$dateToString"]["date"] == "$_first_submit"


async def test_doc_ket_qua_ra_dung_hop_dong(monkeypatch):
    rows = [{
        "_id": {"userId": "u1", "procedure": "chung-thuc-ban-sao"},
        "name": "Phường Tân Phong",
        "label": "Chứng thực bản sao",
        "count": 3,
    }]
    collection = _Collection(rows)

    class _Db:
        dossiers = collection

    monkeypatch.setattr(dossiers_stats, "get_db", lambda: _Db())
    assert await dossiers_stats.submitted_counts(user_ids=["u1"], date_from=_FROM, date_to=_TO) == [{
        "userId": "u1",
        "procedure": "chung-thuc-ban-sao",
        "label": "Chứng thực bản sao",
        "name": "Phường Tân Phong",
        "count": 3,
    }]


async def test_ngay_rong_bi_loai_khoi_bieu_do(monkeypatch):
    collection = _Collection([{"_id": {"userId": "u1", "day": None}, "count": 5}])

    class _Db:
        dossiers = collection

    monkeypatch.setattr(dossiers_stats, "get_db", lambda: _Db())
    assert await dossiers_stats.submitted_daily_counts(
        user_ids=["u1"], date_from=_FROM, date_to=_TO,
    ) == []

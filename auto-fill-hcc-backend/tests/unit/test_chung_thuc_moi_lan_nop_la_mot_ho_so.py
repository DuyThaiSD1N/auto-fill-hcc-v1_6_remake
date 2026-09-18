"""Chứng thực: MỖI LẦN NỘP là một hồ sơ. Thủ tục khác: một hồ sơ, dù bấm nộp mấy lần.

Cán bộ làm chứng thực thường nộp nhiều bản trong một phiên (tách tab hoặc không), mỗi lần nộp
cổng cấp một mã hồ sơ riêng. Đếm một là mất trắng phần lớn khối lượng của nhóm thủ tục đông
hồ sơ nhất.

Ranh giới phải giữ: ngoại lệ này CHỈ cho ba thủ tục chứng thực. Áp cho mọi thủ tục là hồ sơ
bấm nộp hụt rồi bấm lại bị đếm thành nhiều — sai kiểu thổi phồng, không ai phát hiện ra.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.dossiers import stats as dossiers_stats

_FROM = datetime(2026, 9, 16, tzinfo=timezone.utc)
_TO = _FROM + timedelta(days=1)


def _cond():
    """Nhánh $cond quyết định một document đáng mấy hồ sơ."""
    return dossiers_stats._dossier_count(_FROM, _TO)["$cond"]


def test_chi_ba_thu_tuc_chung_thuc_moi_duoc_dem_nhieu():
    """Danh sách này là RANH GIỚI của ngoại lệ — nới ra là mọi thủ tục bấm hụt đều bị đếm nhiều."""
    assert dossiers_stats._SUBMIT_IS_A_DOSSIER == (
        "chung-thuc-ban-sao", "chung-thuc-chu-ky", "chung-thuc-chu-ky-nguoi-dich-ctv",
    )
    assert _cond()[0] == {"$in": ["$procedure", list(dossiers_stats._SUBMIT_IS_A_DOSSIER)]}


def test_thu_tuc_khac_bam_nop_may_lan_cung_la_mot():
    """Nhánh else là 1 cứng: khai sinh/kết hôn… bấm nộp 4 lần vẫn đúng một hồ sơ."""
    assert _cond()[2] == 1


def test_dem_su_kien_TRONG_KHOANG_khong_dung_submit_count():
    """submit_count cộng dồn cả đời hồ sơ: lấy nó là lần nộp tháng trước cũng vào kỳ này."""
    many = _cond()[1]
    body = repr(many)
    assert "submit_count" not in body, "phải đếm submit_events lọc theo khoảng"
    assert "submit_events" in body
    # Mốc khoảng phải là ĐỐI TƯỢNG datetime thật, không phải chuỗi — so sánh trong Mongo.
    flat = body
    assert "datetime.datetime(2026, 9, 16, 0, 0" in flat, "phải kẹp đúng đầu khoảng"
    assert "$max" in body, "hồ sơ tách chưa nộp lần nào vẫn là 1"


@pytest.fixture()
def captured(monkeypatch):
    seen: dict = {}

    class _Cursor:
        async def to_list(self, length=None):
            return []

    class _Collection:
        def aggregate(self, pipeline, **_kwargs):
            seen["pipeline"] = pipeline
            return _Cursor()

    class _Db:
        dossiers = _Collection()

    monkeypatch.setattr(dossiers_stats, "get_db", lambda: _Db())
    return seen


async def test_ca_bang_tong_lan_bieu_do_theo_ngay_deu_ap_quy_tac(captured):
    """Cột theo ngày và KPI tổng phải cùng một cách đếm, không thì nhìn vào thấy vênh."""
    for call in (dossiers_stats.submitted_counts, dossiers_stats.submitted_daily_counts):
        await call(user_ids=["u1"], date_from=_FROM, date_to=_TO)
        pipeline = captured["pipeline"]
        assert any("_count" in (stage.get("$set") or {}) for stage in pipeline), call.__name__
        group = next(stage["$group"] for stage in pipeline if "$group" in stage)
        assert group["count"] == {"$sum": "$_count"}, call.__name__

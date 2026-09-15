"""Nhật ký hồ sơ lọc được "đã hoàn thành" — tức đã bấm nộp.

Từ 14/9/2026 thống kê chỉ đếm hồ sơ đã nộp. Không có bộ lọc này thì cán bộ nhìn KPI ra một
số, mở nhật ký ra thấy nhiều dòng hơn (vì có cả hồ sơ làm dở) và không cách nào đối chiếu.
"""
from datetime import datetime, timezone

import pytest

from app.dossiers import repo as dossiers_repo

_FROM = datetime(2026, 9, 14, tzinfo=timezone.utc)
_TO = datetime(2026, 9, 15, tzinfo=timezone.utc)


class _Cursor:
    def __aiter__(self):
        return self

    async def __anext__(self):
        raise StopAsyncIteration

    def sort(self, *_a, **_k):
        return self

    def skip(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self


class _Collection:
    def __init__(self):
        self.queries: list[dict] = []

    async def count_documents(self, query):
        self.queries.append(query)
        return 0

    def find(self, query, _projection=None):
        self.queries.append(query)
        return _Cursor()


@pytest.fixture()
def dossiers(monkeypatch):
    collection = _Collection()

    class _Db:
        dossiers = collection

    monkeypatch.setattr(dossiers_repo, "get_db", lambda: _Db())
    return collection


async def _list(**kwargs):
    return await dossiers_repo.list_for_dashboard(
        user_ids=["u1"], date_from=_FROM, date_to=_TO, **kwargs,
    )


async def test_mac_dinh_van_lay_ca_ho_so_lam_do(dossiers):
    """Không lọc thì giữ nguyên hành vi cũ — 'bao nhiêu hồ sơ bỏ dở' vẫn là thứ cần nhìn."""
    await _list()
    assert all("submit_clicked_at" not in query for query in dossiers.queries)


async def test_da_hoan_thanh_chi_lay_ho_so_da_bam_nop(dossiers):
    await _list(submitted=True)
    assert all(query["submit_clicked_at"] == {"$ne": None} for query in dossiers.queries)


async def test_lam_do_chi_lay_ho_so_chua_nop(dossiers):
    await _list(submitted=False)
    assert all(query["submit_clicked_at"] is None for query in dossiers.queries)


async def test_bo_loc_ap_cho_ca_dem_tong_va_danh_sach(dossiers):
    """Đếm tổng và lấy dòng phải dùng CÙNG một điều kiện, nếu không phân trang sẽ sai."""
    await _list(submitted=True)
    assert len(dossiers.queries) == 2
    assert dossiers.queries[0] == dossiers.queries[1]

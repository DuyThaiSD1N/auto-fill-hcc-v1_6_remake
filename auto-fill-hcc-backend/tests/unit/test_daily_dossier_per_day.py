"""Biểu đồ 'hồ sơ theo ngày' phải khử trùng hồ sơ TRONG TỪNG NGÀY (không theo 'ngày đầu trong
range') → con số 1 ngày (vd hôm nay) CỐ ĐỊNH ở mọi bộ lọc 7/30/tất cả, khớp số 'Hôm nay'."""
from app.traces.repo import _format_daily_dossier_counts


def _by_day(facets):
    return {row["date"]: row["count"] for row in _format_daily_dossier_counts(facets)}


def test_same_dossier_counts_each_day_independently():
    """Hồ sơ A hoạt động cả 07 lẫn 09 → đếm ở CẢ HAI ngày; ngày 09 độc lập việc có ngày 07 hay không
    (đây chính là điểm sửa: trước kia A bị gom về 07 nên 09 hụt khi mở rộng range)."""
    facets = {
        "nonSplitFileSets": [
            {"_id": {"userId": "u1", "procedure": "p1", "fileSet": ["a.pdf"], "day": "2026-09-09"}},
            {"_id": {"userId": "u1", "procedure": "p1", "fileSet": ["b.pdf"], "day": "2026-09-09"}},
            {"_id": {"userId": "u1", "procedure": "p1", "fileSet": ["a.pdf"], "day": "2026-09-07"}},
        ],
        "stemNonSplitFileSets": [],
        "splitDossiers": [],
    }
    assert _by_day(facets) == {"2026-09-07": 1, "2026-09-09": 2}


def test_overlapping_file_sets_same_day_merge_to_one():
    """{a} ⊂ {a,b} trong CÙNG ngày → 1 hồ sơ (giữ rule gộp chồng file set, nhưng chỉ trong ngày)."""
    facets = {
        "nonSplitFileSets": [
            {"_id": {"userId": "u1", "procedure": "p1", "fileSet": ["a.pdf"], "day": "2026-09-09"}},
            {"_id": {"userId": "u1", "procedure": "p1", "fileSet": ["a.pdf", "b.pdf"], "day": "2026-09-09"}},
        ],
        "stemNonSplitFileSets": [],
        "splitDossiers": [],
    }
    assert _by_day(facets) == {"2026-09-09": 1}


def test_empty_file_set_counts_each_occurrence():
    facets = {
        "nonSplitFileSets": [
            {"_id": {"userId": "u1", "procedure": "p1", "fileSet": [], "day": "2026-09-09"}},
        ],
        "stemNonSplitFileSets": [],
        "splitDossiers": [],
    }
    assert _by_day(facets) == {"2026-09-09": 1}


def test_split_dossiers_bucket_by_own_day():
    facets = {
        "nonSplitFileSets": [],
        "stemNonSplitFileSets": [],
        "splitDossiers": [
            {"_id": {"userId": "u1", "procedure": "p1", "dossierId": "d1", "day": "2026-09-09"}},
            {"_id": {"userId": "u1", "procedure": "p1", "dossierId": "d2", "day": "2026-09-09"}},
            {"_id": {"userId": "u1", "procedure": "p1", "dossierId": "d1", "day": "2026-09-08"}},
        ],
    }
    assert _by_day(facets) == {"2026-09-08": 1, "2026-09-09": 2}

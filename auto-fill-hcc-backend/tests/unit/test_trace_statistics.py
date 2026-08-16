from datetime import datetime, timezone

import pytest

from app.core.errors import AppError
from app.traces.metadata import build_attach_trace_metadata, count_distinct_attachment_sets
from app.traces.repo import _format_stats_facets, _stats_account_context, _stats_pipeline
from app.traces.router import _parse_stats_range
from scripts.export_thong_ke_lai_chau import _dem_ho_so


def _meta(name: str, digest: str) -> dict:
    return {"name": name, "type": "application/pdf", "role": "", "sha256": digest}


def test_signature_split_creates_one_dossier_per_primary_and_reuses_identity():
    plan = [
        {"fileIndex": 0, "fileName": "TLA.pdf", "componentName": "Tài liệu cần chứng thực"},
        {"fileIndex": 1, "fileName": "TLB.pdf", "componentName": "Tài liệu cần chứng thực 2"},
        {"fileIndex": 2, "fileName": "CCCD.pdf", "componentName": "Giấy tờ tùy thân"},
    ]

    attachments, dossier_ids = build_attach_trace_metadata(
        request_id="req_attach",
        session_id=None,
        procedure="chung-thuc-chu-ky",
        split=True,
        plan=plan,
        files_meta=[_meta("TLA.pdf", "a" * 64), _meta("TLB.pdf", "b" * 64), _meta("CCCD.pdf", "c" * 64)],
    )

    assert dossier_ids == ["req_attach:1", "req_attach:2"]
    assert [item["uses"] for item in attachments] == [1, 1, 2]


def test_copy_split_counts_cccd_as_its_own_dossier():
    plan = [
        {"fileIndex": 0, "fileName": "TLA.pdf", "componentName": "Bản chính"},
        {"fileIndex": 1, "fileName": "CCCD.pdf", "componentName": "Căn cước công dân"},
    ]

    attachments, dossier_ids = build_attach_trace_metadata(
        request_id="req_copy",
        session_id=None,
        procedure="chung-thuc-ban-sao",
        split=True,
        plan=plan,
        files_meta=[_meta("TLA.pdf", "a" * 64), _meta("CCCD.pdf", "c" * 64)],
    )

    assert dossier_ids == ["req_copy:1", "req_copy:2"]
    assert [item["uses"] for item in attachments] == [1, 1]


def test_non_split_attachment_reuses_process_session_as_dossier_id():
    attachments, dossier_ids = build_attach_trace_metadata(
        request_id="req_attach",
        session_id="req_process",
        procedure="khai-sinh",
        split=False,
        plan=[{"fileIndex": 0, "fileName": "A.pdf", "componentName": "Giấy tờ A"}],
        files_meta=[_meta("A.pdf", "a" * 64)],
    )

    assert dossier_ids == ["req_process"]
    assert attachments[0]["sha256"] == "a" * 64


def test_stats_date_only_uses_vietnam_half_open_day():
    date_from, date_to = _parse_stats_range("2026-08-11", "2026-08-11")

    assert date_from == datetime(2026, 8, 10, 17, tzinfo=timezone.utc)
    assert date_to == datetime(2026, 8, 11, 17, tzinfo=timezone.utc)


def test_stats_rejects_reversed_date_range():
    with pytest.raises(AppError) as exc:
        _parse_stats_range("2026-08-12", "2026-08-11")

    assert exc.value.error == "BAD_DATE_RANGE"


def test_stats_pipeline_has_no_trace_limit_and_uses_half_open_upper_bound():
    pipeline = _stats_pipeline({"created_at": {"$gte": "start", "$lt": "end"}})
    rendered = repr(pipeline)

    assert "'$limit'" not in rendered
    assert "'$facet'" in rendered
    assert "'$lt': 'end'" in rendered


def test_stats_official_scope_uses_current_commune_and_province_roles_only():
    accounts = [
        {"_id": "u-commune", "role": "commune"},
        {"_id": "u-province", "role": "province"},
        {"_id": "u-user", "role": "user"},
        {"_id": "u-admin", "role": "admin"},
        {"_id": "u-legacy"},
    ]

    roles, official_ids = _stats_account_context(accounts, "official")
    _, all_ids = _stats_account_context(accounts, "all")

    assert roles["u-legacy"] == "user"
    assert official_ids == ["u-commune", "u-province"]
    assert all_ids == ["u-commune", "u-province", "u-user", "u-admin", "u-legacy"]


def test_stats_rejects_unknown_scope_before_querying():
    with pytest.raises(ValueError):
        _stats_account_context([], "other")


def test_format_stats_separates_exact_and_estimated_dossiers():
    result = _format_stats_facets(
        {
            "buckets": [
                {
                    "_id": {"userId": "u1", "procedure": "p1"},
                    "name": "Song Liễu",
                    "label": "Thủ tục 1",
                    "count": 3,
                    "estimatedCount": 1,
                }
            ],
            "requests": [
                {
                    "_id": {"userId": "u1", "procedure": "p1"},
                    "requests": 2,
                    "estimatedRequests": 1,
                }
            ],
            "documents": [{"unique": 2, "uses": 5}],
        }
    )

    assert result["totalDossiers"] == 3
    assert result["exactDossiers"] == 2
    assert result["estimatedDossiers"] == 1
    assert result["dataQuality"] == "mixed"
    assert result["totalRequests"] == 2
    assert result["procedures"][0]["requests"] == 2
    assert result["uniqueDocuments"] == 2
    assert result["totalDocumentUses"] == 5
    assert result["reusedDocumentUses"] == 3


def test_old_dossier_criterion_groups_equal_and_subset_file_sets_transitively():
    sets = [
        frozenset({"a.pdf"}),
        frozenset({"a.pdf", "b.pdf"}),
        frozenset({"b.pdf"}),
        frozenset({"c.pdf"}),
        frozenset(),
        frozenset(),
    ]

    assert count_distinct_attachment_sets(sets) == 4


def test_export_deduplicates_same_files_but_keeps_request_count():
    exact = [
        {"request_id": "fill", "procedure": "p", "stats_version": 2, "dossier_ids": ["d1"]},
        {"request_id": "attach", "procedure": "p", "stats_version": 2, "dossier_ids": ["d1"]},
    ]
    legacy = [
        {"request_id": "old-1", "procedure": "p", "attachments": [{"name": "CCCD.pdf"}]},
        {"request_id": "old-2", "procedure": "p", "attachments": [{"name": "CCCD.pdf"}]},
    ]

    exact_result = _dem_ho_so(exact)["p"]
    legacy.extend([
        {"request_id": "old-3", "procedure": "p", "attachments": [{"name": "  cccd.PDF  "}]},
    ])
    legacy_result = _dem_ho_so(legacy)["p"]

    assert exact_result["count"] == 1
    assert exact_result["requests"] == 2
    assert legacy_result["count"] == 1
    assert legacy_result["requests"] == 3
    assert legacy_result["estimated"] == 1


def test_export_split_trace_counts_only_its_tabs():
    result = _dem_ho_so([
        {
            "request_id": "split-1",
            "procedure": "chung-thuc-ban-sao",
            "split": True,
            "stats_version": 2,
            "dossier_ids": ["split-1:1", "split-1:2"],
            "attachments": [{"name": "a.pdf"}, {"name": "b.pdf"}],
        }
    ])["chung-thuc-ban-sao"]

    assert result["count"] == 2
    assert result["requests"] == 1


def test_stats_pipeline_groups_non_split_by_normalized_file_set():
    rendered = repr(_stats_pipeline({}))

    assert "'nonSplitFileSets'" in rendered
    assert "'_stats_file_set'" in rendered
    assert "'$regexFindAll'" in rendered
    assert "'splitBuckets'" in rendered


def test_stats_three_retries_with_same_files_are_one_dossier_and_three_requests():
    result = _format_stats_facets(
        {
            "nonSplitFileSets": [
                {
                    "_id": {
                        "userId": "phuong-doan-ket",
                        "procedure": "khai-tu",
                        "fileSet": ["cccd.pdf", "to khai.pdf"],
                        "emptyId": None,
                    },
                    "name": "Phường Đoàn Kết",
                    "label": "Thủ tục đăng ký khai tử",
                    "requests": 3,
                    "estimated": 0,
                }
            ],
            "requests": [
                {
                    "_id": {"userId": "phuong-doan-ket", "procedure": "khai-tu"},
                    "requests": 3,
                    "estimatedRequests": 0,
                }
            ],
            "documents": [],
        }
    )

    assert result["totalDossiers"] == 1
    assert result["totalRequests"] == 3
    assert result["wards"][0]["procedures"][0]["count"] == 1
    assert result["wards"][0]["procedures"][0]["requests"] == 3

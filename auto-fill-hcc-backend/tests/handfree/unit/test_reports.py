from datetime import datetime, timezone

import pytest

from app.core.errors import AppError
from app.reports.schemas import ExcelExportRequest
from app.reports.service import build_options, select_accounts
from app.traces.date_range import parse_stats_range


def _account(
    account_id: str,
    username: str,
    *,
    xa: str,
    tinh: str,
    name: str | None = None,
    role: str = "commune",
) -> dict:
    return {
        "_id": account_id,
        "username": username,
        "name": name,
        "xa": xa,
        "tinh": tinh,
        "role": role,
    }


def test_stats_range_uses_complete_vietnam_days():
    start, end = parse_stats_range("2026-08-11", "2026-08-11")
    assert start == datetime(2026, 8, 10, 17, tzinfo=timezone.utc)
    assert end == datetime(2026, 8, 11, 17, tzinfo=timezone.utc)


def test_report_options_merge_short_and_official_province_names():
    result = build_options([
        _account("u1", "tanphong", xa="Tân Phong", tinh="Lai Châu"),
        _account("u2", "taleng", xa="Tả Lèng", tinh="Tỉnh Lai Châu"),
        _account("u3", "tester", xa="Tân Phong", tinh="Lai Châu", role="user"),
    ])
    assert result["provinces"] == [{
        "value": "Tỉnh Lai Châu",
        "label": "Tỉnh Lai Châu",
        "accountCount": 3,
        "officialAccountCount": 2,
    }]


def test_official_province_selection_excludes_admin_and_regular_users():
    accounts = [
        _account("u1", "commune", xa="Tân Phong", tinh="Lai Châu", role="commune"),
        _account("u2", "province", xa="Tân Phong", tinh="Lai Châu", role="province"),
        _account("u3", "tester", xa="Tân Phong", tinh="Lai Châu", role="user"),
        _account("u4", "admin", xa="Tân Phong", tinh="Lai Châu", role="admin"),
    ]
    body = ExcelExportRequest(
        dateFrom="2026-08-11",
        dateTo="2026-08-11",
        selectionMode="province",
        province="Tỉnh Lai Châu",
        officialOnly=True,
    )
    assert [item["_id"] for item in select_accounts(accounts, body)] == ["u1", "u2"]


def test_missing_named_account_is_rejected():
    body = ExcelExportRequest(
        dateFrom="2026-08-11",
        dateTo="2026-08-11",
        selectionMode="accounts",
        accountIds=["deleted"],
    )
    with pytest.raises(AppError) as exc:
        select_accounts([], body)
    assert exc.value.error == "REPORT_ACCOUNT_NOT_FOUND"

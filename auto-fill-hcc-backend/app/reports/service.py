"""Nghiệp vụ chọn tài khoản và kết xuất báo cáo Excel."""
import asyncio
import re
import unicodedata
from datetime import datetime

from app.core.errors import AppError
from app.db.mongo import get_db
from app.locations.catalog import canonical_location
from app.reports.excel import build_daily_excel, build_excel
from app.reports.handfree_client import fetch_handfree_daily_stats, fetch_handfree_stats
from app.reports.schemas import ExcelExportRequest
from app.stats import cutover
from app.traces import repo as traces_repo
from app.traces.date_range import parse_stats_range
from app.users.roles import NOT_DELETED, is_official_account_role, normalized_role


MAX_EXPORT_ACCOUNTS = 200
_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_PROVINCE_PREFIX = re.compile(r"^(?:tỉnh|thành phố)\s+", re.IGNORECASE)


def _fold(value: str) -> str:
    value = str(value or "").replace("Đ", "D").replace("đ", "d")
    return " ".join(
        "".join(
            char for char in unicodedata.normalize("NFD", value)
            if unicodedata.category(char) != "Mn"
        ).casefold().split()
    )


def _province_name(value: str | None) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        canonical, _ = canonical_location(raw, None)
        return canonical or raw
    except AppError:
        # Không làm biến mất tài khoản legacy có tỉnh chưa thuộc catalog mới.
        return raw


def _public_account(account: dict) -> dict:
    return {
        "id": str(account["_id"]),
        "username": account.get("username") or "",
        "name": account.get("name"),
        "xa": account.get("xa"),
        "tinh": _province_name(account.get("tinh")),
        "role": normalized_role(account.get("role")),
    }


async def _all_accounts() -> list[dict]:
    projection = {"username": 1, "name": 1, "xa": 1, "tinh": 1, "role": 1}
    cursor = get_db().users.find(NOT_DELETED, projection).sort("username", 1)
    return [account async for account in cursor]


def build_options(accounts: list[dict]) -> dict:
    """Province facet được suy ra từ chính tài khoản, không từ toàn bộ catalog hành chính."""
    public_accounts = [_public_account(account) for account in accounts]
    provinces: dict[str, dict] = {}
    for account in public_accounts:
        province = account.get("tinh")
        if not province:
            continue
        key = _fold(province)
        item = provinces.setdefault(key, {
            "value": province,
            "label": province,
            "accountCount": 0,
            "officialAccountCount": 0,
        })
        item["accountCount"] += 1
        if is_official_account_role(account.get("role")):
            item["officialAccountCount"] += 1
    return {
        "provinces": sorted(provinces.values(), key=lambda item: _fold(item["label"])),
        "accounts": public_accounts,
    }


async def options() -> dict:
    result = build_options(await _all_accounts())
    # Hai trải nghiệm dùng chung Mongo; không còn phụ thuộc một backend báo cáo từ xa.
    result["handfreeEnabled"] = True
    return result


def select_accounts(accounts: list[dict], body: ExcelExportRequest) -> list[dict]:
    official_only = body.officialOnly or body.reportLayout == "daily_summary"
    if body.selectionMode == "province":
        province_key = _fold(_province_name(body.province) or "")
        province_accounts = [
            account for account in accounts
            if _fold(_province_name(account.get("tinh")) or "") == province_key
        ]
        if not province_accounts:
            raise AppError(
                "REPORT_PROVINCE_EMPTY",
                "Tỉnh/thành đã chọn hiện không có tài khoản nào.",
                400,
            )
        selected = (
            [
                account for account in province_accounts
                if is_official_account_role(account.get("role"))
            ]
            if official_only
            else province_accounts
        )
        if official_only and not selected:
            raise AppError(
                "REPORT_PROVINCE_OFFICIAL_EMPTY",
                "Tỉnh/thành đã chọn chưa có tài khoản hành chính công.",
                400,
            )
    else:
        by_id = {str(account["_id"]): account for account in accounts}
        missing = [account_id for account_id in body.accountIds if account_id not in by_id]
        if missing:
            raise AppError(
                "REPORT_ACCOUNT_NOT_FOUND",
                "Một hoặc nhiều tài khoản đã chọn không còn tồn tại. Vui lòng tải lại danh sách.",
                400,
            )
        selected = [by_id[account_id] for account_id in body.accountIds]
        if body.reportLayout == "daily_summary":
            non_official = [
                account for account in selected
                if not is_official_account_role(account.get("role"))
            ]
            if non_official:
                raise AppError(
                    "REPORT_DAILY_OFFICIAL_ONLY",
                    "Báo cáo tổng hợp theo ngày chỉ hỗ trợ tài khoản HCC xã hoặc HCC tỉnh.",
                    400,
                )

    if len(selected) > MAX_EXPORT_ACCOUNTS:
        raise AppError(
            "REPORT_TOO_MANY_ACCOUNTS",
            f"Mỗi file chỉ hỗ trợ tối đa {MAX_EXPORT_ACCOUNTS} tài khoản.",
            400,
        )
    return selected


def _filename_part(value: str, fallback: str) -> str:
    cleaned = _INVALID_FILENAME_CHARS.sub("-", " ".join(str(value or "").split()))
    return cleaned.strip(" .") or fallback


def _filename_scope(body: ExcelExportRequest, accounts: list[dict]) -> str:
    if body.selectionMode == "province":
        province = _province_name(body.province) or "Tỉnh thành"
        return _filename_part(_PROVINCE_PREFIX.sub("", province).strip(), "Tỉnh thành")
    if len(accounts) == 1:
        account = accounts[0]
        return _filename_part(
            account.get("name") or account.get("username") or "Tài khoản",
            "Tài khoản",
        )
    return f"{len(accounts)} tài khoản"


def _filename_date(value: str) -> str:
    return datetime.strptime(value[:10], "%Y-%m-%d").strftime("%d-%m-%Y")


def _filename(body: ExcelExportRequest, accounts: list[dict]) -> str:
    scope = _filename_scope(body, accounts)
    date_from = _filename_date(body.dateFrom)
    date_to = _filename_date(body.dateTo)
    if body.reportLayout == "daily_summary":
        report_name = "Tổng hợp hồ sơ" if date_from == date_to else "Tổng hợp hồ sơ theo ngày"
    else:
        report_name = "Báo cáo hồ sơ tổng hợp" if body.includeHandfree else "Báo cáo hồ sơ"
    if date_from == date_to:
        period = f"ngày {date_from}"
    else:
        period = f"từ {date_from} đến {date_to}"
    return f"[{scope}] {report_name} {period}.xlsx"


async def export_excel(body: ExcelExportRequest) -> tuple[bytes, str]:
    date_from, date_to = parse_stats_range(body.dateFrom, body.dateTo)
    if not date_from or not date_to:
        raise AppError("REPORT_DATE_REQUIRED", "Vui lòng nhập đầy đủ từ ngày và đến ngày.", 400)
    accounts = select_accounts(await _all_accounts(), body)
    account_ids = [str(account["_id"]) for account in accounts]
    if body.reportLayout == "daily_summary":
        daily_counts, handfree_daily_stats = await asyncio.gather(
            cutover.daily_dossier_counts(
                user_ids=account_ids,
                date_from=date_from,
                date_to=date_to,
                experience="autofill",
            ),
            # Tab Tổng hợp luôn là tổng hai hệ thống; cờ includeHandfree chỉ còn
            # dùng để phân biệt hai nút ở báo cáo Chi tiết cũ.
            fetch_handfree_daily_stats(accounts, body),
        )
        data = await asyncio.to_thread(
            build_daily_excel,
            accounts=accounts,
            daily_counts=daily_counts,
            handfree_daily_stats=handfree_daily_stats,
            date_from=date_from,
            date_to=date_to,
        )
        return data, _filename(body, accounts)

    local_stats_task = cutover.dossier_stats(
        user_ids=account_ids,
        date_from=date_from,
        date_to=date_to,
        experience="autofill",
    )
    if body.includeHandfree:
        stats, handfree_stats = await asyncio.gather(
            local_stats_task,
            fetch_handfree_stats(accounts, body),
        )
    else:
        stats = await local_stats_task
        handfree_stats = None
    data = await asyncio.to_thread(
        build_excel,
        accounts=accounts,
        stats=stats,
        handfree_stats=handfree_stats,
        date_from=date_from,
        date_to=date_to,
    )
    filename = _filename(body, accounts)
    return data, filename

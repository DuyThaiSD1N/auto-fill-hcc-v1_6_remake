"""Client server-to-server lấy thống kê đã tổng hợp từ Handfree."""
import hashlib
import hmac
import json
import time
import uuid
from typing import Literal

import httpx

from app.config import settings
from app.core.errors import AppError
from app.reports.integration import province_name, unit_key
from app.reports.schemas import ExcelExportRequest


def _signature(timestamp: str, body: bytes) -> str:
    message = timestamp.encode("utf-8") + b"." + body
    return hmac.new(
        settings.handfree_report_service_secret.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()


def _units(accounts: list[dict]) -> list[dict]:
    units: dict[str, dict] = {}
    for account in accounts:
        province = province_name(account.get("tinh"))
        ward = str(account.get("xa") or "").strip()
        if not province or not ward:
            # Tài khoản cấp tỉnh/legacy không có đủ khóa ghép vẫn phải được xuất.
            # Workbook sẽ giữ số Auto Fill và điền 0 ở cột Handfree cho tài khoản này.
            continue
        key = unit_key(province, ward)
        units.setdefault(key, {"unitKey": key, "province": province, "ward": ward})
    return list(units.values())


async def _post_handfree(path: str, payload: dict) -> dict:
    base_url = settings.handfree_report_base_url.strip().rstrip("/")
    if not base_url or not settings.handfree_report_service_secret:
        raise AppError(
            "REPORT_HANDFREE_NOT_CONFIGURED",
            "Chức năng tổng hợp Handfree chưa được cấu hình trên backend Auto Fill.",
            503,
        )
    raw_body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    timestamp = str(int(time.time()))
    headers = {
        "Content-Type": "application/json",
        "X-Report-Client": settings.handfree_report_client,
        "X-Report-Timestamp": timestamp,
        "X-Report-Signature": _signature(timestamp, raw_body),
    }
    timeout = httpx.Timeout(settings.handfree_report_timeout_seconds)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}{path}",
                content=raw_body,
                headers=headers,
            )
    except httpx.TimeoutException as exc:
        raise AppError(
            "REPORT_HANDFREE_TIMEOUT",
            "Handfree phản hồi quá thời gian; chưa thể tải số liệu.",
            504,
        ) from exc
    except httpx.RequestError as exc:
        raise AppError(
            "REPORT_HANDFREE_UNAVAILABLE",
            "Không kết nối được backend Handfree; chưa thể tải số liệu.",
            502,
        ) from exc

    if response.status_code != 200:
        raise AppError(
            "REPORT_HANDFREE_FAILED",
            "Backend Handfree từ chối hoặc không xử lý được yêu cầu tổng hợp.",
            502,
        )
    try:
        result = response.json()
    except ValueError as exc:
        raise AppError(
            "REPORT_HANDFREE_INVALID_RESPONSE",
            "Backend Handfree trả dữ liệu không hợp lệ.",
            502,
        ) from exc
    if not isinstance(result, dict) or result.get("source") != "handfree":
        raise AppError(
            "REPORT_HANDFREE_INVALID_RESPONSE",
            "Backend Handfree trả dữ liệu không đúng hợp đồng báo cáo.",
            502,
        )
    return result


async def fetch_handfree_stats(accounts: list[dict], body: ExcelExportRequest) -> dict:
    units = _units(accounts)
    if not units:
        # API nội bộ Handfree yêu cầu ít nhất một đơn vị. Không có đơn vị ghép
        # được không phải lỗi: báo cáo phía Auto Fill vẫn phải xuất bình thường.
        return {"source": "handfree", "units": []}

    result = await _post_handfree("/internal/v1/reports/stats", {
        "requestId": f"report_{uuid.uuid4().hex}",
        "dateFrom": body.dateFrom,
        "dateTo": body.dateTo,
        # Hai Mongo không dùng chung user_id; ghép theo tên tỉnh + xã/phường đã chuẩn hóa.
        "units": units,
    })
    if not isinstance(result.get("units"), list):
        raise AppError(
            "REPORT_HANDFREE_INVALID_RESPONSE",
            "Backend Handfree trả dữ liệu không đúng hợp đồng báo cáo.",
            502,
        )
    return result


async def fetch_handfree_dashboard_stats(
    *,
    scope: Literal["all", "official"],
    date_from: str | None,
    date_to: str | None,
) -> dict:
    result = await _post_handfree("/internal/v1/reports/dashboard-stats", {
        "requestId": f"dashboard_{uuid.uuid4().hex}",
        "dateFrom": date_from,
        "dateTo": date_to,
        "scope": scope,
    })
    stats = result.get("stats")
    if not isinstance(stats, dict) or not isinstance(stats.get("wards"), list):
        raise AppError(
            "REPORT_HANDFREE_INVALID_RESPONSE",
            "Backend Handfree trả dữ liệu không đúng hợp đồng thống kê.",
            502,
        )
    return stats

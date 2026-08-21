import io
import hashlib
import hmac
import json

import httpx
import pytest
from openpyxl import load_workbook

from app.config import settings
from app.reports.excel import build_excel
from app.reports import handfree_client
from app.reports.integration import unit_key
from app.reports.schemas import ExcelExportRequest
from app.traces.date_range import parse_stats_range


def test_combined_excel_unions_procedures_zero_fills_and_totals():
    date_from, date_to = parse_stats_range("2026-08-18", "2026-08-18")
    account = {
        "_id": "auto-1",
        "username": "hccnghiahung",
        "name": "HCC Xã Nghĩa Hưng",
        "xa": "Xã Nghĩa Hưng",
        "tinh": "Tỉnh Ninh Bình",
        "role": "commune",
    }
    content = build_excel(
        accounts=[account],
        stats={"wards": [{
            "userId": "auto-1",
            "procedures": [
                {"key": "chung-thuc-ban-sao", "count": 7},
                {"key": "khai-tu", "count": 1},
            ],
        }]},
        handfree_stats={"source": "handfree", "units": [{
            "unitKey": unit_key("Tỉnh Ninh Bình", "Xã Nghĩa Hưng"),
            "procedures": [
                {
                    "canonicalProcedureId": "tthc:2.000815",
                    "procedureKey": "chung-thuc-ban-sao",
                    "procedureCode": "2.000815",
                    "label": "Chứng thực bản sao",
                    "count": 31,
                },
                {
                    "canonicalProcedureId": "tthc:1.000894",
                    "procedureKey": "ket-hon",
                    "procedureCode": "1.000894",
                    "label": "Thủ tục đăng ký kết hôn",
                    "count": 1,
                },
            ],
        }]},
        date_from=date_from,
        date_to=date_to,
    )
    sheet = load_workbook(io.BytesIO(content)).active

    assert sheet["F7"].value == "Số lượng hồ sơ đã tiếp nhận (bản chưa tích hợp giọng nói)"
    assert sheet["G7"].value == "Số lượng hồ sơ đã tiếp nhận (bản đã tích hợp giọng nói)"
    assert sheet["H7"].value == "TỔNG SỐ HỒ SƠ"
    rows = {sheet.cell(row=row, column=2).value: row for row in range(8, 11)}
    assert [sheet.cell(rows["2.000815"], column=column).value for column in (6, 7, 8)] == [7, 31, 38]
    assert [sheet.cell(rows["1.000656"], column=column).value for column in (6, 7, 8)] == [1, 0, 1]
    assert [sheet.cell(rows["1.000894"], column=column).value for column in (6, 7, 8)] == [0, 1, 1]
    assert [sheet.cell(row=11, column=column).value for column in (6, 7, 8)] == [8, 32, 40]


@pytest.mark.asyncio
async def test_handfree_client_sends_canonical_units_and_hmac(monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, *, timeout):
            captured["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, *, content, headers):
            captured.update({"url": url, "content": content, "headers": headers})
            return httpx.Response(200, json={"source": "handfree", "units": []})

    monkeypatch.setattr(settings, "handfree_report_base_url", "https://handfree.example/")
    monkeypatch.setattr(settings, "handfree_report_service_secret", "shared-secret")
    monkeypatch.setattr(handfree_client.httpx, "AsyncClient", FakeClient)
    body = ExcelExportRequest(
        dateFrom="2026-08-18",
        dateTo="2026-08-18",
        selectionMode="accounts",
        accountIds=["auto-1"],
        includeHandfree=True,
    )

    result = await handfree_client.fetch_handfree_stats([{
        "_id": "auto-1",
        "xa": "Xã Nghĩa Hưng",
        "tinh": "Ninh Bình",
    }], body)

    payload = json.loads(captured["content"])
    assert result == {"source": "handfree", "units": []}
    assert captured["url"] == "https://handfree.example/internal/v1/reports/stats"
    assert payload["units"] == [{
        "unitKey": "tinh ninh binh::xa nghia hung",
        "province": "Tỉnh Ninh Bình",
        "ward": "Xã Nghĩa Hưng",
    }]
    assert payload["officialOnly"] is True
    timestamp = captured["headers"]["X-Report-Timestamp"]
    expected = hmac.new(
        b"shared-secret",
        timestamp.encode() + b"." + captured["content"],
        hashlib.sha256,
    ).hexdigest()
    assert captured["headers"]["X-Report-Signature"] == expected

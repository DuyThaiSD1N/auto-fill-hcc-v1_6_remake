import re
import unicodedata
from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.core.deps import require_admin
from app.reports import service
from app.reports.schemas import ExcelExportRequest


router = APIRouter(prefix="/api/v1/reports", tags=["reports"])
_XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _ascii_filename(filename: str) -> str:
    raw = str(filename or "").replace("Đ", "D").replace("đ", "d")
    folded = "".join(
        char
        for char in unicodedata.normalize("NFD", raw)
        if unicodedata.category(char) != "Mn"
    )
    cleaned = re.sub(r'[^A-Za-z0-9 ._\-\[\]()]', "-", folded)
    return " ".join(cleaned.split()).strip(" .") or "Bao cao ho so.xlsx"


def _content_disposition(filename: str) -> str:
    # filename* mang tên UTF-8 chuẩn RFC 5987; filename là phương án dự phòng ASCII.
    safe_filename = str(filename or "").replace("\r", "").replace("\n", "")
    encoded = quote(safe_filename, safe="")
    ascii_filename = _ascii_filename(safe_filename)
    return (
        f'attachment; filename="{ascii_filename}"; '
        f"filename*=UTF-8''{encoded}"
    )


@router.get("/options")
async def report_options(_: dict = Depends(require_admin)):
    return await service.options()


@router.post("/excel")
async def export_excel(body: ExcelExportRequest, _: dict = Depends(require_admin)):
    data, filename = await service.export_excel(body)
    return Response(
        content=data,
        media_type=_XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": _content_disposition(filename)},
    )

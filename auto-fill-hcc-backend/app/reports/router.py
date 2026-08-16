from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.core.deps import require_admin
from app.reports import service
from app.reports.schemas import ExcelExportRequest


router = APIRouter(prefix="/api/v1/reports", tags=["reports"])
_XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/options")
async def report_options(_: dict = Depends(require_admin)):
    return await service.options()


@router.post("/excel")
async def export_excel(body: ExcelExportRequest, _: dict = Depends(require_admin)):
    data, filename = await service.export_excel(body)
    return Response(
        content=data,
        media_type=_XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

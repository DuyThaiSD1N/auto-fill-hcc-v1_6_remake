from fastapi import APIRouter, Depends

from app.core.deps import require_auth
from app.procedures.registry import public_list

router = APIRouter(prefix="/api/v1", tags=["procedures"])


@router.get("/procedures")
async def procedures(_: dict = Depends(require_auth)):
    return {"procedures": public_list()}

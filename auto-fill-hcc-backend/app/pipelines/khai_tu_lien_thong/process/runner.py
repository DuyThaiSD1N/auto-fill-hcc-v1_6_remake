"""Compact agent process pipeline for liên thông khai tử."""

from app.pipelines.khai_tu.process.runner import extract
from app.pipelines.khai_tu_lien_thong.process import mapper


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await extract(files_by_role, options)
    res["fields"] = mapper.enrich(
        res["fields"],
        options,
        reasoning_context=res.get("reasoning_context") or "",
        ocr_text=res.get("ocr_text") or "",
    )
    return res

"""Compact agent process pipeline for khai sinh liên thông."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.khai_sinh_lien_thong.process import mapper
from app.pipelines.khai_sinh_lien_thong.process.prompt import EXTRA_RULES
from app.pipelines.khai_sinh_lien_thong.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
    )
    res["fields"] = mapper.enrich(res["fields"])

    # Rà soát bbox (Kiểu A): chỉ chạy khi router bật cờ _review (thủ tục có "review": True).
    if (options or {}).get("_review"):
        from app.review import capture
        from app.pipelines.khai_sinh_lien_thong.process.schema import (
            REVIEW_FIELDS,
            REVIEW_NAME_GROUPS,
        )
        try:
            cap = await capture.capture(
                files_by_role, res["fields"],
                review_names=REVIEW_FIELDS, name_groups=REVIEW_NAME_GROUPS,
            )
            if cap:
                res["_review"] = cap
        except Exception as e:  # noqa: BLE001
            res.setdefault("errors", []).append(f"review: {e}")
    return res

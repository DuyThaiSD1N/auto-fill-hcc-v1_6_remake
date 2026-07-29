"""Compact agent pipeline for "Cấp bản sao trích lục Giấy khai sinh"."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.trich_luc.process import mapper
from app.pipelines.trich_luc.process.prompt import EXTRA_RULES
from app.pipelines.trich_luc.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


def _requester_hint(options: dict) -> str:
    """Mỏ neo người yêu cầu cổng đã điền sẵn (VNeID) → giúp LLM chọn ĐÚNG CCCD người yêu cầu
    khi upload nhiều CCCD (vd mẹ đi làm bản sao khai sinh cho con: có cả CCCD mẹ lẫn con)."""
    ctx = (options or {}).get("formContext") or {}
    name = str(ctx.get("applicantFullname") or "").strip()
    idnum = str(ctx.get("applicantIdentityNumber") or "").strip()
    if not name and not idnum:
        return ""
    return (
        "\n\n<requester_context>\n"
        f'NGƯỜI YÊU CẦU đã đăng nhập (cổng điền sẵn từ VNeID): họ tên="{name}", số định danh="{idnum}".\n'
        "Cccd_* CHỈ lấy từ CCCD TRÙNG tên/số định danh này. CCCD KHÔNG trùng = của người khác\n"
        "(chủ thể hộ tịch/thân nhân) → KHÔNG đưa vào Cccd_*.\n"
        "</requester_context>"
    )


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES + _requester_hint(options),
    )
    res["fields"] = mapper.enrich(res["fields"], options)

    # Rà soát bbox (Kiểu A): chỉ chạy khi router bật cờ _review (thủ tục có "review": True).
    if (options or {}).get("_review"):
        from app.review import capture
        from app.pipelines.trich_luc.process.schema import REVIEW_FIELDS
        try:
            cap = await capture.capture(files_by_role, res["fields"], review_names=REVIEW_FIELDS)
            if cap:
                res["_review"] = cap
        except Exception as e:  # noqa: BLE001
            res.setdefault("errors", []).append(f"review: {e}")
    return res

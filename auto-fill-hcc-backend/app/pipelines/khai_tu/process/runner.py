"""Compact agent pipeline for "Đăng ký khai tử"."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.khai_tu.process import mapper
from app.pipelines.khai_tu.process.prompt import EXTRA_RULES
from app.pipelines.khai_tu.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


def _requester_hint(options: dict) -> str:
    """Mỏ neo người yêu cầu cổng đã điền sẵn (VNeID) → giúp LLM tách CCCD người yêu cầu vs người mất."""
    ctx = (options or {}).get("formContext") or {}
    name = str(ctx.get("applicantFullname") or "").strip()
    idnum = str(ctx.get("applicantIdentityNumber") or "").strip()
    if not name and not idnum:
        return ""
    return (
        "\n\n<requester_context>\n"
        f'NGƯỜI YÊU CẦU đã đăng nhập (cổng điền sẵn từ VNeID): họ tên="{name}", số định danh="{idnum}".\n'
        "Cccd_* CHỈ lấy từ CCCD TRÙNG tên/số định danh này. Một CCCD KHÔNG trùng = CCCD của NGƯỜI ĐÃ MẤT\n"
        "→ trích danh tính người đó vào nhóm Gbt_* (Gbt_HoTenNguoiMat, Gbt_NgaySinhNguoiMat đủ dd/mm/yyyy,\n"
        "Gbt_GioiTinhNguoiMat, Gbt_DanTocNguoiMat, Gbt_QuocTichNguoiMat, Gbt_SoDinhDanhNguoiMat,\n"
        "Gbt_NgayCapDDNguoiMat, Gbt_NoiCapDDNguoiMat, Gbt_NoiCuTruNguoiMat), KHÔNG để vào Cccd_*.\n"
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
        from app.pipelines.khai_tu.process.schema import REVIEW_FIELDS
        try:
            cap = await capture.capture(files_by_role, res["fields"], review_names=REVIEW_FIELDS)
            if cap:
                res["_review"] = cap
        except Exception as e:  # noqa: BLE001
            res.setdefault("errors", []).append(f"review: {e}")
    return res

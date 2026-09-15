"""Compact agent pipeline "[Bắc Ninh] Điền thông tin tài khoản".

MỘT người = CHỦ TÀI KHOẢN đã đăng nhập VNeID. context_builder neo Họ tên + Số định danh (cổng prefill sẵn,
FE đọc từ ô trên trang) để LLM chọn ĐÚNG người trong giấy tờ (CCCD/tờ khai/GCN có nhiều người)."""

import re
import unicodedata

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dien_thong_tin_tai_khoan_bac_ninh.process import mapper
from app.pipelines.dien_thong_tin_tai_khoan_bac_ninh.process.prompt import EXTRA_RULES
from app.pipelines.dien_thong_tin_tai_khoan_bac_ninh.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


def _norm_text(value: str) -> str:
    text = str(value or "").replace("Đ", "D").replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^0-9a-zA-Z]+", " ", text).strip().lower())


async def _account_context(documents: list[dict], options: dict) -> str:
    """Neo CHỦ TÀI KHOẢN (Họ tên + Số định danh cổng prefill vào form) để LLM chọn đúng người."""
    ctx = (options or {}).get("formContext") or {}
    raw_name = ctx.get("applicantFullname") or ctx.get("fullname") or ctx.get("ownerFullname") or ""
    identity = re.sub(
        r"\D+", "",
        str(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber") or ctx.get("ownerIdentityNumber") or ""),
    )[:20]
    if not raw_name and not identity:
        return ""
    anchor = f'Họ tên "{raw_name}"' + (f', Số định danh "{identity}"' if identity else "")
    return (
        "\n\n<account_context>\n"
        f"CHỦ TÀI KHOẢN đã đăng nhập VNeID là: {anchor}. CHỈ trích thông tin của ĐÚNG người này. "
        "Nếu giấy tờ có nhiều người (đồng sở hữu GCN, người liên quan trong tờ khai), lấy người khớp Số "
        "định danh (ưu tiên) hoặc Họ tên; KHÔNG lấy nhân thân người khác.\n"
        "</account_context>"
    )


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        context_builder=_account_context,
    )
    res["fields"] = mapper.enrich(res["fields"], options)
    return res

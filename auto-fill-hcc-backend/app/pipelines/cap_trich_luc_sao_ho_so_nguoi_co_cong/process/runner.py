"""Compact agent process pipeline cho "Cấp trích lục hoặc sao hồ sơ người có công với cách mạng" (1.010828)."""

import re

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_trich_luc_sao_ho_so_nguoi_co_cong.process import mapper
from app.pipelines.cap_trich_luc_sao_ho_so_nguoi_co_cong.process.prompt import EXTRA_RULES
from app.pipelines.cap_trich_luc_sao_ho_so_nguoi_co_cong.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)
from app.pipelines.di_chuyen_ho_so_nguoi_huong_tro_cap.process.runner import _matches_anchor, _norm_text

_NO_SUBMITTER = (
    '\n\n<nguoi_nop_context result="{result}">\n{reason} Không trả NguoiNop_*; trích Don_* và Person1_* bình '
    "thường.\n</nguoi_nop_context>"
)


async def _submitter_context(documents: list[dict], options: dict) -> str:
    """Neo NGƯỜI NỘP (người đăng nhập VNeID, cổng đổ họ tên + CCCD vào Phần I) để LLM tách khỏi người làm đơn.

    Nộp thay hay kèm cả CCCD của người nộp; không có mốc, LLM dễ lấy thẻ đó làm Person1_*. Bật "Lấy người nộp
    theo tờ khai" thì người nộp = người làm đơn → bỏ mốc.
    """
    if str((options or {}).get("submitterMode") or "") == "owner_as_submitter":
        return _NO_SUBMITTER.format(
            result="owner_as_submitter", reason="Chế độ người nộp = người làm đơn: không dùng tài khoản đăng nhập."
        )
    context = (options or {}).get("formContext") or {}
    raw_name = context.get("applicantFullname") or context.get("fullname") or ""
    name = _norm_text(raw_name)
    identity = re.sub(r"\D+", "", str(context.get("applicantIdentityNumber") or context.get("identityNumber") or ""))
    if not name and not identity:
        return _NO_SUBMITTER.format(result="missing_ui_anchor", reason="Form chưa cho biết người đăng nhập.")

    anchor = f'tên "{raw_name}"' + (f', số định danh "{identity}"' if identity else "")
    for index, document in enumerate(documents, start=1):
        text = str(document.get("text") or "")
        if _matches_anchor(text, name, identity):
            return (
                '\n\n<nguoi_nop_context result="co_giay_to">\n'
                f"NGƯỜI NỘP (tài khoản đăng nhập) là {anchor}; tài liệu #{index} là giấy tờ của người này.\n"
                "- Người nộp CHÍNH LÀ người làm đơn (cùng họ tên hoặc số định danh với Đơn) → tự nộp, bỏ trống "
                "NguoiNop_*.\n"
                f"- KHÁC người làm đơn → nộp thay: NguoiNop_* lấy từ tài liệu #{index}; TUYỆT ĐỐI không đưa tài liệu "
                "này vào Person1_*.\n"
                f"<giay_to_nguoi_nop tai_lieu=\"{index}\">\n{text[:4000]}\n</giay_to_nguoi_nop>\n"
                "</nguoi_nop_context>"
            )
    return _NO_SUBMITTER.format(
        result="khong_co_giay_to", reason=f"NGƯỜI NỘP (tài khoản đăng nhập) là {anchor} nhưng hồ sơ không có giấy tờ "
        "của người này."
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
        context_builder=_submitter_context,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res

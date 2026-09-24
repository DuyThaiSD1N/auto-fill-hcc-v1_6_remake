"""Compact agent process pipeline cho "Gia hạn Chứng chỉ hành nghề thú y".

HAI vai (thường trùng): NGƯỜI ĐỀ NGHỊ (chủ hồ sơ) và NGƯỜI NỘP. context_builder neo NGƯỜI NỘP (tên +
CCCD tài khoản cổng tự đổ vào Phần I) để LLM tách khỏi người đề nghị khi có nộp thay — cùng cách làm
với cap_lai_CCHN_thu_y."""

import re

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_lai_CCHN_thu_y.process.runner import _matches_anchor, _norm_text
from app.pipelines.gia_han_chung_chi_hanh_nghe_thu_y.process import mapper
from app.pipelines.gia_han_chung_chi_hanh_nghe_thu_y.process.prompt import EXTRA_RULES
from app.pipelines.gia_han_chung_chi_hanh_nghe_thu_y.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


async def _submitter_context(documents: list[dict], options: dict) -> str:
    """Neo NGƯỜI NỘP (tên+CCCD cổng tự đổ từ tài khoản vào Phần I) để LLM tách khỏi NGƯỜI ĐỀ NGHỊ."""
    context = (options or {}).get("formContext") or {}
    raw_name = context.get("applicantFullname") or context.get("ownerFullname") or context.get("fullname") or ""
    name = _norm_text(raw_name)
    identity = re.sub(
        r"\D+",
        "",
        str(
            context.get("applicantIdentityNumber")
            or context.get("ownerIdentityNumber")
            or context.get("identityNumber")
            or ""
        ),
    )[:20]
    if not name and not identity:
        return ""

    matched = None
    for index, document in enumerate(documents, start=1):
        text = str(document.get("text") or "")
        if _matches_anchor(text, name, identity):
            matched = (index, text[:4000])
            break

    anchor = f'tên "{raw_name}"' + (f', số định danh "{identity}"' if identity else "")
    if matched:
        idx, scope = matched
        return (
            "\n\n<nguoi_nop_context result=\"co_giay_to\">\n"
            f"NGƯỜI NỘP HỒ SƠ (tài khoản đăng nhập) là: {anchor}. Tài liệu #{idx} có nhân thân của NGƯỜI "
            "NỘP. Có HAI người, phải tách RIÊNG, KHÔNG được lẫn:\n"
            f"- NGƯỜI NỘP = người trên tài liệu #{idx}. Trích vào các field NguoiNop_* TỪ CHÍNH tài liệu "
            f"#{idx}.\n"
            "- NGƯỜI ĐỀ NGHỊ (chủ hồ sơ) = người đứng tên Đơn gia hạn. Trích vào các field NguoiDeNghi_* "
            "TỪ Đơn + CCCD / Giấy khám sức khỏe của họ, TUYỆT ĐỐI KHÔNG lấy nhân thân người đề nghị từ "
            f"giấy tờ của người nộp (tài liệu #{idx}).\n"
            "- NẾU người nộp CHÍNH LÀ người đề nghị (cùng họ tên hoặc cùng số định danh với Đơn) → chỉ "
            f"1 người: BỎ TRỐNG NguoiNop_*, chỉ trích NguoiDeNghi_* từ tài liệu #{idx} + Đơn.\n"
            f"<giay_to_nguoi_nop tai_lieu=\"{idx}\">\n{scope}\n</giay_to_nguoi_nop>\n"
            "</nguoi_nop_context>"
        )
    return (
        "\n\n<nguoi_nop_context result=\"khong_co_giay_to\">\n"
        f"NGƯỜI NỘP HỒ SƠ (tài khoản đăng nhập) là: {anchor}, NHƯNG hồ sơ KHÔNG có giấy tờ nào của người "
        "này. NguoiDeNghi_* trích bình thường từ Đơn / CCCD / Giấy khám sức khỏe của người đề nghị. Bỏ "
        "trống NguoiNop_*.\n"
        "</nguoi_nop_context>"
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

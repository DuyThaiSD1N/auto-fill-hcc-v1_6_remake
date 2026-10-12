"""Compact agent process pipeline cho "Đề nghị miễn, giảm học phí trong cơ sở GDNN, GDĐH tư thục…" (mã 1.014335,
cổng DVC Bộ GD&ĐT)."""

import re

from app.pipelines._shared.compact_agent import runner
from app.pipelines.mien_giam_hoc_phi_gdnn_dai_hoc_tu_thuc.process import mapper
from app.pipelines.mien_giam_hoc_phi_gdnn_dai_hoc_tu_thuc.process.prompt import EXTRA_RULES
from app.pipelines.mien_giam_hoc_phi_gdnn_dai_hoc_tu_thuc.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
    OCR_MAX_PAGES,
)
from app.services.pdf_utils import trim_files_for_classify


async def _submitter_context(documents: list[dict], options: dict) -> str:
    """Neo NGƯỜI NỘP = người đăng nhập VNeID (formContext) vào đúng thẻ CCCD của họ, để LLM không lấy người nộp
    từ Giấy tiếp nhận hồ sơ/Đơn (thường là cha/mẹ hoặc chính sinh viên)."""
    context = (options or {}).get("formContext") or {}
    raw_name = str(context.get("applicantFullname") or context.get("fullname") or "").strip()
    identity = re.sub(r"\D+", "", str(context.get("applicantIdentityNumber") or context.get("identityNumber") or ""))
    if not raw_name and not identity:
        return ""
    anchor = f'tên "{raw_name}"' + (f', số định danh "{identity}"' if identity else "")
    for idx, document in enumerate(documents, start=1):
        text = str(document.get("text") or "")
        if mapper.card_of_account(text, identity, raw_name):
            return (
                "\n\n<nguoi_nop_context result=\"co_giay_to\">\n"
                f"NGƯỜI NỘP HỒ SƠ (tài khoản đăng nhập) là: {anchor}. Tài liệu #{idx} là thẻ CCCD của người này "
                "(trích đoạn bên dưới) → trích NguoiNop_* TỪ CHÍNH thẻ này (họ tên, số, giới tính, ngày cấp, nơi "
                "thường trú). KHÔNG lấy NguoiNop_* từ Giấy tiếp nhận hồ sơ hay Đơn. Nếu đây cũng là thẻ của sinh "
                "viên thì SinhVien_* lấy như thường.\n"
                f"<cccd_nguoi_nop tai_lieu=\"{idx}\">\n{text[:4000]}\n</cccd_nguoi_nop>\n"
                "</nguoi_nop_context>"
            )
    return (
        "\n\n<nguoi_nop_context result=\"khong_co_giay_to\">\n"
        f"NGƯỜI NỘP HỒ SƠ (tài khoản đăng nhập) là: {anchor}, NHƯNG hồ sơ KHÔNG có thẻ CCCD của người này → BỎ "
        "TRỐNG toàn bộ NguoiNop_* (KHÔNG lấy người ghi trên Giấy tiếp nhận hồ sơ). Các field khác trích bình thường.\n"
        "</nguoi_nop_context>"
    )


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    # Chỉ OCR vài trang đầu mỗi PDF (xem OCR_MAX_PAGES) — người dân hay quét gộp cả bộ hồ sơ thành một PDF dài.
    trimmed = {role: trim_files_for_classify(files or [], OCR_MAX_PAGES) for role, files in files_by_role.items()}
    res = await runner.run(
        trimmed,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        max_tokens=1800,
        context_builder=_submitter_context,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options, ocr_text=res.get("ocr_text", ""))
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res

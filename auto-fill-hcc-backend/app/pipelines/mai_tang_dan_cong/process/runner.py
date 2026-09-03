"""Compact agent process pipeline cho mai táng phí dân công hỏa tuyến.

HAI vai (thường trùng): CHỦ HỒ SƠ (người đứng khai) và NGƯỜI NỘP (tài khoản). context_builder neo NGƯỜI
NỘP theo formContext UI để LLM tách khỏi chủ hồ sơ khi có nộp thay."""

import re
import unicodedata

from app.pipelines._shared.compact_agent import runner
from app.pipelines.mai_tang_dan_cong.process import mapper
from app.pipelines.mai_tang_dan_cong.process.prompt import EXTRA_RULES
from app.pipelines.mai_tang_dan_cong.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


def _norm_text(value: str) -> str:
    text = str(value or "").replace("Đ", "D").replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^0-9a-zA-Z]+", " ", text).strip().lower()
    return re.sub(r"\s+", " ", text)


def _identity_occurs(identity: str, text: str) -> bool:
    if not identity:
        return False
    for cand in re.findall(r"(?:\d[ \t.\-]*){9,12}", str(text or "")):
        if re.sub(r"\D+", "", cand) == identity:
            return True
    return False


def _matches_anchor(text: str, name: str, identity: str) -> bool:
    name_matches = bool(name and name in _norm_text(text))
    identity_matches = _identity_occurs(identity, text)
    if name and identity:
        return name_matches and identity_matches
    return name_matches if name else identity_matches


async def _submitter_context(documents: list[dict], options: dict) -> str:
    """Neo NGƯỜI NỘP (tên+CCCD tài khoản do FE gửi qua formContext) để LLM tách khỏi CHỦ HỒ SƠ."""
    context = (options or {}).get("formContext") or {}
    raw_name = context.get("applicantFullname") or context.get("ownerFullname") or context.get("fullname") or ""
    name = _norm_text(raw_name)
    identity = re.sub(
        r"\D+", "",
        str(context.get("applicantIdentityNumber") or context.get("ownerIdentityNumber")
            or context.get("identityNumber") or ""),
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
            f"NGƯỜI NỘP HỒ SƠ (tài khoản đăng nhập) là: {anchor}. Hồ sơ CÓ CCCD của NGƯỜI NỘP (tài liệu #{idx}). "
            "Có HAI người, phải tách RIÊNG, KHÔNG được lẫn:\n"
            f"- NGƯỜI NỘP = người trên CCCD tài liệu #{idx}. Trích NguoiNop_* TỪ CHÍNH CCCD tài liệu #{idx}.\n"
            "- CHỦ HỒ SƠ = người đứng khai ở mục 1 Bản khai Mẫu 02-MTP. Trích ChuHoSo_* TỪ mục 1 + CCCD của "
            f"chính họ, TUYỆT ĐỐI KHÔNG lấy nhân thân chủ hồ sơ từ CCCD người nộp (tài liệu #{idx}).\n"
            "- NẾU người nộp CHÍNH LÀ chủ hồ sơ (cùng họ tên hoặc cùng số định danh với mục 1) → chỉ 1 người: "
            f"BỎ TRỐNG NguoiNop_*, chỉ trích ChuHoSo_* từ mục 1 + CCCD #{idx}.\n"
            f"<cccd_nguoi_nop tai_lieu=\"{idx}\">\n{scope}\n</cccd_nguoi_nop>\n"
            "</nguoi_nop_context>"
        )
    return (
        "\n\n<nguoi_nop_context result=\"khong_co_giay_to\">\n"
        f"NGƯỜI NỘP HỒ SƠ (tài khoản đăng nhập) là: {anchor}, NHƯNG hồ sơ KHÔNG có CCCD riêng của người này. "
        "ChuHoSo_* trích bình thường từ mục 1 Bản khai + CCCD của người đứng khai. Bỏ trống NguoiNop_*.\n"
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

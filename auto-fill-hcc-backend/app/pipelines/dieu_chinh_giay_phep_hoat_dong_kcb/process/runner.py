"""Compact agent process pipeline cho "Điều chỉnh giấy phép hoạt động khám bệnh, chữa bệnh".

Chủ hồ sơ là CƠ SỞ KCB + người đại diện ký Đơn. context_builder neo NGƯỜI NỘP (tên + CCCD tài khoản cổng tự
đổ vào Phần I) để LLM tách CCCD người nộp thay khỏi CCCD người đại diện."""

import re
import unicodedata

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dieu_chinh_giay_phep_hoat_dong_kcb.process import mapper
from app.pipelines.dieu_chinh_giay_phep_hoat_dong_kcb.process.prompt import EXTRA_RULES
from app.pipelines.dieu_chinh_giay_phep_hoat_dong_kcb.process.schema import (
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
    """Neo NGƯỜI NỘP (tên+CCCD cổng tự đổ từ tài khoản vào Phần I) để LLM tách khỏi NGƯỜI ĐẠI DIỆN.

    Người nộp thay (cán bộ của cơ sở, người được ủy quyền) có thể upload CCCD của mình cạnh CCCD người đại diện
    → không có mỏ neo, LLM dễ lấy nhầm CCCD người nộp làm người đại diện ký Đơn.
    """
    # Chế độ "người nộp = chủ hồ sơ": bỏ mốc tài khoản, chỉ trích cơ sở + người đại diện.
    if str((options or {}).get("submitterMode") or "") == "owner_as_submitter":
        return ""
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
            f"NGƯỜI NỘP HỒ SƠ (tài khoản đăng nhập) là: {anchor}. Hồ sơ CÓ CCCD của người này (tài liệu #{idx}).\n"
            "- Nếu người này KHÁC người ký Đơn → trích NguoiNop_* TỪ CHÍNH CCCD tài liệu "
            f"#{idx}; TUYỆT ĐỐI KHÔNG dùng CCCD #{idx} cho DaiDien_*.\n"
            "- Nếu người này CHÍNH LÀ người ký Đơn (cùng họ tên) → đó là CCCD người đại diện: trích DaiDien_*, "
            "BỎ TRỐNG NguoiNop_*.\n"
            f"<cccd_nguoi_nop tai_lieu=\"{idx}\">\n{scope}\n</cccd_nguoi_nop>\n"
            "</nguoi_nop_context>"
        )
    return (
        "\n\n<nguoi_nop_context result=\"khong_co_giay_to\">\n"
        f"NGƯỜI NỘP HỒ SƠ (tài khoản đăng nhập) là: {anchor}, NHƯNG hồ sơ KHÔNG có CCCD riêng của người này. "
        "Bỏ trống NguoiNop_*.\n"
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

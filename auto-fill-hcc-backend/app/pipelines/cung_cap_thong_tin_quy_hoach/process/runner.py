"""Compact agent process pipeline cho "Cung cấp thông tin quy hoạch đô thị và nông thôn"."""

import re
import unicodedata

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cung_cap_thong_tin_quy_hoach.process import mapper
from app.pipelines.cung_cap_thong_tin_quy_hoach.process.prompt import EXTRA_RULES
from app.pipelines.cung_cap_thong_tin_quy_hoach.process.schema import (
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
        # Có cả tên lẫn số → chỉ khớp khi cùng tài liệu chứa đủ (tránh trùng tên khác người).
        return name_matches and identity_matches
    return name_matches if name else identity_matches


async def _submitter_context(documents: list[dict], options: dict) -> str:
    """Đưa MỎ NEO người nộp (tên+CCCD cổng tự điền từ VNeID) vào prompt để LLM trích đúng người.
    Có CCCD người nộp trong hồ sơ → trích NguoiNop_* từ đúng tài liệu đó (kể cả khi khác người trên
    GCN/Đơn). Không có CCCD người nộp → để trống NguoiNop_*. Không có mỏ neo → giữ hành vi tự nộp."""
    context = (options or {}).get("formContext") or {}
    raw_name = context.get("applicantFullname") or context.get("fullname") or ""
    name = _norm_text(raw_name)
    identity = re.sub(
        r"\D+", "", str(context.get("applicantIdentityNumber") or context.get("identityNumber") or "")
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
            f"NGƯỜI NỘP HỒ SƠ (tài khoản đăng nhập) là: {anchor}. Hồ sơ CÓ giấy tờ tùy thân của người "
            f"này (tài liệu #{idx}).\n"
            "- BẮT BUỘC trích NguoiNop_* (họ tên, ngày sinh, giới tính, số định danh, ngày cấp, nơi cấp, "
            f"nơi thường trú, điện thoại) CỦA CHÍNH NGƯỜI NÀY từ CCCD tài liệu #{idx}.\n"
            "- Nếu người nộp KHÁC người sử dụng đất trên Giấy chứng nhận/Đơn (nộp thay) → vẫn lấy thông "
            "tin NGƯỜI NỘP, KHÔNG lấy thông tin người trên GCN.\n"
            f"<cccd_nguoi_nop tai_lieu=\"{idx}\">\n{scope}\n</cccd_nguoi_nop>\n"
            "</nguoi_nop_context>"
        )
    return (
        "\n\n<nguoi_nop_context result=\"khong_co_giay_to\">\n"
        f"NGƯỜI NỘP HỒ SƠ (tài khoản đăng nhập) là: {anchor}, NHƯNG hồ sơ KHÔNG có giấy tờ tùy thân của "
        "người này. BẮT BUỘC để TRỐNG toàn bộ NguoiNop_* (cổng đã tự điền từ VNeID, không đè).\n"
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
        max_tokens=900,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res

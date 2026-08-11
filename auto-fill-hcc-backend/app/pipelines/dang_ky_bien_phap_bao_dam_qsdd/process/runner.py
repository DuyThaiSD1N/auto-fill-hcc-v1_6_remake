"""Compact agent process pipeline cho "Đăng ký biện pháp bảo đảm bằng QSDĐ, tài sản gắn liền với đất".

context_builder neo NGƯỜI YÊU CẦU (tên + CCCD tài khoản cổng tự đổ) để LLM chỉ trích người này, không lẫn
bên còn lại (bên bảo đảm vs bên nhận bảo đảm) trong Phiếu Mẫu 01a."""

import re
import unicodedata

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_bien_phap_bao_dam_qsdd.process import mapper
from app.pipelines.dang_ky_bien_phap_bao_dam_qsdd.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_bien_phap_bao_dam_qsdd.process.schema import (
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


async def _requester_context(documents: list[dict], options: dict) -> str:
    """Neo NGƯỜI YÊU CẦU (tên + CCCD tài khoản cổng tự đổ vào form) để LLM tách khỏi bên còn lại."""
    context = (options or {}).get("formContext") or {}
    raw_name = (
        context.get("ownerFullname")
        or context.get("applicantFullname")
        or context.get("fullname")
        or ""
    )
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

    anchor = f'tên "{raw_name}"' + (f', số định danh "{identity}"' if identity else "")
    matched = None
    for index, document in enumerate(documents, start=1):
        text = str(document.get("text") or "")
        if _matches_anchor(text, name, identity):
            matched = (index, text[:4000])
            break

    if matched:
        idx, scope = matched
        return (
            "\n\n<nguoi_yeu_cau_context result=\"co_giay_to\">\n"
            f"NGƯỜI YÊU CẦU ĐĂNG KÝ (tài khoản đăng nhập) là: {anchor}. Hồ sơ CÓ giấy tờ tùy thân của người "
            f"này (tài liệu #{idx}). Phiếu Mẫu 01a có HAI bên (bên bảo đảm Mục 3, bên nhận bảo đảm Mục 4) — "
            f"CHỈ trích thông tin của NGƯỜI YÊU CẦU (người khớp tài liệu #{idx} và Mục 1 Phiếu), TUYỆT ĐỐI "
            "KHÔNG lấy nhân thân của bên còn lại.\n"
            f"<giay_to_nguoi_yeu_cau tai_lieu=\"{idx}\">\n{scope}\n</giay_to_nguoi_yeu_cau>\n"
            "</nguoi_yeu_cau_context>"
        )
    return (
        "\n\n<nguoi_yeu_cau_context result=\"khong_ro\">\n"
        f"NGƯỜI YÊU CẦU ĐĂNG KÝ (tài khoản đăng nhập) là: {anchor}. Trích thông tin của CHÍNH người này từ "
        "Phiếu Mẫu 01a (Mục 1 + Mục 3 hoặc 4 tương ứng) và CCCD của họ. Không lấy nhân thân bên còn lại.\n"
        "</nguoi_yeu_cau_context>"
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
        context_builder=_requester_context,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res

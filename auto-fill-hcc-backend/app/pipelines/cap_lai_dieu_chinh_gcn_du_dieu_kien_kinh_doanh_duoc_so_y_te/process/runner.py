"""Compact agent process pipeline cho "Cấp lại, điều chỉnh GCN đủ điều kiện kinh doanh dược (Sở Y tế)".

HAI vai: CHỦ HỒ SƠ (chủ cơ sở) và NGƯỜI NỘP (tài khoản đăng nhập). context_builder neo NGƯỜI NỘP vào đúng
thẻ CCCD của họ. GCN đăng ký hộ kinh doanh cũng in họ tên + số định danh CHỦ HỘ nên chỉ nhận đoạn văn bản
có dấu hiệu thẻ căn cước, và dò theo TỪNG TRANG vì hồ sơ hay là một PDF gộp."""

import re
import unicodedata

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_lai_dieu_chinh_gcn_du_dieu_kien_kinh_doanh_duoc_so_y_te.process import mapper
from app.pipelines.cap_lai_dieu_chinh_gcn_du_dieu_kien_kinh_doanh_duoc_so_y_te.process.prompt import (
    EXTRA_RULES,
)
from app.pipelines.cap_lai_dieu_chinh_gcn_du_dieu_kien_kinh_doanh_duoc_so_y_te.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

_PAGE_SPLIT_RE = re.compile(r"(?im)^[\t ─-╿-]*(?:trang|page)\s+\d+\s*/\s*\d+[\t ─-╿-]*$")
_ID_CARD_MARKERS = (
    "can cuoc",
    "chung minh nhan dan",
    "identity card",
    "personal identification",
    "citizen identity",
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


def _looks_like_id_card(text: str) -> bool:
    folded = _norm_text(text)
    return any(marker in folded for marker in _ID_CARD_MARKERS)


def find_submitter_card(documents: list[dict], name: str, identity: str) -> tuple[int, str] | None:
    """(số thứ tự tài liệu 1-based, đoạn văn bản thẻ CCCD) của người nộp, hoặc None."""
    for index, document in enumerate(documents, start=1):
        text = str(document.get("text") or "")
        chunks = [c for c in _PAGE_SPLIT_RE.split(text) if c.strip()] or [text]
        for chunk in chunks:
            if _looks_like_id_card(chunk) and _matches_anchor(chunk, name, identity):
                return index, chunk[:4000]
    return None


async def _submitter_context(documents: list[dict], options: dict) -> str:
    """Neo NGƯỜI NỘP (tên + CCCD cổng tự đổ từ tài khoản vào Phần I) để LLM tách khỏi CHỦ HỒ SƠ."""
    context = (options or {}).get("formContext") or {}
    raw_name = context.get("applicantFullname") or context.get("fullname") or ""
    name = _norm_text(raw_name)
    identity = re.sub(
        r"\D+", "", str(context.get("applicantIdentityNumber") or context.get("identityNumber") or "")
    )[:20]
    if not name and not identity:
        return ""

    anchor = f'tên "{raw_name}"' + (f', số định danh "{identity}"' if identity else "")
    matched = find_submitter_card(documents, name, identity)
    if matched:
        idx, scope = matched
        return (
            "\n\n<nguoi_nop_context result=\"co_giay_to\">\n"
            f"NGƯỜI NỘP HỒ SƠ (tài khoản đăng nhập) là: {anchor}. Tài liệu #{idx} CÓ thẻ CCCD của người này "
            "(trích đoạn bên dưới).\n"
            "- Nếu người này KHÁC chủ cơ sở (người đại diện theo pháp luật / chủ hộ kinh doanh trên Đơn, GCN "
            "đăng ký hộ kinh doanh) → trích NguoiNop_* TỪ CHÍNH thẻ này; ChuHoSo_* vẫn lấy theo chủ cơ sở, "
            "TUYỆT ĐỐI KHÔNG lấy từ thẻ này.\n"
            "- Nếu người này CHÍNH LÀ chủ cơ sở (trùng họ tên hoặc số định danh) → trích thẻ này vào ChuHoSo_* "
            "và BỎ TRỐNG NguoiNop_*.\n"
            f"<cccd_nguoi_nop tai_lieu=\"{idx}\">\n{scope}\n</cccd_nguoi_nop>\n"
            "</nguoi_nop_context>"
        )
    return (
        "\n\n<nguoi_nop_context result=\"khong_co_giay_to\">\n"
        f"NGƯỜI NỘP HỒ SƠ (tài khoản đăng nhập) là: {anchor}, NHƯNG hồ sơ KHÔNG có thẻ CCCD của người này → BỎ "
        "TRỐNG toàn bộ NguoiNop_*. ChuHoSo_* trích bình thường theo chủ cơ sở.\n"
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

"""Compact agent process pipeline cho thủ tục giải quyết chế độ người HĐKC GPDT, bảo vệ Tổ quốc."""

import re
import unicodedata

from app.pipelines._shared.compact_agent import runner
from app.pipelines.giai_quyet_che_do_khang_chien.process import mapper
from app.pipelines.giai_quyet_che_do_khang_chien.process.prompt import EXTRA_RULES
from app.pipelines.giai_quyet_che_do_khang_chien.process.schema import (
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
    """Đưa MỎ NEO người nộp (tên+CCCD cổng tự đổ từ tài khoản vào Phần I) vào prompt.

    Thủ tục này thường NỘP THAY: cán bộ/thân nhân đứng nộp cho đối tượng HĐKC cao tuổi và có thể
    UPLOAD CẢ CCCD CỦA MÌNH. Không có mỏ neo, LLM dễ vơ CCCD người nộp làm đối tượng (Nguoi_*). Mỏ neo
    giúp LLM biết CCCD nào là của NGƯỜI NỘP để BỎ QUA khi trích đối tượng; đối tượng lấy từ Bản khai/BHXH/GCN.
    """
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
            f"NGƯỜI NỘP HỒ SƠ (tài khoản đăng nhập) là: {anchor}. Hồ sơ CÓ CCCD của NGƯỜI NỘP (tài liệu #{idx}). "
            "Có HAI người, phải tách RIÊNG, KHÔNG được lẫn:\n"
            f"- NGƯỜI NỘP = người trên CCCD tài liệu #{idx}. Trích thông tin NGƯỜI NỘP vào các field NguoiNop_* "
            "(NguoiNop_GioiTinh, NguoiNop_NgayCap, NguoiNop_NoiCap, NguoiNop_ThuongTru, NguoiNop_DienThoai, "
            "NguoiNop_Email) TỪ "
            f"CHÍNH CCCD tài liệu #{idx}.\n"
            "- ĐỐI TƯỢNG HĐKC (chủ hồ sơ) = người đứng tên trên Bản khai Mẫu 11 / Sổ BHXH / GCN Huân-Huy chương. "
            "Trích thông tin đối tượng vào các field Nguoi_* + HDKC_* TỪ các giấy tờ đó, TUYỆT ĐỐI KHÔNG lấy "
            f"họ tên/ngày sinh/số định danh/địa chỉ/quê quán của đối tượng từ CCCD người nộp (tài liệu #{idx}).\n"
            "- NẾU người nộp CHÍNH LÀ đối tượng (cùng họ tên hoặc cùng số định danh với Bản khai) → chỉ 1 người: "
            f"cả Nguoi_* lẫn NguoiNop_* lấy từ CCCD #{idx} + Bản khai.\n"
            f"<cccd_nguoi_nop tai_lieu=\"{idx}\">\n{scope}\n</cccd_nguoi_nop>\n"
            "</nguoi_nop_context>"
        )
    return (
        "\n\n<nguoi_nop_context result=\"khong_co_giay_to\">\n"
        f"NGƯỜI NỘP HỒ SƠ (tài khoản đăng nhập) là: {anchor}, NHƯNG hồ sơ KHÔNG có CCCD của người này. "
        "Nguoi_* (đối tượng HĐKC = chủ hồ sơ) trích bình thường từ Bản khai Mẫu 11 / Sổ BHXH / GCN Huân-Huy "
        "chương của người đứng tên trên đó.\n"
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

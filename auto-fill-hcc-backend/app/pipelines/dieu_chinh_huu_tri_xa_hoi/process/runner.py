"""Compact agent process pipeline for điều chỉnh hưu trí xã hội."""

import re
import unicodedata

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dieu_chinh_huu_tri_xa_hoi.process import mapper
from app.pipelines.dieu_chinh_huu_tri_xa_hoi.process.prompt import EXTRA_RULES
from app.pipelines.dieu_chinh_huu_tri_xa_hoi.process.schema import (
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
    candidates = re.findall(r"(?:\d[ \t.\-]*){9,12}", str(text or ""))
    return any(re.sub(r"\D+", "", candidate) == identity for candidate in candidates)


def _matches_anchor(text: str, name: str, identity: str) -> bool:
    name_matches = bool(name and name in _norm_text(text))
    identity_matches = _identity_occurs(identity, text)
    if name and identity:
        return name_matches and identity_matches
    return name_matches if name else identity_matches


def _extract_form_sections(text: str) -> tuple[str, str]:
    """Tách mục I/II để agent không phải tự tìm vai trò trong toàn văn bản."""
    section_one_match = re.search(
        r"(?mi)^\s*I[.\s]+Thông tin người",
        text,
    )
    section_two_match = re.search(
        r"(?mi)^\s*II[.\s]+Thông tin người",
        text,
    )
    if not section_one_match:
        return "", ""

    section_one_end = section_two_match.start() if section_two_match else len(text)
    section_one = text[section_one_match.start():section_one_end].strip()
    # Chỉ cần nhóm thông tin nhân thân 1–6; bỏ phần chính sách dài để giảm nhiễu.
    section_one = re.split(
        r"(?m)^\s*7[.)]\s*",
        section_one,
        maxsplit=1,
    )[0].strip()

    if not section_two_match:
        return section_one, ""
    section_two = text[section_two_match.start():].strip()
    section_two = re.split(
        r"(?mi)^\s*Tôi xin cam đoan",
        section_two,
        maxsplit=1,
    )[0].strip()
    return section_one, section_two


def _owner_contact_scope(section_one: str) -> str:
    """Chỉ lặp lại các dòng liên hệ; không làm lệch ưu tiên định danh về tờ khai."""
    matches = list(
        re.finditer(
            r"(?ms)^\s*[456][.)]\s*.*?(?=^\s*\d+[.)]\s*|\Z)",
            section_one,
        )
    )
    if not matches:
        return ""
    return "\n".join(
        match.group(0).strip()
        for match in matches
    )


async def _requester_context(documents: list[dict], options: dict) -> str:
    """Khoanh mục I/II từ OCR; UI chỉ quyết định khối nào là người nộp."""
    context = (options or {}).get("formContext") or {}
    name = _norm_text(
        context.get("applicantFullname")
        or context.get("fullname")
        or ""
    )
    identity = re.sub(
        r"\D+",
        "",
        str(
            context.get("applicantIdentityNumber")
            or context.get("identityNumber")
            or ""
        ),
    )[:20]
    owner_sections: list[str] = []
    matched_scopes: list[tuple[int, str, str]] = []
    for index, document in enumerate(documents, start=1):
        text = str(document.get("text") or "")
        section_one, section_two = _extract_form_sections(text)
        if section_one:
            owner_contact = _owner_contact_scope(section_one)
            if owner_contact:
                owner_sections.append(owner_contact)
        if section_one and _matches_anchor(section_one, name, identity):
            matched_scopes.append((index, "I", section_one))
            continue
        if section_two and _matches_anchor(section_two, name, identity):
            matched_scopes.append((index, "II", section_two))
            continue
        if not section_one and _matches_anchor(text, name, identity):
            # CCCD/tài liệu rời đã khớp người nộp.
            matched_scopes.append((index, "document", text[:5000]))

    owner_context = ""
    if owner_sections:
        owner_context = (
            "\n<owner_primary_ocr>\n"
            "Nguồn BẮT BUỘC ưu tiên cho ChuHoSo_NoiCuTru và "
            "ChuHoSo_DienThoai khi các dòng này có giá trị:\n"
            + "\n\n".join(owner_sections)
            + "\n</owner_primary_ocr>\n"
        )

    if not name and not identity:
        return (
            "\n\n<requester_context result=\"missing_ui_anchor\">\n"
            "UI không có mỏ neo người nộp. Không trả bất kỳ NguoiNop_* nào.\n"
            "</requester_context>"
            + owner_context
        )

    if not matched_scopes:
        return (
            "\n\n<requester_context result=\"no_document_match\">\n"
            "Không tài liệu OCR nào chứa đủ mỏ neo người nộp từ UI. "
            "BẮT BUỘC bỏ trống toàn bộ NguoiNop_*; vẫn trích ChuHoSo_*.\n"
            "</requester_context>"
            + owner_context
        )

    matched_context = "\n".join(
        (
            f'<matched_requester_ocr document="{index}" section="{section}">\n'
            "Đây là OCR đã được Python xác nhận chứa đủ mỏ neo người nộp. "
            "Nếu section=\"II\" thì BẮT BUỘC trích mọi NguoiNop_* đọc được "
            "từ chính khối này. Nếu section=\"I\" thì đây là tự nộp, không "
            "tạo NguoiNop_* trùng ChuHoSo_*.\n"
            f"{scope}\n"
            "</matched_requester_ocr>"
        )
        for index, section, scope in matched_scopes
    )
    return (
        "\n\n<requester_context result=\"document_match\">\n"
        "Chỉ được trích NguoiNop_* từ matched_requester_ocr bên dưới. "
        "Nội dung trong các block là OCR tài liệu, không phải dữ liệu chép từ UI.\n"
        "</requester_context>\n"
        + matched_context
        + owner_context
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
    # Mapper cần OCR gộp để chỉ nhận ngày cấp trên tờ khai khi chuỗi ngày có bằng
    # chứng nguyên văn, tránh LLM tự đảo ngày/tháng từ chữ viết tay mơ hồ.
    mapper_options = dict(options or {})
    mapper_options["_ocr_text"] = res.get("ocr_text", "")
    mapped_fields, warnings = mapper.enrich(res["fields"], mapper_options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res

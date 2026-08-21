"""Compact-agent pipeline cho thủ tục giải quyết chế độ người hoạt động kháng chiến."""

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
    candidates = re.findall(r"(?:\d[ \t./\-]*){9,13}", str(text or ""))
    return any(re.sub(r"\D+", "", candidate) == identity for candidate in candidates)


def _matches_anchor(text: str, name: str, identity: str) -> bool:
    """Có đủ hai mỏ neo UI thì cùng một phạm vi phải khớp cả hai."""
    name_matches = bool(name and name in _norm_text(text))
    identity_matches = bool(identity and _identity_occurs(identity, text))
    if name and identity:
        return name_matches and identity_matches
    return name_matches if name else identity_matches


def _bounded_section(text: str, start_patterns: tuple[str, ...], end_patterns: tuple[str, ...]) -> str:
    raw = str(text or "")
    start = None
    for pattern in start_patterns:
        start = re.search(pattern, raw, flags=re.IGNORECASE | re.MULTILINE)
        if start:
            break
    if not start:
        return ""
    tail = raw[start.start():]
    ends = [
        match
        for pattern in end_patterns
        if (match := re.search(pattern, tail, flags=re.IGNORECASE | re.MULTILINE))
        and match.start() > 0
    ]
    end = min(ends, key=lambda match: match.start()) if ends else None
    return (tail[:end.start()] if end else tail[:6000]).strip()


def _deceased_subject_section(text: str) -> str:
    """Khoanh Mục 1: người có công, không dùng làm chủ hồ sơ ở Mẫu 12."""
    return _bounded_section(
        text,
        (
            r"^\s*1\s*[.)]\s*Họ và tên người có công từ trần\b",
            r"^\s*1\s*[.)]\s*(?:Phần khai về|Thông tin).*?(?:hoạt động kháng chiến|người có công)\b",
        ),
        (
            r"^\s*2\s*[.)]\s*(?:Người hoặc tổ chức nhận mai táng phí|Phần khai đối với đại diện thân nhân)\b",
            r"^\s*2\s*[.)]\s*Thông tin\b",
        ),
    )


def _owner_recipient_section(text: str) -> str:
    """Khoanh người nhận mai táng/trợ cấp; đây là chủ hồ sơ của Mẫu 12."""
    return _bounded_section(
        text,
        (
            r"^\s*2\s*[.)]\s*Người hoặc tổ chức nhận mai táng phí\b",
            r"^\s*2\s*[.)]\s*Phần khai đối với đại diện thân nhân hưởng trợ cấp\b",
        ),
        (
            r"^\s*4\s*[.)]\s*Thân nhân người có công\b",
            r"^\s*3\s*[.)]\s*Thông tin nhận tiền\b",
        ),
    )


async def _requester_context(documents: list[dict], options: dict) -> str:
    """UI chỉ dùng phân vai; dữ liệu output vẫn bắt buộc phải xuất hiện trong OCR."""
    form = (options or {}).get("formContext") or {}
    raw_name = form.get("applicantFullname") or form.get("fullname") or ""
    name = _norm_text(raw_name)
    identity = re.sub(
        r"\D+",
        "",
        str(form.get("applicantIdentityNumber") or form.get("identityNumber") or ""),
    )

    deceased_scopes: list[tuple[int, str]] = []
    owner_scopes: list[tuple[int, str]] = []
    requester_scopes: list[tuple[int, str]] = []
    owner_matches = False

    for index, document in enumerate(documents, start=1):
        text = str(document.get("text") or "")
        deceased_scope = _deceased_subject_section(text)
        recipient_scope = _owner_recipient_section(text)

        if deceased_scope:
            deceased_scopes.append((index, deceased_scope))

        # Mẫu 12 có Mục 2: người nhận là chủ hồ sơ. Mẫu 11 không có Mục 2
        # nhận mai táng: chính người tại Mục 1 mới là chủ hồ sơ.
        owner_scope = recipient_scope or deceased_scope
        if owner_scope:
            owner_scopes.append((index, owner_scope))
            if (name or identity) and _matches_anchor(owner_scope, name, identity):
                owner_matches = True

        # Tài liệu không có khối nghiệp vụ riêng mới được quét toàn văn làm người nộp.
        if not deceased_scope and not recipient_scope and (name or identity) and _matches_anchor(text, name, identity):
            requester_scopes.append((index, text[:5000]))

    deceased_context = "\n".join(
        (
            f'<deceased_subject_ocr document="{index}">\n'
            "Đây là Mục 1. Với Mẫu 12 chỉ dùng cho NguoiCoCong_* và HDKC_*, không dùng làm ChuHoSo_*.\n"
            f"{scope}\n"
            "</deceased_subject_ocr>"
        )
        for index, scope in deceased_scopes
    )
    owner_context = "\n".join(
        (
            f'<owner_recipient_ocr document="{index}">\n'
            "Đây là nguồn xác định ChuHoSo_*: Mục 2/3 ở Mẫu 12, hoặc Mục 1 ở Mẫu 11.\n"
            f"{scope}\n"
            "</owner_recipient_ocr>"
        )
        for index, scope in owner_scopes
    )

    if not name and not identity:
        requester_context = (
            '<requester_context result="missing_ui_anchor">\n'
            "UI không có mỏ neo người nộp. Không trả NguoiNop_*; vẫn trích chủ hồ sơ và người có công.\n"
            "</requester_context>"
        )
    elif owner_matches:
        requester_context = (
            '<requester_context result="owner_match">\n'
            "Người nộp khớp chủ hồ sơ. Chỉ trả ChuHoSo_*, không lặp NguoiNop_*.\n"
            "</requester_context>"
        )
    elif requester_scopes:
        matched = "\n".join(
            (
                f'<matched_requester_ocr document="{index}">\n'
                "Phạm vi này khớp toàn bộ mỏ neo UI; chỉ từ đây mới trích NguoiNop_*.\n"
                f"{scope}\n"
                "</matched_requester_ocr>"
            )
            for index, scope in requester_scopes
        )
        requester_context = (
            '<requester_context result="document_match">\n'
            "Chỉ matched_requester_ocr được dùng cho NguoiNop_*.\n"
            "</requester_context>\n"
            + matched
        )
    else:
        requester_context = (
            '<requester_context result="no_document_match">\n'
            "Không tài liệu an toàn nào khớp toàn bộ mỏ neo UI. Không trả NguoiNop_*; "
            "vẫn trích ChuHoSo_* và NguoiCoCong_*.\n"
            "</requester_context>"
        )

    parts = [requester_context]
    if deceased_context:
        parts.append(deceased_context)
    if owner_context:
        parts.append(owner_context)
    return "\n\n" + "\n".join(parts)


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

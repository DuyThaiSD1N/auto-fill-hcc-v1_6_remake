"""Compact agent process pipeline for "Xác định mức độ khuyết tật"."""

import re
import unicodedata

from app.pipelines._shared.compact_agent import runner
from app.pipelines.khuyet_tat.process import mapper
from app.pipelines.khuyet_tat.process.prompt import EXTRA_RULES
from app.pipelines.khuyet_tat.process.schema import (
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
    """Có đủ hai mỏ neo UI thì cùng một tài liệu phải khớp cả hai."""
    name_matches = bool(name and name in _norm_text(text))
    identity_matches = bool(identity and _identity_occurs(identity, text))
    if name and identity:
        return name_matches and identity_matches
    return name_matches if name else identity_matches


async def _requester_context(documents: list[dict], options: dict) -> str:
    """Khoanh giấy tờ người nộp bằng UI; dữ liệu output vẫn phải có trong OCR."""
    form = (options or {}).get("formContext") or {}
    name = _norm_text(form.get("applicantFullname") or form.get("fullname") or "")
    identity = re.sub(
        r"\D+",
        "",
        str(form.get("applicantIdentityNumber") or form.get("identityNumber") or ""),
    )

    if not name and not identity:
        return (
            '\n\n<requester_context result="missing_ui_anchor">\n'
            "UI không có mỏ neo người nộp. Không trả NguoiNop_*.\n"
            "</requester_context>"
        )

    matched = [
        (index, str(document.get("text") or "")[:6000])
        for index, document in enumerate(documents, start=1)
        if _matches_anchor(str(document.get("text") or ""), name, identity)
    ]
    if not matched:
        return (
            '\n\n<requester_context result="no_document_match">\n'
            "Không tài liệu OCR nào khớp đủ mỏ neo người nộp từ UI. "
            "Không trả NguoiNop_*; vẫn trích ChuHoSo_* và các field nghiệp vụ.\n"
            "</requester_context>"
        )

    scopes = "\n".join(
        (
            f'<matched_requester_ocr document="{index}">\n'
            "Đây là tài liệu đã được Python xác nhận thuộc người nộp. "
            "BẮT BUỘC trích mọi NguoiNop_* đọc được từ chính OCR này.\n"
            f"{text}\n"
            "</matched_requester_ocr>"
        )
        for index, text in matched
    )
    return (
        '\n\n<requester_context result="document_match">\n'
        "Chỉ trích NguoiNop_* từ matched_requester_ocr; không dùng tài liệu người khác.\n"
        "</requester_context>\n"
        + scopes
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
        max_tokens=2200,
    )
    res["fields"] = mapper.enrich(res["fields"], options)
    return res

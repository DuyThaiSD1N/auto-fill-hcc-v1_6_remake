"""Compact agent process pipeline for "Thi tuyển công chức".

Hai chế độ người nộp (xem mapper.enrich): theo tài khoản đưa mốc VNeID vào prompt để LLM chỉ trích
NguoiNop_* từ đúng giấy tờ của người đang đăng nhập; theo tờ khai (`submitterMode="owner_as_submitter"`)
bỏ mốc, người nộp = người dự tuyển trên Phiếu.
"""

import re
import unicodedata

from app.pipelines._shared.compact_agent import runner
from app.pipelines.thi_tuyen_cong_chuc.process import mapper
from app.pipelines.thi_tuyen_cong_chuc.process.prompt import EXTRA_RULES
from app.pipelines.thi_tuyen_cong_chuc.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or "")).replace("Đ", "D").replace("đ", "d")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text).strip().lower()


def _anchor(options: dict) -> tuple[str, str]:
    form = (options or {}).get("formContext") or {}
    name = _fold(form.get("applicantFullname") or form.get("fullname") or "")
    identity = re.sub(r"\D+", "", str(form.get("applicantIdentityNumber") or form.get("identityNumber") or ""))
    return name, identity


def _matches(text: str, name: str, identity: str) -> bool:
    # Số định danh quyết khi có; thiếu số mới xét họ tên (OCR hay rơi dấu nên so bản bỏ dấu).
    if identity:
        return identity in re.sub(r"\D+", "", text)
    return bool(name) and name in _fold(text)


def _is_phieu(text: str) -> bool:
    folded = _fold(text)
    return "phieu dang ky du tuyen" in folded or "phieu dang ky thi tuyen" in folded


async def _requester_context(documents: list[dict], options: dict) -> str:
    """Chế độ THEO TÀI KHOẢN: mốc chỉ xác định ai đang nộp; nhân thân vẫn đọc từ OCR của đúng người."""
    name, identity = _anchor(options)
    if not name and not identity:
        return (
            '\n\n<requester_context result="missing_ui_anchor">\n'
            "UI không có mốc tài khoản người nộp. Không trả NguoiNop_*.\n"
            "</requester_context>"
        )

    owner_match = False
    matched: list[tuple[int, str]] = []
    for index, document in enumerate(documents, start=1):
        text = str(document.get("text") or "")
        if not _matches(text, name, identity):
            continue
        if _is_phieu(text):
            owner_match = True
        else:
            matched.append((index, text[:5000]))

    if owner_match:
        return (
            '\n\n<requester_context result="owner_match">\n'
            "Tài khoản đăng nhập chính là người dự tuyển trên Phiếu (tự nộp). Không trả NguoiNop_*.\n"
            "</requester_context>"
        )
    if matched:
        blocks = "\n".join(
            f'<matched_requester_ocr document="{index}">\n{scope}\n</matched_requester_ocr>'
            for index, scope in matched
        )
        return (
            '\n\n<requester_context result="document_match">\n'
            "Chỉ matched_requester_ocr khớp tài khoản đăng nhập; trích NguoiNop_* từ chính OCR này nếu "
            "người đó KHÁC người dự tuyển.\n"
            "</requester_context>\n" + blocks
        )
    return (
        '\n\n<requester_context result="no_document_match">\n'
        "Không giấy tờ nào khớp tài khoản đăng nhập. Không trả NguoiNop_*.\n"
        "</requester_context>"
    )


async def _owner_only_context(documents: list[dict], options: dict) -> str:
    """Chế độ THEO TỜ KHAI: không đưa mốc tài khoản vào prompt."""
    _ = documents, options
    return (
        '\n\n<requester_context result="missing_ui_anchor">\n'
        "Chế độ người nộp = người dự tuyển trên Phiếu: KHÔNG dùng mốc tài khoản. Không trả NguoiNop_*.\n"
        "</requester_context>"
    )


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    owner_mode = str((options or {}).get("submitterMode") or "") == "owner_as_submitter"
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        context_builder=_owner_only_context if owner_mode else _requester_context,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res

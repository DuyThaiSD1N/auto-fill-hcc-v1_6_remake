"""Compact-agent pipeline cho mai táng người hưởng hưu trí xã hội."""

import re
import unicodedata

from app.pipelines._shared.compact_agent import runner
from app.pipelines.ho_tro_mai_tang_huu_tri_xa_hoi.process import mapper
from app.pipelines.ho_tro_mai_tang_huu_tri_xa_hoi.process.prompt import EXTRA_RULES
from app.pipelines.ho_tro_mai_tang_huu_tri_xa_hoi.process.schema import (
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
    candidates = re.findall(r"(?:\d[ \t./\-]*){9,13}", str(text or ""))
    return any(
        re.sub(r"\D+", "", candidate) == identity
        for candidate in candidates
    )


def _matches_anchor(text: str, name: str, identity: str) -> bool:
    """Có đủ hai mỏ neo UI thì cùng một scope phải khớp cả hai."""
    name_matches = bool(name and name in _norm_text(text))
    identity_matches = bool(identity and _identity_occurs(identity, text))
    if name and identity:
        return name_matches and identity_matches
    return name_matches if name else identity_matches


def _owner_section(text: str) -> str:
    """Khoanh đúng mục II.2; người chết ở mục I không được tham gia đối chiếu."""
    start = re.search(
        r"(?mi)^\s*2\s*[.)]?\s*Trường hợp hộ gia đình,\s*cá nhân đứng ra mai táng",
        str(text or ""),
    )
    if not start:
        return ""
    tail = str(text)[start.start():]
    end = re.search(r"(?mi)^\s*Tôi xin cam đoan", tail)
    return (tail[:end.start()] if end else tail).strip()


def _death_declarant_section(text: str) -> str:
    """Chỉ lấy khối người đi khai tử, loại toàn bộ thông tin người chết phía trên."""
    start = re.search(
        r"(?mi)^\s*Họ\s*,?\s*chữ đệm\s*,?\s*tên người đi khai tử\s*:",
        str(text or ""),
    )
    if not start:
        return ""
    tail = str(text)[start.start():]
    end = re.search(
        r"(?mi)^\s*(?:NGƯỜI KÝ TRÍCH LỤC|NƠI NHẬN|NGƯỜI THỰC HIỆN)",
        tail,
    )
    return (tail[:end.start()] if end else tail).strip()


async def _requester_context(documents: list[dict], options: dict) -> str:
    """UI chỉ xác định vai trò; dữ liệu field vẫn phải đọc từ OCR đã khoanh."""
    form = (options or {}).get("formContext") or {}
    name = _norm_text(
        form.get("applicantFullname")
        or form.get("fullname")
        or ""
    )
    identity = re.sub(
        r"\D+",
        "",
        str(
            form.get("applicantIdentityNumber")
            or form.get("identityNumber")
            or ""
        ),
    )

    owner_scopes: list[tuple[int, str]] = []
    owner_support_scopes: list[tuple[int, str]] = []
    requester_scopes: list[tuple[int, str]] = []
    owner_matches = False

    for index, document in enumerate(documents, start=1):
        text = str(document.get("text") or "")
        owner = _owner_section(text)
        if owner:
            owner_scopes.append((index, owner))
            if (name or identity) and _matches_anchor(owner, name, identity):
                owner_matches = True
            continue

        declarant = _death_declarant_section(text)
        if declarant:
            # Khối này được đưa riêng để bổ sung giấy tờ cho đúng người; phần
            # người chết phía trên tuyệt đối không được chuyển cho LLM.
            owner_support_scopes.append((index, declarant))
            if (name or identity) and _matches_anchor(declarant, name, identity):
                requester_scopes.append((index, declarant))
            continue

        if (name or identity) and _matches_anchor(text, name, identity):
            requester_scopes.append((index, text[:5000]))

    owner_context = "\n".join(
        (
            f'<owner_ocr document="{index}">\n'
            "Đây là mục II.2 Mẫu số 04, nguồn bắt buộc cho ChuHoSo_*.\n"
            f"{scope}\n"
            "</owner_ocr>"
        )
        for index, scope in owner_scopes
    )
    owner_support_context = "\n".join(
        (
            f'<owner_support_ocr document="{index}">\n'
            "Đây chỉ là khối người đi khai tử. Chỉ bổ sung ChuHoSo_* khi khớp "
            "người tại owner_ocr; không tạo thêm vai trò.\n"
            f"{scope}\n"
            "</owner_support_ocr>"
        )
        for index, scope in owner_support_scopes
    )

    if not name and not identity:
        requester_context = (
            '<requester_context result="missing_ui_anchor">\n'
            "UI không có mỏ neo người nộp. Không trả NguoiNop_*; vẫn trích ChuHoSo_*.\n"
            "</requester_context>"
        )
    elif owner_matches:
        requester_context = (
            '<requester_context result="owner_match">\n'
            "Người nộp khớp chính mục II.2. Đây là tự nộp: chỉ trả ChuHoSo_*, "
            "không lặp NguoiNop_*.\n"
            "</requester_context>"
        )
    elif requester_scopes:
        matched = "\n".join(
            (
                f'<matched_requester_ocr document="{index}">\n'
                "Khối này khớp toàn bộ mỏ neo người nộp UI; trích NguoiNop_* "
                "từ chính OCR này.\n"
                f"{scope}\n"
                "</matched_requester_ocr>"
            )
            for index, scope in requester_scopes
        )
        requester_context = (
            '<requester_context result="document_match">\n'
            "Chỉ matched_requester_ocr mới được dùng cho NguoiNop_*.\n"
            "</requester_context>\n"
            + matched
        )
    else:
        requester_context = (
            '<requester_context result="no_document_match">\n'
            "Không tài liệu nào khớp toàn bộ mỏ neo UI. Không trả NguoiNop_*; "
            "vẫn trích ChuHoSo_*.\n"
            "</requester_context>"
        )

    parts = [requester_context]
    if owner_context:
        parts.append(owner_context)
    if owner_support_context:
        parts.append(owner_support_context)
    return "\n\n" + "\n".join(parts)


async def _owner_only_context(documents: list[dict], options: dict) -> str:
    """Mode owner_as_submitter: KHÔNG đưa mỏ neo UI vào prompt. Gắn result="missing_ui_anchor" để prompt
    sẵn có tự bỏ NguoiNop_* (mapper luôn lấy chủ hồ sơ làm người nộp); chỉ khoanh mục II.2 cho ChuHoSo_*."""
    _ = options
    owner_scopes = [
        (index, scope)
        for index, document in enumerate(documents, start=1)
        if (scope := _owner_section(str(document.get("text") or "")))
    ]
    requester_context = (
        '<requester_context result="missing_ui_anchor">\n'
        "Chế độ điền người nộp = chủ hồ sơ: KHÔNG dùng mỏ neo UI. Không trả NguoiNop_*; vẫn trích ChuHoSo_*.\n"
        "</requester_context>"
    )
    parts = [requester_context]
    if owner_scopes:
        parts.append("\n".join(
            (
                f'<owner_ocr document="{index}">\n'
                "Đây là mục II.2 Mẫu số 04, nguồn bắt buộc cho ChuHoSo_*.\n"
                f"{scope}\n"
                "</owner_ocr>"
            )
            for index, scope in owner_scopes
        ))
    return "\n\n" + "\n".join(parts)


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    # Toggle extension: "owner_as_submitter" bỏ mỏ neo UI; mapper LUÔN lấy chủ hồ sơ làm người nộp.
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

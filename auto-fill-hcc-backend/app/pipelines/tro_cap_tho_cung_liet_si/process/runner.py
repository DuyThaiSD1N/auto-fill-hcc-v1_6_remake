"""Compact-agent pipeline cho trợ cấp thờ cúng liệt sĩ."""

import re
import unicodedata

from app.pipelines._shared.compact_agent import runner
from app.pipelines.tro_cap_tho_cung_liet_si.process import mapper
from app.pipelines.tro_cap_tho_cung_liet_si.process.prompt import EXTRA_RULES
from app.pipelines.tro_cap_tho_cung_liet_si.process.schema import (
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


def _proposal_section(text: str) -> str:
    """Khoanh mục 1 Mẫu 18, không kéo bảng thân nhân vào vai trò chủ hồ sơ."""
    start = re.search(
        r"(?mi)^\s*1\s*[.)]\s*Thông tin người đề nghị\b",
        str(text or ""),
    )
    if not start:
        return ""
    tail = str(text)[start.start():]
    end = re.search(
        r"(?mi)^\s*2\s*[.)]\s*Thông tin về thân nhân liệt sĩ\b",
        tail,
    )
    return (tail[:end.start()] if end else tail).strip()


def _authorization_sections(text: str) -> list[str]:
    """Lấy riêng từng BÊN ĐƯỢC ỦY QUYỀN; loại bên ủy quyền và nội dung người khác."""
    raw = str(text or "")
    starts = list(re.finditer(r"(?mi)^\s*BÊN ĐƯỢC ỦY QUYỀN\s*:\s*", raw))
    sections: list[str] = []
    for start in starts:
        tail = raw[start.start():]
        end = re.search(r"(?mi)^\s*NỘI DUNG ỦY QUYỀN\s*:\s*", tail)
        section = (tail[:end.start()] if end else tail[:2500]).strip()
        if section and section not in sections:
            sections.append(section)
    return sections


async def _requester_context(documents: list[dict], options: dict) -> str:
    """UI chỉ dùng phân vai; dữ liệu output vẫn bắt buộc có trong OCR."""
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

    proposal_scopes: list[tuple[int, str]] = []
    authorization_scopes: list[tuple[int, str]] = []
    requester_scopes: list[tuple[int, str]] = []
    owner_matches = False

    for index, document in enumerate(documents, start=1):
        text = str(document.get("text") or "")
        proposal = _proposal_section(text)
        authorizations = _authorization_sections(text)

        if proposal:
            proposal_scopes.append((index, proposal))
            if (name or identity) and _matches_anchor(proposal, name, identity):
                owner_matches = True

        for authorization in authorizations:
            authorization_scopes.append((index, authorization))
            if (name or identity) and _matches_anchor(authorization, name, identity):
                owner_matches = True

        # Tài liệu chứa Mẫu 18/ủy quyền còn có liệt sĩ, thân nhân, bên ủy
        # quyền và người chết. Không quét toàn văn tài liệu đó làm người nộp.
        if proposal or authorizations:
            continue
        if (name or identity) and _matches_anchor(text, name, identity):
            requester_scopes.append((index, text[:5000]))

    proposal_context = "\n".join(
        (
            f'<owner_proposal_ocr document="{index}">\n'
            "Đây là mục 1 Mẫu 18, nguồn xác định ChuHoSo_* và dữ liệu nghiệp vụ.\n"
            f"{scope}\n"
            "</owner_proposal_ocr>"
        )
        for index, scope in proposal_scopes
    )
    authorization_context = "\n".join(
        (
            f'<owner_authorization_ocr document="{index}">\n'
            "Đây chỉ là BÊN ĐƯỢC ỦY QUYỀN; dùng bổ sung ChuHoSo_* khi tương ứng người đề nghị.\n"
            f"{scope}\n"
            "</owner_authorization_ocr>"
        )
        for index, scope in authorization_scopes
    )

    if not name and not identity:
        requester_context = (
            '<requester_context result="missing_ui_anchor">\n'
            "UI không có mỏ neo người nộp. Không trả NguoiNop_*; vẫn trích ChuHoSo_* và Mẫu 18.\n"
            "</requester_context>"
        )
    elif owner_matches:
        requester_context = (
            '<requester_context result="owner_match">\n'
            "Người nộp khớp người đề nghị/BÊN ĐƯỢC ỦY QUYỀN. Đây là tự nộp: "
            "chỉ trả ChuHoSo_*, không lặp NguoiNop_*.\n"
            "</requester_context>"
        )
    elif requester_scopes:
        matched = "\n".join(
            (
                f'<matched_requester_ocr document="{index}">\n'
                "Tài liệu này khớp toàn bộ mỏ neo UI; chỉ từ đây mới trích NguoiNop_*.\n"
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
            "vẫn trích ChuHoSo_* và Mẫu 18.\n"
            "</requester_context>"
        )

    parts = [requester_context]
    if proposal_context:
        parts.append(proposal_context)
    if authorization_context:
        parts.append(authorization_context)
    return "\n\n" + "\n".join(parts)


async def _owner_only_context(documents: list[dict], options: dict) -> str:
    """Mode owner_as_submitter: KHÔNG dùng mỏ neo UI (gắn missing_ui_anchor để prompt tự bỏ NguoiNop);
    vẫn khoanh mục 1 Mẫu 18 + BÊN ĐƯỢC ỦY QUYỀN cho ChuHoSo_* và Mẫu 18."""
    _ = options
    proposal_scopes: list[tuple[int, str]] = []
    authorization_scopes: list[tuple[int, str]] = []
    for index, document in enumerate(documents, start=1):
        text = str(document.get("text") or "")
        if proposal := _proposal_section(text):
            proposal_scopes.append((index, proposal))
        for authorization in _authorization_sections(text):
            authorization_scopes.append((index, authorization))

    parts = [
        '<requester_context result="missing_ui_anchor">\n'
        "Chế độ điền người nộp = chủ hồ sơ: KHÔNG dùng mỏ neo UI. Không trả NguoiNop_*; vẫn trích "
        "ChuHoSo_* và Mẫu 18.\n"
        "</requester_context>"
    ]
    if proposal_scopes:
        parts.append("\n".join(
            (
                f'<owner_proposal_ocr document="{index}">\n'
                "Đây là mục 1 Mẫu 18, nguồn xác định ChuHoSo_* và dữ liệu nghiệp vụ.\n"
                f"{scope}\n"
                "</owner_proposal_ocr>"
            )
            for index, scope in proposal_scopes
        ))
    if authorization_scopes:
        parts.append("\n".join(
            (
                f'<owner_authorization_ocr document="{index}">\n'
                "Đây chỉ là BÊN ĐƯỢC ỦY QUYỀN; dùng bổ sung ChuHoSo_* khi tương ứng người đề nghị.\n"
                f"{scope}\n"
                "</owner_authorization_ocr>"
            )
            for index, scope in authorization_scopes
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

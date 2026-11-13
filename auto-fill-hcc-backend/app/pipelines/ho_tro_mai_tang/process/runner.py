"""Compact-agent pipeline cho thủ tục hỗ trợ chi phí mai táng."""

import re
import unicodedata

from app.pipelines._shared.area_remap import is_current_area
from app.pipelines._shared.compact_agent import runner
from app.pipelines.ho_tro_mai_tang.process import mapper
from app.pipelines.ho_tro_mai_tang.process.prompt import EXTRA_RULES, REQUESTER_OWNER_RULES
from app.pipelines.ho_tro_mai_tang.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
    REQUESTER_OWNER_FIELDS,
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
    name_matches = bool(name and name in _norm_text(text))
    identity_matches = bool(identity and _identity_occurs(identity, text))
    if name and identity:
        return name_matches and identity_matches
    return name_matches if name else identity_matches


def _owner_section(text: str) -> str:
    """Khoanh khối người đứng ra mai táng: mục II.2 Mẫu số 04 hoặc mục 3.1 Mẫu số 02/03.

    Người chết (mục I Mẫu 04, mục 2 Mẫu 02/03) không được tham gia đối chiếu người nộp.
    """
    start = re.search(
        r"(?mi)^\s*(?:2\s*[.)]?\s*Trường hợp hộ gia đình,\s*cá nhân đứng ra mai táng"
        r"|3\s*\.\s*1\s*[.)]?\s*Trường hợp cá nhân,\s*thân nhân đứng ra tổ chức mai táng)",
        str(text or ""),
    )
    if not start:
        return ""
    tail = str(text)[start.start():]
    end = re.search(r"(?mi)^\s*(?:Tôi (?:xin )?cam đoan|3\s*\.\s*2\s*[.)]?\s*Trường hợp cơ quan)", tail)
    return (tail[:end.start()] if end else tail).strip()


def _proposer_section(text: str) -> str:
    """Khoanh mục 1 "Thông tin người đề nghị (người khai)" Mẫu số 02/03, dừng trước mục 2 người chết."""
    start = re.search(
        r"(?mi)^\s*1\s*[.)]?\s*Thông tin người\s+(?:người\s+)?đề nghị",
        str(text or ""),
    )
    if not start:
        return ""
    tail = str(text)[start.start():]
    end = re.search(r"(?mi)^\s*2\s*[.)]?\s*Thông tin người chết", tail)
    return (tail[:end.start()] if end else tail).strip()


def _owner_scope(text: str, options: dict | None) -> str:
    """Cờ requesterAsOwner (phường Nha Trang, phường Tiên Du): chủ hồ sơ = người đề nghị nên ghép mục 1 trước khối người đứng
    ra mai táng (mục 3.1 cùng người còn bổ sung ngày sinh, giới tính, số điện thoại)."""
    owner = _owner_section(text)
    if not mapper.is_requester_owner(options):
        return owner
    return "\n".join(part for part in (_proposer_section(text), owner) if part)


_AREA_PREFIX_RE = re.compile(r"^(?:tinh|thanh pho|tp|phuong|xa|thi tran|dac khu)\s+")


def _keep_proposer_area(fields: list[dict], ocr_text: str) -> list[str]:
    """Cờ requesterAsOwner: tỉnh/xã chủ hồ sơ phải nằm trên dòng "Nơi cư trú" mục 1. LLM hay lấy tỉnh/xã mục
    3.1 khi mục 1 đọc lỗi; tỉnh sai trông như dữ liệu thật nên bỏ trống cho cán bộ chọn (giữ chi tiết dưới xã)."""
    match = re.search(r"(?mi)^\s*Nơi cư trú\s*:?(.*)$", _proposer_section(ocr_text))
    if not match:
        return []
    line = _norm_text(match.group(1))

    def mentioned(name: str) -> bool:
        key = _AREA_PREFIX_RE.sub("", _norm_text(name)).strip()
        return bool(key) and f" {key} " in f" {line} "

    for field in fields:
        value = field.get("value")
        if field.get("name") != "ChuHoSo_NoiCuTru" or not isinstance(value, dict):
            continue
        xa = str(value.get("xa") or "")
        tinh = str(value.get("tinh") or "")
        xa_ok = not xa or mentioned(xa)
        # Tỉnh suy đúng từ xã có trên dòng mục 1 (cặp tỉnh-xã hiện hành) thì giữ.
        tinh_ok = not tinh or mentioned(tinh) or bool(xa and xa_ok and is_current_area(tinh, xa))
        if xa_ok and tinh_ok:
            return []
        field["value"] = {**value, "xa": xa if xa_ok else "", "tinh": tinh if tinh_ok else ""}
        return ["Tỉnh/phường nơi cư trú của người đề nghị không khớp dòng Nơi cư trú mục 1 tờ khai; để trống cho cán bộ chọn."]
    return []


def _owner_note(options: dict | None) -> str:
    if mapper.is_requester_owner(options):
        return (
            "Đây là khối người đề nghị (mục 1) và người đứng ra mai táng (mục 3.1), nguồn bắt buộc cho "
            "ChuHoSo_*; mục 1 là nguồn chính.\n"
        )
    return "Đây là khối người đứng ra mai táng, nguồn bắt buộc cho ChuHoSo_*.\n"


async def _requester_context(documents: list[dict], options: dict) -> str:
    """UI chỉ dùng để xác định vai trò; dữ liệu field vẫn phải đọc từ OCR."""
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
    requester_scopes: list[tuple[int, str]] = []
    owner_matches = False

    for index, document in enumerate(documents, start=1):
        text = str(document.get("text") or "")
        owner = _owner_scope(text, options)
        if owner:
            owner_scopes.append((index, owner))
            if (name or identity) and _matches_anchor(owner, name, identity):
                owner_matches = True
            # Không quét toàn bộ tờ khai làm người nộp: phần người chết và
            # cuối trang còn có cán bộ/chữ ký, rất dễ gán sai vai trò.
            continue
        if (name or identity) and _matches_anchor(text, name, identity):
            requester_scopes.append((index, text[:5000]))

    owner_context = ""
    if owner_scopes:
        owner_context = "\n".join(
            (
                f'<owner_ocr document="{index}">\n'
                f"{_owner_note(options)}"
                f"{scope}\n"
                "</owner_ocr>"
            )
            for index, scope in owner_scopes
        )

    if not name and not identity:
        requester_context = (
            '<requester_context result="missing_ui_anchor">\n'
            "UI không có mỏ neo người nộp. Không trả NguoiNop_*; vẫn trích NguoiMat_* và ChuHoSo_*.\n"
            "</requester_context>"
        )
    elif owner_matches:
        requester_context = (
            '<requester_context result="owner_match">\n'
            "Người nộp khớp chính người đứng ra mai táng: chỉ trả ChuHoSo_*, "
            "không lặp NguoiNop_*.\n"
            "</requester_context>"
        )
    elif requester_scopes:
        matched = "\n".join(
            (
                f'<matched_requester_ocr document="{index}">\n'
                "Tài liệu này đã khớp toàn bộ mỏ neo người nộp UI; trích NguoiNop_* từ OCR này.\n"
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
            "vẫn trích NguoiMat_* và ChuHoSo_*.\n"
            "</requester_context>"
        )

    return "\n\n" + requester_context + ("\n" + owner_context if owner_context else "")


async def _owner_only_context(documents: list[dict], options: dict) -> str:
    """Mode owner_as_submitter (Nghĩa Hưng): KHÔNG đưa mỏ neo UI vào prompt. Gắn result="missing_ui_anchor"
    để prompt sẵn có tự bỏ NguoiNop_* (mapper lấy người đứng ra mai táng làm người nộp); chỉ khoanh khối
    người đứng ra mai táng cho ChuHoSo_*."""
    owner_scopes = [
        (index, scope)
        for index, document in enumerate(documents, start=1)
        if (scope := _owner_scope(str(document.get("text") or ""), options))
    ]
    requester_context = (
        '<requester_context result="missing_ui_anchor">\n'
        "Chế độ điền người nộp = người đứng ra mai táng: KHÔNG dùng mỏ neo UI. Không trả NguoiNop_*; vẫn trích NguoiMat_* và ChuHoSo_*.\n"
        "</requester_context>"
    )
    parts = [requester_context]
    if owner_scopes:
        parts.append("\n".join(
            (
                f'<owner_ocr document="{index}">\n'
                f"{_owner_note(options)}"
                f"{scope}\n"
                "</owner_ocr>"
            )
            for index, scope in owner_scopes
        ))
    return "\n\n" + "\n".join(parts)


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    # Toggle extension: "owner_as_submitter" bỏ mỏ neo UI; mapper lấy người đứng ra mai táng làm người nộp.
    owner_mode = str((options or {}).get("submitterMode") or "") == "owner_as_submitter"
    # Cờ theo tài khoản (phường Nha Trang, phường Tiên Du): ChuHoSo_* = người đề nghị và là chủ hồ sơ trên cổng.
    requester_owner = mapper.is_requester_owner(options)
    res = await runner.run(
        files_by_role,
        fields=REQUESTER_OWNER_FIELDS if requester_owner else FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES + (REQUESTER_OWNER_RULES if requester_owner else ""),
        options=options,
        context_builder=_owner_only_context if owner_mode else _requester_context,
    )
    area_warnings = _keep_proposer_area(res["fields"], res.get("ocr_text") or "") if requester_owner else []
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    warnings = area_warnings + warnings
    if owner_mode:
        # Họ tên + CCCD Phần I cổng khoá (disabled) theo tài khoản VNeID; người nộp theo tờ khai có thể là người
        # khác nên kèm enableInput để extension bỏ disabled trước khi ghi, cán bộ còn sửa được khi OCR sai.
        for field in mapped_fields:
            if field.get("name") in ("data[fullname]", "data[identityNumber]") and field.get("occurrence") in (None, 0):
                field["enableInput"] = True
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res

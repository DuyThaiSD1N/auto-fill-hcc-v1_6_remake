"""Compact agent process pipeline for "Xác định mức độ khuyết tật"."""

import asyncio
import re
import unicodedata

from app.pipelines._shared.compact_agent import runner
from app.pipelines.khuyet_tat.process import mapper, vision
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


_SECTION_I_RE = re.compile(
    r"\bi\s*[.)]\s*thong tin nguoi duoc xac dinh(.*?)(?:\bii\s*[.)]\s*thong tin nguoi dai dien|$)", re.S
)
_SECTION_I_IDENTITY_RE = re.compile(
    r"(?:cmnd|can cuoc|cccd|dinh danh)[^:\n]{0,40}:[ \t]*((?:\d[ .]?){8,11}\d)"
)


def section_i_identity(ocr_text: str) -> str:
    """Số CMND/CCCD ghi ở mục I Mẫu số 01 (người được xác định mức độ khuyết tật).

    Chỉ là lưới đỡ khi LLM bỏ sót Nkt_SoDinhDanh dù OCR đọc rõ: chỉ tìm TRONG khối mục I (dừng ở tiêu đề
    mục II) nên không lấy nhầm số của người đại diện; số phải đủ 9 hoặc 12 chữ số.
    """
    text = str(ocr_text or "").replace("Đ", "D").replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn").lower()
    section = _SECTION_I_RE.search(text)
    if not section:
        return ""
    match = _SECTION_I_IDENTITY_RE.search(section.group(1))
    digits = re.sub(r"\D+", "", match.group(1)) if match else ""
    return digits if len(digits) in (9, 12) else ""


def fill_section_i_identity(res: dict) -> None:
    """Bù Nkt_SoDinhDanh từ mục I khi LLM không trả (mapper dùng nó cho cả khối người KT lẫn chủ hồ sơ)."""
    fields = res.get("fields") or []
    if any(f.get("name") == "Nkt_SoDinhDanh" and f.get("value") for f in fields):
        return
    identity = section_i_identity(res.get("ocr_text") or "")
    if identity:
        res["fields"] = [f for f in fields if f.get("name") != "Nkt_SoDinhDanh"] + [
            {"name": "Nkt_SoDinhDanh", "comp": "x-input", "value": identity}
        ]


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


async def _owner_only_context(documents: list[dict], options: dict) -> str:
    """Chế độ THEO TỜ KHAI: không đưa mỏ neo tài khoản vào prompt; mapper lấy người nộp từ mục II."""
    _ = documents, options
    return (
        '\n\n<requester_context result="missing_ui_anchor">\n'
        "Chế độ người nộp theo tờ khai: KHÔNG dùng mỏ neo UI. Không trả NguoiNop_*; vẫn trích ChuHoSo_*, "
        "Nkt_* và đủ Ndd_*.\n"
        "</requester_context>"
    )


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    owner_mode = str((options or {}).get("submitterMode") or "") == "owner_as_submitter"
    # Mục III đọc thẳng từ ảnh song song với OCR + LLM; luôn chờ cả hai xong.
    res, section_iii = await asyncio.gather(runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        context_builder=_owner_only_context if owner_mode else _requester_context,
        max_tokens=2200,
    ), vision.read_section_iii(runner.flatten(files_by_role)))
    if section_iii is not None:
        # Bảng tích ✓ viết tay: kết quả đọc ảnh thay hẳn phần LLM bóc từ OCR văn bản (kể cả khi rỗng).
        res["fields"] = [f for f in res["fields"] if f.get("name") not in section_iii] + [
            {"name": name, "comp": "raw", "value": value} for name, value in section_iii.items()
        ]
    fill_section_i_identity(res)
    res["fields"] = mapper.enrich(res["fields"], options)
    return res

"""Compact agent pipeline for "Đăng ký khai tử"."""

import re
import unicodedata

from app.pipelines._shared.compact_agent import runner
from app.pipelines.khai_tu.process import mapper, reason
from app.pipelines.khai_tu.process.prompt import EXTRA_RULES
from app.pipelines.khai_tu.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

_LEGACY_DECEASED_FIELD_NAMES = {
    "Gbt_HoTenNguoiMat": "NguoiMat_HoTen",
    "Gbt_NgaySinhNguoiMat": "NguoiMat_NgaySinh",
    "Gbt_GioiTinhNguoiMat": "NguoiMat_GioiTinh",
    "Gbt_DanTocNguoiMat": "NguoiMat_DanToc",
    "Gbt_QuocTichNguoiMat": "NguoiMat_QuocTich",
    "Gbt_SoDinhDanhNguoiMat": "NguoiMat_SoDinhDanh",
    "Gbt_NgayCapDDNguoiMat": "NguoiMat_NgayCapGiayTo",
    "Gbt_NoiCapDDNguoiMat": "NguoiMat_NoiCapGiayTo",
    "Gbt_NoiCuTruNguoiMat": "NguoiMat_NoiCuTruCuoiCung",
    "Gbt_NgayMat": "NguoiMat_NgayMat",
    "Gbt_GioMat": "NguoiMat_GioMat",
    "Gbt_NguyenNhanMat": "NguoiMat_NguyenNhanMat",
    "Gbt_NoiChet": "NguoiMat_NoiChet",
}

_GBT_METADATA_FIELDS = ("Gbt_So", "Gbt_CoQuanCap", "Gbt_NgayCap")
_PAGE_MARKER_RE = re.compile(r"(?im)^.*\btrang\s+\d+\s*/\s*\d+\b.*$")
_DECLARATION_TITLE_RE = re.compile(r"(?im)^\s*to khai dang ky khai tu\s*$")
_DEATH_NOTICE_TITLE_RE = re.compile(r"(?im)^\s*giay bao tu\s*$")


def _source_fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("Đ", "D").replace("đ", "d").lower()


def _source_pages(text: str) -> list[str]:
    """Tách trang để tiêu đề TRÍCH LỤC ở trang sau không làm nhiễu TỜ KHAI trang trước."""
    folded = _source_fold(text)
    pages = [part.strip() for part in _PAGE_MARKER_RE.split(folded) if part.strip()]
    return pages or ([folded.strip()] if folded.strip() else [])


def _declaration_gbt_segment(page: str) -> str:
    """Chỉ lấy đoạn đúng mục Giấy báo tử trên Tờ khai, không lấy metadata tài liệu khác cùng PDF."""
    if not _DECLARATION_TITLE_RE.search(page):
        return ""
    start_match = re.search(r"so\s+giay\s+bao\s+tu\s*/\s*giay\s+to\s+thay\s+the", page)
    if not start_match:
        return ""
    end = len(page)
    for marker in ("toi cam doan", "de nghi cap ban sao", "lam tai"):
        marker_pos = page.find(marker, start_match.end())
        if marker_pos >= 0:
            end = min(end, marker_pos)
    return page[start_match.start():end].strip()


def _allowed_gbt_evidence(documents: list[dict]) -> list[str]:
    """Nguồn hợp lệ của Gbt_*: đúng mục trên Tờ khai hoặc trang có tiêu đề GIẤY BÁO TỬ.

    TRÍCH LỤC KHAI TỬ không có tiêu đề chính xác này nên không bao giờ trở thành evidence.
    """
    evidence: list[str] = []
    for document in documents or []:
        for page in _source_pages(document.get("text") or ""):
            declaration_segment = _declaration_gbt_segment(page)
            if declaration_segment:
                evidence.append(declaration_segment)
            if _DEATH_NOTICE_TITLE_RE.search(page):
                evidence.append(page)
    return evidence


def _compact_source(value) -> str:
    folded = _source_fold(value)
    folded = re.sub(r"\buy\s+ban\s+nhan\s+dan\b", "ubnd", folded)
    return re.sub(r"[^a-z0-9]+", "", folded)


def _number_supported(value, evidence: list[str]) -> bool:
    raw = str(value or "").strip()
    compact = _compact_source(raw)
    if not compact:
        return False
    if not compact.isdigit():
        return any(compact in _compact_source(source) for source in evidence)
    number = str(int(compact)) if int(compact) else "0"
    return any(
        re.search(rf"(?<!\d)0*{re.escape(number)}(?!\d)", source)
        for source in evidence
    )


def _date_supported(value, evidence: list[str]) -> bool:
    match = re.search(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b", str(value or ""))
    if not match:
        return False
    day, month, year = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    pattern = re.compile(
        rf"(?<!\d)0?{day}(?:\s*[/\-.]\s*|\s+thang\s+)0?{month}"
        rf"(?:\s*[/\-.]\s*|\s+nam\s+){year}(?!\d)"
    )
    return any(pattern.search(source) for source in evidence)


def _agency_supported(value, evidence: list[str]) -> bool:
    compact = _compact_source(value)
    return bool(compact) and any(compact in _compact_source(source) for source in evidence)


def _filter_gbt_metadata(canonical: dict, documents: list[dict]) -> dict:
    """Loại metadata chỉ xuất hiện ở Trích lục khai tử trước khi mapper có thể điền nhầm UI."""
    if not documents:
        return canonical
    evidence = _allowed_gbt_evidence(documents)
    validators = {
        "Gbt_So": _number_supported,
        "Gbt_CoQuanCap": _agency_supported,
        "Gbt_NgayCap": _date_supported,
    }
    for name in _GBT_METADATA_FIELDS:
        value = canonical.get(name)
        if value not in (None, "") and not validators[name](value, evidence):
            canonical.pop(name, None)
    return canonical


def _canonicalize_deceased_fields(raw_fields, documents):
    """Chuyển output compact cũ trước validation; tên mới luôn được ưu tiên.

    Chỉ tương thích cục bộ cho khai tử, không đưa tên cũ trở lại schema/prompt
    vì hai bộ tên cùng xuất hiện sẽ làm model tiếp tục lẫn Gbt với người mất.
    """
    if isinstance(raw_fields, dict):
        items = raw_fields.items()
    elif isinstance(raw_fields, list):
        items = (
            (field.get("name"), field.get("value"))
            for field in raw_fields
            if isinstance(field, dict)
        )
    else:
        return raw_fields

    canonical: dict = {}
    legacy: list[tuple[str, object]] = []
    for name, value in items:
        if name in _LEGACY_DECEASED_FIELD_NAMES:
            legacy.append((_LEGACY_DECEASED_FIELD_NAMES[name], value))
        elif name:
            canonical[name] = value
    for name, value in legacy:
        canonical.setdefault(name, value)
    return _filter_gbt_metadata(canonical, documents)


def _requester_hint(options: dict) -> str:
    """Mỏ neo người yêu cầu cổng đã điền sẵn (VNeID) → giúp LLM tách CCCD người yêu cầu vs người mất."""
    ctx = (options or {}).get("formContext") or {}
    name = str(ctx.get("applicantFullname") or "").strip()
    idnum = str(ctx.get("applicantIdentityNumber") or "").strip()
    if not name and not idnum:
        return ""
    return (
        "\n\n<requester_context>\n"
        f'NGƯỜI YÊU CẦU đã đăng nhập (cổng điền sẵn từ VNeID): họ tên="{name}", số định danh="{idnum}".\n'
        "Đây chỉ là mỏ neo phân vai; không phải nguồn dữ liệu giấy tờ và không thay <source_authority>.\n"
        "</requester_context>"
    )


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=_requester_hint(options) + EXTRA_RULES,
        options=options,
        context_builder=reason.build_context,
        compact_field_fallback=_canonicalize_deceased_fields,
    )
    reasoning_context = res.get("reasoning_context") or ""
    res["fields"] = reason.sanitize_identity_fields(
        res["fields"],
        reasoning_context,
    )
    res["fields"] = mapper.enrich(
        res["fields"],
        options,
        reasoning_context=reasoning_context,
    )

    # Rà soát bbox (Kiểu A): chỉ chạy khi router bật cờ _review (thủ tục có "review": True).
    if (options or {}).get("_review"):
        from app.review import capture
        from app.pipelines.khai_tu.process.schema import REVIEW_FIELDS
        try:
            cap = await capture.capture(files_by_role, res["fields"], review_names=REVIEW_FIELDS)
            if cap:
                res["_review"] = cap
        except Exception as e:  # noqa: BLE001
            res.setdefault("errors", []).append(f"review: {e}")
    return res

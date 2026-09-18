"""Compact agent pipeline for "Đăng ký khai tử"."""

import re
import unicodedata

from app.pipelines._shared.compact_agent import runner
from app.pipelines.khai_tu.process import declaration, mapper, reason
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
    """Mỏ neo tài khoản cổng (VNeID) → giúp LLM tách CCCD người yêu cầu vs người mất.

    Tài khoản đăng nhập CÓ THỂ là người nộp thay/cán bộ tiếp nhận, nên đây chỉ là mỏ neo hạng hai:
    có tờ khai thì người đứng đơn trên tờ khai mới là người yêu cầu.
    """
    ctx = (options or {}).get("formContext") or {}
    name = str(ctx.get("applicantFullname") or "").strip()
    idnum = str(ctx.get("applicantIdentityNumber") or "").strip()
    if not name and not idnum:
        return ""
    return (
        "\n\n<requester_context>\n"
        f'TÀI KHOẢN NỘP HỒ SƠ trên cổng (VNeID điền sẵn): họ tên="{name}", số định danh="{idnum}".\n'
        "Đây CHƯA CHẮC là người yêu cầu: có thể là người nộp thay hoặc cán bộ tiếp nhận.\n"
        "- Hồ sơ CÓ TỜ KHAI ĐĂNG KÝ KHAI TỬ: người ghi tại nhãn 'Họ, chữ đệm, tên người yêu cầu' mới là\n"
        "  NGƯỜI YÊU CẦU. Vẫn phải xuất đủ NguoiYeuCau_* từ tờ khai DÙ lệch hoàn toàn tài khoản này.\n"
        "  Lệch tài khoản KHÔNG phải lý do bỏ trống field người yêu cầu.\n"
        "- Hồ sơ KHÔNG có tờ khai: mới dùng tài khoản này làm mỏ neo nhận diện thẻ của người yêu cầu.\n"
        "Đây là mỏ neo phân vai; không phải nguồn dữ liệu giấy tờ và không thay <source_authority>.\n"
        "</requester_context>"
    )


async def extract(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    """OCR + agent trích compact facts khai tử, đã phân vai và bù từ tờ khai; CHƯA map sang UI.

    Tách khỏi `run` để biểu mẫu khác của cùng bộ giấy tờ (liên thông khai tử trên
    lienthong.dichvucong.gov.vn) dùng lại nguyên phần trích xuất, chỉ thay mapper.
    """
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
    # Đưa hai khối thẻ về đúng vai TRƯỚC khi sanitize, nếu không cụm bị gán ngược sẽ bị xóa
    # thay vì được trả về đúng người.
    res["fields"] = reason.enforce_role_assignment(res["fields"], reasoning_context)
    res["fields"] = reason.sanitize_identity_fields(
        res["fields"],
        reasoning_context,
    )
    # Agent hay dồn dữ kiện người yêu cầu của tờ khai vào Cccd_* rồi bỏ trống NguoiYeuCau_*,
    # khiến mapper rơi xuống dữ liệu VNeID của tài khoản đăng nhập. Tờ khai là biểu mẫu chuẩn
    # nên đọc lại khối đó tất định và bù các ô còn thiếu.
    res["fields"] = declaration.fill_missing(
        res["fields"],
        res.get("ocr_text") or "",
        COMPACT_COMP_BY_NAME,
    )
    return res


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await extract(files_by_role, options)
    res["fields"] = mapper.enrich(
        res["fields"],
        options,
        reasoning_context=res.get("reasoning_context") or "",
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

"""Compact agent process pipeline for regular birth registration."""

import re

from app.pipelines._shared.compact_agent import runner
from app.pipelines._shared.compact_agent.issuer import (
    ISSUER_BO_CONG_AN,
    ISSUER_CUC,
    _fold,
    default_issuer,
    normalize_issuer,
)
from app.pipelines.khai_sinh_thuong.process import mapper
from app.pipelines.khai_sinh_thuong.process.prompt import EXTRA_RULES
from app.pipelines.khai_sinh_thuong.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

# CCCD cha + mẹ hay scan chung một file (trang 1 hai mặt trước, trang 2 hai mặt sau). Mặt sau không
# in họ tên nên LLM gán nhầm ngày/nơi cấp của thẻ này cho người kia. MRZ cuối mặt sau
# ("IDVNM<9 số thẻ><check><12 số định danh>...") nhúng số định danh → cắt OCR theo từng dòng MRZ:
# phần chữ giữa MRZ trước (hoặc đầu trang) và MRZ này là mặt sau của thẻ đó. Chỉ sửa khi đoạn mặt
# sau có đúng MỘT ngày cấp; thẻ không có MRZ (CMND 9 số, OCR mất MRZ) giữ nguyên kết quả LLM.
_ID_ISSUE_GROUPS = [
    ("CccdNam_SoDinhDanh", "CccdNam_NgayCap", "CccdNam_NoiCap"),
    ("CccdNu_SoDinhDanh", "CccdNu_NgayCap", "CccdNu_NoiCap"),
    ("CccdChuThe_SoDinhDanh", "CccdChuThe_NgayCap", "CccdChuThe_NoiCap"),
]
_MRZ_LINE1_RE = re.compile(r"IDVNM[0-9O<\s]{10,}", re.IGNORECASE)
# Dòng MRZ 2/3: chỉ gồm chữ HOA, số, "<" và có ít nhất một "<".
_MRZ_TAIL_RE = re.compile(r"^[A-Z0-9<\s]+$")
_SEGMENT_BREAK_RE = re.compile(r"^\s*(─{3,}.*trang|={3,}|-{3,}\s*$)", re.IGNORECASE)
_DATE = r"(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})"
# Nhãn ngày cấp trên mặt sau (đã _fold):
#  - Căn cước mới: "Ngày, tháng, năm cấp / Date of issue: dd/mm/yyyy"
#  - CCCD chip cũ: "Ngày, tháng, năm / Date, month, year: dd/mm/yyyy"
# KHÔNG khớp "ngày, tháng, năm sinh" hay "ngày, tháng, năm hết hạn".
_ISSUE_DATE_RES = (
    re.compile(r"ngay,?\s*thang,?\s*nam\s*cap\b[^0-9]{0,40}?" + _DATE),
    re.compile(r"date\s*of\s*issue[^0-9]{0,20}?" + _DATE),
    re.compile(r"ngay,?\s*thang,?\s*nam\s*/\s*date,?\s*month,?\s*year[^0-9]{0,10}?" + _DATE),
)


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _issue_date_hits(segment: str) -> dict[int, str]:
    """{vị trí ngày trong chuỗi đã fold: dd/mm/yyyy}. Khoá theo vị trí để một nhãn song ngữ khớp
    nhiều regex vẫn chỉ tính một lần."""
    folded = _fold(segment)
    hits: dict[int, str] = {}
    for rx in _ISSUE_DATE_RES:
        for m in rx.finditer(folded):
            date = _norm_date(m.group(1), m.group(2), m.group(3))
            if date:
                hits[m.start(1)] = date
    return hits


def _norm_date(day, month, year) -> str:
    day, month, year = int(day), int(month), int(year)
    if 1 <= day <= 31 and 1 <= month <= 12:
        return f"{day:02d}/{month:02d}/{year}"
    return ""


def _norm_value_date(value) -> str:
    m = re.match(r"^\s*" + _DATE + r"\s*$", str(value or ""))
    return _norm_date(*m.groups()) if m else ""


def _issuer(segment: str) -> str:
    iss = normalize_issuer(segment)
    return iss if iss in (ISSUER_CUC, ISSUER_BO_CONG_AN) else ""


def _parse_backs(text: str) -> list[dict]:
    """Mỗi mặt sau có MRZ → {"mrz_digits", "ngay_cap", "noi_cap"}; ngay_cap rỗng nếu không chắc."""
    backs: list[dict] = []
    buffer: list[str] = []
    in_mrz_tail = False
    for line in str(text or "").splitlines():
        stripped = line.strip()
        if in_mrz_tail and stripped and "<" in stripped and _MRZ_TAIL_RE.match(stripped):
            continue
        in_mrz_tail = False
        m = _MRZ_LINE1_RE.search(stripped)
        if m:
            segment = "\n".join(buffer)
            dates = set(_issue_date_hits(segment).values())
            ngay_cap = next(iter(dates)) if len(dates) == 1 else ""
            backs.append({
                "mrz_digits": _digits(m.group(0).upper().replace("O", "0")),
                "ngay_cap": ngay_cap,
                "noi_cap": (_issuer(segment) or default_issuer(ngay_cap)) if ngay_cap else "",
            })
            buffer = []
            in_mrz_tail = True
            continue
        if _SEGMENT_BREAK_RE.match(stripped):
            buffer = []
            continue
        buffer.append(line)
    return backs


def _owner(backs: list[dict], id_num: str) -> dict | None:
    """Mặt sau có MRZ chứa đúng số định danh 12 chữ số này (chỉ nhận khi duy nhất)."""
    if len(id_num) != 12:
        return None
    hits = [b for b in backs if id_num in b["mrz_digits"]]
    return hits[0] if len(hits) == 1 else None


def _reassign_issue_by_mrz(fields: dict, groups: list[tuple[str, str, str]], text: str) -> dict:
    """Sửa ``fields`` tại chỗ theo MRZ. ``groups`` = [(key số định danh, key ngày cấp, key nơi cấp)].

    - Nhóm có mặt sau khớp MRZ → ghi đè ngày cấp + nơi cấp đọc từ chính mặt sau đó.
    - Nhóm KHÔNG có mặt sau khớp mà ngày cấp LLM trả trùng ngày cấp mặt sau của người khác → xoá
      (đó là ngày cấp mượn nhầm; để trống còn hơn điền sai). Chỉ xoá khi toàn bộ OCR không còn nhãn
      ngày cấp nào ngoài các mặt sau đã khớp — vợ chồng hay làm thẻ cùng ngày, mặt sau mất MRZ của
      người kia vẫn có thể mang đúng ngày đó.
    """
    backs = [b for b in _parse_backs(text) if b["ngay_cap"]]
    if not backs:
        return fields
    owned_dates: set[str] = set()
    owned_backs = 0
    orphans: list[tuple[str, str]] = []
    for id_key, date_key, issuer_key in groups:
        id_num = _digits(fields.get(id_key))
        if not id_num:
            continue
        back = _owner(backs, id_num)
        if back:
            fields[date_key] = back["ngay_cap"]
            fields[issuer_key] = back["noi_cap"]
            owned_dates.add(back["ngay_cap"])
            owned_backs += 1
        else:
            orphans.append((date_key, issuer_key))
    if len(_issue_date_hits(text)) > owned_backs:
        return fields
    for date_key, issuer_key in orphans:
        if _norm_value_date(fields.get(date_key)) in owned_dates:
            fields.pop(date_key, None)
            fields.pop(issuer_key, None)
    return fields


def _fix_issue_by_mrz(raw_fields, documents: list[dict]):
    if not isinstance(raw_fields, dict):
        return raw_fields
    text = "\n\n".join(str(d.get("text") or "") for d in documents or [])
    return _reassign_issue_by_mrz(dict(raw_fields), _ID_ISSUE_GROUPS, text)


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        compact_field_fallback=_fix_issue_by_mrz,
    )
    res["fields"] = mapper.enrich(res["fields"])
    return res

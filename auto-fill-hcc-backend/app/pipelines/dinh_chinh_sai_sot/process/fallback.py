"""OCR fallback extractors for land-certificate correction."""

import re

_SKIP_SERIAL_LINE_RE = re.compile(
    r"(s[ốo]\s*(vào|\.?\s*sổ)|so\s+vao\s+so|sổ\s+cấp\s+gcn|cmtnd|cmnd|cccd|hợp\s+đồng|quyển)",
    re.IGNORECASE,
)
_LABEL_SERIAL_RE = re.compile(r"\bS[ỐO0]\s*[:.]?\s*([A-Z]{1,3})\s*[-.]?\s*(\d{5,8})\b", re.IGNORECASE)
_COMPACT_LABEL_SERIAL_RE = re.compile(r"\bS[ỐO0]([A-Z]{1,3})\s*[-.]?\s*(\d{5,8})\b", re.IGNORECASE)
_PLAIN_SERIAL_RE = re.compile(r"\b([A-Z]{1,3})\s*[-.]?\s*(\d{5,8})\b", re.IGNORECASE)
_APPLICANT_IDENTITY_BLOCK_RE = re.compile(
    r"giấy\s+tờ\s+nhân\s+thân\s*/?\s*pháp\s+nhân",
    re.IGNORECASE,
)
_ISSUE_DATE_RE = re.compile(
    r"ngày\s+cấp\s*[:.]?\s*(\d{1,2})\s*[/.-]\s*(\d{1,2})\s*[/.-]\s*(\d{4})",
    re.IGNORECASE,
)

# Tương thích ngắn hạn với output tên field cũ trong lúc triển khai cuốn chiếu. Các tên này không còn
# xuất hiện trong schema/prompt mới nên không tiếp tục dẫn hướng LLM theo nguồn tài liệu CCCD.
_LEGACY_APPLICANT_FIELDS = {
    "Cccd_HoTen": "NguoiNop_HoTen",
    "Cccd_SoDinhDanh": "NguoiNop_SoDinhDanh",
    "Cccd_NgaySinh": "NguoiNop_NgaySinh",
    "Cccd_GioiTinh": "NguoiNop_GioiTinh",
    "Cccd_DanToc": "NguoiNop_DanToc",
    "Cccd_NgayCap": "NguoiNop_NgayCapGiayTo",
    "Cccd_NoiCap": "NguoiNop_NoiCapGiayTo",
    "Cccd_NoiCuTru": "NguoiNop_NoiCuTru",
    "Don_DienThoaiLienHe": "NguoiNop_DienThoai",
}


def _as_dict(raw_fields):
    if isinstance(raw_fields, dict):
        return dict(raw_fields)
    if isinstance(raw_fields, list):
        return {
            f.get("name"): f.get("value")
            for f in raw_fields
            if isinstance(f, dict) and f.get("name") and f.get("value") not in (None, "", {}, [])
        }
    return {}


def _normalize_serial(prefix: str, number: str) -> str | None:
    prefix = re.sub(r"[^A-Z]", "", (prefix or "").upper())
    number = re.sub(r"\D", "", number or "")
    if not prefix or not number:
        return None
    # OCR hay dính chữ "Số" vào serial: SOAN 276270 => AN 276270.
    if prefix.startswith("SO") and len(prefix) > 2:
        prefix = prefix[2:]
    elif prefix.startswith("S") and len(prefix) > 1:
        prefix = prefix[1:]
    if not 1 <= len(prefix) <= 3 or not 5 <= len(number) <= 8:
        return None
    return f"{prefix} {number}"


def extract_gcn_serial(text: str) -> str | None:
    """Extract cover serial from OCR text, avoiding "Số vào sổ cấp GCN"."""
    if not text:
        return None
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    candidates: list[tuple[int, str]] = []
    for idx, line in enumerate(lines):
        if _SKIP_SERIAL_LINE_RE.search(line):
            continue
        searchers = (_LABEL_SERIAL_RE, _COMPACT_LABEL_SERIAL_RE, _PLAIN_SERIAL_RE)
        for rx in searchers:
            match = rx.search(line.upper())
            if not match:
                continue
            serial = _normalize_serial(match.group(1), match.group(2))
            if not serial:
                continue
            # Số phát hành thường nằm trên bìa, gần đầu tài liệu.
            score = 0 if idx <= 35 else idx
            if idx and "GIẤY CHỨNG NHẬN" in "\n".join(lines[max(0, idx - 8):idx + 1]).upper():
                score -= 10
            candidates.append((score, serial))
            break

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def extract_applicant_identity_issue_date(text: str) -> str | None:
    """Lấy ngày cấp từ đúng khối giấy tờ nhân thân trên Đơn, không quét ngày trên GCN."""
    if not text:
        return None
    marker = _APPLICANT_IDENTITY_BLOCK_RE.search(text)
    if not marker:
        return None
    # Ngày cấp nằm cùng dòng hoặc ngay sau nhãn giấy tờ; giới hạn vùng để không bắt ngày ký đơn/GCN.
    block = text[marker.start():marker.start() + 700]
    match = _ISSUE_DATE_RE.search(block)
    if not match:
        return None
    day, month, year = (int(part) for part in match.groups())
    if not 1 <= day <= 31 or not 1 <= month <= 12:
        return None
    return f"{day:02d}/{month:02d}/{year:04d}"


def apply_ocr_fallback(raw_fields, documents: list[dict]) -> dict:
    fields = _as_dict(raw_fields)
    for old_name, new_name in _LEGACY_APPLICANT_FIELDS.items():
        if new_name not in fields and old_name in fields:
            fields[new_name] = fields[old_name]
        fields.pop(old_name, None)

    text = "\n".join(d.get("text") or "" for d in documents)
    if not fields.get("NguoiNop_NgayCapGiayTo"):
        issue_date = extract_applicant_identity_issue_date(text)
        if issue_date:
            fields["NguoiNop_NgayCapGiayTo"] = issue_date
    if not fields.get("Gcn_SoPhatHanh"):
        serial = extract_gcn_serial(text)
        if serial:
            fields["Gcn_SoPhatHanh"] = serial
    return fields

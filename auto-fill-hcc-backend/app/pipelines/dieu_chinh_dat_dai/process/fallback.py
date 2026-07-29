"""OCR fallback extractors for land-decision adjustment."""

import re

_SKIP_SERIAL_LINE_RE = re.compile(
    r"(s[ốo]\s*(vào|\.?\s*sổ)|so\s+vao\s+so|sổ\s+cấp\s+gcn|cmtnd|cmnd|cccd|hợp\s+đồng|quyển)",
    re.IGNORECASE,
)
_LABEL_SERIAL_RE = re.compile(r"\bS[ỐO0]\s*[:.]?\s*([A-Z]{1,3})\s*[-.]?\s*(\d{5,8})\b", re.IGNORECASE)
_COMPACT_LABEL_SERIAL_RE = re.compile(r"\bS[ỐO0]([A-Z]{1,3})\s*[-.]?\s*(\d{5,8})\b", re.IGNORECASE)
_PLAIN_SERIAL_RE = re.compile(r"\b([A-Z]{1,3})\s*[-.]?\s*(\d{5,8})\b", re.IGNORECASE)


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


def apply_ocr_fallback(raw_fields, documents: list[dict]) -> dict:
    fields = _as_dict(raw_fields)
    if not fields.get("Gcn_SoPhatHanh"):
        text = "\n".join(d.get("text") or "" for d in documents)
        serial = extract_gcn_serial(text)
        if serial:
            fields["Gcn_SoPhatHanh"] = serial
    return fields


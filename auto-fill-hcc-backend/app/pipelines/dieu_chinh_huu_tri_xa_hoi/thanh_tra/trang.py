"""Trang giấy của hồ sơ trợ cấp hưu trí xã hội và hạng nguồn của từng trang — phần mã dùng chung của các thanh tra.

Hồ sơ hay quét cả tập vào một tệp PDF nhiều trang nên đếm theo TRANG, không theo tệp. Hạng nguồn: giấy in do cơ quan cấp
(CCCD, giấy khai sinh / trích lục, giấy xác nhận cư trú) > văn bản đề nghị
Mẫu số 01 (viết tay) > giấy người dân tự lập (cam đoan, ủy quyền).
"""

import re

from app.pipelines._shared.thanh_tra.ho_so import fold
from app.pipelines.xac_nhan_tthn_dvc_moi.thanh_tra import dinh_danh as base

_DON = ("tro cap huu tri", "van ban de nghi", "tro cap xa hoi")
_AGENCY_MARKERS = ("can cuoc", "chung minh nhan dan", "identity card", "giay khai sinh", "trich luc khai sinh",
                   "so ho khau", "thong tin ve cu tru", "thong tin cu tru", "benh vien", "so y te", "trung tam y te",
                   "tram y te", "giay ra vien", "benh an", "phieu kham", "giam dinh y khoa")
_SELF_MADE_MARKERS = ("cam doan", "cam ket", "uy quyen", "bien ban")
_HEADER_LINES = 12

name_key = base._name_key
WORD_RE = base._WORD_RE


def pages(documents: list[dict]) -> list[dict]:
    """[{doc, lines, kind}] — kind: "don" (đơn đề nghị viết tay) | "ban_in" | "tu_lap". Trang quét trùng nguyên văn chỉ
    giữ một."""
    out, seen = [], set()
    for index, document in enumerate(documents, start=1):
        for text in base._PAGE_BREAK_RE.split(str(document.get("text") or "")):
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            body = "\n".join(lines)
            if not lines or body in seen:
                continue
            seen.add(body)
            head = " ".join(fold(line) for line in lines[:_HEADER_LINES])
            if any(marker in head for marker in _DON):
                kind = "don"
            elif any(m in head for m in _AGENCY_MARKERS) and not any(m in head for m in _SELF_MADE_MARKERS):
                kind = "ban_in"
            else:
                kind = "tu_lap"
            out.append({"doc": index, "lines": lines, "kind": kind})
    return out


def card_line(line: str) -> bool:
    """Dòng họ tên in hoa của thẻ (nhãn song ngữ): OCR hay rơi / lệch dấu ở chữ in hoa."""
    return "full name" in fold(line)


def words(value) -> str:
    return f" {' '.join(WORD_RE.findall(name_key(value)))} "


def support(name, page_list: list[dict]) -> dict:
    """Số TRANG ghi đúng nguyên văn cách viết họ tên này, theo hạng nguồn."""
    needle = words(name)
    out = {"trang": 0, "ban_in": 0, "the": 0, "tu_lap": 0, "don": 0}
    if not needle.strip():
        return out
    for page in page_list:
        hits = [line for line in page["lines"] if needle in words(line)]
        if not hits:
            continue
        out["trang"] += 1
        if page["kind"] == "ban_in" and all(card_line(line) for line in hits):
            out["the"] += 1
        else:
            out[page["kind"]] += 1
    return out


def rank(stat: dict) -> tuple:
    """Nhiều trang hơn trước; bằng nhau thì giấy in cơ quan cấp (kể cả thẻ) > đơn đề nghị > giấy tự lập."""
    return stat["trang"], stat["ban_in"] + stat["the"], stat["don"], stat["tu_lap"]


def digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))

"""Trang giấy của hồ sơ khai sinh kết hợp nhận cha, mẹ, con và hạng nguồn của từng trang — phần mã dùng chung của các
thanh tra.

Hồ sơ hay quét cả tập vào một tệp PDF nhiều trang nên đếm theo TRANG, không theo tệp. Hạng nguồn: giấy in do cơ quan cấp
(giấy chứng sinh, CCCD, hộ chiếu, giấy khai sinh, kết quả giám định ADN) > tờ khai (tờ khai đăng ký khai sinh, tờ khai
đăng ký nhận cha, mẹ, con — viết tay) > giấy người dân tự lập (cam đoan, thoả thuận, đơn).
"""

import re

from app.pipelines._shared.thanh_tra.ho_so import fold
from app.pipelines.xac_nhan_tthn_dvc_moi.thanh_tra import dinh_danh as base

_TO_KHAI = ("to khai dang ky khai sinh", "to khai dang ky nhan cha", "to khai dang ki nhan cha")
_AGENCY_MARKERS = ("giay chung sinh", "can cuoc", "chung minh nhan dan", "identity card", "ho chieu", "passport",
                   "giay khai sinh", "trich luc khai sinh", "xet nghiem adn", "giam dinh", "benh vien", "so y te",
                   "trung tam y te", "tram y te")
_SELF_MADE_MARKERS = ("cam doan", "cam ket", "thoa thuan", "don ", "uy quyen", "bien ban")
_HEADER_LINES = 12

name_key = base._name_key
WORD_RE = base._WORD_RE


def pages(documents: list[dict]) -> list[dict]:
    """[{doc, lines, kind}] — kind: "to_khai" | "ban_in" | "tu_lap". Trang quét trùng nguyên văn chỉ giữ một."""
    out, seen = [], set()
    for index, document in enumerate(documents, start=1):
        for text in base._PAGE_BREAK_RE.split(str(document.get("text") or "")):
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            body = "\n".join(lines)
            if not lines or body in seen:
                continue
            seen.add(body)
            head = " ".join(fold(line) for line in lines[:_HEADER_LINES])
            if any(marker in head for marker in _TO_KHAI):
                kind = "to_khai"
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
    out = {"trang": 0, "ban_in": 0, "the": 0, "tu_lap": 0, "to_khai": 0}
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
    """Nhiều trang hơn trước; bằng nhau thì giấy in cơ quan cấp (kể cả thẻ) > tờ khai > giấy tự lập."""
    return stat["trang"], stat["ban_in"] + stat["the"], stat["to_khai"], stat["tu_lap"]


def digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))

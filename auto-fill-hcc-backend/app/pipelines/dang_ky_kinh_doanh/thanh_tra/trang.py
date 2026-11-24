"""Trang giấy của hồ sơ đăng ký hộ kinh doanh và hạng nguồn của từng trang — phần mã dùng chung của các thanh tra.

Hồ sơ hay quét cả tập (giấy đề nghị + CCCD + giấy ủy quyền) vào một tệp nhiều trang nên xét theo TRANG. Trang 2–4 của giấy
đề nghị không có tiêu đề riêng → trang không mang dấu hiệu loại giấy nào thì thuộc loại của trang trước trong cùng tệp.
kind: "don" (giấy đề nghị, viết tay) | "ban_in" (thẻ căn cước) | "tu_lap" (giấy ủy quyền, hợp đồng… người dân tự lập) |
"khac" (không dùng làm nguồn: hồ sơ tải lẫn giấy đề nghị của người khác thì không biết thẻ / giấy ủy quyền nào của ai, nên
mọi trang ngoài giấy đề nghị của chủ hộ đều thành "khac").
"""

import asyncio
import re

from app.pipelines._shared.thanh_tra.ho_so import fold
from app.pipelines.xac_nhan_tthn_dvc_moi.thanh_tra import dinh_danh as base

_DON = ("giay de nghi dang ky ho kinh doanh", "de nghi dang ky ho kinh doanh")
_CARD = ("can cuoc", "chung minh nhan dan", "identity card")
_SELF_MADE = ("uy quyen", "hop dong", "cam ket", "cam doan", "bien ban")
_HEADER_LINES = 12

name_key = base._name_key
WORD_RE = base._WORD_RE


def pages(documents: list[dict], values: dict | None = None) -> list[dict]:
    """[{doc, lines, kind, form}]. Trang quét trùng nguyên văn chỉ giữ một. ``values`` (field lượt trích): tải lẫn nhiều giấy
    đề nghị thì chỉ giữ giấy mang số / họ tên chủ hộ của lượt trích (form = số thứ tự giấy đề nghị)."""
    out, seen, form = [], set(), 0
    for index, document in enumerate(documents, start=1):
        kind = ""
        for text in base._PAGE_BREAK_RE.split(str(document.get("text") or "")):
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            body = "\n".join(lines)
            if not lines or body in seen:
                continue
            seen.add(body)
            head = " ".join(fold(line) for line in lines[:_HEADER_LINES])
            if any(marker in head for marker in _DON):
                kind = "don"
                form += 1
            elif any(marker in head for marker in _SELF_MADE):
                kind = "tu_lap"
            elif any(marker in head for marker in _CARD):
                kind = "ban_in"
            out.append({"doc": index, "lines": lines, "kind": kind or "tu_lap", "form": form if kind == "don" else 0})
    return _own_form(out, values) if values is not None else out


def _own_form(page_list: list[dict], values: dict) -> list[dict]:
    forms = {page["form"] for page in page_list if page["kind"] == "don"}
    if len(forms) <= 1:
        return page_list
    number = digits(values.get("ChuHo_SoDinhDanh"))
    name = fold(" ".join(words(values.get("ChuHo_HoTen")).split()))

    def mine(form: int) -> bool:
        text = "\n".join(line for page in page_list if page["form"] == form for line in page["lines"])
        return (len(number) >= 9 and number in digits(text)) or (bool(name) and name in fold(" ".join(
            words(text).split())))

    chosen = [form for form in forms if mine(form)]
    keep = chosen[0] if len(chosen) == 1 else None
    return [page if page["kind"] == "don" and page["form"] == keep else {**page, "kind": "khac"} for page in page_list]


def words(value) -> str:
    return f" {' '.join(WORD_RE.findall(name_key(value)))} "


def card_line(line: str) -> bool:
    """Dòng họ tên in hoa của thẻ (nhãn song ngữ): OCR hay rơi / lệch dấu ở chữ in hoa."""
    return "full name" in fold(line)


def digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


# Lượt đọc ảnh chạy song song từ đầu lượt trích; đợt soát chỉ chờ thêm chừng này rồi bỏ qua nguồn đó (cả đợt soát có hạn
# second_pass_timeout_seconds).
VISION_WAIT_SECONDS = 10


async def vision(options: dict) -> dict:
    """Kết quả lượt Qwen đọc ảnh giấy đề nghị (``options["_vision"]``: dict, hoặc tác vụ còn đang chạy); {} khi không có."""
    data = options.get("_vision")
    if isinstance(data, asyncio.Future):
        try:
            data = await asyncio.wait_for(asyncio.shield(data), VISION_WAIT_SECONDS)
        except Exception:  # noqa: BLE001 — chậm / lỗi thì soát không có nguồn này
            return {}
    return data if isinstance(data, dict) else {}

"""Lượt LLM nhỏ chuẩn hoá DẤU tên hộ kinh doanh viết tay.

OCR chữ viết tay hay lệch dấu ở tên hộ kinh doanh (một chữ ra từ vô nghĩa). Đưa quy tắc vào prompt trích xuất chính
không ăn — lượt đó bám chặt chữ OCR — nên tách một câu hỏi riêng chỉ về tên. Kết quả chỉ được nhận khi bỏ dấu đi
vẫn y hệt tên gốc (chỉ đổi dấu, không đổi/thêm/bớt chữ cái hay ký tự nào).
"""

import logging
import unicodedata

from app.services.llm import client

logger = logging.getLogger(__name__)

_MAX_TOKENS = 200

PROMPT = """Dưới đây là TÊN HỘ KINH DOANH do OCR đọc từ chữ viết tay, có thể lệch DẤU (dấu thanh, dấu mũ/móc).
Xét TỪNG CHỮ (âm tiết) của tên:
- Chữ là một âm tiết tiếng Việt CÓ NGHĨA, dù nghĩa gì → GIỮ NGUYÊN, không đổi sang từ khác "hợp hơn".
- Chữ là tên người, thương hiệu, từ nước ngoài → GIỮ NGUYÊN.
- Chỉ chữ KHÔNG mang nghĩa nào trong tiếng Việt, mà đổi dấu (giữ nguyên các chữ cái) là ra một từ thông dụng hợp
  nghĩa với cả tên → đưa vào danh sách sửa. Không chắc → không sửa.

Tên: {name}

Trả DUY NHẤT JSON: {{"sua": [{{"chu_goc": "<chữ như trong tên>", "chu_goc_co_nghia": false, "chu_moi": "<chữ sau khi sửa dấu>"}}]}}
Không có chữ nào cần sửa → {{"sua": []}}"""


def _strip_marks(value: str) -> str:
    text = unicodedata.normalize("NFD", value.replace("Đ", "D").replace("đ", "d"))
    return unicodedata.normalize("NFC", "".join(ch for ch in text if unicodedata.category(ch) != "Mn"))


async def fix_diacritics(name: str) -> str | None:
    """Tên đã sửa dấu; None khi giữ nguyên, LLM lỗi hoặc đề xuất đổi cả chữ cái / chữ vốn có nghĩa."""
    name = str(name or "").strip()
    if not any(ch.isalpha() for ch in name):
        return None
    try:
        raw = await client.chat(
            [{"role": "user", "content": PROMPT.format(name=name)}],
            temperature=0,
            max_tokens=_MAX_TOKENS,
            purpose="hkd_ten_ho_sua_dau",
        )
        edits = client.extract_json_block(raw).get("sua") or []
    except Exception as exc:  # noqa: BLE001 — lượt phụ lỗi thì giữ tên OCR
        logger.warning("Chuẩn hoá dấu tên hộ kinh doanh lỗi, giữ tên OCR: %s", exc)
        return None
    words = unicodedata.normalize("NFC", name).split()
    changed = False
    for edit in edits if isinstance(edits, list) else []:
        if not isinstance(edit, dict) or edit.get("chu_goc_co_nghia") is not False:
            continue
        old = unicodedata.normalize("NFC", str(edit.get("chu_goc") or "").strip())
        new = unicodedata.normalize("NFC", str(edit.get("chu_moi") or "").strip())
        # Chỉ nhận đổi DẤU của đúng một chữ có trong tên — không đổi chữ cái, không thêm/bớt chữ.
        if not old or not new or old == new or old not in words or _strip_marks(old) != _strip_marks(new):
            continue
        words = [new if w == old else w for w in words]
        changed = True
    return " ".join(words) if changed else None

"""Lượt LLM riêng đọc bảng "Dạng khuyết tật" (mục III.1 Mẫu số 01), chạy song song lượt trích chính.

Lượt trích chính (prompt dài, đọc cả hồ sơ) hay sai bảng này theo hai kiểu: OCR đặt dấu đúng cột "Không" mà model hiểu là
"Có" (có hồ sơ bị tích "Có" gần hết 37 dòng), và bảng không có dấu nào (dấu viết tay OCR làm mất) thì model tự suy dạng
khuyết tật từ chẩn đoán trong bệnh án. Lượt này chỉ nhận OCR, buộc model CHÉP từng dòng và hai ô cuối (Có, Không) trong
chính JSON trả về; MÃ suy Có / Không từ ô có dấu, không tin kết luận của model. Như muc_do.py cho bảng mức độ.
"""

import logging
import re

from app.services.llm import client

from .vision import ROWS

logger = logging.getLogger(__name__)

_MAX_TOKENS = 4000
_MARKS = ("x", "✓", "✔", "√", "v", "☑", "☒")
# Mọi dòng con đọc được đều "Có" (từ 20 dòng trở lên) là đọc lệch cột, không phải tờ khai thật. Người khuyết tật nặng
# tích "Có" cả mấy nhóm là có thật nên không chặn theo tỉ lệ.
_DEGENERATE_MIN_ROWS = 20
# OCR hay dính dấu nháy / chấm sau STT dòng nhóm ("| 6’ | Khuyết tật khác |"): bỏ khi so STT, không thì mất cả dòng.
_STT_NOISE = ".’‘'`´ "
WARNING = ("Chưa đọc chắc được bảng dạng khuyết tật (Mục III.1) — cán bộ soát lại các ô Có/Không.")

PROMPT = """<task>
Đọc OCR của Đơn đề nghị xác định mức độ khuyết tật (Mẫu số 01). CHỈ đọc bảng "1. Thông tin về dạng khuyết tật"
(cột STT | Các dạng khuyết tật | Có | Không). Bỏ qua mọi phần khác của đơn và mọi giấy tờ khác (bệnh án, giấy ra viện,
CCCD...). TUYỆT ĐỐI KHÔNG suy dạng khuyết tật từ chẩn đoán, bệnh án hay hiểu biết: chỉ chép dấu có trên dòng OCR của bảng.
</task>

<table_structure>
Dòng dữ liệu của bảng trong OCR có dạng "| <STT> | <tên dạng khuyết tật> | <ô Có> | <ô Không> |". STT là "1".."6" (dòng
nhóm) hoặc "1.1".."6.3" (dòng con). Bảng có thể kéo sang nhiều trang, có trang lặp lại tiêu đề cột.
Hai ô CUỐI của dòng là ô "Có" rồi ô "Không" (trái → phải). Dấu đánh: X, x, ✓, √, V, ☑.
</table_structure>

<steps>
Làm TỪNG dòng có STT trong bảng, độc lập với dòng khác, GHI KẾT QUẢ MỖI BƯỚC vào JSON:
1. "so": STT của dòng ("1", "1.4", "6.1"...).
2. "dong_ocr": chép NGUYÊN VĂN dòng OCR đó (bắt đầu bằng "| <STT> |").
3. "o_danh_dau": tách dòng theo dấu "|", bỏ phần rỗng trước dấu "|" đầu và sau dấu "|" cuối, lấy đúng 2 ô CUỐI, giữ
   nguyên chữ trong ô, ô trống ghi "". Dòng không có dạng "| ... |" (chữ thường, vỡ bảng, trang không còn cột) thì BỎ dòng
   đó — KHÔNG tự dựng dòng bảng cho mục chỉ có chữ, không đoán dấu.
Không suy dấu của dòng này từ dòng trên / dưới, không suy dòng nhóm từ dòng con.
</steps>

<examples>
Các ví dụ chỉ minh hoạ HÌNH DẠNG dòng OCR, không phải đáp án của đơn đang đọc.
"| 1.2 | Thiếu tay hoặc không cử động được tay | X | |" → {"so":"1.2","dong_ocr":"...","o_danh_dau":["X",""]}
"| 2 | Khuyết tật nghe, nói | | x |" → {"so":"2","dong_ocr":"...","o_danh_dau":["","x"]}
"| 3.1 | Mù một hoặc hai mắt | | |" → {"so":"3.1","dong_ocr":"...","o_danh_dau":["",""]}
</examples>

<output_contract>
Trả DUY NHẤT một JSON object, không markdown, không giải thích ngoài JSON:
{"dong":[{"so":"1","dong_ocr":"...","o_danh_dau":["",""]}]}
Chỉ liệt kê dòng có trong OCR. Không có bảng dạng khuyết tật → {"dong":[]}.
</output_contract>"""


def _marked(cell) -> bool:
    text = str(cell or "").strip().lower()
    return bool(text) and any(mark in text for mark in _MARKS)


def _squeeze(text) -> str:
    return re.sub(r"\s+", "", str(text or ""))


def _cells(line: str) -> list[str] | None:
    """Hai ô cuối (Có, Không) của một dòng bảng "| STT | tên | Có | Không |"; None khi dòng không có dạng bảng."""
    text = line.strip()
    if not (text.startswith("|") and text.endswith("|")):
        return None
    parts = [part.strip() for part in text[1:-1].split("|")]
    return parts[-2:] if len(parts) >= 4 else None


def _row_line(key: str, copied: str, ocr_text: str) -> str:
    """Dòng bảng "| <STT> | …|" trong OCR: chỉ một dòng mang STT đó thì lấy dòng đó; nhiều dòng (hồ sơ quét trùng trang)
    thì lấy dòng model đã chép nguyên văn. Không tin dòng model tự chép khi không có trong OCR."""
    pattern = re.compile(rf"^\|\s*{re.escape(key)}[{re.escape(_STT_NOISE)}]*\|")
    lines = [line.strip() for line in str(ocr_text or "").splitlines() if pattern.match(line.strip())]
    if len(lines) == 1:
        return lines[0]
    same = [line for line in lines if _squeeze(line) == _squeeze(copied)]
    return same[0] if same else ""


def rows_from(data, ocr_text: str = "") -> dict[str, str] | None:
    """JSON model → {STT: "co" | "khong" | "trong"}; None khi không có dòng nào của bảng. Model chỉ chỉ ra DÒNG: dòng
    phải có nguyên văn trong OCR và đúng STT, hai ô Có / Không do MÃ tách từ chính dòng đó (model từng bịa "Có" cho cả
    trang OCR vỡ bảng không còn cột)."""
    rows = data.get("dong") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return None
    out: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = str(row.get("so") or "").strip().rstrip(_STT_NOISE)
        if key not in ROWS:
            continue
        line = _row_line(key, str(row.get("dong_ocr") or ""), ocr_text)
        cells = _cells(line) if line else None
        if cells is None:
            continue
        co, khong = (_marked(cell) for cell in cells)
        # Dấu ở cả hai ô: không biết bên nào → coi như trống.
        out[key] = "co" if co and not khong else "khong" if khong and not co else "trong"
    return out or None


def to_fields(rows: dict[str, str]) -> dict:
    """{STT: co/khong/trong} → field compact. Không dòng nào có dấu → không tích gì (field rỗng)."""
    marked = [key for key in ROWS if rows.get(key) == "co"]
    # Dòng con "Có" mà dòng nhóm để trống: cổng chỉ hiện dòng con khi nhóm "Có".
    groups = list(dict.fromkeys([key for key in marked if "." not in key] + [key.split(".")[0] for key in marked]))
    return {
        "KhuyetTat_DanhMuc": [f"kt{key}" for key in groups],
        "KhuyetTat_ChiTiet": [f"kt{key.replace('.', '_')}" for key in marked if "." in key],
    }


def is_degenerate(rows: dict[str, str]) -> bool:
    children = [value for key, value in rows.items() if "." in key and value != "trong"]
    return len(children) >= _DEGENERATE_MIN_ROWS and all(value == "co" for value in children)


async def read_disability_types(documents: list[dict]) -> dict | None:
    """{STT: co/khong/trong} của bảng dạng khuyết tật; None khi lỗi / OCR không có bảng (runner giữ lượt chính)."""
    text = "\n\n".join(str(d.get("text") or "") for d in documents if d.get("text"))
    if not text.strip():
        return None
    try:
        raw = await client.chat(
            [{"role": "system", "content": PROMPT}, {"role": "user", "content": "OCR:\n" + text}],
            max_tokens=_MAX_TOKENS,
            temperature=0,
            purpose="dang_khuyet_tat",
        )
        return rows_from(client.extract_json_block(raw), text)
    except Exception as exc:  # noqa: BLE001 — lượt phụ lỗi không được làm hỏng luồng chính
        logger.warning("Đọc bảng dạng khuyết tật lỗi, giữ kết quả lượt chính: %s", exc)
        return None


def apply(res: dict, rows: dict[str, str] | None) -> None:
    """Thay KhuyetTat_* của lượt chính bằng kết quả bảng đọc riêng. Bảng không dấu → bỏ hẳn (không tích gì); đọc lệch
    (mọi dòng con "Có") → bỏ hẳn + cảnh báo. ``rows`` None (lỗi / không có bảng) → giữ lượt chính."""
    if rows is None:
        return
    names = ("KhuyetTat_DanhMuc", "KhuyetTat_ChiTiet")
    res["fields"] = [f for f in res["fields"] if f.get("name") not in names]
    if is_degenerate(rows):
        res.setdefault("errors", []).append(WARNING)
        return
    res["fields"] += [{"name": name, "comp": "raw", "value": value} for name, value in to_fields(rows).items() if value]

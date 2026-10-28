"""Qwen đọc thẳng ẢNH tài liệu → mục III Mẫu số 01 (dạng khuyết tật + mức độ hoạt động).

Bảng tích ✓ viết tay qua OCR văn bản hay mất vị trí cột (dấu cột "Không" thành "| | X |", LLM hiểu nhầm là "Có";
trang sau vỡ bảng). Model đa phương thức nhìn được dấu nằm dưới cột nào nên đọc riêng hai bảng này.
Runner gọi song song với OCR + LLM; trả ``None`` khi lỗi/không parse được để runner giữ kết quả cũ.
"""

import asyncio
import base64
import logging
from contextlib import ExitStack

import fitz  # PyMuPDF

from app.monitor import recorder as mon
from app.services import ocr_qwen
from app.services.llm.client import extract_json_block
from app.services.ocr_tiengnoi import _open_input

logger = logging.getLogger(__name__)

# Cạnh dài 1600px đủ thấy dấu tích viết tay; trang A4 ~1.8k token ảnh.
_MAX_SIDE_PX = 1600
_JPEG_QUALITY = 85
# Đơn nằm ở đầu hồ sơ; chặn trần để hồ sơ dài không vượt context model.
_MAX_PAGES = 20
_MAX_TOKENS = 2500
_TIMEOUT_S = 300
# Cùng ảnh, model đôi khi trả kết quả suy biến (mọi dòng "co"); đọc lại 1 lần thường ra đúng.
_MAX_ATTEMPTS = 2

ROWS = (
    "1", "1.1", "1.2", "1.3", "1.4", "1.5", "1.6",
    "2", "2.1", "2.2", "2.3", "2.4", "2.5", "2.6",
    "3", "3.1", "3.2", "3.3", "3.4", "3.5", "3.6", "3.7",
    "4", "4.1", "4.2", "4.3", "4.4", "4.5",
    "5", "5.1", "5.2", "5.3", "5.4",
    "6", "6.1", "6.2", "6.3",
)
_VALID_MUC_DO = {"THD", "CTG", "KTHD", "KXD"}
SECTION_III_WARNING = (
    "Chưa đọc chắc được bảng Mục III (dạng khuyết tật, mức độ) từ ảnh — cán bộ soát lại các ô Có/Không và mức độ."
)

PROMPT = """Bạn đọc ẢNH các trang của hồ sơ "Đơn đề nghị xác định, xác định lại mức độ khuyết tật" (Mẫu số 01, Thông tư 01/2019/TT-BLĐTBXH).
Chỉ trích mục "III. Thông tin về tình trạng khuyết tật", gồm 2 bảng. Bỏ qua mọi trang/giấy tờ khác (CCCD, bệnh án, phiếu của trường...).

BẢNG 1 — "Thông tin về dạng khuyết tật": cột STT | Các dạng khuyết tật | Có | Không. Bảng có thể kéo sang nhiều trang
(Mẫu số 01-1, 01-2, 01-3), mỗi trang lặp lại tiêu đề cột.
- Dấu đánh có thể là ✓, √, V, X, x viết tay. Dấu nằm DƯỚI tiêu đề cột "Có" → "co"; DƯỚI tiêu đề cột "Không" → "khong".
- Xác định cột theo vị trí ngang của dấu so với đường kẻ dọc giữa cột "Có" và "Không", không theo thứ tự xuất hiện.
- Dấu viết tay hay lệch lên/xuống: gán cho dòng mà dấu nằm chủ yếu trong ô của dòng đó. Dấu đè đúng lên đường kẻ
  giữa hai dòng, không rõ thuộc dòng nào → "khong_ro".
- Ô của dòng không có dấu ở cả hai cột → "trong". Có dấu ở cả hai cột cùng dòng → "khong_ro".
- KHÔNG suy luận theo nghiệp vụ (vd dòng nhóm cha phải "co" vì dòng con "co"); chỉ chép đúng dấu nhìn thấy.

BẢNG 2 — "Thông tin về mức độ khuyết tật": 10 hoạt động, 4 cột mức độ theo thứ tự trái → phải:
"Thực hiện được" = THD; "Thực hiện được nhưng cần sự trợ giúp" = CTG; "Không thực hiện được" = KTHD; "Không xác định được" = KXD.
- Mỗi hoạt động trả mã cột chứa dấu. Không có dấu → "trong"; dấu ở nhiều cột hoặc không rõ cột → "khong_ro".

Trả DUY NHẤT một JSON, không giải thích:
{"dang_khuyet_tat": {"1": "...", "1.1": "...", ... đủ 37 dòng: %ROWS%},
 "muc_do": {"1": "...", ..., "10": "..."}}
Giá trị dang_khuyet_tat ∈ "co" | "khong" | "trong" | "khong_ro". Giá trị muc_do ∈ "THD" | "CTG" | "KTHD" | "KXD" | "trong" | "khong_ro".""".replace(
    "%ROWS%", ", ".join(ROWS)
)


def _page_images(files: list[dict]) -> list[bytes]:
    images: list[bytes] = []
    for f in files:
        name = str(f.get("name") or "").lower()
        if name.endswith(".docx") or "wordprocessingml" in str(f.get("type") or ""):
            continue
        with ExitStack() as stack:
            _, src, mime = _open_input(f, stack)
            raw = src if isinstance(src, bytes) else src.read()
        filetype = "pdf" if "pdf" in mime else (mime.split("/")[-1] or None)
        doc = fitz.open(stream=raw, filetype=filetype)
        for page in doc:
            if len(images) >= _MAX_PAGES:
                return images
            zoom = min(_MAX_SIDE_PX / max(page.rect.width, page.rect.height), 3.0)
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            images.append(pix.tobytes("jpeg", jpg_quality=_JPEG_QUALITY))
    return images


def _row_values(rows: dict) -> dict[str, str]:
    values = {str(k): str(v).strip().lower() for k, v in rows.items() if str(k) in ROWS}
    # Dòng nhóm in đậm hay để trống trên giấy, model lại hay tích nhầm nó. Nhóm "co" mà MỌI dòng con "khong"
    # là tự mâu thuẫn; nhóm trống mà không dòng con nào "co" và có dòng con "khong" thì cổng vẫn cần chọn
    # "Không" ở dòng nhóm → cả hai theo các dòng con.
    for parent in [r for r in ROWS if "." not in r]:
        kids = [values.get(c) for c in ROWS if c.startswith(parent + ".")]
        if values.get(parent) == "co" and all(v == "khong" for v in kids):
            values[parent] = "khong"
        elif values.get(parent) in (None, "trong") and "co" not in kids and "khong" in kids:
            values[parent] = "khong"
    return values


def is_degenerate(data: dict) -> bool:
    """Mọi dòng con cùng "co" — kiểu trả lời suy biến model thỉnh thoảng ra với cùng ảnh, không phải tờ khai thật."""
    rows = data.get("dang_khuyet_tat") if isinstance(data, dict) else None
    if not isinstance(rows, dict):
        return False
    children = [r for r in ROWS if "." in r]
    return all(str(rows.get(r) or "").strip().lower() == "co" for r in children)


def to_compact_fields(data: dict) -> dict | None:
    """JSON model → field compact của pipeline. Thiếu khung bảng → None (coi như không đọc được)."""
    rows = data.get("dang_khuyet_tat") if isinstance(data, dict) else None
    muc_do = data.get("muc_do") if isinstance(data, dict) else None
    if not isinstance(rows, dict) or not isinstance(muc_do, dict):
        return None
    if not any(str(k) in ROWS for k in rows):
        return None
    values = _row_values(rows)
    marked = [k for k in ROWS if values.get(k) == "co"]
    return {
        "KhuyetTat_DanhMuc": [f"kt{k}" for k in marked if "." not in k],
        "KhuyetTat_ChiTiet": [f"kt{k.replace('.', '_')}" for k in marked if "." in k],
        "KhuyetTat_Khong": [f"kt{k.replace('.', '_')}" for k in ROWS if values.get(k) == "khong"],
        "MucDo_HoatDong": {
            str(k): str(v).strip().upper()
            for k, v in muc_do.items()
            if str(v).strip().upper() in _VALID_MUC_DO
        },
    }


async def read_section_iii(files: list[dict]) -> dict | None:
    try:
        async with mon.span("llm.vision_muc_iii") as span:
            images = await asyncio.to_thread(_page_images, files)
            if not images:
                return None
            content = [{"type": "text", "text": PROMPT}] + [
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(b).decode()}}
                for b in images
            ]
            span.attrs["pages"] = len(images)
            for attempt in range(_MAX_ATTEMPTS):
                res = await ocr_qwen.chat(
                    [{"role": "user", "content": content}],
                    max_tokens=_MAX_TOKENS,
                    timeout_s=_TIMEOUT_S,
                    ocr_server=True,
                )
                span.attrs["usage"] = res.get("usage")
                if res.get("finish_reason") == "length":
                    raise ValueError("JSON bị cắt (chạm max_tokens)")
                data = extract_json_block(res.get("content") or "")
                mon.output("vision_muc_iii" if attempt == 0 else f"vision_muc_iii_{attempt + 1}", data)
                if not is_degenerate(data or {}):
                    break
            else:
                raise ValueError("Mọi dòng con đều 'co' sau %d lần đọc" % _MAX_ATTEMPTS)
            parsed = to_compact_fields(data or {})
            if parsed is None:
                raise ValueError("JSON không đúng khung dang_khuyet_tat/muc_do")
            return parsed
    except Exception as exc:  # noqa: BLE001 — lỗi lượt phụ không được làm hỏng luồng chính
        logger.warning("Qwen đọc mục III khuyết tật lỗi, giữ kết quả OCR + LLM: %s", exc)
        return None

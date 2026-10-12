"""Agent rà soát duy nhất của luồng mới 2: chuẩn hoá MỤC ĐÍCH.

Phần tên/số/ngày do code so v1 ↔ bản đọc thứ hai (luong2.quyet_dinh); agent chỉ ghép câu mục đích viết tay từ v1 +
dòng OCR Vintern + câu bản đọc thứ hai. Hồ sơ không có dòng mục đích thì không gọi.
"""
from __future__ import annotations

import re

from app.services import ocr_qwen
from app.services.llm import client as llm_client
from scripts.luongmoi import muc_dich

_BLOCK = lambda tag: re.search(rf"<{tag}>.*?</{tag}>", muc_dich.PROMPT, re.S).group(0)  # noqa: E731

PROMPT = f"""Bạn rà soát hồ sơ "Cấp Giấy xác nhận tình trạng hôn nhân" sau bước trích xuất: khôi phục câu "Mục đích sử
dụng Giấy xác nhận tình trạng hôn nhân" người dân VIẾT TAY trên tờ khai (hoặc dòng "Giấy này được sử dụng để: ..." của
giấy XNTTHN cũ). Đầu vào: BẢN V1 (bước trích xuất từ OCR 1), dòng mục đích OCR 1 (Vintern) đọc, và BẢN ĐỌC 2 (máy khác
đọc thẳng từ ảnh). Cả ba đều có thể sai.
{_BLOCK("tri_thuc")}
{_BLOCK("cach_lam")}

Trả NGAY một JSON trong code block, không giải thích ngoài JSON:
```json
{{"muc_dich": "<câu>", "da_sua": ["<cụm cũ> → <cụm mới>"], "do_chac": "cao|thap"}}
```"""


async def ra_soat(case: dict, v1: dict, b: dict, thinking: bool = False) -> dict | None:
    """→ {"muc_dich": {muc_dich, da_sua, do_chac, ocr1, ocr2}, "ms"} hoặc None khi hồ sơ không có dòng mục đích.

    ``b``: ô của bản đọc thứ hai → (giá trị, p, chữ yếu)."""
    v1_purpose = v1.get("Purpose") or ""
    line1 = muc_dich.purpose_line(case["vintern_text"])
    line2 = (b.get("Purpose") or ("",))[0] or ""
    if not (v1_purpose or line1 or line2):
        return None
    user = (f"BẢN V1: {v1_purpose or '(trống)'}\nOCR 1 (Vintern): {line1 or '(không thấy dòng)'}\n"
            f"BẢN ĐỌC 2: {line2 or '(không thấy)'}")
    resp = await ocr_qwen.chat([{"role": "system", "content": PROMPT}, {"role": "user", "content": user}],
                               max_tokens=6000 if thinking else 600, timeout_s=180, thinking=thinking)
    try:
        out = llm_client.extract_json_block(resp["content"])
    except Exception:  # noqa: BLE001 — giữ output thô để xem agent trả sai định dạng ra sao
        out = {"muc_dich": None, "_raw": resp["content"][:1500]}
    return {"muc_dich": {**out, "ocr1": line1, "ocr2": line2}, "ms": resp["ms"]}

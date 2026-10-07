"""Đính kèm thay đổi, cải chính hộ tịch (Cổng DVC quốc gia mới).

Bảng thành phần có hai dòng: "Văn bản ủy quyền..." và "Giấy tờ làm căn cứ
thay đổi, cải chính, bổ sung thông tin hộ tịch". Một dòng nhận nhiều tệp (nút "Tải lên file" + input dùng
chung). LLM đọc từng tệp để nhận ra VĂN BẢN ỦY QUYỀN → dòng 1; mọi tệp còn lại (CCCD, trích lục, tờ khai, giấy
tờ làm căn cứ) → dòng 2. LLM lỗi / OCR hụt → dòng 2, không tệp nào bị bỏ.

Cổng chỉ nhận tệp dưới 2 MB: tệp trên `SHRINK_ABOVE_BYTES` được vẽ lại từng trang thành JPEG theo thang
`_SHRINK_LADDER` cho tới khi lọt `MAX_FILE_BYTES` (giữ màu lâu nhất, nấc cuối là mức sàn còn đọc được), trả về ở
`replaceFiles` để extension đính bản nén thay bản gốc. Tệp nhỏ hơn để nguyên. OCR vẫn đọc bản gốc.
"""

import asyncio
import base64
import os
import time

from app.config import settings
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
SHRINK_ABOVE_BYTES = 2_000_000  # chỉ nén tệp trên 2 MB (cách tính chặt), tệp nhỏ hơn để nguyên
MAX_FILE_BYTES = 1_900_000  # đích nén: dưới 2 MB của cổng, chừa biên cho cả cách tính 2.000.000 lẫn 2 MiB
_SHRINK_LADDER = [  # (dpi, chất lượng JPEG, ảnh xám)
    (150, 75, False), (150, 60, False), (120, 75, False), (120, 60, False),
    (120, 70, True), (100, 60, True), (100, 50, True),
]
_UY_QUYEN = "uy_quyen"

ROW_UY_QUYEN = {"slotKey": "cai_chinh_uy_quyen", "slotIndex": 0, "slotName": "Văn bản ủy quyền"}
ROW_CAN_CU = {
    "slotKey": "cai_chinh_can_cu",
    "slotIndex": 1,
    "slotName": "Giấy tờ làm căn cứ thay đổi, cải chính, bổ sung thông tin hộ tịch",
}


def build_plan_items(file_names: list[str], doc_types: dict[int, str]) -> list[dict]:
    items = []
    for index, name in enumerate(file_names):
        is_uy_quyen = doc_types.get(index) == _UY_QUYEN
        row = ROW_UY_QUYEN if is_uy_quyen else ROW_CAN_CU
        items.append({
            "fileIndex": index,
            "fileName": name,
            "documentName": os.path.splitext(name)[0] or name,
            "componentName": row["slotName"],
            "target": "fixed-slot",
            "needsAddComponent": False,
            "detectedType": _UY_QUYEN if is_uy_quyen else "other",
            "noChooserClick": True,
            **row,
        })
    return items


def _decode(data_url: str) -> bytes:
    return base64.b64decode(data_url.split(",", 1)[1] if "," in data_url else data_url)


def _render_pdf(raw: bytes, dpi: int, quality: int, gray: bool) -> bytes:
    import pymupdf

    src = pymupdf.open(stream=raw)
    out = pymupdf.open()
    colorspace = pymupdf.csGRAY if gray else pymupdf.csRGB
    for page in src:
        jpg = page.get_pixmap(dpi=dpi, colorspace=colorspace).tobytes("jpeg", jpg_quality=quality)
        target = out.new_page(width=page.rect.width, height=page.rect.height)
        target.insert_image(target.rect, stream=jpg)
    return out.tobytes(garbage=4, deflate=True)


def shrink_file(raw: bytes) -> tuple[bytes, str]:
    """Nấc đầu tiên lọt `MAX_FILE_BYTES`; hết thang vẫn vượt thì trả bản nhỏ nhất kèm nhãn nấc sàn."""
    best, label = raw, ""
    for dpi, quality, gray in _SHRINK_LADDER:
        out = _render_pdf(raw, dpi, quality, gray)
        if len(out) < len(best):
            best, label = out, f"{'xám' if gray else 'màu'} {dpi}dpi q{quality}"
        if len(out) <= MAX_FILE_BYTES:
            break
    return best, label


def _shrink_one(file: dict) -> dict | None:
    raw = _decode(file["dataUrl"])
    if len(raw) <= SHRINK_ABOVE_BYTES:
        return None
    out, label = shrink_file(raw)
    stem = os.path.splitext(file["name"])[0] or "tai-lieu"
    return {
        "name": f"{stem}.pdf",
        "type": "application/pdf",
        "dataUrl": "data:application/pdf;base64," + base64.b64encode(out).decode(),
        "originalBytes": len(raw),
        "bytes": len(out),
        "level": label,
    }


async def shrink_oversized(raw_files: list[dict], errors: list[str]) -> dict[str, dict]:
    async def one(index: int, file: dict):
        try:
            return index, await asyncio.to_thread(_shrink_one, file)
        except Exception as e:  # noqa: BLE001 — nén hỏng thì đính bản gốc, cổng tự báo nếu từ chối
            errors.append(f"Không nén được {file.get('name')}: {e}")
            return index, None

    results = await asyncio.gather(*(one(i, f) for i, f in enumerate(raw_files) if f.get("dataUrl")))
    replaced = {str(i): r for i, r in results if r}
    for r in replaced.values():
        if r["bytes"] > MAX_FILE_BYTES:
            errors.append(f"Tệp {r['name']} nén hết mức vẫn {r['bytes'] / 1e6:.1f} MB, vượt giới hạn 2 MB của cổng.")
    return replaced


async def _classify_one(index: int, text: str) -> tuple[int, str]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt([{"index": index, "text": text[:12000]}])},
    ]
    raw = await client.chat(messages, max_tokens=120, enable_thinking=settings.agent_reasoning)
    first = next(iter(client.extract_json_block(raw).get("documents", []) or []), {})
    return index, _UY_QUYEN if str(first.get("docType") or "").strip() == _UY_QUYEN else "other"


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    from app.services import ocr

    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    errors: list[str] = []
    pairs = [(i, f) for i, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]
    started = time.monotonic()
    shrink_task = asyncio.create_task(shrink_oversized(raw_files, errors))
    ocr_results = await ocr.ocr_per_file([f for _, f in pairs]) if pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    texts = {}
    for (index, file), result in zip(pairs, ocr_results):
        if result.get("error"):
            errors.append(f"OCR {file.get('name')}: {result['error']}")
        if str(result.get("text") or "").strip():
            texts[index] = str(result["text"])

    started = time.monotonic()
    outcomes = await asyncio.gather(*(_classify_one(i, t) for i, t in texts.items()), return_exceptions=True)
    llm_ms = int((time.monotonic() - started) * 1000)
    doc_types: dict[int, str] = {}
    for index, outcome in zip(texts, outcomes):
        if isinstance(outcome, BaseException):
            errors.append(f"attachment_agent file {index}: {outcome}")
            continue
        doc_types[index] = outcome[1]

    replace_files = await shrink_task
    names = [replace_files[str(i)]["name"] if str(i) in replace_files else f["name"] for i, f in enumerate(raw_files)]
    attachments = build_plan_items(names, doc_types)
    return {
        "attachments": attachments,
        "replaceFiles": replace_files or None,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "classified": [
                {"fileName": item["fileName"], "docType": item["detectedType"], "slotIndex": item["slotIndex"]}
                for item in attachments
            ],
            "shrunk": [
                {"fileName": r["name"], "originalBytes": r["originalBytes"], "bytes": r["bytes"], "level": r["level"]}
                for r in replace_files.values()
            ],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

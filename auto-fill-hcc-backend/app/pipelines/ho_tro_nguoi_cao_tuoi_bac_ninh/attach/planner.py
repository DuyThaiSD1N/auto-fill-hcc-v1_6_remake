"""Đính kèm (attach-only) "[Bắc Ninh] Hỗ trợ Người cao tuổi…" (1.014589).

LLM phân loại là chính → nhãn rút gọn (catalog.py) → BE map sang componentName (mã KQ) + slotKey hoặc ô
đính kèm BỔ SUNG. Chỉ 1 thành phần bắt buộc: Tờ khai (Mẫu 01) → KQ001012.
"""
import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import normalize_document_name
from app.process.schemas import FileItem
from app.services.llm import client

from . import catalog
from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[:limit] + "..."


def _looks_like_identity(h: str) -> bool:
    if any(k in h for k in (
        "can cuoc cong dan", "the can cuoc", "cccd", "chung minh nhan dan", "ho chieu", "passport",
    )):
        return True
    if "so dinh danh ca nhan" not in h:
        return False
    markers = ("co gia tri den", "date of expiry", "noi thuong tru", "que quan", "dac diem nhan dang")
    return sum(1 for m in markers if m in h) >= 2


def _label_by_keywords(ocr_text: str) -> str | None:
    h = _fold(ocr_text or "")
    if not h.strip():
        return None
    # Tờ khai là tài liệu chính — ưu tiên cả khi file gộp tờ khai + CCCD.
    if "to khai" in h and ("tro cap xa hoi" in h or "nguoi cao tuoi" in h or "de nghi huong" in h):
        return "to_khai"
    if "de nghi huong tro cap xa hoi" in h or "mau so 01" in h and "tro cap" in h:
        return "to_khai"
    if "co so du lieu quoc gia ve dan cu" in h or "ket qua kiem tra thong tin cong dan" in h:
        return "kq_dan_cu"
    if _looks_like_identity(h):
        return "cccd"
    return None


def _label_by_filename(name: str) -> str | None:
    h = _fold(name or "")
    if not h.strip():
        return None
    if "can cuoc" in h or "cccd" in h or "cmnd" in h or "cmt" in h:
        return "cccd"
    if "to khai" in h or "tro cap" in h or "nguoi cao tuoi" in h:
        return "to_khai"
    if "dan cu" in h or "tra cuu" in h:
        return "kq_dan_cu"
    return None


def _unique_document_name(base: str, used: set[str], fallback: str) -> str:
    normalized = normalize_document_name(base, fallback)
    key = _fold(normalized)
    if key and key not in used:
        used.add(key)
        return normalized
    stem = normalized[:45].strip() or fallback[:45].strip() or "Tài liệu"
    n = 2
    while True:
        candidate = f"{stem} {n}"[:50].strip()
        key = _fold(candidate)
        if key not in used:
            used.add(key)
            return candidate
        n += 1


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
    if not documents:
        return {}
    docs = [{"index": item["index"], "text": _truncate_text(item.get("text", ""))} for item in documents]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(docs)},
    ]
    raw = await client.chat(messages, max_tokens=700, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    parsed_docs = parsed.get("documents", []) or []

    def _coerce(item: dict) -> dict[str, str]:
        label = str(item.get("label") or "").strip()
        return {
            "label": label if catalog.is_valid(label) else "",
            "documentName": str(item.get("documentName") or "").strip(),
        }

    out: dict[int, dict[str, str]] = {}
    if len(parsed_docs) == len(documents):
        for pos, item in enumerate(parsed_docs):
            out[documents[pos]["index"]] = _coerce(item)
        return out
    raw_items: list[tuple[int, dict]] = []
    for item in parsed_docs:
        try:
            raw_items.append((int(item.get("index")), item))
        except Exception:  # noqa: BLE001
            continue
    offset = 0 if any(r == 0 for r, _ in raw_items) else 1
    valid = {d["index"] for d in documents}
    for r, item in raw_items:
        idx = r - offset
        if idx in valid:
            out[idx] = _coerce(item)
    return out


def _build_item(file: dict, idx: int, label: str, document_name: str) -> dict:
    target, component_name, slot_key = catalog.resolve(label)
    return {
        "fileIndex": idx,
        "fileName": str(file.get("name") or f"file-{idx + 1}"),
        "documentName": document_name,
        "componentName": component_name,  # mã KQ (existing) hoặc "" (bổ sung)
        "target": target,
        "slotKey": slot_key,
        "needsAddComponent": False,
        "detectedType": label,
    }


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options or {}
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]

    from app.services import ocr

    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for r in ocr_results:
        if r.get("error"):
            errors.append(f"OCR {r.get('name')}: {r['error']}")

    ocr_by_name = {r.get("name"): r for r in ocr_results}
    llm_docs = [
        {"index": idx, "text": str(ocr_by_name.get(file.get("name"), {}).get("text") or "")}
        for idx, file in enumerate(raw_files)
    ]

    t1 = time.monotonic()
    llm_types: dict[int, dict[str, str]] = {}
    if any(d["text"].strip() for d in llm_docs):
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as e:  # noqa: BLE001
            errors.append(f"attachment_agent: {e}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments: list[dict] = []
    classified: list[dict] = []
    used_names: set[str] = set()
    for idx, file in enumerate(raw_files):
        detected = llm_types.get(idx) or {"label": "", "documentName": ""}
        ocr_text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")

        label = detected.get("label") or ""
        route_src = "llm" if (catalog.is_valid(label) and label != "khac") else ""
        if not route_src:
            fb = _label_by_keywords(ocr_text) or _label_by_filename(file.get("name"))
            if fb:
                label = fb
                route_src = "keyword_filename"
        if not catalog.is_valid(label):
            label = "khac"
            route_src = route_src or "default"

        fallback_label = catalog.display_name(label)
        base = detected.get("documentName") if route_src == "llm" else ""
        base = base or fallback_label
        document_name = _unique_document_name(base, used_names, fallback_label)

        item = _build_item(file, idx, label, document_name)
        attachments.append(item)
        classified.append({
            "fileName": file.get("name"),
            "label": label,
            "routeSrc": route_src,
            "documentName": document_name,
            "target": item["target"],
            "componentName": item["componentName"],
            "slotKey": item["slotKey"],
        })

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [f["name"] for f in raw_files],
            "sessionId": (session or {}).get("request_id"),
            "classified": classified,
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

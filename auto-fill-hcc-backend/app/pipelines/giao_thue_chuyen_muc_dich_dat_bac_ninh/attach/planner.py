"""Đính kèm cho "[Bắc Ninh] Giao/thuê/chuyển mục đích/gia hạn SDĐ".

Kiến trúc: **LLM phân loại là chính** → NHÃN RÚT GỌN (catalog.py) → BE map sang componentName
CHI TIẾT (mã KQ) hoặc ô đính kèm BỔ SUNG → FE khớp đúng ô để upload.

Rule từ khóa / tên file CHỈ là fallback khi OCR rỗng hoặc LLM không chắc ("khac"/nhãn lạ). FE khớp
thành phần theo mã KQ (bền hơn mô tả dài dễ trùng).
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


def _looks_like_identity(haystack: str) -> bool:
    if any(k in haystack for k in (
        "can cuoc cong dan", "the can cuoc", "cccd", "chung minh nhan dan", "ho chieu", "passport",
    )):
        return True
    if "so dinh danh ca nhan" not in haystack:
        return False
    markers = ("co gia tri den", "date of expiry", "noi thuong tru", "que quan", "dac diem nhan dang")
    return sum(1 for m in markers if m in haystack) >= 2


def _label_by_keywords(ocr_text: str) -> str | None:
    """Fallback theo nội dung OCR → nhãn rút gọn. None = không rõ."""
    h = _fold(ocr_text or "")
    if not h.strip():
        return None
    # GCN THẬT (sổ đỏ) có "số vào sổ" — dấu hiệu chỉ có trên Giấy chứng nhận, KHÔNG có trên đơn.
    # Ưu tiên "gcn" cả khi file gộp cả đơn: 1 file chứa cả đơn + GCN → gắn vào ô GCN.
    if "so vao so" in h and "giay chung nhan" in h:
        return "gcn"
    # Đơn đề nghị nhận diện TRƯỚC "giấy chứng nhận" (thân đơn hay nhắc GCN → dễ nhầm).
    if "don de nghi" in h or "don dang ky" in h:
        if "mau so 04" in h:
            return "don_mau_04"
        if "mau so 01" in h:
            return "don_mau_01"
        return "don_de_nghi"
    if "mau so 04" in h:
        return "don_mau_04"
    if "mau so 01" in h:
        return "don_mau_01"
    if "tang dat mat" in h or "mau so 26" in h:
        return "tang_dat_mat"
    if "uy quyen" in h:
        return "uy_quyen"
    if "dau gia" in h and "rung" in h:
        return "dau_gia_thue_rung"
    if "du an" in h and "rung" in h:
        return "du_an_giao_rung"
    if "phuong an su dung dat" in h:
        return "phuong_an_su_dung_dat"
    if "giay chung nhan" in h and ("quyen su dung dat" in h or "quyen so huu" in h):
        return "gcn"
    if _looks_like_identity(h):
        return "cccd"
    return None


def _label_by_filename(name: str) -> str | None:
    """Fallback CUỐI khi OCR rỗng → nhãn rút gọn theo tên file."""
    h = _fold(name or "")
    if not h.strip():
        return None
    if "uy quyen" in h:
        return "uy_quyen"
    if "mau so 04" in h or "mau 04" in h:
        return "don_mau_04"
    if "mau so 01" in h or "mau 01" in h:
        return "don_mau_01"
    if "tang dat mat" in h or "mau 26" in h:
        return "tang_dat_mat"
    if "can cuoc" in h or "cccd" in h or "cmnd" in h or "cmt" in h:
        return "cccd"
    if any(k in h for k in ("so dat", "so do", "so hong", "gcn", "qsdd", "chung nhan")):
        return "gcn"
    if "don de nghi" in h or "don dk" in h or "don dki" in h:
        return "don_de_nghi"
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
    # LLM trả đúng số lượng → map theo THỨ TỰ (tránh lệch 0/1-based index).
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
    target, component_name = catalog.resolve(label)
    item = {
        "fileIndex": idx,
        "fileName": str(file.get("name") or f"file-{idx + 1}"),
        "documentName": document_name,
        "componentName": component_name,  # mã KQ (existing) hoặc "" (bổ sung)
        "target": target,
        "slotKey": "banChinh",
        "needsAddComponent": False,
        "detectedType": label,
    }
    return item


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

        # LLM LÀ CHÍNH: dùng nhãn LLM nếu hợp lệ và không phải "khac".
        label = detected.get("label") or ""
        route_src = "llm" if (catalog.is_valid(label) and label != "khac") else ""
        # Fallback khi LLM không chắc (khac/lạ) hoặc OCR rỗng: từ khóa nội dung → tên file.
        if not route_src:
            fb = _label_by_keywords(ocr_text) or _label_by_filename(file.get("name"))
            if fb:
                label = fb
                route_src = "keyword_filename"
        if not catalog.is_valid(label):
            label = "khac"
            route_src = route_src or "default"

        fallback_label = catalog.display_name(label)
        # documentName: tin LLM khi chính nó phân loại; fallback thì dùng nhãn hiển thị.
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

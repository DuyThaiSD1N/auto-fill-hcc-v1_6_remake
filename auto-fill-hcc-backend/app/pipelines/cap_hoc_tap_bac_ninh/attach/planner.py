"""Đính kèm thủ tục hỗ trợ chi phí học tập (Bắc Ninh 1.014581) — LUÔN tách file gộp theo trang.

Hồ sơ thường là MỘT PDF gộp nhiều giấy tờ (Mẫu 01, Mẫu 02, Bằng tốt nghiệp, CCCD, Đơn ủy quyền, Lời
chứng). Dịch vụ OCR tự chèn marker "Trang n/N" giữa các trang → dùng marker này để tách text theo trang
(giống cơ chế bên hộ tịch), phân loại TỪNG trang bằng LLM, gộp các trang liên tiếp cùng loại thành một
đoạn "từ trang a đến trang b", rồi định tuyến mỗi đoạn vào đúng thành phần hồ sơ (mã KQ) hoặc ô "File
đính kèm khác".

FE (popup.js applyMergeGroups → PdfConvert.composeSegmentsToPdf) tự dựng PDF con từ `sourceSegments`
rồi content.js/attachBacNinhByPlan gắn vào ô Bản chính của thành phần khớp componentName (mã KQ), hoặc
gộp mọi item `target=supplementary` vào ô fileDinhKem.
"""

import base64
import re
import time
from typing import Any

import fitz

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.process.schemas import FileItem
from app.services.llm import client

from . import catalog
from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# Marker phân trang do dịch vụ OCR tự sinh: "───── Trang 1/8 ─────".
_PAGE_HEADER_RE = re.compile(
    r"(?im)^[\t ─-╿-]*(?:trang|page)\s+(\d+)\s*/\s*(\d+)[\t ─-╿-]*$"
)


def _truncate(text: str, limit: int = 1600) -> str:
    value = re.sub(r"\s+", " ", text or "").strip()
    return value if len(value) <= limit else value[:limit] + "..."


def _decode_data_url(data_url: str) -> bytes:
    _, sep, payload = str(data_url or "").partition(",")
    if not sep:
        return b""
    payload += "=" * (-len(payload) % 4)
    try:
        return base64.b64decode(payload)
    except Exception:  # noqa: BLE001
        return b""


def _pdf_page_count(file: dict) -> int:
    is_pdf = "pdf" in str(file.get("type") or "").lower() or str(file.get("name") or "").lower().endswith(".pdf")
    if not is_pdf:
        return 1
    try:
        doc = fitz.open(stream=_decode_data_url(file.get("dataUrl") or ""), filetype="pdf")
        try:
            return max(1, doc.page_count)
        finally:
            doc.close()
    except Exception:  # noqa: BLE001 - file lỗi vẫn phải giữ để không mất tài liệu
        return 1


def _split_pages(text: str, page_count: int) -> tuple[list[dict], bool]:
    """Tách text theo marker 'Trang n/N'. Không có marker → 1 đơn vị phủ trọn file (không cắt được)."""
    value = str(text or "")
    matches = list(_PAGE_HEADER_RE.finditer(value))
    if not matches:
        return [{"pageNumber": 1, "pageTo": page_count, "text": value}], False
    total = page_count
    units: list[dict] = []
    for pos, m in enumerate(matches):
        num = int(m.group(1))
        total = max(total, int(m.group(2)))
        end = matches[pos + 1].start() if pos + 1 < len(matches) else len(value)
        units.append({"pageNumber": num, "pageTo": num, "text": value[m.end():end].strip()})
    units.sort(key=lambda u: u["pageNumber"])
    return units, True


_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("don_de_nghi", ("don de nghi ho tro chi phi hoc tap", "don de nghi ho tro chi phi")),
    ("xac_nhan_dao_tao", ("giay xac nhan cua co so dao tao", "xac nhan cua co so dao tao", "mau so 02")),
    ("bang_tot_nghiep", ("bang tot nghiep trung hoc", "bang tot nghiep")),
    ("giay_uu_tien", ("ho ngheo", "ho can ngheo", "khuyet tat", "tro cap xa hoi")),
    ("don_uy_quyen", ("xac nhan uy quyen nop ho so", "uy quyen nop ho so", "van ban uy quyen")),
    ("loi_chung", ("loi chung chung thuc chu ky", "chung thuc chu ky")),
    ("cccd", ("can cuoc cong dan", "citizen identity", "chung minh nhan dan", "the can cuoc", "ho chieu")),
]


def _rule_page_type(text: str) -> str:
    h = _fold(text)
    if not h.strip():
        return "khac"
    for label, markers in _RULES:
        if any(m in h for m in markers):
            return label
    return "khac"


def _normalize_type(value: Any) -> str:
    label = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    return label if catalog.is_valid(label) else "khac"


async def _classify_pages_with_llm(pages: list[dict[str, Any]]) -> dict[tuple[int, int], str]:
    if not pages:
        return {}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(pages)},
    ]
    raw = await client.chat(
        messages,
        max_tokens=max(500, min(3000, len(pages) * 60)),
        enable_thinking=settings.agent_reasoning,
    )
    parsed = client.extract_json_block(raw)
    out: dict[tuple[int, int], str] = {}
    for item in parsed.get("pages", []) or []:
        try:
            key = (int(item.get("fileIndex")), int(item.get("pageNumber")))
        except Exception:  # noqa: BLE001
            continue
        out[key] = _normalize_type(item.get("docType") or item.get("type"))
    return out


def _segments_for_file(
    file_index: int,
    units: list[dict],
    page_count: int,
    types_by_key: dict[tuple[int, int], str],
) -> list[dict]:
    """Gộp các trang liên tiếp cùng docType thành đoạn [pageFrom, pageTo]."""
    typed = []
    for unit in units:
        num = int(unit["pageNumber"])
        doc_type = types_by_key.get((file_index, num)) or _rule_page_type(unit.get("text") or "")
        typed.append((num, int(unit.get("pageTo") or num), doc_type))

    segments: list[dict] = []
    for page_from, page_to, doc_type in typed:
        if segments and segments[-1]["docType"] == doc_type and page_from == segments[-1]["pageTo"] + 1:
            segments[-1]["pageTo"] = page_to
        else:
            segments.append({"pageFrom": page_from, "pageTo": page_to, "docType": doc_type})
    return segments


def _build_item(file: dict, file_index: int, segment: dict, page_count: int) -> dict:
    doc_type = segment["docType"]
    target, component_name, slot_key = catalog.resolve(doc_type)
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    item = {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": catalog.display_name(doc_type),
        "componentName": component_name,
        "target": target,
        "slotKey": slot_key,
        "needsAddComponent": False,
        "detectedType": doc_type,
    }
    # Chỉ dựng PDF con khi đoạn KHÔNG phủ trọn file; đoạn = cả file → giữ nguyên file gốc.
    if not (segment["pageFrom"] == 1 and segment["pageTo"] >= page_count):
        item["sourceSegments"] = [{
            "fileIndex": file_index,
            "pageIndexes": list(range(segment["pageFrom"] - 1, segment["pageTo"])),
        }]
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
    ocr_by_name = {r.get("name"): r for r in ocr_results}
    for r in ocr_results:
        if r.get("error"):
            errors.append(f"OCR {r.get('name')}: {r['error']}")

    # Tách trang + gom danh sách trang để phân loại.
    units_by_file: dict[int, list[dict]] = {}
    page_count_by_file: dict[int, int] = {}
    llm_pages: list[dict] = []
    for idx, file in enumerate(raw_files):
        text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        page_count = _pdf_page_count(file)
        units, _boundaries = _split_pages(text, page_count)
        page_count = max(page_count, max((int(u["pageTo"]) for u in units), default=1))
        units_by_file[idx] = units
        page_count_by_file[idx] = page_count
        for u in units:
            if str(u.get("text") or "").strip():
                llm_pages.append({"fileIndex": idx, "pageNumber": int(u["pageNumber"]), "text": _truncate(u["text"])})

    t1 = time.monotonic()
    types_by_key: dict[tuple[int, int], str] = {}
    if llm_pages:
        try:
            types_by_key = await _classify_pages_with_llm(llm_pages)
        except Exception as exc:  # noqa: BLE001 - fallback rule keyword giữ đủ tài liệu
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments: list[dict] = []
    classified: list[dict] = []
    for idx, file in enumerate(raw_files):
        page_count = page_count_by_file[idx]
        for segment in _segments_for_file(idx, units_by_file[idx], page_count, types_by_key):
            attachments.append(_build_item(file, idx, segment, page_count))
            classified.append({
                "fileName": file.get("name"),
                "pageFrom": segment["pageFrom"],
                "pageTo": segment["pageTo"],
                "docType": segment["docType"],
                "target": attachments[-1]["target"],
                "componentName": attachments[-1]["componentName"],
            })

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [f.get("name") for f in raw_files],
            "sessionId": (session or {}).get("request_id"),
            "attachmentMode": "split_documents",
            "classified": classified,
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

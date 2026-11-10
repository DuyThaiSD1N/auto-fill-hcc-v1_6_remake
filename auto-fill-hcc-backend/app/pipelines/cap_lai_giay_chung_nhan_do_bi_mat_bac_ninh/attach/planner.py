"""Đính kèm cho "[Bắc Ninh] Cấp lại Giấy chứng nhận do bị mất" (1.115465).

Tab "Tải thành phần hồ sơ" có 3 thành phần, mỗi thành phần 2 dòng con Bản chính / Bản sao (dòng Bản sao không có nút
đính kèm). FE khớp thành phần theo `componentName` = MÃ TP-H05 in ở dòng tiêu đề, tick checkbox rồi gán tệp vào ô
Bản chính:
- Đơn đăng ký biến động (Mẫu 18) → TP-H05.000026. Hồ sơ thường scan CHUNG cả bộ (Đơn + giấy xác nhận tình trạng hôn
  nhân + Bản cam kết + Đơn trình báo mất + CCCD) thành một tệp, Đơn đứng đầu → LLM xếp application → đính nguyên tệp
  vào dòng này, không tách (ánh xạ đính kèm ngày 10/11/2026).
- Giấy chứng nhận đã cấp → TP-H05.000040: GCN đã MẤT nên thường để trống. Chỉ tệp đúng là GCN (bản sao, trang sổ) mới
  vào đây; Đơn trình báo mất / Bản cam kết KHÔNG phải GCN.
- Mảnh trích đo bản đồ địa chính (khi có nhu cầu đo đạc lại) → TP-H05.000045.
- CCCD / giấy ủy quyền / Đơn trình báo, Bản cam kết, giấy xác nhận… tải RIÊNG từng tệp → "File đính kèm khác"
  (target "supplementary").

Phân loại LLM-FIRST (LLM đọc OCR → type; KHÔNG dùng rule keyword). Type không rõ → "other" → "File đính kèm khác" ⇒
ĐÍNH ĐỦ, không rớt file nào. Mọi file luôn sinh 1 attachment item.

Cài đặt "Có tách hồ sơ khi đính kèm" (``options.splitDocuments`` là boolean true): tệp scan gộp được chia theo trang
trước rồi phân loại từng giấy (xem ``_plan_tach_giay_to``). Thiếu cờ → giữ nguyên tệp.
"""
import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import normalize_document_name
# Helper chia trang/cắt PDF của bộ tách HKD không gắn với giấy tờ HKD (prompt chia giấy là của thủ tục này).
from app.pipelines._shared import kinh_doanh_tach_giay_to as tach
from app.pipelines._shared.documents import join_ocr_documents
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SPLIT_SYSTEM_PROMPT, SYSTEM_PROMPT, build_split_user_prompt, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_ALLOWED_LLM_TYPES = {"identity", "application", "land_certificate", "cadastral_survey", "authorization"}

# componentName = MÃ TP-H05 (FE khớp substring đã fold: "tp h05.000040" nằm trong dòng tiêu đề thành phần).
_COMP_APPLICATION = "TP-H05.000026"   # Đơn đăng ký biến động đất đai (Mẫu số 18)
_COMP_LAND_CERT = "TP-H05.000040"     # Giấy chứng nhận đã cấp (GCN bị mất → thường không có)
_COMP_SURVEY = "TP-H05.000045"        # Mảnh trích đo bản đồ địa chính thửa đất

# type → (target, componentName, nhãn hiển thị mặc định).
# Form cấp lại có ô riêng cho Đơn (000026), GCN (000040), Mảnh trích đo (000045);
# CCCD/ủy quyền/Đơn trình báo/Bản cam kết/khác → "File đính kèm khác".
_ROUTE = {
    "application": ("existing", _COMP_APPLICATION, "Đơn đăng ký biến động Mẫu số 18"),
    "land_certificate": ("existing", _COMP_LAND_CERT, "Giấy chứng nhận đã cấp"),
    "cadastral_survey": ("existing", _COMP_SURVEY, "Mảnh trích đo bản đồ địa chính"),
    "identity": ("supplementary", "", "Căn cước công dân"),
    "authorization": ("supplementary", "", "Văn bản ủy quyền"),
    "other": ("supplementary", "", "Giấy tờ kèm theo đơn"),
}


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[:limit] + "..."


def _canonical_type(value: str) -> str:
    doc_type = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    return doc_type if doc_type in _ALLOWED_LLM_TYPES else "other"


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
        return {
            "type": _canonical_type(str(item.get("type") or "")),
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


def _build_item(file: dict, idx: int, doc_type: str, document_name: str) -> dict:
    target, component_name, _ = _ROUTE.get(doc_type, _ROUTE["other"])
    item = {
        "fileIndex": idx,
        "fileName": str(file.get("name") or f"file-{idx + 1}"),
        "documentName": document_name,
        "componentName": component_name,
        "target": target,
        "needsAddComponent": False,
        "detectedType": document_name,
    }
    if target == "existing":
        item["slotKey"] = "banChinh"  # gán vào ô Bản chính (không ký số) của nhóm
    return item


async def _plan_theo_tep(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
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
        detected = llm_types.get(idx) or {"type": "", "documentName": ""}
        # LLM-FIRST: type do LLM quyết. Không hợp lệ/không rõ → "other" → "File đính kèm khác"
        # (ĐÍNH ĐỦ, KHÔNG rớt file). KHÔNG dùng rule keyword để phân loại.
        llm_type = detected.get("type") or ""
        if llm_type in _ALLOWED_LLM_TYPES:
            doc_type = llm_type
            route_src = "llm"
        else:
            doc_type = "other"
            route_src = "default"

        _, _, fallback_label = _ROUTE.get(doc_type, _ROUTE["other"])
        # Giữ tên LLM đặt cả với type "other": khi tách giấy, Đơn trình báo / Bản cam kết / giấy xác nhận… cùng vào
        # "File đính kèm khác" — tên chung "Giấy tờ kèm theo đơn 2, 3" thì cán bộ không biết tệp nào là giấy nào.
        base_name = detected.get("documentName") or fallback_label
        document_name = _unique_document_name(base_name, used_names, fallback_label)

        item = _build_item(file, idx, doc_type, document_name)
        attachments.append(item)
        classified.append({
            "fileName": file.get("name"),
            "type": doc_type,
            "routeSrc": route_src,
            "documentName": document_name,
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
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "ocr_text": join_ocr_documents(ocr_results),
        "errors": errors,
    }


async def _chia_giay(pages_by_file: dict[int, list[str]]) -> dict[int, list[int]]:
    """LLM chỉ ra trang nào MỞ giấy mới → {tệp: [trang đầu 0-based]}."""
    total = sum(len(pages) for pages in pages_by_file.values())
    # temperature 0: chỉ ra số trang, cần ổn định giữa các lần chạy cùng tệp.
    raw = await client.chat(
        [
            {"role": "system", "content": SPLIT_SYSTEM_PROMPT},
            {"role": "user", "content": build_split_user_prompt(pages_by_file)},
        ],
        temperature=0,
        max_tokens=max(300, min(2000, 100 + 20 * total)),
        enable_thinking=settings.agent_reasoning,
    )
    return tach.page_starts(client.extract_json_block(raw), pages_by_file)


def _ve_tep_goc(item: dict, segments: list[dict]) -> dict:
    """Mục kế hoạch trên tệp ảo (một giấy đã cắt) → mục trên tệp gốc kèm sourceSegments."""
    segment = segments[int(item["fileIndex"])]
    out = {**item, "fileIndex": segment["source"]}
    if segment["pages"] is not None:
        out["sourceSegments"] = [{"fileIndex": segment["source"], "pageIndexes": segment["pages"]}]
    return out


async def _plan_tach_giay_to(files: list[FileItem], options: dict | None = None,
                             session: dict | None = None) -> dict:
    """Tách tệp scan gộp nhiều giấy rồi phân loại TỪNG giấy.

    Không tách thì cả bộ (Đơn + XN TTHN + cam kết + trình báo + CCCD) đính nguyên vào dòng Đơn TP-H05.000026.
    1. OCR tệp gốc một lần; LLM đọc đầu từng trang, chỉ ra trang nào mở giấy mới.
    2. Cắt mỗi đoạn thành PDF con, chạy ``_plan_theo_tep`` trên các PDF con (chữ OCR nạp sẵn qua
       ``ocr.preset_texts``, không OCR lần hai) → Đơn vào TP-H05.000026, giấy lẻ vào "File đính kèm khác"…
    3. Đổi kế hoạch về tệp gốc bằng ``sourceSegments``; extension cắt trang trước khi tải lên cổng.
    LLM chia lỗi / tệp ảnh / số trang OCR lệch PDF → tệp đó đính nguyên như không tách.
    """
    from app.services import ocr

    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl, "role": f.role} for f in files]
    ocr_pairs = [(idx, file) for idx, file in enumerate(raw_files) if file.get("type") in _OCR_TYPES]
    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file([file for _, file in ocr_pairs]) if ocr_pairs else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    texts = {
        idx: str(result.get("text") or "")
        for (idx, _), result in zip(ocr_pairs, ocr_results)
        if not result.get("error") and str(result.get("text") or "").strip()
    }
    pages_by_file = {
        idx: pages for idx, text in texts.items() if len(pages := tach.split_pages(text)) > 1
    }

    errors: list[str] = []
    t1 = time.monotonic()
    starts: dict[int, list[int]] = {}
    if pages_by_file:
        try:
            starts = await _chia_giay(pages_by_file)
        except Exception as e:  # noqa: BLE001 — chia giấy hỏng thì đính nguyên tệp
            errors.append(f"Tách giấy tờ: {e} — đính nguyên tệp.")
    split_ms = int((time.monotonic() - t1) * 1000)

    segments = tach.build_segments(raw_files, texts, starts)
    virtual = [FileItem(**segment["file"]) for segment in segments]
    with ocr.preset_texts({seg["file"]["dataUrl"]: seg["text"] for seg in segments if seg["text"]}):
        result = await _plan_theo_tep(virtual, options, session)

    result["attachments"] = [_ve_tep_goc(item, segments) for item in result.get("attachments") or []]
    result["extracted"] = {
        **(result.get("extracted") or {}),
        "documents": [file["name"] for file in raw_files],
        "attachmentMode": "split_documents",
        "tachGiayTo": [
            {"fileName": raw_files[seg["source"]]["name"],
             "pages": "cả tệp" if seg["pages"] is None else [p + 1 for p in seg["pages"]]}
            for seg in segments
        ],
    }
    result["errors"] = [*errors, *(result.get("errors") or [])]
    stats = dict(result.get("stats") or {})
    stats["ocr_latency_ms"] = int(stats.get("ocr_latency_ms") or 0) + ocr_ms
    stats["llm_latency_ms"] = int(stats.get("llm_latency_ms") or 0) + split_ms
    stats["total_latency_ms"] = int(stats.get("total_latency_ms") or 0) + ocr_ms + split_ms
    result["stats"] = stats
    return result


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    """Chỉ boolean ``True`` mới tách (và extension phải cắt được trang); client cũ giữ nguyên tệp."""
    planner = _plan_tach_giay_to if tach.split_requested(options) else _plan_theo_tep
    return await planner(files, options, session)

"""Đính kèm cho thủ tục Giải quyết chế độ trợ cấp thờ cúng liệt sĩ.

Bước "Thành phần hồ sơ" có 3 ô cố định + "Thêm giấy tờ":
- STT1 (fixed-slot 0): Văn bản ủy quyền.
- STT2 (fixed-slot 1): Đơn đề nghị Mẫu số 18.
- STT3 (fixed-slot 2): Bản sao chứng thực từ Bằng "Tổ quốc ghi công".
- CCCD, Trích lục khai tử, Đơn thay đổi người thờ cúng, giấy chưa rõ loại → cùng ô Đơn (cổng không phải lúc nào
  cũng có "Thêm giấy tờ").

Cài đặt "Có tách hồ sơ khi đính kèm" (``options.splitDocuments``, cách làm như thủ tục NCC từ trần cùng cổng): LLM
xếp loại TỪNG TRANG; mỗi giấy trong PDF gộp thành một tệp riêng chỉ gồm đúng các trang của nó (``sourceSegments``,
extension cắt PDF, tên tệp = documentName), bỏ trang trắng. Văn bản ủy quyền / Đơn / Bằng vào đúng ô của mình, giấy
còn lại vào ô Đơn như chế độ thường. Chia trang lỗi / số trang OCR lệch PDF → tệp đó đính nguyên.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.lao_cai_tach_giay_to import split_pages
from app.pipelines.di_chuyen_ho_so_nguoi_huong_tro_cap.attach.planner import split_requested, splittable_pages
from app.pipelines.tro_cap_tho_cung_liet_si.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
# Trang trắng / mặt sau in xuyên dấu: OCR chỉ ra vài chữ rác → không đưa vào tệp cắt.
_MIN_PAGE_CHARS = 40
# Trang LLM trả other mà ít chữ (mặt sau in xuyên, trang chỉ có dấu/chức danh) là trang nối tiếp của giấy liền trước,
# không tách thành tệp "Giấy tờ kèm theo" riêng.
_SHORT_OTHER_CHARS = 200

_UY_QUYEN = "van_ban_uy_quyen"
_DON = "don_de_nghi"
_BANG = "bang_tqgc"
_CCCD = "cccd"
_KHAI_TU = "trich_luc_khai_tu"
_DON_THAY_DOI = "don_thay_doi_nguoi_tho_cung"
_OTHER = "other"

SLOTS: list[dict[str, Any]] = [
    {
        "slotKey": _UY_QUYEN,
        "slotIndex": 0,
        "slotName": "Văn bản ủy quyền",
        "slotKeywords": ["van ban uy quyen"],
        "detectedType": "Văn bản ủy quyền",
        "documentName": "Văn bản ủy quyền thờ cúng liệt sĩ",
    },
    {
        "slotKey": _DON,
        "slotIndex": 1,
        "slotName": "Đơn đề nghị Mẫu số 18 Phụ lục I Nghị định số 131/2021/NĐ-CP",
        "slotKeywords": ["mau so 18 phu luc i", "don de nghi theo mau so 18"],
        "detectedType": "Đơn đề nghị giải quyết chế độ trợ cấp thờ cúng liệt sĩ",
        "documentName": "Đơn đề nghị giải quyết chế độ trợ cấp thờ cúng liệt sĩ (Mẫu số 18)",
    },
    {
        "slotKey": _BANG,
        "slotIndex": 2,
        "slotName": 'Bản sao chứng thực từ Bằng "Tổ quốc ghi công"',
        "slotKeywords": ["to quoc ghi cong"],
        "detectedType": 'Bằng "Tổ quốc ghi công"',
        "documentName": 'Bằng "Tổ quốc ghi công"',
    },
]
_SLOT_BY_KEY = {s["slotKey"]: s for s in SLOTS}

_NEW_DOCS: dict[str, dict[str, str]] = {
    _CCCD: {"documentName": "Căn cước công dân người nộp", "detectedType": "Căn cước công dân"},
    _KHAI_TU: {"documentName": "Trích lục khai tử thân nhân liệt sĩ", "detectedType": "Trích lục khai tử"},
    _DON_THAY_DOI: {"documentName": "Đơn đề nghị thay đổi người thờ cúng liệt sĩ",
                    "detectedType": "Đơn thay đổi người thờ cúng"},
}
_ALLOWED_DOC_TYPES = set(_SLOT_BY_KEY) | set(_NEW_DOCS) | {_OTHER}


def _is_identity_text(text: str) -> bool:
    haystack = _fold(text)
    return any(
        marker in haystack
        for marker in (
            "can cuoc cong dan",
            "chung minh nhan dan",
            "the can cuoc",
            "citizen identity card",
            "ho chieu",
            "passport",
        )
    )


def _rule_doc_type(text: str) -> str:
    """Phân loại nhanh bằng rule. Nhận diện Đơn TRƯỚC vì đơn cũng nhắc 'ủy quyền'/'Tổ quốc ghi công'."""
    haystack = _fold(text)
    if not haystack:
        return ""

    # 1. Đơn đề nghị trợ cấp thờ cúng (Mẫu 18). Đơn thay đổi người thờ cúng (không có Mẫu 18) cũng nhắc
    # "đơn đề nghị" + "thờ cúng liệt sĩ" → tách ra trước; PDF gộp mở đầu bằng Mẫu 18 vẫn là Đơn.
    if "thay doi nguoi tho cung" in haystack and "mau so 18" not in haystack:
        return _DON_THAY_DOI
    if ("don de nghi" in haystack and "tho cung liet si" in haystack) or "mau so 18" in haystack:
        return _DON

    # 2. Trích lục khai tử / giấy chứng tử.
    if "trich luc khai tu" in haystack or "giay chung tu" in haystack:
        return _KHAI_TU

    # 3. Văn bản ủy quyền.
    if "uy quyen" in haystack and ("tho cung" in haystack or "bien ban hop" in haystack or "gia dinh" in haystack):
        return _UY_QUYEN

    # 4. Bằng Tổ quốc ghi công.
    if "to quoc ghi cong" in haystack and ("bang so" in haystack or "quyet dinh so" in haystack):
        return _BANG

    # 5. CCCD/giấy tùy thân.
    if _is_identity_text(haystack):
        return _CCCD

    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if "thay doi" in text:
        return _DON_THAY_DOI
    if "don" in text and "tho cung" in text:
        return _DON
    if "khai tu" in text or "chung tu" in text:
        return _KHAI_TU
    # Biên bản họp gia đình / họp đồng thuận thống nhất người thờ cúng nằm chung ô Văn bản ủy quyền.
    if "uy quyen" in text or "bien ban hop" in text:
        return _UY_QUYEN
    if "bang" in text and ("to quoc" in text or "ghi cong" in text):
        return _BANG
    if any(k in text for k in ("can cuoc", "cccd", "cmnd", "ho chieu", "identity")):
        return _CCCD
    return value if value in _ALLOWED_DOC_TYPES else _OTHER


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=500, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    out: dict[int, str] = {}
    for item in parsed.get("documents", []) or []:
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        out[idx] = _normalize_doc_type(str(item.get("docType") or item.get("type") or ""))
    return out


def _build_fixed_item(file: dict, file_index: int, slot_key: str) -> dict:
    slot = _SLOT_BY_KEY[slot_key]
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": slot["documentName"],
        "componentName": slot["slotName"],
        "target": "fixed-slot",
        "needsAddComponent": False,
        "detectedType": slot["detectedType"],
        "slotKey": slot["slotKey"],
        "slotIndex": slot["slotIndex"],
        "slotName": slot["slotName"],
        "slotKeywords": slot["slotKeywords"],
    }


def _build_extra_item(file: dict, file_index: int, doc_type: str) -> dict:
    """Giấy kèm thêm (ngoài các ô cố định) và giấy chưa rõ loại đính chung ô Đơn."""
    item = _build_fixed_item(file, file_index, _DON)
    cfg = _NEW_DOCS.get(doc_type) or {"documentName": "Giấy tờ kèm theo", "detectedType": "Giấy tờ kèm theo"}
    item["documentName"] = cfg["documentName"]
    item["detectedType"] = cfg["detectedType"]
    return item


def _is_blank(page: str) -> bool:
    return len(re.findall(r"\w", page or "")) < _MIN_PAGE_CHARS


async def _classify_pages(pages_by_file: dict[int, list[str]]) -> dict[int, list[str]]:
    """LLM xếp loại TỪNG TRANG (trang nối tiếp mang loại của giấy chứa nó) → {tệp: [docType mỗi trang]}."""
    total = sum(len(p) for p in pages_by_file.values())
    messages = [
        {"role": "system", "content": prompt.SPLIT_SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_split_user_prompt(pages_by_file)},
    ]
    # temperature 0: cùng tệp phải ra cùng cách chia giữa các lần chạy.
    raw = await client.chat(messages, temperature=0, max_tokens=max(300, min(3000, 100 + 20 * total)),
                            enable_thinking=settings.agent_reasoning)
    out: dict[int, list[str]] = {}
    for item in client.extract_json_block(raw).get("tep", []) or []:
        try:
            idx = int(item.get("fileIndex"))
        except Exception:  # noqa: BLE001
            continue
        types = [_normalize_doc_type(str(t)) for t in item.get("trang") or []]
        # Số phần tử lệch số trang → không biết trang nào là gì, tệp đó đính nguyên như chế độ thường.
        if idx in pages_by_file and idx not in out and len(types) == len(pages_by_file[idx]):
            out[idx] = types
    return out


def _absorb_short_other(types: list[str], pages: list[str]) -> list[str]:
    out: list[str] = []
    for page, doc_type in enumerate(types):
        prev = next((t for t in reversed(out) if t != _OTHER), "")
        short = len(re.findall(r"\w", pages[page] or "")) < _SHORT_OTHER_CHARS
        out.append(prev if doc_type == _OTHER and prev and short else doc_type)
    return out


def _page_runs(types: list[str], pages: list[str]) -> list[dict]:
    """Các đoạn trang liền nhau cùng loại (trang 1-based, bỏ trang trắng) — ghi trace ``tachGiayTo``."""
    runs: list[dict] = []
    for page, doc_type in enumerate(types):
        if _is_blank(pages[page]):
            continue
        if runs and runs[-1]["docType"] == doc_type and runs[-1]["pages"][-1] == page:
            runs[-1]["pages"].append(page + 1)
        else:
            runs.append({"docType": doc_type, "pages": [page + 1]})
    return runs


def _split_file_items(file: dict, idx: int, pages: list[str], types: list[str]) -> tuple[list[dict], str, dict]:
    """Tệp đã xếp loại theo trang → mỗi giấy một mục chỉ gồm đúng các trang của nó: giấy có ô (ủy quyền, Đơn,
    Bằng) theo thứ tự ô, giấy còn lại theo thứ tự xuất hiện vào ô Đơn như chế độ thường."""
    file_name = str(file.get("name") or f"file-{idx + 1}")
    types = _absorb_short_other(types, pages)
    by_type: dict[str, list[int]] = {}
    for page, doc_type in enumerate(types):
        if not _is_blank(pages[page]):
            by_type.setdefault(doc_type, []).append(page)
    slot_order = list(_SLOT_BY_KEY)
    order = sorted(by_type, key=lambda t: (slot_order.index(t) if t in _SLOT_BY_KEY else len(slot_order),
                                           by_type[t][0]))
    items: list[dict] = []
    for doc_type in order:
        if doc_type in _SLOT_BY_KEY:
            item = _build_fixed_item(file, idx, doc_type)
        else:
            item = _build_extra_item(file, idx, doc_type)
        if by_type[doc_type] != list(range(len(pages))):
            item["sourceSegments"] = [{"fileIndex": idx, "pageIndexes": by_type[doc_type]}]
        items.append(item)
    entry = {"fileName": file_name, "docType": ",".join(order) or _OTHER, "source": "llm-pages",
             "tachGiayTo": _page_runs(types, pages)}
    warning = ""
    if not items or _OTHER in by_type:
        warning = f"Chưa xác định được loại giấy tờ của một số trang trong file '{file_name}' — đã đính vào dòng Đơn, cán bộ kiểm lại."
    return items, warning, entry


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, str] | None = None,
    page_types: dict[int, list[str]] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    page_types = page_types or {}
    by_name = {item.get("name"): item for item in ocr_results}
    items: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        text = str(by_name.get(file_name, {}).get("text") or "")
        if idx in page_types:
            split_items, warning, entry = _split_file_items(file, idx, split_pages(text), page_types[idx])
            items.extend(split_items)
            warnings.extend([warning] if warning else [])
            classified.append(entry)
            continue
        rule_type = _rule_doc_type(text)
        llm_type = llm_types.get(idx, "")
        doc_type = rule_type or (llm_type if llm_type in _ALLOWED_DOC_TYPES else _OTHER)

        if doc_type in _SLOT_BY_KEY:
            items.append(_build_fixed_item(file, idx, doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "source": "rule" if rule_type else "llm"})
            continue
        items.append(_build_extra_item(file, idx, doc_type))
        if doc_type in _NEW_DOCS:
            classified.append({"fileName": file_name, "docType": doc_type, "source": "rule" if rule_type else "llm"})
            continue

        warnings.append(f"Chưa xác định được loại giấy tờ của file '{file_name}' — đã đính vào dòng Đơn, cán bộ kiểm lại.")
        classified.append({"fileName": file_name, "docType": _OTHER, "source": "unknown"})

    return items, warnings, classified


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    """Entry point đính kèm cho tro-cap-tho-cung-liet-si."""
    _ = session
    split = split_requested(options)
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]

    from app.services import ocr

    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    ocr_by_name = {item.get("name"): item for item in ocr_results}
    texts = {idx: str(ocr_by_name.get(f.get("name"), {}).get("text") or "") for idx, f in enumerate(raw_files)}

    t1 = time.monotonic()
    page_types: dict[int, list[str]] = {}
    if split:
        # Tệp gộp hay khớp luật Đơn (trang đầu Mẫu 18) → tách thì xếp loại theo trang mọi tệp có chữ.
        pages_by_file = {
            idx: pages for idx, text in texts.items() if (pages := splittable_pages(raw_files[idx], text))
        }
        if pages_by_file:
            try:
                page_types = await _classify_pages(pages_by_file)
            except Exception as exc:  # noqa: BLE001 — chia trang hỏng thì đính nguyên tệp
                errors.append(f"Tách giấy tờ: {exc} — đính nguyên tệp.")
    llm_docs: list[dict[str, Any]] = [
        {"index": idx, "text": text}
        for idx, text in texts.items()
        if idx not in page_types and text.strip() and not _rule_doc_type(text)
    ]
    llm_types: dict[int, str] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types, page_types)
    errors.extend(warnings)
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [raw_files[doc["index"]]["name"] for doc in llm_docs],
            "classified": classified,
            "skippedOcr": skipped_ocr,
            "slots": SLOTS,
            "splitDocuments": split,
        },
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "errors": errors,
    }

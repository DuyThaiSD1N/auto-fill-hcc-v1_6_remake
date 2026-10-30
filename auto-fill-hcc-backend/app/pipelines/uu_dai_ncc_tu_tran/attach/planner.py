"""Đính kèm cho thủ tục Hưởng trợ cấp khi người có công đang hưởng trợ cấp ưu đãi từ trần.

Bước "Thành phần hồ sơ" có 2 ô cố định (2 nhánh trợ cấp: a) một lần/mai táng · b) tuất hằng tháng),
cả hai đều nhận Bản khai Mẫu 12 + trích lục khai tử. Vì không xác định được nhánh từ OCR, mặc định
đính Bản khai vào ô 1 (nhánh a — trợ cấp một lần, phổ biến); các giấy tờ còn lại (trích lục khai tử,
giấy khai sinh, CCCD, biên bản họp GĐ, danh sách, giấy chưa rõ loại) → cùng ô Bản khai (cổng không phải lúc
nào cũng có "Thêm giấy tờ").

Cài đặt "Có tách hồ sơ khi đính kèm" (``options.splitDocuments``, cách làm như thủ tục di chuyển hồ sơ cùng cổng): LLM
xếp loại TỪNG TRANG; mỗi giấy trong PDF gộp thành một tệp riêng chỉ gồm đúng các trang của nó (``sourceSegments``,
extension cắt PDF, tên tệp = documentName), bỏ trang trắng. Các tệp cắt vẫn cùng vào ô Bản khai như chế độ thường.
Chia trang lỗi / số trang OCR lệch PDF → tệp đó đính nguyên.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.lao_cai_tach_giay_to import split_pages
from app.pipelines.di_chuyen_ho_so_nguoi_huong_tro_cap.attach.planner import split_requested, splittable_pages
from app.pipelines.uu_dai_ncc_tu_tran.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
# Trang trắng / mặt sau hoa văn: OCR chỉ ra vài chữ rác → không đưa vào tệp cắt.
_MIN_PAGE_CHARS = 40

_BAN_KHAI = "ban_khai"
_KHAI_TU = "trich_luc_khai_tu"
_KHAI_SINH = "giay_khai_sinh"
_BIEN_BAN = "bien_ban_hop"
_DANH_SACH = "danh_sach"
_XAC_NHAN = "giay_xac_nhan"
_UY_QUYEN = "giay_uy_quyen"
_CCCD = "cccd"
_OTHER = "other"

SLOTS: list[dict[str, Any]] = [
    {
        "slotKey": _BAN_KHAI,
        "slotIndex": 0,
        "slotName": "Trợ cấp một lần, mai táng – Bản khai theo Mẫu số 12 Phụ lục I Nghị định số 131/2021/NĐ-CP",
        "slotKeywords": ["tro cap mot lan"],
        "detectedType": "Bản khai Mẫu số 12",
        "documentName": "Bản khai giải quyết chế độ ưu đãi khi người có công từ trần (Mẫu số 12)",
    },
]
_SLOT_BY_KEY = {s["slotKey"]: s for s in SLOTS}

_NEW_DOCS: dict[str, dict[str, str]] = {
    _KHAI_TU: {"documentName": "Trích lục khai tử/giấy báo tử", "detectedType": "Trích lục khai tử"},
    _KHAI_SINH: {"documentName": "Giấy khai sinh/trích lục khai sinh", "detectedType": "Giấy khai sinh"},
    _BIEN_BAN: {"documentName": "Biên bản họp gia đình", "detectedType": "Biên bản họp gia đình"},
    _DANH_SACH: {"documentName": "Danh sách đề nghị trợ cấp", "detectedType": "Danh sách đề nghị"},
    _XAC_NHAN: {"documentName": "Giấy xác nhận của UBND cấp xã", "detectedType": "Giấy xác nhận"},
    _UY_QUYEN: {"documentName": "Giấy ủy quyền", "detectedType": "Giấy ủy quyền"},
    _CCCD: {"documentName": "Căn cước công dân", "detectedType": "Căn cước công dân"},
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
    """Phân loại nhanh bằng rule. Nhận diện Bản khai TRƯỚC (đơn cũng nhắc khai tử/thân nhân)."""
    haystack = _fold(text)
    if not haystack:
        return ""

    # 1. Bản khai Mẫu 12.
    if ("ban khai" in haystack and ("tu tran" in haystack or "nguoi co cong" in haystack)) or "mau so 12" in haystack:
        return _BAN_KHAI

    # 2. Trích lục khai TỬ (ưu tiên trước khai sinh vì cùng chứa "khai").
    if "khai tu" in haystack or "giay chung tu" in haystack or "giay bao tu" in haystack:
        return _KHAI_TU

    # 3. Giấy khai SINH.
    if "khai sinh" in haystack:
        return _KHAI_SINH

    # 4. Biên bản họp gia đình.
    if "bien ban hop gia dinh" in haystack or ("bien ban" in haystack and "gia dinh" in haystack):
        return _BIEN_BAN

    # 5. Danh sách đề nghị.
    if "danh sach de nghi" in haystack and ("tro cap" in haystack or "mai tang" in haystack):
        return _DANH_SACH

    # 6. CCCD/giấy tùy thân.
    if _is_identity_text(haystack):
        return _CCCD

    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if "ban khai" in text or "mau so 12" in text:
        return _BAN_KHAI
    if "khai tu" in text or "chung tu" in text or "bao tu" in text:
        return _KHAI_TU
    if "khai sinh" in text:
        return _KHAI_SINH
    # "Biên bản ủy quyền" là giấy ủy quyền, không phải biên bản họp gia đình.
    if "uy quyen" in text:
        return _UY_QUYEN
    if "bien ban" in text:
        return _BIEN_BAN
    if "danh sach" in text:
        return _DANH_SACH
    if "xac nhan" in text:
        return _XAC_NHAN
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
    """Giấy kèm thêm (ngoài các ô cố định) và giấy chưa rõ loại đính chung ô Bản khai."""
    item = _build_fixed_item(file, file_index, _BAN_KHAI)
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
    """Tệp đã xếp loại theo trang → mỗi giấy một mục chỉ gồm đúng các trang của nó (Bản khai trước, còn lại theo
    thứ tự xuất hiện), tất cả vào ô Bản khai như chế độ thường."""
    file_name = str(file.get("name") or f"file-{idx + 1}")
    by_type: dict[str, list[int]] = {}
    for page, doc_type in enumerate(types):
        if not _is_blank(pages[page]):
            by_type.setdefault(doc_type, []).append(page)
    order = sorted(by_type, key=lambda t: (t != _BAN_KHAI, by_type[t][0]))
    items: list[dict] = []
    for doc_type in order:
        item = _build_fixed_item(file, idx, _BAN_KHAI) if doc_type == _BAN_KHAI else _build_extra_item(file, idx, doc_type)
        if by_type[doc_type] != list(range(len(pages))):
            item["sourceSegments"] = [{"fileIndex": idx, "pageIndexes": by_type[doc_type]}]
        items.append(item)
    entry = {"fileName": file_name, "docType": ",".join(order) or _OTHER, "source": "llm-pages",
             "tachGiayTo": _page_runs(types, pages)}
    warning = ""
    if not items or _OTHER in by_type:
        warning = f"Chưa xác định được loại giấy tờ của một số trang trong file '{file_name}' — đã đính vào dòng Bản khai, cán bộ kiểm lại."
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

        warnings.append(f"Chưa xác định được loại giấy tờ của file '{file_name}' — đã đính vào dòng Bản khai, cán bộ kiểm lại.")
        classified.append({"fileName": file_name, "docType": _OTHER, "source": "unknown"})

    return items, warnings, classified


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    """Entry point đính kèm cho uu-dai-ncc-tu-tran."""
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
        # Tệp gộp cũng hay khớp luật Bản khai (trang đầu) → tách thì xếp loại theo trang mọi tệp có chữ.
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

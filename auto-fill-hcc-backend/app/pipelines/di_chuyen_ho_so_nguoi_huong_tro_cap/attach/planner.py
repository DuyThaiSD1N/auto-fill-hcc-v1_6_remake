"""Đính kèm bước "Thành phần hồ sơ" cho thủ tục "Di chuyển hồ sơ khi người hưởng trợ cấp ưu đãi thay
đổi nơi thường trú" (cổng MOHA).

2 thành phần cố định (nút "Chọn tệp" — engine attach MOHA fixed-slot):
  slot 0  Bản sao chứng thực CCCD/CMND HOẶC giấy xác nhận của cơ quan đăng ký cư trú     ← cccd / xac_nhan_cu_tru
          (1 Bản sao — ưu tiên CCCD; dùng CT07 nếu cần xác nhận thêm; có thể đính cả 2)
  slot 1  Đơn đề nghị theo Mẫu số 27 Phụ lục I NĐ 131/2021/NĐ-CP (1 Bản chính)          ← don_mau_27

Giấy tờ nguồn khác (Bản khai thân nhân Mẫu 05, Giấy chứng nhận GĐ liệt sĩ, Giấy khai sinh, Bằng Tổ quốc
ghi công, Phiếu báo di chuyển hồ sơ...) KHÔNG có ô cố định riêng → BỎ QUA (skipped), KHÔNG route "new".
LLM phân loại MỌI tệp; luật dò chữ (`_rule_doc_type`) chỉ dự phòng cho tệp LLM không trả lời, không đè kết luận
đính được của LLM. Ngoại lệ là tệp GỘP nhiều trang mà LLM xếp loại không có ô (other / giấy nguồn khác): dò tiêu đề
từng trang, có trang là Đơn Mẫu 27 / CCCD / CT07 thì đính cả tệp vào ô đó (`_combined_slot_type`, luật 5 của prompt).

Cài đặt "Có tách hồ sơ khi đính kèm" (``options.splitDocuments``, cách làm như thủ tục Form.io iGate Lào Cai): LLM xếp
loại TỪNG TRANG; mỗi loại có ô nhận đúng các trang của nó qua ``sourceSegments`` (extension cắt PDF), bỏ trang trắng.
Trang thuộc giấy không có ô vẫn bỏ qua — cổng MOHA không có dòng "Giấy tờ khác". Chia trang lỗi / số trang OCR lệch
PDF → tệp đó đính nguyên như chế độ thường.
"""

import base64
import re
import time
from typing import Any

import fitz  # pymupdf

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.lao_cai_tach_giay_to import split_pages
from app.pipelines.di_chuyen_ho_so_nguoi_huong_tro_cap.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
# Trang trắng / mặt sau hoa văn: OCR chỉ ra vài chữ rác → không đưa vào tệp cắt.
_MIN_PAGE_CHARS = 40

_DON = "don_mau_27"
_CCCD = "cccd"
_CU_TRU = "xac_nhan_cu_tru"
_BAN_KHAI = "ban_khai"
_KHAI_SINH = "giay_khai_sinh"
_GCN_GD_LS = "gcn_gia_dinh_ls"
_TQGC = "to_quoc_ghi_cong"
_PHIEU_BAO = "phieu_bao_di_chuyen"
_OTHER = "other"

# Thứ tự dòng ĐÚNG như bảng Thành phần hồ sơ đang hiện trên cổng: dòng 1 bản sao CCCD / xác nhận cư trú, dòng 2 đơn Mẫu
# số 27 (cổng đã đổi thứ tự — trước đơn đứng trên). Extension không có từ khóa cho hai dòng này nên tìm ô theo slotIndex.
SLOTS: list[dict[str, Any]] = [
    {
        "slotKey": _CCCD,
        "slotIndex": 0,
        "slotName": "Bản sao được chứng thực từ căn cước công dân hoặc giấy xác nhận của cơ quan đăng ký cư trú",
        "detectedType": "CCCD/CMND hoặc Xác nhận cư trú",
        "documentName": "Bản sao chứng thực CCCD/CMND hoặc Xác nhận cư trú",
    },
    {
        "slotKey": _DON,
        "slotIndex": 1,
        "slotName": "Đơn đề nghị theo Mẫu số 27 Phụ lục I Nghị định số 131/2021/NĐ-CP",
        "detectedType": "Đơn đề nghị Mẫu số 27",
        "documentName": "Đơn đề nghị di chuyển hồ sơ (Mẫu số 27)",
    },
]
_SLOT_BY_KEY = {s["slotKey"]: s for s in SLOTS}

# CCCD và Xác nhận cư trú CT07 cùng vào dòng CCCD ("chọn 1 hoặc đính kèm cả 2", ưu tiên CCCD).
_ROUTE_TO_SLOT = {_DON: _DON, _CCCD: _CCCD, _CU_TRU: _CCCD}
# Giấy tờ nguồn KHÁC không có ô cố định → bỏ qua.
_SKIP_DOCS = {_BAN_KHAI, _KHAI_SINH, _GCN_GD_LS, _TQGC, _PHIEU_BAO}
_ALLOWED_DOC_TYPES = set(_ROUTE_TO_SLOT) | _SKIP_DOCS | {_OTHER}


def _is_identity_text(text: str) -> bool:
    haystack = _fold(text)
    return any(
        m in haystack
        for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "citizen identity", "ho chieu", "passport")
    )


def _rule_doc_type(text: str) -> str:
    """Dự phòng khi LLM không trả lời cho tệp này. Nhận Đơn Mẫu 27 và giấy tờ đặc trưng TRƯỚC, CCCD sau cùng."""
    h = _fold(text)
    if not h:
        return ""
    # Đơn đề nghị Mẫu số 27 — tiêu đề "ĐƠN ĐỀ NGHỊ" + "di chuyển hồ sơ" hoặc "mẫu số 27".
    if "mau so 27" in h or ("don de nghi" in h and "di chuyen ho so" in h):
        return _DON
    # Phiếu báo di chuyển hồ sơ (công văn) — tránh nhầm với Đơn.
    if "phieu bao di chuyen" in h or ("phieu bao" in h and "ho so" in h):
        return _PHIEU_BAO
    # Xác nhận thông tin về cư trú (Mẫu CT07).
    if "xac nhan thong tin ve cu tru" in h or "mau ct07" in h or "ct07" in h or "thong bao ve cu tru" in h:
        return _CU_TRU
    # Bằng Tổ quốc ghi công.
    if "to quoc ghi cong" in h or "bang to quoc" in h:
        return _TQGC
    # Giấy chứng nhận gia đình liệt sĩ.
    if "gia dinh liet si" in h or "chung nhan gia dinh" in h:
        return _GCN_GD_LS
    # Giấy khai sinh.
    if "giay khai sinh" in h or "trich luc khai sinh" in h or "ban sao khai sinh" in h:
        return _KHAI_SINH
    # Bản khai thân nhân / tình hình thân nhân liệt sĩ (Mẫu 05).
    if "ban khai" in h and ("than nhan" in h or "tinh hinh than nhan" in h or "mau so 05" in h):
        return _BAN_KHAI
    # CCCD/CMND (sau cùng vì đơn/bản khai cũng nhắc số CCCD).
    if _is_identity_text(h):
        return _CCCD
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if "mau so 27" in text or ("don" in text and "di chuyen" in text):
        return _DON
    if "phieu bao" in text:
        return _PHIEU_BAO
    if "cu tru" in text or "ct07" in text:
        return _CU_TRU
    if "to quoc ghi cong" in text:
        return _TQGC
    if "gia dinh liet si" in text:
        return _GCN_GD_LS
    if "khai sinh" in text:
        return _KHAI_SINH
    if "ban khai" in text:
        return _BAN_KHAI
    if any(k in text for k in ("can cuoc", "cccd", "cmnd", "ho chieu", "identity")):
        return _CCCD
    return value if value in _ALLOWED_DOC_TYPES else _OTHER


def _merge_page_types(types: list[str]) -> str:
    """Một tệp chỉ vào MỘT dòng: có Đơn → đơn, rồi CCCD, rồi CT07; không có thì lấy loại có nghĩa đầu tiên."""
    for doc_type in (_DON, _CCCD, _CU_TRU):
        if doc_type in types:
            return doc_type
    return next((t for t in types if t != _OTHER), _OTHER)


def _combined_slot_type(text: str) -> str:
    """Tệp gộp ≥2 trang: loại có ô cố định nhận ra từ TIÊU ĐỀ một trang nào đó (đơn → CCCD → CT07), không có → ""."""
    pages = split_pages(text)
    if len(pages) < 2:
        return ""
    found: list[str] = []
    for page in pages:
        head = _fold(page)[:400]
        if "mau so 27" in head or ("don de nghi" in head and "di chuyen" in head):
            found.append(_DON)
        elif "xac nhan thong tin ve cu tru" in head or "ct07" in head:
            found.append(_CU_TRU)
        elif _is_identity_text(head):
            found.append(_CCCD)
    return _merge_page_types(found) if found else ""


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=500, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    entries: list[tuple[int, str]] = []
    for item in parsed.get("documents", []) or []:
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        entries.append((idx, _normalize_doc_type(str(item.get("docType") or item.get("type") or ""))))
    requested = {int(doc["index"]) for doc in documents}
    # Model hay coi mốc "───── Trang i/n ─────" là ranh giới tài liệu và trả MỖI TRANG một phần tử → index lệch tệp.
    if len(entries) > len(documents) or any(idx not in requested for idx, _ in entries):
        if len(documents) == 1:
            return {next(iter(requested)): _merge_page_types([t for _, t in entries])}
        return {}
    return dict(entries)


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
    }


def split_requested(options: dict | None) -> bool:
    """Cài đặt "Có tách hồ sơ khi đính kèm" (``splitDocuments``) và extension cắt được trang (Auto Fill không gửi
    supportsSourceSegments nhưng luôn cắt được). Client cũ không gửi splitDocuments → đính nguyên tệp."""
    opts = options or {}
    return opts.get("splitDocuments") is True and opts.get("supportsSourceSegments") is not False


def _is_blank(page: str) -> bool:
    return len(re.findall(r"\w", page or "")) < _MIN_PAGE_CHARS


def _pdf_page_count(file: dict) -> int | None:
    header, sep, payload = str(file.get("dataUrl") or "").partition(",")
    if not sep or "pdf" not in (header.lower() + str(file.get("type") or "").lower()):
        return None
    try:
        with fitz.open(stream=base64.b64decode(payload), filetype="pdf") as doc:
            return doc.page_count
    except Exception:  # noqa: BLE001
        return None


def splittable_pages(file: dict, text: str) -> list[str]:
    """Trang OCR của tệp tách được; [] khi không có chữ hoặc số trang OCR lệch PDF (cắt theo chỉ số sẽ sai trang)."""
    if not text.strip():
        return []
    pages = split_pages(text)
    if len(pages) > 1 and _pdf_page_count(file) != len(pages):
        return []
    return pages


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
    """Tệp đã xếp loại theo trang → mỗi loại có ô (Đơn / CCCD / CT07) một mục chỉ gồm đúng các trang của nó."""
    file_name = str(file.get("name") or f"file-{idx + 1}")
    by_type: dict[str, list[int]] = {}
    for page, doc_type in enumerate(types):
        if not _is_blank(pages[page]):
            by_type.setdefault(doc_type, []).append(page)
    items: list[dict] = []
    for doc_type in (_DON, _CCCD, _CU_TRU):
        page_indexes = by_type.get(doc_type)
        if not page_indexes:
            continue
        item = _build_fixed_item(file, idx, _ROUTE_TO_SLOT[doc_type])
        if page_indexes != list(range(len(pages))):
            item["sourceSegments"] = [{"fileIndex": idx, "pageIndexes": page_indexes}]
        items.append(item)
    entry = {"fileName": file_name, "docType": ",".join(i["slotKey"] for i in items) or _OTHER,
             "source": "llm-pages", "tachGiayTo": _page_runs(types, pages)}
    warning = ""
    if not items:
        if by_type and set(by_type) <= _SKIP_DOCS:
            entry["skipped"] = True
        else:
            warning = f"Không xác định được loại giấy tờ cho file '{file_name}' — vui lòng đính kèm thủ công."
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
        if idx in llm_types:
            llm_type = llm_types[idx]
            doc_type, source = (llm_type if llm_type in _ALLOWED_DOC_TYPES else _OTHER), "llm"
        else:
            # LLM không trả lời cho tệp này (lỗi / thiếu) → mới dùng luật dò chữ.
            rule_type = _rule_doc_type(text)
            doc_type, source = (rule_type or _OTHER), ("rule" if rule_type else "unknown")

        if doc_type not in _ROUTE_TO_SLOT:
            combined_type = _combined_slot_type(text)
            if combined_type:
                doc_type, source = combined_type, "pages"

        slot_key = _ROUTE_TO_SLOT.get(doc_type)
        if slot_key:
            items.append(_build_fixed_item(file, idx, slot_key))
            classified.append({"fileName": file_name, "docType": doc_type, "source": source})
            continue
        if doc_type in _SKIP_DOCS:
            classified.append({"fileName": file_name, "docType": doc_type, "source": source, "skipped": True})
            continue

        warnings.append(f"Không xác định được loại giấy tờ cho file '{file_name}' — vui lòng đính kèm thủ công.")
        classified.append({"fileName": file_name, "docType": _OTHER, "source": source})

    return items, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
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
    llm_docs: list[dict[str, Any]] = []
    for idx, file in enumerate(raw_files):
        text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        if text.strip():
            llm_docs.append({"index": idx, "text": text})

    t1 = time.monotonic()
    page_types: dict[int, list[str]] = {}
    if split:
        pages_by_file = {
            doc["index"]: pages
            for doc in llm_docs
            if (pages := splittable_pages(raw_files[doc["index"]], doc["text"]))
        }
        if pages_by_file:
            try:
                page_types = await _classify_pages(pages_by_file)
            except Exception as exc:  # noqa: BLE001 — chia trang hỏng thì đính nguyên tệp
                errors.append(f"Tách giấy tờ: {exc} — đính nguyên tệp.")
    llm_types: dict[int, str] = {}
    whole_docs = [doc for doc in llm_docs if doc["index"] not in page_types]
    if whole_docs:
        try:
            llm_types = await _classify_with_llm(whole_docs)
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
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

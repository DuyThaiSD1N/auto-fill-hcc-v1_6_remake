"""Đính kèm cho thủ tục "Thực hiện, điều chỉnh, thôi hưởng trợ cấp hưu trí xã hội" (cổng BYT).

⚑ BẢNG THÀNH PHẦN HỒ SƠ CHỈ CÒN **ĐÚNG MỘT DÒNG** (chốt user 2026-09-15): "Văn bản đề nghị hưởng trợ
cấp hưu trí xã hội (theo Mẫu số 01 ban hành kèm theo Nghị định số 176/2025/NĐ-CP)". Cổng đã bỏ các
thành phần phụ và bỏ luôn nút "Thêm giấy tờ" → **MỌI FILE đều đính vào dòng 1** (fixed-slot,
slotIndex 0). Không còn nhánh `add-document-dialog` nào ở thủ tục này.

Phân loại LLM **chỉ còn để đặt TÊN HIỂN THỊ + cảnh báo**, không còn quyết định đích đến. (Với
target `fixed-slot`, FE upload bằng TÊN FILE GỐC — `documentName` chỉ hiện trong kế hoạch/trace.)

⚠ TUYỆT ĐỐI KHÔNG dùng lưới keyword để phân loại (chốt user 2026-09-15). Hai hàm
`is_excluded_document` / `detect_slot_key` bên dưới CHỈ còn để đối chứng, không nằm trong luồng.

Cài đặt "Có tách hồ sơ khi đính kèm" (``options.splitDocuments``, cách làm như thủ tục thờ cúng liệt sĩ cùng cổng):
PDF nhiều trang được LLM xếp loại TỪNG TRANG; mỗi giấy (Văn bản đề nghị, Giấy ủy quyền, CCCD…) thành một tệp riêng
chỉ gồm đúng các trang của nó (``sourceSegments``, extension cắt PDF, tên tệp = documentName), bỏ trang trắng. Vẫn
cùng dòng 1, Văn bản đề nghị đứng đầu. Chia trang lỗi / số trang OCR lệch PDF → tệp đó đính nguyên như chế độ thường.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.lao_cai_tach_giay_to import split_pages
from app.pipelines.di_chuyen_ho_so_nguoi_huong_tro_cap.attach.planner import split_requested, splittable_pages
from app.pipelines.dieu_chinh_huu_tri_xa_hoi.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
# Trang trắng / mặt sau in xuyên dấu: OCR chỉ ra vài chữ rác → không đưa vào tệp cắt.
_MIN_PAGE_CHARS = 40
# Trang LLM trả other mà ít chữ (trang chỉ có dấu/chức danh) là trang nối tiếp của giấy liền trước.
_SHORT_OTHER_CHARS = 200

_TYPE_GIAY_TO_TUY_THAN = "giay_to_tuy_than"
_TYPE_UY_QUYEN = "giay_uy_quyen"
_TYPE_OTHER = "other"

_IDENTITY_LABEL = "Giấy tờ tùy thân có ảnh (CCCD/CMND/Hộ chiếu)"
# Tên tệp cắt khi tách (extension đặt tên tệp = documentName) → không chứa "/".
_SPLIT_LABELS = {
    _TYPE_UY_QUYEN: "Giấy ủy quyền",
    _TYPE_GIAY_TO_TUY_THAN: "Căn cước công dân",
    _TYPE_OTHER: "Giấy tờ kèm theo",
}

SLOT = {
    "slotKey": "van_ban_de_nghi_huu_tri",
    "slotIndex": 0,
    # Text VERBATIM dòng duy nhất của cổng (đã đổi theo Nghị định 176/2025/NĐ-CP). FE dùng slotIndex
    # (slotKey không nằm trong FIXED_SLOT_KEYWORDS) nên đây chủ yếu để hiển thị/đối chiếu trace.
    "slotName": (
        "Văn bản đề nghị hưởng trợ cấp hưu trí xã hội "
        "(theo Mẫu số 01 ban hành kèm theo Nghị định số 176/2025/NĐ-CP)"
    ),
    "detectedType": "Văn bản đề nghị trợ cấp hưu trí xã hội",
}



def is_excluded_document(text: str, file_name: str = "") -> bool:
    """⚠ KHÔNG CÒN DÙNG TRONG LUỒNG QUYẾT ĐỊNH — giữ lại chỉ để tham chiếu/đối chứng.

    Lưới keyword này từng quét OCR tìm "can cuoc cong dan"/"the can cuoc"… để coi file là giấy tờ tùy
    thân. Nó SAI ở mọi giấy tờ hành chính có NHẮC số căn cước của người khác: hồ sơ thật
    (req_1d66e02a4271) nộp TRÍCH LỤC KHAI TỬ có dòng "Giấy tờ tùy thân: Thẻ căn cước công dân số …"
    → bị xếp thành CCCD và đính vào dòng "Một trong các giấy tờ có ảnh…". Việc phân loại giờ do LLM
    đảm nhiệm hoàn toàn (prompt.py có type giay_to_tuy_than + khối <traps>).
    """
    _ = file_name
    haystack = _fold(text or "")
    if not haystack:
        return False
    return any(
        marker in haystack
        for marker in (
            "can cuoc cong dan",
            "cccd",
            "chung minh nhan dan",
            "the can cuoc",
            "citizen identity card",
            "identity card",
            "ho chieu",
            "passport",
        )
    )


def detect_slot_key(text: str, file_name: str = "") -> str:
    """⚠ KHÔNG CÒN DÙNG TRONG LUỒNG QUYẾT ĐỊNH — giữ lại chỉ để tham chiếu/đối chứng.

    Lưới keyword nhận diện văn bản đề nghị từ OCR text. Đã gỡ khỏi `build_plan_items` (chốt user
    2026-09-15: "đừng dùng keyword, dùng LLM"). Phân loại giờ do LLM đảm nhiệm 100%; LLM im lặng thì
    file rơi về dòng Văn bản đề nghị kèm cảnh báo, KHÔNG đoán bằng keyword.
    """
    _ = file_name
    haystack = _fold(text or "")
    if not haystack:
        return ""
    # Mẫu số 01 là biểu mẫu duy nhất của thủ tục này. Chặn sớm để tiêu đề chung
    # không làm rule fallback nhận nhầm một mẫu khác ghi rõ Mẫu số 02.
    if "mau so 02" in haystack and "mau so 01" not in haystack:
        return ""
    if (
        "van ban de nghi huong tro cap huu tri xa hoi" in haystack
        or "de nghi huong tro cap huu tri xa hoi" in haystack
        or "de nghi nhan tro cap huu tri xa hoi tai noi cu tru moi" in haystack
        or "de nghi thay doi thong tin nguoi dang huong tro cap huu tri xa hoi" in haystack
        or (
            "mau so 01" in haystack
            and "tro cap huu tri xa hoi" in haystack
            and (
                "thong tin nguoi de nghi" in haystack
                or "thong tin nguoi dang huong" in haystack
            )
        )
    ):
        return SLOT["slotKey"]
    return ""


def _slot_from_llm_type(value: str) -> str:
    """Chuẩn hoá type LLM → "" (other) | slotKey văn bản đề nghị | giay_to_tuy_than."""
    raw = str(value or "").strip()
    if raw == SLOT["slotKey"]:
        return SLOT["slotKey"]
    if raw == _TYPE_GIAY_TO_TUY_THAN:
        return _TYPE_GIAY_TO_TUY_THAN
    text = _fold(raw)
    if "van ban de nghi" in text and "huu tri" in text:
        return SLOT["slotKey"]
    if "tro cap huu tri" in text and "de nghi" in text:
        return SLOT["slotKey"]
    if "giay to tuy than" in text or "can cuoc" in text or "ho chieu" in text:
        return _TYPE_GIAY_TO_TUY_THAN
    return ""


async def _classify_documents_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=300, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    out: dict[int, str] = {}
    for item in parsed.get("documents", []) or []:
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        out[idx] = _slot_from_llm_type(str(item.get("type") or ""))
    return out


def _build_item(file: dict, file_index: int, document_name: str = "") -> dict:
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    label = document_name or SLOT["detectedType"]
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": label,
        "componentName": SLOT["slotName"],
        "target": "fixed-slot",
        "needsAddComponent": False,
        "detectedType": label,
        "slotKey": SLOT["slotKey"],
        "slotIndex": SLOT["slotIndex"],
        "slotName": SLOT["slotName"],
    }


def _page_type(value: str) -> str:
    """Type LLM của một trang → slotKey văn bản đề nghị | giay_to_tuy_than | giay_uy_quyen | other."""
    slot = _slot_from_llm_type(value)
    if slot:
        return slot
    if str(value or "").strip() == _TYPE_UY_QUYEN or "uy quyen" in _fold(value or ""):
        return _TYPE_UY_QUYEN
    return _TYPE_OTHER


async def _classify_pages(pages_by_file: dict[int, list[str]]) -> dict[int, list[str]]:
    """LLM xếp loại TỪNG TRANG (trang nối tiếp mang loại của giấy chứa nó) → {tệp: [type mỗi trang]}."""
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
        types = [_page_type(str(t)) for t in item.get("trang") or []]
        # Số phần tử lệch số trang → không biết trang nào là gì, tệp đó đính nguyên như chế độ thường.
        if idx in pages_by_file and idx not in out and len(types) == len(pages_by_file[idx]):
            out[idx] = types
    return out


def _is_blank(page: str) -> bool:
    return len(re.findall(r"\w", page or "")) < _MIN_PAGE_CHARS


def _absorb_short_other(types: list[str], pages: list[str]) -> list[str]:
    out: list[str] = []
    for page, doc_type in enumerate(types):
        prev = next((t for t in reversed(out) if t != _TYPE_OTHER), "")
        short = len(re.findall(r"\w", pages[page] or "")) < _SHORT_OTHER_CHARS
        out.append(prev if doc_type == _TYPE_OTHER and prev and short else doc_type)
    return out


def split_log(files: list[dict], ocr_results: list[dict], page_types: dict[int, list[str]]) -> list[dict]:
    """Các đoạn trang liền nhau cùng loại của mỗi tệp đã tách (trang 1-based, bỏ trang trắng) — ghi trace."""
    by_name = {item.get("name"): item for item in ocr_results}
    log: list[dict] = []
    for idx, raw_types in page_types.items():
        file_name = str(files[idx].get("name") or f"file-{idx + 1}")
        pages = split_pages(str(by_name.get(file_name, {}).get("text") or ""))
        runs: list[dict] = []
        for page, doc_type in enumerate(_absorb_short_other(raw_types, pages)):
            if _is_blank(pages[page]):
                continue
            if runs and runs[-1]["docType"] == doc_type and runs[-1]["pages"][-1] == page:
                runs[-1]["pages"].append(page + 1)
            else:
                runs.append({"docType": doc_type, "pages": [page + 1]})
        log.append({"fileName": file_name, "tachGiayTo": runs})
    return log


def _split_file_items(file: dict, idx: int, pages: list[str], types: list[str]) -> tuple[list[dict], list[str]]:
    """Tệp đã xếp loại theo trang → mỗi giấy một mục chỉ gồm đúng các trang của nó, cùng dòng 1: Văn bản đề nghị
    đứng đầu, giấy còn lại theo thứ tự xuất hiện."""
    file_name = str(file.get("name") or f"file-{idx + 1}")
    by_type: dict[str, list[int]] = {}
    for page, doc_type in enumerate(_absorb_short_other(types, pages)):
        if not _is_blank(pages[page]):
            by_type.setdefault(doc_type, []).append(page)
    order = sorted(by_type, key=lambda t: (t != SLOT["slotKey"], by_type[t][0]))
    items: list[dict] = []
    for doc_type in order:
        item = _build_item(file, idx, "" if doc_type == SLOT["slotKey"] else _SPLIT_LABELS[doc_type])
        if by_type[doc_type] != list(range(len(pages))):
            item["sourceSegments"] = [{"fileIndex": idx, "pageIndexes": by_type[doc_type]}]
        items.append(item)
    warnings: list[str] = []
    if SLOT["slotKey"] not in by_type:
        warnings.append(
            f"File '{file_name}' không có trang nào là Văn bản đề nghị (Mẫu số 01) — các giấy tách ra vẫn đính "
            "vào dòng duy nhất của thủ tục; cán bộ kiểm tra lại."
        )
    if _TYPE_OTHER in by_type:
        warnings.append(
            f"Chưa xác định được loại giấy tờ của một số trang trong file '{file_name}' — đã tách thành "
            f"'{_SPLIT_LABELS[_TYPE_OTHER]}' và đính vào dòng duy nhất; cán bộ kiểm tra lại."
        )
    return items, warnings


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_slots: dict[int, str] | None = None,
    page_types: dict[int, list[str]] | None = None,
) -> tuple[list[dict], list[str]]:
    """MỌI FILE đều đính vào dòng 1 — bảng của thủ tục này chỉ còn đúng một dòng.

    LLM chỉ dùng để đặt tên hiển thị và cảnh báo giấy tờ không phải Văn bản đề nghị; nó KHÔNG còn
    quyết định đích đến, và KHÔNG có lưới keyword nào tham gia. ``page_types`` (chỉ có khi bật tách) chia
    tệp theo trang do LLM xếp loại; OCR text chỉ dùng để cắt trang, không để suy loại.
    """
    llm_slots = llm_slots or {}
    page_types = page_types or {}
    by_name = {item.get("name"): item for item in ocr_results}
    items: list[dict] = []
    warnings: list[str] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        if idx in page_types:
            pages = split_pages(str(by_name.get(file_name, {}).get("text") or ""))
            split_items, split_warnings = _split_file_items(file, idx, pages, page_types[idx])
            items.extend(split_items)
            warnings.extend(split_warnings)
            continue
        doc_type = llm_slots.get(idx, "")

        if doc_type == SLOT["slotKey"]:
            items.append(_build_item(file, idx))
            continue

        # Không phải Văn bản đề nghị nhưng VẪN đính (dòng 1 là chỗ duy nhất) — tuyệt đối không bỏ sót
        # file. Tên hiển thị giữ khác nhau để cán bộ soát được trong danh sách kế hoạch.
        if doc_type == _TYPE_GIAY_TO_TUY_THAN:
            label = _IDENTITY_LABEL
            reason = "là giấy tờ tùy thân"
        else:
            label = f"Tài liệu khác - {file_name}"
            reason = "chưa nhận diện chắc loại giấy tờ"
        items.append(_build_item(file, idx, label))
        warnings.append(
            f"File '{file_name}' {reason}, không phải Văn bản đề nghị (Mẫu số 01) — vẫn đính vào dòng "
            "duy nhất của thủ tục; cán bộ kiểm tra lại."
        )

    return items, warnings


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    """Entry point đính kèm cho dieu-chinh-huu-tri-xa-hoi."""
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
        # Chỉ tệp nhiều trang mới có thể gộp nhiều giấy; tệp một trang đi phân loại thường.
        pages_by_file = {
            idx: pages for idx, text in texts.items()
            if len(pages := splittable_pages(raw_files[idx], text)) > 1
        }
        if pages_by_file:
            try:
                page_types = await _classify_pages(pages_by_file)
            except Exception as exc:  # noqa: BLE001 — chia trang hỏng thì đính nguyên tệp
                errors.append(f"Tách giấy tờ: {exc} — đính nguyên tệp.")
    llm_docs: list[dict[str, Any]] = [
        {"index": idx, "text": text}
        for idx, text in texts.items()
        if idx not in page_types and text.strip()
    ]

    llm_slots: dict[int, str] = {}
    if llm_docs:
        try:
            llm_slots = await _classify_documents_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings = build_plan_items(raw_files, ocr_results, llm_slots, page_types)
    errors.extend(warnings)
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES]
    ocr_text = "\n\n---\n\n".join(
        f"===== {r.get('name') or '(không tên)'} =====\n{str(r.get('text') or '').strip()}"
        for r in ocr_results
        if r.get("text")
    )

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [raw_files[doc["index"]]["name"] for doc in llm_docs],
            "skippedOcr": skipped_ocr,
            "slots": [SLOT["slotName"]],
            "splitDocuments": split,
            "tachGiayTo": split_log(raw_files, ocr_results, page_types),
        },
        "ocr_text": ocr_text,
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "errors": errors,
    }

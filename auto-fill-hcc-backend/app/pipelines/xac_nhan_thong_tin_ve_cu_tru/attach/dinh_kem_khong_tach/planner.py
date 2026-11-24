"""Đính kèm Xác nhận thông tin về cư trú — chế độ KHÔNG tách (đính nguyên tệp).

Trang kê khai dang-ky-thuong-tru.html?TT=THUONGTRU_09 (ảnh chạy thật 24/11/2026): mục "Trường hợp và hồ sơ đính kèm" là
MỘT bảng hiện sẵn (div#div_TPHS_OLD > table#tblGiayToDinhKem), KHÔNG chia nhóm như Đăng ký thường trú — chỉ có dòng
"1. Tờ khai thay đổi thông tin cư trú" và nút "+" thêm dòng. Gửi số nhóm của trang thường trú làm extension gọi
load_table_tphs_new(i) → trang lỗi "Cannot read properties of undefined (reading 'CODE')", không đính được tệp nào.
Vì vậy mọi mục mang `bcaPlainTable` (extension lấy bảng đang hiện, không bấm nhóm) như Tách hộ / Điều chỉnh cư trú.

LLM đọc OCR theo trang, liệt kê giấy tờ trong từng tệp. Tờ khai → dòng sẵn có; giấy chỗ ở hợp pháp, hợp đồng thuê /
mượn / ở nhờ, giấy diện tích nhà ở, giấy kết hôn, CCCD, ủy quyền, giấy chưa rõ loại… → dòng "+" mang tên giấy, mọi giấy
như vậy của CÙNG tệp chung một dòng (đính nguyên tệp một lần). Tệp gộp có cả tờ khai thì đính vào cả hai dòng, Ghi chú
"Đính kèm chung tệp …: <giấy> tại trang a/N". LLM lỗi → mọi tệp vào dòng Tờ khai + cảnh báo. Không bỏ tệp nào.
"""

import time

from app.config import settings
from app.pipelines.dang_ky_thuong_tru.attach.planner import _clean_name
from app.pipelines.dieu_chinh_thong_tin_ve_cu_tru.attach.dinh_kem_khong_tach.planner import _page_numbers, ocr_pages
from app.pipelines.khai_sinh_dvc_moi.attach.dinh_kem_tach.planner import _OCR_TYPES
from app.pipelines.tach_ho.attach.dinh_kem_khong_tach.planner import _shared_note, finalize_rows
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

TO_KHAI = "to_khai"
SO_HUU = "so_huu"
CHO_O = "cho_o"
HOP_DONG = "hop_dong"
DIEN_TICH = "dien_tich"
NHAN_THAN = "nhan_than"
UY_QUYEN = "uy_quyen"
CCCD = "cccd"
OTHER = "other"
DOC_TYPES = {TO_KHAI, SO_HUU, CHO_O, HOP_DONG, DIEN_TICH, NHAN_THAN, UY_QUYEN, CCCD, OTHER}

# Bảng một trường hợp hiện sẵn → extension lấy bảng đang hiện, không bấm mở nhóm.
GROUP = {"groupIndex": 0, "groupLabel": "Xác nhận thông tin về cư trú", "bcaPlainTable": True}

# componentName = nhãn dòng trên cổng; rowKey = cụm chữ (bỏ dấu, bỏ dấu câu) có trong dòng.
ROWS: dict[str, dict[str, str]] = {
    TO_KHAI: {"componentName": "Tờ khai thay đổi thông tin cư trú", "rowKey": "to khai thay doi thong tin cu tru"},
}
LLM_FAILED_ROW = TO_KHAI

DOCUMENT_NAMES = {
    TO_KHAI: "Tờ khai thay đổi thông tin cư trú",
    SO_HUU: "Giấy tờ chứng minh chỗ ở hợp pháp",
    CHO_O: "Giấy tờ chứng minh chỗ ở hợp pháp",
    HOP_DONG: "Hợp đồng cho thuê cho mượn cho ở nhờ",
    DIEN_TICH: "Giấy tờ chứng minh đủ diện tích nhà ở",
    NHAN_THAN: "Giấy tờ hộ tịch",
    UY_QUYEN: "Giấy ủy quyền",
    CCCD: "Thẻ căn cước",
    OTHER: "Giấy tờ khác",
}
NEW_ROW_NAME_MAX = 100


def doc_type(doc: dict) -> str:
    kind = str(doc.get("docType") or "").strip()
    return kind if kind in DOC_TYPES else OTHER


def plan_item(file_index: int, file_name: str, document_name: str, row_type: str, detected: str = "") -> dict:
    row = ROWS[row_type]
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name or file_name,
        "componentName": row["componentName"],
        "target": "bca-row",
        "needsAddComponent": False,
        "newRow": False,
        "rowKey": row["rowKey"],
        "detectedType": detected or row_type,
        **GROUP,
    }


def new_row_item(file_index: int, file_name: str, document_name: str, detected: str) -> dict:
    """Dòng thêm bằng nút "+" của bảng, tên dòng = tên giấy (extension gom các mục cùng tên vào một dòng)."""
    name = (document_name or file_name)[:NEW_ROW_NAME_MAX].strip(" ,")
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": name,
        "componentName": name,
        "target": "bca-row",
        "needsAddComponent": True,
        "newRow": True,
        "rowKey": "",
        "detectedType": detected,
        **GROUP,
    }


def missing_warnings(items: list[dict]) -> list[str]:
    """Dòng sẵn có của bảng chưa có giấy (tờ khai là giấy bắt buộc)."""
    filled = {item["rowKey"] for item in items}
    missing = [row["componentName"] for row in ROWS.values() if row["rowKey"] not in filled]
    return ["Hồ sơ chưa có giấy cho dòng: " + "; ".join(missing)] if missing else []


def build_plan_items(file_names: list[str], page_counts: dict[int, int], documents: list[dict],
                     llm_ok: bool = True) -> tuple[list[dict], list[str], list[dict]]:
    """Mỗi tệp → một mục cho MỖI dòng mà tệp chứa giấy (dòng Tờ khai hoặc dòng "+"); không bỏ tệp nào."""
    docs_all = [d for d in documents if isinstance(d, dict)]
    items: list[dict] = []
    notes: list[str] = []
    classified: list[dict] = []
    unknown: list[str] = []
    other_rows: list[str] = []
    for index, file_name in enumerate(file_names):
        total = page_counts.get(index, 0)
        docs = [d for d in docs_all if str(d.get("fileIndex")) == str(index)]
        if not llm_ok or not docs:
            # LLM lỗi / không nhận ra giấy nào trong tệp → dòng Tờ khai (luôn có) + cảnh báo.
            items.append(plan_item(index, file_name, file_name, LLM_FAILED_ROW, OTHER))
            notes.append("")
            classified.append({"fileName": file_name, "docTypes": [OTHER], "routedTo": LLM_FAILED_ROW})
            unknown.append(file_name)
            continue
        by_row: dict[str, list[dict]] = {}
        extras: list[dict] = []
        for doc in docs:
            kind = doc_type(doc)
            if kind in ROWS:
                by_row.setdefault(kind, []).append(doc)
            else:
                extras.append(doc)
        shared = len(docs) > 1
        for row_type, row_docs in ((r, by_row[r]) for r in ROWS if r in by_row):
            names = [_clean_name(d.get("documentName")) or DOCUMENT_NAMES[row_type] for d in row_docs]
            items.append(plan_item(index, file_name, names[0], row_type))
            notes.append(_shared_note(file_name, total, names,
                                      [p for d in row_docs for p in _page_numbers(d, total)], shared))
        if extras:
            # Mọi giấy không có dòng của CÙNG tệp → một dòng "+" (đính nguyên tệp một lần), tên liệt kê các giấy.
            names = list(dict.fromkeys(_clean_name(d.get("documentName")) or DOCUMENT_NAMES[doc_type(d)]
                                       for d in extras))
            items.append(new_row_item(index, file_name, ", ".join(names), doc_type(extras[0])))
            notes.append(_shared_note(file_name, total, names,
                                      [p for d in extras for p in _page_numbers(d, total)], shared))
            if any(doc_type(d) == OTHER for d in extras):
                other_rows.append(file_name)
        classified.append({"fileName": file_name, "docTypes": sorted({doc_type(d) for d in docs}),
                           "rows": [r for r in ROWS if r in by_row] + (["new_row"] if extras else [])})
    finalize_rows(items, notes)
    warnings = missing_warnings(items)
    if unknown:
        reason = "Giấy tờ chưa rõ loại" if llm_ok else "Chưa phân loại được giấy tờ"
        warnings.append(f"{reason} — đã đính vào dòng \"{ROWS[LLM_FAILED_ROW]['componentName']}\": "
                        + ", ".join(unknown))
    if other_rows:
        warnings.append("Giấy tờ chưa rõ loại đã đính vào dòng \"+\" (giấy tờ khác): " + ", ".join(other_rows))
    return items, warnings, classified


async def _classify_all(pages_by_file: dict[int, list[str]]) -> list[dict]:
    payload = [{"fileIndex": i, "pages": [{"page": n + 1, "text": t[:2500]} for n, t in enumerate(pages)]}
               for i, pages in pages_by_file.items()]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(payload)},
    ]
    max_tokens = max(900, min(4000, sum(len(p) for p in pages_by_file.values()) * 150))
    raw = await client.chat(messages, max_tokens=max_tokens, enable_thinking=settings.agent_reasoning)
    data = client.extract_json_block(raw) or {}
    return [d for d in data.get("documents") or [] if isinstance(d, dict)]


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    from app.services import ocr

    _ = options, session
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    errors: list[str] = []
    pairs = [(i, f) for i, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]
    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file([f for _, f in pairs]) if pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    pages_by_file: dict[int, list[str]] = {}
    for (index, file), result in zip(pairs, ocr_results):
        if result.get("error"):
            errors.append(f"OCR {file.get('name')}: {result['error']}")
        if str(result.get("text") or "").strip():
            pages_by_file[index] = ocr_pages(str(result["text"]))

    started = time.monotonic()
    documents: list[dict] = []
    llm_ok = True
    if pages_by_file:
        try:
            documents = await _classify_all(pages_by_file)
        except Exception as exc:  # noqa: BLE001 — LLM lỗi thì mọi tệp vẫn được đính vào dòng Tờ khai
            errors.append(f"attachment_agent: {exc}")
            llm_ok = False
    else:
        llm_ok = False
    llm_ms = int((time.monotonic() - started) * 1000)

    names = [str(f.get("name") or f"file-{i + 1}") for i, f in enumerate(raw_files)]
    page_counts = {i: len(p) for i, p in pages_by_file.items()}
    attachments, warnings, classified = build_plan_items(names, page_counts, documents, llm_ok)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {"documents": names, "classified": classified},
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

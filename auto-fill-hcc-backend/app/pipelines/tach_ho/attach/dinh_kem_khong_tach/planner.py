"""Đính kèm Tách hộ — chế độ KHÔNG tách (đính nguyên tệp).

Mục "Trường hợp và hồ sơ đính kèm" của trang tách hộ có 3 dòng cố định (ảnh chạy thật 20/11/2026, bảng
#tblGiayToDinhKem hiện sẵn, dòng cuối có nút "+" thêm dòng):
  1. Tờ khai thay đổi thông tin cư trú
  2. Giấy tờ, tài liệu chứng minh việc tiếp tục được sử dụng chỗ ở hợp pháp đó
  3. Giấy tờ, tài liệu chứng minh việc ly hôn
Mapping không ghi "Loại giấy tờ" → để mặc định của cổng, chỉ ghi Số lượng / Ghi chú.

LLM đọc OCR theo trang và liệt kê giấy tờ trong từng tệp. Tệp gộp nhiều giấy được đính NGUYÊN tệp vào MỌI dòng mà nó
chứa giấy, Ghi chú "Đính kèm chung tệp …: <giấy> tại trang a/N". Giấy có loại rõ mà bảng không có dòng (giấy khai sinh,
giấy kết hôn, CCCD…) → dòng "+" mang tên giấy (KHÔNG dồn vào dòng ly hôn). Giấy chưa rõ loại → dòng chỗ ở hợp pháp +
cảnh báo; LLM lỗi → mọi tệp vào dòng Tờ khai + cảnh báo. Không bỏ tệp nào.

Plan item target "bca-row" do extension (attachFilesByBcaPlan) thi hành như Điều chỉnh thông tin cư trú
(`bcaPlainTable`: lấy bảng đang hiện, không bấm nhóm).
"""

import time

from app.config import settings
from app.pipelines.dang_ky_thuong_tru.attach.planner import _clean_name
from app.pipelines.dieu_chinh_thong_tin_ve_cu_tru.attach.dinh_kem_khong_tach.planner import (
    _page_numbers,
    ocr_pages,
    page_label,
)
from app.pipelines.khai_sinh_dvc_moi.attach.dinh_kem_tach.planner import _OCR_TYPES
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

TO_KHAI = "to_khai"
CHO_O = "cho_o"
LY_HON = "ly_hon"
NHAN_THAN = "nhan_than"
CCCD = "cccd"
OTHER = "other"
DOC_TYPES = {TO_KHAI, CHO_O, LY_HON, NHAN_THAN, CCCD, OTHER}

# componentName = nhãn dòng trên cổng; rowKey = cụm chữ (bỏ dấu, bỏ dấu câu) có trong dòng.
ROWS: dict[str, dict[str, str]] = {
    TO_KHAI: {"componentName": "Tờ khai thay đổi thông tin cư trú", "rowKey": "to khai thay doi thong tin cu tru"},
    CHO_O: {"componentName": "Giấy tờ, tài liệu chứng minh việc tiếp tục được sử dụng chỗ ở hợp pháp đó",
            "rowKey": "tiep tuc duoc su dung cho o hop phap"},
    LY_HON: {"componentName": "Giấy tờ, tài liệu chứng minh việc ly hôn", "rowKey": "chung minh viec ly hon"},
}
ROW_ORDER = (TO_KHAI, CHO_O, LY_HON)
# Giấy có loại rõ nhưng bảng không có dòng riêng → thêm dòng "+" mang tên giấy.
NEW_ROW_TYPES = (NHAN_THAN, CCCD)
# Giấy chưa rõ loại → dòng chỗ ở hợp pháp; LLM lỗi → dòng Tờ khai (bắt buộc).
LEFTOVER_ROW = CHO_O
LLM_FAILED_ROW = TO_KHAI

# Thủ tục một bảng giấy tờ hiện sẵn → extension lấy bảng đang hiện, không bấm mở nhóm.
GROUP = {"groupIndex": 0, "groupLabel": "Tách hộ", "bcaPlainTable": True}

DOCUMENT_NAMES = {
    TO_KHAI: "Tờ khai thay đổi thông tin cư trú",
    CHO_O: "Giấy tờ chứng minh chỗ ở hợp pháp",
    LY_HON: "Giấy tờ chứng minh việc ly hôn",
    NHAN_THAN: "Giấy tờ hộ tịch",
    CCCD: "Thẻ căn cước",
}
NOTE_MAX = 500  # ô Ghi chú txtNOTE_OF_DOC<i> maxlength
NEW_ROW_NAME_MAX = 100


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


def _row_id(item: dict) -> str:
    return item["rowKey"] or f"new:{item['componentName']}"


def finalize_rows(items: list[dict], notes: list[str] | None = None) -> None:
    """Gắn `rowFields` (Số lượng = số mục của dòng, Ghi chú gộp) giống nhau cho mọi mục cùng dòng — extension chỉ đọc
    mục đầu của mỗi dòng. Loại giấy tờ để mặc định của cổng (mapping không ghi)."""
    notes = notes or [""] * len(items)
    for row_id in dict.fromkeys(_row_id(item) for item in items):
        members = [(item, note) for item, note in zip(items, notes) if _row_id(item) == row_id]
        joined = "; ".join(dict.fromkeys(note for _, note in members if note))
        fields = {"count": f"{len(members):02d}"}
        if joined:
            fields["note"] = joined[:NOTE_MAX]
        for item, _ in members:
            item["rowFields"] = dict(fields)


def _doc_type(doc: dict) -> str:
    kind = str(doc.get("docType") or "").strip()
    return kind if kind in DOC_TYPES else OTHER


def _shared_note(file_name: str, total: int, names: list[str], pages: list[int], shared: bool) -> str:
    if not (shared and total and pages):
        return ""
    return f"Đính kèm chung tệp {file_name} ({total} trang): {', '.join(dict.fromkeys(names))} tại " \
           f"{page_label(pages, total)}"


def build_plan_items(file_names: list[str], page_counts: dict[int, int], documents: list[dict],
                     llm_ok: bool = True) -> tuple[list[dict], list[str], list[dict]]:
    """Mỗi tệp → một mục cho MỖI dòng mà tệp chứa giấy (dòng sẵn có hoặc dòng "+"); không bỏ tệp nào."""
    items: list[dict] = []
    notes: list[str] = []
    classified: list[dict] = []
    leftovers: list[str] = []
    for index, file_name in enumerate(file_names):
        total = page_counts.get(index, 0)
        docs = [d for d in documents if isinstance(d, dict) and str(d.get("fileIndex")) == str(index)]
        by_row: dict[str, list[dict]] = {}
        extras: list[dict] = []
        for doc in docs:
            kind = _doc_type(doc)
            if kind in ROWS:
                by_row.setdefault(kind, []).append(doc)
            elif kind in NEW_ROW_TYPES:
                extras.append(doc)
        if not by_row and not extras:
            row_type = LEFTOVER_ROW if llm_ok else LLM_FAILED_ROW
            kinds = sorted({_doc_type(d) for d in docs}) or [OTHER]
            name = _clean_name(next((d.get("documentName") for d in docs if d.get("documentName")), "")) \
                or DOCUMENT_NAMES.get(kinds[0], "")
            items.append(plan_item(index, file_name, name or file_name, row_type, kinds[0]))
            notes.append("")
            classified.append({"fileName": file_name, "docTypes": kinds, "routedTo": row_type})
            leftovers.append(file_name)
            continue
        shared = len(docs) > 1
        for row_type in ROW_ORDER:
            row_docs = by_row.get(row_type)
            if not row_docs:
                continue
            names = [_clean_name(d.get("documentName")) or DOCUMENT_NAMES[row_type] for d in row_docs]
            items.append(plan_item(index, file_name, names[0], row_type))
            notes.append(_shared_note(file_name, total, names,
                                      [p for d in row_docs for p in _page_numbers(d, total)], shared))
        if extras:
            # Mọi giấy không có dòng của CÙNG tệp → một dòng "+" (đính nguyên tệp một lần), tên liệt kê các giấy.
            names = list(dict.fromkeys(_clean_name(d.get("documentName")) or DOCUMENT_NAMES[_doc_type(d)]
                                       for d in extras))
            items.append(new_row_item(index, file_name, ", ".join(names), _doc_type(extras[0])))
            notes.append(_shared_note(file_name, total, names,
                                      [p for d in extras for p in _page_numbers(d, total)], shared))
        classified.append({"fileName": file_name, "docTypes": sorted({_doc_type(d) for d in docs}),
                           "rows": [r for r in ROW_ORDER if r in by_row] + (["new_row"] if extras else [])})
    finalize_rows(items, notes)
    warnings = []
    if leftovers:
        row = ROWS[LEFTOVER_ROW if llm_ok else LLM_FAILED_ROW]["componentName"]
        warnings.append(f"Giấy tờ chưa rõ loại đã đính vào dòng \"{row}\": " + ", ".join(leftovers))
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

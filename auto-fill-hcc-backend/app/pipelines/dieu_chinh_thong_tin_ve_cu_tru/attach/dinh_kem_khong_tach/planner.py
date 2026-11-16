"""Đính kèm Điều chỉnh thông tin về cư trú — chế độ KHÔNG tách (đính nguyên tệp).

Mục "Trường hợp và hồ sơ đính kèm" của trường hợp "Thay đổi chủ hộ" có 3 dòng cố định (mapping 16/11/2026):
  1. Tờ khai thay đổi thông tin cư trú                                   — Loại giấy tờ: Giấy tờ điện tử
  2. Ý kiến đồng ý của chủ hộ hoặc người khác trong gia đình về việc thay đổi chủ hộ — Bản gốc
  3. Giấy tờ, tài liệu chứng minh việc điều chỉnh thông tin               — Bản sao
Thẻ căn cước khai thác qua tài khoản định danh, không có dòng riêng.

LLM đọc OCR theo trang và liệt kê giấy tờ trong từng tệp. Tệp gộp nhiều giấy (cả bộ hồ sơ một PDF) được đính
NGUYÊN tệp vào MỌI dòng mà nó chứa giấy, ô Ghi chú ghi "Đính kèm chung tệp …: <giấy> tại trang a/N". Tệp chỉ có
CCCD / giấy chưa rõ loại → dòng 3 + cảnh báo; LLM lỗi → mọi tệp vào dòng Tờ khai + cảnh báo. Không bỏ tệp nào.

Plan item target "bca-row" do extension (attachFilesByBcaPlan) thi hành: `bcaPlainTable` = bảng giấy tờ hiện sẵn
(không có nhóm trường hợp chỗ ở để bấm như Đăng ký thường trú); `rowFields` đặt Loại giấy tờ / Số lượng / Ghi chú
của dòng sau khi chọn tệp.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines.dang_ky_thuong_tru.attach.planner import _clean_name
from app.pipelines.khai_sinh_dvc_moi.attach.dinh_kem_tach.planner import _OCR_TYPES, _pages
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

TO_KHAI = "to_khai"
Y_KIEN = "y_kien"
CHUNG_MINH = "chung_minh"
CCCD = "cccd"
OTHER = "other"
DOC_TYPES = {TO_KHAI, Y_KIEN, CHUNG_MINH, CCCD, OTHER}

# componentName = nhãn dòng trên cổng; rowKey = cụm chữ (bỏ dấu, bỏ dấu câu) có trong dòng; fileKind = option "Loại
# giấy tờ" (cboKIND_OF_FILE<i>) theo mapping.
ROWS: dict[str, dict[str, str]] = {
    TO_KHAI: {"componentName": "Tờ khai thay đổi thông tin cư trú", "rowKey": "to khai thay doi thong tin cu tru",
              "fileKind": "Giấy tờ điện tử"},
    Y_KIEN: {"componentName": "Ý kiến đồng ý của chủ hộ hoặc người khác trong gia đình về việc thay đổi chủ hộ",
             "rowKey": "y kien dong y cua chu ho", "fileKind": "Bản gốc"},
    CHUNG_MINH: {"componentName": "Giấy tờ, tài liệu chứng minh việc điều chỉnh thông tin",
                 "rowKey": "chung minh viec dieu chinh thong tin", "fileKind": "Bản sao"},
}
ROW_ORDER = (TO_KHAI, Y_KIEN, CHUNG_MINH)
# CCCD (cổng không có dòng), giấy chưa rõ loại → dòng giấy tờ chứng minh; LLM lỗi → dòng Tờ khai (bắt buộc).
LEFTOVER_ROW = CHUNG_MINH
LLM_FAILED_ROW = TO_KHAI

# Thủ tục chỉ có một trường hợp, bảng giấy tờ hiện sẵn → extension lấy bảng đang hiện, không bấm mở nhóm.
GROUP = {"groupIndex": 0, "groupLabel": "Thay đổi chủ hộ", "bcaPlainTable": True}

DOCUMENT_NAMES = {
    TO_KHAI: "Tờ khai thay đổi thông tin cư trú",
    Y_KIEN: "Văn bản thống nhất về việc thay đổi chủ hộ",
    CHUNG_MINH: "Giấy tờ chứng minh việc điều chỉnh",
    CCCD: "Thẻ căn cước",
}
NOTE_MAX = 500  # ô Ghi chú txtNOTE_OF_DOC<i> maxlength

# Mốc trang do dịch vụ OCR chèn ("───── Trang 2/5 ─────"). Hồ sơ hay in sẵn chân trang "Trang 2 / 5" — `_pages` dùng
# chung coi cả dòng đó là mốc → đếm gấp đôi số trang (bộ mẫu 5 trang thành 10, chạy thật 16/11/2026). Có mốc OCR thì
# chỉ cắt theo mốc OCR.
_OCR_PAGE_MARK = re.compile(r"(?m)^\s*─+\s*Trang\s+\d+\s*/\s*\d+\s*─+\s*$")


def ocr_pages(text: str) -> list[str]:
    """Text OCR → text từng trang; ưu tiên mốc trang của dịch vụ OCR, không có thì như `_pages`."""
    marks = list(_OCR_PAGE_MARK.finditer(text))
    if not marks:
        return _pages(text)
    return [text[m.end():(marks[k + 1].start() if k + 1 < len(marks) else len(text))].strip()
            for k, m in enumerate(marks)]


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


def finalize_rows(items: list[dict], notes: list[str] | None = None) -> None:
    """Gắn `rowFields` (Loại giấy tờ, Số lượng = số mục của dòng, Ghi chú gộp) giống nhau cho mọi mục cùng dòng —
    extension chỉ đọc mục đầu của mỗi dòng."""
    notes = notes or [""] * len(items)
    for row_type, row in ROWS.items():
        members = [(item, note) for item, note in zip(items, notes) if item["rowKey"] == row["rowKey"]]
        if not members:
            continue
        joined = "; ".join(dict.fromkeys(note for _, note in members if note))
        fields = {"kind": row["fileKind"], "count": f"{len(members):02d}"}
        if joined:
            fields["note"] = joined[:NOTE_MAX]
        for item, _ in members:
            item["rowFields"] = dict(fields)


def page_label(pages: list[int], total: int) -> str:
    """[2] → "trang 2/5"; [2, 3] → "trang 2–3/5"; [2, 4] → "trang 2, 4/5" (số trang đếm từ 1)."""
    pages = sorted(set(pages))
    if len(pages) > 1 and pages == list(range(pages[0], pages[-1] + 1)):
        span = f"{pages[0]}–{pages[-1]}"
    else:
        span = ", ".join(str(p) for p in pages)
    return f"trang {span}/{total}"


def _doc_type(doc: dict) -> str:
    kind = str(doc.get("docType") or "").strip()
    return kind if kind in DOC_TYPES else OTHER


def _page_numbers(doc: dict, total: int) -> list[int]:
    out = []
    for page in doc.get("pages") or []:
        try:
            number = int(page)
        except (TypeError, ValueError):
            continue
        if 1 <= number <= total:
            out.append(number)
    return out


def build_plan_items(file_names: list[str], page_counts: dict[int, int], documents: list[dict],
                     llm_ok: bool = True) -> tuple[list[dict], list[str], list[dict]]:
    """Mỗi tệp → một mục cho MỖI dòng mà tệp chứa giấy; tệp gộp nhiều giấy ghi chú trang. Không bỏ tệp nào."""
    items: list[dict] = []
    notes: list[str] = []
    classified: list[dict] = []
    leftovers: list[str] = []
    for index, file_name in enumerate(file_names):
        total = page_counts.get(index, 0)
        docs = [d for d in documents if isinstance(d, dict) and str(d.get("fileIndex")) == str(index)]
        by_row: dict[str, list[dict]] = {}
        for doc in docs:
            if _doc_type(doc) in ROWS:
                by_row.setdefault(_doc_type(doc), []).append(doc)
        if not by_row:
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
            pages = [p for d in row_docs for p in _page_numbers(d, total)]
            notes.append(
                f"Đính kèm chung tệp {file_name} ({total} trang): {', '.join(dict.fromkeys(names))} tại "
                f"{page_label(pages, total)}" if shared and total and pages else ""
            )
        classified.append({"fileName": file_name, "docTypes": sorted({_doc_type(d) for d in docs}),
                           "rows": [r for r in ROW_ORDER if r in by_row]})
    finalize_rows(items, notes)
    warnings = []
    if leftovers:
        row = ROWS[LEFTOVER_ROW if llm_ok else LLM_FAILED_ROW]["componentName"]
        warnings.append(f"Giấy tờ không có dòng riêng hoặc chưa rõ loại đã đính vào dòng \"{row}\": "
                        + ", ".join(leftovers))
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

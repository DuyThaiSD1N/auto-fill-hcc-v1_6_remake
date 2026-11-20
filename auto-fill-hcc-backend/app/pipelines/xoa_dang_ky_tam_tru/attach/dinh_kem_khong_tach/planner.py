"""Đính kèm Xóa đăng ký tạm trú — chế độ KHÔNG tách (đính nguyên tệp).

Mục "HỒ SƠ ĐÍNH KÈM" của trang (bảng #tblGiayToDinhKem hiện sẵn, nạp theo Trường hợp; nút "+ Thêm mới" dưới bảng).
Ảnh chạy thật 20/11/2026 với "Nhân khẩu do không còn chỗ ở hợp pháp" (TAT-XOA-13), 2 dòng:
  1. Tờ khai thay đổi thông tin cư trú
  2. Giấy tờ chứng minh về việc không còn chỗ ở hợp pháp
Mapping ghi dòng 2 thuộc trường hợp không còn chỗ ở hợp pháp; các trường hợp vắng mặt / đã đăng ký thường trú chưa
chụp DOM. Planner không biết Trường hợp đang chọn trên trang → chỉ dòng Tờ khai được coi là luôn có: giấy chưa rõ loại
và lượt LLM lỗi đều đính vào dòng Tờ khai; dòng 2 chỉ nhận giấy chứng minh không còn chỗ ở hợp pháp (đi kèm đúng
trường hợp đó). Giấy có loại rõ mà bảng không có dòng (chứng minh vắng mặt, giấy tờ thường trú, hộ tịch, CCCD) → dòng
"+ Thêm mới" mang tên giấy. Không bỏ tệp nào.

Tệp gộp nhiều giấy được đính NGUYÊN tệp vào MỌI dòng mà nó chứa giấy, Ghi chú "Đính kèm chung tệp …: <giấy> tại trang
a/N" (trang tạm trú dùng ô Ghi chú txtFILE_NOTE<i>, extension hiện chỉ ghi ô txtNOTE_OF_DOC<i> của trang thường trú).
Hình thức giấy tờ để mặc định cổng ("Bản gốc"), Số lượng cổng tự đếm.

Plan item target "bca-row" do extension (attachFilesByBcaPlan) thi hành như Tách hộ (`bcaPlainTable`: lấy bảng
đang hiện, không bấm nhóm).
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
CHO_O = "cho_o"
VANG_MAT = "vang_mat"
THUONG_TRU = "thuong_tru"
NHAN_THAN = "nhan_than"
CCCD = "cccd"
OTHER = "other"
DOC_TYPES = {TO_KHAI, CHO_O, VANG_MAT, THUONG_TRU, NHAN_THAN, CCCD, OTHER}

# componentName = nhãn dòng trên cổng; rowKey = cụm chữ (bỏ dấu, bỏ dấu câu) có trong dòng.
ROWS: dict[str, dict[str, str]] = {
    TO_KHAI: {"componentName": "Tờ khai thay đổi thông tin cư trú", "rowKey": "to khai thay doi thong tin cu tru"},
    CHO_O: {"componentName": "Giấy tờ chứng minh về việc không còn chỗ ở hợp pháp",
            "rowKey": "khong con cho o hop phap"},
}
ROW_ORDER = (TO_KHAI, CHO_O)
# Giấy có loại rõ nhưng bảng không có dòng riêng → thêm dòng "+ Thêm mới" mang tên giấy.
NEW_ROW_TYPES = (VANG_MAT, THUONG_TRU, NHAN_THAN, CCCD)
# Giấy chưa rõ loại / LLM lỗi → dòng Tờ khai: dòng duy nhất có ở MỌI trường hợp.
LEFTOVER_ROW = TO_KHAI

# Thủ tục một bảng giấy tờ hiện sẵn → extension lấy bảng đang hiện, không bấm mở nhóm.
GROUP = {"groupIndex": 0, "groupLabel": "Xóa đăng ký tạm trú", "bcaPlainTable": True}

DOCUMENT_NAMES = {
    TO_KHAI: "Tờ khai thay đổi thông tin cư trú",
    CHO_O: "Giấy tờ chứng minh không còn chỗ ở hợp pháp",
    VANG_MAT: "Giấy tờ chứng minh vắng mặt",
    THUONG_TRU: "Giấy tờ về đăng ký thường trú",
    NHAN_THAN: "Giấy tờ hộ tịch",
    CCCD: "Thẻ căn cước",
}
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
    """Dòng thêm bằng nút "+ Thêm mới" dưới bảng, tên dòng = tên giấy (extension gom các mục cùng tên vào một dòng)."""
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


def _doc_type(doc: dict) -> str:
    kind = str(doc.get("docType") or "").strip()
    return kind if kind in DOC_TYPES else OTHER


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
            kinds = sorted({_doc_type(d) for d in docs}) or [OTHER]
            name = _clean_name(next((d.get("documentName") for d in docs if d.get("documentName")), "")) \
                or DOCUMENT_NAMES.get(kinds[0], "")
            items.append(plan_item(index, file_name, name or file_name, LEFTOVER_ROW, kinds[0]))
            notes.append("")
            classified.append({"fileName": file_name, "docTypes": kinds, "routedTo": LEFTOVER_ROW})
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
    if leftovers and llm_ok:
        warnings.append(f"Giấy tờ chưa rõ loại đã đính vào dòng \"{ROWS[LEFTOVER_ROW]['componentName']}\": "
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
    if not llm_ok and attachments:
        warnings.append(f"Chưa phân loại được giấy tờ, đã đính tất cả vào dòng "
                        f"\"{ROWS[LEFTOVER_ROW]['componentName']}\" — kiểm tra lại trước khi nộp.")
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {"documents": names, "classified": classified},
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

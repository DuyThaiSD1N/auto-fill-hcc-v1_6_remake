"""Đính kèm Xóa đăng ký tạm trú — chế độ KHÔNG tách (đính nguyên tệp).

Mục "HỒ SƠ ĐÍNH KÈM" của trang (bảng #tblGiayToDinhKem hiện sẵn, nạp theo Trường hợp; nút "+ Thêm mới" dưới bảng).
Ảnh của user theo Trường hợp (20/11 + 24/11/2026):
  - Nhân khẩu / Cả hộ do không còn chỗ ở hợp pháp (TAT-XOA-13/14): 1. Tờ khai thay đổi thông tin cư trú, 2. Giấy tờ
    chứng minh về việc không còn chỗ ở hợp pháp
  - Nhân khẩu / Hộ do vắng mặt từ 6 tháng trở lên, Nhân khẩu / Hộ do đã đăng ký thường trú tại chính nơi tạm trú
    (TAT-XOA-15..18): CHỈ dòng 1 Tờ khai
Trường hợp đang chọn trên trang = trường hợp mapper chọn theo lý do ở mục 10 CT01 → planner đọc lại mục 10 trong OCR
(`table_has_no_home_row`; trợ lý gửi options.bcaCase thì theo đó). Bảng không có dòng 2 → giấy chứng minh không còn
chỗ ở hợp pháp đi dòng "+ Thêm mới" mang tên giấy; chưa rõ trường hợp → vẫn vào dòng 2 (giấy đó đi kèm đúng trường
hợp có dòng 2). Giấy chưa rõ loại và lượt LLM lỗi đều đính vào dòng Tờ khai (dòng có ở MỌI trường hợp). Giấy có loại
rõ mà bảng không có dòng (chứng minh vắng mặt, giấy tờ thường trú, hộ tịch, CCCD) → dòng "+ Thêm mới" mang tên giấy.
Không bỏ tệp nào.

Ghi chú dòng Tờ khai theo ảnh ánh xạ 24/11: "Tờ khai CT01 bản gốc (N trang) của <người đề nghị>, kèm ý kiến chủ hộ
<…>, chủ sở hữu chỗ ở hợp pháp <…>, cha/mẹ/người giám hộ <…>" (`to_khai_note`, tên LLM đọc trên tờ khai). Tệp gộp
nhiều giấy được đính NGUYÊN tệp vào MỌI dòng mà nó chứa giấy, Ghi chú thêm "Đính kèm chung tệp …: <giấy> tại trang
a/N". Ô Ghi chú trang tạm trú là txtFILE_NOTE<i> (extension tìm cả txtNOTE_OF_DOC<i> của trang thường trú).
Hình thức giấy tờ để mặc định cổng ("Bản gốc"), Số lượng cổng tự đếm (ô khoá).

Plan item target "bca-row" do extension (attachFilesByBcaPlan) thi hành như Tách hộ (`bcaPlainTable`: lấy bảng
đang hiện, không bấm nhóm).
"""

import re
import time

from app.config import settings
from app.pipelines._shared.naming import fold
from app.pipelines.dang_ky_thuong_tru.attach.planner import _clean_name
from app.pipelines.dieu_chinh_thong_tin_ve_cu_tru.attach.dinh_kem_khong_tach.planner import _page_numbers, ocr_pages
from app.pipelines.khai_sinh_dvc_moi.attach.dinh_kem_tach.planner import _OCR_TYPES
from app.pipelines.tach_ho.attach.dinh_kem_khong_tach.planner import _shared_note, finalize_rows
from app.pipelines.xoa_dang_ky_tam_tru.process.mapper import _REASONS
from app.pipelines.xoa_dang_ky_tam_tru.process.schema import CASE_NO_HOME, CASE_NO_HOME_HH, CASES
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


# Mục 10 CT01: "10. Nội dung đề nghị(2): …" đến mục 11 "Những thành viên…". Chú thích cuối tờ khai "(2) Ghi rõ ràng, cụ
# thể nội dung đề nghị. Ví dụ: đăng ký thường trú…" cũng có cụm này → chỉ lấy lần xuất hiện ĐẦU, cắt ở mục 11.
_REQUEST_LABEL = "noi dung de nghi"
_REQUEST_END = re.compile(r"nhung thanh vien|\b11\s*[.)]|\(\d\)\s*ghi ro")
_REQUEST_MAX = 400


def table_has_no_home_row(pages_by_file: dict[int, list[str]], options: dict | None = None) -> bool | None:
    """Bảng giấy tờ có dòng "chứng minh về việc không còn chỗ ở hợp pháp" không — chỉ hai trường hợp không còn chỗ ở hợp
    pháp có dòng đó (ảnh user 24/11/2026). Trợ lý gửi Trường hợp công dân chọn (options.bcaCase) → theo đó; không thì
    đọc lý do ở mục 10 tờ khai như mapper chọn ô Trường hợp (`_REASONS`). Không rõ → None."""
    chosen = (options or {}).get("bcaCase")
    if chosen in CASES:
        return chosen in (CASE_NO_HOME, CASE_NO_HOME_HH)
    for pages in pages_by_file.values():
        text = fold(" ".join(pages))
        start = text.find(_REQUEST_LABEL)
        if start < 0:
            continue
        request = _REQUEST_END.split(text[start + len(_REQUEST_LABEL):start + _REQUEST_MAX], maxsplit=1)[0]
        for keys, person_case, _ in _REASONS:
            if any(key in request for key in keys):
                return person_case == CASE_NO_HOME
    return None


_OPINIONS = (("yKienChuHo", "chủ hộ"), ("yKienChuSoHuu", "chủ sở hữu chỗ ở hợp pháp"),
             ("yKienChaMe", "cha/mẹ/người giám hộ"))
_PERSON_MAX = 60


def _person(value) -> str:
    """Họ tên viết hoa chữ đầu như ảnh ánh xạ; chấm chấm / không có chữ → ""."""
    words = re.sub(r"[^\w\s]+", " ", str(value or "")).split()
    if not any(ch.isalpha() for word in words for ch in word):
        return ""
    return " ".join(word[:1].upper() + word[1:].lower() for word in words)[:_PERSON_MAX]


def to_khai_note(doc: dict, pages: int) -> str:
    """Ghi chú dòng Tờ khai (ảnh ánh xạ 24/11/2026): "Tờ khai CT01 bản gốc (1 trang) của A, kèm ý kiến chủ hộ B, chủ sở
    hữu chỗ ở hợp pháp C, cha/mẹ/người giám hộ D". LLM không đọc được tên người đề nghị → không ghi."""
    name = _person(doc.get("nguoiDeNghi"))
    if not name:
        return ""
    note = "Tờ khai CT01 bản gốc" + (f" ({pages} trang)" if pages else "") + f" của {name}"
    opinions = [f"{label} {_person(doc.get(key))}" for key, label in _OPINIONS if _person(doc.get(key))]
    return note + (", kèm ý kiến " + ", ".join(opinions) if opinions else "")


def build_plan_items(file_names: list[str], page_counts: dict[int, int], documents: list[dict],
                     llm_ok: bool = True, no_home_row: bool | None = None) -> tuple[list[dict], list[str], list[dict]]:
    """Mỗi tệp → một mục cho MỖI dòng mà tệp chứa giấy (dòng sẵn có hoặc dòng "+"); không bỏ tệp nào.
    `no_home_row` False (trường hợp vắng mặt / đã đăng ký thường trú: bảng chỉ có dòng Tờ khai) → giấy chứng minh không
    còn chỗ ở hợp pháp đi dòng "+"."""
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
            if kind == CHO_O and no_home_row is False:
                extras.append(doc)
            elif kind in ROWS:
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
            note = _shared_note(file_name, total, names,
                                [p for d in row_docs for p in _page_numbers(d, total)], shared)
            if row_type == TO_KHAI:
                note = "; ".join(filter(None, [to_khai_note(row_docs[0], len(_page_numbers(row_docs[0], total))),
                                               note]))
            notes.append(note)
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

    _ = session
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
    attachments, warnings, classified = build_plan_items(names, page_counts, documents, llm_ok,
                                                         table_has_no_home_row(pages_by_file, options))
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

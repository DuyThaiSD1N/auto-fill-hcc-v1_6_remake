"""Đính kèm bước "Thành phần hồ sơ" cho thủ tục "Điều chỉnh giấy phép hành nghề trong giai đoạn chuyển
tiếp..." (cổng Bộ Y tế — Angular mat-table, engine FE `attp-row`).

Bảng có 10 dòng, cổng gộp cấu hình nhiều trường hợp nên TÊN DÒNG TRÙNG NHAU:
  1  "Đơn theo Mẫu 08 Phụ lục I …;"                    ← Đơn đề nghị (bản chính) + tệp không nhận ra + CCCD
  2  "a) Đơn theo Mẫu 08 Phụ lục I …."                  ← (trùng dòng 1, để trống)
  3  "b) Bản sao hợp lệ giấy phép hành nghề đã cấp …"    ← CCHN/GPHN đã cấp (bản sao)
  4  ") Bản sao hợp lệ của một trong các giấy tờ sau …"  ← Chứng chỉ đào tạo (bản sao)
  5  "Bản chính hoặc bản sao hợp lệ giấy xác nhận … Mẫu 07 …"   ← Giấy xác nhận thực hành
  6  "Bản sao hợp lệ giấy phép hành nghề đã cấp (không áp dụng …" ← (trùng dòng 3, để trống)
  7  "d) Bản chính hoặc bản sao hợp lệ giấy xác nhận … Mẫu 07 …" ← (trùng dòng 5, để trống)
  8  "Bản sao hợp lệ giấy phép hành nghề đã cấp …" (chỉ Bản sao) ← (trùng dòng 3, để trống)
  9  "c) Bản sao hợp lệ giấy chứng nhận người có bài thuốc gia truyền …" ← GCN gia truyền
  10 "c) Bản sao hợp lệ văn bằng đào tạo …"             ← Văn bằng đào tạo (bản sao)
MỖI TỆP ĐÍNH ĐÚNG MỘT DÒNG: nộp 5 tệp thì cổng nhận 5 tệp. Trước đây một giấy tờ đính vào mọi dòng trùng
nội dung → 5 tệp thành 9 (Đơn ×2, CCHN ×3, văn bằng ×2), cán bộ phải xoá bớt.

Engine attp-row GOM item theo componentName rồi tìm dòng bằng (componentName, componentIndex). Dòng 3/6/8
trùng chữ → mỗi dòng một componentName KHÁC NHAU (đoạn con vẫn khớp đúng dòng đó) + componentIndex; nếu
cổng đổi thứ tự dòng, engine rơi về dòng đầu tiên khớp tên và bỏ qua tệp đã có ở dòng đó (không đính trùng).
Dòng trùng vẫn giữ trong _ROWS (docTypes rỗng) để trace thấy đủ bảng.

Phân loại THUẦN LLM, mỗi tệp một lượt gọi (xem prompt). ⚑ KHÔNG BỎ SÓT TỆP: tệp không xếp được (other),
lượt gọi lỗi, hoặc CCCD (không có dòng riêng) → đính vào dòng 1 (Đơn), giữ tên tệp gốc.

Cài đặt "Có tách hồ sơ khi đính kèm" (``options.splitDocuments``): tệp PDF nhiều trang được LLM xếp loại TỪNG
TRANG và đánh dấu trang mở đầu giấy mới (kèm tiêu đề in trên giấy); mỗi giấy thành một mục riêng chỉ gồm đúng các
trang của nó (``sourceSegments``, extension cắt PDF) vào dòng của loại đó. Chia theo giấy, không theo loại: hai giấy
cùng loại là hai tệp trong cùng dòng, tên tệp = tiêu đề giấy. Không bỏ trang nào. Tệp một trang, tệp không có chữ, số
trang OCR lệch PDF, hoặc LLM trả lệch số trang → phân loại cả tệp như chế độ thường. TẮT / extension cũ không gửi cờ
→ hành vi cũ.
"""

import asyncio
import re
import time
from pathlib import PurePath
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.dieu_chinh_giay_phep_hanh_nghe_chuyen_tiep.attach import prompt
from app.pipelines.di_chuyen_ho_so_nguoi_huong_tro_cap.attach.planner import split_requested, splittable_pages
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_BAN_CHINH = "Bản chính"
_BAN_SAO = "Bản sao"
# Trang LLM trả other mà ít chữ (mặt sau in xuyên, trang chỉ có dấu/chức danh) là trang nối tiếp của giấy liền trước.
_SHORT_OTHER_CHARS = 200
# Cổng BYT cắt / từ chối tên tệp từ 50 ký tự (tính cả đuôi ".pdf").
_TITLE_MAX = 45

_DON = "don_de_nghi"
_GPHN = "gphn"
_VANBANG = "van_bang"
_CHUNGCHI = "chung_chi_dao_tao"
_THUCHANH = "thuc_hanh"
_GIATRUYEN = "gia_truyen"
_CCCD = "cccd"
_OTHER = "other"

_DOC_NAMES = {
    _DON: "Đơn đề nghị điều chỉnh giấy phép hành nghề (Mẫu 08 PL I NĐ 96/2023)",
    _GPHN: "Bản sao chứng chỉ hành nghề - giấy phép hành nghề đã cấp",
    _VANBANG: "Bản sao văn bằng đào tạo",
    _CHUNGCHI: "Bản sao chứng chỉ đào tạo",
    _THUCHANH: "Giấy xác nhận hoàn thành quá trình thực hành (Mẫu 07 PL I)",
    _GIATRUYEN: "Bản sao giấy chứng nhận bài thuốc - phương pháp chữa bệnh gia truyền",
}

# Theo THỨ TỰ dòng trên cổng. componentName = đoạn con của tên dòng, KHÁC NHAU giữa mọi dòng (engine gom
# theo nó). Mỗi docType nằm ở ĐÚNG MỘT dòng → mỗi tệp chỉ đính một lần; dòng trùng tên để docTypes rỗng.
_ROWS: list[dict[str, Any]] = [
    {"componentIndex": 1, "componentName": "Đơn theo Mẫu 08 Phụ lục I",
     "loaiBan": _BAN_CHINH, "docTypes": [_DON, _OTHER, _CCCD]},
    {"componentIndex": 2, "componentName": "a) Đơn theo Mẫu 08 Phụ lục I",
     "loaiBan": _BAN_CHINH, "docTypes": []},
    {"componentIndex": 3, "componentName": "b) Bản sao hợp lệ giấy phép hành nghề đã cấp",
     "loaiBan": _BAN_SAO, "docTypes": [_GPHN]},
    {"componentIndex": 4, "componentName": "Bản sao hợp lệ của một trong các giấy tờ sau",
     "loaiBan": _BAN_SAO, "docTypes": [_CHUNGCHI]},
    {"componentIndex": 5, "componentName": "Bản chính hoặc bản sao hợp lệ giấy xác nhận hoàn thành quá trình thực hành",
     "loaiBan": _BAN_CHINH, "docTypes": [_THUCHANH]},
    {"componentIndex": 6, "componentName": "Bản sao hợp lệ giấy phép hành nghề đã cấp (không áp dụng",
     "loaiBan": _BAN_SAO, "docTypes": []},
    {"componentIndex": 7, "componentName": "d) Bản chính hoặc bản sao hợp lệ giấy xác nhận hoàn thành",
     "loaiBan": _BAN_CHINH, "docTypes": []},
    {"componentIndex": 8, "componentName": "Bản sao hợp lệ giấy phép hành nghề đã cấp",
     "loaiBan": _BAN_SAO, "docTypes": []},
    {"componentIndex": 9, "componentName": "Bản sao hợp lệ giấy chứng nhận người có bài thuốc gia truyền",
     "loaiBan": _BAN_SAO, "docTypes": [_GIATRUYEN]},
    {"componentIndex": 10, "componentName": "c) Bản sao hợp lệ văn bằng đào tạo",
     "loaiBan": _BAN_SAO, "docTypes": [_VANBANG]},
]
_SKIP_DOCS = {_CCCD}
_ALLOWED_DOC_TYPES = set(_DOC_NAMES) | _SKIP_DOCS | {_OTHER}


def _canon(value: Any) -> str:
    return re.sub(r"[\s_\-]+", "_", _fold(str(value or ""))).strip("_")


def _normalize_doc_type(value: Any) -> str:
    """Khớp ĐÚNG nhãn trong allowed_types. Nhãn lạ → other (không đoán theo chuỗi con)."""
    canon = _canon(value)
    return next((doc_type for doc_type in _ALLOWED_DOC_TYPES if _canon(doc_type) == canon), _OTHER)


async def _classify_one(index: int, file_name: str, text: str) -> tuple[int, str]:
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(file_name, text)},
    ]
    raw = await client.chat(messages, max_tokens=120, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    first = next(iter(parsed.get("documents", []) or []), None) or parsed
    return index, _normalize_doc_type(first.get("docType") or first.get("type"))


async def _classify_with_llm(
    documents: list[dict[str, Any]],
    errors: list[str] | None = None,
) -> dict[int, str]:
    """Một lượt gọi cho MỖI tệp — lỗi của tệp này không kéo theo tệp khác."""
    if not documents:
        return {}
    outcomes = await asyncio.gather(
        *(_classify_one(d["index"], d["name"], d["text"]) for d in documents),
        return_exceptions=True,
    )
    result: dict[int, str] = {}
    for document, outcome in zip(documents, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            if errors is not None:
                errors.append(f"attachment_agent file {document['name']}: {outcome}")
            continue
        index, doc_type = outcome
        result[index] = doc_type
    return result


async def _classify_pages(pages_by_file: dict[int, list[str]]) -> dict[int, list[dict]]:
    """LLM xếp loại TỪNG TRANG + đánh dấu trang mở đầu giấy mới → {tệp: [giấy gồm các trang liền nhau]}."""
    total = sum(len(p) for p in pages_by_file.values())
    messages = [
        {"role": "system", "content": prompt.SPLIT_SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_split_user_prompt(pages_by_file)},
    ]
    # temperature 0: cùng tệp phải ra cùng cách chia giữa các lần chạy.
    raw = await client.chat(messages, temperature=0, max_tokens=max(400, min(3000, 150 + 40 * total)),
                            enable_thinking=settings.agent_reasoning)
    out: dict[int, list[dict]] = {}
    for item in client.extract_json_block(raw).get("tep", []) or []:
        try:
            idx = int(item.get("fileIndex"))
        except Exception:  # noqa: BLE001
            continue
        if idx in pages_by_file and idx not in out:
            docs = _parse_docs(item.get("trang"), len(pages_by_file[idx]))
            # Lệch số trang → không biết trang nào thuộc giấy nào, tệp đó phân loại cả tệp như chế độ thường.
            if docs:
                out[idx] = docs
    return out


def _parse_docs(raw_pages: Any, page_count: int) -> list[dict] | None:
    """Kết quả từng trang (loại + cờ giấy mới) → các giấy liền nhau, trang 0-based. Thiếu/thừa/lệch số trang → None.

    Giấy mới bắt đầu khi LLM đánh giayMoi hoặc khi loại đổi so với trang trước."""
    if not isinstance(raw_pages, list) or len(raw_pages) != page_count:
        return None
    docs: list[dict] = []
    for page, raw in enumerate(raw_pages):
        if not isinstance(raw, dict):
            return None
        try:
            if int(raw.get("trang", page + 1)) != page + 1:
                return None
        except Exception:  # noqa: BLE001
            return None
        doc_type = _normalize_doc_type(raw.get("docType"))
        if not docs or raw.get("giayMoi") is True or docs[-1]["docType"] != doc_type:
            docs.append({"docType": doc_type, "pages": [page], "title": raw.get("tenGiay")})
        else:
            docs[-1]["pages"].append(page)
    return docs


def _merge_short_other(docs: list[dict], pages: list[str]) -> list[dict]:
    """Giấy other mà mọi trang đều ít chữ (mặt sau in xuyên, trang chỉ có dấu/chức danh) là phần nối của giấy
    liền trước, không thành tệp riêng."""
    out: list[dict] = []
    for doc in docs:
        short = all(len(re.findall(r"\w", pages[p] or "")) < _SHORT_OTHER_CHARS for p in doc["pages"])
        if doc["docType"] == _OTHER and short and out:
            out[-1] = {**out[-1], "pages": out[-1]["pages"] + doc["pages"]}
        else:
            out.append(doc)
    return out


def _clip_title(value: Any) -> str:
    text = " ".join(re.sub(r"[()\[\]{}.]", " ", str(value or "")).split()).strip(" -,;:")
    if len(text) > _TITLE_MAX:
        text = text[:_TITLE_MAX].rsplit(" ", 1)[0]
    return text


def _doc_title(value: Any, fallback: str) -> str:
    """Tiêu đề LLM đọc trên giấy làm tên tệp: bỏ ngoặc/dấu chấm, ≤ _TITLE_MAX ký tự; trống → tên mặc định của dòng
    (cũng cắt cho vừa)."""
    return _clip_title(value) or _clip_title(fallback)


def _document_name(file_name: str, doc_type: str, same_type_count: int) -> str:
    # Tệp lạ / CCCD (không có tên chuẩn) giữ TÊN GỐC để cán bộ nhận ra; nhiều tệp cùng loại (vd 2 chứng chỉ đào
    # tạo) thêm tên gốc để hai tệp trong cùng dòng không mang cùng một tên.
    if doc_type not in _DOC_NAMES:
        return file_name
    base = _DOC_NAMES[doc_type]
    return f"{base} ({PurePath(file_name).stem})" if same_type_count > 1 else base


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, str] | None = None,
    page_types: dict[int, list[dict]] | None = None,
    pages_by_file: dict[int, list[str]] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    page_types = page_types or {}
    pages_by_file = pages_by_file or {}
    warnings: list[str] = []
    classified: list[dict] = []
    # docType → các mục (tệp, trang, tiêu đề giấy); trang None = nguyên tệp.
    by_type: dict[str, list[tuple[int, list[int] | None, Any]]] = {}
    names: dict[int, str] = {}

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        names[idx] = file_name
        if idx in page_types and idx in pages_by_file:
            # Mỗi GIẤY một mục (hai giấy cùng loại là hai tệp trong cùng dòng), không gom theo loại.
            docs = _merge_short_other(page_types[idx], pages_by_file[idx])
            for doc in docs:
                by_type.setdefault(doc["docType"], []).append(
                    (idx, doc["pages"] if len(docs) > 1 else None, doc.get("title"))
                )
            classified.append({"fileName": file_name, "docType": ",".join(d["docType"] for d in docs),
                               "source": "llm-pages",
                               "tachGiayTo": [{"docType": d["docType"], "pages": [p + 1 for p in d["pages"]],
                                               "tenGiay": d.get("title")} for d in docs]})
            continue
        doc_type = llm_types.get(idx, _OTHER)
        entry = {"fileName": file_name, "docType": doc_type, "source": "llm" if idx in llm_types else "fallback"}
        by_type.setdefault(doc_type, []).append((idx, None, None))
        entry["rows"] = [r["componentIndex"] for r in _ROWS if doc_type in r["docTypes"]]
        if doc_type in (_OTHER, _CCCD):
            entry["fallbackRow"] = _DON
            entry["routedTo"] = _DON
        classified.append(entry)

    items: list[dict] = []
    for row in _ROWS:
        for doc_type in row["docTypes"]:
            units = by_type.get(doc_type, [])
            seen_names: dict[str, int] = {}
            for idx, page_list, title in units:
                item = {
                    "fileIndex": idx,
                    "fileName": names[idx],
                    "documentName": _document_name(names[idx], doc_type, len(units)),
                    "componentName": row["componentName"],
                    "componentIndex": row["componentIndex"],
                    "loaiBan": row["loaiBan"],
                    "target": "attp-row",
                    "needsAddComponent": False,
                    "detectedType": doc_type,
                }
                if page_list is not None:
                    item["sourceSegments"] = [{"fileIndex": idx, "pageIndexes": page_list}]
                    fallback_name = "Bản sao Căn cước công dân" if doc_type == _CCCD else _DOC_NAMES.get(doc_type)
                    name = _doc_title(title, fallback_name or names[idx])
                    # Hai giấy cùng tiêu đề trong một dòng → đánh số để cán bộ và bộ chống trùng phân biệt.
                    seen_names[name.casefold()] = seen_names.get(name.casefold(), 0) + 1
                    count = seen_names[name.casefold()]
                    item["documentName"] = name if count == 1 else f"{name} {count}"
                items.append(item)

    fallback = [names[idx] for idx in sorted({u[0] for u in by_type.get(_OTHER, []) + by_type.get(_CCCD, [])})]
    if fallback:
        warnings.append(
            "Giấy tờ không có dòng riêng hoặc chưa rõ loại đã đính chung dòng Đơn Mẫu 08 để không bỏ sót — cán bộ "
            f"kiểm tra lại: {', '.join(fallback)}."
        )
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
    texts = {
        idx: str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        for idx, file in enumerate(raw_files)
        if file.get("type") in _OCR_TYPES
    }

    t1 = time.monotonic()
    pages_by_file: dict[int, list[str]] = {}
    page_types: dict[int, list[dict]] = {}
    if split:
        # Chỉ tệp NHIỀU trang mới có thể gộp nhiều giấy; tệp một trang giữ phân loại cả tệp.
        pages_by_file = {
            idx: pages for idx, text in texts.items()
            if len(pages := splittable_pages(raw_files[idx], text)) > 1
        }
        if pages_by_file:
            try:
                page_types = await _classify_pages(pages_by_file)
            except Exception as exc:  # noqa: BLE001 — chia trang hỏng thì phân loại cả tệp
                errors.append(f"Tách giấy tờ: {exc} — đính nguyên tệp.")
    llm_docs = [
        {"index": idx, "name": str(raw_files[idx].get("name") or ""), "text": text}
        for idx, text in texts.items()
        if idx not in page_types
    ]
    llm_types: dict[int, str] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs, errors)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, llm_types, page_types, pages_by_file)
    errors.extend(warnings)
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [doc["name"] for doc in llm_docs],
            "classified": classified,
            "skippedOcr": skipped_ocr,
            "rows": [dict(row) for row in _ROWS],
            "splitDocuments": split,
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

"""Đính kèm bước "Thành phần hồ sơ" cho thủ tục "Điều chỉnh giấy phép hành nghề trong giai đoạn chuyển
tiếp..." (cổng Bộ Y tế — Angular mat-table, engine FE `attp-row`).

Bảng có 10 dòng, cổng gộp cấu hình nhiều trường hợp nên TÊN DÒNG TRÙNG NHAU:
  1  "Đơn theo Mẫu 08 Phụ lục I …;"                    ← Đơn đề nghị (bản chính) + tệp không nhận ra
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

Phân loại THUẦN LLM, mỗi tệp một lượt gọi (xem prompt). ⚑ KHÔNG BỎ SÓT TỆP: tệp không xếp được (other)
hoặc lượt gọi lỗi → đính vào dòng 1 (Đơn), giữ tên tệp gốc. CCCD không có dòng riêng → bỏ qua.
"""

import asyncio
import re
import time
from pathlib import PurePath
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.dieu_chinh_giay_phep_hanh_nghe_chuyen_tiep.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_BAN_CHINH = "Bản chính"
_BAN_SAO = "Bản sao"

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
     "loaiBan": _BAN_CHINH, "docTypes": [_DON, _OTHER]},
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


def _document_name(file_name: str, doc_type: str, same_type_count: int) -> str:
    # Tệp lạ giữ TÊN GỐC để cán bộ nhận ra; nhiều tệp cùng loại (vd 2 chứng chỉ đào tạo) thêm tên gốc để
    # hai tệp trong cùng dòng không mang cùng một tên.
    if doc_type == _OTHER:
        return file_name
    base = _DOC_NAMES[doc_type]
    return f"{base} ({PurePath(file_name).stem})" if same_type_count > 1 else base


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    warnings: list[str] = []
    classified: list[dict] = []
    by_type: dict[str, list[int]] = {}
    names: dict[int, str] = {}

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        names[idx] = file_name
        doc_type = llm_types.get(idx, _OTHER)
        entry = {"fileName": file_name, "docType": doc_type, "source": "llm" if idx in llm_types else "fallback"}
        if doc_type in _SKIP_DOCS:
            entry["skipped"] = True
        else:
            by_type.setdefault(doc_type, []).append(idx)
            entry["rows"] = [r["componentIndex"] for r in _ROWS if doc_type in r["docTypes"]]
        if doc_type == _OTHER:
            entry["fallbackRow"] = _DON
        classified.append(entry)

    items: list[dict] = []
    for row in _ROWS:
        for doc_type in row["docTypes"]:
            indices = by_type.get(doc_type, [])
            for idx in indices:
                items.append({
                    "fileIndex": idx,
                    "fileName": names[idx],
                    "documentName": _document_name(names[idx], doc_type, len(indices)),
                    "componentName": row["componentName"],
                    "componentIndex": row["componentIndex"],
                    "loaiBan": row["loaiBan"],
                    "target": "attp-row",
                    "needsAddComponent": False,
                    "detectedType": doc_type,
                })

    fallback = [names[idx] for idx in by_type.get(_OTHER, [])]
    if fallback:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã đính kèm chung vào dòng Đơn Mẫu 08 để không bỏ sót — cán bộ "
            f"kiểm tra lại: {', '.join(fallback)}."
        )
    return items, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options or {}
    _ = session
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
    llm_docs = [
        {"index": idx, "name": str(file.get("name") or ""),
         "text": str(ocr_by_name.get(file.get("name"), {}).get("text") or "")}
        for idx, file in enumerate(raw_files)
        if file.get("type") in _OCR_TYPES
    ]

    t1 = time.monotonic()
    llm_types: dict[int, str] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs, errors)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, llm_types)
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
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

"""Đính kèm KHÔNG TÁCH cho "Đăng ký biến động ... do chia, tách, hợp nhất, sáp nhập tổ chức..." (1.013977, cổng DVC
Đà Nẵng, engine FE `attp-row`) — cài đặt "Tách giấy tờ" tắt.

OCR từng tệp như chế độ tách (`ocr.ocr_per_file`) → MỘT lượt LLM phân loại cả hồ sơ, mỗi tệp liệt kê mọi loại giấy có
trong tệp (docTypes) → MỖI TỆP ĐÍNH NGUYÊN, MỘT LẦN (không `sourceSegments`) vào dòng của giấy chính trong tệp. Bảng 9
dòng + ánh xạ loại giấy → dòng dùng chung với chế độ tách (`_ROWS`, `_row_of` của dinh_kem_tach) nên hai chế độ đặt
cùng dòng:
  Đơn Mẫu 18 → 1 · GCN đã cấp → 2 · văn bản đại diện → 3 · QĐ quy hoạch chi tiết → 4 · mảnh trích đo → 5 · bản vẽ
  tách/hợp thửa → 6 · GCN đăng ký doanh nghiệp → 7 · QĐ chia, tách, sáp nhập → 8 · QĐ điều chỉnh quy hoạch → 9;
  đính kèm chung: tờ khai thuế → 1, giấy tờ tài sản → 2, công văn thế chấp → 3, bảng thay đổi ĐKDN → 7, chứng từ
  nghĩa vụ tài chính → 9 nếu hồ sơ có QĐ điều chỉnh quy hoạch, không thì 1.
Giấy chính chọn theo _PRIORITY: Đơn trước, giấy có dòng riêng (loại đầu của từng dòng) sau, giấy đính kèm chung cuối.
Tệp gộp giấy của nhiều dòng → cảnh báo cán bộ. CCCD / OCR rỗng / LLM lỗi → dòng 1, giữ tên gốc. Không bỏ tệp nào.

Phần lõi (`plan_whole_files`, `classify_files`, `primary`) dùng chung cho các thủ tục attp-row Đà Nẵng cùng khuôn.
"""

import time
from collections.abc import Callable
from typing import Any

from app.config import settings
from app.pipelines._shared.documents import join_ocr_documents, representative_excerpt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

from ..dinh_kem_tach.planner import (
    _CCCD,
    _DON18,
    _GCN,
    _MAIN_TYPES,
    _OCR_TYPES,
    _OTHER,
    _ROWS,
    _SHARED_NAMES,
    _normalize_type,
    _row_of,
    _unique_name,
)
from .prompt import SYSTEM_PROMPT, build_user_prompt

# Trích đoạn đầu từng trang gửi LLM (representative_excerpt): đủ để liệt kê giấy trong PDF gộp vài chục trang.
_LLM_TEXT_MAX_CHARS = 8000

_FALLBACK_ROW = 1
# Đơn → giấy có dòng riêng (theo thứ tự dòng) → giấy đính kèm chung → CCCD.
_PRIORITY: tuple[str, ...] = tuple(dict.fromkeys((
    _DON18,
    *(row["types"][0] for _, row in sorted(_ROWS.items())),
    *(doc_type for _, row in sorted(_ROWS.items()) for doc_type in row["types"][1:]),
    _CCCD,
)))

BuildItems = Callable[[list[dict], dict[int, list[str]]], tuple[list[dict], list[dict], list[str]]]


# ---------------- Lõi dùng chung: OCR + một lượt LLM + gom kết quả ----------------
def doc_types_of(raw: Any, normalize: Callable[[str], str]) -> list[str]:
    """docTypes LLM trả (list hoặc một chuỗi) → loại đã chuẩn hóa, không trùng, giữ thứ tự."""
    if not isinstance(raw, list):
        raw = [raw]
    out: list[str] = []
    for value in raw:
        doc_type = normalize(str(value or ""))
        if doc_type not in out:
            out.append(doc_type)
    return out


def primary(doc_types: list[str], priority: tuple[str, ...], fallback: str) -> str:
    """Giấy chính của tệp: loại đứng trước nhất trong `priority`; không có thì `fallback`."""
    return next((doc_type for doc_type in priority if doc_type in doc_types), fallback)


async def classify_files(
    texts: dict[int, str],
    system_prompt: str,
    user_prompt: Callable[[list[dict[str, Any]]], str],
    normalize: Callable[[str], str],
) -> tuple[dict[int, list[str]], list[dict]]:
    """MỘT lượt LLM cho cả hồ sơ → ({fileIndex: docTypes}, mục LLM trả nguyên văn)."""
    documents = [{"index": index, "text": representative_excerpt(text, _LLM_TEXT_MAX_CHARS)}
                 for index, text in sorted(texts.items())]
    raw = await client.chat(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt(documents)}],
        max_tokens=max(600, min(3000, 300 + 80 * len(documents))),
        enable_thinking=settings.agent_reasoning,
    )
    items = [item for item in client.extract_json_block(raw).get("documents", []) or [] if isinstance(item, dict)]
    result: dict[int, list[str]] = {}
    for item in items:
        try:
            index = int(item.get("index", item.get("fileIndex")))
        except (TypeError, ValueError):
            continue
        doc_types = doc_types_of(item.get("docTypes", item.get("docType")), normalize)
        if index in texts and index not in result and doc_types:
            result[index] = doc_types
    return result, items


async def plan_whole_files(
    files: list[FileItem],
    session: dict | None,
    *,
    system_prompt: str,
    user_prompt: Callable[[list[dict[str, Any]]], str],
    normalize: Callable[[str], str],
    build_items: BuildItems,
) -> dict:
    """OCR từng tệp như chế độ tách → phân loại một lượt → `build_items` đặt mỗi tệp đúng một mục."""
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_pairs = [(i, f) for i, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]

    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file([f for _, f in ocr_pairs]) if ocr_pairs else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    ocr_by_index = {ri: res for (ri, _), res in zip(ocr_pairs, ocr_results)}
    for ri, res in ocr_by_index.items():
        if res.get("error"):
            errors.append(f"OCR fileIndex={ri} {raw_files[ri].get('name')}: {res['error']}")
    texts = {i: str(res.get("text")) for i, res in ocr_by_index.items() if str(res.get("text") or "").strip()}

    t1 = time.monotonic()
    types_by_file: dict[int, list[str]] = {}
    raw_documents: list[dict] = []
    if texts:
        try:
            types_by_file, raw_documents = await classify_files(texts, system_prompt, user_prompt, normalize)
        except Exception as exc:  # noqa: BLE001 — LLM lỗi → mọi tệp về dòng dự phòng, giữ tên gốc
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, classified, warnings = build_items(raw_files, types_by_file)
    errors.extend(warnings)

    indexed_ocr = [{**res, "name": f"fileIndex={i} · {raw_files[i].get('name')}"} for i, res in ocr_by_index.items()]
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [raw_files[i]["name"] for i in texts],
            "llmDocuments": [raw_files[i]["name"] for i in sorted(texts)],
            "sessionId": (session or {}).get("request_id"),
            "classified": classified,
            "attachmentMode": "preserve_files",
        },
        "ocr_text": join_ocr_documents(indexed_ocr),
        "llm_output": {"documents": raw_documents},
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }


def shared_row_warning(component_name: str, file_names: list[str]) -> str:
    return (f"Giấy tờ không có dòng riêng hoặc chưa rõ loại đã đính chung dòng \"{component_name}\": "
            + "; ".join(file_names) + ".")


def merged_file_warning(file_name: str, row: int, row_label: str, others: list[int]) -> str:
    return (f"'{file_name}' gộp nhiều giấy tờ — đính nguyên tệp vào dòng {row} ({row_label}), không tách sang dòng "
            f"{', '.join(map(str, others))}.")


# ---------------- Bảng 9 dòng của thủ tục này ----------------
def build_plan_items(
    raw_files: list[dict], types_by_file: dict[int, list[str]],
) -> tuple[list[dict], list[dict], list[str]]:
    """Mỗi tệp → đúng một mục attp-row (không sourceSegments). Thuần tất định, không gọi OCR/LLM."""
    found = {doc_type for doc_types in types_by_file.values() for doc_type in doc_types}
    entries = []
    for index, file in enumerate(raw_files):
        doc_types = types_by_file.get(index, [])
        doc_type = primary(doc_types, _PRIORITY, _OTHER)
        row_idx = _row_of(doc_type, found) or _FALLBACK_ROW
        others = sorted({row for item in doc_types if (row := _row_of(item, found))} - {row_idx})
        entries.append((index, str(file.get("name") or f"file-{index + 1}"), doc_type, doc_types, row_idx, others))

    def order(entry: tuple) -> tuple:
        row_types = _ROWS[entry[4]]["types"]
        return entry[4], row_types.index(entry[2]) if entry[2] in row_types else 99, entry[0]

    attachments: list[dict] = []
    classified: list[dict] = []
    warnings: list[str] = []
    shared: list[str] = []
    used_names: set[str] = set()
    for index, file_name, doc_type, doc_types, row_idx, others in sorted(entries, key=order):
        row = _ROWS[row_idx]
        if others or _row_of(doc_type, found) is None:
            base = file_name  # tệp gộp nhiều dòng / CCCD / chưa rõ loại: giữ tên gốc để cán bộ nhận ra.
        elif _MAIN_TYPES.get(doc_type) == row_idx:
            base = row["documentName"]
        else:
            base = _SHARED_NAMES.get(doc_type, row["documentName"])
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": _unique_name(base, used_names, file_name),
            "componentName": row["componentName"],
            "componentIndex": row_idx,
            "loaiBan": row["loaiBan"],
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": doc_type,
            "includedTypes": doc_types or [doc_type],
        })
        classified.append({"fileIndex": index, "fileName": file_name, "docType": doc_type, "docTypes": doc_types,
                           "source": "llm" if index in types_by_file else "unknown", "componentIndex": row_idx})
        if others:
            warnings.append(merged_file_warning(file_name, row_idx, row["documentName"], others))
        elif _row_of(doc_type, found) is None:
            shared.append(file_name)

    if shared:
        warnings.append(shared_row_warning(_ROWS[_FALLBACK_ROW]["componentName"], shared))
    if types_by_file and _DON18 not in found:
        warnings.append("Không tìm thấy Đơn đăng ký biến động Mẫu số 18 (dòng 1, bắt buộc) — vui lòng đính tay.")
    if types_by_file and _GCN not in found:
        warnings.append("Không tìm thấy Giấy chứng nhận đã cấp (dòng 2, bắt buộc) — vui lòng đính tay.")
    return attachments, classified, warnings


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options  # chế độ không tách không cần cài đặt nào khác.
    result = await plan_whole_files(
        files, session, system_prompt=SYSTEM_PROMPT, user_prompt=build_user_prompt, normalize=_normalize_type,
        build_items=build_plan_items,
    )
    result["extracted"]["rows"] = [{"componentIndex": k, **{n: v for n, v in row.items() if n != "types"}}
                                   for k, row in _ROWS.items()]
    return result

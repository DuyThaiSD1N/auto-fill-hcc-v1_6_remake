"""Đính kèm "Thủ tục chia, tách; sáp nhập; hợp nhất hội (cấp tỉnh)" (1.012945, attp-row) — chế độ KHÔNG tách giấy tờ.

Cài đặt "Tách giấy tờ" tắt (hoặc client cũ): OCR từng tệp như chế độ tách, MỘT lượt LLM liệt kê mọi loại giấy có trong
từng tệp (docTypes), rồi MỖI TỆP đính NGUYÊN, MỘT lần (không `sourceSegments`), vào dòng của giấy chính trong tệp theo
_PRIORITY: Đơn đề nghị trước; giấy có dòng riêng sau; Biên bản họp (đi chung dòng Nghị quyết), CCCD và giấy chưa rõ đứng
cuối. Bảng 7 dòng, ánh xạ loại giấy → dòng và shape item lấy từ chế độ tách (dinh_kem_tach/planner.py) nên hai chế độ
đặt cùng dòng. Tệp gộp nhiều giấy có dòng riêng → cảnh báo (bật "Tách giấy tờ" để tách). Chế độ này KHÔNG cắt trang
Đề án sang dòng 1 (trụ sở) / dòng 5 (Ban kiểm tra) như chế độ tách — dòng nào không có giấy thì cảnh báo.

OCR rỗng / LLM lỗi → tệp về dòng 2 (Đơn đề nghị), giữ tên gốc + cảnh báo. Không bỏ tệp nào.

`run_plan` (OCR + một lượt LLM + gói kết quả) dùng lại cho thông báo kết quả đại hội hội và đăng ký nội quy lao động.
"""

import time
from collections.abc import Callable
from typing import Any

from app.config import settings
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.attach.dinh_kem_tach.planner import (
    _coerce_int,
    _truncate,
    _unique_name,
)
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

from ..dinh_kem_tach.planner import (
    _BIEN_BAN,
    _CCCD,
    _DE_AN,
    _DIEU_LE,
    _DON,
    _DS_BCH,
    _LLTP,
    _NGHI_QUYET,
    _OTHER,
    _ROWS,
    _SYLL,
    _TRU_SO,
    _normalize_type,
    _row_of,
    _rule_type,
    _split_ocr_pages,
)
from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
# Hạn mức chữ mỗi tệp gửi LLM: lấy phần ĐẦU từng trang (tiêu đề giấy nằm đầu trang) để thấy đủ các giấy trong tệp gộp.
_LLM_FILE_CHARS = 9000

# Dòng dự phòng của chế độ tách cho CCCD / giấy chưa rõ loại.
_FALLBACK_ROW = 2
# Tệp gộp nhiều giấy: dòng của giấy ĐỨNG TRƯỚC nhận nguyên tệp.
_PRIORITY = (_DON, _DE_AN, _NGHI_QUYET, _DS_BCH, _DIEU_LE, _SYLL, _LLTP, _TRU_SO, _BIEN_BAN, _CCCD, _OTHER)
_NAMES = {
    _TRU_SO: "Văn bản xác nhận nơi dự kiến đặt trụ sở",
    _DON: "Đơn đề nghị chia, tách, sáp nhập, hợp nhất hội",
    _DE_AN: "Đề án chia, tách, sáp nhập, hợp nhất hội",
    _NGHI_QUYET: "Nghị quyết của ban chấp hành hội",
    _BIEN_BAN: "Biên bản họp",
    _DS_BCH: "Danh sách ban chấp hành và ban kiểm tra",
    _SYLL: "Sơ yếu lý lịch",
    _LLTP: "Phiếu lý lịch tư pháp số 1",
    _DIEU_LE: "Dự thảo điều lệ hội",
}


# ---------------- Phần chung: OCR + một lượt LLM (dùng lại cho thủ tục hội / nội quy lao động) ----------------
def llm_excerpt(text: str, limit: int = _LLM_FILE_CHARS) -> str:
    """Có header "Trang n/m" → đoạn đầu TỪNG trang kèm nhãn [Trang n]; không có → cắt đầu tệp."""
    pages, boundaries = _split_ocr_pages(text, 1)
    if not boundaries or len(pages) <= 1:
        return _truncate(text, limit)
    per_page = max(200, min(800, limit // len(pages)))
    return " ".join(f"[Trang {p}] {_truncate(t, per_page)}" for p, t in sorted(pages.items()))


def doc_types(raw: Any, normalize: Callable[[str], str]) -> list[str]:
    values = raw if isinstance(raw, list) else [raw]
    out: list[str] = []
    for value in values:
        doc_type = normalize(str(value or ""))
        if doc_type not in out:
            out.append(doc_type)
    return [t for t in out if t != _OTHER] or [_OTHER]


async def classify_files(
    documents: list[dict[str, Any]],
    system_prompt: str,
    user_prompt: Callable[[list[dict[str, Any]]], str],
    normalize: Callable[[str], str],
) -> tuple[dict[int, list[str]], list[dict]]:
    """MỘT lượt LLM cho cả hồ sơ → ({fileIndex: docTypes}, mảng LLM trả về)."""
    if not documents:
        return {}, []
    raw = await client.chat(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt(documents)}],
        max_tokens=max(600, min(4000, 120 * len(documents) + 300)),
        enable_thinking=settings.agent_reasoning,
    )
    answered = [item for item in client.extract_json_block(raw).get("documents", []) or [] if isinstance(item, dict)]
    sent = {d["index"] for d in documents}
    result: dict[int, list[str]] = {}
    for item in answered:
        index = _coerce_int(item.get("index", item.get("fileIndex")))
        if index in sent and index not in result:
            result[index] = doc_types(item.get("docTypes", item.get("types", item.get("type"))), normalize)
    return result, answered


BuildItems = Callable[[list[dict], dict[int, list[str]], dict[int, str]], tuple[list[dict], list[dict], list[str]]]


async def run_plan(
    files: list[FileItem],
    session: dict | None,
    *,
    system_prompt: str,
    user_prompt: Callable[[list[dict[str, Any]]], str],
    normalize: Callable[[str], str],
    rule_type: Callable[[str], str],
    build_items: BuildItems,
    rows: list[dict],
) -> dict:
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
    texts = {i: str(r.get("text") or "") for i, r in ocr_by_index.items() if str(r.get("text") or "").strip()}
    llm_docs = [{"index": i, "text": llm_excerpt(t)} for i, t in sorted(texts.items())]

    t1 = time.monotonic()
    answers: dict[int, list[str]] = {}
    answered: list[dict] = []
    if llm_docs:
        try:
            answers, answered = await classify_files(llm_docs, system_prompt, user_prompt, normalize)
        except Exception as e:  # noqa: BLE001 — LLM lỗi → mọi tệp về dòng dự phòng, giữ tên gốc
            errors.append(f"attachment_agent: {e}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    # LLM là chính; rule OCR theo tiêu đề đầu tệp chỉ vá tệp LLM trả other (như chế độ tách).
    types_by_file: dict[int, list[str]] = {}
    for index, types in answers.items():
        ruled = rule_type(texts.get(index, "")) if types == [_OTHER] else _OTHER
        types_by_file[index] = [ruled] if ruled != _OTHER else types
    attachments, classified, warnings = build_items(raw_files, types_by_file, texts)
    errors.extend(warnings)

    indexed_ocr = [{**res, "name": f"fileIndex={i} · {raw_files[i].get('name')}"} for i, res in ocr_by_index.items()]
    return {
        "attachments": attachments,
        "extracted": {
            "attachmentMode": "preserve_files",
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [raw_files[i]["name"] for i in texts],
            "llmDocuments": [raw_files[d["index"]]["name"] for d in llm_docs],
            "sessionId": (session or {}).get("request_id"),
            "classified": classified,
            "rows": rows,
        },
        "ocr_text": join_ocr_documents(indexed_ocr),
        "llm_output": {"documents": answered},
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }


def gop_warning(file_name: str, row: int | str, row_name: str, other_rows: list[int] | list[int | str]) -> str:
    return (f"'{file_name}' gộp nhiều giấy tờ — đính nguyên tệp một lần vào dòng {row} ({row_name}), không tách sang "
            f"dòng {', '.join(map(str, other_rows))}. Bật cài đặt \"Tách giấy tờ\" nếu cần đính từng giấy đúng dòng.")


# ---------------- Bảng dòng của thủ tục chia, tách, sáp nhập, hợp nhất hội ----------------
def primary(types: list[str]) -> str:
    return next((t for t in _PRIORITY if t in types), _OTHER)


def build_plan_items(
    raw_files: list[dict],
    types_by_file: dict[int, list[str]],
    texts: dict[int, str] | None = None,
) -> tuple[list[dict], list[dict], list[str]]:
    """{fileIndex: docTypes} → (attachments, classified, warnings). Thuần tất định, không gọi OCR/LLM."""
    del texts
    attachments: list[dict] = []
    classified: list[dict] = []
    warnings: list[str] = []
    shared: list[str] = []
    found: set[str] = set()
    used_names: set[str] = set()

    for index, file in enumerate(raw_files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        types = types_by_file.get(index) or [_OTHER]
        found.update(types)
        doc_type = primary(types)
        own_row = _row_of(doc_type)
        row_idx = own_row or _FALLBACK_ROW
        row = _ROWS[row_idx]
        other_rows = sorted({r for r in map(_row_of, types) if r} - {row_idx})
        # Tệp gộp hoặc chưa rõ loại giữ TÊN GỐC để cán bộ nhận ra; tệp một giấy mang tên giấy.
        base_name = file_name if other_rows or own_row is None else _NAMES.get(doc_type, row["documentName"])
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": _unique_name(base_name, used_names, row["documentName"]),
            "componentName": row["componentName"],
            "loaiBan": row["loaiBan"],
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": doc_type,
            "includedTypes": types,
            "componentIndex": row_idx,
        })
        classified.append({"fileIndex": index, "fileName": file_name, "type": doc_type, "docTypes": types,
                           "componentIndex": row_idx, "source": "llm" if index in types_by_file else "unknown",
                           **({} if own_row else {"routedTo": row_idx})})
        if own_row is None:
            shared.append(file_name)
        if other_rows:
            warnings.append(gop_warning(file_name, row_idx, row["componentName"], other_rows))

    order = {t: i for i, t in enumerate(_PRIORITY)}
    attachments.sort(key=lambda a: (a["componentIndex"], order.get(a["detectedType"], 99), a["fileIndex"]))
    if shared:
        warnings.append("Giấy tờ không có dòng riêng hoặc chưa rõ loại đã đính chung dòng "
                        f"\"{_ROWS[_FALLBACK_ROW]['componentName']}\" (dòng {_FALLBACK_ROW}): " + ", ".join(shared))
    if types_by_file:
        for row_idx, row in _ROWS.items():
            if not any(t in found for t in row["types"]):
                warnings.append(f"Không tìm thấy {row['documentName']} (dòng {row_idx}) — vui lòng đính tay.")
    return attachments, classified, warnings


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    return await run_plan(
        files, session,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=build_user_prompt,
        normalize=_normalize_type,
        rule_type=_rule_type,
        build_items=build_plan_items,
        rows=[{"componentIndex": k, **{n: v for n, v in row.items() if n != "types"}} for k, row in _ROWS.items()],
    )

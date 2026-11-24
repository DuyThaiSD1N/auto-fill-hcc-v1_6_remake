"""Đính kèm KHÔNG TÁCH cho "Cấp giấy phép thi công công trình trên đường bộ đang khai thác" (1.013061, attp-row
5 dòng) — cài đặt "Tách giấy tờ" tắt.

OCR từng tệp → MỘT lượt LLM liệt kê mọi loại giấy trong từng tệp → MỖI TỆP đính NGUYÊN, đúng MỘT lần (không
`sourceSegments`), vào dòng của thành phần chính trong tệp: Đơn → thành phần có dòng riêng (theo thứ tự xuất hiện)
→ giấy đi chung dòng Đơn (CCCD, giấy tờ khác). Bảng dòng, ánh xạ loại → dòng, rule vá loại theo tiêu đề / khung tên
bản vẽ dùng CHUNG với chế độ tách nên hai chế độ đặt giấy cùng dòng. Tệp gộp cả bộ hồ sơ → đính một lần vào dòng Đơn
và cảnh báo nên bật "Tách giấy tờ". LLM lỗi / trả other → rule OCR vá; vẫn không rõ (OCR rỗng, tệp Word) → dòng 1.
"""

import time
from typing import Any

from app.pipelines.cap_moi_chung_chi_hanh_nghe_moi_gioi_bat_dong_san.attach.dinh_kem_khong_tach.planner import (
    classify_files,
    llm_documents,
    ocr_files,
    ocr_texts,
    pick_primary,
    plan_result,
)
from app.process.schemas import FileItem

from ..dinh_kem_tach.planner import (
    _CCCD,
    _DON,
    _FALLBACK_ROW,
    _KHAC,
    _ORDER,
    _OTHER,
    _ROUTE,
    _ROWS,
    _is_word,
    _normalize_type,
    _rule_type,
    _unique_name,
    common_warnings,
    untick_optional,
)
from .prompt import SYSTEM_PROMPT, build_user_prompt

# Thành phần chính của tệp gộp: Đơn → thành phần có dòng riêng → giấy đi chung dòng Đơn; cùng tầng thì giấy trước.
_TIERS: tuple[frozenset[str], ...] = (
    frozenset({_DON}),
    frozenset(_ROUTE) - {_DON},
    frozenset({_CCCD, _KHAC}),
)


def _file_types(file: dict, text: str, llm: list[str] | None) -> tuple[list[str], str]:
    """Loại giấy trong tệp + nguồn. LLM là chính; LLM lỗi / chỉ trả other → rule theo tiêu đề; tệp Word → Đơn."""
    types = [t for t in llm or [] if t != _OTHER]
    if types:
        return types, "llm"
    doc_type = _rule_type(text)
    if doc_type != _OTHER:
        return [doc_type], "rule"
    if _is_word(file):
        return [_DON], "word"
    return [], "unknown"


def build_plan_items(
    raw_files: list[dict],
    texts: dict[int, str],
    llm_types: dict[int, list[str]] | None = None,
) -> tuple[list[dict], list[dict], list[str]]:
    """Mỗi tệp → đúng MỘT item đính nguyên tệp. Thuần tất định, không gọi OCR/LLM."""
    order = {t: i for i, t in enumerate(_ORDER)}
    used_names: set[str] = set()
    items: list[tuple[int, int, dict]] = []
    classified: list[dict] = []
    warnings: list[str] = []
    found_rows: set[int] = set()
    found_types: set[str] = set()
    extra_names: list[str] = []

    for index, file in enumerate(raw_files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        types, source = _file_types(file, texts.get(index, ""), (llm_types or {}).get(index))
        primary = pick_primary(types, _TIERS, _OTHER)
        row_idx = _ROUTE.get(primary, _FALLBACK_ROW)
        row = _ROWS[row_idx]
        found_types.update(types)
        found_rows.update(_ROUTE[t] for t in types if t in _ROUTE)
        others = sorted({_ROUTE[t] for t in types if t in _ROUTE} - {row_idx})
        mixed = len(set(types)) > 1
        # Tệp một thành phần có dòng riêng mang tên thành phần; tệp gộp / không có dòng riêng giữ TÊN GỐC.
        base_name = row["documentName"] if primary in _ROUTE and not mixed else file_name
        item = {
            "fileIndex": index,
            "fileName": file_name,
            "documentName": _unique_name(base_name.replace("/", "-"), used_names, row["documentName"]),
            "componentName": row["componentName"],
            "componentIndex": row_idx,
            "loaiBan": row["loaiBan"],
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": primary,
            "includedTypes": types or [primary],
        }
        entry = {"fileIndex": index, "fileName": file_name, "type": primary, "docTypes": types, "source": source,
                 "componentIndex": row_idx}
        if primary not in _ROUTE:
            entry["routedTo"] = _FALLBACK_ROW
            if primary != _CCCD:
                extra_names.append(file_name)
        items.append((row_idx, order.get(primary, 99), item))
        classified.append(entry)
        if others:
            warnings.append(f"'{file_name}' gộp nhiều thành phần hồ sơ — chế độ không tách đính nguyên tệp một lần "
                            f"vào dòng {row_idx} ({row['documentName']}), không tách sang dòng "
                            f"{', '.join(map(str, others))}. Nên bật cài đặt \"Tách giấy tờ\" để mỗi thành phần về "
                            "đúng dòng.")

    attachments = [item for _, _, item in sorted(items, key=lambda p: (p[0], p[1], p[2]["fileIndex"]))]
    # Dòng tick mà không có tệp thì cổng chặn chuyển bước → bỏ tick theo tệp THẬT đính vào dòng (giấy nằm trong tệp
    # gộp đã đính ở dòng Đơn không tính).
    untick_optional(attachments, {item["componentIndex"] for item in attachments})
    warnings += common_warnings(found_rows, found_types, extra_names)
    return attachments, classified, warnings


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, list[str]]:
    if not documents:
        return {}
    return await classify_files(SYSTEM_PROMPT, build_user_prompt(documents), {d["index"] for d in documents},
                                _normalize_type)


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_by_index, ocr_ms = await ocr_files(raw_files, errors)
    texts = ocr_texts(ocr_by_index)
    llm_docs = llm_documents(texts)

    started = time.monotonic()
    llm_types: dict[int, list[str]] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001 — LLM lỗi → rule theo tiêu đề, không rõ thì dòng Đơn, giữ tên gốc
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, classified, warnings = build_plan_items(raw_files, texts, llm_types)
    errors.extend(warnings)
    return plan_result(raw_files, ocr_by_index, llm_docs, llm_types, attachments, classified, errors, session,
                       ocr_ms, llm_ms, rows=[{"componentIndex": k, **row} for k, row in _ROWS.items()])

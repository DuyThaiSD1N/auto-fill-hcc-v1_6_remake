"""Đính kèm KHÔNG TÁCH cho "Đăng ký lại phương tiện ... chuyển quyền sở hữu" (1.004002, attp-row 4 dòng) — cài đặt
"Tách giấy tờ" tắt.

OCR từng tệp → MỘT lượt LLM liệt kê mọi loại giấy trong từng tệp → MỖI TỆP đính NGUYÊN, đúng MỘT lần (không
`sourceSegments`), vào dòng của giấy chính trong tệp:
  Đơn Mẫu 07 → giấy có dòng riêng (biên lai lệ phí, GCN an toàn kỹ thuật, hợp đồng) → giấy đính chung dòng có sẵn
  (hóa đơn, GCN đăng ký cũ ở dòng 3; Đơn Mẫu 10 ở dòng 4) → CCCD (dòng Đơn).
Trong cùng một tầng lấy giấy xuất hiện trước. Bảng 4 dòng, ánh xạ loại → dòng, loại bản (GCN an toàn kỹ thuật chứng
thực → Bản sao), rule vá loại theo tiêu đề dùng CHUNG với chế độ tách. Tệp gộp nhiều giấy ở các dòng khác nhau → cảnh
báo. Dòng 1, 2 không có tệp → `untickRows` như chế độ tách. LLM lỗi / trả other → rule theo tiêu đề đầu tệp; vẫn không
rõ (OCR rỗng) → dòng 4 (Đơn), giữ tên gốc.
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
    _BIEN_LAI,
    _CCCD,
    _CONDITIONAL_ROWS,
    _DON_07,
    _DON_10,
    _FALLBACK_ROW,
    _GCN_ATKT,
    _GCN_DK,
    _HOA_DON,
    _HOP_DONG,
    _ORDER,
    _OTHER,
    _REQUIRED,
    _ROUTE,
    _ROWS,
    _certified,
    _normalize_type,
    _rule_type,
    _unique_name,
)
from .prompt import SYSTEM_PROMPT, build_user_prompt

_TIERS: tuple[frozenset[str], ...] = (
    frozenset({_DON_07}),
    frozenset({_BIEN_LAI, _GCN_ATKT, _HOP_DONG}),
    frozenset({_HOA_DON, _GCN_DK, _DON_10}),
    frozenset({_CCCD}),
)


def _file_types(text: str, llm: list[str] | None) -> tuple[list[str], str]:
    """LLM là chính; LLM lỗi / chỉ trả other → rule theo tiêu đề đầu tệp (như chế độ tách)."""
    types = [t for t in llm or [] if t != _OTHER]
    if types:
        return types, "llm"
    doc_type = _rule_type(text)
    return ([doc_type], "rule") if doc_type != _OTHER else ([], "unknown")


def build_plan_items(
    raw_files: list[dict],
    texts: dict[int, str],
    llm_types: dict[int, list[str]] | None = None,
) -> tuple[list[dict], list[dict], list[str]]:
    """Mỗi tệp → đúng MỘT item đính nguyên tệp. Thuần tất định, không gọi OCR/LLM."""
    order = {t: i for i, t in enumerate(_ORDER)}
    used_names: set[str] = set()
    own: list[tuple[int, int, dict]] = []
    extra: list[dict] = []
    classified: list[dict] = []
    warnings: list[str] = []
    found_rows: set[int] = set()
    found_types: set[str] = set()
    extra_names: list[str] = []

    for index, file in enumerate(raw_files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        text = texts.get(index, "")
        types, source = _file_types(text, (llm_types or {}).get(index))
        primary = pick_primary(types, _TIERS, _OTHER)
        row_idx = _ROUTE.get(primary, _FALLBACK_ROW)
        row = _ROWS[row_idx]
        found_types.update(types)
        found_rows.update(_ROUTE[t] for t in types if t in _ROUTE)
        others = sorted({_ROUTE[t] for t in types if t in _ROUTE} - {row_idx})
        mixed = len(set(types)) > 1
        # Tệp một giấy có dòng mang tên giấy; tệp gộp / không có dòng riêng / không rõ giữ TÊN GỐC.
        base_name = row["documentName"] if primary in _ROUTE and not mixed else file_name
        item = {
            "fileIndex": index,
            "fileName": file_name,
            "documentName": _unique_name(base_name.replace("/", "-"), used_names, row["documentName"]),
            "componentName": row["componentName"],
            "componentIndex": row_idx,
            "loaiBan": "Bản sao" if row_idx == 2 and _certified(text) else row["loaiBan"],
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": primary,
            "includedTypes": types or [primary],
        }
        entry = {"fileIndex": index, "fileName": file_name, "type": primary, "docTypes": types, "source": source,
                 "componentIndex": row_idx}
        if primary in _ROUTE:
            own.append((row_idx, order.get(primary, 99), item))
        else:
            extra.append(item)
            extra_names.append(file_name)
            entry["routedTo"] = _FALLBACK_ROW
        classified.append(entry)
        if others:
            warnings.append(f"'{file_name}' gộp nhiều giấy tờ — đính nguyên tệp một lần vào dòng {row_idx} "
                            f"({row['documentName']}), không tách sang dòng {', '.join(map(str, others))}.")

    attachments = [item for _, _, item in sorted(own, key=lambda p: (p[0], p[1], p[2]["fileIndex"]))] + extra

    # Dòng 1, 2 chỉ áp dụng một số phương tiện — không có tệp ở dòng đó thì bỏ tick (như chế độ tách).
    rows_with_item = {item["componentIndex"] for item in attachments}
    untick = [_ROWS[idx]["componentName"] for idx in _CONDITIONAL_ROWS if idx not in rows_with_item]
    if attachments and untick:
        attachments[0]["untickRows"] = untick

    # --- Cảnh báo (cùng nội dung chế độ tách) ---
    for row_idx, label in _REQUIRED:
        if row_idx not in found_rows:
            warnings.append(f"Chưa có {label} (dòng {row_idx}) — cần bổ sung.")
    for row_idx, label in _CONDITIONAL_ROWS.items():
        if row_idx not in found_rows:
            warnings.append(f"Hồ sơ không có {label} — đã bỏ tick dòng {row_idx}; bổ sung nếu phương tiện thuộc diện.")
    if _HOP_DONG in found_types and _GCN_DK not in found_types:
        warnings.append("Chưa thấy Giấy chứng nhận đăng ký phương tiện cũ trong hồ sơ — cần nộp kèm để đăng ký lại.")
    if extra_names:
        warnings.append(f"Giấy tờ không có dòng riêng hoặc chưa rõ loại đã đính chung dòng "
                        f"\"{_ROWS[_FALLBACK_ROW]['componentName']}\": " + "; ".join(extra_names))
    return attachments, classified, warnings


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, list[str]]:
    if not documents:
        return {}
    return await classify_files(SYSTEM_PROMPT, build_user_prompt(documents), {d["index"] for d in documents},
                                _normalize_type)


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options or {}
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

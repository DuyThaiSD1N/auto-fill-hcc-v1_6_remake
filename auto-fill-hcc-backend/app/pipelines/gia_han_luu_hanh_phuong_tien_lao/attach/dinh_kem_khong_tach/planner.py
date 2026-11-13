"""Đính kèm KHÔNG TÁCH cho "Gia hạn thời gian lưu hành tại Việt Nam cho phương tiện của Lào" (cổng Bộ Xây dựng,
attp-row 2 dòng) — cài đặt "Tách giấy tờ" tắt.

OCR từng tệp → MỘT lượt LLM liệt kê mọi loại giấy trong từng tệp → MỖI TỆP đính NGUYÊN, đúng MỘT lần (không
`sourceSegments`), vào dòng của giấy chính trong tệp: Giấy đề nghị gia hạn (dòng 1) → Giấy phép liên vận (dòng 2) →
giấy không có dòng riêng (báo giá / giấy chứng minh lý do, ủy quyền, CCCD) đính chung dòng 1. Bảng dòng, tên tài liệu
và chuẩn hóa loại dùng CHUNG với chế độ tách. Phân loại THUẦN LLM như chế độ tách: LLM lỗi / OCR rỗng → dòng 1, giữ
tên gốc, có cảnh báo. Tệp gộp Giấy đề nghị + Giấy phép liên vận → đính dòng 1, cảnh báo cán bộ.
"""

import time
from pathlib import Path
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
    _CHUNG_MINH,
    _DE_NGHI,
    _EXTRA_NAMES,
    _FALLBACK,
    _GPLV,
    _OTHER,
    _ROWS,
    _UY_QUYEN,
    _normalize_type,
    _unique_name,
)
from .prompt import SYSTEM_PROMPT, build_user_prompt

_TIERS: tuple[frozenset[str], ...] = (
    frozenset({_DE_NGHI}),
    frozenset({_GPLV}),
    frozenset({_CHUNG_MINH, _UY_QUYEN, _CCCD}),
)


def build_plan_items(
    raw_files: list[dict],
    llm_types: dict[int, list[str]] | None = None,
) -> tuple[list[dict], list[dict], list[str]]:
    """Mỗi tệp → đúng MỘT item đính nguyên tệp. Thuần tất định, không gọi OCR/LLM."""
    used_names: set[str] = set()
    attachments: list[dict] = []
    classified: list[dict] = []
    warnings: list[str] = []
    unknown: list[str] = []

    for index, file in enumerate(raw_files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        types = [t for t in (llm_types or {}).get(index) or [] if t != _OTHER]
        primary = pick_primary(types, _TIERS, _OTHER)
        row = _ROWS[primary if primary in _ROWS else _FALLBACK]
        mixed = len(set(types)) > 1
        if primary == _OTHER:
            unknown.append(file_name)
        # Tệp một giấy mang tên giấy; tệp gộp / không rõ loại giữ TÊN GỐC (bỏ đuôi tệp).
        if mixed or primary == _OTHER:
            base_name = Path(file_name).stem
        else:
            base_name = row["documentName"] if primary in _ROWS else _EXTRA_NAMES.get(primary, "Giấy tờ kèm theo")
        document_name = _unique_name(base_name, used_names, row["documentName"])
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": document_name,
            "componentName": row["componentName"],
            "componentIndex": row["componentIndex"],
            "loaiBan": "Bản chính",
            "target": "attp-row",
            # Cổng tick sẵn mọi dòng → dòng không đính bị bắt buộc khi chuyển bước; FE bỏ tick trước khi đính.
            "untickUnplannedRows": True,
            "needsAddComponent": False,
            "detectedType": primary,
        })
        classified.append({"fileIndex": index, "fileName": file_name, "type": primary, "docTypes": types,
                           "source": "llm" if types else "unknown", "documentName": document_name,
                           "componentIndex": row["componentIndex"]})
        other_rows = sorted({_ROWS[t]["componentIndex"] for t in types if t in _ROWS} - {row["componentIndex"]})
        if other_rows:
            warnings.append(f"'{file_name}' gộp nhiều giấy tờ — đính nguyên tệp một lần vào dòng "
                            f"{row['componentIndex']} ({row['documentName']}), không tách sang dòng "
                            f"{', '.join(map(str, other_rows))}.")

    if unknown:
        warnings.append("Chưa nhận ra loại giấy tờ, đã đính chung vào dòng Giấy đề nghị gia hạn để không bỏ sót — "
                        "cán bộ kiểm tra lại: " + "; ".join(unknown))
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
    llm_docs = llm_documents(ocr_texts(ocr_by_index))

    started = time.monotonic()
    llm_types: dict[int, list[str]] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001 — LLM lỗi → mọi tệp về dòng 1, giữ tên gốc
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, classified, warnings = build_plan_items(raw_files, llm_types)
    errors.extend(warnings)
    return plan_result(raw_files, ocr_by_index, llm_docs, llm_types, attachments, classified, errors, session,
                       ocr_ms, llm_ms)

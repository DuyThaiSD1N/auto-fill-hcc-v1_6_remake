"""Đính kèm KHÔNG TÁCH cho "Hỗ trợ cơ sở sản xuất bị thiệt hại do dịch bệnh động vật" (1.013997, cổng ngành Nông
nghiệp và Môi trường — attp-row) — cài đặt "Tách giấy tờ" tắt.

Bảng thành phần hồ sơ CHỈ CÓ MỘT dòng (Đơn đề nghị Mẫu số 2a/2b) → mọi tệp vào dòng đó, MỖI TỆP đính NGUYÊN, đúng MỘT
lần (không `sourceSegments`). OCR từng tệp → MỘT lượt LLM liệt kê loại giấy trong từng tệp; giấy chính chỉ quyết định
thứ tự và tên tài liệu: Đơn → Biên bản tiêu hủy → không rõ loại → CCCD (như chế độ tách). Dòng, loại bản, tên tài liệu
và rule vá loại dùng CHUNG với chế độ tách. LLM lỗi / trả other → rule theo tiêu đề đầu tệp; vẫn không rõ (OCR rỗng)
→ giữ tên gốc, cảnh báo.
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
    _BIEN_BAN,
    _CCCD,
    _DON,
    _DON_ROW,
    _LABELS,
    _ORDER,
    _OTHER,
    _normalize_type,
    _rule_type,
)
from .prompt import SYSTEM_PROMPT, build_user_prompt

_TIERS: tuple[frozenset[str], ...] = (frozenset({_DON}), frozenset({_BIEN_BAN}), frozenset({_CCCD}))
# Thứ tự tệp trên dòng Đơn: Đơn → Biên bản → không rõ loại → CCCD.
_RANK = {doc_type: i for i, doc_type in enumerate([*_ORDER, _CCCD])}


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
    """Mỗi tệp → đúng MỘT item đính nguyên tệp ở dòng Đơn. Thuần tất định, không gọi OCR/LLM."""
    picked: list[tuple[int, str, list[str], str]] = []
    for index, _file in enumerate(raw_files):
        types, source = _file_types(texts.get(index, ""), (llm_types or {}).get(index))
        picked.append((index, pick_primary(types, _TIERS, _OTHER), types, source))
    picked.sort(key=lambda p: (_RANK[p[1]], p[0]))

    attachments: list[dict] = []
    classified: list[dict] = []
    # FE coi tệp trùng tên đã có trên dòng là đã đính → mỗi item một tên.
    used_names: set[str] = set()
    unknown: list[str] = []
    cccd: list[str] = []
    found: set[str] = set()
    for index, primary, types, source in picked:
        file_name = str(raw_files[index].get("name") or f"file-{index + 1}")
        found.update(types)
        # Tệp một giấy mang tên giấy; tệp gộp / không rõ loại giữ TÊN GỐC (bỏ đuôi tệp).
        mixed = len(set(types)) > 1
        base = (Path(file_name).stem if mixed or primary == _OTHER else _LABELS[primary]).replace("/", "-")
        document_name, n = base, 2
        while document_name in used_names:
            document_name, n = f"{base[:46]} {n}", n + 1
        used_names.add(document_name)
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": document_name,
            "componentName": _DON_ROW["componentName"],
            "componentIndex": _DON_ROW["componentIndex"],
            "loaiBan": _DON_ROW["loaiBan"],
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": primary,
        })
        entry = {"fileIndex": index, "fileName": file_name, "type": primary, "docTypes": types, "source": source,
                 "componentIndex": _DON_ROW["componentIndex"]}
        if primary == _OTHER:
            unknown.append(file_name)
        elif primary == _CCCD:
            cccd.append(file_name)
            entry["routedTo"] = _DON
        classified.append(entry)

    warnings: list[str] = []
    if _DON not in found:
        warnings.append(
            "Chưa có Đơn đề nghị hỗ trợ thiệt hại (Mẫu số 2a/2b) — cần bổ sung; đã đính Biên bản vào dòng Đơn."
        )
    if unknown:
        warnings.append(
            "Không xác định được loại giấy tờ, đã đính chung dòng Đơn đề nghị (cán bộ kiểm tra lại): "
            + "; ".join(unknown)
        )
    if cccd:
        warnings.append(
            "Giấy tờ không có dòng riêng hoặc chưa rõ loại đã đính chung dòng \"Đơn đề nghị hỗ trợ\": "
            + ", ".join(cccd) + "."
        )
    return attachments, sorted(classified, key=lambda c: c["fileIndex"]), warnings


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
        except Exception as exc:  # noqa: BLE001 — LLM lỗi → rule theo tiêu đề, không rõ thì giữ tên gốc
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, classified, warnings = build_plan_items(raw_files, texts, llm_types)
    errors.extend(warnings)
    return plan_result(raw_files, ocr_by_index, llm_docs, llm_types, attachments, classified, errors, session,
                       ocr_ms, llm_ms)

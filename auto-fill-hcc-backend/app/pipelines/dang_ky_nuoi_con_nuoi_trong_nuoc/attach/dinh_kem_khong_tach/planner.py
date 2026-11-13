"""Đính kèm KHÔNG TÁCH cho "Đăng ký việc nuôi con nuôi trong nước" (2.001263, Cổng DVC quốc gia) — cài đặt "Tách
giấy tờ" tắt.

MỖI TỆP đính NGUYÊN, đúng MỘT lần (không `sourceSegments`), vào thành phần của giấy chính trong tệp. Loại giấy của tệp
lấy như chế độ tách: luật OCR theo tiêu đề (cả tệp + từng trang, `_segments_of_file`) là chính, MỘT lượt LLM cho cả hồ
sơ liệt kê loại giấy từng tệp (dùng khi luật không nhận ra), giấy tùy thân / khám sức khỏe / xác nhận tình trạng hôn
nhân phân xử chủ thể bằng số định danh trên đơn. Giấy chính:
  dòng có sẵn STT 1–4 (CCCD, khám sức khỏe của cha mẹ nuôi, hoàn cảnh kinh tế, tình trạng hôn nhân) → thành phần thêm
  mới (khai sinh, khám sức khỏe, ảnh của trẻ, giấy tờ cha mẹ đẻ, lý lịch tư pháp, ủy quyền) → giấy khác;
cùng tầng thì giấy xuất hiện trước. Đơn xin nhận con nuôi khai bằng eForm (STT 5) nên không phải giấy chính; tệp CHỈ có
đơn / tài liệu kẹp nhầm không đính, như chế độ tách. Mỗi dòng có sẵn / mỗi loại thêm mới nhận MỘT tệp: nhiều tệp cùng
giấy chính → ghép nguyên tệp (`sourceFileIndexes`) như chế độ tách. Tệp gộp nhiều giấy thuộc thành phần khác → cảnh
báo. LLM lỗi / OCR hụt → luật OCR; vẫn không rõ → thành phần thêm mới mang tên gốc của tệp.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines.cap_moi_chung_chi_hanh_nghe_moi_gioi_bat_dong_san.attach.dinh_kem_khong_tach.planner import (
    llm_documents,
    ocr_files,
    ocr_texts,
    parse_doc_types,
    pick_primary,
    plan_result,
)
from app.process.schemas import FileItem
from app.services.llm import client

from ..dinh_kem_tach.planner import (
    _ALLOWED_DOC_TYPES,
    _APPLICATION,
    _APPLICATION_LABEL,
    _CHILD_PHOTO,
    _EXISTING_ROWS,
    _MARRIAGE,
    _NEW_GROUP_LABELS,
    _OCR_TYPES,
    _OTHER,
    _OTHER_LABEL,
    _SKIP,
    _SKIP_LABEL,
    _application_ids,
    _application_text,
    _is_photo,
    _normalize_doc_type,
    _page_doc_type,
    _plan_item,
    _resolve_subject,
    _rule_doc_type,
    _segments_of_file,
    _split_pages,
    _unique_document_name,
)
from .prompt import SYSTEM_PROMPT, build_user_prompt

_TIERS: tuple[frozenset[str], ...] = (
    frozenset(_EXISTING_ROWS),
    frozenset(_NEW_GROUP_LABELS),
    frozenset({_OTHER}),
)
_LABELS = {**{t: row[2] for t, row in _EXISTING_ROWS.items()}, **_NEW_GROUP_LABELS}


def build_plan_items(
    files: list[dict],
    ocr_by_index: dict[int, dict],
    llm_types: dict[int, dict[str, Any]] | None = None,
) -> tuple[list[dict], list[dict], list[str]]:
    """Mỗi tệp → đúng MỘT nguồn nguyên tệp trong một item. Thuần tất định, không gọi OCR/LLM."""
    llm_types = llm_types or {}
    entries: list[dict] = []
    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        ocr_item = ocr_by_index.get(idx) or {}
        text = str(ocr_item.get("text") or "")
        detected = llm_types.get(idx) or {}
        llm_list = [t for t in detected.get("types") or [] if t in _ALLOWED_DOC_TYPES]
        if _is_photo(text, ocr_item.get("error")):
            # Đi trước LLM như chế độ tách: vài ký tự chữ ký nháy trên ảnh từng bị LLM đặt làm tên tài liệu.
            doc_type, source, llm_list, llm_name = _CHILD_PHOTO, "rule", [], ""
        else:
            rule_type = _rule_doc_type(text)
            llm_first = next((t for t in llm_list if t != _OTHER), llm_list[0] if llm_list else "")
            doc_type = rule_type or llm_first or _OTHER
            source = "rule" if rule_type else ("llm" if llm_first else "default")
            llm_name = str(detected.get("documentName") or "")
        entries.append({"idx": idx, "fileName": file_name, "text": text, "pages": _split_pages(text),
                        "type": doc_type, "llmTypes": llm_list, "llmName": llm_name, "source": source})

    adopter_ids: set[str] = set()
    child_ids: set[str] = set()
    for entry in entries:
        if entry["type"] == _APPLICATION:
            adopters, children = _application_ids(_application_text(entry["pages"]) or entry["text"])
            adopter_ids |= adopters
            child_ids |= children
    has_marriage = any(_page_doc_type(page) == _MARRIAGE for entry in entries for page in entry["pages"])

    grouped: dict[str, list[dict]] = {}
    has_marriage_cert = False
    attachments: list[dict] = []
    classified: list[dict] = []
    warnings: list[str] = []
    used_names: set[str] = set()
    for entry in entries:
        entry["type"] = _resolve_subject(entry["type"], entry["text"], adopter_ids, child_ids, has_marriage)
        types: list[str] = []
        for segment in _segments_of_file(entry, adopter_ids, child_ids, has_marriage):
            if segment["type"] not in types:
                types.append(segment["type"])
        # LLM chỉ bổ sung khi luật theo trang không thấy giấy đính được nào trong tệp.
        if not any(t in _LABELS for t in types):
            for raw in entry["llmTypes"]:
                resolved = _resolve_subject(raw, entry["text"], adopter_ids, child_ids, has_marriage)
                if resolved not in types:
                    types.append(resolved)
        primary = pick_primary(types, _TIERS, "")
        source = {"fileIndex": entry["idx"], "pageIndexes": None}
        record = {"fileName": entry["fileName"], "fileIndex": entry["idx"], "pageFrom": 1,
                  "pageTo": max(1, len(entry["pages"])), "docType": primary or entry["type"], "docTypes": types,
                  "source": entry["source"]}
        if not primary:
            # Chỉ có đơn (khai eForm ở STT 5) / tài liệu kẹp nhầm → không đính, như chế độ tách.
            label = _APPLICATION_LABEL if _APPLICATION in types else _SKIP_LABEL
            classified.append({**record, "docType": _APPLICATION if _APPLICATION in types else _SKIP,
                               "documentName": label, "target": "skip", "componentIndex": None})
            continue
        others = [t for t in types if t in _LABELS and t != primary]
        if others:
            warnings.append(f"'{entry['fileName']}' gộp nhiều giấy tờ — đính nguyên tệp một lần vào "
                            f"\"{_LABELS.get(primary, _OTHER_LABEL)}\", không tách: "
                            + ", ".join(_LABELS[t] for t in others) + ".")
        if primary in _LABELS:
            grouped.setdefault(primary, []).append(source)
            if primary == _MARRIAGE and any(_page_doc_type(page) == _MARRIAGE for page in entry["pages"]):
                has_marriage_cert = True
            classified.append({**record, "group": primary})
            continue
        # Không rõ loại → thành phần thêm mới mang tên giấy LLM đọc được, không có thì tên gốc của tệp.
        document_name = _unique_document_name(entry["llmName"] or entry["fileName"], used_names, _OTHER_LABEL)
        attachments.append(_plan_item(files, [source], document_name,
                                      component_name=document_name, component_index=None))
        classified.append({**record, "documentName": document_name, "target": "new", "componentIndex": None})
        warnings.append(f"Chưa nhận diện chắc loại giấy tờ cho '{entry['fileName']}' — đính thành phần mới "
                        f"\"{document_name}\"; cán bộ kiểm tra lại.")

    group_items: dict[str, dict] = {}

    def add_group(doc_type: str, label: str, component_name: str | None, component_index: int | None) -> None:
        sources = grouped.get(doc_type)
        if not sources:
            return
        document_name = _unique_document_name(label, used_names, label)
        item = _plan_item(files, sources, document_name,
                          component_name=component_name or document_name, component_index=component_index)
        attachments.append(item)
        group_items[doc_type] = item

    for doc_type, (component_index, component_name, label) in _EXISTING_ROWS.items():
        # Dòng 4 chỉ có giấy xác nhận tình trạng hôn nhân (người nhận con nuôi đơn thân).
        if doc_type == _MARRIAGE and not has_marriage_cert:
            label = "Giấy xác nhận tình trạng hôn nhân"
        add_group(doc_type, label, component_name, component_index)
    for doc_type, label in _NEW_GROUP_LABELS.items():
        add_group(doc_type, label, None, None)

    for record in classified:
        item = group_items.get(record.pop("group", None))
        if item:
            record.update(documentName=item["documentName"], target=item["target"],
                          componentIndex=item["componentIndex"])
    return attachments, classified, warnings


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """MỘT lượt LLM: {index: {"types": [...], "documentName": "..."}}."""
    if not documents:
        return {}
    raw = await client.chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(documents)},
        ],
        max_tokens=max(600, min(2000, 200 + 100 * len(documents))),
        enable_thinking=settings.agent_reasoning,
    )
    parsed = client.extract_json_block(raw)
    types = parse_doc_types(parsed, {d["index"] for d in documents}, _normalize_doc_type)
    names: dict[int, str] = {}
    for item in parsed.get("documents") or []:
        if not isinstance(item, dict):
            continue
        try:
            index = int(item.get("index"))
        except (TypeError, ValueError):
            continue
        if index in types and index not in names:
            names[index] = str(item.get("documentName") or item.get("title") or "").strip()
    return {i: {"types": t, "documentName": names.get(i, "")} for i, t in types.items()}


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options or {}
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_by_index, ocr_ms = await ocr_files(raw_files, errors)
    texts = ocr_texts(ocr_by_index)
    # Ảnh trẻ gần như không có chữ → không hỏi LLM (như chế độ tách).
    llm_docs = llm_documents(texts, skip=[i for i, text in texts.items() if _is_photo(text)])

    started = time.monotonic()
    llm_types: dict[int, dict[str, Any]] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001 — LLM lỗi → luật OCR; không rõ thì thành phần mới mang tên gốc
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, classified, warnings = build_plan_items(raw_files, ocr_by_index, llm_types)
    errors.extend(warnings)
    return plan_result(raw_files, ocr_by_index, llm_docs, {i: v["types"] for i, v in llm_types.items()},
                       attachments, classified, errors, session, ocr_ms, llm_ms,
                       skippedOcr=[f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES])

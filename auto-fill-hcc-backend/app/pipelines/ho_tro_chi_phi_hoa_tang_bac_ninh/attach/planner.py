"""Phân loại và định tuyến hồ sơ hỏa táng vào eForm Bắc Ninh."""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import normalize_document_name
from app.process.schemas import FileItem
from app.services.llm import client

from . import catalog
from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_LABEL_PRIORITY = [
    "to_khai",
    "hop_dong_hoa_tang",
    "bien_ban_uy_quyen",
    "trich_luc_khai_tu",
    "hoa_don_hoa_tang",
    "cccd",
    "khac",
]


def _truncate_text(text: str, limit: int = 5000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[:limit] + "..."


def labels_by_keywords(ocr_text: str) -> list[str]:
    text = _fold(ocr_text or "")
    labels: list[str] = []
    if (
        "don de nghi ho tro kinh phi hoa tang" in text
        or "to khai de nghi ho tro kinh phi hoa tang" in text
        or ("mau so 01" in text and "ho tro" in text and "hoa tang" in text)
    ):
        labels.append("to_khai")
    if "hop dong" in text and ("hoa tang" in text or "dien tang" in text):
        labels.append("hop_dong_hoa_tang")
    if ("bien ban uy quyen" in text or "van ban uy quyen" in text) and "uy quyen" in text:
        labels.append("bien_ban_uy_quyen")
    if any(marker in text for marker in ("trich luc khai tu", "giay bao tu", "giay chung tu")):
        labels.append("trich_luc_khai_tu")
    if ("hoa don" in text or "chung tu thanh toan" in text) and ("hoa tang" in text or "dien tang" in text):
        labels.append("hoa_don_hoa_tang")
    identity_markers = ("can cuoc cong dan", "citizen identity card", "chung minh nhan dan", "the can cuoc")
    if any(marker in text for marker in identity_markers):
        labels.append("cccd")
    return labels


def _labels_by_filename(name: str) -> list[str]:
    text = _fold(name or "")
    if "hop dong" in text and ("hoa tang" in text or "dien tang" in text):
        return ["hop_dong_hoa_tang"]
    if "uy quyen" in text:
        return ["bien_ban_uy_quyen"]
    if "khai tu" in text or "bao tu" in text or "chung tu" in text:
        return ["trich_luc_khai_tu"]
    if "hoa don" in text:
        return ["hoa_don_hoa_tang"]
    if any(marker in text for marker in ("cccd", "can cuoc", "cmnd")):
        return ["cccd"]
    if "to khai" in text or "don de nghi" in text:
        return ["to_khai"]
    return []


def _ordered_labels(values: list[str]) -> list[str]:
    found = {value for value in values if catalog.is_valid(value) and value != "khac"}
    return [label for label in _LABEL_PRIORITY if label in found]


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=900, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    parsed_docs = parsed.get("documents", []) or []
    raw_items: list[tuple[int, dict]] = []
    for item in parsed_docs:
        try:
            raw_items.append((int(item.get("index")), item))
        except Exception:  # noqa: BLE001
            continue
    offset = 0 if any(index == 0 for index, _ in raw_items) else 1
    valid = {item["index"] for item in documents}
    out: dict[int, dict[str, Any]] = {}
    for raw_index, item in raw_items:
        index = raw_index - offset
        if index not in valid:
            continue
        labels = item.get("labels")
        if not isinstance(labels, list):
            labels = [item.get("label")] if item.get("label") else []
        out[index] = {
            "labels": _ordered_labels([str(label or "") for label in labels]),
            "documentName": str(item.get("documentName") or "").strip(),
        }
    return out


def _unique_name(base: str, used: set[str], fallback: str) -> str:
    normalized = normalize_document_name(base, fallback)
    key = _fold(normalized)
    if key and key not in used:
        used.add(key)
        return normalized
    stem = normalized[:45].strip() or fallback[:45].strip()
    number = 2
    while True:
        candidate = f"{stem} {number}"[:50].strip()
        key = _fold(candidate)
        if key not in used:
            used.add(key)
            return candidate
        number += 1


def _build_item(
    file: dict,
    index: int,
    detected_label: str,
    route_label: str,
    document_name: str,
) -> dict:
    target, component_name, slot_key = catalog.resolve(route_label)
    return {
        "fileIndex": index,
        "fileName": str(file.get("name") or f"file-{index + 1}"),
        "documentName": document_name,
        "componentName": component_name,
        "target": target,
        "slotKey": slot_key,
        "needsAddComponent": False,
        "detectedType": detected_label,
    }


def build_plan_items(
    raw_files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, dict[str, Any]] | None = None,
) -> tuple[list[dict], list[dict]]:
    llm_types = llm_types or {}
    ocr_by_name = {item.get("name"): item for item in ocr_results}
    attachments: list[dict] = []
    classified: list[dict] = []
    used_names: set[str] = set()

    for index, file in enumerate(raw_files):
        ocr_text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        llm_item = llm_types.get(index) or {}
        labels = _ordered_labels(
            list(llm_item.get("labels") or [])
            + labels_by_keywords(ocr_text)
            + _labels_by_filename(str(file.get("name") or ""))
        )
        if not labels:
            labels = ["khac"]

        # Cổng chỉ dùng dòng 2 khi người dân tải một FILE RIÊNG chỉ chứa hợp đồng. File gộp có
        # hợp đồng cùng giấy tờ khác và mọi file lẻ còn lại đều vào dòng 1. Mỗi file chỉ sinh đúng
        # một plan item: tuyệt đối không nhân bản hay tách PDF để lấp cả hai dòng.
        detected_label = labels[0]
        route_label = (
            "hop_dong_hoa_tang"
            if labels == ["hop_dong_hoa_tang"]
            else "to_khai"
        )
        fallback = (
            "Hồ sơ hỗ trợ chi phí hỏa táng"
            if len(labels) > 1
            else catalog.display_name(detected_label)
        )
        suggested = str(llm_item.get("documentName") or "")
        document_name = _unique_name(suggested or fallback, used_names, fallback)
        item = _build_item(file, index, detected_label, route_label, document_name)
        attachments.append(item)
        classified.append({
            "fileName": file.get("name"),
            "label": detected_label,
            "labels": labels,
            "routeLabel": route_label,
            "documentName": document_name,
            "target": item["target"],
            "componentName": item["componentName"],
            "slotKey": item["slotKey"],
        })
    return attachments, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options or {}
    errors: list[str] = []
    raw_files = [{"name": file.name, "type": file.type, "dataUrl": file.dataUrl} for file in files]
    ocr_files = [file for file in raw_files if file.get("type") in _OCR_TYPES]

    from app.services import ocr

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    for result in ocr_results:
        if result.get("error"):
            errors.append(f"OCR {result.get('name')}: {result['error']}")

    ocr_by_name = {result.get("name"): result for result in ocr_results}
    llm_documents = [
        {"index": index, "text": _truncate_text(str(ocr_by_name.get(file.get("name"), {}).get("text") or ""))}
        for index, file in enumerate(raw_files)
    ]
    llm_documents = [item for item in llm_documents if item["text"]]

    started = time.monotonic()
    llm_types: dict[int, dict[str, Any]] = {}
    if llm_documents:
        try:
            llm_types = await _classify_with_llm(llm_documents)
        except Exception as error:  # noqa: BLE001
            errors.append(f"attachment_agent: {error}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, classified = build_plan_items(raw_files, ocr_results, llm_types)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [file["name"] for file in raw_files],
            "ocrDocuments": [item.get("name") for item in ocr_results if item.get("text")],
            "llmDocuments": [raw_files[item["index"]]["name"] for item in llm_documents],
            "sessionId": (session or {}).get("request_id"),
            "classified": classified,
        },
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "errors": errors,
    }

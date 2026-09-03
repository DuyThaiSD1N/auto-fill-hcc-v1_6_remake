"""Phân loại và định tuyến hồ sơ đăng ký biện pháp bảo đảm vào eForm Bắc Ninh 1.011441."""

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
    "phieu_01a", "hop_dong_bao_dam", "gcn_qsdd", "gcn_dkdn", "giay_gioi_thieu", "cccd", "khac",
]


def _truncate_text(text: str, limit: int = 5000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[:limit] + "..."


def labels_by_keywords(ocr_text: str) -> list[str]:
    text = _fold(ocr_text or "")
    labels: list[str] = []
    if "phieu yeu cau dang ky bien phap bao dam" in text or "mau so 01a" in text or (
        "phieu yeu cau" in text and "bien phap bao dam" in text
    ):
        labels.append("phieu_01a")
    if "hop dong the chap" in text or "hop dong bao dam" in text or ("hop dong" in text and "the chap" in text):
        labels.append("hop_dong_bao_dam")
    if "giay chung nhan quyen su dung dat" in text or ("quyen su dung dat" in text and "so vao so" in text):
        labels.append("gcn_qsdd")
    if "giay chung nhan dang ky doanh nghiep" in text or "ma so doanh nghiep" in text:
        labels.append("gcn_dkdn")
    if "giay gioi thieu" in text or "van ban uy quyen" in text or "giay uy quyen" in text:
        labels.append("giay_gioi_thieu")
    if any(m in text for m in ("can cuoc cong dan", "citizen identity card", "chung minh nhan dan", "the can cuoc")):
        labels.append("cccd")
    return labels


def _labels_by_filename(name: str) -> list[str]:
    text = _fold(name or "")
    out: list[str] = []
    if "phieu" in text or "01a" in text or "yeu cau" in text:
        out.append("phieu_01a")
    if "hop dong" in text or "the chap" in text or "hdtc" in text:
        out.append("hop_dong_bao_dam")
    if "gcn" in text and ("qsdd" in text or "dat" in text):
        out.append("gcn_qsdd")
    if "gioi thieu" in text or "uy quyen" in text:
        out.append("giay_gioi_thieu")
    if any(m in text for m in ("cccd", "can cuoc", "cmnd")):
        out.append("cccd")
    return out


def _ordered_labels(values: list[str]) -> list[str]:
    found = {value for value in values if catalog.is_valid(value) and value != "khac"}
    return [label for label in _LABEL_PRIORITY if label in found]


def _route_label(labels: list[str]) -> str:
    for label in _LABEL_PRIORITY:
        if label in labels:
            return label
    return "khac"


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


def _build_item(file: dict, index: int, detected_label: str, route_label: str, document_name: str) -> dict:
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

        detected_label = labels[0]
        route_label = _route_label(labels)
        fallback = (
            "Hồ sơ đăng ký biện pháp bảo đảm"
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

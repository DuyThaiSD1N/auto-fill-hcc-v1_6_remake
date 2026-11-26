"""Đính kèm 1.115460 Bắc Ninh — chế độ KHÔNG tách (cài đặt "Tách giấy tờ" tắt / client cũ).

Theo ảnh ánh xạ 25/11/2026: mỗi tệp giữ NGUYÊN, đính vào MỌI dòng có giấy tương ứng trong tệp — Đơn → TP-H05.000026,
GCN → TP-H05.000040, Văn bản cam kết thành viên hộ → CHUNG TP-H05.000049 + TP-H05.000051, CCCD → TP-H05.000049 Bản sao,
giấy khác → "File đính kèm khác". Mỗi dòng nhận một tệp một lần; tệp nào cũng sinh ít nhất một mục, không rớt tệp.
"""

import re

from app.pipelines._shared import fold as _fold
from app.pipelines._shared import normalize_document_name
from app.process.schemas import FileItem

from .. import catalog
from ..phan_trang import read_documents


def build_item(file_index: int, file_name: str, document_name: str, label: str,
               sources: list[dict] | None = None, row: tuple[str, str, str] | None = None) -> dict:
    target, component_name, slot_key = row or catalog.resolve(label)
    item = {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": component_name,  # mã TP-H05 (existing) hoặc "" (File đính kèm khác)
        "target": target,
        "slotKey": slot_key,
        "needsAddComponent": False,
        "detectedType": label,
    }
    if sources is not None:
        item["sourceSegments"] = sources
    return item


def build_items(file_index: int, file_name: str, document_name: str, label: str,
                sources: list[dict] | None = None) -> list[dict]:
    """Một giấy → một mục cho MỖI dòng nhận nó (Văn bản cam kết thành viên hộ đính chung 000049 + 000051)."""
    return [build_item(file_index, file_name, document_name, label, sources, row) for row in catalog.targets(label)]


def unique_name(base: str, used: set[str], fallback: str) -> str:
    # normalize_document_name lấy Path(...).stem: số hiệu "12/QĐ-UBND" bị cắt mất phần trước "/" → đổi trước.
    normalized = normalize_document_name(re.sub(r"[/\\.]+", " ", base or ""), fallback)
    key = _fold(normalized)
    if key and key not in used:
        used.add(key)
        return normalized
    stem = normalized[:45].strip() or fallback[:45].strip() or "Tài liệu"
    n = 2
    while True:
        candidate = f"{stem} {n}"[:50].strip()
        if _fold(candidate) not in used:
            used.add(_fold(candidate))
            return candidate
        n += 1


def whole_file_items(raw_files: list[dict], documents: list[dict]) -> list[dict]:
    """Giấy đã chia → mục đính NGUYÊN tệp: mỗi dòng thành phần có giấy trong tệp nhận cả tệp một lần."""
    attachments: list[dict] = []
    used: set[str] = set()
    for file_index, file in enumerate(raw_files):
        name = str(file.get("name") or f"file-{file_index + 1}")
        docs = [d for d in documents if d["fileIndex"] == file_index] or [{"label": "khac", "name": ""}]
        rows_done: set[tuple[str, str, str]] = set()  # mỗi dòng (kể cả File đính kèm khác) nhận tệp này một lần
        for label in dict.fromkeys(d["label"] for d in docs):
            items = [it for it in build_items(file_index, name, "", label)
                     if (it["target"], it["componentName"], it["slotKey"]) not in rows_done]
            if not items:
                continue
            fallback = catalog.display_name(label)
            document_name = unique_name(fallback, used, fallback)
            for it in items:
                rows_done.add((it["target"], it["componentName"], it["slotKey"]))
                attachments.append({**it, "documentName": document_name})
    return attachments


def extracted(raw_files: list[dict], documents: list[dict], session: dict | None, mode: str) -> dict:
    return {
        "documents": [f["name"] for f in raw_files],
        "attachmentMode": mode,
        "sessionId": (session or {}).get("request_id"),
        "giayTo": [
            {"fileName": raw_files[d["fileIndex"]]["name"], "label": d["label"], "name": d.get("name") or "",
             "source": d.get("source"),
             "pages": "cả tệp" if d["pages"] is None else [p + 1 for p in d["pages"]]}
            for d in documents
        ],
    }


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    _, documents, errors, stats = await read_documents(raw_files)
    return {
        "attachments": whole_file_items(raw_files, documents),
        "extracted": extracted(raw_files, documents, session, "whole_files"),
        "stats": stats,
        "errors": errors,
    }

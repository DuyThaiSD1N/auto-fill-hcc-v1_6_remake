"""Đính kèm 1.011442 Bắc Ninh — chế độ KHÔNG tách (cài đặt "Tách giấy tờ" tắt / client cũ).

Theo ảnh ánh xạ 12/11/2026: hồ sơ scan CHUNG một tệp thì đính NGUYÊN tệp vào MỌI dòng có giấy tương ứng trong tệp —
Phiếu 02a → KQ003703 Bản chính (có bản thứ hai → cả Bản sao), HĐ sửa đổi → KQ003704 Bản sao, văn bản căn cứ →
KQ003706 Bản sao, GCN → KQ003707 Bản chính, Giấy giới thiệu → KQ003709 Bản sao, HĐ thế chấp gốc / CCCD / khác →
"File đính kèm khác" (một lần mỗi tệp). Tệp nào cũng sinh ít nhất một mục, không rớt tệp.
"""

import re

from app.pipelines._shared import fold as _fold
from app.pipelines._shared import normalize_document_name
from app.process.schemas import FileItem

from .. import catalog
from ..phan_trang import read_documents


def build_item(file_index: int, file_name: str, document_name: str, label: str, copy_index: int = 0,
               sources: list[dict] | None = None) -> dict:
    target, component_name, slot_key = catalog.resolve(label, copy_index)
    item = {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": component_name,  # mã KQ (existing) hoặc "" (File đính kèm khác)
        "target": target,
        "slotKey": slot_key,
        "needsAddComponent": False,
        "detectedType": label,
    }
    if sources is not None:
        item["sourceSegments"] = sources
    return item


def unique_name(base: str, used: set[str], fallback: str) -> str:
    # normalize_document_name lấy Path(...).stem: số hiệu "7619/NHNo-TCNS" bị cắt mất phần trước "/" → đổi trước.
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
        labels = list(dict.fromkeys(d["label"] for d in docs))
        phieu_copies = sum(1 for d in docs if d["label"] == catalog.PHIEU)
        supplementary_done = False
        for label in labels:
            if catalog.is_supplementary(label):
                if supplementary_done:
                    continue
                supplementary_done = True
            fallback = catalog.display_name(label)
            copies = range(min(phieu_copies, 2)) if label == catalog.PHIEU else range(1)
            for copy_index in copies:
                document_name = unique_name(fallback, used, fallback)
                attachments.append(build_item(file_index, name, document_name, label, copy_index))
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

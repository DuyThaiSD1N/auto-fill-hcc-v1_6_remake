"""Đính kèm cho "Xét tuyển Viên chức (NĐ 85/2023) (Lai Châu)".

Thành phần hồ sơ có DUY NHẤT 1 ô (Lai Châu, nút "Chọn tệp tin"): Phiếu đăng ký dự tuyển Mẫu 01
(kèm hợp đồng lao động NĐ 115/2020) — Bản chính. Mọi file (Phiếu + CCCD) bơm vào ô này theo slotIndex 0
(engine fixed-slot). Không cần LLM phân loại (1 ô).
"""

import time

from app.process.schemas import FileItem

_SLOT_KEY = "phieu_du_tuyen_vien_chuc"
_SLOT_INDEX = 0
_SLOT_NAME = "Phiếu đăng ký dự tuyển theo mẫu số 01 ban hành kèm theo Nghị định số 85/2023/NĐ-CP"
_DOCUMENT_NAME = "Phiếu đăng ký dự tuyển viên chức (Mẫu số 01)"


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options, session
    raw_files = [{"name": f.name, "type": f.type} for f in files]
    if not raw_files:
        return {"attachments": [], "extracted": {}, "errors": ["Chưa có file nào để đính kèm."]}

    source_indexes = list(range(len(raw_files)))
    attachments = [{
        "fileIndex": 0,
        "sourceFileIndexes": source_indexes,   # gộp mọi file (Phiếu + CCCD) vào 1 ô
        "fileName": raw_files[0]["name"],
        "documentName": _DOCUMENT_NAME,
        "componentName": _SLOT_NAME,
        "target": "fixed-slot",
        "needsAddComponent": False,
        "detectedType": _DOCUMENT_NAME,
        "slotKey": _SLOT_KEY,
        "slotIndex": _SLOT_INDEX,
        "slotName": _SLOT_NAME,
    }]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "slots": [{"slotKey": _SLOT_KEY, "slotIndex": _SLOT_INDEX, "slotName": _SLOT_NAME}],
        },
        "stats": {"total_latency_ms": int(time.monotonic() * 0)},
        "errors": [],
    }

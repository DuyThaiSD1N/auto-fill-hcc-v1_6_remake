"""Đính kèm cho thủ tục cấp Giấy chứng nhận cơ sở đủ điều kiện ATTP.

Trang thành phần hồ sơ của thủ tục này gom toàn bộ giấy tờ vào một dòng
"A. Thành phần hồ sơ..." nên không cần OCR/LLM phân loại. Mỗi file được upload
lặp lại vào cùng slot vì cổng có thể chỉ nhận một file cho mỗi lần bấm
"Chọn tệp tin".
"""

import time
from pathlib import Path

from app.process.schemas import FileItem

_SLOT_KEY = "attp_dossier"
_SLOT_INDEX = 0
_SLOT_NAME = (
    "A. Thành phần hồ sơ: Đơn đề nghị cấp Giấy chứng nhận; Giấy chứng nhận đăng ký kinh doanh/"
    "doanh nghiệp; bản thuyết minh cơ sở vật chất, trang thiết bị; giấy xác nhận đủ sức khỏe; "
    "danh sách người sản xuất/kinh doanh đã tập huấn kiến thức an toàn thực phẩm"
)


def _document_name(file_name: str) -> str:
    stem = Path(file_name or "").stem.strip()
    return stem[:80] or "Tài liệu hồ sơ an toàn thực phẩm"


def _build_item(file: dict, index: int) -> dict:
    file_name = str(file.get("name") or f"file-{index + 1}")
    return {
        "fileIndex": index,
        "fileName": file_name,
        "documentName": _document_name(file_name),
        "componentName": _SLOT_NAME,
        "target": "fixed-slot",
        "componentIndex": 1,
        "needsAddComponent": False,
        "detectedType": "Tài liệu thành phần hồ sơ an toàn thực phẩm",
        "slotKey": _SLOT_KEY,
        "slotIndex": _SLOT_INDEX,
        "slotName": _SLOT_NAME,
        "repeatUpload": True,
    }


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    _ = options or {}
    _ = session
    t0 = time.monotonic()
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    attachments = [_build_item(file, idx) for idx, file in enumerate(raw_files)]
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "classified": [
                {
                    "fileName": item["fileName"],
                    "slotKey": item["slotKey"],
                    "slotIndex": item["slotIndex"],
                    "documentName": item["documentName"],
                }
                for item in attachments
            ],
            "slots": [
                {
                    "slotKey": _SLOT_KEY,
                    "slotIndex": _SLOT_INDEX,
                    "slotName": _SLOT_NAME,
                }
            ],
        },
        "stats": {
            "ocr_latency_ms": 0,
            "llm_latency_ms": 0,
            "total_latency_ms": elapsed_ms,
        },
        "errors": [],
    }


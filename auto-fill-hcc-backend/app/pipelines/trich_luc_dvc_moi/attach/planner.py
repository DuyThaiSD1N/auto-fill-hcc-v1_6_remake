"""Đính kèm cấp bản sao trích lục (Cổng DVC quốc gia mới).

Bảng thành phần hồ sơ chỉ có MỘT dòng ("Văn bản ủy quyền ...") và một input file dùng chung, không
`multiple`: extension bấm nút "Tải lên file" của dòng rồi nạp từng tệp. Chỉ có một đích nên không cần
OCR/LLM phân loại; mọi tệp đều vào dòng này để không sót tệp.
"""

import os

from app.process.schemas import FileItem

ROW_NAME = "Văn bản ủy quyền theo quy định của pháp luật"


def build_plan_items(file_names: list[str]) -> list[dict]:
    return [
        {
            "fileIndex": index,
            "fileName": name,
            "documentName": os.path.splitext(name)[0] or name,
            "componentName": ROW_NAME,
            "target": "fixed-slot",
            "needsAddComponent": False,
            "slotKey": "uy_quyen",
            "slotIndex": 0,
            "slotName": ROW_NAME,
            "noChooserClick": True,
        }
        for index, name in enumerate(file_names)
    ]


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    names = [f.name for f in files]
    attachments = build_plan_items(names)
    return {
        "attachments": attachments,
        "extracted": {"documents": names},
        "stats": {"ocr_latency_ms": 0, "llm_latency_ms": 0, "total_latency_ms": 0},
        "errors": [],
    }

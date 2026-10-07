"""Đính kèm cấp bản sao trích lục (Cổng DVC quốc gia mới).

Bảng thành phần hồ sơ chỉ có MỘT dòng ("Văn bản ủy quyền ...") và một input file dùng chung, không
`multiple`: extension bấm nút "Tải lên file" của dòng rồi nạp từng tệp. Chỉ có một đích nên không cần
OCR/LLM phân loại; mọi tệp đều vào dòng này để không sót tệp.

Cổng chỉ nhận tệp dưới 2 MB: tệp trên 2 MB được nén bằng đúng thang của cải chính (cùng Cổng DVC quốc gia mới), trả
về ở `replaceFiles` để extension đính bản nén thay bản gốc. Tệp nhỏ hơn để nguyên.
"""

import os

from app.pipelines.cai_chinh_dvc_moi.attach.planner import shrink_oversized
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
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    errors: list[str] = []
    replace_files = await shrink_oversized(raw_files, errors)
    names = [replace_files[str(i)]["name"] if str(i) in replace_files else f["name"] for i, f in enumerate(raw_files)]
    attachments = build_plan_items(names)
    return {
        "attachments": attachments,
        "replaceFiles": replace_files or None,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "shrunk": [
                {"fileName": r["name"], "originalBytes": r["originalBytes"], "bytes": r["bytes"], "level": r["level"]}
                for r in replace_files.values()
            ],
        },
        "stats": {"ocr_latency_ms": 0, "llm_latency_ms": 0, "total_latency_ms": 0},
        "errors": errors,
    }

"""Đính kèm bước "Thành phần hồ sơ" cho "Thông báo sửa đổi, bổ sung nội dung chương trình khuyến mại"
(cổng Bộ Công Thương — bảng Angular, engine FE `attp-row`).

Cổng chỉ có MỘT dòng thành phần: Thông báo theo Mẫu 06 (Bản chính). Mọi tệp tải lên — kể cả CCCD của
người nộp — đều đính vào dòng đó, nên không cần OCR/LLM phân loại: định tuyến tất định, không tệp nào rơi.
Engine attp-row đặt tên tệp theo `documentName` → giữ nguyên TÊN TỆP GỐC.
"""

from app.process.schemas import FileItem

_ROW = {
    # Đoạn nguyên văn đặc trưng của dòng (FE khớp substring đã fold dấu vào cột tên giấy tờ).
    "componentName": "Thông báo sửa đổi, bổ sung nội dung chương trình",
    "loaiBan": "Bản chính",
}


def build_plan_items(files: list[dict]) -> list[dict]:
    items: list[dict] = []
    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        items.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": file_name,
            "componentName": _ROW["componentName"],
            "loaiBan": _ROW["loaiBan"],
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": "thong_bao_sua_doi_ctkm",
        })
    return items


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options, session
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    attachments = build_plan_items(raw_files)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "classified": [
                {"fileName": item["fileName"], "docType": item["detectedType"], "source": "single-row"}
                for item in attachments
            ],
        },
        "stats": {"ocr_latency_ms": 0, "llm_latency_ms": 0, "total_latency_ms": 0},
        "errors": [],
    }

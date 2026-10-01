"""Đính kèm bước "Thành phần hồ sơ" cho "Đăng ký đất đai lần đầu đối với trường hợp được Nhà nước giao đất để quản
lý" (1.012756, cổng DVC Đà Nẵng — Angular mat-table, engine FE `attp-row`).

Bảng 2 dòng (thứ tự trên cổng, cả hai "Bản chính"):
  [1] Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu 15)
  [2] Báo cáo kết quả rà soát hiện trạng sử dụng đất (Mẫu 15đ)

KHÔNG TÁCH FILE: hồ sơ hay là MỘT PDF gộp vài chục trang (Đơn, Báo cáo rà soát, quyết định, hợp đồng thuê đất, GCN
đăng ký doanh nghiệp …) → đính NGUYÊN file vào dòng 1, không cắt trang, không cần OCR/LLM. Nhiều file tải lên thì
mọi file đều vào dòng 1 (ô "Chọn tệp tin" nhận nhiều tệp). Engine attp-row đặt tên tệp theo `documentName` → giữ
nguyên TÊN TỆP GỐC.
"""

from app.process.schemas import FileItem

_ROW = {
    # Đoạn nguyên văn đặc trưng của dòng 1 (FE khớp substring đã fold dấu vào cột tên giấy tờ).
    "componentName": "Đơn đăng ký đất đai, tài sản gắn liền với đất",
    "componentIndex": 1,
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
            "componentIndex": _ROW["componentIndex"],
            "loaiBan": _ROW["loaiBan"],
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": "don_mau_15",
        })
    return items


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    attachments = build_plan_items(raw_files)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "sessionId": (session or {}).get("request_id"),
            "classified": [
                {"fileName": item["fileName"], "componentIndex": item["componentIndex"], "source": "whole-file"}
                for item in attachments
            ],
        },
        "stats": {"ocr_latency_ms": 0, "llm_latency_ms": 0, "total_latency_ms": 0},
        "errors": [],
    }

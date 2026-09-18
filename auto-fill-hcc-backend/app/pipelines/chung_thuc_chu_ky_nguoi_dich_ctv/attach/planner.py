"""Đính kèm cho "Chứng thực chữ ký người dịch mà người dịch là cộng tác viên dịch thuật của
Ủy ban nhân dân cấp xã, tổ chức hành nghề công chứng" (mã 2.000992).

KHÔNG gọi OCR/LLM: thủ tục chỉ có MỘT loại giấy tờ ("Bản dịch và giấy tờ, văn bản cần dịch")
nên không có gì để phân loại. Giữ planner thuần tất định để bước đính ở quầy không tốn thêm
lượt OCR/LLM nào — khác chứng thực bản sao/chữ ký, hai thủ tục đó buộc phải đoán từng giấy là
loại gì mới biết xếp vào dòng nào.

Kênh popup (auto-fill) KHÔNG đi qua đây: nó tự đính cục bộ theo `clientAttachmentCase` khai
trong registry và chỉ gửi metadata lên backend. Planner này phục vụ kênh Handfree, nơi tệp vốn
đã nằm sẵn trên backend (upload_session) nên lập kế hoạch ở backend là đường tự nhiên.
"""
from app.pipelines._shared import normalize_document_name
from app.process.schemas import FileItem

# Khớp NGUYÊN VĂN `clientAttachmentCase.componentName` trong registry: FE tìm dòng cố định
# bằng cách so substring đã fold dấu, lệch một chữ là không thấy hàng.
COMPONENT_NAME = "Bản dịch và giấy tờ, văn bản cần dịch."
COMPONENT_INDEX = 1

# Bỏ dấu chấm cuối khi đánh số cho dòng thêm: "… cần dịch 2" đọc xuôi hơn "… cần dịch. 2".
_COMPONENT_BASE = COMPONENT_NAME.rstrip(".")


def _component_name_for(order: int) -> str:
    """Dòng đầu giữ tên gốc; dòng thêm được đánh số ngay từ backend.

    Cổng cho sửa tên thành phần nhưng input là React có debounce — đặt tên trùng rồi sửa lại ở
    frontend từng bị cổng ghi đè. Phát tên đã khác nhau sẵn thì không bao giờ phải sửa.
    """
    return COMPONENT_NAME if order == 0 else f"{_COMPONENT_BASE} {order + 1}"


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    """Entry point đính kèm cho chung-thuc-chu-ky-nguoi-dich-ctv."""
    _ = session
    options = options or {}
    # Tách nhiều hồ sơ: frontend cắt plan thành MỖI TỆP MỘT HỒ SƠ riêng (mỗi hồ sơ một tab), nên
    # tệp nào cũng rơi vào dòng cố định STT1 của hồ sơ đó — không có dòng nào cần thêm.
    # Gộp: tệp đầu vào STT1, các tệp sau thêm thành phần hồ sơ mới trong cùng một hồ sơ.
    split_mode = options.get("splitMode") is True

    attachments: list[dict] = []
    for index, file in enumerate(files):
        file_name = str(getattr(file, "name", "") or f"file-{index + 1}")
        to_fixed_row = split_mode or index == 0
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": normalize_document_name(file_name, "Bản dịch"),
            "componentName": COMPONENT_NAME if to_fixed_row else _component_name_for(index),
            "target": "existing" if to_fixed_row else "new",
            "componentIndex": COMPONENT_INDEX if to_fixed_row else None,
            "needsAddComponent": not to_fixed_row,
            "detectedType": _COMPONENT_BASE,
        })

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [str(getattr(f, "name", "") or "") for f in files],
            "multiDossierBundleEnabled": split_mode,
        },
        "errors": [],
    }

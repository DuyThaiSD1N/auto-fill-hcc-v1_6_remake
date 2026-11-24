"""Đính kèm 1.115462 Bắc Ninh — chế độ KHÔNG tách (cài đặt "Tách giấy tờ" tắt / client cũ).

Theo ảnh ánh xạ: mỗi tệp giữ NGUYÊN — tệp Đơn Mẫu 09 (kèm trang xác nhận UBND xã) → TP-H05.000053, tệp GCN (bìa +
trang chứng nhận) → TP-H05.000040, tệp Giấy ủy quyền + lời chứng chứng thực → "File đính kèm khác". Hồ sơ scan CHUNG
một tệp thì đính nguyên tệp vào MỌI dòng có giấy tương ứng (khuôn 1.115460); CCCD / ủy quyền / khác → "File đính kèm
khác" một lần mỗi tệp. Tệp nào cũng sinh ít nhất một mục, không rớt tệp.
"""

from app.pipelines.dang_ky_bien_dong_doi_ten_nguoi_su_dung_dat_bac_ninh.attach.dinh_kem_khong_tach.planner import (
    extracted,
    unique_name,
)
from app.process.schemas import FileItem

from .. import catalog
from ..phan_trang import read_documents

__all__ = ["build_item", "extracted", "plan", "unique_name", "whole_file_items"]


def build_item(file_index: int, file_name: str, document_name: str, label: str,
               sources: list[dict] | None = None) -> dict:
    target, component_name, slot_key = catalog.resolve(label)
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


def whole_file_items(raw_files: list[dict], documents: list[dict]) -> list[dict]:
    """Giấy đã chia → mục đính NGUYÊN tệp: mỗi dòng thành phần có giấy trong tệp nhận cả tệp một lần."""
    attachments: list[dict] = []
    used: set[str] = set()
    for file_index, file in enumerate(raw_files):
        name = str(file.get("name") or f"file-{file_index + 1}")
        docs = [d for d in documents if d["fileIndex"] == file_index] or [{"label": "khac", "name": ""}]
        supplementary_done = False
        for label in dict.fromkeys(d["label"] for d in docs):
            # Giấy ủy quyền / CCCD / khác cùng tệp → "File đính kèm khác" MỘT lần mỗi tệp (bắt buộc khi nộp thay).
            if catalog.is_supplementary(label):
                if supplementary_done:
                    continue
                supplementary_done = True
            fallback = catalog.display_name(label)
            attachments.append(build_item(file_index, name, unique_name(fallback, used, fallback), label))
    return attachments


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    _, documents, errors, stats = await read_documents(raw_files)
    return {
        "attachments": whole_file_items(raw_files, documents),
        "extracted": extracted(raw_files, documents, session, "whole_files"),
        "stats": stats,
        "errors": errors,
    }

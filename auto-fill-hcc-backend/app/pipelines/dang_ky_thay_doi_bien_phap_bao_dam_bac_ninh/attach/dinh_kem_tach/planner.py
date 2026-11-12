"""Đính kèm 1.011442 Bắc Ninh — chế độ TÁCH giấy tờ (cài đặt "Tách giấy tờ" bật, ``splitDocuments is True``).

Cùng lượt LLM chia trang với chế độ không tách (``phan_trang.read_documents``); mỗi giấy thành MỘT mục có
``sourceSegments`` (extension cắt đúng trang trước khi tải lên) đặt vào đúng dòng của bảng ``catalog``. Bản thứ nhất
của Phiếu 02a → Bản chính, bản thứ hai → Bản sao. Tệp chỉ một giấy → đính nguyên tệp.
LLM chia lỗi / số trang OCR lệch PDF → quay về đính nguyên tệp như chế độ không tách (không sót trang nào).
"""

import base64

from app.process.schemas import FileItem

from .. import catalog
from ..dinh_kem_khong_tach.planner import build_item, extracted, unique_name, whole_file_items
from ..phan_trang import read_documents


def _pdf_page_count(file: dict) -> int | None:
    header, sep, payload = str(file.get("dataUrl") or "").partition(",")
    if not sep or "pdf" not in header.lower():
        return None
    try:
        import fitz  # pymupdf

        with fitz.open(stream=base64.b64decode(payload), filetype="pdf") as doc:
            return doc.page_count
    except Exception:  # noqa: BLE001
        return None


def split_items(raw_files: list[dict], pages_by_file: dict[int, list[str]], documents: list[dict]) -> list[dict]:
    attachments: list[dict] = []
    used: set[str] = set()
    copies: dict[str, int] = {}
    for file_index, file in enumerate(raw_files):
        name = str(file.get("name") or f"file-{file_index + 1}")
        docs = [d for d in documents if d["fileIndex"] == file_index]
        cuttable = (len(docs) > 1 and all(d["pages"] is not None for d in docs)
                    and _pdf_page_count(file) == len(pages_by_file.get(file_index) or []))
        if not cuttable and len(docs) > 1:
            # Không cắt được (ảnh, số trang OCR lệch PDF) → tệp này đính nguyên như chế độ không tách.
            for item in whole_file_items([file], [{**d, "fileIndex": 0} for d in docs]):
                attachments.append({**item, "fileIndex": file_index})
            continue
        for doc in docs or [{"label": "khac", "name": "", "pages": None}]:
            label = doc["label"]
            copy_index = copies.get(label, 0)
            copies[label] = copy_index + 1
            fallback = catalog.display_name(label)
            document_name = unique_name(doc.get("name") or fallback, used, fallback)
            sources = [{"fileIndex": file_index, "pageIndexes": doc["pages"]}] if cuttable else None
            attachments.append(build_item(file_index, name, document_name, label, copy_index, sources))
    return attachments


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    pages_by_file, documents, errors, stats = await read_documents(raw_files)
    if any(d.get("source") == "keyword" for d in documents):
        # LLM chia lỗi → không tin ranh giới đoán bằng từ khoá để cắt trang: đính nguyên tệp.
        return {
            "attachments": whole_file_items(raw_files, documents),
            "extracted": extracted(raw_files, documents, session, "whole_files"),
            "stats": stats,
            "errors": [*errors, "Tách giấy tờ lỗi — đính nguyên tệp."],
        }
    return {
        "attachments": split_items(raw_files, pages_by_file, documents),
        "extracted": extracted(raw_files, documents, session, "split_documents"),
        "stats": stats,
        "errors": errors,
    }

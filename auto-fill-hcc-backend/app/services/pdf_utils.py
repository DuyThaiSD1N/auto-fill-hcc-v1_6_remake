"""Tiện ích PDF cho bước ĐÍNH KÈM: cắt PDF về vài trang đầu để OCR phân loại NHANH.

Chỉ dùng cho path attach/classify — loại giấy tờ + tên người luôn nằm ở trang 1-2 nên
không cần OCR toàn bộ PDF nhiều trang. Path điền form vẫn OCR đầy đủ (không gọi vào đây).
"""
import base64

import fitz  # pymupdf


def first_pages_data_url(data_url: str, max_pages: int) -> str:
    """Cắt PDF trong data URL về tối đa `max_pages` trang đầu. Không phải PDF / lỗi → trả nguyên bản."""
    try:
        header, sep, b64 = data_url.partition(",")
        if not sep or "pdf" not in header.lower():
            return data_url  # ảnh (jpg/png) hoặc data URL lạ → giữ nguyên
        raw = base64.b64decode(b64)
        doc = fitz.open(stream=raw, filetype="pdf")
        try:
            if doc.page_count <= max_pages:
                return data_url
            out = fitz.open()
            try:
                out.insert_pdf(doc, from_page=0, to_page=max_pages - 1)
                trimmed = out.tobytes()
            finally:
                out.close()
        finally:
            doc.close()
        return f"{header},{base64.b64encode(trimmed).decode('ascii')}"
    except Exception:  # noqa: BLE001 — cắt lỗi thì OCR nguyên bản, không được làm hỏng luồng
        return data_url


def trim_files_for_classify(files: list[dict], max_pages: int) -> list[dict]:
    """Trả bản sao danh sách file với PDF đã cắt còn `max_pages` trang đầu (giữ nguyên name/type)."""
    if not max_pages or max_pages <= 0:
        return files
    out: list[dict] = []
    for f in files:
        du = f.get("dataUrl") or ""
        out.append({**f, "dataUrl": first_pages_data_url(du, max_pages)} if du else f)
    return out

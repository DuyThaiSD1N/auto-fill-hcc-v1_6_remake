"""Chụp dữ liệu rà soát tại thời điểm process (Kiểu A): mọi giấy tờ → ẢNH TỪNG TRANG →
OCR có token → khớp value→bbox → trả sources + ảnh để lưu.

Mọi thứ được quy về ẢNH trước khi OCR (bake EXIF ảnh thường, render PDF ra ảnh bằng pymupdf)
vì Vision chỉ trả bbox theo pixel cho ẢNH; gửi thẳng PDF thì tokens rỗng. Ảnh phục vụ FE = đúng
ảnh đã OCR nên khung luôn khớp. Đặt RIÊNG (không nhét vào shared runner) → thủ tục khác không ảnh hưởng.
"""
import base64
import io

import fitz  # pymupdf
from PIL import Image, ImageOps

from app.review import service as review_service
from app.services import ocr

_IMG_EXTS = (".jpg", ".jpeg", ".png")
_PDF_DPI = 200          # render PDF: đủ nét cho OCR, không quá to
_MAX_PAGES = 10         # trần số ảnh gửi OCR để màn rà soát không quá nặng


def _decode(data_url: str) -> bytes:
    b64 = data_url.split(",", 1)[1] if "," in data_url else data_url
    return base64.b64decode(b64)


def _bake_exif(data_url: str) -> bytes:
    """Nướng hướng EXIF vào pixel + xuất JPEG q92. Lỗi decode → trả bytes gốc."""
    raw = _decode(data_url)
    try:
        im = Image.open(io.BytesIO(raw))
        im = ImageOps.exif_transpose(im)
        if im.mode != "RGB":
            im = im.convert("RGB")
        out = io.BytesIO()
        im.save(out, format="JPEG", quality=92)
        return out.getvalue()
    except Exception:  # noqa: BLE001
        return raw


def _pdf_pages_to_jpeg(data_url: str) -> list[bytes]:
    """Render từng trang PDF ra JPEG (để OCR có bbox pixel). Lỗi → []."""
    try:
        doc = fitz.open(stream=_decode(data_url), filetype="pdf")
    except Exception:  # noqa: BLE001
        return []
    out: list[bytes] = []
    try:
        for page in doc:
            pix = page.get_pixmap(dpi=_PDF_DPI)
            out.append(pix.tobytes("jpeg"))
            if len(out) >= _MAX_PAGES:
                break
    finally:
        doc.close()
    return out


def _collect_page_images(files_by_role: dict[str, list[dict]]) -> list[dict]:
    """Quy mọi giấy tờ về [{name, bytes(JPEG)}] — mỗi trang PDF là 1 ảnh riêng."""
    pages: list[dict] = []
    for arr in files_by_role.values():
        for f in arr or []:
            typ = (f.get("type") or "").lower()
            name = (f.get("name") or "").lower()
            data_url = f.get("dataUrl") or ""
            if name.endswith(".pdf") or typ == "application/pdf":
                jpegs = _pdf_pages_to_jpeg(data_url)
                for i, b in enumerate(jpegs):
                    label = f.get("name") or "tài liệu.pdf"
                    pages.append({"name": f"{label} (trang {i + 1})" if len(jpegs) > 1 else label, "bytes": b})
            elif typ.startswith("image/") or name.endswith(_IMG_EXTS):
                pages.append({"name": f.get("name"), "bytes": _bake_exif(data_url)})
            # docx: bỏ qua (không có ảnh gốc để khoanh)
            if len(pages) >= _MAX_PAGES:
                return pages
    return pages


async def capture(
    files_by_role: dict[str, list[dict]],
    fields: list[dict],
    review_names: dict[str, str] | None = None,
    name_groups: list[dict] | None = None,
) -> dict | None:
    """Trả {"sources": {...}, "images": [{index, bytes}]} hoặc None nếu không có ảnh.

    review_names: {field_name: nhãn} — whitelist field đáng rà + nhãn hiển thị. None → rà tất cả.
    name_groups: gộp các ô Họ/Chữ đệm/Tên thành 1 mục (xem service.build_sources).
    """
    pages = _collect_page_images(files_by_role)
    if not pages:
        return None

    ocr_files = [
        {"name": pages[i]["name"], "type": "image/jpeg",
         "dataUrl": "data:image/jpeg;base64," + base64.b64encode(pages[i]["bytes"]).decode("ascii")}
        for i in range(len(pages))
    ]
    ocr_res = await ocr.ocr_tokens_per_file(ocr_files)
    tokens_by_file = [
        {"file_index": i, "name": pages[i]["name"], "tokens": ocr_res[i].get("tokens") or []}
        for i in range(len(pages))
    ]

    include = set(review_names) if review_names else None
    sources = review_service.build_sources(
        fields, tokens_by_file, labels=review_names, include=include, name_groups=name_groups
    )
    images = [{"index": i, "bytes": pages[i]["bytes"]} for i in range(len(pages))]
    return {"sources": sources, "images": images}

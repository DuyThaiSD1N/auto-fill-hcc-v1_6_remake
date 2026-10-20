# -*- coding: utf-8 -*-
"""Đọc tệp đầu vào thành danh sách trang ảnh (PIL, RGB).

Nhận PDF (scan hoặc PDF chữ), ảnh JPG/PNG/WEBP/BMP/TIFF/GIF, hoặc ZIP chứa các tệp đó. Nhận diện theo nội dung tệp,
không tin đuôi tệp. Ảnh chụp điện thoại được xoay theo EXIF. PDF scan giữ đúng độ phân giải ảnh gốc bên trong
(PDF chữ render 300 dpi). Cạnh dài tối đa 6000 px.

Trích nguyên văn từ ocr_engine.py của web Bàn đọc giấy tờ.
"""
from __future__ import annotations

import io
import zipfile

from PIL import Image, ImageOps, ImageSequence

import pypdfium2 as pdfium

Image.MAX_IMAGE_PIXELS = 250_000_000


MAX_STORE_EDGE = 6000                # cạnh dài tối đa khi lưu trang trên máy


IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif")


# ---------------------------------------------------------------- đọc tệp đầu vào
def _normalize(img: Image.Image) -> Image.Image:
    """Xoay theo EXIF (ảnh chụp điện thoại), chuyển về RGB, giới hạn kích thước."""
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    if img.mode in ("I;16", "I;16B", "I;16L", "I"):
        img = img.convert("I").point(lambda v: v * (1 / 256)).convert("L")
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[-1])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    if max(img.size) > MAX_STORE_EDGE:
        img.thumbnail((MAX_STORE_EDGE, MAX_STORE_EDGE), Image.LANCZOS)
    return img


def _pdf_native_scale(page) -> float | None:
    """Tỉ lệ render sao cho ảnh scan bên trong PDF giữ nguyên độ phân giải gốc."""
    pw, ph = page.get_size()
    page_area = max(pw * ph, 1)
    best = None
    try:
        for obj in page.get_objects():
            if obj.type != pdfium.raw.FPDF_PAGEOBJ_IMAGE:
                continue
            l, b, r, t = obj.get_bounds()
            bw, bh = abs(r - l), abs(t - b)
            if bw * bh < 0.2 * page_area or bw < 1 or bh < 1:
                continue
            px_w, px_h = obj.get_px_size()
            s = max(px_w / bw, px_h / bh)
            best = s if best is None else max(best, s)
    except Exception:
        return None
    return best


def render_pdf(data: bytes) -> list[Image.Image]:
    pages = []
    pdf = pdfium.PdfDocument(data)
    try:
        for page in pdf:
            pw, ph = page.get_size()
            scale = _pdf_native_scale(page) or (300 / 72)   # PDF chữ: 300 dpi
            scale = min(max(scale, 2.0), 5.0)
            scale = min(scale, MAX_STORE_EDGE / max(pw, ph, 1))
            bitmap = page.render(scale=scale, draw_annots=True)
            pages.append(_normalize(bitmap.to_pil()))
            page.close()
    finally:
        pdf.close()
    return pages


def images_from_bytes(data: bytes) -> list[Image.Image]:
    img = Image.open(io.BytesIO(data))
    frames = []
    for frame in ImageSequence.Iterator(img):
        frames.append(_normalize(frame.copy()))
        if img.format not in ("TIFF", "MPO"):
            break  # GIF/WebP động: chỉ lấy khung đầu
    return frames


def _natural_key(name: str):
    import re
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


def images_from_zip(data: bytes) -> list[Image.Image]:
    pages = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = [n for n in zf.namelist() if not n.endswith("/") and "__MACOSX" not in n]
        for name in sorted(names, key=_natural_key):
            low = name.lower()
            if low.endswith(".pdf") or low.endswith(IMAGE_EXTS):
                pages.extend(load_document(zf.read(name), name))
    return pages


def load_document(data: bytes, filename: str = "") -> list[Image.Image]:
    """Nhận diện theo nội dung tệp (không tin đuôi tệp) rồi tách thành các trang ảnh."""
    head = data[:1024]
    if b"%PDF" in head:
        return render_pdf(data)
    if data[:2] == b"PK":
        pages = images_from_zip(data)
        if not pages:
            raise ValueError("Tệp nén không chứa ảnh hoặc PDF nào.")
        return pages
    try:
        return images_from_bytes(data)
    except Exception as exc:
        raise ValueError(
            "Không đọc được tệp. Hỗ trợ PDF, JPG, PNG, WEBP, BMP, TIFF, GIF và ZIP chứa các tệp đó."
        ) from exc


# ---------------------------------------------------------------- xử lý ảnh
def apply_rotation(img: Image.Image, rot: int) -> Image.Image:
    rot = rot % 360
    return img.rotate(-rot, expand=True) if rot else img

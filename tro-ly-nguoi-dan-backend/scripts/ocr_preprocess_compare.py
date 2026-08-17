"""So sánh OCR Vintern: TH1 (qua tiền xử lý xoay/chuẩn hóa) vs TH2 (gửi ảnh thô).

Chạy:  .venv/bin/python scripts/ocr_preprocess_compare.py "mau/ex/dki lại/file2"
(mặc định đọc thư mục trên). Cùng endpoint/prompt/params; chỉ khác khâu tiền xử lý ảnh.
Cần tesseract trong PATH để TH1 xoay được (export PATH=/opt/homebrew/bin:$PATH trên macOS).
"""
import asyncio
import base64
import os
import sys

import fitz  # PyMuPDF
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings  # noqa: E402
from app.services import ocr_vintern as ov  # noqa: E402

DEFAULT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "mau", "ex", "dki lại", "file2")


def _raw_page_images(data_url: str) -> list[str]:
    """TH2: KHÔNG tiền xử lý — PDF render thô (không PIL/OSD), ảnh gửi thẳng data_url gốc."""
    raw, mime = ov._decode_data_url(data_url)
    is_pdf = mime == "application/pdf" or raw[:5] == b"%PDF-"
    if is_pdf:
        urls = []
        with fitz.open(stream=raw, filetype="pdf") as doc:
            for page in doc:
                png = page.get_pixmap(dpi=settings.ocr_pdf_dpi).tobytes("png")
                urls.append("data:image/png;base64," + base64.b64encode(png).decode())
        return urls
    return [data_url]


async def _ocr_set(client, sem, images):
    pages = await asyncio.gather(*(ov._ocr_image(client, sem, u) for u in images))
    return "\n".join(t.strip() for t in pages if t and t.strip()).strip()


async def run(folder: str):
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith((".pdf", ".jpg", ".jpeg", ".png")))
    print(f"Thư mục: {folder}\nSố file: {len(files)} | endpoint: {settings.ocr_vintern_base_url}")
    print(f"PIL_OK={ov._PIL_OK} TESS_OK={ov._TESS_OK}\n" + "=" * 80)

    timeout = httpx.Timeout(settings.ocr_timeout_ms / 1000)
    sem = asyncio.Semaphore(settings.ocr_concurrency)
    async with httpx.AsyncClient(timeout=timeout) as client:
        for name in files:
            raw = open(os.path.join(folder, name), "rb").read()
            mime = "application/pdf" if name.lower().endswith(".pdf") else "image/jpeg"
            data_url = f"data:{mime};base64," + base64.b64encode(raw).decode()

            pre = ov._page_images(data_url)      # TH1 (tiền xử lý)
            rawimgs = _raw_page_images(data_url)  # TH2 (thô)
            t1 = await _ocr_set(client, sem, pre)
            t2 = await _ocr_set(client, sem, rawimgs)

            print(f"\n### FILE: {name}  (pages: {len(pre)})")
            print(f"  TH1 (tiền xử lý): {len(t1)} ký tự")
            print(f"  TH2 (thô)      : {len(t2)} ký tự")
            print("\n----- TH1 (tiền xử lý) -----\n" + t1)
            print("\n----- TH2 (thô) -----\n" + t2)
            print("=" * 80)


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DIR
    asyncio.run(run(folder))

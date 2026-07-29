"""Provider OCR Vintern-1B-v3.5 (OpenAI vision) — dùng cho giấy tờ CÓ BẢN VIẾT TAY.

Vintern nhận ẢNH chứ không nhận PDF, nên PDF được tách từng trang (PyMuPDF) -> PNG ->
OCR mỗi trang rồi ghép lại. Public API trùng ocr_raw để dispatcher gọi đồng nhất.
"""
import asyncio
import base64
import binascii
import io
import logging

import fitz  # PyMuPDF
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Pillow: chỉ dùng để xoay ảnh theo EXIF (ảnh chụp điện thoại) + chuẩn hóa RGB/PNG, GIỐNG HỆT web
# tham chiếu (ocr-compare). Thiếu Pillow → gửi thẳng data URL gốc.
#
# KHÔNG dùng Tesseract OSD (xoay theo nội dung) nữa: trang PDF do PyMuPDF render vốn ĐÃ đúng chiều,
# OSD chỉ đoán SAI trên form tiếng Việt → xoay nhầm → Vintern đọc ra rác + chậm ~10× (0°=2.6s đúng;
# 90/180°=26s rác). Web không hề chạy OSD nên luôn đúng — đây là toàn bộ khác biệt. Đã bỏ hẳn OSD.
try:
    from PIL import Image, ImageOps
    _PIL_OK = True
except Exception:  # noqa: BLE001
    _PIL_OK = False

# Prompt OCR thuần ưu tiên ĐỦ THÔNG TIN (V6 — đã đo trên form in/viết tay/bảng nhiều trang):
# quét tuần tự 1 lượt, không bỏ sót mục/dòng, chốt CHỐNG LẶP. Xem [[ocr-vintern-prompt-v6-completeness]].
# Lưu ý: KHÔNG thêm vế "scan đầy đủ/dịch ra toàn bộ" — làm model tóm tắt & bỏ khối (đã test, tệ).
# _OCR_PROMPT = """
# Bạn là máy OCR. Chép lại y nguyên chữ trong ảnh, không bình luận, không đánh giá bất kỳ chi tiết nào, việc của bạn chỉ có quét thật kỹ càng và đưa ra toàn bộ chữ có trong ảnh.
# Vui lòng không làm các công việc khác ngoài mệnh lệnh trên.
# """

# _OCR_PROMPT = (
#     "Bạn là máy OCR. Chép lại y nguyên chữ trong ảnh, không bình luận, không đánh giá bất kỳ chi tiết nào."
#     "Việc của bạn chỉ có quét thật kỹ càng và đưa ra toàn bộ chữ có trong ảnh. "
#     "Vui lòng không làm các công việc khác ngoài mệnh lệnh trên."
# )
# _OCR_PROMPT = "Đọc kỹ và ghi lại TẤT CẢ chữ VIẾT TAY và TẤT CẢ CHỮ IN điền trong các ô, kể cả chữ có xấu và bị che khuất."

_OCR_PROMPT = (
    "Bạn là máy OCR chuyên nhận dạng văn bản tiếng Việt.\n"
    "Chép lại toàn bộ chữ trong ảnh y nguyên, bao gồm đầy đủ dấu thanh và dấu phụ tiếng Việt.\n"
    "Giữ nguyên bố cục, xuống dòng theo ảnh.\n"
    "Nếu chữ không đọc được thì viết [?].\n"
    "Tuyệt đối không thêm chữ, không bình luận, không giải thích.\n"
    "Nếu được hãy quét một cách rõ ràng và đưa ra tất cả các chữ trong tờ giấy"
)


def _decode_data_url(data_url: str) -> tuple[bytes, str]:
    """'data:<mime>;base64,<payload>' -> (bytes, mime). Chấp nhận cả base64 thuần."""
    payload = data_url or ""
    mime = "application/octet-stream"
    if payload.startswith("data:"):
        header, _, payload = payload.partition(",")
        mime = header[len("data:"):].split(";", 1)[0] or mime
    try:
        raw = base64.b64decode(payload, validate=False)
    except (binascii.Error, ValueError):
        raw = b""
    return raw, mime


def _pil_to_png_dataurl(im: "Image.Image") -> str:
    """PIL image -> data URL PNG (chuẩn hóa mode về RGB/L cho model đọc ổn định)."""
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _png_dataurl(png: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png).decode()


def _page_images(data_url: str) -> list[str]:
    """Trả danh sách data URL ảnh (mỗi trang 1 ảnh), GIỐNG HỆT web tham chiếu (ocr-compare):

    - PDF: render từng trang qua PyMuPDF với Matrix(dpi/72) rồi gửi PNG THẲNG (đã đúng chiều,
      KHÔNG xoay OSD, KHÔNG re-encode) — byte-for-byte như web.
    - Ảnh: chỉ xoay theo EXIF (ảnh chụp điện thoại) rồi chuẩn hóa RGB/PNG; ảnh không có EXIF thì
      gửi thẳng data URL gốc. KHÔNG xoay theo nội dung (OSD).
    - Thiếu Pillow → gửi thẳng data URL / PNG render thô.
    """
    if not data_url:
        return []
    raw, mime = _decode_data_url(data_url)
    is_pdf = mime == "application/pdf" or raw[:5] == b"%PDF-"
    if is_pdf:
        if not raw:
            return []
        # Matrix(dpi/72) thay vì get_pixmap(dpi=...) để khớp TỪNG BYTE với web tham chiếu.
        mat = fitz.Matrix(settings.ocr_pdf_dpi / 72.0, settings.ocr_pdf_dpi / 72.0)
        urls: list[str] = []
        with fitz.open(stream=raw, filetype="pdf") as doc:
            for page in doc:
                png = page.get_pixmap(matrix=mat, alpha=False).tobytes("png")
                urls.append(_png_dataurl(png))
        return urls

    # Ảnh đơn: LUÔN xoay theo EXIF + chuẩn hóa RGB/PNG, GIỐNG HỆT web (ocr-compare) và
    # client_sample.py tham chiếu. Không dùng OSD.
    if _PIL_OK and raw:
        try:
            im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))
            return [_pil_to_png_dataurl(im)]
        except Exception as e:  # noqa: BLE001
            logger.debug("Chuẩn hóa ảnh lỗi, gửi data URL gốc: %s", e)
    return [data_url]


async def _ocr_image(client: httpx.AsyncClient, sem: asyncio.Semaphore, image_url: str) -> str:
    """OCR 1 ảnh qua Vintern, trả text."""
    async with sem:
        r = await client.post(
            settings.ocr_vintern_base_url.rstrip("/") + "/v1/chat/completions",
            json={
                "model": settings.ocr_model,
                "messages": [{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {"type": "text", "text": _OCR_PROMPT},
                ]}],
                "max_tokens": settings.ocr_max_tokens,
                "temperature": 0,
                "repetition_penalty": settings.ocr_repetition_penalty,
            },
        )
    if r.status_code >= 400:
        raise RuntimeError(f"OCR HTTP {r.status_code}: {r.text[:300]}")
    choices = r.json().get("choices") or []
    if not choices:
        return ""
    return (choices[0].get("message") or {}).get("content", "") or ""


async def _ocr_files(client: httpx.AsyncClient, sem: asyncio.Semaphore, files: list[dict]) -> str:
    """OCR danh sách file -> ghép fullText theo thứ tự trang/file."""
    texts: list[str] = []
    for f in files or []:
        image_urls = await asyncio.to_thread(_page_images, f.get("dataUrl") or f.get("url") or "")
        if not image_urls:
            continue
        pages = await asyncio.gather(*(_ocr_image(client, sem, u) for u in image_urls))
        texts.extend(t.strip() for t in pages if t and t.strip())
    return "\n".join(texts).strip()


async def ocr_per_file(files: list[dict]) -> list[dict]:
    """OCR từng file riêng (giữ thứ tự) → [{name, type, text, error?}]."""
    timeout = httpx.Timeout(settings.ocr_timeout_ms / 1000)
    sem = asyncio.Semaphore(settings.ocr_concurrency)
    out: list[dict] = [None] * len(files)  # type: ignore

    async with httpx.AsyncClient(timeout=timeout) as client:
        async def run(idx: int, f: dict) -> None:
            item = {"name": f.get("name"), "type": f.get("type"), "text": ""}
            try:
                item["text"] = await _ocr_files(client, sem, [f])
            except Exception as e:  # noqa: BLE001
                item["error"] = str(e)
            out[idx] = item

        await asyncio.gather(*(run(i, f) for i, f in enumerate(files)))

    return out


async def ocr_by_role(files_by_role: dict[str, list[dict]]) -> dict[str, str]:
    """files_by_role: { role: [...] } -> { role: fullText, role_error?: "..." }."""
    out: dict[str, str] = {}
    timeout = httpx.Timeout(settings.ocr_timeout_ms / 1000)
    sem = asyncio.Semaphore(settings.ocr_concurrency)

    async with httpx.AsyncClient(timeout=timeout) as client:
        async def run(role: str, files: list[dict]) -> None:
            if not files:
                return
            try:
                out[role] = await _ocr_files(client, sem, files)
            except Exception as e:  # noqa: BLE001
                out[role] = ""
                out[role + "_error"] = str(e)

        await asyncio.gather(*(run(role, files) for role, files in files_by_role.items()))

    return out

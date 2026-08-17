"""Provider OCR Gemini (Google Generative Language API).

Thay cho raw/vintern khi bật cờ RAW_BY_GEMINI / VINTERN_BY_GEMINI (xem app/services/ocr.py).
Đọc GEMINI_API_KEY + GEMINI_MODEL từ env (app.config.settings).

Luồng: PDF/ảnh -> render/tiền xử lý (Matrix dpi/72, KHÔNG OSD, cạnh dài <= gemini_max_edge, xuất
JPEG cho nhẹ) -> gọi generateContent SONG SONG từng trang (tắt thinking) -> ghép text.
Public API trùng ocr_raw/ocr_vintern để dispatcher gọi đồng nhất: ocr_per_file / ocr_by_role.
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

# Pillow: xoay ảnh theo EXIF + chuẩn hóa/thu nhỏ + xuất JPEG. Thiếu Pillow -> gửi thẳng bytes gốc.
try:
    from PIL import Image, ImageOps
    _PIL_OK = True
except Exception:  # noqa: BLE001
    _PIL_OK = False

_MAX_PAGES = 30
_IMAGE_MIME = "image/jpeg"

# System prompt OCR: chép y nguyên, giữ dấu tiếng Việt; CẤM chép lại dòng chấm/gạch điền tay
# (nếu không model lặp "……" hàng nghìn ký tự -> phình output + chậm gấp nhiều lần).
_SYSTEM_PROMPT = (
    "Bạn là máy OCR chuyên nhận dạng văn bản tiếng Việt.\n"
    "Chép lại toàn bộ chữ trong ảnh y nguyên, bao gồm đầy đủ dấu thanh và dấu phụ tiếng Việt.\n"
    "Giữ nguyên bố cục, xuống dòng theo ảnh.\n"
    "Nếu chữ không đọc được thì viết [?].\n"
    "Với các dòng chấm/gạch để trống điền tay (ví dụ '……' hoặc '____'), TUYỆT ĐỐI KHÔNG chép lại "
    "chuỗi dấu chấm/gạch đó; chỉ ghi nội dung đã điền (nếu có) rồi bỏ qua phần chấm.\n"
    "Tuyệt đối không thêm chữ, không bình luận, không giải thích."
)
_USER_HINT = "Trích xuất toàn bộ chữ trong ảnh sau."


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


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def _pdf_zoom(page) -> float:
    """Scale render: theo ocr_pdf_dpi nhưng KHÔNG để cạnh dài vượt gemini_max_edge."""
    zoom = settings.ocr_pdf_dpi / 72.0
    longest_pt = max(page.rect.width, page.rect.height) or 1
    return min(zoom, settings.gemini_max_edge / longest_pt)


def _page_images(data_url: str) -> list[str]:
    """Trả list base64 JPEG (mỗi trang 1 ảnh). PDF -> render từng trang; ảnh -> exif + thu nhỏ."""
    if not data_url:
        return []
    raw, mime = _decode_data_url(data_url)
    is_pdf = mime == "application/pdf" or raw[:5] == b"%PDF-"
    if is_pdf:
        if not raw:
            return []
        out: list[str] = []
        q = settings.gemini_jpeg_quality
        with fitz.open(stream=raw, filetype="pdf") as doc:
            for page in doc:
                if len(out) >= _MAX_PAGES:
                    break
                z = _pdf_zoom(page)
                jpg = page.get_pixmap(matrix=fitz.Matrix(z, z), alpha=False).tobytes("jpg", jpg_quality=q)
                out.append(_b64(jpg))
        return out

    # Ảnh đơn: xoay EXIF, thu nhỏ nếu cạnh dài > max_edge, xuất JPEG.
    if _PIL_OK and raw:
        try:
            im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            edge = settings.gemini_max_edge
            if max(im.size) > edge:
                scale = edge / max(im.size)
                im = im.resize((round(im.width * scale), round(im.height * scale)))
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=settings.gemini_jpeg_quality)
            return [_b64(buf.getvalue())]
        except Exception as e:  # noqa: BLE001
            logger.debug("Chuẩn hóa ảnh lỗi, gửi bytes gốc: %s", e)
    return [_b64(raw)] if raw else []


def _endpoint() -> str:
    return (settings.gemini_base_url.rstrip("/")
            + f"/v1beta/models/{settings.gemini_model}:generateContent")


async def _ocr_image(client: httpx.AsyncClient, sem: asyncio.Semaphore, img_b64: str) -> str:
    """OCR 1 ảnh (1 trang) qua Gemini generateContent."""
    if not settings.gemini_api_key:
        raise RuntimeError("Thiếu GEMINI_API_KEY")
    payload = {
        "systemInstruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [
            {"inline_data": {"mime_type": _IMAGE_MIME, "data": img_b64}},
            {"text": _USER_HINT},
        ]}],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 8192,
            "thinkingConfig": {"thinkingBudget": 0},   # tắt thinking cho nhanh
        },
    }
    async with sem:
        r = await client.post(_endpoint(), params={"key": settings.gemini_api_key}, json=payload)
    if r.status_code >= 400:
        raise RuntimeError(f"Gemini HTTP {r.status_code}: {r.text[:300]}")
    cands = r.json().get("candidates") or []
    if not cands:
        return ""
    parts = (cands[0].get("content") or {}).get("parts") or []
    return "\n".join(p.get("text", "") for p in parts).strip()


async def _ocr_files(client: httpx.AsyncClient, sem: asyncio.Semaphore, files: list[dict]) -> str:
    """OCR danh sách file -> ghép fullText theo thứ tự trang/file (các trang chạy song song)."""
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
    timeout = httpx.Timeout(settings.gemini_timeout_ms / 1000)
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
    timeout = httpx.Timeout(settings.gemini_timeout_ms / 1000)
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

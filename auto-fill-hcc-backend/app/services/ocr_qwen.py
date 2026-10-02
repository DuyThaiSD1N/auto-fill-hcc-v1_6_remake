"""OCR bằng Qwen đa phương thức (OCR_QWEN_BASE_URL / OCR_QWEN_MODEL, trống thì LLM_*; OpenAI-compatible).

CHƯA nối vào pipeline — facade OCR của hệ thống vẫn là ``app.services.ocr`` (Tiếng Nói). Module
này phục vụ so sánh chất lượng OCR (``scripts/ocr_compare.py``) trước khi quyết định dùng thật.

Contract giống ``ocr.ocr_per_file``: nhận ``[{name, type, dataUrl}]``, trả mỗi tệp
``{name, type, text, provider: "qwen", pages, ms, error?}`` theo đúng thứ tự đầu vào.
"""
from __future__ import annotations

import asyncio
import base64
import re
import time

import fitz  # PyMuPDF
import httpx

from app.config import settings

_DATA_URL_RE = re.compile(r"^data:([^;,]*)(;base64)?,(.*)$", re.DOTALL)
# Cạnh dài tối đa khi gửi ảnh: đủ nét cho chữ viết tay trên trang A4, không phình token ảnh.
_MAX_SIDE_PX = 2000
_MAX_ZOOM = 3.0
_JPEG_QUALITY = 85
_PAGE_CONCURRENCY = 4
# Trang bình thường ra tối đa ~1000 token (p99 846); trần thấp cắt sớm trang bị lặp vòng (từng chạy tới 8192, ~4 phút).
_OCR_MAX_TOKENS = 2000
# OCR là chép lại nên cần ổn định: bộ nothink (0.7/0.8/20) đã thử làm cùng một ảnh đọc ra ngày
# sinh khác nhau giữa hai lượt mà không bớt lỗi cố định nào.
OCR_SAMPLING = {"temperature": 0}
_TIMEOUT_S = 180

OCR_PROMPT = """Bạn là công cụ OCR. Chép lại NGUYÊN VĂN toàn bộ chữ trong ảnh giấy tờ tiếng Việt, theo thứ tự đọc từ trên xuống, trái sang phải; mỗi dòng trên giấy là một dòng.
- Giữ đúng dấu tiếng Việt, chữ số, ký hiệu, chữ hoa/thường như trên giấy. Chữ viết tay chép đúng nét nhìn thấy.
- KHÔNG sửa chính tả, KHÔNG diễn giải, KHÔNG tóm tắt, KHÔNG thêm thông tin không có trong ảnh.
- Chữ viết tay đọc CHƯA CHẮC thì vẫn chép theo nét nhìn thấy và ghi [?] ngay sau chữ đó (dạng "<chữ>[?]"); KHÔNG thay
  bằng một từ khác nghe hợp lý hơn.
- Đoạn không đọc được thì ghi [?] MỘT lần cho cả đoạn rồi đọc tiếp; KHÔNG lặp lại [?] hay lặp lại một dòng.
- Bảng thì chép từng hàng, ngăn các ô bằng " | ".
- Bỏ qua hoa văn và con dấu không có chữ đọc được.
Chỉ trả về phần chữ đã chép, không kèm lời dẫn."""


def _endpoint(base_url: str) -> str:
    # Base có thể đã kèm "/v1" — cùng quy ước với app/services/llm/client.py.
    base = base_url.rstrip("/")
    return base + ("/chat/completions" if base.endswith("/v1") else "/v1/chat/completions")


async def chat(messages: list[dict], *, max_tokens: int, timeout_s: float = _TIMEOUT_S,
               thinking: bool = False, sampling: dict | None = None, ocr_server: bool = False) -> dict:
    """Một lượt gọi Qwen, KHÔNG rơi sang OpenAI như client chính — so sánh phải đúng một model.

    ``sampling`` ghi đè thông số lấy mẫu (temperature/top_p/top_k/presence_penalty); mặc định
    temperature 0. ``ocr_server`` → gọi máy OCR riêng (OCR_QWEN_*) nếu có cấu hình. Trả
    ``{content, finish_reason, usage, ms}``; lỗi HTTP ném RuntimeError.
    """
    base_url, model = settings.llm_base_url, settings.llm_model
    if ocr_server and settings.ocr_qwen_base_url:
        base_url, model = settings.ocr_qwen_base_url, settings.ocr_qwen_model or settings.llm_model
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        **(sampling or {}),
        "max_tokens": max_tokens,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": thinking},
    }
    t0 = time.monotonic()
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_s), verify=False) as client:
        resp = await client.post(_endpoint(base_url), json=payload)
    ms = int((time.monotonic() - t0) * 1000)
    if resp.status_code >= 400:
        raise RuntimeError(f"Qwen HTTP {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    choice = (data.get("choices") or [{}])[0]
    return {
        "content": (choice.get("message") or {}).get("content") or "",
        "finish_reason": choice.get("finish_reason"),
        "usage": data.get("usage") or {},
        "ms": ms,
    }


def _decode(file: dict) -> tuple[bytes, str]:
    match = _DATA_URL_RE.match(file.get("dataUrl") or "")
    if not match:
        raise ValueError("dataUrl không hợp lệ")
    payload = match.group(3)
    payload += "=" * (-len(payload) % 4)
    return base64.b64decode(payload), (match.group(1) or file.get("type") or "").lower()


def _page_images(raw: bytes, mime: str) -> list[bytes]:
    """PDF → từng trang; ảnh → một trang. Mọi trang render lại JPEG để kích thước ổn định."""
    filetype = "pdf" if "pdf" in mime else (mime.split("/")[-1] or None)
    doc = fitz.open(stream=raw, filetype=filetype)
    images = []
    for page in doc:
        zoom = min(_MAX_SIDE_PX / max(page.rect.width, page.rect.height), _MAX_ZOOM)
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        images.append(pix.tobytes("jpeg", jpg_quality=_JPEG_QUALITY))
    return images


async def _ocr_page(image: bytes, sem: asyncio.Semaphore) -> dict:
    url = "data:image/jpeg;base64," + base64.b64encode(image).decode()
    async with sem:
        return await chat(
            [{"role": "user", "content": [
                {"type": "text", "text": OCR_PROMPT},
                {"type": "image_url", "image_url": {"url": url}},
            ]}],
            max_tokens=_OCR_MAX_TOKENS,
            sampling=OCR_SAMPLING,
            ocr_server=True,
        )


async def _ocr_file(file: dict, sem: asyncio.Semaphore) -> dict:
    out = {"name": file.get("name"), "type": file.get("type"), "text": "", "provider": "qwen",
           "pages": 0, "ms": 0}
    t0 = time.monotonic()
    try:
        raw, mime = _decode(file)
        if "wordprocessingml" in mime or (file.get("name") or "").lower().endswith(".docx"):
            out["error"] = "OCR Qwen chưa hỗ trợ DOCX"
            return out
        images = await asyncio.to_thread(_page_images, raw, mime)
        results = await asyncio.gather(*(_ocr_page(img, sem) for img in images))
    except Exception as exc:  # noqa: BLE001 — lỗi theo từng tệp, giữ shape kết quả
        out["error"] = f"OCR Qwen: {exc}"
        out["ms"] = int((time.monotonic() - t0) * 1000)
        return out
    out["pages"] = len(results)
    if len(results) == 1:
        out["text"] = results[0]["content"].strip()
    else:
        out["text"] = "\n\n".join(
            f"--- Trang {i}/{len(results)} ---\n{r['content'].strip()}" for i, r in enumerate(results, 1)
        )
    cut = [i for i, r in enumerate(results, 1) if r.get("finish_reason") == "length"]
    if cut:
        out["error"] = f"OCR Qwen bị cắt ở trang {cut} (chạm max_tokens)"
    out["ms"] = int((time.monotonic() - t0) * 1000)
    return out


async def ocr_per_file(files: list[dict]) -> list[dict]:
    sem = asyncio.Semaphore(_PAGE_CONCURRENCY)
    return list(await asyncio.gather(*(_ocr_file(f, sem) for f in files)))

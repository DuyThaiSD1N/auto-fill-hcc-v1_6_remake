"""Provider OCR thô vnekyc — POST /api/v1/ocr/raw (Google Vision).

Nhận PDF/ảnh trực tiếp, trả fullText. Dùng mặc định cho bước đính kèm và cho bước fill
khi KHÔNG tích "Có bản viết tay". Public API trùng ocr_vintern để dispatcher gọi đồng nhất.
"""
import asyncio

import httpx

from app.config import settings


async def _call_raw(client: httpx.AsyncClient, files: list[dict]) -> str:
    """Gọi /api/v1/ocr/raw cho 1 nhóm file, trả fullText."""
    if not files:
        return ""
    r = await client.post(
        settings.ocr_raw_base_url.rstrip("/") + "/api/v1/ocr/raw",
        json={"files": files, "include_tokens": False},
    )
    if r.status_code >= 400:
        raise RuntimeError(f"OCR raw HTTP {r.status_code}: {r.text[:300]}")
    data = r.json()
    return data.get("fullText", "") or ""


async def ocr_per_file(files: list[dict]) -> list[dict]:
    """OCR từng file riêng (giữ thứ tự) → [{name, type, text, error?}]."""
    timeout = httpx.Timeout(settings.ocr_timeout_ms / 1000)
    out: list[dict] = [None] * len(files)  # type: ignore

    async with httpx.AsyncClient(timeout=timeout) as client:
        async def run(idx: int, f: dict) -> None:
            item = {"name": f.get("name"), "type": f.get("type"), "text": ""}
            try:
                item["text"] = await _call_raw(client, [f])
            except Exception as e:  # noqa: BLE001
                item["error"] = str(e)
            out[idx] = item

        await asyncio.gather(*(run(i, f) for i, f in enumerate(files)))

    return out


async def ocr_by_role(files_by_role: dict[str, list[dict]]) -> dict[str, str]:
    """files_by_role: { role: [...] } -> { role: fullText, role_error?: "..." }."""
    out: dict[str, str] = {}
    timeout = httpx.Timeout(settings.ocr_timeout_ms / 1000)

    async with httpx.AsyncClient(timeout=timeout) as client:
        async def run(role: str, files: list[dict]) -> None:
            if not files:
                return
            try:
                out[role] = await _call_raw(client, files)
            except Exception as e:  # noqa: BLE001
                out[role] = ""
                out[role + "_error"] = str(e)

        await asyncio.gather(*(run(role, files) for role, files in files_by_role.items()))

    return out


async def ocr_tokens_per_file(files: list[dict]) -> list[dict]:
    """OCR từng file với include_tokens=True (cho rà soát bbox).

    Trả [{name, type, text, tokens:[{text,bbox[x,y,w,h],confidence,page}], error?}].
    bbox đã chuẩn hoá [0,1] do vnekyc /ocr/raw trả sẵn.
    """
    timeout = httpx.Timeout(settings.ocr_timeout_ms / 1000)
    out: list[dict] = [None] * len(files)  # type: ignore

    async with httpx.AsyncClient(timeout=timeout) as client:
        async def run(idx: int, f: dict) -> None:
            item = {"name": f.get("name"), "type": f.get("type"), "text": "", "tokens": []}
            try:
                r = await client.post(
                    settings.ocr_raw_base_url.rstrip("/") + "/api/v1/ocr/raw",
                    json={"files": [f], "include_tokens": True},
                )
                if r.status_code >= 400:
                    raise RuntimeError(f"OCR raw HTTP {r.status_code}: {r.text[:300]}")
                data = r.json()
                item["text"] = data.get("fullText", "") or ""
                toks: list[dict] = []
                for p in data.get("pages") or []:
                    page_no = int(p.get("page", 0) or 0)
                    for t in p.get("tokens") or []:
                        toks.append({
                            "text": t.get("text", ""),
                            "bbox": t.get("bbox") or [0, 0, 0, 0],
                            "confidence": t.get("confidence", 0),
                            "page": page_no,
                        })
                item["tokens"] = toks
            except Exception as e:  # noqa: BLE001
                item["error"] = str(e)
            out[idx] = item

        await asyncio.gather(*(run(i, f) for i, f in enumerate(files)))

    return out

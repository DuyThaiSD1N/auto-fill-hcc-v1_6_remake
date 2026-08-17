"""Dispatcher OCR: chọn provider theo từng request.

- "raw": OCR thô vnekyc /api/v1/ocr/raw (mặc định, bước đính kèm + fill không viết tay).
- "vintern": Vintern-1B-v3.5 (khi UI tích "Có bản viết tay").

Provider được set 1 lần ở router (process/attachments) qua ContextVar request-scoped, nên
mọi pipeline gọi ocr.ocr_per_file/ocr_by_role không cần truyền thêm tham số. Có thể truyền
provider= tường minh để ghi đè (vd test).
"""
import asyncio
import logging
from contextvars import ContextVar

from app.config import settings
from app.services import ocr_gemini, ocr_raw, ocr_tiengnoi, ocr_vintern

logger = logging.getLogger(__name__)

_PROVIDERS = {"raw": ocr_raw, "vintern": ocr_vintern}
_DEFAULT_PROVIDER = "raw"

# Provider hiệu lực cho request hiện tại. Mỗi request (1 asyncio task) có context riêng nên
# không rò rỉ giữa các request; asyncio.gather copy context con → propagate vào OCR song song.
_provider_ctx: ContextVar[str] = ContextVar("ocr_provider", default=_DEFAULT_PROVIDER)


def provider_from_options(options: dict | None) -> str:
    """Map option UI -> provider. "Có bản viết tay" -> vintern, ngược lại -> raw."""
    return "vintern" if (options or {}).get("hasHandwriting") else "raw"


def use_provider(provider: str | None) -> None:
    """Set provider cho request hiện tại (gọi ở router trước khi chạy pipeline)."""
    _provider_ctx.set(provider if provider in _PROVIDERS else _DEFAULT_PROVIDER)


def current_provider() -> str:
    return _provider_ctx.get()


def _resolve(provider: str | None) -> tuple[object, str]:
    """Trả (module OCR, nhãn) cho 1 provider logic. Bật cờ *_by_gemini + CÓ GEMINI_API_KEY -> Gemini;
    THIẾU key -> FALLBACK engine cũ (nhãn vẫn raw/vintern)."""
    key = provider if provider in _PROVIDERS else _DEFAULT_PROVIDER
    use_gemini = bool(settings.gemini_api_key) and (
        (key == "raw" and settings.raw_by_gemini)
        or (key == "vintern" and settings.vintern_by_gemini)
    )
    if use_gemini:
        return ocr_gemini, "gemini"
    return _PROVIDERS[key], key


def resolved_label(provider: str | None = None) -> str:
    """Nhãn engine THẬT sẽ chạy (cho trace). None -> provider hiệu lực của request hiện tại."""
    if provider is None and settings.ocr_by_tiengnoi:
        return "tiengnoi"
    return _resolve(provider or _provider_ctx.get())[1]


async def _tiengnoi_then_gemini(files: list[dict]) -> list[dict]:
    """OCR fill: tiengnoi (vintern-v6) CHÍNH → Gemini fallback.

    - Batch tiengnoi lỗi/sập (vd 502) → OCR LẠI toàn bộ bằng Gemini.
    - File nào rỗng/lỗi từ tiengnoi → OCR bù riêng file đó bằng Gemini (per-file).
    Gắn "provider" theo engine THẬT phục vụ từng file (tiengnoi | gemini) cho trace.
    """
    try:
        results = await ocr_tiengnoi.ocr_per_file(files, max_tokens=settings.ocr_tiengnoi_fill_max_tokens)
    except Exception as e:  # noqa: BLE001 — tiengnoi sập → Gemini toàn bộ
        logger.warning("OCR tiengnoi batch lỗi (%s) → fallback Gemini toàn bộ", e)
        results = await ocr_gemini.ocr_per_file(files)
        for r in results:
            r["provider"] = "gemini"
        return results

    bad = [i for i, r in enumerate(results) if r.get("error") or not (r.get("text") or "").strip()]
    if bad:
        gem = await ocr_gemini.ocr_per_file([files[i] for i in bad])
        for j, i in enumerate(bad):
            results[i] = gem[j]
            results[i]["provider"] = "gemini"
    for r in results:
        r.setdefault("provider", "tiengnoi")
    return results


async def ocr_per_file(files: list[dict], provider: str | None = None) -> list[dict]:
    """OCR từng file. Nếu file mang cờ `hasHandwriting` (mỗi tài liệu chọn viết tay riêng) thì
    ROUTE THEO TỪNG FILE: viết tay → Vintern, còn lại → raw. Không có cờ nào → dùng 1 provider
    (context/tham số, tương thích cũ). Mỗi result gắn thêm khóa "provider".
    """
    # Chuyển hẳn OCR fill sang tiengnoi (vintern-v6) + fallback Gemini — khi KHÔNG ép provider.
    # Bỏ qua định tuyến raw/vintern/gemini cũ: tiengnoi xử cả in lẫn viết tay.
    if not provider and settings.ocr_by_tiengnoi:
        return await _tiengnoi_then_gemini(files)

    # Provider tường minh, hoặc không file nào khai cờ per-file → 1 provider cho cả lô.
    if provider or not any("hasHandwriting" in (f or {}) for f in files):
        mod, label = _resolve(provider or _provider_ctx.get())
        results = await mod.ocr_per_file(files)
        for r in results:
            r.setdefault("provider", label)
        return results

    # Route theo từng file (2 nhóm), OCR song song, ghép lại theo thứ tự gốc.
    groups: dict[str, list[tuple[int, dict]]] = {"vintern": [], "raw": []}
    for i, f in enumerate(files):
        groups["vintern" if (f or {}).get("hasHandwriting") else "raw"].append((i, f))

    async def _run(key: str, items: list[tuple[int, dict]]):
        mod, label = _resolve(key)
        sub = await mod.ocr_per_file([f for _, f in items])
        return label, items, sub

    results_by_index: dict[int, dict] = {}
    for label, items, sub in await asyncio.gather(
        *(_run(key, items) for key, items in groups.items() if items)
    ):
        for (i, _), r in zip(items, sub):
            r["provider"] = label
            results_by_index[i] = r
    return [results_by_index[i] for i in range(len(files))]


async def ocr_by_role(files_by_role: dict[str, list[dict]], provider: str | None = None) -> dict[str, str]:
    mod, _label = _resolve(provider or _provider_ctx.get())
    return await mod.ocr_by_role(files_by_role)

"""Nạp dữ liệu một hồ sơ: trace prod, tệp gốc, OCR Vintern prod đã lưu, OCR Qwen (có cache theo nội dung tệp)."""
from __future__ import annotations

import base64
import hashlib
import json
import re
import time
import unicodedata
from pathlib import Path

import fitz

from app.config import settings
from app.services import ocr_qwen
from scripts.ocr_compare import _file_dict, _out_root, _prepare_request, _qwen_ocr_unique

_SECTION_RE = re.compile(r"^===== (.+?) \((?:tiengnoi|docx[^)]*)\) =====$", re.M)
_QWEN_CACHE = "ocr_qwen_cache.json"


def out_root() -> Path:
    return _out_root()


def _sha(file: dict) -> str:
    return hashlib.sha256(file["dataUrl"].encode()).hexdigest()


def _vintern_sections(ocr_text: str) -> list[str]:
    parts = _SECTION_RE.split(ocr_text or "")
    return [parts[i + 1].strip().removesuffix("---").strip() for i in range(1, len(parts), 2)]


def load(rid: str) -> dict:
    """Trace + tệp (đúng thứ tự lượt gốc) + OCR Vintern theo sha256 tệp + options như router prod."""
    _, paths, trace = _prepare_request(rid, out_root())
    docs = [_file_dict(p) for p in paths]
    sections = _vintern_sections(trace.get("ocr_text"))
    vintern = {_sha(d): sections[i] if i < len(sections) else "" for i, d in enumerate(docs)}
    options = {}
    if trace.get("applicant_name"):
        options["formContext"] = {"applicantFullname": trace["applicant_name"]}
    name = (trace.get("name") or "").lower()
    if "hiệp hoà" in name or "hiệp hòa" in name:
        options["grantorAsRequester"] = True
    vintern_ms = (trace.get("stats") or {}).get("ocr_latency_ms") or 0
    return {"rid": rid, "docs": docs, "vintern_by_sha": vintern, "vintern_text": trace.get("ocr_text") or "",
            "vintern_prod_s": round(vintern_ms / 1000, 1), "options": options, "dir": out_root() / rid}


async def load_file(path: Path) -> dict:
    """Một tệp lẻ (không có trace prod) = một hồ sơ: OCR Vintern chạy THẬT (cache tắt), lưu cache ở <tệp>_luongmoi/."""
    from app.services import ocr

    settings.ocr_cache_enabled = False
    doc = _file_dict(path)
    t0 = time.monotonic()
    result = (await ocr.ocr_per_file([doc]))[0]
    text = result.get("text") or ""
    folder = path.parent / f"{path.stem}_luongmoi"
    folder.mkdir(exist_ok=True)
    return {"rid": path.stem, "docs": [doc], "vintern_by_sha": {_sha(doc): text},
            "vintern_text": f"===== {doc['name']} (tiengnoi) =====\n{text}",
            "vintern_prod_s": round(time.monotonic() - t0, 1), "options": {}, "dir": folder}


_DATE_RE = re.compile(r"(\d{1,2})\s*(?:[/.\-]|tháng)\s*(\d{1,2})\s*(?:[/.\-]|năm)\s*(\d{4})", re.I)
_PAGE_RE = re.compile(r"--- Trang (\d+)/(\d+) ---")
_ROTATE_TRY = (90, 270)


def _numbers(text: str) -> set[str]:
    """Ngày + dãy số dài (số giấy tờ) — phần điền tay không thể trùng ngẫu nhiên giữa hai OCR."""
    text = unicodedata.normalize("NFC", text or "")
    found = {f"{int(d)}/{int(m)}/{y}" for d, m, y in _DATE_RE.findall(text)}
    return found | set(re.findall(r"\d{6,}", text))


def _overlap(text: str, anchor: set[str]) -> tuple[float, int]:
    nums = _numbers(text)
    return (len(nums & anchor) / len(nums) if nums else 1.0), len(nums)


async def _ocr_rotated(doc: dict, page_index: int, angle: int) -> str:
    raw, mime = ocr_qwen._decode(doc)
    filetype = "pdf" if "pdf" in mime else (mime.split("/")[-1] or None)
    page = fitz.open(stream=raw, filetype=filetype)[page_index]
    zoom = min(ocr_qwen._MAX_SIDE_PX / max(page.rect.width, page.rect.height), ocr_qwen._MAX_ZOOM)
    image = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom).prerotate(angle)).tobytes("jpeg", jpg_quality=ocr_qwen._JPEG_QUALITY)
    url = "data:image/jpeg;base64," + base64.b64encode(image).decode()
    resp = await ocr_qwen.chat([{"role": "user", "content": [{"type": "text", "text": ocr_qwen.OCR_PROMPT},
                                                             {"type": "image_url", "image_url": {"url": url}}]}],
                               max_tokens=ocr_qwen._OCR_MAX_TOKENS, sampling=ocr_qwen.OCR_SAMPLING, ocr_server=True)
    return resp["content"].strip()


async def _fix_rotated(doc: dict, text: str, vintern: str) -> tuple[str, list[int]]:
    """Trang scan xoay 90° làm Qwen bịa nguyên trang (tên, ngày, số không có trên giấy). Dấu hiệu: số/ngày Qwen đọc
    gần như không trùng OCR Vintern của cùng tệp (Vintern tự xoay đúng chiều) → OCR lại ở 90°/270°, giữ bản trùng
    nhiều nhất. Trang bình thường không tốn thêm lượt gọi nào."""
    anchor = _numbers(vintern)
    if not anchor:
        return text, []
    parts = _PAGE_RE.split(text)
    pages = [parts[0]] if len(parts) == 1 else [parts[i + 2] for i in range(1, len(parts), 3)]
    fixed = []
    for index, page_text in enumerate(pages):
        score, count = _overlap(page_text, anchor)
        if count < 3 or score > 1 / 3:
            continue
        best_text, best_score = page_text, score
        for angle in _ROTATE_TRY:
            candidate = await _ocr_rotated(doc, index, angle)
            cand_score, _ = _overlap(candidate, anchor)
            if cand_score > best_score:
                best_text, best_score = candidate, cand_score
        if best_score >= 0.5:
            pages[index] = best_text.strip()
            fixed.append(index + 1)
    if not fixed:
        return text, []
    if len(pages) == 1:
        return pages[0], fixed
    return "\n\n".join(f"--- Trang {i}/{len(pages)} ---\n{p.strip()}" for i, p in enumerate(pages, 1)), fixed


async def qwen_ocr(case: dict, refresh: bool = False) -> tuple[list[dict], float, bool]:
    """→ (kết quả từng tệp, giây OCR, có lấy cache không). Cache ở <mã>/ocr_qwen_cache.json theo sha256 + model."""
    cache_path = case["dir"] / _QWEN_CACHE
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.is_file() else {}
    keys = [_sha(d) for d in case["docs"]]
    model = settings.ocr_qwen_model or settings.llm_model
    if cache.get("_model", model) != model:
        cache = {}
    cached = not refresh and all(k in cache for k in keys)
    t0 = time.monotonic()
    if not cached:
        rows = await _qwen_ocr_unique(case["docs"])
        for k, r in zip(keys, rows):
            cache[k] = {"text": r.get("text") or "", "error": r.get("error"), "pages": r.get("pages"), "ms": r.get("ms")}
    # Soát trang xoay (một lần cho mỗi tệp, ghi lại vào cache).
    for k, d in zip(keys, case["docs"]):
        if not cache[k].get("rot_checked"):
            cache[k]["text"], cache[k]["rot_fixed"] = await _fix_rotated(d, cache[k]["text"], case["vintern_by_sha"].get(k, ""))
            cache[k]["rot_checked"] = True
    if not cached:
        cache["_wall_s"], cache["_model"] = round(time.monotonic() - t0, 1), model
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    rows = [{**cache[k], "name": d["name"]} for k, d in zip(keys, case["docs"])]
    return rows, cache.get("_wall_s", 0.0), cached


def qwen_text(rows: list[dict]) -> str:
    return "\n\n".join(f"### Tài liệu {i}: {r.get('name')}\n{(r.get('text') or '(không đọc được)').strip()}"
                       for i, r in enumerate(rows, 1))

"""Compact agent process pipeline cho "Đăng ký biến động 1.013980" (cổng DVC Đà Nẵng).

HAI vai: CHỦ HỒ SƠ (bên được đăng ký biến động) và NGƯỜI NỘP (có thể ủy quyền) + Phần II thửa đất. Xem mapper.

Hồ sơ thủ tục này hay là MỘT PDF quét gộp vài chục trang (bộ mẫu 75 trang): OCR một request mất ~120s, quá
timeout 100s của extension. Server OCR có trần song song mỗi request nên PDF lớn được cắt thành tối đa
_OCR_MAX_PARTS phần gửi đồng thời (đo bộ mẫu: 1 phần 122s, 4 phần 60s, 8 phần 47s), rồi ghép text lại đúng thứ
tự trang. Mỗi phần vẫn qua cache OCR như thường."""

import asyncio
import base64
import math

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_bien_dong_thoa_thuan_thanh_vien_ho_gia_dinh_da_nang.process import mapper
from app.pipelines.dang_ky_bien_dong_thoa_thuan_thanh_vien_ho_gia_dinh_da_nang.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_bien_dong_thoa_thuan_thanh_vien_ho_gia_dinh_da_nang.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

_OCR_MAX_PARTS = 6
_OCR_MIN_PAGES_PER_PART = 8


def _split_pdf(file: dict) -> list[dict] | None:
    """Cắt PDF lớn thành các phần liền trang; None = giữ nguyên (ảnh, PDF ít trang, hoặc đọc lỗi)."""
    header, sep, b64 = str(file.get("dataUrl") or "").partition(",")
    if not sep or "pdf" not in header.lower():
        return None
    try:
        import fitz  # pymupdf

        src = fitz.open(stream=base64.b64decode(b64), filetype="pdf")
    except Exception:  # noqa: BLE001 — không cắt được thì OCR nguyên tệp như cũ
        return None
    try:
        pages = src.page_count
        parts = min(_OCR_MAX_PARTS, pages // _OCR_MIN_PAGES_PER_PART)
        if parts < 2:
            return None
        size = math.ceil(pages / parts)
        chunks = []
        for start in range(0, pages, size):
            out = fitz.open()
            try:
                out.insert_pdf(src, from_page=start, to_page=min(start + size, pages) - 1)
                data = base64.b64encode(out.tobytes()).decode("ascii")
            finally:
                out.close()
            chunks.append({**file, "name": f"{file.get('name')}#trang{start + 1}", "dataUrl": f"{header},{data}"})
        return chunks
    finally:
        src.close()


async def _ocr_split_large_pdfs(files: list[dict]) -> list[dict]:
    """Thay ocr.ocr_per_file: cùng đầu vào/đầu ra, nhưng PDF lớn OCR song song theo phần."""
    from app.services import ocr

    split = [_split_pdf(f) for f in files]
    whole = [f for f, chunks in zip(files, split) if chunks is None]
    jobs = [ocr.ocr_per_file(whole)] if whole else []
    jobs += [ocr.ocr_per_file([chunk]) for chunks in split if chunks for chunk in chunks]
    done = iter(await asyncio.gather(*jobs))
    whole_results = iter(next(done) if whole else [])

    results: list[dict] = []
    for f, chunks in zip(files, split):
        if chunks is None:
            results.append(next(whole_results))
            continue
        parts = [next(done)[0] for _ in chunks]
        errors = [p["error"] for p in parts if p.get("error")]
        item = {
            "name": f.get("name"),
            "type": f.get("type"),
            "text": "\n".join(p.get("text") or "" for p in parts).strip(),
            "provider": "tiengnoi",
        }
        if errors:
            item["error"] = "; ".join(errors)
        results.append(item)
    return results


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        ocr_fn=_ocr_split_large_pdfs,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res

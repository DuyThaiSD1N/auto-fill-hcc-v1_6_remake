"""Đính kèm TÁCH giấy tờ cho tính hoặc tính lại tiền sử dụng đất (1.115148, cổng Khánh Hòa) — cài đặt "Tách giấy tờ" bật.

LLM đọc đầu từng trang trong MỘT lượt, chỉ ra trang nào mở giấy mới và loại giấy; mỗi giấy thành một mục có
`sourceSegments` (extension cắt đúng các trang) vào dòng duy nhất của bảng. Bảng trùng bản Lâm Đồng nên dùng lại hàm đọc
JSON chia giấy và dựng mục của bản đó; prompt ghi cổng Khánh Hòa. Tệp không cắt được → nguyên tệp một lần; LLM chia giấy
lỗi → đính như chế độ không tách (của Khánh Hòa).
"""

import time

from app.config import settings
from app.pipelines._shared.documents import representative_excerpt
from app.pipelines.di_chuyen_ho_so_nguoi_huong_tro_cap.attach.planner import splittable_pages
from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_tuyen_quang.attach.dinh_kem_tach.planner import _page_ocr
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_lam_dong.attach.dinh_kem_tach.planner import (
    build_plan_items,
    parse_documents,
)
from app.process.schemas import FileItem
from app.services.llm import client

from ..dinh_kem_khong_tach.planner import plan as plan_without_split
from ..dinh_kem_khong_tach.planner import portal_rows
from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

__all__ = ["build_plan_items", "parse_documents", "plan"]


async def _segment(units: dict[int, list[str]]) -> dict[int, list[tuple[int, str, str]]]:
    payload = [
        {"fileIndex": index, "soTrang": len(pages),
         "trang": [{"trang": n + 1, "ocr": _page_ocr(page)} for n, page in enumerate(pages)]}
        for index, pages in units.items()
    ]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": build_user_prompt(payload)}]
    total = sum(len(pages) for pages in units.values())
    for attempt in range(2):  # JSON hỏng → hỏi lại một lần
        # temperature 0: cùng tệp phải ra cùng cách chia giữa các lần chạy.
        raw = await client.chat(messages, temperature=0, max_tokens=max(400, min(4000, 120 + 60 * total)),
                                enable_thinking=settings.agent_reasoning)
        try:
            return parse_documents(client.extract_json_block(raw), {i: len(p) for i, p in units.items()})
        except Exception:  # noqa: BLE001
            if attempt:
                raise
    return {}


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    from app.services import ocr

    rows = portal_rows(options)
    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    pairs = [(index, file) for index, file in enumerate(raw_files) if file.get("type") in _OCR_TYPES]
    errors: list[str] = []

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file([file for _, file in pairs]) if pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    pages_by_file: dict[int, list[str]] = {}
    for (index, file), result in zip(pairs, ocr_results):
        if result.get("error"):
            errors.append(f"OCR {file.get('name')}: {result['error']}")
        text = str(result.get("text") or "")
        if text.strip():
            # Không cắt được (số trang OCR lệch PDF) → cả tệp là một "trang" trích đoạn đại diện.
            pages_by_file[index] = splittable_pages(file, text) or [representative_excerpt(text, 6000)]

    started = time.monotonic()
    try:
        documents = await _segment(pages_by_file) if pages_by_file else {}
    except Exception as exc:  # noqa: BLE001 — chia giấy hỏng thì đính nguyên tệp như chế độ không tách
        result = await plan_without_split(files, options, session)
        result["errors"] = [f"Tách giấy tờ: {exc} — đính nguyên tệp.", *errors, *result.get("errors", [])]
        return result
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, segments = build_plan_items(raw_files, pages_by_file, documents, rows)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [item["name"] for item in raw_files],
            "tachGiayTo": segments,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

"""Đính kèm thủ tục hỗ trợ chi phí học tập (Bắc Ninh 1.014581) — chế độ KHÔNG tách (cài đặt "Tách giấy tờ" tắt).

OCR từng tệp (cùng cách gọi của chế độ tách) → MỘT lượt LLM liệt kê mọi loại giấy trong từng tệp → MỖI TỆP đính
NGUYÊN, đúng MỘT lần (không `sourceSegments`), theo giấy chính của tệp (_PRIORITY):
  Đơn đề nghị Mẫu 01                → KQ001000
  Xác nhận cơ sở đào tạo Mẫu 02     → KQ001001
  Bằng tốt nghiệp THCS/THPT         → KQ001002
  Giấy tờ đối tượng ưu tiên         → KQ001003
  Đơn ủy quyền, Lời chứng, CCCD, giấy chưa rõ → ô "File đính kèm khác" (fileDinhKem, target=supplementary)
Định tuyến (mã KQ / fileDinhKem) và shape item dùng CHUNG `catalog` + `_build_item` với chế độ tách để hai chế độ
đặt cùng chỗ. LLM lỗi / không trả lời tệp → rule keyword theo từng trang của chế độ tách; OCR rỗng → "khac" vào
fileDinhKem, giữ tên gốc. Không bao giờ bỏ tệp.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared.documents import representative_excerpt
from app.process.schemas import FileItem
from app.services.llm import client

from .. import catalog
from ..dinh_kem_tach.planner import (
    _OCR_TYPES,
    _build_item,
    _normalize_type,
    _pdf_page_count,
    _rule_page_type,
    _split_pages,
)
from .prompt import SYSTEM_PROMPT, build_user_prompt

_LLM_TEXT_MAX_CHARS = 6000

# Tệp gộp nhiều giấy: giấy ĐỨNG TRƯỚC nhận nguyên tệp. Đơn Mẫu 01 trước, giấy có mã KQ riêng sau, giấy đi ô
# "File đính kèm khác" cuối.
_PRIORITY: tuple[str, ...] = (
    "don_de_nghi", "xac_nhan_dao_tao", "bang_tot_nghiep", "giay_uu_tien",
    "don_uy_quyen", "loi_chung", "cccd", "khac",
)


def doc_types(raw: Any) -> list[str]:
    """docTypes LLM trả (chuỗi hoặc danh sách) → danh sách nhãn catalog hợp lệ, không trùng, giữ thứ tự."""
    if not isinstance(raw, list):
        raw = [raw]
    out: list[str] = []
    for value in raw:
        label = _normalize_type(value)
        if label not in out:
            out.append(label)
    return out


def primary(types: list[str]) -> str:
    return next((label for label in _PRIORITY if label in types), "khac")


def rule_types(text: str, page_count: int) -> list[str]:
    """Rule keyword của chế độ tách chạy theo từng trang → các loại giấy có trong tệp."""
    units, _ = _split_pages(text, page_count)
    return doc_types([_rule_page_type(u.get("text") or "") for u in units])


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, list[str]]:
    if not documents:
        return {}
    raw = await client.chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(documents)},
        ],
        max_tokens=max(500, min(2000, len(documents) * 100)),
        enable_thinking=settings.agent_reasoning,
    )
    parsed = client.extract_json_block(raw)
    result: dict[int, list[str]] = {}
    for item in parsed.get("documents", []) or []:
        try:
            result[int(item.get("index"))] = doc_types(item.get("docTypes", item.get("docType")))
        except (TypeError, ValueError, AttributeError):
            continue
    return result


def build_plan_items(
    raw_files: list[dict],
    types_by_file: dict[int, list[str]],
    page_counts: dict[int, int],
) -> tuple[list[dict], list[dict], list[str]]:
    """Mỗi tệp → đúng 1 item (shape `_build_item` của chế độ tách, đoạn phủ trọn tệp). Thuần tất định."""
    attachments: list[dict] = []
    classified: list[dict] = []
    warnings: list[str] = []
    for idx, file in enumerate(raw_files):
        page_count = page_counts.get(idx, 1)
        types = types_by_file.get(idx) or ["khac"]
        label = primary(types)
        item = _build_item(file, idx, {"pageFrom": 1, "pageTo": page_count, "docType": label}, page_count)
        kq_codes = sorted({code for code in (catalog.resolve(t)[1] for t in types) if code})
        others = [code for code in kq_codes if code != item["componentName"]]
        # Tệp gộp nhiều giấy có mã KQ riêng hoặc chưa rõ loại giữ TÊN GỐC để cán bộ nhận ra.
        if others or label == "khac":
            item["documentName"] = item["fileName"]
        attachments.append(item)
        classified.append({
            "fileName": file.get("name"),
            "pageFrom": 1,
            "pageTo": page_count,
            "docType": label,
            "docTypes": types,
            "target": item["target"],
            "componentName": item["componentName"],
        })
        where = item["componentName"] or "File đính kèm khác"
        if others:
            warnings.append(
                f"'{item['fileName']}' gộp nhiều giấy tờ — đính nguyên tệp một lần vào {where}, không tách sang "
                f"{', '.join(others)}; cán bộ kiểm tra lại."
            )
        elif label == "khac":
            warnings.append(
                f"Chưa nhận diện chắc loại giấy tờ cho '{item['fileName']}' — tạm đính vào ô File đính kèm khác; "
                "cán bộ kiểm tra lại."
            )
    return attachments, classified, warnings


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options or {}
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    pairs = [(i, f) for i, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]

    from app.services import ocr

    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file([f for _, f in pairs]) if pairs else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    texts: dict[int, str] = {}
    for (idx, file), result in zip(pairs, ocr_results):
        if result.get("error"):
            errors.append(f"OCR {file.get('name')}: {result['error']}")
        if str(result.get("text") or "").strip():
            texts[idx] = str(result["text"])

    page_counts = {i: _pdf_page_count(f) for i, f in enumerate(raw_files)}
    llm_docs = [{"index": i, "text": representative_excerpt(t, _LLM_TEXT_MAX_CHARS)} for i, t in texts.items()]

    t1 = time.monotonic()
    llm_types: dict[int, list[str]] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001 - fallback rule keyword giữ đủ tài liệu
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    types_by_file = {
        i: llm_types.get(i) or rule_types(texts[i], page_counts[i]) for i in texts
    }
    attachments, classified, warnings = build_plan_items(raw_files, types_by_file, page_counts)
    errors.extend(warnings)

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [raw_files[i]["name"] for i in texts],
            "llmDocuments": [raw_files[d["index"]]["name"] for d in llm_docs],
            "sessionId": (session or {}).get("request_id"),
            "attachmentMode": "whole_files",
            "classified": classified,
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

"""Đính kèm cấp Phiếu lý lịch tư pháp (3.000333, Cổng DVC quốc gia mới) — chế độ KHÔNG tách giấy tờ.

Bảng "Thành phần hồ sơ" của cổng chỉ có MỘT dòng: "Các giấy tờ để chứng minh đối tượng miễn, hoặc giảm phí (nếu có)",
một dòng nhận nhiều tệp qua nút "Tải lên file". Cổng không có dòng nào khác nên MỌI giấy tờ đã tải lên (tờ khai, căn
cước, ủy quyền, biên lai…) đính chung dòng đó như khai sinh cổng mới (user 24/11: phải đính được, không bỏ tệp); giấy
chứng minh miễn/giảm phí xếp đầu. LLM đọc từng tệp (một lượt) để đặt tên tệp theo tiêu đề giấy và ghép hai mặt thẻ căn
cước của cùng một người thành một tệp. OCR / LLM lỗi → vẫn đính đủ tệp, giữ tên gốc.

Cổng chỉ nhận tệp dưới 2 MB: tệp lớn hơn nén theo thang của cải chính (cùng cổng), trả ở ``replaceFiles``.
"""

import asyncio
import time

from app.config import settings
from app.pipelines._shared.identity_merge import ho_ten_co_dau, mat_the, so_dinh_danh_the
from app.pipelines.cai_chinh_dvc_moi.attach.dinh_kem_khong_tach.planner import shrink_merged, shrink_oversized
from app.pipelines.khai_sinh_dvc_moi.attach.dinh_kem_khong_tach.planner import (
    _document_name,
    _llm_document_name,
    _max_tokens,
    both_sides,
    pair_card_sides,
)
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

MIEN_GIAM = "mien_giam_phi"
ROW = {
    "slotKey": "lltp_mien_giam_phi",
    "slotIndex": 0,
    "slotName": "Các giấy tờ để chứng minh đối tượng miễn, hoặc giảm phí",
}


def item(file_index: int, file_name: str, document_name: str, doc_type: str = "",
         sources: list[dict] | None = None, file_indexes: list[int] | None = None) -> dict:
    out = {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": ROW["slotName"],
        "target": "fixed-slot",
        "needsAddComponent": False,
        "detectedType": doc_type or "other",
        "noChooserClick": True,
        **ROW,
    }
    if sources is not None:
        out["sourceSegments"] = sources
    if file_indexes and len(file_indexes) > 1:
        out["sourceFileIndexes"] = file_indexes
    return out


def unique_name(name: str, seen: dict[str, int]) -> str:
    seen[name.lower()] = seen.get(name.lower(), 0) + 1
    return name if seen[name.lower()] == 1 else f"{name} {seen[name.lower()]}"


def exemption_first(items: list[dict]) -> list[dict]:
    """Giấy chứng minh miễn/giảm phí (đúng tên dòng) lên đầu, còn lại giữ thứ tự tải lên."""
    return sorted(items, key=lambda it: it.get("detectedType") != MIEN_GIAM)


def card_meta(answer: dict, text: str) -> dict:
    """Số định danh / mặt thẻ đọc từ OCR — khoá ghép hai mặt (họ tên LLM đọc có thể lệch giữa hai mặt)."""
    return {**answer, "_soThe": so_dinh_danh_the(text), "_matTheOcr": mat_the(text),
            "chuThe": ho_ten_co_dau(answer.get("chuThe") or "", text)}


async def _classify_all(texts: dict[int, str]) -> dict[int, dict]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt([{"index": i, "text": t[:12000]} for i, t in texts.items()])},
    ]
    raw = await client.chat(messages, max_tokens=_max_tokens(texts), enable_thinking=settings.agent_reasoning)
    out: dict[int, dict] = {}
    for answer in client.extract_json_block(raw).get("documents", []) or []:
        try:
            index = int(answer.get("index"))
        except (AttributeError, TypeError, ValueError):
            continue
        if index in texts and index not in out:
            out[index] = answer
    return out


def build_items(names: list[str], answers: dict[int, dict]) -> list[dict]:
    """Mỗi tệp (hai mặt thẻ cùng người gộp một) → một mục trên dòng duy nhất; giấy miễn/giảm phí đứng đầu."""
    docs = [answers.get(i, {}) for i in range(len(names))]
    items: list[dict] = []
    seen: dict[str, int] = {}
    for group in pair_card_sides(docs):
        first = group[0]
        doc = both_sides(docs[first]) if len(group) > 1 else docs[first]
        doc_type = str(doc.get("docType") or "").strip()
        name = unique_name(_document_name(names[first], _llm_document_name(doc) if doc else ""), seen)
        items.append(item(first, names[first], name, doc_type, file_indexes=group))
    return exemption_first(items)


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    from app.services import ocr

    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    errors: list[str] = []
    pairs = [(i, f) for i, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]
    started = time.monotonic()
    shrink_task = asyncio.create_task(shrink_oversized(raw_files, errors))
    ocr_results = await ocr.ocr_per_file([f for _, f in pairs]) if pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    texts: dict[int, str] = {}
    for (index, file), result in zip(pairs, ocr_results):
        if result.get("error"):
            errors.append(f"OCR {file.get('name')}: {result['error']}")
        if str(result.get("text") or "").strip():
            texts[index] = str(result["text"])

    started = time.monotonic()
    answers: dict[int, dict] = {}
    if texts:
        try:
            answers = await _classify_all(texts)
        except Exception as exc:  # noqa: BLE001 — LLM lỗi → vẫn đính đủ tệp, giữ tên gốc
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)
    answers = {i: card_meta(a, texts.get(i, "")) for i, a in answers.items()}

    replace_files = await shrink_task
    names = [replace_files[str(i)]["name"] if str(i) in replace_files else f["name"] for i, f in enumerate(raw_files)]
    attachments = build_items(names, answers)
    await shrink_merged(raw_files, attachments, replace_files, errors)
    return {
        "attachments": attachments,
        "replaceFiles": replace_files or None,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "classified": [{"fileName": raw_files[i]["name"], "docType": str((answers.get(i) or {}).get("docType") or "")}
                           for i in range(len(raw_files))],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

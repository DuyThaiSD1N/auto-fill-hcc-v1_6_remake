"""Đính kèm đăng ký thành lập hộ kinh doanh (1.001612, Cổng DVC quốc gia mới) — chế độ KHÔNG tách giấy tờ.

Bảng "Thành phần hồ sơ" mặc định có hai dòng, mỗi dòng nhận nhiều tệp qua nút "Tải lên file":
1. Giấy đề nghị đăng ký hộ kinh doanh — đính NGUYÊN tệp giấy đề nghị; mọi giấy khác (căn cước, biên bản họp…) cũng
   vào đây để không bỏ tệp.
2. Bản sao văn bản ủy quyền của thành viên hộ gia đình cho một thành viên làm chủ hộ — CHỈ văn bản ủy quyền giữa các
   thành viên hộ gia đình (chủ thể thành lập là hộ gia đình).
Có giấy ủy quyền NỘP HỒ SƠ (người được ủy quyền nộp thay): extension chọn "Trường hợp ủy quyền thực hiện thủ tục…" ở ô
"Chọn trường hợp thực hiện" trước khi đính, cổng hiện thêm dòng theo trường hợp, giấy ủy quyền vào dòng "Văn bản ủy
quyền cho cá nhân…" (không thấy dòng thì về dòng 1).
LLM đọc từng tệp (một lượt) để phân loại, đặt tên theo tiêu đề và ghép hai mặt thẻ căn cước. OCR / LLM lỗi → vẫn đính
đủ tệp vào dòng 1, giữ tên gốc. Cổng chỉ nhận tệp dưới 2 MB: tệp lớn hơn nén theo thang của cải chính (cùng cổng).
"""

import asyncio
import time

from app.config import settings
from app.pipelines.cai_chinh_dvc_moi.attach.dinh_kem_khong_tach.planner import shrink_merged, shrink_oversized
from app.pipelines.cap_phieu_ly_lich_tu_phap_cong_an_cap_tinh.attach.dinh_kem_khong_tach.planner import (
    card_meta,
    unique_name,
)
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

GIAY_DE_NGHI = "giay_de_nghi"
UY_QUYEN_NOP = "uy_quyen_nop_ho_so"
UY_QUYEN_HGD = "uy_quyen_ho_gia_dinh"

ROW_GIAY_DE_NGHI = {
    "slotKey": "hkd_giay_de_nghi",
    "slotIndex": 0,
    "slotName": "Giấy đề nghị đăng ký hộ kinh doanh",
}
ROW_UY_QUYEN_HGD = {
    "slotKey": "hkd_uy_quyen_thanh_vien_ho_gia_dinh",
    "slotIndex": 1,
    "slotName": "Bản sao văn bản ủy quyền của thành viên hộ gia đình",
}
# Giấy ủy quyền nộp hồ sơ: ô "Chọn trường hợp thực hiện" cạnh bảng phải chọn trường hợp ủy quyền TRƯỚC (người dùng chốt
# 27/11) — cổng mới hiện thêm các dòng theo trường hợp, giấy ủy quyền cho cá nhân vào dòng "Văn bản ủy quyền cho cá
# nhân…". Dòng khớp theo cụm "ủy quyền cho cá nhân" (không dòng nào khác có cụm này); không thấy dòng (chọn trường hợp
# hỏng / cổng đổi chữ) thì extension đính vào dòng Giấy đề nghị như trước.
EXECUTION_CASE = "Trường hợp ủy quyền thực hiện thủ tục"
ROW_UY_QUYEN_NOP = {
    "slotKey": "hkd_uy_quyen_cho_ca_nhan",
    "slotIndex": 2,
    "slotName": "ủy quyền cho cá nhân",
    "fallbackSlotName": ROW_GIAY_DE_NGHI["slotName"],
    "executionCase": EXECUTION_CASE,
    "executionCasePrefer": "ca nhan",
}

# Thứ tự trên dòng 1: giấy đề nghị rồi giấy khác theo thứ tự tải lên.
_ORDER = {GIAY_DE_NGHI: 0, UY_QUYEN_NOP: 1}


def row_of(doc_type: str) -> dict:
    if doc_type == UY_QUYEN_HGD:
        return ROW_UY_QUYEN_HGD
    return ROW_UY_QUYEN_NOP if doc_type == UY_QUYEN_NOP else ROW_GIAY_DE_NGHI


def item(file_index: int, file_name: str, document_name: str, doc_type: str = "",
         sources: list[dict] | None = None, file_indexes: list[int] | None = None) -> dict:
    row = row_of(doc_type)
    out = {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": row["slotName"],
        "target": "fixed-slot",
        "needsAddComponent": False,
        "detectedType": doc_type or "other",
        "noChooserClick": True,
        **row,
    }
    if sources is not None:
        out["sourceSegments"] = sources
    if file_indexes and len(file_indexes) > 1:
        out["sourceFileIndexes"] = file_indexes
    return out


def ordered(items: list[dict]) -> list[dict]:
    """Dòng 1 trước dòng 2; trong dòng 1 giấy đề nghị rồi giấy ủy quyền nộp hồ sơ, còn lại giữ thứ tự tải lên."""
    return sorted(items, key=lambda it: (it["slotIndex"], _ORDER.get(it.get("detectedType"), 2)))


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
    """Mỗi tệp (hai mặt thẻ cùng người gộp một) → một mục ở dòng theo loại giấy."""
    docs = [answers.get(i, {}) for i in range(len(names))]
    items: list[dict] = []
    seen: dict[str, int] = {}
    for group in pair_card_sides(docs):
        first = group[0]
        doc = both_sides(docs[first]) if len(group) > 1 else docs[first]
        doc_type = str(doc.get("docType") or "").strip()
        name = unique_name(_document_name(names[first], _llm_document_name(doc) if doc else ""), seen)
        items.append(item(first, names[first], name, doc_type, file_indexes=group))
    return ordered(items)


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
        except Exception as exc:  # noqa: BLE001 — LLM lỗi → vẫn đính đủ tệp vào dòng 1, giữ tên gốc
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

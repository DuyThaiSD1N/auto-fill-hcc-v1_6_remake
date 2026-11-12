"""Đính kèm khai sinh có yếu tố nước ngoài (2.000528, Cổng DVC quốc gia mới) — chế độ KHÔNG tách giấy tờ.

Bảng thành phần hồ sơ: STT 1 là mẫu hộ tịch điện tử cổng tự sinh từ tờ khai (không đính); 5 dòng có nút "Tải lên
file": giấy chứng sinh / văn bản thay giấy chứng sinh (người làm chứng, cam đoan) / giấy tờ nước ngoài xác nhận việc
sinh ở nước ngoài / văn bản thỏa thuận lựa chọn quốc tịch / văn bản ủy quyền. LLM đọc từng tệp để xếp đúng dòng; giấy
không có dòng riêng (tờ khai giấy, giấy kết hôn, hộ chiếu, giấy tờ tùy thân nước ngoài + bản dịch, kết quả ADN) đính
chung dòng giấy chứng sinh — engine SurveyJS của extension chưa bấm được "Thêm thành phần hồ sơ". LLM lỗi / OCR hụt →
dòng giấy chứng sinh. Khớp dòng theo tên dòng (slotName), slotIndex chỉ là dự phòng.

Tệp trên 2 MB nén bằng thang của cải chính (cùng cổng), trả ở `replaceFiles`; ghép hai mặt CCCD giống 1.001193.
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
    _merge_groups,
    both_sides,
    pair_card_sides,
)
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

ROW_CHUNG_SINH = {"slotKey": "ks_nn_chung_sinh", "slotIndex": 0, "slotName": "Giấy chứng sinh"}
ROWS = {
    "birth_witness": {"slotKey": "ks_nn_thay_chung_sinh", "slotIndex": 1,
                      "slotName": "Trường hợp không có Giấy chứng sinh thì thay thế bằng"},
    "foreign_birth_doc": {"slotKey": "ks_nn_sinh_nuoc_ngoai", "slotIndex": 2,
                          "slotName": "Trường hợp trẻ em sinh ra tại nước ngoài"},
    "nationality_agreement": {"slotKey": "ks_nn_thoa_thuan_quoc_tich", "slotIndex": 3,
                              "slotName": "Trường hợp cha hoặc mẹ hoặc cả cha, mẹ là người nước ngoài"},
    "authorization": {"slotKey": "ks_nn_uy_quyen", "slotIndex": 4,
                      "slotName": "Văn bản ủy quyền (được chứng thực)"},
}


def plan_item(file_index: int, file_name: str, document_name: str, doc_type: str) -> dict:
    row = ROWS.get(doc_type, ROW_CHUNG_SINH)
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": row["slotName"],
        "target": "fixed-slot",
        "needsAddComponent": False,
        "detectedType": doc_type if doc_type in ROWS else "other",
        "noChooserClick": True,
        **row,
    }


def build_plan_items(file_names: list[str], doc_types: dict[int, str],
                     doc_names: dict[int, str] | None = None) -> list[dict]:
    items = []
    seen: dict[str, int] = {}
    for index, name in enumerate(file_names):
        # Hai tệp cùng loại giấy (CCCD hai người, hai bản dịch...) → đánh số để cổng và cán bộ phân biệt được.
        document_name = _document_name(name, (doc_names or {}).get(index, ""))
        seen[document_name.lower()] = seen.get(document_name.lower(), 0) + 1
        if seen[document_name.lower()] > 1:
            document_name = f"{document_name} {seen[document_name.lower()]}"
        items.append(plan_item(index, name, document_name, doc_types.get(index, "")))
    return items


async def _classify_all(texts: dict[int, str]) -> dict[int, dict]:
    """MỘT lượt LLM cho cả hồ sơ; tệp trùng nội dung chỉ gửi một bản rồi dùng chung kết quả (như 1.001193)."""
    first_of: dict[str, int] = {}
    for i, t in texts.items():
        first_of.setdefault(t, i)
    sent = {i: t for t, i in first_of.items()}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt([{"index": i, "text": t[:12000]} for i, t in sent.items()])},
    ]
    raw = await client.chat(messages, max_tokens=_max_tokens(sent), enable_thinking=settings.agent_reasoning)
    answers: dict[int, dict] = {}
    for item in client.extract_json_block(raw).get("documents", []) or []:
        try:
            index = int(item.get("index"))
        except (AttributeError, TypeError, ValueError):
            continue
        if index in sent and index not in answers:
            answers[index] = item
    for i, t in texts.items():
        if i not in answers and first_of[t] in answers:
            answers[i] = answers[first_of[t]]
    return answers


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    from app.services import ocr

    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    errors: list[str] = []
    pairs = [(i, f) for i, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]
    started = time.monotonic()
    shrink_task = asyncio.create_task(shrink_oversized(raw_files, errors))
    ocr_results = await ocr.ocr_per_file([f for _, f in pairs]) if pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    texts = {}
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
        except Exception as exc:  # noqa: BLE001 — LLM lỗi → mọi tệp về dòng giấy chứng sinh, giữ tên gốc
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)
    doc_types = {i: str(a.get("docType") or "").strip() for i, a in answers.items()}
    # Số định danh đọc từ OCR của từng tệp: khoá ghép hai mặt thẻ (họ tên LLM đọc có thể lệch giữa hai mặt).
    for i, a in answers.items():
        a["_soThe"] = so_dinh_danh_the(texts.get(i, ""))
        a["_matTheOcr"] = mat_the(texts.get(i, ""))
        a["chuThe"] = ho_ten_co_dau(a.get("chuThe") or "", texts.get(i, ""))
    doc_names = {i: _llm_document_name(a) for i, a in answers.items()}
    # Hai TỆP là hai mặt thẻ của cùng một người → một mục gộp (extension ghép thành một PDF).
    groups = pair_card_sides([answers.get(i, {}) for i in range(len(raw_files))])
    for group in groups:
        if len(group) > 1:
            doc_names[group[0]] = _llm_document_name(both_sides(answers[group[0]]))

    replace_files = await shrink_task
    names = [replace_files[str(i)]["name"] if str(i) in replace_files else f["name"] for i, f in enumerate(raw_files)]
    attachments = _merge_groups(build_plan_items(names, doc_types, doc_names), groups)
    await shrink_merged(raw_files, attachments, replace_files, errors)
    return {
        "attachments": attachments,
        "replaceFiles": replace_files or None,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "classified": [
                {"fileName": item["fileName"], "docType": item["detectedType"], "slotIndex": item["slotIndex"]}
                for item in attachments
            ],
            "shrunk": [
                {"fileName": r["name"], "originalBytes": r["originalBytes"], "bytes": r["bytes"], "level": r["level"]}
                for r in replace_files.values()
            ],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

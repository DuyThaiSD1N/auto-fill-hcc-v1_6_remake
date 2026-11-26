"""Đính kèm khai tử có yếu tố nước ngoài (1.001766, cổng Bộ Tư pháp) — chế độ KHÔNG tách giấy tờ.

Bước "Thành phần hồ sơ" (theo ảnh ánh xạ đính kèm của BA): STT 1 là mẫu hộ tịch điện tử cổng tự sinh từ eForm (không
đính); STT 2 Giấy báo tử / giấy tờ thay Giấy báo tử; STT 3 giấy tờ chứng minh sự kiện chết cho người chết đã lâu; STT 4
Văn bản ủy quyền. LLM đọc từng tệp để xếp đúng dòng; giấy không có dòng riêng (tờ khai bản giấy, hộ chiếu của người chết,
CCCD người yêu cầu, bản dịch...) → "Thêm thành phần hồ sơ" mới mang tên giấy. Mỗi tệp đính nguyên, không cắt trang.

Số thứ tự + tên dòng lấy từ bảng thật trên trang (`options.attachmentContext.components`, extension gửi kèm); không có
bảng → số thứ tự 2..4 + đoạn tên theo ảnh ánh xạ. Extension khớp dòng theo tên trước, số thứ tự chỉ là gợi ý.
Tệp trên 2 MB nén bằng thang của cải chính, trả ở `replaceFiles`; ghép hai mặt CCCD giống khai sinh 1.001193.
"""

import asyncio
import re
import time
import unicodedata

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

DEATH_NOTICE = "death_notice"
DEATH_PROOF = "death_proof"
AUTHORIZATION = "authorization"
# Loại giấy → dòng có sẵn: số thứ tự mặc định + đoạn tên dòng (extension tìm dòng chứa đoạn này).
ROWS = {
    DEATH_NOTICE: {"componentIndex": 2, "componentName": "Giấy báo tử hoặc giấy tờ thay Giấy báo tử"},
    DEATH_PROOF: {"componentIndex": 3, "componentName": "chứng minh sự kiện chết"},
    AUTHORIZATION: {"componentIndex": 4, "componentName": "Văn bản ủy quyền"},
}
# Nhận dòng trên trang theo chữ đã bỏ dấu; xét theo thứ tự này vì dòng chứng cứ (người chết đã lâu) cũng nhắc "không có
# Giấy báo tử".
_ROW_MARKERS = (
    (AUTHORIZATION, ("uy quyen",)),
    (DEATH_PROOF, ("chung minh su kien chet", "chet da lau")),
    (DEATH_NOTICE, ("giay bao tu",)),
)


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def live_rows(options: dict | None) -> dict[str, dict]:
    """{loại giấy: {componentIndex, componentName}} theo bảng thật trên trang; dòng không thấy giữ mặc định."""
    rows = {key: dict(row) for key, row in ROWS.items()}
    found: set[str] = set()
    components = ((options or {}).get("attachmentContext") or {}).get("components") or []
    for component in components:
        if not isinstance(component, dict):
            continue
        try:
            index = int(component.get("index"))
        except (TypeError, ValueError):
            continue
        name = str(component.get("componentName") or "").strip()
        folded = _fold(name).lstrip("- ")
        # Dòng mẫu hộ tịch điện tử / tờ khai do cổng tự sinh → không phải đích đính kèm.
        if index <= 0 or not folded or folded.startswith(("to khai", "mau ho tich")):
            continue
        doc_type = next((key for key, markers in _ROW_MARKERS if any(m in folded for m in markers)), "")
        if doc_type and doc_type not in found:
            found.add(doc_type)
            rows[doc_type] = {"componentIndex": index, "componentName": name}
    return rows


def plan_item(file_index: int, file_name: str, document_name: str, doc_type: str,
              rows: dict[str, dict] | None = None) -> dict:
    row = (rows or ROWS).get(doc_type)
    item = {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
        "detectedType": doc_type if doc_type in ROWS else "other",
    }
    if row:
        return {**item, "target": "existing", "componentIndex": row["componentIndex"],
                "componentName": row["componentName"], "needsAddComponent": False}
    return {**item, "target": "new", "componentIndex": None, "componentName": document_name,
            "needsAddComponent": True}


def build_plan_items(file_names: list[str], doc_types: dict[int, str],
                     doc_names: dict[int, str] | None = None, rows: dict[str, dict] | None = None) -> list[dict]:
    items = []
    seen: dict[str, int] = {}
    for index, name in enumerate(file_names):
        # Hai tệp cùng loại giấy (CCCD hai người, hai bản dịch...) → đánh số để cổng và cán bộ phân biệt được.
        document_name = _document_name(name, (doc_names or {}).get(index, ""))
        seen[document_name.lower()] = seen.get(document_name.lower(), 0) + 1
        if seen[document_name.lower()] > 1:
            document_name = f"{document_name} {seen[document_name.lower()]}"
        items.append(plan_item(index, name, document_name, doc_types.get(index, ""), rows))
    return items


async def _classify_all(texts: dict[int, str]) -> dict[int, dict]:
    """MỘT lượt LLM cho cả hồ sơ; tệp trùng nội dung chỉ gửi một bản rồi dùng chung kết quả."""
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
        except Exception as exc:  # noqa: BLE001 — LLM lỗi → thành phần mới theo tên gốc
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
    attachments = _merge_groups(build_plan_items(names, doc_types, doc_names, live_rows(options)), groups)
    await shrink_merged(raw_files, attachments, replace_files, errors)
    return {
        "attachments": attachments,
        "replaceFiles": replace_files or None,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "classified": [
                {"fileName": item["fileName"], "docType": item["detectedType"], "target": item["target"],
                 "componentIndex": item["componentIndex"]}
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

"""Đính kèm khai sinh có yếu tố nước ngoài (2.000528, cổng Bộ Tư pháp) — chế độ KHÔNG tách giấy tờ.

Bước "Thành phần hồ sơ" của cổng Bộ Tư pháp: STT 1 là mẫu hộ tịch điện tử sinh từ tờ khai (không đính), các dòng có
sẵn theo danh mục TTHC: giấy chứng sinh / văn bản thay giấy chứng sinh (người làm chứng, cam đoan) / giấy tờ nước
ngoài xác nhận việc sinh ở nước ngoài / văn bản thỏa thuận lựa chọn quốc tịch / văn bản ủy quyền. LLM đọc từng tệp để
xếp đúng dòng; giấy không có dòng riêng (tờ khai giấy, giấy kết hôn, hộ chiếu, CCCD, giấy tờ tùy thân nước ngoài + bản
dịch, kết quả ADN) → "Thêm thành phần hồ sơ" mới mang tên giấy. Hồ sơ không có giấy nào vào dòng Giấy chứng sinh (bắt
buộc) thì giấy "khác" đầu tiên không phải thẻ lên dòng đó, như bản SurveyJS trước đây dồn mọi giấy vào dòng này.

Số thứ tự + tên dòng lấy từ bảng thật trên trang (`options.attachmentContext.components`, extension gửi kèm); không
có bảng → số thứ tự 2..6 + đoạn tên theo danh mục TTHC (SUY, chưa chụp bảng thật của 2.000528). Extension khớp dòng
theo tên trước, số thứ tự chỉ là gợi ý.

Tệp trên 2 MB nén bằng thang của cải chính, trả ở `replaceFiles`; ghép hai mặt CCCD giống 1.001193.
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

BIRTH_CERTIFICATE = "birth_certificate"
# Loại giấy → dòng có sẵn: số thứ tự mặc định + đoạn tên dòng (extension tìm dòng chứa đoạn này).
ROWS = {
    BIRTH_CERTIFICATE: {"componentIndex": 2, "componentName": "Giấy chứng sinh"},
    "birth_witness": {"componentIndex": 3,
                      "componentName": "Trường hợp không có Giấy chứng sinh thì thay thế bằng"},
    "foreign_birth_doc": {"componentIndex": 4, "componentName": "Trường hợp trẻ em sinh ra tại nước ngoài"},
    "nationality_agreement": {"componentIndex": 5,
                              "componentName": "Trường hợp cha hoặc mẹ hoặc cả cha, mẹ là người nước ngoài"},
    "authorization": {"componentIndex": 6, "componentName": "Văn bản ủy quyền"},
}
# Nhận dòng trên trang theo chữ đã bỏ dấu; xét theo thứ tự này vì dòng "không có Giấy chứng sinh thì thay thế" và dòng
# "sinh ra tại nước ngoài thì nộp Giấy chứng sinh" đều chứa chữ "giấy chứng sinh".
_ROW_MARKERS = (
    ("authorization", ("uy quyen",)),
    ("foreign_birth_doc", ("sinh ra tai nuoc ngoai", "sinh ra o nuoc ngoai", "sinh tai nuoc ngoai")),
    ("nationality_agreement", ("quoc tich", "nguoi nuoc ngoai")),
    ("birth_witness", ("thay the", "lam chung", "cam doan")),
    (BIRTH_CERTIFICATE, ("giay chung sinh",)),
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
        folded = _fold(name)
        if index <= 0 or not folded or folded.startswith("to khai"):
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


def promote_birth_row(items: list[dict], cards: set[int], rows: dict[str, dict] | None = None) -> list[dict]:
    """Dòng Giấy chứng sinh bắt buộc: không mục nào vào dòng đó thì mục "khác" đầu tiên không phải thẻ (``cards`` =
    vị trí trong ``items`` của mục là thẻ CCCD / CMND) lên dòng — như bản SurveyJS trước đây dồn giấy vào dòng này."""
    if any(item["detectedType"] == BIRTH_CERTIFICATE for item in items):
        return items
    row = (rows or ROWS)[BIRTH_CERTIFICATE]
    for position, item in enumerate(items):
        if item["target"] == "new" and position not in cards:
            item.update(target="existing", componentIndex=row["componentIndex"], componentName=row["componentName"],
                        needsAddComponent=False)
            break
    return items


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
        except Exception as exc:  # noqa: BLE001 — LLM lỗi → thành phần mới theo tên gốc, tệp đầu lên dòng GCS
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
    rows = live_rows(options)
    card_files = {i for i, a in answers.items() if a.get("matThe") or a.get("_matTheOcr")}
    attachments = _merge_groups(build_plan_items(names, doc_types, doc_names, rows), groups)
    promote_birth_row(attachments, {pos for pos, item in enumerate(attachments) if item["fileIndex"] in card_files},
                      rows)
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

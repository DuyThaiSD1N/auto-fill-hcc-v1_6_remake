"""Đính kèm bước "Thành phần hồ sơ" cho [Lâm Đồng] đăng ký đất đai cấp GCN lần đầu (1.116360).

Cổng Lâm Đồng (Form.io/Angular apply-online) — CÙNG nền tảng đính kèm GPXD/đính chính lamdong.
Mỗi ô "Chọn tệp tin" NHẬN NHIỀU FILE → KHÔNG gộp PDF: phát 1 attachment/file, các file cùng slotKey
được FE (`attachFilesByFixedSlot`) tự gom rồi bơm cả loạt vào đúng ô. Tên hiển thị = tên giấy tờ thật.

⚑ BẢNG ĐÃ ĐỔI (Quyết định 40/2026/QĐ-UBND) — 20 dòng, `slotIndex = STT − 1` (thứ tự DOM của
`input[type=file]`, xem `fixedSlotUploadInputs` trong content.js). Bảng CŨ chỉ có ~17 dòng và Đơn Mẫu 15
nằm ở đầu bảng; nay Đơn xuống gần CUỐI (STT 19) nên mọi slotIndex cũ đều lệch. Bảng hiện tại:

| STT | slotIndex | Dòng dùng tới                                                        |
|-----|-----------|----------------------------------------------------------------------|
| 1   | 0         | Một trong các loại giấy tờ … Điều 137, **khoản 1**, khoản 5 Điều 148… |
| 8   | 7         | Văn bản xác định các thành viên có chung quyền sử dụng đất của hộ GĐ  |
| 14  | 13        | Mảnh trích đo bản đồ địa chính thửa đất                              |
| 16  | 15        | Chứng từ thực hiện nghĩa vụ tài chính                                |
| 18  | 17        | Văn bản về việc **đại diện** … thông qua người đại diện (← Giấy ủy quyền) |
| 19  | 18        | Đơn đăng ký đất đai, tài sản gắn liền với đất, **Mẫu số 15** Phụ lục VI |

⚠ ĐỪNG khớp dòng bằng keyword: text "Một trong các loại giấy tờ quy định tại Điều 137…" lặp ở STT 1 và
STT 12 (chỉ khác "khoản 1" / "khoản 4"), text "Giấy tờ về việc nhận thừa kế…" lặp ở STT 5 và 13. slotKey
của package này CỐ Ý không nằm trong `FIXED_SLOT_KEYWORDS` (content.js) → FE bỏ bước keyword, dùng
thẳng slotIndex. Nhờ vậy sửa được HOÀN TOÀN Ở BACKEND, không phải phát hành lại extension.

Giấy ủy quyền đi vào **STT 18 "Văn bản về việc đại diện theo quy định của pháp luật về dân sự…"** —
KHÔNG chung ô với Đơn, cũng KHÔNG qua nút "+ Thêm giấy tờ": cổng có sẵn dòng dành riêng cho nó.

Phân loại THUẦN LLM (không còn lưới keyword nào — xem prompt.py). Không nhận ra loại → "other" và vẫn
đính vào ô Đơn: tuyệt đối không bỏ sót file nào.
"""
import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import normalize_document_name
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# --- Loại giấy tờ ---
_T_APPLICATION = "application"        # Đơn đăng ký đất đai (Mẫu 15)
_T_IDENTITY = "identity"              # CCCD
_T_AUTHORIZATION = "authorization"    # Giấy ủy quyền
_T_HOUSEHOLD_RIGHTS = "household_rights"  # Văn bản xác định thành viên chung quyền SDĐ / tài sản riêng-chung
_T_BOUNDARY_DESC = "boundary_desc"    # Phụ lục 12 bản mô tả ranh giới, mốc giới
_T_SURVEY_ADJUST = "survey_adjust"    # Mảnh trích đo / mảnh đo đạc chỉnh lý thửa đất
_T_MAP_EXTRACT = "map_extract"        # Trích lục bản đồ địa chính
_T_TAX = "tax_receipt"                # Biên lai thuế/phí
_T_ORIGIN = "origin_doc"              # Giấy tờ nguồn gốc (Điều 137 khoản 1)
_T_OTHER = "other"

_ALLOWED_LLM_TYPES = {
    _T_APPLICATION, _T_IDENTITY, _T_AUTHORIZATION, _T_HOUSEHOLD_RIGHTS,
    _T_BOUNDARY_DESC, _T_SURVEY_ADJUST, _T_MAP_EXTRACT, _T_TAX, _T_ORIGIN,
}

# --- Nhóm (ô upload) trên form ---
_G_ORIGIN = "g_origin"
_G_HOUSEHOLD = "g_household"
_G_SURVEY = "g_survey"
_G_FINANCE = "g_finance"
_G_REPRESENTATION = "g_representation"
_G_APPLICATION = "g_application"

# componentName = text VERBATIM (rút gọn phần đầu, đủ phân biệt) của đúng dòng trên cổng.
_COMP_ORIGIN = (
    "Một trong các loại giấy tờ quy định tại Điều 137, khoản 1, khoản 5 Điều 148, khoản 1, "
    "khoản 5 Điều 149 Luật Đất đai"
)
_COMP_HOUSEHOLD = (
    "Văn bản xác định các thành viên có chung quyền sử dụng đất của hộ gia đình đang sử dụng đất"
)
_COMP_SURVEY = "Mảnh trích đo bản đồ địa chính thửa đất"
_COMP_FINANCE = "Chứng từ thực hiện nghĩa vụ tài chính"
_COMP_REPRESENTATION = (
    "Văn bản về việc đại diện theo quy định của pháp luật về dân sự đối với trường hợp thực hiện "
    "thủ tục đăng ký đất đai, tài sản gắn liền với đất thông qua người đại diện"
)
_COMP_APPLICATION = "Đơn đăng ký đất đai, tài sản gắn liền với đất, Mẫu số 15"

# nhóm → (slotIndex = STT − 1, componentName, nhãn hiển thị nhóm). Xếp theo thứ tự dòng trên form.
_GROUPS: dict[str, dict[str, Any]] = {
    _G_ORIGIN: {"slotIndex": 0, "componentName": _COMP_ORIGIN, "label": "Giấy tờ nguồn gốc sử dụng đất (STT 1)"},
    _G_HOUSEHOLD: {"slotIndex": 7, "componentName": _COMP_HOUSEHOLD, "label": "Văn bản xác định thành viên chung quyền SDĐ (STT 8)"},
    _G_SURVEY: {"slotIndex": 13, "componentName": _COMP_SURVEY, "label": "Mảnh trích đo bản đồ địa chính (STT 14)"},
    _G_FINANCE: {"slotIndex": 15, "componentName": _COMP_FINANCE, "label": "Chứng từ nghĩa vụ tài chính (STT 16)"},
    _G_REPRESENTATION: {"slotIndex": 17, "componentName": _COMP_REPRESENTATION, "label": "Văn bản về việc đại diện / Giấy ủy quyền (STT 18)"},
    _G_APPLICATION: {"slotIndex": 18, "componentName": _COMP_APPLICATION, "label": "Đơn đăng ký đất đai Mẫu 15 (STT 19)"},
}

# loại giấy tờ → nhóm
_TYPE_TO_GROUP = {
    _T_APPLICATION: _G_APPLICATION,
    _T_IDENTITY: _G_APPLICATION,
    _T_AUTHORIZATION: _G_REPRESENTATION,  # cổng có dòng riêng cho văn bản đại diện (STT 18)
    _T_HOUSEHOLD_RIGHTS: _G_HOUSEHOLD,
    _T_BOUNDARY_DESC: _G_SURVEY,
    _T_SURVEY_ADJUST: _G_SURVEY,
    _T_MAP_EXTRACT: _G_SURVEY,
    _T_TAX: _G_FINANCE,
    _T_ORIGIN: _G_ORIGIN,
    _T_OTHER: _G_APPLICATION,  # không rõ → "Tài liệu khác" đính vào ô Đơn, KHÔNG bỏ sót
}

# thứ tự ưu tiên khi nhiều file vào cùng 1 ô (số nhỏ lên trước)
_TYPE_PRIORITY = {
    _T_APPLICATION: 10, _T_IDENTITY: 20, _T_OTHER: 90,
    _T_AUTHORIZATION: 10,
    _T_HOUSEHOLD_RIGHTS: 10,
    _T_SURVEY_ADJUST: 10, _T_MAP_EXTRACT: 20, _T_BOUNDARY_DESC: 30,
    _T_TAX: 10,
    _T_ORIGIN: 10,
}

_LABELS = {
    _T_APPLICATION: "Đơn đăng ký đất đai Mẫu 15",
    _T_IDENTITY: "Căn cước công dân",
    _T_AUTHORIZATION: "Giấy ủy quyền",
    _T_HOUSEHOLD_RIGHTS: "Văn bản xác định quyền sử dụng đất của hộ gia đình",
    _T_BOUNDARY_DESC: "Bản mô tả ranh giới, mốc giới thửa đất",
    _T_SURVEY_ADJUST: "Mảnh trích đo bản đồ địa chính thửa đất",
    _T_MAP_EXTRACT: "Trích lục bản đồ địa chính",
    _T_TAX: "Biên lai thực hiện nghĩa vụ tài chính",
    _T_ORIGIN: "Giấy tờ chứng minh nguồn gốc sử dụng đất",
    _T_OTHER: "Tài liệu khác",
}


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[:limit] + "..."


def _canonical_type(value: str) -> str:
    raw = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    return raw if raw in _ALLOWED_LLM_TYPES else _T_OTHER


def _label_for_type(doc_type: str, title: str = "", file_name: str = "") -> str:
    """Tên hiển thị trong kế hoạch/trace (FE upload vẫn dùng tên file GỐC ở nhánh fixed-slot)."""
    title = normalize_document_name(title, "") if title else ""
    if doc_type == _T_OTHER:
        # Ghi rõ là tài liệu KHÔNG nhận ra loại để cán bộ soát lại đúng file nào.
        return f"Tài liệu khác - {title or file_name}".strip(" -")
    if title and doc_type != _T_IDENTITY:
        return title
    return _LABELS.get(doc_type, _LABELS[_T_OTHER])


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
    if not documents:
        return {}
    docs = [{"index": item["index"], "text": _truncate_text(item.get("text", ""))} for item in documents]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(docs)},
    ]
    raw = await client.chat(messages, max_tokens=800, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    parsed_docs = parsed.get("documents", []) or []

    def _coerce(item: dict) -> dict[str, str]:
        return {
            "type": _canonical_type(str(item.get("type") or "")),
            "documentName": str(item.get("documentName") or "").strip(),
        }

    out: dict[int, dict[str, str]] = {}
    # Đủ số phần tử → map theo THỨ TỰ MẢNG, không tin field "index" LLM tự đánh (hay lệch 1 nhịp).
    if len(parsed_docs) == len(documents):
        for pos, item in enumerate(parsed_docs):
            out[documents[pos]["index"]] = _coerce(item)
        return out
    raw_items: list[tuple[int, dict]] = []
    for item in parsed_docs:
        try:
            raw_items.append((int(item.get("index")), item))
        except Exception:  # noqa: BLE001
            continue
    offset = 0 if any(r == 0 for r, _ in raw_items) else 1
    valid = {d["index"] for d in documents}
    for r, item in raw_items:
        idx = r - offset
        if idx in valid:
            out[idx] = _coerce(item)
    return out


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, dict[str, str]] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    _ = ocr_results  # OCR chỉ để nuôi LLM; planner KHÔNG tự đọc text để đoán loại.
    llm_types = llm_types or {}
    resolved: list[dict] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        detected = llm_types.get(idx) or {}
        # THUẦN LLM: không có lưới keyword nào tham gia quyết định. LLM im lặng/lỗi → "other" và file
        # vẫn được đính (vào ô Đơn) kèm cảnh báo, thay vì bị bỏ rơi.
        doc_type = _canonical_type(detected.get("type") or "")
        resolved.append({
            "idx": idx, "fileName": file_name, "docType": doc_type,
            "title": detected.get("documentName", ""),
            "source": "llm" if idx in llm_types else "default",
        })

    groups: dict[str, list[dict]] = {g: [] for g in _GROUPS}
    for entry in resolved:
        groups[_TYPE_TO_GROUP.get(entry["docType"], _G_APPLICATION)].append(entry)

    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    def _emit(entry: dict, group_key: str) -> None:
        meta = _GROUPS[group_key]
        document_name = _label_for_type(entry["docType"], entry.get("title", ""), entry["fileName"])
        attachments.append({
            "fileIndex": entry["idx"],
            "sourceFileIndexes": [entry["idx"]],   # chỉ chính nó → FE KHÔNG gộp PDF
            "fileName": entry["fileName"],
            "documentName": document_name,
            "componentName": meta["componentName"],
            "target": "fixed-slot",
            "needsAddComponent": False,
            "detectedType": document_name,
            "slotKey": group_key,
            "slotIndex": meta["slotIndex"],
            "slotName": meta["componentName"],
        })
        classified.append({
            "fileName": entry["fileName"], "docType": entry["docType"],
            "documentName": document_name,
            "group": group_key, "slotIndex": meta["slotIndex"], "source": entry["source"],
        })

    for group_key in _GROUPS:
        for entry in sorted(groups[group_key], key=lambda e: (_TYPE_PRIORITY.get(e["docType"], 99), e["idx"])):
            _emit(entry, group_key)

    # LƯỚI AN TOÀN cuối hàm: mọi file đều phải có mặt trong kế hoạch (kể cả khi logic phía trên đổi).
    planned = {item["fileIndex"] for item in attachments}
    for entry in resolved:
        if entry["idx"] not in planned:
            _emit(entry, _G_APPLICATION)

    unknown = [e["fileName"] for e in resolved if e["docType"] == _T_OTHER]
    if unknown:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã tạm đính vào ô Đơn đăng ký (STT 19) để không bỏ sót — "
            f"cán bộ kiểm tra lại: {', '.join(unknown)}."
        )
    if not attachments:
        warnings.append("Không có tài liệu nào để đính kèm.")
    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options or {}
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]

    from app.services import ocr

    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for r in ocr_results:
        if r.get("error"):
            errors.append(f"OCR {r.get('name')}: {r['error']}")

    ocr_by_name = {r.get("name"): r for r in ocr_results}
    llm_docs = [
        {"index": idx, "text": str(ocr_by_name.get(file.get("name"), {}).get("text") or "")}
        for idx, file in enumerate(raw_files)
    ]

    t1 = time.monotonic()
    llm_types: dict[int, dict[str, str]] = {}
    if any(d["text"].strip() for d in llm_docs):
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as e:  # noqa: BLE001
            errors.append(f"attachment_agent: {e}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types)
    errors.extend(warnings)

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [f["name"] for f in raw_files],
            "sessionId": (session or {}).get("request_id"),
            "classified": classified,
            "groups": [{"slotKey": k, **v} for k, v in _GROUPS.items()],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

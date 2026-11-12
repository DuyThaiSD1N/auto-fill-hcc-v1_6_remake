"""Đính kèm cho "Đăng ký tham dự kiểm tra kết quả tập sự hành nghề công chứng" (mã TTHC 1.013818).

Thủ tục chỉ có bước đính kèm. Bảng "Thành phần hồ sơ" trên cổng (wizard tư pháp DVCQG) có 3 dòng cố định:
  1. Bản chính/bản sao có chứng thực/bản sao điện tử Quyết định công nhận hoàn thành tập sự      → decision
  2. Bản chính/bản sao có chứng thực/bản sao điện tử giấy tờ chứng minh đã nộp phí thẩm định tiêu
     chuẩn, điều kiện hành nghề công chứng                                                        → fee_receipt
  3. Giấy đăng ký tham dự kiểm tra kết quả tập sự hành nghề công chứng (Mẫu TP-TSCC-10) — dòng tờ khai điện tử: cổng
     tự gắn "Tờ khai.pdf" từ bước Kê khai, không có nút chọn tệp → planner không xếp file vào dòng này.

Giấy đăng ký đã ký tải lên → "Thêm thành phần hồ sơ" (giữ đủ file, không đẩy vào dòng 3 mà engine không đính được).

Mỗi file đính NGUYÊN KHỐI, không tách trang. Nhiều file cùng một dòng thì gộp một PDF (``sourceFileIndexes``, theo thứ
tự tải lên). Một file chứa nhiều giấy (vd Giấy đăng ký kèm biên lai) thuộc dòng của giấy CHÍNH (tiêu đề xuất hiện sớm
nhất); dòng nào không có file riêng mà nằm trong file gộp đó thì đính thêm chính file đó vào dòng ấy. Căn cước / giấy
khác → "Thêm thành phần hồ sơ" (như thủ tục luật sư cùng cổng); không bỏ file nào. Dòng không có giấy → để trống +
cảnh báo cần bổ sung.

Phân loại: tiêu đề giấy (rule) trước; file rule không nhận ra mới hỏi LLM, LLM lỗi thì rule căn cước / other.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold
from app.pipelines._shared.compact_agent.runner import _extract_docx_text, _is_docx
from app.pipelines._shared.identity_merge import _looks_like_cccd
from app.pipelines.xac_nhan_thong_tin_ho_tich.attach.planner import _coerce_int, _unique_document_name
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

DECISION = "decision"
FEE_RECEIPT = "fee_receipt"
REGISTRATION = "registration"
IDENTITY = "identity"
OTHER = "other"
_ALLOWED_TYPES = {DECISION, FEE_RECEIPT, REGISTRATION, IDENTITY, OTHER}

# (STT dòng trên cổng, loại giấy, đoạn chữ RIÊNG của dòng để FE khớp, tên tài liệu đính vào dòng).
# Dòng 1 và 2 cùng mở đầu "Bản chính hoặc bản sao có chứng thực hoặc bản sao điện tử…" → componentName lấy đoạn sau
# (FE khớp chứa-trong sau khi fold), không lấy chữ đầu dòng.
ROWS: tuple[tuple[int, str, str, str], ...] = (
    (1, DECISION, "Quyết định công nhận hoàn thành tập sự", "Quyết định công nhận hoàn thành tập sự"),
    (2, FEE_RECEIPT, "giấy tờ chứng minh đã nộp phí thẩm định tiêu chuẩn",
     "Chứng từ nộp phí thẩm định hành nghề công chứng"),
)
_ROW_TYPES = {doc_type for _, doc_type, _, _ in ROWS}

# Câu báo thiếu theo đúng chữ trên bảng thành phần hồ sơ.
_MISSING = {
    DECISION: "Quyết định công nhận hoàn thành tập sự hành nghề công chứng",
    FEE_RECEIPT: "giấy tờ chứng minh đã nộp phí thẩm định tiêu chuẩn, điều kiện hành nghề công chứng",
}

_EXTRA_LABELS = {
    REGISTRATION: "Giấy đăng ký tham dự kiểm tra kết quả tập sự đã ký",
    IDENTITY: "Căn cước công dân",
    OTHER: "Tài liệu khác",
}

# Tiêu đề giấy (đã fold, bỏ dấu câu). Giấy đăng ký có câu "Đã được công nhận hoàn thành tập sự theo quyết định số …"
# — không chứa cụm "quyet dinh cong nhan hoan thanh tap su" nên không bị nhận nhầm thành Quyết định.
_TITLE_MARKERS: dict[str, tuple[str, ...]] = {
    REGISTRATION: (
        "giay dang ky tham du kiem tra ket qua tap su",
        "tp tscc 10",
    ),
    DECISION: (
        "quyet dinh cong nhan hoan thanh tap su",
        "dieu 1 cong nhan hoan thanh tap su",
    ),
    FEE_RECEIPT: (
        "phi tham dinh tieu chuan dieu kien hanh nghe cong chung",
        "bien lai thu phi",
        "bien lai thu tien phi",
        "bien lai dien tu",
        "giay nop tien vao ngan sach",
        "uy nhiem chi",
        "chuyen tien thanh cong",
        "chuyen khoan thanh cong",
        "giao dich thanh cong",
    ),
}


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", fold(text or "")).strip()


def rule_types(text: str) -> list[str]:
    """Các loại giấy có tiêu đề trong file, xếp theo vị trí xuất hiện (giấy chính đứng đầu)."""
    haystack = _norm(text)
    if not haystack:
        return []
    first_hit: dict[str, int] = {}
    for doc_type, markers in _TITLE_MARKERS.items():
        positions = [haystack.find(marker) for marker in markers if marker in haystack]
        if positions:
            first_hit[doc_type] = min(positions)
    return sorted(first_hit, key=first_hit.get)


def _canonical_type(value: Any) -> str:
    raw = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    aliases = {
        "quyet_dinh": DECISION, "decision_document": DECISION,
        "fee": FEE_RECEIPT, "receipt": FEE_RECEIPT, "bien_lai": FEE_RECEIPT, "payment": FEE_RECEIPT,
        "dang_ky": REGISTRATION, "registration_form": REGISTRATION, "giay_dang_ky": REGISTRATION,
        "cccd": IDENTITY, "cmnd": IDENTITY, "id": IDENTITY, "passport": IDENTITY,
    }
    raw = aliases.get(raw, raw)
    return raw if raw in _ALLOWED_TYPES else OTHER


def _validated_classifications(raw_items: list[dict], file_count: int) -> dict[int, dict]:
    result: dict[int, dict] = {}
    for raw in raw_items or []:
        if not isinstance(raw, dict):
            continue
        file_index = _coerce_int(raw.get("fileIndex", raw.get("index")))
        if file_index is None or not 0 <= file_index < file_count or file_index in result:
            continue
        result[file_index] = {
            "type": _canonical_type(raw.get("type") or raw.get("docType")),
            "documentName": str(raw.get("documentName") or raw.get("title") or "").strip(),
        }
    return result


async def _classify_with_llm(documents: list[dict[str, Any]]) -> list[dict]:
    if not documents:
        return []
    raw = await client.chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(documents)},
        ],
        max_tokens=max(600, min(2000, len(documents) * 160)),
        enable_thinking=settings.agent_reasoning,
    )
    parsed = client.extract_json_block(raw)
    return parsed.get("documents", []) if isinstance(parsed, dict) else []


def build_plan_items(
    raw_files: list[dict],
    ocr_text_by_index: dict[int, str],
    llm_by_index: dict[int, dict] | None = None,
) -> tuple[list[dict], list[dict], list[str]]:
    """Dựng kế hoạch đính kèm từ loại giấy đã phân (tách khỏi I/O để test)."""
    llm_by_index = llm_by_index or {}

    def file_name(index: int) -> str:
        return str(raw_files[index].get("name") or f"file-{index + 1}")

    main_type: dict[int, str] = {}
    covers: dict[int, list[str]] = {}
    source: dict[int, str] = {}
    for index in range(len(raw_files)):
        text = ocr_text_by_index.get(index, "")
        found = rule_types(text)
        if found:
            main_type[index], covers[index], source[index] = found[0], found, "rule"
            continue
        llm_item = llm_by_index.get(index)
        if llm_item:
            doc_type, source[index] = llm_item["type"], "llm"
        else:
            doc_type, source[index] = (IDENTITY if _looks_like_cccd(text) else OTHER), "default"
        main_type[index], covers[index] = doc_type, [doc_type]

    used_names: set[str] = set()
    attachments: list[dict] = []
    rows_by_file: dict[int, list[int]] = {index: [] for index in range(len(raw_files))}
    warnings: list[str] = []
    shared_notes: list[str] = []

    for row, doc_type, component, label in ROWS:
        primary = [i for i in range(len(raw_files)) if main_type[i] == doc_type]
        # Không có file riêng → dùng file gộp có chứa giấy này (đính nguyên file, không tách).
        sources = primary or [i for i in range(len(raw_files)) if doc_type in covers[i]]
        if not sources:
            warnings.append(f"Hồ sơ đã gửi không có {_MISSING[doc_type]} (dòng {row}). Cần bổ sung.")
            continue
        if not primary:
            shared_notes.append(f"dòng {row}: " + ", ".join(file_name(i) for i in sources))
        first = sources[0]
        item = {
            "fileIndex": first,
            "fileName": file_name(first),
            "documentName": _unique_document_name(label, used_names, label),
            "componentName": component,
            "target": "existing",
            "componentIndex": row,
            "needsAddComponent": False,
            "detectedType": doc_type,
        }
        if len(sources) > 1:
            item["sourceFileIndexes"] = sources
        attachments.append(item)
        for index in sources:
            rows_by_file[index].append(row)

    extra_files: list[str] = []
    registration_files: list[str] = []
    for index in range(len(raw_files)):
        if main_type[index] in _ROW_TYPES:
            continue
        doc_type = main_type[index]
        fallback = _EXTRA_LABELS[doc_type]
        # Giấy khác: lấy tiêu đề LLM đọc được; căn cước luôn dùng tên chung.
        base = ""
        if doc_type == OTHER:
            base = (llm_by_index.get(index) or {}).get("documentName") or ""
        document_name = _unique_document_name(base or fallback, used_names, fallback)
        attachments.append({
            "fileIndex": index,
            "fileName": file_name(index),
            "documentName": document_name,
            "componentName": document_name,
            "target": "new",
            "componentIndex": None,
            "needsAddComponent": True,
            "detectedType": doc_type,
        })
        (registration_files if doc_type == REGISTRATION else extra_files).append(file_name(index))

    classified = []
    for index in range(len(raw_files)):
        rows = rows_by_file[index]
        classified.append({
            "fileIndex": index,
            "fileName": file_name(index),
            "type": main_type[index],
            "covers": covers[index],
            "source": source[index],
            "target": "existing" if rows else "new",
            "componentIndex": rows[0] if rows else None,
            "componentIndexes": rows,
        })

    if shared_notes:
        warnings.append(
            "File chứa nhiều giấy được đính nguyên file vào cả dòng không có file riêng — "
            + "; ".join(shared_notes) + "."
        )
    if registration_files:
        warnings.append(
            "Dòng 3 là tờ khai điện tử do cổng tự sinh nên Giấy đăng ký đã ký được thêm thành phần hồ sơ mới: "
            + ", ".join(registration_files) + "."
        )
    if extra_files:
        warnings.append(
            "Giấy tờ ngoài 3 thành phần hồ sơ đã thêm thành phần hồ sơ mới: " + ", ".join(extra_files) + "."
        )
    return attachments, classified, warnings


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_pairs = [(i, f) for i, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file([f for _, f in ocr_pairs]) if ocr_pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    ocr_by_index = {i: result for (i, _), result in zip(ocr_pairs, ocr_results)}
    for i, result in ocr_by_index.items():
        if result.get("error"):
            errors.append(f"OCR fileIndex={i} {raw_files[i].get('name')}: {result['error']}")
    ocr_text_by_index = {i: str((ocr_by_index.get(i) or {}).get("text") or "") for i in range(len(raw_files))}
    for i, f in enumerate(raw_files):
        if _is_docx(f) and not ocr_text_by_index[i]:
            ocr_text_by_index[i] = str(_extract_docx_text(f).get("text") or "")

    # Chỉ hỏi LLM những file tiêu đề không nhận ra — hồ sơ đúng mẫu thì không tốn lượt gọi.
    llm_docs = [
        {"fileIndex": i, "ocrText": ocr_text_by_index[i]}
        for i in range(len(raw_files))
        if not rule_types(ocr_text_by_index[i])
    ]
    started = time.monotonic()
    raw_classifications: list[dict] = []
    if llm_docs:
        try:
            raw_classifications = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001 - rule dự phòng vẫn giữ đủ file
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    llm_indexes = {doc["fileIndex"] for doc in llm_docs}
    llm_by_index = {
        i: item for i, item in _validated_classifications(raw_classifications, len(raw_files)).items()
        if i in llm_indexes
    }
    attachments, classified, warnings = build_plan_items(raw_files, ocr_text_by_index, llm_by_index)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [raw_files[i].get("name") for i, r in ocr_by_index.items() if r.get("text")],
            "llmDocuments": [raw_files[doc["fileIndex"]]["name"] for doc in llm_docs],
            "sessionId": (session or {}).get("request_id"),
            "attachmentMode": "preserve_files",
            "classified": classified,
            "skippedOcr": [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES and not _is_docx(f)],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

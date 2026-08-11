"""Đính kèm cho thủ tục Chứng thực chữ ký — TÁCH RIÊNG khỏi chứng thực bản sao.

Form chứng thực chữ ký có 2 thành phần hồ sơ CỐ ĐỊNH:
  - STT1: Giấy tờ, văn bản cần chứng thực chữ ký (+ bản dịch nếu có).
  - STT2: Giấy tùy thân (Căn cước điện tử / Thẻ CCCD / Căn cước / Hộ chiếu / giấy tờ XNC...).

Quy tắc định tuyến (khác hẳn bản sao — bản sao chỉ có 1 ô có sẵn):
  - File KHÔNG phải giấy tùy thân → STT1: cái đầu vào ô có sẵn #1, các cái sau → thành phần mới.
  - File LÀ giấy tùy thân        → STT2: cái đầu vào ô có sẵn #2, các cái sau (≥2) → thành phần mới.
  - TUYỆT ĐỐI không để giấy tùy thân vào ô #1.

Phân loại/OCR/LLM dùng lại helper của chung_thuc_ban_sao (thuần nhận dạng loại giấy tờ);
chỉ RIÊNG logic xếp ô (build_plan_items) là của thủ tục này.
"""
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import normalize_document_name
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines._shared.naming import GENERIC_DOCUMENT_TYPE as _GENERIC_DOCUMENT_TYPE
from app.pipelines.chung_thuc_ban_sao.attach.planner import (
    _coerce_llm_document_info,
    _unique_document_name,
    detect_document_type,
)
from app.pipelines.chung_thuc_chu_ky.attach import prompt as chu_ky_prompt
from app.process.schemas import FileItem

# Tên 2 ô cố định — đặt bằng đoạn text CÓ trong dòng tương ứng trên form để extension
# khớp ô theo componentTextMatches (rowText.includes(want)).
SIGNATURE_DOC_COMPONENT = "Giấy tờ, văn bản mà mình sẽ yêu cầu chứng thực chữ ký"
IDENTITY_COMPONENT = (
    "Một trong các giấy tờ sau: Căn cước điện tử; bản chính hoặc bản sao của Thẻ căn cước "
    "công dân hoặc Thẻ căn cước hoặc Giấy chứng nhận căn cước hoặc Hộ chiếu"
)

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# Từ khóa giấy tùy thân — CHỈ dùng khi classifier CHƯA xác định được loại (detected generic/rỗng).
# KHÔNG dò từ khóa khi đã biết loại: văn bản ủy quyền / khai sinh / kết hôn... hay chứa số CCCD của
# đương sự → nếu dò sẽ nhận nhầm thành giấy tùy thân (đúng bẫy prompt LLM đã cảnh báo).
_IDENTITY_KEYWORDS_FOLDED = (
    "can cuoc cong dan",
    "the can cuoc",
    "can cuoc dien tu",
    "giay chung nhan can cuoc",
    "cccd",
    "chung minh nhan dan",
    "ho chieu",
    "passport",
    "giay thong hanh",
    "xuat nhap canh",
    "giay to co gia tri di lai quoc te",
)


def _is_identity(detected: str, ocr_text: str, file_name: str) -> bool:
    """Có phải giấy tùy thân (route STT2) không.

    Ưu tiên TIN classifier: detected == "Căn cước công dân" → tùy thân; detected là loại KHÁC đã
    xác định (ủy quyền, khai sinh, kết hôn, hợp đồng...) → KHÔNG phải, kể cả khi text nhắc CCCD.
    Chỉ khi detected generic/rỗng mới dò từ khóa (bắt Hộ chiếu/XNC — không nằm trong taxonomy LLM).
    """
    if detected == "Căn cước công dân":
        return True
    if detected and detected != _GENERIC_DOCUMENT_TYPE:
        return False
    haystack = _fold((ocr_text or "") + "\n" + (file_name or ""))
    return any(kw in haystack for kw in _IDENTITY_KEYWORDS_FOLDED)


# --- Gộp MỌI giấy tùy thân thành 1 PDF vào ô STT2 ---
# Form chứng thực chữ ký chỉ có DUY NHẤT 1 ô giấy tùy thân (STT2). Dù có nhiều CCCD / nhiều mặt /
# nhiều người (vd người yêu cầu + người làm chứng/ủy quyền), TẤT CẢ phải gộp thành 1 PDF theo THỨ TỰ
# file gốc rồi đính vào ô đó — KHÔNG tách mặt trước hay người thứ 2 sang thành phần mới. (Không gom
# theo số định danh nữa: mặt sau chỉ có MRZ nên số 12 chữ số hay rỗng → gom theo người rất dễ nhầm.)


def build_plan_items(
    files: list[dict], ocr_results: list[dict], llm_types: dict[int, Any] | None = None
) -> list[dict]:
    llm_types = llm_types or {}
    by_name = {item.get("name"): item for item in ocr_results}

    # 1) Nhận dạng loại + giấy tùy thân? cho từng file (giữ thứ tự gốc).
    docs: list[dict] = []
    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        ocr_item = by_name.get(file_name, {})
        ocr_text = str(ocr_item.get("text") or "")

        llm_info = _coerce_llm_document_info(llm_types[idx]) if idx in llm_types else {"detectedType": "", "documentName": ""}
        llm_detected = llm_info["detectedType"]
        rule_detected = detect_document_type(ocr_text, file_name)
        # ƯU TIÊN LLM hơn rule: LLM đọc toàn văn OCR nên ít nhầm hơn rule keyword → LLM trả gì
        # dùng nấy; chỉ khi LLM trống mới dùng rule; cả hai trống → generic.
        detected = llm_detected or rule_detected or _GENERIC_DOCUMENT_TYPE

        docs.append({
            "index": idx,
            "fileName": file_name,
            "detectedType": detected,
            "documentName": llm_info["documentName"] or normalize_document_name(file_name, detected),
            "componentBaseName": llm_info["documentName"] or detected,
            "isIdentity": _is_identity(detected, ocr_text, file_name),
        })

    # 2) Chia 2 nhóm, GIỮ THỨ TỰ: giấy tờ (STT1) và giấy tùy thân (STT2).
    doc_bucket = [d for d in docs if not d["isIdentity"]]
    id_bucket = [d for d in docs if d["isIdentity"]]

    used_document_names: set[str] = set()
    used_component_names: set[str] = set()
    items: list[dict] = []

    def _emit_unit(unit: list[dict], *, existing_index: int | None, existing_component: str) -> None:
        """Một đơn vị đính kèm. unit>1 file → FE gộp thành 1 PDF (sourceFileIndexes, mặt trước→sau).
        Tên tài liệu/thành phần lấy theo file ĐẦU unit (mặt trước, thường có tiêu đề rõ)."""
        primary = unit[0]
        source_indexes = [d["index"] for d in unit]
        document_name = _unique_document_name(
            primary.get("documentName") or primary["detectedType"], used_document_names, primary["detectedType"]
        )
        if existing_index is not None:
            component_name = existing_component
            target = "existing"
            component_index: int | None = existing_index
            needs_add = False
        else:
            base = primary.get("componentBaseName") or document_name
            if _fold(base) == _fold(_GENERIC_DOCUMENT_TYPE):
                # OCR trống/không phân loại được → base = "Tài liệu chứng thực" cho MỌI file. Đánh số tên
                # THÀNH PHẦN bằng bộ đếm RIÊNG sẽ lệch pha với documentName và sinh tên trần "Tài liệu
                # chứng thực" — bị FE (khớp substring 2 chiều ở attachmentKeyMatches) coi là trùng của
                # "Tài liệu chứng thực 2/3…" nên bỏ sót file. Dùng THẲNG documentName đã đánh số duy nhất.
                component_name = document_name
                used_component_names.add(_fold(component_name))
            else:
                component_name = _unique_document_name(
                    base, used_component_names, primary["detectedType"]
                )
            target = "new"
            component_index = None
            needs_add = True
        item = {
            "fileIndex": primary["index"],
            "fileName": primary["fileName"],
            "documentName": document_name,
            "componentName": component_name,
            "target": target,
            "componentIndex": component_index,
            "needsAddComponent": needs_add,
            "detectedType": primary["detectedType"],
        }
        # CHỈ gắn khi >1 để không đổi hành vi file lẻ (FE coi thiếu field = [fileIndex]).
        if len(source_indexes) > 1:
            item["sourceFileIndexes"] = source_indexes
        items.append(item)

    # STT1: mỗi giấy tờ 1 đơn vị (không gộp). Cái đầu → ô #1, còn lại → thành phần mới.
    for pos, doc in enumerate(doc_bucket):
        _emit_unit([doc], existing_index=1 if pos == 0 else None, existing_component=SIGNATURE_DOC_COMPONENT)
    # STT2: GỘP TẤT CẢ giấy tùy thân (mọi CCCD/mọi mặt/mọi người) → 1 PDF DUY NHẤT theo thứ tự file
    # gốc, đính vào ô #2 có sẵn. Form chỉ 1 ô giấy tùy thân → không tách thành phần mới cho CCCD.
    if id_bucket:
        _emit_unit(id_bucket, existing_index=2, existing_component=IDENTITY_COMPONENT)

    # Sắp: ô có sẵn trước (theo componentIndex), rồi tới thành phần mới — theo fileIndex cho ổn định.
    items.sort(key=lambda it: (
        0 if it["target"] == "existing" else 1,
        it["componentIndex"] or 0,
        it["fileIndex"],
    ))
    return items


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    """Entry point đính kèm cho chung-thuc-chu-ky (gọi qua registry.get_attach_pipeline)."""
    _ = session
    _ = options or {}
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]

    from app.services import attach_classify

    t0 = time.monotonic()
    # OCR cho phân loại: cắt 2 trang đầu + provider tiengnoi (thử nghiệm) / fallback raw — module riêng.
    ocr_results = await attach_classify.ocr_for_classify(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for r in ocr_results:
        if r.get("error"):
            errors.append(f"OCR {r.get('name')}: {r['error']}")

    ocr_by_name = {r.get("name"): r for r in ocr_results}
    llm_docs: list[dict[str, Any]] = []
    for idx, f in enumerate(raw_files):
        text = str(ocr_by_name.get(f.get("name"), {}).get("text") or "")
        if text.strip():
            llm_docs.append({"index": idx, "fileName": f.get("name"), "text": text})

    t1 = time.monotonic()
    llm_types: dict[int, Any] = {}
    if llm_docs:
        try:
            # Dùng prompt RIÊNG của chữ ký (đặt tên theo loại/tiêu đề, không lấy tên người);
            # phần OCR nén + map theo thứ tự vẫn do module chung attach_classify lo.
            llm_types = await attach_classify.classify(chu_ky_prompt.SYSTEM_PROMPT, llm_docs)
        except Exception as e:  # noqa: BLE001
            errors.append(f"attachment_agent: {e}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments = build_plan_items(raw_files, ocr_results, llm_types)
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [doc["fileName"] for doc in llm_docs],
            "skippedOcr": skipped_ocr,
        },
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "ocr_text": join_ocr_documents(ocr_results),
        "llm_output": {str(idx): val for idx, val in llm_types.items()},
        "errors": errors,
    }

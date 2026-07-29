"""Đính kèm cho thủ tục Chứng thực bản sao từ bản chính / chứng thực chữ ký.

OCR + LLM phân loại tài liệu rồi lập kế hoạch đính kèm vào ví giấy tờ. Helper đặt tên/fold
dùng chung lấy từ app.pipelines._shared.
"""
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import normalize_document_name
from app.pipelines._shared.naming import GENERIC_DOCUMENT_TYPE as _GENERIC_DOCUMENT_TYPE
from app.pipelines.chung_thuc_ban_sao.attach import prompt
from app.pipelines._shared.documents import join_ocr_documents
from app.process.schemas import FileItem
from app.services import attach_classify

DEFAULT_COPY_CERTIFICATION_COMPONENT = (
    "Bản chính giấy tờ, văn bản làm cơ sở để chứng thực bản sao và bản sao cần chứng thực. "
    "Trường hợp người yêu cầu chứng thực chỉ xuất trình bản chính thì cơ quan, tổ chức tiến hành "
    "chụp từ bản chính để thực hiện chứng thực, trừ trường hợp cơ quan, tổ chức không có phương "
    "tiện để chụp. Bản sao từ bản chính để thực hiện chứng thực phải có đầy đủ các trang đã ghi "
    "thông tin của bản chính."
)

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_IDENTITY_DOCUMENT_TYPES = {"Căn cước công dân"}


def _looks_like_identity_document(haystack: str) -> bool:
    if (
        "can cuoc cong dan" in haystack
        or "the can cuoc" in haystack
        or "cccd" in haystack
        or "chung minh nhan dan" in haystack
    ):
        return True

    # Một số giấy tờ hộ tịch/đất đai cũng có "số định danh cá nhân" của đương sự.
    # Chỉ dùng tín hiệu này khi có thêm các cụm đặc trưng của chính thẻ CCCD.
    if "so dinh danh ca nhan" not in haystack:
        return False
    identity_markers = [
        "co gia tri den",
        "date of expiry",
        "noi thuong tru",
        "place of residence",
        "que quan",
        "place of origin",
        "dac diem nhan dang",
    ]
    return sum(1 for marker in identity_markers if marker in haystack) >= 2


def detect_document_type(text: str, file_name: str = "") -> str:
    haystack = _fold((text or "") + "\n" + (file_name or ""))
    if "quyet dinh" in haystack:
        return "Quyết định"
    if "bien ban" in haystack:
        return "Biên bản"
    if "cong van" in haystack:
        return "Công văn"
    if "to trinh" in haystack:
        return "Tờ trình"
    if "hop dong" in haystack:
        return "Hợp đồng"
    if "van ban uy quyen" in haystack or "giay uy quyen" in haystack:
        return "Văn bản ủy quyền"
    if "don de nghi" in haystack or "don xin" in haystack:
        return "Đơn đề nghị"
    if "xac nhan tinh trang hon nhan" in haystack:
        return "Giấy xác nhận tình trạng hôn nhân"
    if (
        "giay chung nhan ket hon" in haystack
        or ("ket hon" in haystack and ("vo" in haystack or "chong" in haystack or "ben nam" in haystack or "ben nu" in haystack))
    ):
        return "Giấy chứng nhận kết hôn"
    if "giay khai sinh" in haystack or "trich luc khai sinh" in haystack:
        return "Giấy khai sinh"
    if "giay chung sinh" in haystack:
        return "Giấy chứng sinh"
    if "giay bao tu" in haystack or "bao tu" in haystack:
        return "Giấy báo tử"
    if "ban chinh" in haystack and "giay to" in haystack:
        return "Bản chính giấy tờ"
    if (
        "giay chung nhan quyen su dung dat" in haystack
        or "quyen su dung dat" in haystack
        or "cnqsd" in haystack
        or "gcnqsd" in haystack
        or ("thua dat" in haystack and "so vao so" in haystack)
    ):
        return "Giấy chứng nhận quyền sử dụng đất"
    if _looks_like_identity_document(haystack):
        return "Căn cước công dân"
    if "so ho khau" in haystack:
        return "Sổ hộ khẩu"
    if "trich luc" in haystack:
        return "Trích lục hộ tịch"
    return ""


def canonical_document_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "tai lieu chung thuc":
        return _GENERIC_DOCUMENT_TYPE
    if "quyet dinh" in text:
        return "Quyết định"
    if "bien ban" in text:
        return "Biên bản"
    if "cong van" in text:
        return "Công văn"
    if "to trinh" in text:
        return "Tờ trình"
    if "hop dong" in text:
        return "Hợp đồng"
    if "uy quyen" in text:
        return "Văn bản ủy quyền"
    if "don de nghi" in text or "don xin" in text:
        return "Đơn đề nghị"
    if "xac nhan tinh trang hon nhan" in text:
        return "Giấy xác nhận tình trạng hôn nhân"
    if "ket hon" in text:
        return "Giấy chứng nhận kết hôn"
    if "khai sinh" in text:
        return "Giấy khai sinh"
    if "chung sinh" in text:
        return "Giấy chứng sinh"
    if "bao tu" in text:
        return "Giấy báo tử"
    if "quyen su dung dat" in text or "cnqsd" in text or "gcnqsd" in text:
        return "Giấy chứng nhận quyền sử dụng đất"
    if "can cuoc" in text or "cccd" in text or "chung minh nhan dan" in text or text == "cmnd":
        return "Căn cước công dân"
    if "so ho khau" in text:
        return "Sổ hộ khẩu"
    if "trich luc" in text:
        return "Trích lục hộ tịch"
    return normalize_document_name(value, _GENERIC_DOCUMENT_TYPE)


def _coerce_llm_document_info(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        detected = canonical_document_type(str(value.get("detectedType") or value.get("type") or ""))
        raw_name = str(value.get("documentName") or value.get("name") or value.get("title") or "")
        document_name = normalize_document_name(raw_name, detected) if raw_name else ""
        return {"detectedType": detected, "documentName": document_name}

    detected = canonical_document_type(str(value or ""))
    return {"detectedType": detected, "documentName": ""}


def _unique_document_name(base: str, used: set[str], fallback: str) -> str:
    normalized = normalize_document_name(base, fallback)
    key = _fold(normalized)
    if key and key not in used:
        used.add(key)
        return normalized

    stem = normalized[:45].strip() or fallback[:45].strip() or _GENERIC_DOCUMENT_TYPE
    n = 2
    while True:
        candidate = f"{stem} {n}"[:50].strip()
        key = _fold(candidate)
        if key not in used:
            used.add(key)
            return candidate
        n += 1


async def _classify_documents_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
    # OCR nén + output {"d":[{t,n}]} + map THEO THỨ TỰ do module chung attach_classify lo (dùng chung
    # cho cả chứng thực bản sao & chữ ky). Trả {index: {detectedType, documentName}}, planner
    # tự chuẩn hóa tiếp qua _coerce_llm_document_info khi build_plan_items.
    return await attach_classify.classify(prompt.SYSTEM_PROMPT, documents)


def _select_primary_index(detected_by_index: dict[int, str], count: int) -> int:
    if count <= 1:
        return 0
    for idx in range(count):
        detected = detected_by_index.get(idx) or ""
        if detected and detected not in _IDENTITY_DOCUMENT_TYPES and detected != "Tài liệu chứng thực":
            return idx
    for idx in range(count):
        detected = detected_by_index.get(idx) or ""
        if detected and detected not in _IDENTITY_DOCUMENT_TYPES:
            return idx
    return 0


def build_plan_items(files: list[dict], ocr_results: list[dict], llm_types: dict[int, Any] | None = None) -> list[dict]:
    llm_types = llm_types or {}
    by_name = {item.get("name"): item for item in ocr_results}
    docs: list[dict] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        ocr_item = by_name.get(file_name, {})
        llm_info = _coerce_llm_document_info(llm_types[idx]) if idx in llm_types else {"detectedType": "", "documentName": ""}
        llm_detected = llm_info["detectedType"]
        rule_detected = detect_document_type(str(ocr_item.get("text") or ""), file_name)
        detected = llm_detected if llm_detected and llm_detected != _GENERIC_DOCUMENT_TYPE else rule_detected
        if not detected and llm_detected:
            detected = llm_detected
        if not detected:
            detected = _GENERIC_DOCUMENT_TYPE

        document_name = llm_info["documentName"] or normalize_document_name(file_name, detected)
        component_base_name = llm_info["documentName"] or detected
        docs.append(
            {
                "index": idx,
                "fileName": file_name,
                "detectedType": detected,
                "documentName": document_name,
                "componentBaseName": component_base_name,
            }
        )

    detected_by_index = {doc["index"]: doc["detectedType"] for doc in docs}
    primary_index = _select_primary_index(detected_by_index, len(docs))
    ordered_docs = [doc for doc in docs if doc["index"] == primary_index] + [
        doc for doc in docs if doc["index"] != primary_index
    ]

    used_document_names: set[str] = set()
    used_component_names: set[str] = set()
    items: list[dict] = []
    for doc in ordered_docs:
        idx = doc["index"]
        file_name = doc["fileName"]
        detected = doc["detectedType"]
        document_name = _unique_document_name(doc.get("documentName") or detected, used_document_names, detected)

        if idx == primary_index:
            component_name = DEFAULT_COPY_CERTIFICATION_COMPONENT
            target = "existing"
            component_index = 1
        else:
            component_name = _unique_document_name(
                doc.get("componentBaseName") or document_name,
                used_component_names,
                detected,
            )
            target = "new"
            component_index = None

        items.append(
            {
                "fileIndex": idx,
                "fileName": file_name,
                "documentName": document_name,
                "componentName": component_name,
                "target": target,
                "componentIndex": component_index,
                "needsAddComponent": target == "new",
                "detectedType": detected,
            }
        )

    return items


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    """Entry point đính kèm cho chung-thuc-ban-sao (gọi qua registry.get_attach_pipeline)."""
    _ = session
    _ = options or {}
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]

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
            llm_types = await _classify_documents_with_llm(llm_docs)
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
        # Cho trace (AttachmentPlanResp tự lược 2 field này khỏi HTTP response).
        "ocr_text": join_ocr_documents(ocr_results),
        "llm_output": {str(idx): val for idx, val in llm_types.items()},
        "errors": errors,
    }


# Bí danh tương thích tên cũ (router/shim cũ gọi plan_copy_certification_attachments).
plan_copy_certification_attachments = plan

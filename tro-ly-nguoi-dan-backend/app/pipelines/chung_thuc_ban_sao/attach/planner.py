"""OCR + LLM phân loại khi LẬP KẾ HOẠCH đính kèm Chứng thực bản sao.

Phân loại realtime lúc upload được bỏ qua để nhận tệp nhanh. Chỉ khi người dân chốt đính kèm,
pipeline này mới đọc nội dung và đặt tên từng tài liệu theo core auto-fill-hcc-backend.
"""
import json
import logging
import re
import time
from typing import Any

from app.pipelines._shared import fold, normalize_document_name
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.chung_thuc_ban_sao.attach.prompt import SYSTEM_PROMPT
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client


DEFAULT_COPY_CERTIFICATION_COMPONENT = (
    "Bản chính giấy tờ, văn bản làm cơ sở để chứng thực bản sao và bản sao cần chứng thực. "
    "Trường hợp người yêu cầu chứng thực chỉ xuất trình bản chính thì cơ quan, tổ chức tiến hành "
    "chụp từ bản chính để thực hiện chứng thực, trừ trường hợp cơ quan, tổ chức không có phương "
    "tiện để chụp. Bản sao từ bản chính để thực hiện chứng thực phải có đầy đủ các trang đã ghi "
    "thông tin của bản chính."
)
DOCUMENT_TYPE = "Giấy tờ cần chứng thực bản sao"
GENERIC_DOCUMENT_TYPE = "Tài liệu chứng thực"
_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_IDENTITY_TYPES = {"Căn cước công dân"}
logger = logging.getLogger(__name__)


def _looks_like_identity(text: str) -> bool:
    if any(x in text for x in ("can cuoc cong dan", "the can cuoc", "cccd", "chung minh nhan dan")):
        return True
    if "so dinh danh ca nhan" not in text:
        return False
    markers = ["co gia tri den", "date of expiry", "noi thuong tru", "place of residence",
               "que quan", "place of origin", "dac diem nhan dang"]
    return sum(marker in text for marker in markers) >= 2


def detect_document_type(text: str) -> str:
    """Rule fallback khi LLM lỗi; thứ tự tránh nhận nhầm giấy hộ tịch thành CCCD."""
    value = fold(text or "")
    rules = [
        ("quyet dinh", "Quyết định"),
        ("bien ban", "Biên bản"),
        ("cong van", "Công văn"),
        ("to trinh", "Tờ trình"),
        ("hop dong", "Hợp đồng"),
        ("van ban uy quyen", "Văn bản ủy quyền"),
        ("giay uy quyen", "Văn bản ủy quyền"),
        ("don de nghi", "Đơn đề nghị"),
        ("xac nhan tinh trang hon nhan", "Giấy xác nhận tình trạng hôn nhân"),
        ("giay chung nhan ket hon", "Giấy chứng nhận kết hôn"),
        ("giay khai sinh", "Giấy khai sinh"),
        ("trich luc khai sinh", "Giấy khai sinh"),
        ("giay chung sinh", "Giấy chứng sinh"),
        ("giay bao tu", "Giấy báo tử"),
        ("giay chung nhan quyen su dung dat", "Giấy chứng nhận quyền sử dụng đất"),
        ("quyen su dung dat", "Giấy chứng nhận quyền sử dụng đất"),
        ("so ho khau", "Sổ hộ khẩu"),
        ("trich luc", "Trích lục hộ tịch"),
    ]
    for marker, label in rules:
        if marker in value:
            return label
    if _looks_like_identity(value):
        return "Căn cước công dân"
    return GENERIC_DOCUMENT_TYPE


def canonical_document_type(value: str) -> str:
    text = fold(value or "")
    if not text:
        return GENERIC_DOCUMENT_TYPE
    aliases = [
        ("quyet dinh", "Quyết định"), ("bien ban", "Biên bản"),
        ("cong van", "Công văn"), ("to trinh", "Tờ trình"),
        ("hop dong", "Hợp đồng"), ("uy quyen", "Văn bản ủy quyền"),
        ("don", "Đơn đề nghị"), ("tinh trang hon nhan", "Giấy xác nhận tình trạng hôn nhân"),
        ("ket hon", "Giấy chứng nhận kết hôn"), ("khai sinh", "Giấy khai sinh"),
        ("chung sinh", "Giấy chứng sinh"), ("bao tu", "Giấy báo tử"),
        ("chung tu", "Giấy báo tử"), ("quyen su dung dat", "Giấy chứng nhận quyền sử dụng đất"),
        ("cnqsd", "Giấy chứng nhận quyền sử dụng đất"),
        ("can cuoc", "Căn cước công dân"), ("cccd", "Căn cước công dân"),
        ("chung minh nhan dan", "Căn cước công dân"), ("so ho khau", "Sổ hộ khẩu"),
        ("trich luc", "Trích lục hộ tịch"),
    ]
    for marker, label in aliases:
        if marker in text:
            return label
    return str(value).strip()[:50] or GENERIC_DOCUMENT_TYPE


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
    """Map theo đúng thứ tự OCR, không tin index do LLM tự sinh."""
    if not documents:
        return {}
    compact = [{"text": re.sub(r"\s+", " ", str(d.get("text") or "")).strip()[:1200]}
               for d in documents]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": (
            "DANH SÁCH OCR theo đúng thứ tự:\n"
            f"{json.dumps(compact, ensure_ascii=False)}\n"
            'Trả JSON {"documents":[{"detectedType":"...","documentName":"..."}]} '
            "đúng thứ tự, mỗi đầu vào đúng một phần tử."
        )},
    ]
    raw = await client.chat(messages, max_tokens=600, enable_thinking=False)
    parsed = client.extract_json_block(raw)
    values = parsed.get("documents") or parsed.get("d") or []
    out: dict[int, dict[str, str]] = {}
    for position, item in enumerate(values[:len(documents)]):
        detected = item.get("detectedType") or item.get("t") or ""
        name = item.get("documentName") or item.get("n") or ""
        out[documents[position]["index"]] = {
            "detectedType": canonical_document_type(str(detected)),
            "documentName": str(name).strip(),
        }
    return out


def _unique_name(raw: str, used: set[str], fallback: str) -> str:
    base = normalize_document_name(raw, fallback)
    candidate = base
    number = 2
    while fold(candidate) in used:
        suffix = f" {number}"
        candidate = (base[:max(1, 50 - len(suffix))].rstrip() + suffix).strip()
        number += 1
    used.add(fold(candidate))
    return candidate


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict] | None = None,
    llm_results: dict[int, dict[str, str]] | None = None,
) -> list[dict]:
    """Chọn giấy tờ chính vào STT1; tài liệu khác tạo dòng mới với tên LLM cụ thể."""
    ocr_results = ocr_results or []
    llm_results = llm_results or {}
    metadata: list[dict] = []
    for index, file in enumerate(files):
        text = str(ocr_results[index].get("text") or "") if index < len(ocr_results) else ""
        llm_item = llm_results.get(index) or {}
        detected = canonical_document_type(llm_item.get("detectedType") or detect_document_type(text))
        metadata.append({"index": index, "detectedType": detected,
                         "suggestedName": llm_item.get("documentName") or detected})

    primary = next((m for m in metadata
                    if m["detectedType"] not in _IDENTITY_TYPES
                    and m["detectedType"] != GENERIC_DOCUMENT_TYPE), None)
    primary = primary or next((m for m in metadata if m["detectedType"] not in _IDENTITY_TYPES), None)
    primary = primary or (metadata[0] if metadata else None)
    ordered = ([primary] if primary else []) + [m for m in metadata if m is not primary]

    used_names: set[str] = set()
    items: list[dict] = []
    for position, meta in enumerate(ordered):
        index = meta["index"]
        file = files[index]
        document_name = _unique_name(
            meta["suggestedName"] or file.get("name") or "",
            used_names,
            meta["detectedType"] or DOCUMENT_TYPE,
        )
        is_primary = position == 0
        items.append({
            "fileIndex": index,
            "fileName": file.get("name") or f"Tệp {index + 1}",
            "documentName": document_name,
            "detectedType": meta["detectedType"],
            "componentName": DEFAULT_COPY_CERTIFICATION_COMPONENT if is_primary else document_name,
            "target": "existing" if is_primary else "new",
            "componentIndex": 1 if is_primary else None,
            "needsAddComponent": not is_primary,
            "appendOnOccupied": False,
        })
    return items


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    """Chỉ chạy khi chốt đính kèm: OCR → LLM classify → attachment plan."""
    _ = options, session
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_inputs = [f for f in raw_files if f.get("type") in _OCR_TYPES]

    t0 = time.monotonic()
    raw_ocr = await ocr.ocr_per_file(ocr_inputs, provider="raw") if ocr_inputs else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    # `raw` là route logic; khi RAW_BY_GEMINI bật thì engine thực tế là Gemini.
    # Giữ provider từ kết quả OCR để trace không hiển thị nhầm model cấu hình chung.
    ocr_provider = next(
        (str(item.get("provider")) for item in raw_ocr if item.get("provider")),
        ocr.resolved_label("raw"),
    )
    ocr_iter = iter(raw_ocr)
    ocr_results = [next(ocr_iter) if f.get("type") in _OCR_TYPES else {"text": ""} for f in raw_files]

    llm_docs = [{"index": i, "text": r.get("text") or ""}
                for i, r in enumerate(ocr_results) if str(r.get("text") or "").strip()]
    errors: list[str] = []
    llm_results: dict[int, dict[str, str]] = {}
    t1 = time.monotonic()
    if llm_docs:
        try:
            llm_results = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001 — rule fallback vẫn tạo plan để không mất tệp
            logger.warning("LLM phân loại chứng thực bản sao lỗi: %s", exc)
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments = build_plan_items(raw_files, ocr_results, llm_results)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "classifiedDocuments": [raw_files[d["index"]]["name"] for d in llm_docs],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms,
                  "total_latency_ms": ocr_ms + llm_ms},
        "ocr_provider": ocr_provider,
        "ocr_text": join_ocr_documents(ocr_results),
        "llm_output": {str(i): value for i, value in llm_results.items()},
        "errors": errors,
    }

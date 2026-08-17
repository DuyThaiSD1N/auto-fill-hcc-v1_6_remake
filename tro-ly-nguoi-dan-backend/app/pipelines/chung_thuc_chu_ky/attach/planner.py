"""OCR + LLM phân loại khi LẬP KẾ HOẠCH đính kèm Chứng thực CHỮ KÝ.

TỰ CHỨA (không phụ thuộc chung_thuc_ban_sao): vỏ OCR/classify theo khuôn native của repo
(ocr.ocr_per_file provider=raw + _classify_with_llm local), phần định tuyến 2 ô cố định lấy từ core
auto-fill. Form chứng thực chữ ký có 2 thành phần hồ sơ CỐ ĐỊNH:
  - STT1 (componentIndex=1): Giấy tờ, văn bản cần chứng thực chữ ký (mỗi giấy 1 đơn vị).
  - STT2 (componentIndex=2): Giấy tùy thân (CCCD/Căn cước/Hộ chiếu...) — GỘP tất cả thành 1 PDF.
Quy tắc: KHÔNG để giấy tùy thân vào ô #1; giấy tùy thân gộp hết vào ô #2 theo thứ tự file gốc.
"""
import json
import logging
import re
import time
from typing import Any

from app.pipelines._shared import fold, normalize_document_name
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines._shared.naming import GENERIC_DOCUMENT_TYPE
from app.pipelines.chung_thuc_chu_ky.attach.prompt import SYSTEM_PROMPT
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

# Tên 2 ô cố định — đặt bằng đoạn text CÓ trong dòng tương ứng trên form để extension khớp ô theo
# componentTextMatches (rowText.includes(want)).
SIGNATURE_DOC_COMPONENT = "Giấy tờ, văn bản mà mình sẽ yêu cầu chứng thực chữ ký"
IDENTITY_COMPONENT = (
    "Một trong các giấy tờ sau: Căn cước điện tử; bản chính hoặc bản sao của Thẻ căn cước "
    "công dân hoặc Thẻ căn cước hoặc Giấy chứng nhận căn cước hoặc Hộ chiếu"
)
_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_IDENTITY_TYPES = {"Căn cước công dân"}

# Từ khóa giấy tùy thân — CHỈ dùng khi classifier CHƯA xác định được loại (detected generic/rỗng).
# KHÔNG dò từ khóa khi đã biết loại: văn bản ủy quyền / khai sinh / kết hôn... hay chứa số CCCD của
# đương sự → nếu dò sẽ nhận nhầm thành giấy tùy thân (đúng bẫy prompt LLM đã cảnh báo).
_IDENTITY_KEYWORDS_FOLDED = (
    "can cuoc cong dan", "the can cuoc", "can cuoc dien tu", "giay chung nhan can cuoc",
    "cccd", "chung minh nhan dan", "ho chieu", "passport", "giay thong hanh",
    "xuat nhap canh", "giay to co gia tri di lai quoc te",
)
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


def _is_identity(detected: str, ocr_text: str, file_name: str) -> bool:
    """Có phải giấy tùy thân (route STT2) không.

    Ưu tiên TIN classifier: detected == "Căn cước công dân" → tùy thân; detected là loại KHÁC đã xác
    định (ủy quyền, khai sinh, kết hôn, hợp đồng...) → KHÔNG phải, kể cả khi text nhắc CCCD. Chỉ khi
    detected generic/rỗng mới dò từ khóa (bắt Hộ chiếu/XNC — không nằm trong taxonomy LLM).
    """
    if detected in _IDENTITY_TYPES:
        return True
    if detected and detected != GENERIC_DOCUMENT_TYPE:
        return False
    haystack = fold((ocr_text or "") + "\n" + (file_name or ""))
    return any(kw in haystack for kw in _IDENTITY_KEYWORDS_FOLDED)


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
    """STT1 = giấy tờ cần chứng thực; STT2 = giấy tùy thân (gộp mọi CCCD/mọi mặt thành 1 PDF)."""
    ocr_results = ocr_results or []
    llm_results = llm_results or {}

    docs: list[dict] = []
    for index, file in enumerate(files):
        text = str(ocr_results[index].get("text") or "") if index < len(ocr_results) else ""
        llm_item = llm_results.get(index) or {}
        detected = canonical_document_type(llm_item.get("detectedType") or detect_document_type(text))
        suggested = llm_item.get("documentName") or detected
        docs.append({
            "index": index,
            "fileName": file.get("name") or f"Tệp {index + 1}",
            "detectedType": detected,
            "documentName": suggested,
            "componentBaseName": suggested,
            "isIdentity": _is_identity(detected, text, file.get("name") or ""),
        })

    # Chia 2 nhóm, GIỮ THỨ TỰ: giấy tờ (STT1) và giấy tùy thân (STT2).
    doc_bucket = [d for d in docs if not d["isIdentity"]]
    id_bucket = [d for d in docs if d["isIdentity"]]

    used_document_names: set[str] = set()
    used_component_names: set[str] = set()
    items: list[dict] = []

    def _emit_unit(unit: list[dict], *, existing_index: int | None, existing_component: str) -> None:
        """Một đơn vị đính kèm. unit>1 file → FE gộp thành 1 PDF (sourceFileIndexes, theo thứ tự gốc).
        Tên tài liệu/thành phần lấy theo file ĐẦU unit."""
        primary = unit[0]
        source_indexes = [d["index"] for d in unit]
        document_name = _unique_name(
            primary["documentName"] or primary["detectedType"], used_document_names, primary["detectedType"]
        )
        if existing_index is not None:
            component_name = existing_component
            target = "existing"
            component_index: int | None = existing_index
            needs_add = False
        else:
            base = primary.get("componentBaseName") or document_name
            if fold(base) == fold(GENERIC_DOCUMENT_TYPE):
                # OCR trống/không phân loại → base generic cho MỌI file; dùng THẲNG documentName đã
                # đánh số duy nhất để FE không coi là trùng.
                component_name = document_name
                used_component_names.add(fold(component_name))
            else:
                component_name = _unique_name(base, used_component_names, primary["detectedType"])
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
            "appendOnOccupied": False,
            "detectedType": primary["detectedType"],
        }
        if len(source_indexes) > 1:
            item["sourceFileIndexes"] = source_indexes
        items.append(item)

    # STT1: mỗi giấy tờ 1 đơn vị (không gộp). Cái đầu → ô #1, còn lại → thành phần mới.
    for pos, doc in enumerate(doc_bucket):
        _emit_unit([doc], existing_index=1 if pos == 0 else None, existing_component=SIGNATURE_DOC_COMPONENT)
    # STT2: GỘP TẤT CẢ giấy tùy thân (mọi CCCD/mọi mặt/mọi người) → 1 PDF theo thứ tự file gốc, đính
    # vào ô #2 có sẵn. Form chỉ 1 ô giấy tùy thân → không tách thành phần mới cho CCCD.
    if id_bucket:
        _emit_unit(id_bucket, existing_index=2, existing_component=IDENTITY_COMPONENT)

    # Ô có sẵn trước (theo componentIndex), rồi tới thành phần mới — theo fileIndex cho ổn định.
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
    """Chỉ chạy khi chốt đính kèm: OCR → LLM classify → attachment plan (chung-thuc-chu-ky)."""
    _ = options, session
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_inputs = [f for f in raw_files if f.get("type") in _OCR_TYPES]

    t0 = time.monotonic()
    raw_ocr = await ocr.ocr_per_file(ocr_inputs, provider="raw") if ocr_inputs else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
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
            logger.warning("LLM phân loại chứng thực chữ ký lỗi: %s", exc)
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

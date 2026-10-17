"""Đính kèm bước "Thành phần hồ sơ" cho "Cấp Chứng chỉ hành nghề luật sư (miễn đào tạo, miễn tập sự)" (1.000688).

Giữ nguyên file, không tách trang. Bảng thành phần hồ sơ trên cổng:
  1. Bản sao Bằng cử nhân luật/thạc sỹ luật           → bằng (file gộp kèm chứng chỉ nghiệp vụ vẫn giữ nguyên).
  2. Giấy tờ chứng minh được miễn tập sự (K1 Đ16)      → quyết định bổ nhiệm, quyết định xuất ngũ, chứng chỉ nghiệp vụ.
  3. Giấy chứng nhận sức khỏe                          → giấy khám sức khỏe; không có thì để trống + cảnh báo.
  4. Văn bản giải trình, cam kết…                       → văn bản giải trình/cam kết; theo hướng dẫn của bộ phận một cửa
                                                          Phiếu lý lịch tư pháp cũng đính vào dòng này.
  5. Đơn đề nghị (bắt buộc)                            → cổng tự sinh Tờ khai.pdf từ bước Kê khai, KHÔNG đính đè.
Văn bản đề nghị bản giấy đã ký → thêm thành phần mới "Đơn đề nghị cấp Chứng chỉ hành nghề luật sư". CCCD, ủy quyền, giấy không rõ loại → thêm thành phần mới. Nhiều file cùng dòng gộp một PDF
(``sourceFileIndexes``) theo thứ tự tải lên.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.compact_agent.runner import _extract_docx_text, _is_docx
from app.pipelines._shared.identity_merge import _looks_like_cccd
from app.pipelines.xac_nhan_thong_tin_ho_tich.attach.planner import _coerce_int, _unique_document_name
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_ALLOWED_TYPES = {
    "degree", "exemption_proof", "health", "criminal_record", "commitment", "paper_request", "identity",
    "authorization", "other",
}

# (STT dòng trên cổng, chữ đầu dòng để FE khớp, tên tệp gộp).
_ROWS = {
    "degree": (1, "Bản sao Bằng cử nhân luật", "Bằng cử nhân luật"),
    "exemption_proof": (2, "Bản sao giấy tờ chứng minh là người được miễn tập sự hành nghề luật sư",
                        "Giấy tờ chứng minh miễn tập sự"),
    "health": (3, "Giấy chứng nhận sức khoẻ", "Giấy chứng nhận sức khỏe"),
    "row4": (4, "Văn bản giải trình, cam kết về quá trình phấn đấu", "Văn bản giải trình, cam kết"),
}
# Dòng 4 nhận cả văn bản giải trình lẫn Phiếu LLTP (ảnh hướng dẫn của bộ phận một cửa); văn bản cam kết đứng trước.
_ROW4_TYPES = ("commitment", "criminal_record")
# Tên ngắn cho tệp + thành phần mới; tên đầy đủ của dòng 5 quá dài làm tên tệp.
PAPER_REQUEST_NAME = "Đơn đề nghị cấp Chứng chỉ hành nghề luật sư"

_LABELS = {
    "identity": "Căn cước công dân",
    "authorization": "Văn bản ủy quyền",
    "other": "Tài liệu hồ sơ luật sư",
}

_REQUEST_MARKERS = ("van ban de nghi cap chung chi hanh nghe luat su", "don de nghi cap chung chi hanh nghe luat su",
                    "de nghi cap chung chi hanh nghe luat su")
_RECORD_MARKERS = ("phieu ly lich tu phap",)
_HEALTH_MARKERS = ("giay kham suc khoe", "giay chung nhan suc khoe", "ket luan suc khoe")
_COMMITMENT_MARKERS = ("van ban giai trinh", "ban giai trinh", "ban cam ket", "van ban cam ket")
_DEGREE_MARKERS = ("bang tot nghiep", "bang thac sy", "bang thac si", "bang tien sy", "bang tien si", "cu nhan luat")
_EXEMPTION_MARKERS = (
    "bo nhiem", "xuat ngu", "chung chi nghiep vu", "bau tham phan", "phong ham", "nghi huu",
)
_AUTHORIZATION_MARKERS = ("van ban uy quyen", "giay uy quyen", "hop dong uy quyen")


def _rule_doc_type(text: str) -> str:
    """Dự phòng khi LLM lỗi. Văn bản đề nghị và Phiếu LLTP đều nhắc số CCCD nên nhận chúng TRƯỚC thẻ."""
    folded = _fold(text)
    if not folded:
        return "other"
    head = folded[:600]
    if any(m in head for m in _REQUEST_MARKERS) and "toi ten la" in folded:
        return "paper_request"
    if any(m in head for m in _RECORD_MARKERS):
        return "criminal_record"
    if any(m in head for m in _HEALTH_MARKERS):
        return "health"
    if any(m in head for m in _COMMITMENT_MARKERS):
        return "commitment"
    if any(m in head for m in _AUTHORIZATION_MARKERS):
        return "authorization"
    if any(m in folded for m in _DEGREE_MARKERS):
        return "degree"
    if "quyet dinh" in folded and any(m in folded for m in _EXEMPTION_MARKERS):
        return "exemption_proof"
    if any(m in folded for m in _EXEMPTION_MARKERS):
        return "exemption_proof"
    if _looks_like_cccd(text):
        return "identity"
    return "other"


def _canonical_type(value: Any) -> str:
    raw = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    aliases = {
        "cccd": "identity", "cmnd": "identity", "id": "identity", "passport": "identity",
        "bang": "degree", "diploma": "degree", "exemption": "exemption_proof", "decision": "exemption_proof",
        "lltp": "criminal_record", "ly_lich_tu_phap": "criminal_record", "request": "paper_request",
        "don": "paper_request", "uy_quyen": "authorization", "cam_ket": "commitment",
    }
    raw = aliases.get(raw, raw)
    return raw if raw in _ALLOWED_TYPES else "other"


def _validated_classifications(raw_items: list[dict], file_count: int) -> dict[int, dict]:
    result: dict[int, dict] = {}
    for raw in raw_items or []:
        if not isinstance(raw, dict):
            continue
        file_index = _coerce_int(raw.get("fileIndex", raw.get("index")))
        if file_index is None or not 0 <= file_index < file_count or file_index in result:
            continue
        result[file_index] = {
            "type": _canonical_type(raw.get("type")),
            "documentName": str(raw.get("documentName") or "").strip(),
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
        max_tokens=max(600, min(2400, len(documents) * 160)),
        enable_thinking=settings.agent_reasoning,
    )
    parsed = client.extract_json_block(raw)
    return parsed.get("documents", []) if isinstance(parsed, dict) else []


def build_plan_items(
    raw_files: list[dict],
    ocr_text_by_index: dict[int, str],
    llm_by_index: dict[int, dict],
) -> tuple[list[dict], list[dict], list[str]]:
    """Dựng kế hoạch đính kèm từ loại giấy đã phân (tách khỏi I/O để test)."""
    types: dict[int, str] = {}
    for index in range(len(raw_files)):
        llm_item = llm_by_index.get(index)
        types[index] = llm_item["type"] if llm_item else _rule_doc_type(ocr_text_by_index.get(index, ""))

    def file_name(index: int) -> str:
        return str(raw_files[index].get("name") or f"file-{index + 1}")

    groups = {
        "degree": [i for i in types if types[i] == "degree"],
        "exemption_proof": [i for i in types if types[i] == "exemption_proof"],
        "health": [i for i in types if types[i] == "health"],
        "row4": [i for t in _ROW4_TYPES for i in types if types[i] == t],
    }

    attachments: list[dict] = []
    classified: list[dict] = []
    for key, (row, component, merged_name) in _ROWS.items():
        sources = groups[key]
        if not sources:
            continue
        first = sources[0]
        item = {
            "fileIndex": first,
            "fileName": file_name(first),
            # Một file: giữ tên gốc; nhiều file gộp một PDF thì đặt tên theo dòng.
            "documentName": merged_name if len(sources) > 1 else file_name(first),
            "componentName": component,
            "target": "existing",
            "componentIndex": row,
            "needsAddComponent": False,
            "detectedType": merged_name,
        }
        if len(sources) > 1:
            item["sourceFileIndexes"] = sources
        attachments.append(item)
        for index in sources:
            classified.append({
                "fileIndex": index, "fileName": raw_files[index].get("name"), "type": types[index],
                "documentName": item["documentName"], "target": "existing", "componentIndex": row,
            })

    used_names = {_fold(component) for _, component, _ in _ROWS.values()}
    for index in range(len(raw_files)):
        doc_type = types[index]
        if doc_type in ("degree", "exemption_proof", "health", *_ROW4_TYPES):
            continue
        if doc_type == "paper_request":
            base, fallback = PAPER_REQUEST_NAME, PAPER_REQUEST_NAME
        else:
            fallback = _LABELS[doc_type]
            base = (llm_by_index.get(index) or {}).get("documentName") if doc_type == "other" else ""
            base = base or fallback
        document_name = (
            base if doc_type == "paper_request" and _fold(base) not in used_names
            else _unique_document_name(base, used_names, fallback)
        )
        used_names.add(_fold(document_name))
        attachments.append({
            "fileIndex": index,
            "fileName": file_name(index),
            "documentName": document_name,
            "componentName": document_name,
            "target": "new",
            "componentIndex": None,
            "needsAddComponent": True,
            "detectedType": document_name,
        })
        classified.append({
            "fileIndex": index, "fileName": raw_files[index].get("name"), "type": doc_type,
            "documentName": document_name, "target": "new", "componentIndex": None,
        })

    warnings: list[str] = []
    if not groups["degree"]:
        warnings.append("Hồ sơ chưa có bản sao Bằng cử nhân luật/thạc sỹ luật (dòng 1).")
    if not groups["exemption_proof"]:
        warnings.append("Hồ sơ chưa có giấy tờ chứng minh được miễn tập sự hành nghề luật sư (dòng 2).")
    if not groups["health"]:
        warnings.append("Hồ sơ chưa có Giấy chứng nhận sức khỏe — dòng 3 để trống, người đề nghị cần bổ sung.")
    if not any(types[i] == "commitment" for i in types):
        if groups["row4"]:
            warnings.append("Không có văn bản giải trình, cam kết có xác nhận — dòng 4 đính Phiếu lý lịch tư pháp "
                            "theo hướng dẫn.")
        else:
            warnings.append("Hồ sơ chưa có văn bản giải trình, cam kết hoặc Phiếu lý lịch tư pháp (dòng 4).")
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

    started = time.monotonic()
    raw_classifications: list[dict] = []
    documents = [{"fileIndex": i, "ocrText": ocr_text_by_index[i]} for i in range(len(raw_files))]
    if documents:
        try:
            raw_classifications = await _classify_with_llm(documents)
        except Exception as exc:  # noqa: BLE001 - rule dự phòng vẫn giữ đủ file
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, classified, warnings = build_plan_items(
        raw_files, ocr_text_by_index, _validated_classifications(raw_classifications, len(raw_files)),
    )
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [raw_files[i].get("name") for i, r in ocr_by_index.items() if r.get("text")],
            "sessionId": (session or {}).get("request_id"),
            "attachmentMode": "preserve_files",
            "classified": classified,
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

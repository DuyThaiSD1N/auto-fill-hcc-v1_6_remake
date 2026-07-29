"""Đính kèm bước "Thành phần hồ sơ" cho [Lâm Đồng] đăng ký đất đai cấp GCN lần đầu.

Cổng Lâm Đồng (Form.io/Angular apply-online) — CÙNG nền tảng đính kèm GPXD/đính chính lamdong.
KHÁC: mỗi NHÓM gộp NHIỀU file → 1 PDF (FE `applyMergeGroups` theo `sourceFileIndexes`), rồi bơm
file gộp vào TRIGGER ĐẦU của nhóm (khớp theo slotIndex — FE fallback vị trí, không cần sửa extension).

4 nhóm cố định (slotIndex = trigger 'Chọn tệp tin' đầu tiên của nhóm trên form):
  slot 0  "Đơn đăng ký đất đai, tài sản gắn liền với đất" ← Đơn Mẫu 15 + CCCD + Giấy ủy quyền.
  slot 2  "Một trong các loại giấy tờ quy định tại Điều 137, khoản 1, khoản 5..." (hộ gia đình/cá nhân)
          ← Đơn xác nhận nguồn gốc + Giấy xác nhận UBND + Đơn cho đất + Sổ hộ khẩu + Hợp đồng nước +
            Sơ đồ ranh giới + (GCN cũ nếu có).
  slot 9  "Mảnh trích đo bản đồ địa chính thửa đất" ← Phụ lục 12 mô tả ranh giới + Mảnh đo đạc chỉnh lý +
            Trích lục bản đồ địa chính.
  slot 12 "Chứng từ thực hiện nghĩa vụ tài chính..." ← Biên lai thu thuế/phí.
(Bỏ nhóm "Điều 137 khoản 4,5" cho người gốc VN định cư nước ngoài — slot 16.)

Route TẤT ĐỊNH theo nội dung OCR; LLM chỉ đặt documentName hiển thị. File không rõ → nhóm Điều 137
(nhóm "một trong các loại giấy tờ" nguồn gốc — catch-all).
"""
import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import normalize_document_name
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# --- Loại giấy tờ ---
_T_APPLICATION = "application"        # Đơn đăng ký đất đai (Mẫu 15/ĐK)
_T_IDENTITY = "identity"              # CCCD
_T_AUTHORIZATION = "authorization"    # Giấy ủy quyền
_T_BOUNDARY_DESC = "boundary_desc"    # Phụ lục 12 bản mô tả ranh giới, mốc giới
_T_SURVEY_ADJUST = "survey_adjust"    # Mảnh đo đạc chỉnh lý thửa đất
_T_MAP_EXTRACT = "map_extract"        # Trích lục bản đồ địa chính
_T_TAX = "tax_receipt"                # Biên lai thuế/phí
_T_ORIGIN = "origin_doc"              # Giấy tờ nguồn gốc (Điều 137): xác nhận nguồn gốc, UBND, sổ hộ khẩu, hợp đồng nước, sơ đồ ranh giới, GCN...
_T_OTHER = "other"

_ALLOWED_LLM_TYPES = {
    _T_APPLICATION, _T_IDENTITY, _T_AUTHORIZATION, _T_BOUNDARY_DESC,
    _T_SURVEY_ADJUST, _T_MAP_EXTRACT, _T_TAX, _T_ORIGIN,
}
_CONFIDENT_LLM_TYPES = set(_ALLOWED_LLM_TYPES)

# --- Nhóm (component) trên form ---
_G_APPLICATION = "g_application"
_G_ORIGIN = "g_origin"
_G_SURVEY = "g_survey"
_G_FINANCE = "g_finance"

_COMP_APPLICATION = "Đơn đăng ký đất đai, tài sản gắn liền với đất"
_COMP_ORIGIN = "Một trong các loại giấy tờ quy định tại Điều 137, khoản 1"
_COMP_SURVEY = "Mảnh trích đo bản đồ địa chính thửa đất"
_COMP_FINANCE = "Chứng từ thực hiện nghĩa vụ tài chính"

# nhóm → (slotIndex trigger đầu, componentName, nhãn hiển thị nhóm)
_GROUPS: dict[str, dict[str, Any]] = {
    _G_APPLICATION: {"slotIndex": 0, "componentName": _COMP_APPLICATION, "label": "Đơn đăng ký đất đai + CCCD"},
    _G_ORIGIN: {"slotIndex": 2, "componentName": _COMP_ORIGIN, "label": "Giấy tờ nguồn gốc sử dụng đất"},
    _G_SURVEY: {"slotIndex": 9, "componentName": _COMP_SURVEY, "label": "Mảnh trích đo / trích lục bản đồ"},
    _G_FINANCE: {"slotIndex": 12, "componentName": _COMP_FINANCE, "label": "Chứng từ nghĩa vụ tài chính"},
}

# loại giấy tờ → nhóm
_TYPE_TO_GROUP = {
    _T_APPLICATION: _G_APPLICATION,
    _T_IDENTITY: _G_APPLICATION,
    _T_AUTHORIZATION: _G_APPLICATION,
    _T_BOUNDARY_DESC: _G_SURVEY,
    _T_SURVEY_ADJUST: _G_SURVEY,
    _T_MAP_EXTRACT: _G_SURVEY,
    _T_TAX: _G_FINANCE,
    _T_ORIGIN: _G_ORIGIN,
    _T_OTHER: _G_ORIGIN,  # không rõ → nhóm "một trong các loại giấy tờ" (catch-all)
}

# thứ tự ưu tiên khi gộp trong 1 nhóm (số nhỏ lên trước)
_TYPE_PRIORITY = {
    _T_APPLICATION: 10, _T_IDENTITY: 20, _T_AUTHORIZATION: 30,
    _T_BOUNDARY_DESC: 10, _T_SURVEY_ADJUST: 20, _T_MAP_EXTRACT: 30,
    _T_TAX: 10,
    _T_ORIGIN: 10, _T_OTHER: 90,
}

_LABELS = {
    _T_APPLICATION: "Đơn đăng ký đất đai Mẫu 15",
    _T_IDENTITY: "Căn cước công dân",
    _T_AUTHORIZATION: "Giấy ủy quyền",
    _T_BOUNDARY_DESC: "Bản mô tả ranh giới, mốc giới thửa đất",
    _T_SURVEY_ADJUST: "Mảnh đo đạc chỉnh lý thửa đất",
    _T_MAP_EXTRACT: "Trích lục bản đồ địa chính",
    _T_TAX: "Biên lai thực hiện nghĩa vụ tài chính",
    _T_ORIGIN: "Giấy tờ chứng minh nguồn gốc sử dụng đất",
    _T_OTHER: "Giấy tờ kèm theo hồ sơ",
}


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[:limit] + "..."


def _has_any(haystack: str, needles: tuple[str, ...]) -> bool:
    return any(n in haystack for n in needles)


def _canonical_type(value: str) -> str:
    raw = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    return raw if raw in _ALLOWED_LLM_TYPES else _T_OTHER


def _looks_like_identity(h: str) -> bool:
    if _has_any(h, ("can cuoc cong dan", "the can cuoc", "cccd", "chung minh nhan dan", "ho chieu", "citizen identity")):
        return True
    if "so dinh danh ca nhan" not in h:
        return False
    markers = ("co gia tri den", "date of expiry", "noi thuong tru", "place of residence", "que quan", "dac diem nhan dang")
    return sum(1 for m in markers if m in h) >= 2


def _rule_doc_type(ocr_text: str, file_name: str = "") -> str | None:
    """Route TẤT ĐỊNH theo nội dung OCR (+ tên file). None = không rõ."""
    h = _fold((ocr_text or "") + "\n" + (file_name or ""))
    if not h.strip():
        return None
    if _has_any(h, ("giay uy quyen", "van ban uy quyen", "hop dong uy quyen", "ben duoc uy quyen", "nguoi duoc uy quyen")):
        return _T_AUTHORIZATION
    # Chứng từ tài chính: DẤU HIỆU RIÊNG là "biên lai"/"chứng từ nộp" — KHÔNG bắt bare "thuế" vì giấy tờ
    # nguồn gốc cũng bàn về nghĩa vụ thuế của thửa đất (dễ nhận nhầm).
    if _has_any(h, ("bien lai", "chung tu nop tien", "thong bao nop le phi", "thong bao nop thue",
                    "chung tu thu", "le phi truoc ba", "thong bao nop tien")):
        return _T_TAX
    # Đơn ĐĂNG KÝ đất đai (Mẫu 15/ĐK) — tiêu đề bắt đầu bằng "ĐƠN ĐĂNG KÝ". KHÁC "đăng ký biến động"
    # (Mẫu 18) và KHÁC Giấy chứng nhận (bắt đầu "GIẤY CHỨNG NHẬN") → không dùng keyword chung "cấp GCN".
    if _has_any(h, ("don dang ky dat dai", "don dang ky, cap giay chung nhan", "don dang ky cap giay chung nhan", "mau so 15", "15/dk", "mau 15")):
        return _T_APPLICATION
    if _has_any(h, ("trich luc ban do dia chinh", "trich luc thua dat", "trich luc")):
        return _T_MAP_EXTRACT
    if _has_any(h, ("manh do dac chinh ly", "do dac chinh ly thua dat", "manh trich do", "trich do dia chinh")):
        return _T_SURVEY_ADJUST
    if _has_any(h, ("ban mo ta ranh gioi", "mo ta ranh gioi, moc gioi", "phu luc so 12", "moc gioi thua dat")):
        return _T_BOUNDARY_DESC
    # Nguồn gốc sử dụng đất (Điều 137): các giấy xác nhận + sổ hộ khẩu + hợp đồng nước + sơ đồ ranh giới + GCN.
    if _has_any(h, (
        "xac nhan nguon goc", "giay xac nhan cua ubnd", "xac nhan cho dat", "don xin xac nhan",
        "so ho khau", "hop dong dich vu cap nuoc", "cung cap va su dung nuoc", "hop dong nuoc",
        "so do ranh gioi su dung dat", "giay chung nhan quyen su dung dat", "nguon goc su dung dat",
    )):
        return _T_ORIGIN
    if _looks_like_identity(h):
        return _T_IDENTITY
    return None


def _label_for_type(doc_type: str, title: str = "") -> str:
    title = normalize_document_name(title, "") if title else ""
    if title and doc_type not in {_T_IDENTITY}:
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
    llm_types = llm_types or {}
    by_name = {r.get("name"): r for r in ocr_results}
    resolved: list[dict] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        text = str(by_name.get(file_name, {}).get("text") or "")
        detected = llm_types.get(idx) or {}
        llm_type = detected.get("type") or ""
        llm_ok = llm_type in _CONFIDENT_LLM_TYPES
        # LLM PHÂN LOẠI CHÍNH (đọc đủ OCR, phân biệt tốt các loại giấy đất dùng chung từ vựng). Rule chỉ
        # DỰ PHÒNG khi LLM trả "other"/không chắc hoặc LLM lỗi. Không để keyword tham đè quyết định LLM.
        rule_type = "" if llm_ok else (_rule_doc_type(text, file_name) or "")
        doc_type = (llm_type if llm_ok else "") or rule_type or _T_OTHER
        resolved.append({
            "idx": idx, "fileName": file_name, "docType": doc_type,
            "title": detected.get("title") or detected.get("documentName", ""),
            "source": "llm" if llm_ok else ("rule" if rule_type else "default"),
        })

    # Gom theo nhóm, giữ thứ tự ưu tiên trong nhóm.
    groups: dict[str, list[dict]] = {g: [] for g in _GROUPS}
    for entry in resolved:
        group_key = _TYPE_TO_GROUP.get(entry["docType"], _G_ORIGIN)
        groups[group_key].append(entry)

    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    for group_key, meta in _GROUPS.items():
        entries = sorted(groups[group_key], key=lambda e: (_TYPE_PRIORITY.get(e["docType"], 99), e["idx"]))
        if not entries:
            continue
        source_indexes = [e["idx"] for e in entries]
        # documentName nhóm: ưu tiên nhãn giấy tờ chính (entry đầu) để hiển thị dễ hiểu.
        head = entries[0]
        document_name = _label_for_type(head["docType"], head.get("title", "")) if len(entries) == 1 else meta["label"]
        attachments.append({
            "fileIndex": source_indexes[0],
            "sourceFileIndexes": source_indexes,   # FE gộp các file này thành 1 PDF theo thứ tự
            "fileName": str(files[source_indexes[0]].get("name") or f"file-{source_indexes[0] + 1}"),
            "documentName": document_name,
            "componentName": meta["componentName"],
            "target": "fixed-slot",
            "needsAddComponent": False,
            "detectedType": document_name,
            "slotKey": group_key,
            "slotIndex": meta["slotIndex"],
            "slotName": meta["componentName"],
        })
        for e in entries:
            classified.append({
                "fileName": e["fileName"], "docType": e["docType"],
                "documentName": _label_for_type(e["docType"], e.get("title", "")),
                "group": group_key, "slotIndex": meta["slotIndex"], "source": e["source"],
            })

    if not attachments:
        warnings.append("Không phân loại được tài liệu nào vào 4 nhóm thành phần hồ sơ đăng ký đất đai.")
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

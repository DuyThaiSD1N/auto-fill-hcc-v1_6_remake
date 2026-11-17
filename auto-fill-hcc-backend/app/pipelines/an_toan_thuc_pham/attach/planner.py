"""Đính kèm cho thủ tục cấp Giấy chứng nhận cơ sở đủ điều kiện ATTP (Bộ Y tế, 1.013855).

Bảng "Thành phần hồ sơ" của cổng (ảnh cổng thật 17/11/2026, tài khoản UBND phường Hiệp Hòa) có 5 dòng
a)–e), mỗi dòng một loại giấy, mỗi dòng một ô "Chọn tệp tin":

  a) Đơn đề nghị cấp Giấy chứng nhận (Mẫu số 1 Phụ lục I …)      ← don_de_nghi (+ CCCD / giấy chưa rõ loại)
  b) Bản sao Giấy chứng nhận đăng ký kinh doanh … doanh nghiệp …  ← gcn_dkkd
  c) Bản thuyết minh về cơ sở vật chất, trang thiết bị …           ← thuyet_minh
  d) Giấy xác nhận đủ sức khỏe của chủ cơ sở …                    ← suc_khoe
  e) Danh sách người … đã được tập huấn kiến thức an toàn thực phẩm ← tap_huan

Trước đây planner coi bảng chỉ có MỘT dòng "A. Thành phần hồ sơ" và dồn mọi tệp vào ô đầu → cả 5 giấy nằm ở
dòng a). Nay mỗi loại đi đúng dòng của nó.

Engine FE `attachFilesByFixedSlot` (Auto Fill content.js + trợ lý attach-core.js) tìm ô theo `slotKeywords` BE gửi
(khớp chuỗi con trên CẢ dòng `tr`, gồm cả tên tệp đã đính) rồi mới đến `slotIndex` (vị trí 0-based của ô upload).
Vì vậy:
- slotKey cố ý KHÔNG trùng `FIXED_SLOT_KEYWORDS` của extension (bảng cũ `attp_dossier` bắt dòng a));
- từ khoá là cụm in trên tên dòng mà KHÔNG nằm trong tên tệp do planner đặt (_LABELS), để dòng a) đã mang tệp
  "Giấy xác nhận đủ sức khỏe.pdf" (lần đính lỗi trước) không bị nhận là dòng d);
- cổng còn gom cả năm loại vào một dòng thì các cụm đó vẫn nằm trong dòng gộp → mọi tệp vào dòng đó như cũ.

Phân loại LLM-primary (prompt.py); LLM lỗi / trả other thì dò từ khoá OCR làm dự phòng. Giấy không có dòng riêng
(CCCD, giấy ủy quyền…) hoặc không rõ loại → dòng a) Đơn, giữ tiêu đề in trên giấy / tên tệp gốc + cảnh báo; không
bỏ tệp nào.
"""

import re
import time
from pathlib import Path
from typing import Any

from app.config import settings
from app.pipelines._shared import fold
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.an_toan_thuc_pham.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON = "don_de_nghi"
_GCN_DKKD = "gcn_dkkd"
_THUYET_MINH = "thuyet_minh"
_SUC_KHOE = "suc_khoe"
_TAP_HUAN = "tap_huan"
_OTHER = "other"

# Tên tài liệu theo loại giấy (≤50 ký tự, không ngoặc, không dấu chấm — ràng buộc ô tên của cổng).
_LABELS = {
    _DON: "Đơn đề nghị cấp Giấy chứng nhận ATTP",
    _GCN_DKKD: "Giấy chứng nhận đăng ký kinh doanh",
    _THUYET_MINH: "Bản thuyết minh cơ sở vật chất trang thiết bị",
    _SUC_KHOE: "Giấy xác nhận đủ sức khỏe",
    _TAP_HUAN: "Danh sách người đã tập huấn kiến thức ATTP",
}
_ALLOWED_DOC_TYPES = set(_LABELS) | {_OTHER}


def _row(stt: int, slot_key: str, name: str, keywords: list[str]) -> dict[str, Any]:
    return {"stt": stt, "slotKey": slot_key, "slotIndex": stt - 1, "slotName": name, "slotKeywords": keywords}


# Tên dòng NGUYÊN VĂN cột "Tên giấy tờ". ⚠ slotKey không được trùng FIXED_SLOT_KEYWORDS của extension.
_ROWS: dict[str, dict[str, Any]] = {
    _DON: _row(
        1, "attp_byt_don",
        "a) Đơn đề nghị cấp Giấy chứng nhận (Mẫu số 1 Phụ lục I kèm theo Nghị định số 155/2018/NĐ-CP "
        "ngày 13/11/2018);",
        ["a) Đơn đề nghị cấp Giấy chứng nhận", "Mẫu số 1 Phụ lục I kèm theo Nghị định"],
    ),
    _GCN_DKKD: _row(
        2, "attp_byt_dkkd",
        "b) Bản sao Giấy chứng nhận đăng ký kinh doanh hoặc Giấy chứng nhận đăng ký doanh nghiệp có ngành nghề "
        "phù hợp với loại thực phẩm của cơ sở sản xuất (có xác nhận của cơ sở);",
        ["b) Bản sao Giấy chứng nhận đăng ký kinh doanh", "có ngành nghề phù hợp với loại thực phẩm"],
    ),
    _THUYET_MINH: _row(
        3, "attp_byt_thuyet_minh",
        "c) Bản thuyết minh về cơ sở vật chất, trang thiết bị dụng cụ bảo đảm điều kiện vệ sinh an toàn "
        "thực phẩm.",
        ["c) Bản thuyết minh về cơ sở vật chất", "bảo đảm điều kiện vệ sinh an toàn thực phẩm"],
    ),
    _SUC_KHOE: _row(
        4, "attp_byt_suc_khoe",
        "d) Giấy xác nhận đủ sức khỏe của chủ cơ sở và người trực tiếp sản xuất, kinh doanh thực phẩm do cơ sở "
        "y tế tuyến huyện trở lên cấp.",
        ["d) Giấy xác nhận đủ sức khỏe", "đủ sức khỏe của chủ cơ sở"],
    ),
    _TAP_HUAN: _row(
        5, "attp_byt_tap_huan",
        "e) Danh sách người sản xuất thực phẩm, kinh doanh dịch vụ ăn uống đã được tập huấn kiến thức an toàn "
        "thực phẩm có xác nhận của chủ cơ sở.",
        ["e) Danh sách người sản xuất thực phẩm", "đã được tập huấn kiến thức an toàn thực phẩm"],
    ),
}


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[:limit] + "..."


def _clean_title(value: str) -> str:
    text = re.sub(r"[()\[\]{}.]+", " ", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:50].strip()


def _document_name(file_name: str) -> str:
    stem = Path(file_name or "").stem.strip()
    return stem[:80] or "Tài liệu hồ sơ an toàn thực phẩm"


def _rule_doc_type(text: str) -> str:
    """Dự phòng khi LLM lỗi / trả other: nhận loại giấy theo cụm đặc trưng trong OCR, Đơn trước (Đơn liệt kê
    cả giấy kèm theo)."""
    h = fold(text)
    if not h:
        return ""
    if "don de nghi" in h and "an toan thuc pham" in h:
        return _DON
    if "thuyet minh" in h and ("co so vat chat" in h or "trang thiet bi" in h):
        return _THUYET_MINH
    if "tap huan" in h and ("kien thuc" in h or "an toan thuc pham" in h):
        return _TAP_HUAN
    if "du suc khoe" in h or "kham suc khoe" in h:
        return _SUC_KHOE
    if any(k in h for k in ("dang ky kinh doanh", "dang ky ho kinh doanh", "dang ky doanh nghiep",
                            "ma so doanh nghiep")):
        return _GCN_DKKD
    return ""


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
    if not documents:
        return {}
    docs = [{"index": item["index"], "text": _truncate_text(item.get("text", ""))} for item in documents]
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(docs)},
    ]
    raw = await client.chat(
        messages, max_tokens=max(500, 120 * len(docs)), enable_thinking=settings.agent_reasoning,
    )
    parsed = client.extract_json_block(raw)
    valid = {item["index"] for item in documents}
    out: dict[int, dict[str, str]] = {}
    for item in parsed.get("documents", []) or []:
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        if idx not in valid:
            continue
        doc_type = str(item.get("docType") or item.get("type") or "").strip().lower()
        out[idx] = {
            "docType": doc_type if doc_type in _ALLOWED_DOC_TYPES else _OTHER,
            "title": _clean_title(item.get("title") or ""),
        }
    return out


def _build_item(file: dict, index: int, document_name: str, detected_type: str, row: dict[str, Any]) -> dict:
    file_name = str(file.get("name") or f"file-{index + 1}")
    return {
        "fileIndex": index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": row["slotName"],
        "target": "fixed-slot",
        "componentIndex": row["stt"],
        "needsAddComponent": False,
        "detectedType": detected_type,
        "slotKey": row["slotKey"],
        "slotIndex": row["slotIndex"],
        "slotName": row["slotName"],
        "slotKeywords": list(row["slotKeywords"]),
        # Cổng có thể chỉ nhận một tệp cho mỗi lần bấm "Chọn tệp tin" → FE mở lại đúng ô cho từng tệp.
        "repeatUpload": True,
    }


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, dict[str, str]] | None = None,
    ocr_texts: dict[int, str] | None = None,
) -> tuple[list[dict], list[dict], list[str]]:
    llm_types = llm_types or {}
    ocr_texts = ocr_texts or {}
    attachments: list[dict] = []
    classified: list[dict] = []
    extra_files: list[str] = []
    # Cùng một dòng nhận nhiều tệp: hai tệp cùng loại giấy phải khác tên để cán bộ phân biệt trên cổng.
    seen: dict[str, int] = {}
    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        detected = llm_types.get(idx) or {}
        doc_type = detected.get("docType") or _OTHER
        source = "llm" if doc_type in _LABELS else ""
        if doc_type not in _LABELS:
            rule_type = _rule_doc_type(ocr_texts.get(idx, ""))
            if rule_type:
                doc_type, source = rule_type, "rule"
        name = _LABELS.get(doc_type) or detected.get("title") or ""
        if not source:
            source = "llm" if name else "fileName"
        if not name:
            name = _document_name(file_name)
        else:
            key = fold(name)
            seen[key] = seen.get(key, 0) + 1
            if seen[key] > 1:
                name = f"{name} {seen[key]}"
        row = _ROWS.get(doc_type) or _ROWS[_DON]
        detected_type = _LABELS.get(doc_type, "Tài liệu thành phần hồ sơ an toàn thực phẩm")
        attachments.append(_build_item(file, idx, name, detected_type, row))
        entry = {
            "fileName": file_name,
            "docType": doc_type,
            "slotKey": row["slotKey"],
            "slotIndex": row["slotIndex"],
            "documentName": name,
            "source": source,
        }
        if doc_type not in _ROWS:
            entry["routedTo"] = _DON
            extra_files.append(file_name)
        classified.append(entry)

    warnings: list[str] = []
    if extra_files:
        warnings.append(
            "Giấy tờ không có dòng riêng hoặc chưa rõ loại đã đính chung dòng "
            f"\"{_ROWS[_DON]['slotName']}\": " + ", ".join(extra_files) + "."
        )
    return attachments, classified, warnings


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    _ = options or {}
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_indexes = [idx for idx, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]
    ocr_files = [raw_files[idx] for idx in ocr_indexes]

    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    # ocr_per_file trả đúng thứ tự tệp đưa vào → ghép theo vị trí, không theo tên (hai ảnh có thể trùng tên).
    ocr_texts: dict[int, str] = {}
    llm_docs: list[dict[str, Any]] = []
    for idx, result in zip(ocr_indexes, ocr_results):
        text = str(result.get("text") or "")
        if text.strip():
            ocr_texts[idx] = text
            llm_docs.append({"index": idx, "text": text})

    t1 = time.monotonic()
    llm_types: dict[int, dict[str, str]] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, classified, warnings = build_plan_items(raw_files, llm_types, ocr_texts)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [raw_files[doc["index"]]["name"] for doc in llm_docs],
            "sessionId": (session or {}).get("request_id"),
            "classified": classified,
            "skippedOcr": [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES],
            "slots": [
                {"docType": doc_type, "slotKey": row["slotKey"], "slotIndex": row["slotIndex"],
                 "slotName": row["slotName"]}
                for doc_type, row in _ROWS.items()
            ],
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

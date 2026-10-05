"""Đính kèm bước "Thành phần hồ sơ" cho "Đăng ký hoạt động khuyến mại mang tính may rủi trên địa bàn 01 tỉnh"
(cổng Bộ Công Thương — bảng Angular, engine FE `attp-row`).

Bảng có 3 dòng cố định (FE khớp dòng theo componentName, substring đã fold — thứ tự dòng không quan trọng):
  - "Mẫu bằng chứng xác định trúng thưởng hoặc mô tả chi tiết …"  ← mẫu phiếu bốc thăm / thẻ cào.
  - "01 Thể lệ chương trình khuyến mại theo mẫu quy định"         ← Thể lệ (Mẫu 03 ĐP).
  - "01 Đăng ký thực hiện chương trình khuyến mại theo mẫu quy định" ← Đăng ký (Mẫu 02 ĐP).
Giấy tờ chất lượng hàng hóa khuyến mại, CCCD, giấy tờ khác không có dòng riêng → đính chung dòng Đăng ký
(ô upload nhận nhiều tệp), không bỏ tệp nào. Không dùng modal "+ Thêm giấy tờ": ô "Giấy tờ" của modal chỉ
nhận tên có trong danh mục giấy tờ của thủ tục, danh mục này không có giấy tờ chất lượng.

Phân loại THUẦN LLM (1 lượt cho cả hồ sơ); LLM lỗi → mọi tệp về dòng Đăng ký. documentName = tên theo loại
giấy (engine attp-row đặt tên tệp theo documentName); giấy chưa biết loại giữ TÊN TỆP GỐC.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines.dang_ky_khuyen_mai_may_rui.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DANG_KY = "dang_ky"
_THE_LE = "the_le"
_BANG_CHUNG = "bang_chung"
_CHAT_LUONG = "chat_luong"
_CCCD = "cccd"
_OTHER = "other"

_ROWS: dict[str, dict[str, str]] = {
    _DANG_KY: {"componentName": "Đăng ký thực hiện chương trình khuyến mại theo mẫu quy định", "loaiBan": "Bản chính"},
    _THE_LE: {"componentName": "Thể lệ chương trình khuyến mại theo mẫu quy định", "loaiBan": "Bản chính"},
    _BANG_CHUNG: {"componentName": "Mẫu bằng chứng xác định trúng thưởng", "loaiBan": "Bản chính"},
}
_FALLBACK = _DANG_KY
# Tên tài liệu theo loại (≤50 ký tự, không ngoặc, không dấu chấm). Cài đặt tài khoản tắt "đổi tên tệp"
# thì FE tự giữ tên gốc.
_LABELS: dict[str, str] = {
    _DANG_KY: "Đăng ký thực hiện chương trình khuyến mại",
    _THE_LE: "Thể lệ chương trình khuyến mại",
    _BANG_CHUNG: "Mẫu bằng chứng xác định trúng thưởng",
    _CHAT_LUONG: "Giấy tờ chất lượng hàng hóa khuyến mại",
    _CCCD: "Căn cước công dân",
}
_ALLOWED = set(_ROWS) | {_CHAT_LUONG, _CCCD, _OTHER}


def _normalize_type(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if text in _ALLOWED else _OTHER


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=600, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    wanted = {int(doc["index"]) for doc in documents}
    out: dict[int, str] = {}
    for item in parsed.get("documents", []) or []:
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        if idx not in wanted or idx in out:
            continue
        out[idx] = _normalize_type(item.get("docType") or item.get("type"))
    return out


def _row_item(file_name: str, file_index: int, row: dict[str, str], detected_type: str, document_name: str) -> dict:
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": row["componentName"],
        "loaiBan": row["loaiBan"],
        "target": "attp-row",
        "needsAddComponent": False,
        "detectedType": detected_type,
    }


def build_plan_items(
    files: list[dict], llm_types: dict[int, str] | None = None
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    items: list[dict] = []
    classified: list[dict] = []
    # Nhiều tệp vào cùng một dòng (ô upload nhận nhiều tệp): cùng loại phải khác tên để cán bộ phân biệt.
    name_counts: dict[str, int] = {}
    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        doc_type = llm_types.get(idx, _OTHER)
        document_name = _LABELS.get(doc_type, "")
        if document_name:
            name_counts[document_name] = name_counts.get(document_name, 0) + 1
            if name_counts[document_name] > 1:
                document_name = f"{document_name} {name_counts[document_name]}"
        else:
            document_name = file_name
        entry = {"fileName": file_name, "docType": doc_type, "source": "llm" if idx in llm_types else "unknown"}
        row_type = doc_type if doc_type in _ROWS else _FALLBACK
        if row_type != doc_type:
            entry["routedTo"] = row_type
        items.append(_row_item(file_name, idx, _ROWS[row_type], doc_type, document_name))
        classified.append(entry)
    return items, [], classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options, session
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_pairs = [(i, f) for i, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]

    from app.services import ocr

    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file([f for _, f in ocr_pairs]) if ocr_pairs else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    llm_docs: list[dict[str, Any]] = []
    for (idx, file), res in zip(ocr_pairs, ocr_results):
        if res.get("error"):
            errors.append(f"OCR {file.get('name')}: {res['error']}")
        text = str(res.get("text") or "")
        if text.strip():
            llm_docs.append({"index": idx, "text": text})

    t1 = time.monotonic()
    llm_types: dict[int, str] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, llm_types)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "llmDocuments": [raw_files[doc["index"]]["name"] for doc in llm_docs],
            "classified": classified,
            "rows": [{"docType": k, **v} for k, v in _ROWS.items()],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

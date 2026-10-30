"""Đính kèm cho [Lào Cai - cổng iGate mới] thu hồi GCN cấp lần đầu không đúng quy định, cấp lại (1.115687).

Phân loại giữ NGUYÊN của pipeline cổng cũ (thu_hoi_gcn_cap_lan_dau_khong_dung_quy_dinh_cap_lai/attach: OCR → LLM gán nhãn
catalog + documentName); CCCD không phải thành phần hồ sơ → bỏ qua kèm cảnh báo như cổng cũ.

Bước 2 "Thành phần hồ sơ hệ thống" của cổng mới (crawl 29/10/2026, UBND phường) là CÙNG bảng 2 dòng như cổng cũ, cổng
TÍCH SẴN cả 2, KHÔNG còn danh sách "Giấy tờ khác":
   1 Văn bản kiến nghị việc cấp Giấy chứng nhận không đúng quy định của pháp luật đất đai (bản chính)
   2 Giấy chứng nhận đã cấp (bản gốc)
⚠ Bản crawl ghi componentName dòng 2 là "scannerScan tệp tin…" (đọc nhầm ô nút); dò tên không ra thì lấy theo VỊ TRÍ
dòng khi bảng đúng 2 dòng. Giấy tờ cổng cũ đưa xuống "Giấy tờ khác" (Giấy ủy quyền, văn bản rà soát, giấy tờ người đồng
sử dụng…) → dòng Văn bản kiến nghị, giữ tên + cảnh báo. Không bỏ tệp nào ngoài CCCD.

Engine FE "attp-row" + untickUnplannedRows dùng chung với cho_thue_dat_thue_rung_igate_lao_cai.
"""

import time

from app.pipelines._shared import fold
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.cho_thue_dat_thue_rung_igate_lao_cai.attach import planner as _igate
from app.pipelines.thu_hoi_gcn_cap_lan_dau_khong_dung_quy_dinh_cap_lai.attach import catalog
from app.pipelines.thu_hoi_gcn_cap_lan_dau_khong_dung_quy_dinh_cap_lai.attach import planner as _goc
from app.process.schemas import FileItem
from app.services import ocr

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
# Cổng Lào Cai: "Dung lượng tối đa là 6 Mb".
_GIOI_HAN_BYTE = 6 * 1024 * 1024

# Bảng 2 dòng NGUYÊN VĂN (crawl 29/10/2026; tên dòng 2 lấy từ ô "Tên giấy tờ").
_DEFAULT_ROWS = [
    "Văn bản kiến nghị việc cấp Giấy chứng nhận không đúng quy định của pháp luật đất đai (bản chính)",
    "Giấy chứng nhận đã cấp (bản gốc)",
]
# vị trí dòng (1-based, catalog cổng cũ) → từ khoá dò dòng (= catalog.ROWS).
_ROW_KEYS = {position: keywords for position, (keywords, _) in catalog.ROWS.items()}

Row = _igate.Row


def _default_rows() -> list[Row]:
    return [(i + 1, name, fold(name)) for i, name in enumerate(_DEFAULT_ROWS)]


def _row(position: int, rows: list[Row]) -> Row | None:
    found = _igate._find(_ROW_KEYS[position], rows)
    if found is None and len(rows) == len(_DEFAULT_ROWS):
        found = rows[position - 1]
    return found


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, dict[str, str]] | None = None,
    components: list[dict] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    rows = _igate._portal_rows(components) or _default_rows()
    warnings: list[str] = []
    kien_nghi = _row(catalog.ROW_KIEN_NGHI, rows) or rows[0]

    attachments: list[dict] = []
    classified: list[dict] = []
    ngoai_bang: list[str] = []
    used_names: set[str] = set()
    bytes_per_row: dict[int, int] = {}
    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        detected = llm_types.get(index) or {}
        label = detected.get("label") or "khac"
        if not catalog.is_valid(label):
            label = "khac"
        fallback = catalog.display_name(label)
        document_name = _goc._unique_document_name(detected.get("documentName") or fallback, used_names, fallback)
        base = {"fileName": file_name, "label": label, "documentName": document_name,
                "source": "llm" if index in llm_types else "default"}
        if label in catalog.SKIPPED_LABELS:
            warnings.append(f"File '{file_name}' ({document_name}) không phải thành phần hồ sơ — đã bỏ qua.")
            classified.append({**base, "target": "skip", "reason": "not_a_component"})
            continue

        position = catalog.row_for(label)
        row = (_row(position, rows) if position else None) or kien_nghi
        if not position:
            ngoai_bang.append(f"{file_name} → \"{document_name}\"")
        bytes_per_row[row[0]] = bytes_per_row.get(row[0], 0) + _goc._data_url_size(file.get("dataUrl", ""))
        attachments.append(_igate._item(index, file_name, document_name, row, label))
        classified.append({**base, "target": "attp-row", "componentIndex": row[0]})

    if ngoai_bang:
        warnings.append(
            "Giấy tờ ngoài 2 dòng của bảng (cổng cũ đưa xuống \"Giấy tờ khác\") đã tạm đính vào dòng Văn bản kiến nghị "
            "(vẫn là tệp riêng, giữ tên) vì cổng mới không còn danh sách \"Giấy tờ khác\" — nếu cần tách riêng, cán bộ "
            f"dùng nút \"Thêm giấy tờ\" của cổng: {', '.join(ngoai_bang)}."
        )
    for row_index, total in sorted(bytes_per_row.items()):
        if total > _GIOI_HAN_BYTE:
            warnings.append(
                f"Tổng dung lượng các tệp đính vào dòng thứ {row_index} là {total / 1024 / 1024:.1f} MB, vượt giới hạn "
                "6 MB của cổng — cần nén PDF hoặc giảm DPI trước khi nộp."
            )
    _igate._dedupe_document_names(attachments)
    if not attachments:
        warnings.append("Không có tài liệu nào để đính kèm.")
    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    components = ((options or {}).get("attachmentContext") or {}).get("components")
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]
    errors: list[str] = []

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    by_name = {item.get("name"): item for item in ocr_results}
    llm_documents = [
        {"index": index, "text": str(by_name.get(file.get("name"), {}).get("text") or "")}
        for index, file in enumerate(raw_files)
    ]
    started = time.monotonic()
    llm_types: dict[int, dict[str, str]] = {}
    if any(doc["text"].strip() for doc in llm_documents):
        try:
            llm_types = await _goc._classify_with_llm(llm_documents)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, llm_types, components)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [f["name"] for f in raw_files],
            "portalRows": len(_igate._portal_rows(components)),
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "ocr_text": join_ocr_documents(ocr_results),
        "llm_output": {str(idx): value for idx, value in llm_types.items()},
        "errors": errors,
    }

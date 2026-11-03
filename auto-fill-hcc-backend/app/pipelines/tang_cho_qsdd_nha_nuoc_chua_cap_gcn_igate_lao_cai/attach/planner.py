"""Đính kèm cho [Lào Cai - cổng iGate mới] tặng cho quyền sử dụng đất mở rộng đường giao thông (1.115690).

Phân loại giữ NGUYÊN của pipeline cổng cũ (tang_cho_qsdd_nha_nuoc_chua_cap_gcn/attach: OCR → LLM từng tệp, thuần LLM;
tên mô tả theo ảnh ánh xạ của bộ phận một cửa; không bỏ sót tệp nào, kể cả CCCD; tệp quá 6 MB bị loại vì cổng không nhận).

Cổng cũ không có bảng "Thành phần hồ sơ" → mọi tệp xuống "Giấy tờ khác". Bước 2 "Thành phần hồ sơ hệ thống" của cổng
mới (crawl 02/11/2026, UBND Phường Yên Bái) có ĐÚNG MỘT dòng, cổng TÍCH SẴN:
   1  Văn bản tặng cho quyền sử dụng đất hoặc biên bản họp giữa đại diện thôn, làng, bản, tổ dân phố, điểm dân cư với
      người sử dụng đất về việc tặng cho quyền sử dụng đất
và không còn danh sách "Giấy tờ khác" → mọi tệp đính vào dòng 1 (mỗi tệp vẫn là tệp riêng, giữ tên mô tả); tệp không
phải văn bản tặng cho kèm cảnh báo dùng nút "Thêm giấy tờ" nếu cần tách riêng.

Engine FE "attp-row" dùng chung với cho_thue_dat_thue_rung_igate_lao_cai.
"""

import time

from app.pipelines._shared import fold
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.cho_thue_dat_thue_rung_igate_lao_cai.attach import planner as _igate
from app.pipelines.tang_cho_qsdd_nha_nuoc_chua_cap_gcn.attach import planner as _goc
from app.process.schemas import FileItem
from app.services import ocr

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
# Cổng Lào Cai: "Dung lượng tối đa là 6 Mb" cho mỗi tệp.
_MAX_FILE_BYTES = 6 * 1024 * 1024

_DONG_TANG_CHO = (
    "Văn bản tặng cho quyền sử dụng đất hoặc biên bản họp giữa đại diện thôn, làng, bản, tổ dân phố, điểm dân cư với "
    "người sử dụng đất về việc tặng cho quyền sử dụng đất"
)

Row = _igate.Row


def _row(components: list[dict] | None) -> Row:
    rows = _igate._portal_rows(components)
    if rows:
        return _igate._find(["van ban tang cho"], rows) or rows[0]
    return (1, _DONG_TANG_CHO, fold(_DONG_TANG_CHO))


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, str] | None = None,
    components: list[dict] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    row = _row(components)
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    unknown: list[str] = []
    ngoai_bang: list[str] = []
    seen_types: set[str] = set()

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        llm_type = llm_types.get(index, "")
        doc_type = llm_type if llm_type in _goc._ALLOWED else "other"
        seen_types.add(doc_type)
        if doc_type == "other":
            document_name = _goc._other_display(file_name)
            unknown.append(file_name)
        else:
            document_name = _goc._DISPLAY[doc_type]
        if doc_type != "van_ban_tang_cho":
            ngoai_bang.append(f"{file_name} → \"{document_name}\"")
        attachments.append(_igate._item(index, file_name, document_name, row, doc_type))
        classified.append({"fileName": file_name, "docType": doc_type, "source": "llm" if llm_type else "default",
                           "documentName": document_name, "componentIndex": row[0]})

    thieu = [nhan for doc_type, nhan in _goc._CORE_TYPES if doc_type not in seen_types]
    if thieu:
        warnings.append(
            "Chưa thấy trong bộ tệp đã tải lên: " + "; ".join(thieu) + ". Đây là các giấy tờ chính của hồ sơ hiến đất — "
            "cán bộ kiểm tra lại, nếu thiếu thật thì bổ sung trước khi nộp."
        )
    if "giay_to_tuy_than" in seen_types:
        warnings.append(
            "Có tệp là giấy tờ tùy thân (CCCD/CMND). Hướng dẫn ánh xạ của thủ tục này yêu cầu KHÔNG bỏ sót tệp nào nên "
            "hệ thống vẫn đính kèm — cán bộ tự quyết có giữ lại không."
        )
    if unknown:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã đính kèm với tên lấy theo tên tệp để không bỏ sót — cán bộ sửa lại tên nếu "
            f"cần: {', '.join(unknown)}."
        )
    if ngoai_bang:
        warnings.append(
            "Cổng mới chỉ có MỘT dòng thành phần hồ sơ (Văn bản tặng cho/biên bản họp) và không còn danh sách \"Giấy tờ "
            "khác\" → các giấy tờ sau đã đính chung vào dòng đó (vẫn là tệp riêng, giữ tên) — nếu cần tách riêng, cán "
            f"bộ dùng nút \"Thêm giấy tờ\" của cổng: {', '.join(ngoai_bang)}."
        )
    _igate._dedupe_document_names(attachments)
    if not attachments:
        warnings.append("Không có tài liệu nào để đính kèm.")
    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    components = ((options or {}).get("attachmentContext") or {}).get("components")
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    errors: list[str] = []

    valid_files: list[dict] = []
    original_indexes: list[int] = []
    for raw_index, file in enumerate(raw_files):
        size = _goc._data_url_size(file.get("dataUrl"))
        if size > _MAX_FILE_BYTES:
            errors.append(
                f"File '{file['name']}' vượt quá 6 MB ({_goc._mb(size)}) — cổng Lào Cai không nhận, đã bỏ qua. Hãy nén "
                "PDF hoặc quét lại ở DPI thấp hơn rồi đính bổ sung."
            )
        else:
            valid_files.append(file)
            original_indexes.append(raw_index)

    ocr_files = [f for f in valid_files if f.get("type") in _OCR_TYPES]
    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    by_name = {item.get("name"): item for item in ocr_results}
    llm_documents = [
        {"index": index, "text": str(by_name.get(file.get("name"), {}).get("text") or "")}
        for index, file in enumerate(valid_files)
        if str(by_name.get(file.get("name"), {}).get("text") or "").strip()
    ]
    started = time.monotonic()
    llm_types: dict[int, str] = {}
    if llm_documents:
        try:
            llm_types = await _goc._classify_with_llm(llm_documents, errors)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified = build_plan_items(valid_files, llm_types, components)
    # fileIndex đánh theo valid_files; extension lấy tệp theo vị trí trong danh sách GỐC → đổi lại.
    for item in attachments:
        item["fileIndex"] = original_indexes[item["fileIndex"]]
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [valid_files[d["index"]]["name"] for d in llm_documents],
            "portalRows": len(_igate._portal_rows(components)),
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "ocr_text": join_ocr_documents(ocr_results),
        "errors": errors,
    }

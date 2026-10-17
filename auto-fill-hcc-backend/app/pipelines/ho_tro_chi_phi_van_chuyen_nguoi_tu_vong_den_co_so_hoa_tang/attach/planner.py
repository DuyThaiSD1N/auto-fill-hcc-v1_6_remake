"""Lập kế hoạch đính kèm "Thành phần hồ sơ" cho thủ tục hỗ trợ chi phí vận chuyển người tử vong đến cơ sở hỏa
táng (mã 3.000721, cổng DVC Đà Nẵng — Angular mat-table, engine FE `attp-row`).

Bảng có 3 dòng cố định (theo ảnh ánh xạ + Mapping_HoTroChiPhiVanChuyenHoaTang_DaNang.xlsx):
  index 0: Đơn đề nghị hỗ trợ chi phí vận chuyển ... theo Mẫu ban hành kèm theo NQ 75/2026/NQ-HĐND -> Bản chính
  index 1: Quyết định hỗ trợ ... của Ủy ban nhân dân cấp xã -> văn bản KẾT QUẢ do UBND ban hành, KHÔNG đính
           (gửi untickRows để FE bỏ tick nếu cổng tick sẵn).
  index 2: Hợp đồng dịch vụ hỏa táng; biên bản giao nhận hũ đựng tro cốt -> Bản sao

FILE GỘP KHÔNG TÁCH: người dân hay scan Đơn + Biên bản giao nhận + Hợp đồng vào MỘT PDF. Ảnh ánh xạ ghi rõ
"KHÔNG tách file — đính kèm CHUNG cùng 1 file vào dòng 1 và dòng 3". Vì vậy LLM trả DANH SÁCH docTypes cho
mỗi file và planner phát một item cho MỖI dòng mà file đó có giấy tờ (cùng fileIndex, khác componentName —
FE gom nhóm theo componentName nên mỗi dòng nhận file riêng).

Phân loại LLM-FIRST: không có rule keyword. Giấy tờ không có dòng riêng (Trích lục khai tử, CCCD, ủy quyền,
không rõ loại) đính CHUNG vào dòng Đơn đề nghị để không rớt file, giữ documentName mô tả rõ.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON = "don_de_nghi"
_HOP_DONG = "hop_dong_hoa_tang"
_BIEN_BAN = "bien_ban_giao_nhan_tro_cot"
_QUYET_DINH = "quyet_dinh_ho_tro"
_TRICH_LUC_KHAI_TU = "trich_luc_khai_tu"
_AUTHORIZATION = "authorization"
_IDENTITY = "identity"
_OTHER = "other"

# componentName = đoạn text ĐẶC TRƯNG của dòng (FE khớp substring sau khi fold dấu). Dòng Đơn và dòng Quyết
# định cùng đuôi "hỗ trợ chi phí vận chuyển người tử vong..." nên giữ tiền tố "Đơn đề nghị" để không khớp chéo.
_ROW_DON = "Đơn đề nghị hỗ trợ chi phí vận chuyển người tử vong đến cơ sở hỏa táng"
_ROW_QUYET_DINH = "Quyết định hỗ trợ chi phí vận chuyển người tử vong đến cơ sở hỏa táng"
_ROW_HOP_DONG = "Hợp đồng dịch vụ hỏa táng"

_ROWS: dict[int, dict[str, str]] = {
    0: {"componentName": _ROW_DON, "loaiBan": "Bản chính"},
    2: {"componentName": _ROW_HOP_DONG, "loaiBan": "Bản sao"},
}

# docType -> dòng. Loại không có dòng riêng đi về dòng Đơn (index 0).
_ROW_OF: dict[str, int] = {
    _DON: 0,
    _HOP_DONG: 2,
    _BIEN_BAN: 2,
    _TRICH_LUC_KHAI_TU: 0,
    _AUTHORIZATION: 0,
    _IDENTITY: 0,
}
_NAME_OF: dict[str, str] = {
    _DON: "Đơn đề nghị hỗ trợ chi phí vận chuyển người tử vong đến cơ sở hỏa táng",
    _HOP_DONG: "Hợp đồng dịch vụ hỏa táng",
    _BIEN_BAN: "Biên bản giao nhận hũ đựng tro cốt",
    _TRICH_LUC_KHAI_TU: "Trích lục khai tử/Giấy báo tử",
    _AUTHORIZATION: "Văn bản ủy quyền/giấy giới thiệu",
    _IDENTITY: "Căn cước công dân",
}
_ALLOWED = set(_ROW_OF) | {_QUYET_DINH, _OTHER}


def _normalize_doc_type(value: Any) -> str:
    folded = _fold(str(value or "")).replace(" ", "_")
    for doc_type in _ALLOWED:
        if folded == doc_type:
            return doc_type
    return _OTHER


def _normalize_doc_types(item: dict) -> list[str]:
    raw = item.get("docTypes")
    if raw is None:
        raw = [item.get("docType") or item.get("type")]
    if not isinstance(raw, list):
        raw = [raw]
    out: list[str] = []
    for value in raw:
        doc_type = _normalize_doc_type(value)
        if doc_type not in out:
            out.append(doc_type)
    # "other" lẫn cùng loại đã nhận ra thì bỏ "other".
    if len(out) > 1 and _OTHER in out:
        out.remove(_OTHER)
    return out


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, list[str]]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=700, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    result: dict[int, list[str]] = {}
    for item in parsed.get("documents", []) or []:
        try:
            result[int(item.get("index"))] = _normalize_doc_types(item)
        except (TypeError, ValueError, AttributeError):
            continue
    return result


def _document_name(row_index: int, doc_types: list[str], file_name: str) -> str:
    names = [_NAME_OF[t] for t in doc_types if t in _NAME_OF and _ROW_OF[t] == row_index]
    if not names:
        return file_name
    if row_index == 2 and len(names) > 1:
        return "Hợp đồng hỏa táng và biên bản giao nhận hũ tro cốt"
    return names[0]


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict] | None = None,
    llm_types: dict[int, list[str]] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    del ocr_results  # LLM-first: không dùng OCR text để suy luận rule ở đây.
    llm_types = llm_types or {}
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    seen_types: set[str] = set()

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        doc_types = [t for t in (llm_types.get(index) or []) if t in _ALLOWED] or [_OTHER]
        seen_types.update(doc_types)
        source = "llm" if llm_types.get(index) else "unknown"

        if doc_types == [_QUYET_DINH]:
            classified.append({"fileName": file_name, "docTypes": doc_types, "source": source, "skipped": True})
            warnings.append(
                f"'{file_name}' là Quyết định hỗ trợ của UBND cấp xã (văn bản kết quả) — không đính kèm."
            )
            continue

        rows = sorted({_ROW_OF[t] for t in doc_types if t in _ROW_OF})
        if not rows:
            # Chỉ có "other" (hoặc other + quyết định) -> không bỏ file: đính chung dòng Đơn, giữ tên gốc.
            rows = [0]
            warnings.append(
                f"Chưa nhận diện chắc loại giấy tờ cho '{file_name}' — tạm đính vào dòng Đơn đề nghị; cán bộ "
                f"kiểm tra lại."
            )

        for row_index in rows:
            row = _ROWS[row_index]
            attachments.append({
                "fileIndex": index,
                "fileName": file_name,
                "documentName": _document_name(row_index, doc_types, file_name),
                "componentName": row["componentName"],
                "componentIndex": row_index,
                "loaiBan": row["loaiBan"],
                "target": "attp-row",
                "needsAddComponent": False,
                "untickRows": [_ROW_QUYET_DINH],
                "detectedType": doc_types[0],
                "detectedTypes": doc_types,
            })
        classified.append({
            "fileName": file_name,
            "docTypes": doc_types,
            "source": source,
            "componentIndexes": rows,
        })

    if _DON not in seen_types:
        warnings.append(
            "Chưa có Đơn đề nghị hỗ trợ chi phí vận chuyển người tử vong đến cơ sở hỏa táng — thành phần hồ sơ "
            "bắt buộc."
        )
    if not seen_types & {_HOP_DONG, _BIEN_BAN}:
        warnings.append(
            "Chưa có Hợp đồng dịch vụ hỏa táng / Biên bản giao nhận hũ đựng tro cốt — thành phần hồ sơ bắt buộc."
        )
    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    ocr_indexes = [index for index, item in enumerate(raw_files) if item.get("type") in _OCR_TYPES]
    errors: list[str] = []

    from app.services import ocr

    # OCR ĐỦ trang (không cắt 2 trang đầu): file gộp có Biên bản/Hợp đồng nằm ở trang 3-5, cắt là LLM không
    # thấy. Hồ sơ thủ tục này chỉ vài trang và trùng cache OCR của bước điền.
    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file([raw_files[i] for i in ocr_indexes]) if ocr_indexes else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    # ocr_per_file trả đúng thứ tự tệp đưa vào -> ghép theo vị trí (hai ảnh có thể trùng tên).
    llm_documents = [
        {"index": index, "text": str(result.get("text") or "")}
        for index, result in zip(ocr_indexes, ocr_results)
        if str(result.get("text") or "").strip()
    ]
    started = time.monotonic()
    llm_types: dict[int, list[str]] = {}
    if llm_documents:
        try:
            llm_types = await _classify_with_llm(llm_documents)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [item["name"] for item in raw_files],
            "ocrDocuments": [raw_files[doc["index"]]["name"] for doc in llm_documents],
            "llmDocuments": [raw_files[doc["index"]]["name"] for doc in llm_documents],
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

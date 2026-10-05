"""Đính kèm bước "Thành phần hồ sơ" cho thủ tục "Điều chỉnh giấy phép hoạt động khám bệnh, chữa bệnh" (cổng
Bộ Y tế — Angular mat-table, engine FE `attp-row`).

Bảng 5 dòng, 2 dòng đầu TRÙNG tên "Đơn theo Mẫu 02…" (dòng lặp của cổng) → Đơn chỉ đính 1 lần vào dòng đầu
(engine lấy dòng ĐẦU TIÊN chứa componentName):
  don_de_nghi            "Đơn theo Mẫu 02 Phụ lục II"            ← Đơn đề nghị cấp điều chỉnh GPHĐ.
  giay_phep_hoat_dong +  "Bản gốc giấy phép hoạt động"           ← GPHĐ đã cấp + quyết định của Sở Y tế về
  quyet_dinh_so_y_te                                                giấy phép (đính CÙNG dòng).
  ke_khai                "Bản kê khai cơ sở vật chất"            ← kê khai CSVC, thiết bị, nhân sự.
  quyet_dinh_to_chuc_lai "Các giấy tờ quy định tại điểm b khoản 3 Điều 54" ← QĐ tổ chức lại / đổi tên…

Phân loại THUẦN LLM, mỗi tệp một lượt gọi (asyncio.gather). ⚑ KHÔNG BỎ TỆP: CCCD (không có dòng riêng),
tệp other hoặc lượt gọi lỗi → dòng "Các giấy tờ quy định tại điểm b khoản 3 Điều 54", giữ tên tệp gốc.
"""

import asyncio
import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.dieu_chinh_giay_phep_hoat_dong_kcb.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_LOAI_BAN = "Scan tệp tin"

_DON = "don_de_nghi"
_GPHD = "giay_phep_hoat_dong"
_QD_SYT = "quyet_dinh_so_y_te"
_KE_KHAI = "ke_khai"
_TO_CHUC_LAI = "quyet_dinh_to_chuc_lai"
_CCCD = "cccd"
_OTHER = "other"


def _row(component: str, document: str) -> dict[str, str]:
    return {"componentName": component, "loaiBan": _LOAI_BAN, "documentName": document}


# GPHĐ và quyết định của Sở Y tế về giấy phép cùng một dòng → CHUNG componentName: engine gom tệp theo
# componentName rồi set ô upload một lần; hai tên khác nhau trỏ cùng dòng thì lần sau ghi đè lần trước.
_DONG_GPHD = "Bản gốc giấy phép hoạt động"
_DONG_DIEU_54 = "Các giấy tờ quy định tại điểm b khoản 3 Điều 54"

_ROWS: dict[str, dict[str, str]] = {
    _DON: _row("Đơn theo Mẫu 02 Phụ lục II", "Đơn đề nghị điều chỉnh giấy phép hoạt động (Mẫu 02)"),
    _GPHD: _row(_DONG_GPHD, "Giấy phép hoạt động khám bệnh, chữa bệnh"),
    _QD_SYT: _row(_DONG_GPHD, "Quyết định của Sở Y tế về giấy phép hoạt động"),
    _KE_KHAI: _row("Bản kê khai cơ sở vật chất", "Bản kê khai cơ sở vật chất, thiết bị, nhân sự"),
    _TO_CHUC_LAI: _row(_DONG_DIEU_54, "Quyết định tổ chức lại, đổi tên cơ sở"),
}
# CCCD không có dòng riêng → đi kèm dòng giấy tờ điểm b khoản 3 Điều 54 như tệp other (không bỏ tệp).
_FALLBACK = _TO_CHUC_LAI
_ALLOWED_DOC_TYPES = set(_ROWS) | {_CCCD, _OTHER}
# Tên tài liệu cho CCCD đính kèm dòng khác (≤50 ký tự, không ngoặc — extension đặt tên tệp theo documentName).
_CCCD_LABEL = "Căn cước công dân"


def _canon(value: Any) -> str:
    return re.sub(r"[\s_\-]+", "_", _fold(str(value or ""))).strip("_")


def _normalize_doc_type(value: Any) -> str:
    """Khớp ĐÚNG nhãn trong allowed_types. Nhãn lạ → other.

    Không khớp chuỗi con: bản cũ dò `"anh" in text` nên nhãn "thuc_hanh" (chứa "anh") bị đổi thành
    anh_chan_dung — giấy xác nhận thực hành bị lái sang dòng ảnh.
    """
    canon = _canon(value)
    return next((doc_type for doc_type in _ALLOWED_DOC_TYPES if _canon(doc_type) == canon), _OTHER)


async def _classify_one(index: int, file_name: str, text: str) -> tuple[int, str]:
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(file_name, text)},
    ]
    raw = await client.chat(messages, max_tokens=120, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    first = next(iter(parsed.get("documents", []) or []), None) or parsed
    return index, _normalize_doc_type(first.get("docType") or first.get("type"))


async def _classify_with_llm(
    documents: list[dict[str, Any]],
    errors: list[str] | None = None,
) -> dict[int, str]:
    """Một lượt gọi cho MỖI tệp — lỗi của tệp này không kéo theo tệp khác."""
    if not documents:
        return {}
    outcomes = await asyncio.gather(
        *(_classify_one(d["index"], d["name"], d["text"]) for d in documents),
        return_exceptions=True,
    )
    result: dict[int, str] = {}
    for document, outcome in zip(documents, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            if errors is not None:
                errors.append(f"attachment_agent file {document['name']}: {outcome}")
            continue
        index, doc_type = outcome
        result[index] = doc_type
    return result


def _build_row_item(
    file: dict, file_index: int, doc_type: str, *, detected_type: str | None = None, document_name: str = "",
) -> dict:
    row = _ROWS[doc_type]
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    if detected_type == _CCCD:
        name = document_name or _CCCD_LABEL
    elif detected_type == _OTHER:
        # Tệp lạ giữ TÊN GỐC: đặt tên dòng cho nó thì cán bộ không phân biệt được hai tệp cùng dòng.
        name = file_name
    else:
        name = row["documentName"]
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        # engine attp-row đặt tên tệp theo documentName.
        "documentName": name,
        "componentName": row["componentName"],
        "loaiBan": row["loaiBan"],
        "target": "attp-row",
        "needsAddComponent": False,
        "detectedType": detected_type or doc_type,
    }


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    items: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    fallback: list[str] = []
    cccd_count = 0

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        doc_type = llm_types.get(idx, _OTHER)
        source = "llm" if idx in llm_types else "fallback"

        if doc_type in _ROWS:
            items.append(_build_row_item(file, idx, doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "source": source})
            continue
        # CCCD / chưa xếp được loại → dồn vào dòng giấy tờ điểm b khoản 3 Điều 54 chứ KHÔNG bỏ: bảng không
        # có dòng "giấy tờ khác", mà bỏ tệp là hồ sơ thiếu giấy người dân đã đưa.
        document_name = ""
        if doc_type == _CCCD:
            # Nhiều CCCD cùng dòng phải khác tên để cán bộ phân biệt.
            cccd_count += 1
            document_name = _CCCD_LABEL if cccd_count == 1 else f"{_CCCD_LABEL} {cccd_count}"
        items.append(_build_row_item(file, idx, _FALLBACK, detected_type=doc_type, document_name=document_name))
        classified.append({"fileName": file_name, "docType": doc_type, "source": source, "fallbackRow": _FALLBACK})
        if doc_type == _OTHER:
            fallback.append(file_name)

    if fallback:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã đính kèm chung vào dòng 'Các giấy tờ quy định tại điểm b khoản 3 "
            f"Điều 54' để không bỏ sót — cán bộ kiểm tra lại: {', '.join(fallback)}."
        )
    return items, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options or {}
    _ = session
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]

    from app.services import ocr

    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    ocr_by_name = {item.get("name"): item for item in ocr_results}
    # Gửi MỌI tệp cho LLM, kể cả tệp OCR RỖNG: ảnh chân dung thường không có chữ nào, bỏ qua tệp rỗng
    # là để tệp ảnh không bao giờ được xếp loại.
    llm_docs = [
        {"index": idx, "name": str(file.get("name") or ""),
         "text": str(ocr_by_name.get(file.get("name"), {}).get("text") or "")}
        for idx, file in enumerate(raw_files)
        if file.get("type") in _OCR_TYPES
    ]

    t1 = time.monotonic()
    llm_types: dict[int, str] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs, errors)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, llm_types)
    errors.extend(warnings)
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [doc["name"] for doc in llm_docs],
            "classified": classified,
            "skippedOcr": skipped_ocr,
            "rows": [{"docType": k, **v} for k, v in _ROWS.items()],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

"""Đính kèm bước "Thành phần hồ sơ" cho thủ tục "Cấp lại giấy phép hành nghề đối với trường hợp được cấp
trước ngày 01/01/2024..." (cổng Bộ Y tế — Angular mat-table, engine FE `attp-row`).

Bảng có ~34 dòng, nhiều dòng TRÙNG tên / gộp 2 mục / cụt đầu (cổng ghép danh mục của nhiều trường hợp).
Engine FE lấy dòng ĐẦU TIÊN có chứa componentName (substring đã fold) → componentName chọn đoạn chữ khớp
đúng dòng cần đính trước mọi dòng trùng:
  don_de_nghi       "Đơn theo Mẫu 08 Phụ lục I"                          ← Đơn đề nghị (Mẫu 08).
  giay_phep_cu      "hợp lệ giấy phép hành nghề đã được cấp"             ← chứng chỉ / giấy phép hành nghề cũ.
  anh_chan_dung     "02 ảnh chân dung cỡ 04"                             ← ảnh 4x6.
  suc_khoe +        "hợp lệ giấy khám sức khỏe do cơ sở khám bệnh"       ← dòng gộp b)/c): kết quả đánh giá
  ket_qua_danh_gia                                                        năng lực + giấy khám sức khỏe.
  so_yeu_ly_lich    "Sơ yếu lý lịch tự thuật của người hành nghề"        ← Mẫu 09.
  thuc_hanh         "giấy xác nhận hoàn thành quá trình thực hành theo Mẫu 07".
  thong_tin_thay_doi "tài liệu chứng minh thông tin thay đổi".
  quyet_dinh_thu_hoi "hợp lệ quyết định thu hồi giấy phép hành nghề".

Phân loại THUẦN LLM, mỗi tệp một lượt gọi (asyncio.gather). ⚑ KHÔNG BỎ TỆP: CCCD (không có dòng riêng),
tệp other hoặc lượt gọi lỗi → đính vào dòng Đơn, giữ tên tệp gốc.
"""

import asyncio
import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.cap_lai_giay_phep_hanh_nghe_truoc_2024.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_LOAI_BAN = "Scan tệp tin"

_DON = "don_de_nghi"
_GIAY_PHEP_CU = "giay_phep_cu"
_ANH = "anh_chan_dung"
_SUCKHOE = "suc_khoe"
_SYLL = "so_yeu_ly_lich"
_THUCHANH = "thuc_hanh"
_KET_QUA = "ket_qua_danh_gia"
_THAY_DOI = "thong_tin_thay_doi"
_THU_HOI = "quyet_dinh_thu_hoi"
_CCCD = "cccd"
_OTHER = "other"


def _row(component: str, document: str) -> dict[str, str]:
    return {"componentName": component, "loaiBan": _LOAI_BAN, "documentName": document}


# Dòng đầu tiên nhắc giấy khám sức khỏe là dòng GỘP "b) văn bản xác nhận kết quả đánh giá năng lực … c) giấy
# khám sức khỏe" → hai loại dùng CHUNG componentName: engine gom tệp theo componentName rồi set ô upload một
# lần; hai tên khác nhau trỏ cùng một dòng thì lần set sau ghi đè tệp của lần trước.
_DONG_SUC_KHOE = "hợp lệ giấy khám sức khỏe do cơ sở khám bệnh"

_ROWS: dict[str, dict[str, str]] = {
    _DON: _row("Đơn theo Mẫu 08 Phụ lục I", "Đơn đề nghị cấp lại giấy phép hành nghề (Mẫu 08)"),
    _GIAY_PHEP_CU: _row("hợp lệ giấy phép hành nghề đã được cấp", "Giấy phép hành nghề đã được cấp"),
    _ANH: _row("02 ảnh chân dung cỡ 04", "02 ảnh chân dung 4x6 nền trắng"),
    _SUCKHOE: _row(_DONG_SUC_KHOE, "Giấy khám sức khỏe"),
    _SYLL: _row("Sơ yếu lý lịch tự thuật của người hành nghề", "Sơ yếu lý lịch tự thuật (Mẫu 09)"),
    _THUCHANH: _row(
        "giấy xác nhận hoàn thành quá trình thực hành theo Mẫu 07",
        "Giấy xác nhận hoàn thành thực hành (Mẫu 07)",
    ),
    _KET_QUA: _row(_DONG_SUC_KHOE, "Văn bản xác nhận kết quả đánh giá năng lực"),
    _THAY_DOI: _row("tài liệu chứng minh thông tin thay đổi", "Tài liệu chứng minh thông tin thay đổi"),
    _THU_HOI: _row("hợp lệ quyết định thu hồi giấy phép hành nghề", "Quyết định thu hồi giấy phép hành nghề"),
}
# CCCD không có dòng riêng → đi kèm dòng Đơn như tệp other (không bỏ tệp).
_ALLOWED_DOC_TYPES = set(_ROWS) | {_CCCD, _OTHER}


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


def _build_row_item(file: dict, file_index: int, doc_type: str, *, detected_type: str | None = None) -> dict:
    row = _ROWS[doc_type]
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        # Tệp dồn vào dòng Đơn giữ TÊN GỐC: engine attp-row đặt tên tệp theo documentName, đặt tên
        # "Đơn đề nghị…" cho một tệp lạ là cán bộ không phân biệt được hai tệp cùng dòng.
        "documentName": file_name if detected_type in (_OTHER, _CCCD) else row["documentName"],
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

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        doc_type = llm_types.get(idx, _OTHER)
        source = "llm" if idx in llm_types else "fallback"

        if doc_type in _ROWS:
            items.append(_build_row_item(file, idx, doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "source": source})
            continue
        # CCCD / chưa xếp được loại → dồn vào dòng Đơn chứ KHÔNG bỏ: bảng không có dòng "giấy tờ khác",
        # mà bỏ tệp là hồ sơ thiếu giấy người dân đã đưa.
        items.append(_build_row_item(file, idx, _DON, detected_type=doc_type))
        classified.append({"fileName": file_name, "docType": doc_type, "source": source, "fallbackRow": _DON})
        if doc_type == _OTHER:
            fallback.append(file_name)

    if fallback:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã đính kèm chung vào dòng Đơn Mẫu 08 để không bỏ sót — cán bộ "
            f"kiểm tra lại: {', '.join(fallback)}."
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

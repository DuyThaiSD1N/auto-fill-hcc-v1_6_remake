"""Đính kèm bước "Thành phần hồ sơ" cho thủ tục "Cấp mới giấy phép hành nghề trong giai đoạn chuyển
tiếp..." (cổng Bộ Y tế — Angular mat-table, engine FE `attp-row`).

Bảng thành phần hồ sơ có nhiều dòng (mục a–h); ta gán vào các dòng thường dùng:
  a) "Đơn theo Mẫu 08 Phụ lục I ..."                         ← Đơn đề nghị cấp GPHN.
  b) "... Văn bằng chuyên môn (không áp dụng ..."            ← Bản sao văn bằng chuyên môn (bằng tốt nghiệp).
  d) "... giấy khám sức khỏe do cơ sở khám bệnh ..."         ← Giấy khám sức khỏe.
  e) "Sơ yếu lý lịch tự thuật của người hành nghề ..."       ← Sơ yếu lý lịch (Mẫu 09).
  g) "... giấy xác nhận hoàn thành quá trình thực hành ..."  ← Giấy xác nhận thực hành (Mẫu 07).
  h) "02 ảnh chân dung cỡ 04 cm ..."                         ← 02 ảnh chân dung 4x6.
(Mục c văn bằng chuyên khoa / đ tiếng Việt — trường hợp hiếm, chưa gán tự động.)
FE khớp dòng bằng TÊN giấy tờ (componentName, substring fold), tick checkbox + chọn loaiBan + set file.
Ta upload bản SCAN → loaiBan = "Scan tệp tin".

Phân loại THUẦN LLM — mọi dấu hiệu (kể cả dấu hiệu nhận ảnh chân dung) nằm trong prompt, KHÔNG có rule
keyword/ngưỡng chữ trong code: OCR của cùng một tệp ra khác nhau giữa các lần chạy (watermark app scan,
mốc trang, chữ vụn), rule cứng khớp được lần này thì trượt lần sau. Mỗi tệp một lượt gọi riêng để kết
quả của tệp này không phụ thuộc thứ tự hay số lượng tệp khác, và không phải tin chỉ số LLM trả về.

⚑ KHÔNG BỎ SÓT TỆP: tệp LLM không xếp được (other) hoặc lượt gọi lỗi → đính vào dòng Đơn (tờ khai),
giữ nguyên tên tệp gốc để cán bộ nhận ra. attp-row gộp nhiều tệp vào cùng một dòng theo componentName.
CCCD (thẻ thật) KHÔNG có dòng riêng trên bảng → bỏ qua như trước.
"""

import asyncio
import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.cap_moi_giay_phep_hanh_nghe_chuyen_tiep.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_LOAI_BAN = "Scan tệp tin"

_DON = "don_de_nghi"          # mục a
_VANBANG = "van_bang"         # mục b
_SUCKHOE = "suc_khoe"         # mục d
_SYLL = "so_yeu_ly_lich"      # mục e
_THUCHANH = "thuc_hanh"       # mục g
_ANH = "anh_chan_dung"        # mục h
_CCCD = "cccd"
_OTHER = "other"

# Mỗi loại giấy tờ → 1 dòng (mục a–h). componentName = ĐOẠN TEXT ĐẶC TRƯNG DUY NHẤT của dòng (FE khớp
# substring fold vào tên dòng lấy từ DOM). loaiBan = "Scan tệp tin" (đều là file scan/PDF).
_ROWS: dict[str, dict[str, str]] = {
    _DON: {
        "componentName": "Đơn theo Mẫu 08 Phụ lục I",
        "loaiBan": _LOAI_BAN,
        "documentName": "Đơn đề nghị cấp giấy phép hành nghề (Mẫu 08 PL I NĐ 96/2023)",
    },
    _VANBANG: {
        "componentName": "Văn bằng chuyên môn",  # mục b — bản sao văn bằng chuyên môn.
        "loaiBan": _LOAI_BAN,
        "documentName": "Bản sao văn bằng chuyên môn (bằng tốt nghiệp/cử nhân)",
    },
    _SUCKHOE: {
        "componentName": "giấy khám sức khỏe do cơ sở khám bệnh",  # mục d.
        "loaiBan": _LOAI_BAN,
        "documentName": "Giấy khám sức khỏe",
    },
    _SYLL: {
        "componentName": "Sơ yếu lý lịch tự thuật của người hành nghề",
        "loaiBan": _LOAI_BAN,
        "documentName": "Sơ yếu lý lịch tự thuật của người hành nghề (Mẫu 09 PL I)",
    },
    _THUCHANH: {
        "componentName": "giấy xác nhận hoàn thành quá trình thực hành theo Mẫu 07",  # mục g.
        "loaiBan": _LOAI_BAN,
        "documentName": "Giấy xác nhận hoàn thành quá trình thực hành (Mẫu 07 PL I)",
    },
    _ANH: {
        "componentName": "02 ảnh chân dung cỡ 04 cm",  # mục h.
        "loaiBan": _LOAI_BAN,
        "documentName": "02 ảnh chân dung 4x6 nền trắng",
    },
}
# CCCD chỉ dùng ở bước thông tin, KHÔNG có dòng riêng trên bảng thành phần hồ sơ → bỏ qua.
_SKIP_DOCS = {_CCCD}
_ALLOWED_DOC_TYPES = set(_ROWS) | _SKIP_DOCS | {_OTHER}


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
        "documentName": file_name if detected_type == _OTHER else row["documentName"],
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
        if doc_type in _SKIP_DOCS:
            classified.append({"fileName": file_name, "docType": doc_type, "source": source, "skipped": True})
            continue

        # Không xếp được loại → dồn vào dòng Đơn chứ KHÔNG bỏ: bảng không có dòng "giấy tờ khác", mà
        # bỏ tệp là hồ sơ thiếu giấy người dân đã đưa.
        items.append(_build_row_item(file, idx, _DON, detected_type=_OTHER))
        classified.append({"fileName": file_name, "docType": _OTHER, "source": source, "fallbackRow": _DON})
        fallback.append(file_name)

    if fallback:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã đính kèm chung vào dòng Đơn (mục a) để không bỏ sót — cán bộ "
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

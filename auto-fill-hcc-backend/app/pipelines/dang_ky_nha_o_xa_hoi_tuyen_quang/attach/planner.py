"""Đính kèm bước "Thành phần hồ sơ" cho "Tuyên Quang - Đăng ký mua, thuê mua, thuê nhà ở xã hội…" (cổng DVC Bộ Xây dựng
dvc.moc.gov.vn — Angular mat-table, engine FE `attp-row`).

Bảng 7 dòng, cổng tick sẵn cả 7 nên dòng không đính phải bỏ tick (untickUnplannedRows):

  dòng 1 Mus05 : điều kiện về thu nhập (khoản 5)            ← mau_05
  dòng 2 Mus01 : đối tượng (khoản 9, 10, 11)                ← mau_01
  dòng 3 Mus01a: đối tượng, thu nhập (khoản 5, 6, 8)        ← doi_tuong_thu_nhap (văn bản BHXH, xác nhận thu nhập)
  dòng 4 Mus07 : vay vốn tại tổ chức tín dụng               ← vay_von_tin_dung
  dòng 5 Mus06 : vay vốn qua Ngân hàng Chính sách xã hội    ← vay_von_ngan_hang_csxh
  dòng 6 Mus03 : điều kiện nhà ở, có nhà dưới 15 m²/người   ← mau_03
  dòng 7 Mus02 : điều kiện về nhà ở                         ← mau_02 + giấy tờ kèm

KHÔNG TÁCH FILE: bộ hồ sơ thường là một PDF gộp. File có giấy của dòng nào thì đính NGUYÊN FILE vào dòng đó, nên một file
có thể vào hai dòng (vd dòng 3 và dòng 7). Giấy Chứng nhận, CCCD, CT07, giấy tờ hôn nhân không có dòng riêng, đi theo dòng
nhà ở: dòng 7, hoặc dòng 6 khi hồ sơ chỉ có Mẫu 03. "Loại bản" mỗi dòng chỉ chọn được một nên luôn là Bản chính.

Tên dòng 7 là TIỀN TỐ của tên dòng 6. FE so substring hai chiều nên dòng 7 mang thêm dấu chấm cuối: dòng 7 nằm trọn trong
componentName, còn dòng 6 thì không, bảng có đổi thứ tự dòng cũng không rơi nhầm sang dòng 6.

Văn bản BHXH thường nằm cuối PDF gộp nên phải OCR đủ trang, không dùng cách chỉ đọc vài trang đầu. Bước điền đã OCR cùng
cách nên ở đây chỉ đọc lại cache.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.documents import representative_excerpt
from app.pipelines.dang_ky_bien_dong_thoa_thuan_thanh_vien_ho_gia_dinh_da_nang.process.runner import (
    _ocr_split_large_pdfs,
)
from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.attach.planner import _LLM_TEXT_MAX_CHARS
from app.pipelines.dang_ky_nha_o_xa_hoi_tuyen_quang.attach.prompt import SYSTEM_PROMPT, build_user_prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_MAU_02 = "mau_02"
_MAU_03 = "mau_03"
_GIAY_CHUNG_NHAN = "giay_chung_nhan"
_CCCD = "cccd"
_CU_TRU = "cu_tru"
_HON_NHAN = "hon_nhan"
_DOI_TUONG_THU_NHAP = "doi_tuong_thu_nhap"
_MAU_01 = "mau_01"
_MAU_05 = "mau_05"
_VAY_VON_TIN_DUNG = "vay_von_tin_dung"
_VAY_VON_NGAN_HANG_CSXH = "vay_von_ngan_hang_csxh"
_OTHER = "other"

_HOUSING_NAME = (
    "Giấy tờ chứng minh điều kiện về nhà ở để được mua, thuê mua nhà ở xã hội/nhà ở cho lực lượng vũ trang nhân dân"
)
_ROW_INCOME = 3
_ROW_SMALL_HOUSE = 6
_ROW_HOUSING = 7

# STT -> dòng trên cổng. name là đoạn chữ khớp một dòng duy nhất của cột "Tên giấy tờ".
_ROWS: dict[int, dict[str, str]] = {
    1: {"name": "Giấy tờ chứng minh điều kiện về thu nhập để được mua, thuê mua nhà ở xã hội",
        "documentName": "Giấy tờ chứng minh điều kiện về thu nhập"},
    2: {"name": "Giấy tờ chứng minh đối tượng được hưởng chính sách hỗ trợ về nhà ở xã hội",
        "documentName": "Giấy tờ chứng minh đối tượng"},
    3: {"name": "Giấy tờ chứng minh đối tượng, thu nhập để được hưởng chính sách hỗ trợ về nhà ở xã hội",
        "documentName": "Giấy tờ chứng minh đối tượng, thu nhập"},
    4: {"name": "Giấy tờ chứng minh điều kiện vay vốn ưu đãi của Nhà nước tại tổ chức tín dụng",
        "documentName": "Giấy tờ chứng minh điều kiện vay vốn tại tổ chức tín dụng"},
    5: {"name": "Giấy tờ chứng minh điều kiện vay vốn ưu đãi của Nhà nước thông qua Ngân hàng Chính sách xã hội",
        "documentName": "Giấy tờ chứng minh điều kiện vay vốn qua Ngân hàng Chính sách xã hội"},
    6: {"name": f"{_HOUSING_NAME} (trường hợp có nhà ở nhưng diện tích nhà ở bình quân đầu người thấp hơn 15m2",
        "documentName": "Giấy tờ chứng minh điều kiện về nhà ở (dưới 15m2 sàn/người)"},
    7: {"name": f"{_HOUSING_NAME}.", "documentName": "Giấy tờ chứng minh điều kiện về nhà ở"},
}

_TYPE_ROW: dict[str, int] = {
    _MAU_05: 1,
    _MAU_01: 2,
    _DOI_TUONG_THU_NHAP: _ROW_INCOME,
    _VAY_VON_TIN_DUNG: 4,
    _VAY_VON_NGAN_HANG_CSXH: 5,
    _MAU_03: _ROW_SMALL_HOUSE,
    _MAU_02: _ROW_HOUSING,
}
# Không có dòng riêng: đi theo dòng nhà ở của hồ sơ.
_SUPPORTING = {_GIAY_CHUNG_NHAN, _CCCD, _CU_TRU, _HON_NHAN}
_ALLOWED = set(_TYPE_ROW) | _SUPPORTING | {_OTHER}


def _doc_types(item: dict) -> list[str]:
    raw = item.get("docTypes")
    if raw is None:
        raw = item.get("docType") or item.get("type")
    out: list[str] = []
    for value in raw if isinstance(raw, list) else [raw]:
        folded = _fold(str(value or ""))
        doc_type = next((allowed for allowed in _ALLOWED if folded == _fold(allowed)), _OTHER)
        if doc_type not in out:
            out.append(doc_type)
    return out


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, list[str]]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=900, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    result: dict[int, list[str]] = {}
    for item in parsed.get("documents", []) or []:
        try:
            result[int(item.get("index"))] = _doc_types(item)
        except (TypeError, ValueError, AttributeError):
            continue
    return result


def _housing_row(types_by_file: list[list[str]]) -> int:
    """Hồ sơ chỉ có Mẫu 03 (có nhà dưới 15 m²/người) thì giấy tờ kèm theo dòng 6, còn lại theo dòng 7."""
    types = {doc_type for doc_types in types_by_file for doc_type in doc_types}
    return _ROW_SMALL_HOUSE if _MAU_03 in types and _MAU_02 not in types else _ROW_HOUSING


def _rows_of(doc_types: list[str], housing_row: int) -> list[int]:
    rows = {_TYPE_ROW[item] for item in doc_types if item in _TYPE_ROW}
    if any(item in _SUPPORTING for item in doc_types):
        rows.add(housing_row)
    return sorted(rows) or [housing_row]


def _item(file_index: int, file_name: str, row: int, document_name: str, doc_type: str) -> dict:
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": _ROWS[row]["name"],
        "componentIndex": row,
        "loaiBan": "Bản chính",
        "target": "attp-row",
        "untickUnplannedRows": True,
        "needsAddComponent": False,
        "detectedType": doc_type,
    }


def _dedupe_document_names(items: list[dict]) -> None:
    """Engine đặt tên tệp tải lên theo documentName và chống trùng trong từng dòng: tên trùng trong CÙNG dòng phải đánh số.
    Khác dòng thì trùng tên không sao, file gộp giữ nguyên tên gốc ở cả hai dòng."""
    total: dict[tuple[int, str], int] = {}
    for item in items:
        key = (item["componentIndex"], item["documentName"])
        total[key] = total.get(key, 0) + 1
    counter: dict[tuple[int, str], int] = {}
    for item in items:
        key = (item["componentIndex"], item["documentName"])
        if total[key] < 2:
            continue
        counter[key] = counter.get(key, 0) + 1
        item["documentName"] = f"{item['documentName']} ({counter[key]})"


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict] | None = None,
    llm_types: dict[int, list[str] | str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    del ocr_results  # OCR chỉ để nuôi LLM; planner không tự đọc chữ để đoán loại.
    llm_types = llm_types or {}
    types_by_file = [
        _doc_types({"docTypes": llm_types[index]}) if llm_types.get(index) else [] for index in range(len(files))
    ]
    housing_row = _housing_row(types_by_file)
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    for index, (file, doc_types) in enumerate(zip(files, types_by_file)):
        file_name = str(file.get("name") or f"file-{index + 1}")
        known = [item for item in doc_types if item != _OTHER]
        rows = _rows_of(known, housing_row)
        for row in rows:
            # File gộp giữ tên gốc để cán bộ nhận ra đó là cả bộ hồ sơ, không chỉ một giấy.
            name = file_name if len(known) != 1 else _ROWS[row]["documentName"]
            attachments.append(_item(index, file_name, row, name, known[0] if len(known) == 1 else _OTHER))
        classified.append({"fileName": file_name, "docTypes": doc_types, "rows": rows,
                           "source": "llm" if doc_types else "unknown"})
        if not known:
            warnings.append(
                f"Chưa nhận diện chắc loại giấy tờ cho '{file_name}' — tạm đính vào dòng {housing_row} "
                f"({_ROWS[housing_row]['documentName']}); cán bộ kiểm tra lại."
            )
        elif len(rows) > 1:
            warnings.append(
                f"'{file_name}' gộp nhiều giấy tờ — đính nguyên file vào các dòng "
                f"{', '.join(str(row) for row in rows)}, không tách trang; Loại bản chọn Bản chính."
            )

    _dedupe_document_names(attachments)
    types = {doc_type for doc_types in types_by_file for doc_type in doc_types}
    if _DOI_TUONG_THU_NHAP in types:
        warnings.append(
            f"Giấy tờ đối tượng, thu nhập đã đính dòng {_ROW_INCOME}. Người kê khai thuộc khoản 5 Điều 76, không có hợp "
            "đồng lao động và không hưởng lương hưu thì cán bộ chuyển sang dòng 1."
        )
    if _MAU_02 in types:
        warnings.append(
            "Hồ sơ dùng Mẫu số 02 (chưa có nhà ở) — kiểm tra trên cổng không chọn trường hợp có nhà ở dưới 15 m²/người."
        )
    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    ocr_files = [item for item in raw_files if item.get("type") in _OCR_TYPES]
    errors: list[str] = []

    started = time.monotonic()
    ocr_results = await _ocr_split_large_pdfs(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    by_name = {item.get("name"): item for item in ocr_results}
    llm_documents = [
        {"index": index, "text": representative_excerpt(str(by_name[file.get("name")].get("text")),
                                                        _LLM_TEXT_MAX_CHARS)}
        for index, file in enumerate(raw_files)
        if str(by_name.get(file.get("name"), {}).get("text") or "").strip()
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
            "ocrDocuments": [item.get("name") for item in ocr_results if item.get("text")],
            "llmDocuments": [raw_files[item["index"]]["name"] for item in llm_documents],
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

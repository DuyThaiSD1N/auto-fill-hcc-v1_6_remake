"""Đính kèm 1.115684 (Lào Cai, cổng iGate mới) — chế độ ĐÍNH NGUYÊN TỆP (tắt "Tách giấy tờ"; chế độ tách gọi lại planner
này trên các PDF con, xem ../dinh_kem_tach/planner.py).

Bước 2 "Thành phần hồ sơ hệ thống" (ảnh người dùng gửi 25/11/2026, UBND Phường Cam Đường): bảng mat-table MỘT dòng
   1 Đơn theo Mẫu số 01 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND — "1 Bản chính"
mỗi dòng mat-checkbox + "Scan tệp tin"/"Chọn tệp tin", có "Chọn/Bỏ chọn tất cả" và nút "Thêm giấy tờ", không có dòng
"giấy tờ khác". Thủ tục chỉ yêu cầu Đơn (nhân thân, cư trú cơ quan khai thác từ CSDLQG về dân cư) → MỌI tệp vào dòng Đơn
(mỗi tệp vẫn là một tệp riêng); giấy kèm theo (CCCD, xác nhận cư trú/công tác) được cảnh báo để cán bộ tự quyết có cần
tách dòng bằng "Thêm giấy tờ" không. Không bỏ tệp nào.

Có một dòng nên không cần LLM phân loại: chữ OCR chỉ dùng để đặt tên tài liệu (Đơn / Căn cước / giấy kèm theo) và báo
thiếu Đơn. Engine FE "attp-row" + untickUnplannedRows dùng chung với cho_thue_dat_thue_rung_igate_lao_cai.
"""

import time

from app.pipelines._shared import fold
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.cho_thue_dat_thue_rung_igate_lao_cai.attach import planner as _igate
from app.process.schemas import FileItem
from app.services import ocr

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_GIOI_HAN_BYTE = 6 * 1024 * 1024

_DEFAULT_ROWS = ["Đơn theo Mẫu số 01 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND"]
_DON_KEYS = ["mau so 01", "don de nghi"]

_T_DON, _T_CCCD, _T_OTHER = "don_mau_01", "cccd", "other"
_TEN = {
    _T_DON: "Đơn đề nghị giao đất (Mẫu số 01)",
    _T_CCCD: "Căn cước",
    _T_OTHER: "Giấy tờ kèm theo",
}
_DAU_HIEU_CCCD = ("can cuoc", "citizen identity", "identity card", "personal identification", "idvnm",
                  "chung minh nhan dan")


def _loai(text: str) -> str:
    """Đơn xét TRƯỚC: thân Đơn có cụm "thẻ căn cước số …"."""
    folded = fold(text or "")
    if "giao dat" in folded and ("don de nghi" in folded or "mau so 01" in folded):
        return _T_DON
    if any(key in folded for key in _DAU_HIEU_CCCD):
        return _T_CCCD
    return _T_OTHER


def _kich_thuoc(file: dict) -> int:
    """Kích thước thật, suy từ độ dài base64 của dataUrl (FileItem không mang size)."""
    payload = str(file.get("dataUrl") or "").partition(",")[2]
    return len(payload) * 3 // 4 - payload[-2:].count("=") if payload else 0


def build_plan_items(
    files: list[dict],
    texts: dict[int, str] | None = None,
    components: list[dict] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    texts = texts or {}
    rows = _igate._portal_rows(components) or [(i + 1, n, fold(n)) for i, n in enumerate(_DEFAULT_ROWS)]
    don = _igate._find(_DON_KEYS, rows) or rows[0]
    warnings: list[str] = []

    attachments: list[dict] = []
    classified: list[dict] = []
    kem_theo: list[str] = []
    co_don = False
    tong_byte = 0
    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        doc_type = _loai(texts.get(index, ""))
        co_don = co_don or doc_type == _T_DON
        if doc_type != _T_DON:
            kem_theo.append(file_name)
        tong_byte += _kich_thuoc(file)
        attachments.append(_igate._item(index, file_name, _TEN[doc_type], don, doc_type))
        classified.append({"fileName": file_name, "docType": doc_type, "documentName": _TEN[doc_type],
                           "source": "ocr" if texts.get(index) else "default", "componentIndex": don[0]})

    if attachments and not co_don:
        warnings.append(
            "Chưa nhận ra Đơn đề nghị giao đất (Mẫu số 01) trong các tệp tải lên — đây là thành phần hồ sơ bắt buộc "
            "duy nhất của thủ tục. Mọi tệp đã đính vào dòng Đơn, cán bộ kiểm tra lại."
        )
    elif kem_theo:
        warnings.append(
            "Thủ tục chỉ yêu cầu Đơn theo Mẫu số 01; giấy tờ kèm theo đã đính chung dòng Đơn (vẫn là tệp riêng) — "
            f"nếu nơi tiếp nhận yêu cầu tách, cán bộ dùng nút \"Thêm giấy tờ\" của cổng: {', '.join(kem_theo)}."
        )
    if tong_byte > _GIOI_HAN_BYTE:
        warnings.append(
            f"Tổng dung lượng các tệp đính vào dòng Đơn là {tong_byte / 1024 / 1024:.1f} MB, vượt giới hạn 6 MB của "
            "cổng — cần nén PDF hoặc giảm DPI trước khi nộp."
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
    texts = {
        index: str(by_name.get(file.get("name"), {}).get("text") or "")
        for index, file in enumerate(raw_files)
        if str(by_name.get(file.get("name"), {}).get("text") or "").strip()
    }
    attachments, warnings, classified = build_plan_items(raw_files, texts, components)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "portalRows": len(_igate._portal_rows(components)),
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": 0, "total_latency_ms": ocr_ms},
        "ocr_text": join_ocr_documents(ocr_results),
        "errors": errors,
    }

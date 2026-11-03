"""Đính kèm cho [Lào Cai - cổng iGate mới] đăng ký đất đai, cấp GCN lần đầu hộ gia đình, cá nhân (1.115689).

Phân loại giữ NGUYÊN của pipeline cổng cũ (dang_ky_dat_dai_lan_dau_ho_gia_dinh_lao_cai/attach: OCR → LLM từng tệp →
docType + alsoTypes; chọn nhóm tất định: có Thông báo xác nhận kết quả đăng ký → nhóm c, còn lại nhóm a, không tự chọn
nhóm b; tệp gộp phủ dòng còn trống, ưu tiên Đơn Mẫu 21).

Bước 2 "Thành phần hồ sơ hệ thống" của cổng mới (crawl 02/11/2026, UBND Phường Yên Bái) là bảng PHẲNG 26 dòng, cổng TÍCH
SẴN cả 26, KHÔNG còn dòng tiêu đề nhóm và KHÔNG còn "Giấy tờ khác":
   1–16  nhóm a) hộ gia đình, cá nhân (cổng cũ: slot 1–16)
   17–24 nhóm b) người gốc Việt Nam định cư ở nước ngoài (cổng cũ: slot 18–25)
   25–26 nhóm c) đã có Thông báo xác nhận kết quả đăng ký đất đai (cổng cũ: slot 27–28)
Ba dòng Đơn Mẫu 21 TRÙNG TÊN → bắt buộc đi theo VỊ TRÍ dòng (componentIndex), không dò theo tên. untickUnplannedRows bỏ
chọn mọi dòng không có tệp, nên hai nhóm còn lại tự trống. Giấy tờ ngoài danh mục (hoặc loại mà nhóm đang chọn không có
dòng) → dòng Đơn của nhóm, giữ tên + cảnh báo dùng nút "Thêm giấy tờ". Không bỏ tệp nào.

Engine FE "attp-row" dùng chung với cho_thue_dat_thue_rung_igate_lao_cai.
"""

import time

from app.pipelines._shared import fold
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.cho_thue_dat_thue_rung_igate_lao_cai.attach import planner as _igate
from app.pipelines.dang_ky_dat_dai_lan_dau_ho_gia_dinh_lao_cai.attach import planner as _goc
from app.process.schemas import FileItem
from app.services import ocr

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
# Cổng Lào Cai: "Dung lượng tối đa là 6 Mb".
_GIOI_HAN_BYTE = 6 * 1024 * 1024
_SO_DONG = 26

# slot cổng cũ (có 3 dòng tiêu đề nhóm 0/17/26) → dòng cổng mới (không có tiêu đề).
_LECH_NHOM = {_goc._NHOM_A: 0, _goc._NHOM_B: 1, _goc._NHOM_C: 2}

Row = _igate.Row


def _dong_moi(slot_cu: int, nhom: str) -> int:
    return slot_cu - _LECH_NHOM[nhom]


def _rows(components: list[dict] | None) -> list[Row]:
    rows = _igate._portal_rows(components)
    if len(rows) == _SO_DONG:
        return rows
    # Không có danh sách dòng của trang (hoặc lệch số dòng) → dựng theo vị trí, tên lấy từ catalog cổng cũ.
    names = {_dong_moi(slot, nhom): _goc._SLOT_NAMES[slot]
             for routes in _goc._ROUTES.values() for nhom, slot in routes.items()}
    return [(i, names.get(i, f"Dòng {i}"), fold(names.get(i, ""))) for i in range(1, _SO_DONG + 1)]


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, tuple[str, list[str]] | str] | None = None,
    components: list[dict] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    rows = _rows(components)
    by_index = {row[0]: row for row in rows}
    warnings: list[str] = []

    resolved: list[tuple[int, str, str, list[str], str]] = []
    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        raw = llm_types.get(index)
        doc_type, also = raw if isinstance(raw, tuple) else (raw, [])
        if doc_type not in _goc._ALLOWED:
            doc_type = "other"
        also = _goc._normalize_also(also, doc_type) if doc_type != "other" else []
        resolved.append((index, file_name, doc_type, also, "llm" if index in llm_types else "default"))

    nhom = _goc._chon_nhom([t for _, _, t, _, _ in resolved])
    don = by_index[_dong_moi(_goc._ROUTES["don_mau_21"][nhom], nhom)]

    attachments: list[dict] = []
    classified: list[dict] = []
    ngoai_bang: list[str] = []
    thay_the: list[str] = []
    da_dung: set[str] = set()
    bytes_per_row: dict[int, int] = {}
    for index, file_name, doc_type, also, source in resolved:
        chon = None
        if doc_type != "other":
            # Mỗi tệp CHỈ một dòng; tệp gộp phủ dòng còn trống, ưu tiên Đơn Mẫu 21. Chỉ xét loại có dòng trong nhóm.
            ung_vien = [t for t in _goc._ROW_PRIORITY
                        if t in (doc_type, *also) and nhom in _goc._ROUTES[t] and t not in da_dung]
            chon = ung_vien[0] if ung_vien else (doc_type if nhom in _goc._ROUTES[doc_type] else None)
        if chon is None:
            row = don
            document_name = (_goc._other_component_name(file_name) if doc_type == "other"
                             else _goc._DISPLAY[doc_type])
            ngoai_bang.append(f"{file_name} → \"{document_name}\"")
        else:
            row = by_index[_dong_moi(_goc._ROUTES[chon][nhom], nhom)]
            document_name = _goc._DISPLAY[chon]
            da_dung.add(chon)
            if chon == "ban_mo_ta_ranh_gioi":
                thay_the.append(file_name)
        bytes_per_row[row[0]] = bytes_per_row.get(row[0], 0) + _kich_thuoc(files[index])
        attachments.append(_igate._item(index, file_name, document_name, row, doc_type))
        classified.append({"fileName": file_name, "docType": doc_type, "alsoTypes": also, "assignedType": chon,
                           "nhom": nhom, "source": source, "componentIndex": row[0]})

    if attachments:
        warnings.append(
            f"Hồ sơ được xếp theo NHÓM {nhom.upper()}) "
            + ("(đã có Thông báo xác nhận kết quả đăng ký đất đai)." if nhom == _goc._NHOM_C
               else "(hộ gia đình, cá nhân, cộng đồng dân cư).")
            + " Trợ lý chỉ tích các dòng có tệp của nhóm này. Người sử dụng đất là NGƯỜI GỐC VIỆT NAM ĐỊNH CƯ Ở NƯỚC "
              "NGOÀI thì cán bộ chuyển tệp sang các dòng 17–24 (nhóm b), hệ thống không tự nhận ra điều này từ giấy tờ."
        )
    if thay_the:
        warnings.append(
            "ĐÍNH KÈM THAY THẾ: " + ", ".join(thay_the) + " là Bản mô tả ranh giới, mốc giới thửa đất (không phải mảnh "
            "trích đo) nhưng được đính vào dòng \"Mảnh trích đo bản đồ địa chính thửa đất (nếu có)\" — BẮT BUỘC ghi rõ "
            "việc này vào ô \"Ghi chú\"."
        )
    if ngoai_bang:
        warnings.append(
            "Giấy tờ không có dòng riêng trong nhóm đã chọn hoặc chưa rõ loại đã tạm đính vào dòng Đơn đăng ký (vẫn là "
            "tệp riêng, giữ tên) vì cổng mới không còn danh sách \"Giấy tờ khác\" — nếu cần tách riêng, cán bộ dùng nút "
            f"\"Thêm giấy tờ\" của cổng: {', '.join(ngoai_bang)}."
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


def _kich_thuoc(file: dict) -> int:
    """Số byte của tệp từ dataUrl base64 (pipeline cổng cũ không tính dung lượng)."""
    payload = "".join(str(file.get("dataUrl") or "").partition(",")[2].split())
    if not payload:
        return 0
    return max(0, (len(payload) * 3) // 4 - (len(payload) - len(payload.rstrip("="))))


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
        if str(by_name.get(file.get("name"), {}).get("text") or "").strip()
    ]
    started = time.monotonic()
    llm_types: dict[int, tuple[str, list[str]]] = {}
    if llm_documents:
        try:
            llm_types = await _goc._classify_with_llm(llm_documents, errors)
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
            "llmDocuments": [raw_files[d["index"]]["name"] for d in llm_documents],
            "portalRows": len(_igate._portal_rows(components)),
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "ocr_text": join_ocr_documents(ocr_results),
        "errors": errors,
    }

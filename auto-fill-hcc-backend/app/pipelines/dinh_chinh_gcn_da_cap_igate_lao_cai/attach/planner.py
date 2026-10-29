"""Đính kèm cho [Lào Cai - cổng iGate mới] đính chính Giấy chứng nhận đã cấp lần đầu có sai sót (1.115686).

Phân loại giữ NGUYÊN của pipeline cổng cũ (dinh_chinh_gcn_da_cap_lao_cai/attach: OCR → LLM từng tệp → docType + alsoTypes;
tệp gộp phủ dòng còn trống, ưu tiên Đơn) và tên tài liệu của cổng cũ.

Bước 2 "Thành phần hồ sơ hệ thống" của cổng mới (crawl 29/10/2026, UBND phường) là CÙNG bảng 4 dòng như cổng cũ, cổng
TÍCH SẴN cả 4, KHÔNG có dòng "giấy tờ khác":
   1 Đơn đăng ký biến động đất đai Mẫu số 24 · 2 Bản gốc Giấy chứng nhận đã cấp
   3 Giấy tờ chứng minh sai sót thông tin (thường là CCCD) · 4 Văn bản về việc ủy quyền
⚠ Bản crawl ghi componentName dòng 2 là "scannerScan tệp tin…" (đọc nhầm ô nút); dò tên không ra thì lấy theo VỊ TRÍ
dòng khi bảng đúng 4 dòng. Tài liệu chưa rõ loại (cổng cũ xuống "Giấy tờ khác") → dòng Đơn, giữ tên + cảnh báo. Không bỏ
tệp nào.

Engine FE "attp-row" + untickUnplannedRows dùng chung với cho_thue_dat_thue_rung_igate_lao_cai.
"""

import time

from app.pipelines._shared import fold
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.cho_thue_dat_thue_rung_igate_lao_cai.attach import planner as _igate
from app.pipelines.dinh_chinh_gcn_da_cap_lao_cai.attach import planner as _goc
from app.process.schemas import FileItem
from app.services import ocr

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# Bảng 4 dòng NGUYÊN VĂN (crawl 29/10/2026; tên dòng 2 lấy từ ô "Tên giấy tờ").
_DEFAULT_ROWS = [
    "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 24 ban hành kèm theo Quyết định số "
    "47/2026/QĐ-UBND",
    "Bản gốc Giấy chứng nhận đã cấp",
    "Giấy tờ chứng minh sai sót thông tin của người được cấp Giấy chứng nhận so với thông tin tại thời điểm đề nghị "
    "đính chính đối với trường hợp không khai thác, sử dụng được thông tin trong Cơ sở dữ liệu quốc gia về dân cư, Cơ "
    "sở dữ liệu quốc gia về đăng ký doanh nghiệp hoặc sai sót thông tin về thửa đất, tài sản gắn liền với đất so với "
    "thông tin trên Giấy chứng nhận đã cấp",
    "Văn bản về việc ủy quyền theo quy định của pháp luật về dân sự đối với trường hợp thực hiện thủ tục thông qua "
    "người đại diện",
]
# docType → từ khoá dò dòng; vị trí mặc định = _goc._ROUTES (0-based).
_ROW_KEYS: dict[str, list[str]] = {
    _goc._T_DON: ["mau so 24", "don dang ky bien dong"],
    _goc._T_GCN: ["ban goc giay chung nhan"],
    _goc._T_CHUNG_MINH: ["chung minh sai sot"],
    _goc._T_UY_QUYEN: ["van ban ve viec uy quyen"],
}

Row = _igate.Row


def _default_rows() -> list[Row]:
    return [(i + 1, name, fold(name)) for i, name in enumerate(_DEFAULT_ROWS)]


def _row(doc_type: str, rows: list[Row]) -> Row | None:
    found = _igate._find(_ROW_KEYS[doc_type], rows)
    if found is None and len(rows) == len(_DEFAULT_ROWS):
        found = rows[_goc._ROUTES[doc_type]]
    return found


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, tuple[str, list[str]] | str] | None = None,
    components: list[dict] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    rows = _igate._portal_rows(components) or _default_rows()
    warnings: list[str] = []
    don = _row(_goc._T_DON, rows) or rows[0]

    attachments: list[dict] = []
    classified: list[dict] = []
    unknown: list[str] = []
    da_dung: set[str] = set()
    by_row: dict[int, list[str]] = {}
    bytes_per_row: dict[int, int] = {}
    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        raw = llm_types.get(index)
        doc_type, also = raw if isinstance(raw, tuple) else (raw, [])
        if doc_type not in _goc._ALLOWED:
            doc_type = _goc._T_OTHER
        also = _goc._normalize_also(also, doc_type) if doc_type != _goc._T_OTHER else []
        if doc_type == _goc._T_OTHER:
            chon, row = _goc._T_OTHER, don
            base = _goc._other_component_name(file_name)
            unknown.append(f"{file_name} → \"{base}\"")
        else:
            # Mỗi tệp CHỈ một dòng; tệp gộp phủ dòng còn trống, ưu tiên Đơn Mẫu 24 (như cổng cũ).
            ung_vien = [t for t in _goc._ROW_PRIORITY if t in (doc_type, *also) and t not in da_dung]
            chon = ung_vien[0] if ung_vien else doc_type
            da_dung.add(chon)
            row = _row(chon, rows) or don
            base = _goc._DISPLAY[chon]
        document_name = base  # trùng tên trong cùng dòng → _dedupe_document_names đánh số ở cuối
        by_row.setdefault(row[0], []).append(file_name)
        bytes_per_row[row[0]] = bytes_per_row.get(row[0], 0) + (_goc._kich_thuoc(file) or 0)
        attachments.append(_igate._item(index, file_name, document_name, row, doc_type))
        classified.append({"fileName": file_name, "docType": doc_type, "alsoTypes": also, "assignedType": chon,
                           "source": "llm" if index in llm_types else "default", "componentIndex": row[0]})

    gcn_row = _row(_goc._T_GCN, rows)
    if gcn_row and gcn_row[0] in by_row:
        warnings.append(
            "Một tệp scan có thể gộp nhiều Giấy chứng nhận — ghi rõ tệp gồm mấy Giấy chứng nhận và trang của từng cái "
            "vào ô \"Ghi chú\" để cán bộ đối chiếu."
        )
    if _goc._T_CHUNG_MINH not in da_dung:
        warnings.append(
            "Chưa có tệp ở dòng \"Giấy tờ chứng minh sai sót thông tin của người được cấp Giấy chứng nhận\" — thường "
            "là CĂN CƯỚC CÔNG DÂN của người có thông tin bị sai. Bắt buộc khi cơ quan không khai thác được Cơ sở dữ "
            "liệu quốc gia về dân cư."
        )
    if unknown:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã tạm đính vào dòng Đơn (vẫn là tệp riêng, giữ tên theo tệp) vì cổng mới "
            "không có dòng \"giấy tờ khác\" — nếu cần tách riêng, cán bộ dùng nút \"Thêm giấy tờ\" của cổng: "
            f"{', '.join(unknown)}."
        )
    for row_index, total in sorted(bytes_per_row.items()):
        if total > _goc._GIOI_HAN_BYTE:
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

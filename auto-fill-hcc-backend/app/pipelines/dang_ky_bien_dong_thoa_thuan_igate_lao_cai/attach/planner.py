"""Đính kèm cho [Lào Cai - cổng iGate mới] đăng ký biến động theo thỏa thuận, tài sản công, bản án… (1.115671).

Phân loại và cách chọn nhóm giữ NGUYÊN pipeline cổng cũ (dang_ky_bien_dong_lao_cai/attach: OCR → LLM → nhãn catalog +
nhóm; nhóm theo VĂN BẢN CĂN CỨ, không có thì theo LLM, không nữa → nhóm (1)). Chỉ cách đặt tệp vào bảng là khác.

Bước 2 "Thành phần hồ sơ hệ thống" (crawl 29/10/2026, Sở NN&MT Lào Cai): MỘT bảng 30 dòng, cổng TÍCH SẴN cả 30, KHÔNG
còn dòng tiêu đề nhóm, KHÔNG có dòng "giấy tờ khác". Năm nhóm × 6 dòng, đúng THỨ TỰ dòng của catalog cổng cũ, mỗi nhóm
mở đầu bằng dòng Đơn Mẫu số 24:
   1–6   (1) thỏa thuận hộ gia đình/vợ chồng   · 7–12  (2) công trình ngầm   · 13–18 (3) tài sản công
   19–24 (4) tranh chấp, bản án, trọng tài    · 25–30 (5) xử lý tài sản thế chấp
Đơn/GCN/Bản vẽ/Trích đo/Đại diện lặp y hệt ở cả 5 nhóm → khoanh nhóm theo dòng Đơn, dò từ khoá trong nhóm (không khớp
thì lấy theo vị trí trong nhóm của catalog cũ) và gửi componentIndex để FE chọn đúng dòng. Giấy tờ không có dòng trong
nhóm (cổng cũ xuống "Giấy tờ khác") → dòng Đơn của nhóm, giữ tên + cảnh báo. CCCD không phải thành phần hồ sơ → bỏ
qua như cổng cũ.

Engine FE "attp-row" + untickUnplannedRows dùng chung với cho_thue_dat_thue_rung_igate_lao_cai.
"""

import time

from app.pipelines._shared import fold
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.cho_thue_dat_thue_rung_igate_lao_cai.attach import planner as _igate
from app.pipelines.dang_ky_bien_dong_lao_cai.attach import catalog
from app.pipelines.dang_ky_bien_dong_lao_cai.attach import planner as _goc
from app.process.schemas import FileItem
from app.services import ocr

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON = "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 24 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND"
_GCN = "Giấy chứng nhận đã cấp"
_BAN_VE = (
    "Bản vẽ tách thửa đất, hợp thửa đất theo Mẫu số 28 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND đối với trường "
    "hợp đăng ký biến động đất đai mà phải tách thửa đất, hợp thửa đất"
)
_TRICH_DO = (
    "Mảnh trích đo bản đồ địa chính thửa đất đối với trường hợp người sử dụng đất có nhu cầu đo đạc để xác định lại kích "
    "thước các cạnh, diện tích của thửa đất"
)
_DAI_DIEN = (
    "Văn bản về việc đại diện theo quy định của pháp luật về dân sự đối với trường hợp thực hiện thủ tục đăng ký đất "
    "đai, tài sản gắn liền với đất thông qua người đại diện"
)
# Bảng 30 dòng (crawl 29/10/2026; dòng căn cứ của nhóm 1/4/5 bị cắt ở 600 ký tự — FE so chuỗi con nên vẫn khớp).
_DEFAULT_ROWS = [
    _DON, _GCN,
    "Văn bản thỏa thuận về việc thay đổi quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất theo thỏa thuận của "
    "các thành viên hộ gia đình hoặc của vợ và chồng.",
    _BAN_VE, _TRICH_DO, _DAI_DIEN,
    _DON, _GCN,
    "Văn bản về việc cho phép thay đổi quyền sử dụng đất xây dựng công trình trên mặt đất phục vụ cho việc vận hành, "
    "khai thác sử dụng công trình ngầm, quyền sở hữu công trình ngầm của cơ quan, người có thẩm quyền",
    _BAN_VE, _TRICH_DO, _DAI_DIEN,
    _DON, _GCN,
    "Văn bản cho phép bán tài sản, điều chuyển, chuyển nhượng quyền sử dụng đất, tài sản gắn liền với đất của cơ quan "
    "có thẩm quyền",
    "Hợp đồng mua bán tài sản công là quyền sử dụng đất, tài sản gắn liền với đất theo quy định của pháp luật đối với "
    "trường hợp bán tài sản, chuyển nhượng quyền sử dụng đất là tài sản công",
    _BAN_VE, _DAI_DIEN + ".",
    _DON, _GCN,
    "Một trong các văn bản sau: + Biên bản hòa giải thành hoặc văn bản công nhận kết quả hòa giải thành được cơ quan "
    "có thẩm quyền công nhận.",
    _BAN_VE, _TRICH_DO, _DAI_DIEN,
    _DON, _GCN,
    "Một trong các văn bản sau: + Hợp đồng chuyển nhượng quyền sử dụng đất, tài sản gắn liền với đất giữa người sử "
    "dụng đất, chủ sở hữu tài sản gắn liền với đất với người nhận chuyển nhượng.",
    _BAN_VE, _TRICH_DO, _DAI_DIEN,
]
_DON_KEYS = ["mau so 24"]

Row = _igate.Row


def _default_rows() -> list[Row]:
    return [(i + 1, name, fold(name)) for i, name in enumerate(_DEFAULT_ROWS)]


def _groups(rows: list[Row]) -> list[list[Row]]:
    groups: list[list[Row]] = []
    for row in rows:
        if any(key in row[2] for key in _DON_KEYS) or not groups:
            groups.append([])
        groups[-1].append(row)
    return groups


def _row_in_group(label: str, group: str, rows: list[Row]) -> Row | None:
    found = catalog.row_for(label, group)
    if not found:
        return None
    keywords, _ = catalog.ROWS[found]
    position = found[1]
    return _igate._find(keywords, rows) or (rows[position - 1] if position <= len(rows) else None)


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, dict[str, str]] | None = None,
    llm_group: str = "",
    components: list[dict] | None = None,
) -> tuple[list[dict], list[str], list[dict], str, str]:
    llm_types = llm_types or {}
    entries: list[dict] = []
    used_names: set[str] = set()
    for index, file in enumerate(files):
        detected = llm_types.get(index) or {}
        label = detected.get("label") or "khac"
        fallback = catalog.display_name(label)
        entries.append({
            "idx": index,
            "fileName": str(file.get("name") or f"file-{index + 1}"),
            "label": label,
            "documentName": _goc._unique_document_name(detected.get("documentName") or fallback, used_names, fallback),
            "bytes": _goc._data_url_size(file.get("dataUrl", "")),
        })

    group, group_source = _goc._pick_group(entries, llm_group)
    groups = _groups(_igate._portal_rows(components) or _default_rows())
    rows = groups[int(group) - 1] if int(group) <= len(groups) else groups[0]

    warnings: list[str] = []
    don = _row_in_group("don_dang_ky", group, rows) or rows[0]
    attachments: list[dict] = []
    classified: list[dict] = []
    skipped: list[str] = []
    ngoai: list[str] = []
    bytes_per_row: dict[int, int] = {}
    for entry in entries:
        base = {"fileName": entry["fileName"], "label": entry["label"], "documentName": entry["documentName"]}
        if entry["label"] in catalog.SKIPPED_LABELS:
            skipped.append(f"{entry['fileName']} ({entry['documentName']})")
            classified.append({**base, "target": "skip", "reason": "not_a_component"})
            continue
        row = _row_in_group(entry["label"], group, rows)
        if row is None:
            row = don
            ngoai.append(f"{entry['fileName']} → \"{entry['documentName']}\"")
        bytes_per_row[row[0]] = bytes_per_row.get(row[0], 0) + entry["bytes"]
        attachments.append(_igate._item(entry["idx"], entry["fileName"], entry["documentName"], row, entry["label"]))
        classified.append({**base, "target": "attp-row", "componentIndex": row[0]})

    if attachments:
        warnings.append(
            f"Hồ sơ được xếp theo nhóm ({group}) — dòng {rows[0][0]}–{rows[-1][0]} của bảng"
            + (" (theo văn bản căn cứ)." if group_source == "can_cu" else " (không đọc được văn bản căn cứ, cán bộ "
               "kiểm tra lại nhóm).")
            + " Trợ lý chỉ tích các dòng có tệp."
        )
    if skipped:
        warnings.append(f"CCCD không phải thành phần hồ sơ của thủ tục này — đã bỏ qua: {', '.join(skipped)}.")
    if ngoai:
        warnings.append(
            "Giấy tờ không có dòng trong nhóm này đã tạm đính vào dòng \"Đơn Mẫu số 24\" (vẫn là tệp riêng, giữ tên) "
            "vì cổng mới không có dòng \"giấy tờ khác\" — nếu cần tách riêng, cán bộ dùng nút \"Thêm giấy tờ\" của "
            f"cổng: {', '.join(ngoai)}."
        )
    for row_index, total in sorted(bytes_per_row.items()):
        if total > _goc._MAX_FILE_BYTES:
            warnings.append(
                f"Tổng dung lượng các tệp đính vào dòng thứ {row_index} là {total / 1024 / 1024:.1f} MB, vượt giới hạn "
                "6 MB của cổng — cần nén PDF hoặc tách thành nhiều tệp trước khi nộp."
            )
    _igate._dedupe_document_names(attachments)
    if not attachments:
        warnings.append("Không có tài liệu nào để đính kèm.")
    return attachments, warnings, classified, group, group_source


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    components = ((options or {}).get("attachmentContext") or {}).get("components")
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]
    errors: list[str] = []

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    for result in ocr_results:
        if result.get("error"):
            errors.append(f"OCR {result.get('name')}: {result['error']}")

    by_name = {result.get("name"): result for result in ocr_results}
    llm_docs = [
        {"index": index, "text": str(by_name.get(file.get("name"), {}).get("text") or "")}
        for index, file in enumerate(raw_files)
    ]
    started = time.monotonic()
    llm_group, llm_types = "", {}
    if any(doc["text"].strip() for doc in llm_docs):
        try:
            llm_group, llm_types = await _goc._classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified, group, group_source = build_plan_items(
        raw_files, llm_types, llm_group, components
    )
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [f["name"] for f in raw_files],
            "portalRows": len(_igate._portal_rows(components)),
            "group": group,
            "groupSource": group_source,
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "ocr_text": join_ocr_documents(ocr_results),
        "llm_output": {"group": llm_group, **{str(idx): value for idx, value in llm_types.items()}},
        "errors": errors,
    }

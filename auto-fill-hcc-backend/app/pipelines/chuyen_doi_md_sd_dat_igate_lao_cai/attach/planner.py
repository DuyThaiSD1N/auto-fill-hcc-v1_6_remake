"""Đính kèm cho [Lào Cai - cổng iGate mới] Chuyển mục đích sử dụng đất (1.115651).

Phân loại giữ NGUYÊN của pipeline cổng cũ (chuyen_doi_md_sd_dat_lao_cai/attach: OCR → LLM → nhãn catalog + nhóm hồ
sơ theo mẫu đơn 02/03/17/18). Chỉ cách đặt tệp vào bảng là khác.

Bước 2 "Thành phần hồ sơ hệ thống" (đã crawl ở dichvucongtest.laocai.gov.vn): MỘT bảng 13 dòng, KHÔNG có radio chọn
trường hợp và KHÔNG có dòng tiêu đề nhóm — bốn nhóm nối liền nhau, mỗi nhóm mở bằng dòng Đơn của nó:
  (1) chuyển mục đích      : 1 Đơn Mẫu số 02 · 2 GCN/Điều 137/quyết định giao đất/tài liệu đáp ứng tiêu chí
  (2) chuyển hình thức     : 3 Đơn Mẫu số 03 · 4 GCN/Điều 137 · 5 Quyết định giao đất…
  (3) gia hạn              : 6 Đơn Mẫu số 17 · 7 GCN · 8 Quyết định giao đất… · 9 VB gia hạn thời hạn hoạt động dự án
  (4) điều chỉnh thời hạn  : 10 Đơn Mẫu số 18 · 11 VB thay đổi thời hạn hoạt động · 12 "Một trong các GCN: …" · 13 QĐ
⚠ Từ khoá dòng lặp giữa các nhóm ("khoản 21 Điều 3" ở dòng 2/4/7; dòng 8 và 13 trùng NGUYÊN VĂN) → KHÔNG dò trên cả
bảng: khoanh vùng NHÓM từ dòng Đơn của mẫu đơn trong hồ sơ tới trước dòng Đơn kế tiếp, rồi mới dò từ khoá trong vùng.
⚠ Cổng TÍCH SẴN cả 13 dòng → gửi untickUnplannedRows để FE bỏ chọn tất cả rồi chỉ tích dòng có tệp.

Engine FE "attp-row": mỗi dòng mat-checkbox + input[type=file] multiple; gửi index + tên NGUYÊN VĂN của dòng (FE
kiểm rows[index-1] khớp tên). Dòng lấy từ attachmentContext.components; extension không gửi thì dùng bảng 13 dòng ở
dưới. Giấy tờ không có dòng trong nhóm (bản đồ, GCN ĐKDN, giấy ủy quyền, tài liệu khác) — cổng không có dòng "giấy tờ
khác" → đính chung dòng Đơn của nhóm (vẫn là tệp riêng) + cảnh báo. CCCD không phải thành phần hồ sơ → bỏ qua.
TUYỆT ĐỐI không làm rơi tệp.
"""

import time

from app.pipelines._shared import fold
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.chuyen_doi_md_sd_dat_lao_cai.attach import catalog
from app.pipelines.chuyen_doi_md_sd_dat_lao_cai.attach import planner as _goc
from app.process.schemas import FileItem
from app.services import ocr

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# Bảng 13 dòng NGUYÊN VĂN (crawl 29/10/2026) — dùng khi extension không gửi attachmentContext.
_DEFAULT_ROWS = [
    "Đơn theo Mẫu số 02 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND",
    "Một trong các giấy chứng nhận quy định tại khoản 21 Điều 3, khoản 3 Điều 256 Luật Đất đai hoặc một trong các "
    "loại giấy tờ quy định tại Điều 137 Luật Đất đai hoặc quyết định giao đất, quyết định cho thuê đất, quyết định "
    "cho phép chuyển mục đích sử dụng đất của cơ quan nhà nước có thẩm quyền theo quy định của pháp luật về đất đai "
    "qua các thời kỳ; các tài liệu liên quan đến việc đáp ứng tiêu chí, điều kiện chuyển mục đích sử dụng đất trồng "
    "lúa, đất rừng phòng hộ, đất rừng đặc dụng, đất rừng sản xuất sang mục đích khác quy định tại khoản 1 Điều 46 "
    "Nghị định số 102/2024/NĐ-CP (nếu có)",
    "Đơn theo Mẫu số 03 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND",
    "Một trong các giấy chứng nhận quy định tại khoản 21 Điều 3, khoản 3 Điều 256 Luật Đất đai hoặc một trong các "
    "loại giấy tờ quy định tại Điều 137 Luật Đất đai",
    "Quyết định giao đất, quyết định cho thuê đất, quyết định cho phép chuyển mục đích sử dụng đất của cơ quan nhà "
    "nước có thẩm quyền theo quy định của pháp luật đất đai qua các thời kỳ",
    "Đơn theo Mẫu số 17 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND",
    "Một trong các giấy chứng nhận quy định tại khoản 21 Điều 3, khoản 3 Điều 256 Luật Đất đai",
    "Quyết định giao đất, cho thuê đất, cho phép chuyển mục đích sử dụng đất của cơ quan nhà nước có thẩm quyền "
    "theo quy định của pháp luật về đất đai qua các thời kỳ",
    "Văn bản của cơ quan có thẩm quyền cho phép gia hạn thời hạn hoạt động của dự án đầu tư hoặc thể hiện thời hạn "
    "hoạt động của dự án đầu tư theo quy định của pháp luật về đầu tư đối với trường hợp sử dụng đất để thực hiện "
    "dự án đầu tư",
    "Đơn theo Mẫu số 18 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND",
    "Văn bản của cơ quan có thẩm quyền cho phép thay đổi thời hạn hoạt động của dự án đầu tư theo quy định của "
    "pháp luật về đầu tư",
    "Một trong các giấy chứng nhận: Giấy chứng nhận quyền sử dụng đất, Giấy chứng nhận quyền sở hữu nhà ở và quyền "
    "sử dụng đất ở, Giấy chứng nhận quyền sở hữu nhà ở, Giấy chứng nhận quyền sở hữu công trình xây dựng, Giấy chứng "
    "nhận quyền sử dụng đất, quyền sở hữu nhà ở và tài sản khác gắn liền với đất đã được cấp theo quy định của pháp "
    "luật về đất đai, pháp luật về nhà ở, pháp luật về xây dựng trước ngày Luật Đất đai có hiệu lực thi hành; Giấy "
    "chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất",
    "Quyết định giao đất, cho thuê đất, cho phép chuyển mục đích sử dụng đất của cơ quan nhà nước có thẩm quyền "
    "theo quy định của pháp luật về đất đai qua các thời kỳ",
]

# Dòng Đơn mở đầu mỗi nhóm (từ khoá đã fold).
_DON_KEYS = {
    "don_mau_02": "mau so 02",
    "don_mau_03": "mau so 03",
    "don_mau_17": "mau so 17",
    "don_mau_18": "mau so 18",
}
_DON_BY_GROUP = {group: label for label, group in catalog.FORM_GROUP.items()}

# nhãn catalog → từ khoá (đã fold) dò TRONG nhóm, thử lần lượt. Nhãn không có ở đây → dòng Đơn của nhóm.
_ROW_KEYS: dict[str, list[str]] = {
    "gcn": ["khoan 21 dieu 3", "mot trong cac giay chung nhan"],
    "quyet_dinh_giao_dat": ["quyet dinh giao dat"],
    "tai_lieu_dieu_kien": ["dap ung tieu chi"],
    "vb_thoi_han_du_an": ["gia han thoi han hoat dong"],
    "vb_thay_doi_thoi_han_du_an": ["thay doi thoi han hoat dong"],
}

Row = tuple[int, str, str]  # (index 1-based, tên nguyên văn, tên fold)


def _portal_rows(components: list[dict] | None) -> list[Row]:
    rows: list[Row] = []
    for component in components or []:
        if not isinstance(component, dict):
            continue
        try:
            index = int(component.get("index"))
        except (TypeError, ValueError):
            continue
        name = str(component.get("componentName") or "").strip()
        if index > 0 and name:
            rows.append((index, name, fold(name)))
    return rows


def _default_rows() -> list[Row]:
    return [(i + 1, name, fold(name)) for i, name in enumerate(_DEFAULT_ROWS)]


def _groups(rows: list[Row]) -> dict[str, list[Row]]:
    """Nhãn Đơn → các dòng của nhóm đó (dòng Đơn đứng đầu, tới trước dòng Đơn kế tiếp)."""
    groups: dict[str, list[Row]] = {}
    current: list[Row] | None = None
    for row in sorted(rows):
        label = next((lb for lb, key in _DON_KEYS.items() if key in row[2] and row[2].startswith("don")), None)
        if label and label not in groups:
            current = groups[label] = []
        if current is not None:
            current.append(row)
    return groups


def _find(keys: list[str], rows: list[Row]) -> Row | None:
    for key in keys:
        hits = [row for row in rows if key in row[2]]
        if hits:
            return min(hits, key=lambda row: (len(row[2]), row[0]))
    return None


def _item(entry: dict, row: Row) -> dict:
    return {
        "fileIndex": entry["idx"],
        "fileName": entry["fileName"],
        "documentName": entry["documentName"],
        "componentName": row[1],
        "componentIndex": row[0],
        "target": "attp-row",
        "needsAddComponent": False,
        "detectedType": entry["label"],
        # Cổng tích sẵn mọi dòng → FE bỏ chọn tất cả rồi chỉ tích dòng được đính.
        "untickUnplannedRows": True,
    }


def _dedupe_document_names(attachments: list[dict]) -> None:
    """documentName thành TÊN TỆP khi FE dựng file → hai tệp cùng tên trong một ô sẽ bị bộ chống trùng bỏ qua."""
    counts: dict[tuple, int] = {}
    for item in attachments:
        key = (item["componentIndex"], item["documentName"])
        counts[key] = counts.get(key, 0) + 1
    used: dict[tuple, int] = {}
    for item in attachments:
        key = (item["componentIndex"], item["documentName"])
        if counts[key] < 2:
            continue
        used[key] = used.get(key, 0) + 1
        item["documentName"] = f"{item['documentName']} ({used[key]})"


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, dict[str, str]] | None = None,
    llm_group: str = "",
    components: list[dict] | None = None,
) -> tuple[list[dict], list[str], list[dict], str]:
    llm_types = llm_types or {}
    rows = _portal_rows(components) or _default_rows()
    groups = _groups(rows)
    entries: list[dict] = []
    used_names: set[str] = set()
    for position, file in enumerate(files):
        idx = int(file.get("_index", position))
        detected = llm_types.get(idx) or {}
        label = detected.get("label") or "khac"
        fallback = catalog.display_name(label)
        entries.append({
            "idx": idx,
            "fileName": str(file.get("name") or f"file-{idx + 1}"),
            "label": label,
            "documentName": _goc._unique_document_name(detected.get("documentName") or fallback, used_names, fallback),
        })

    warnings: list[str] = []

    def warn(message: str) -> None:
        if message not in warnings:
            warnings.append(message)

    # Mẫu đơn quyết định nhóm: đơn có trong hồ sơ → nhóm LLM suy ra → mặc định chuyển mục đích (cảnh báo).
    don_label = next((e["label"] for e in entries if e["label"] in _DON_KEYS), "") \
        or _DON_BY_GROUP.get(llm_group.strip().strip("()"), "")
    if not don_label:
        don_label = "don_mau_02"
        if entries:
            warn("Không nhận ra Đơn đề nghị (Mẫu 02/03/17/18) trong hồ sơ — tạm đính theo nhóm chuyển mục đích "
                 "(Mẫu số 02); cán bộ kiểm tra lại.")
    group_rows = groups.get(don_label) or []
    anchor = group_rows[0] if group_rows else rows[0]
    if not group_rows:
        warn(f"Bảng thành phần hồ sơ không có dòng '{catalog.display_name(don_label)}' — tệp tạm đính vào dòng "
             f"'{anchor[1]}'; cán bộ kiểm tra lại.")

    attachments: list[dict] = []
    classified: list[dict] = []
    for entry in entries:
        base = {"fileName": entry["fileName"], "label": entry["label"], "documentName": entry["documentName"]}
        label = entry["label"]
        if label in catalog.SKIPPED_LABELS:
            warn(f"File '{entry['fileName']}' ({entry['documentName']}) không phải thành phần hồ sơ — đã bỏ qua.")
            classified.append({**base, "target": "skip", "reason": "not_a_component"})
            continue
        if label in _DON_KEYS:
            # Đơn khác nhóm (hiếm) vẫn về dòng Đơn của chính nó.
            row = (groups.get(label) or [anchor])[0]
        else:
            row = _find(_ROW_KEYS.get(label, []), group_rows)
            if row is None:
                row = anchor
                warn(f"'{entry['fileName']}' ({entry['documentName']}) không có dòng riêng trong nhóm hồ sơ — đính "
                     f"chung dòng '{anchor[1]}'; cán bộ kiểm tra lại.")
        attachments.append(_item(entry, row))
        classified.append({**base, "target": "attp-row", "componentIndex": row[0], "componentName": row[1]})

    _dedupe_document_names(attachments)
    if not attachments:
        warn("Không có tài liệu nào để đính kèm.")
    return attachments, warnings, classified, don_label


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    components = ((options or {}).get("attachmentContext") or {}).get("components")
    errors: list[str] = []
    raw_files = [
        {"name": file.name, "type": file.type, "dataUrl": file.dataUrl, "_index": idx}
        for idx, file in enumerate(files)
    ]
    valid_files: list[dict] = []
    for file in raw_files:
        size = _goc._data_url_size(file.get("dataUrl", ""))
        if size > _goc._MAX_FILE_BYTES:
            errors.append(f"File '{file['name']}' vượt quá 6 MB ({size / 1024 / 1024:.2f} MB) — đã bỏ qua.")
        else:
            valid_files.append(file)

    ocr_files = [file for file in valid_files if file.get("type") in _OCR_TYPES]
    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for result in ocr_results:
        if result.get("error"):
            errors.append(f"OCR {result.get('name')}: {result['error']}")

    ocr_by_name = {result.get("name"): result for result in ocr_results}
    llm_docs = [
        {"index": file["_index"], "text": str(ocr_by_name.get(file.get("name"), {}).get("text") or "")}
        for file in valid_files
    ]

    t1 = time.monotonic()
    llm_group, llm_types = "", {}
    if any(doc["text"].strip() for doc in llm_docs):
        try:
            llm_group, llm_types = await _goc._classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings, classified, don_label = build_plan_items(valid_files, llm_types, llm_group, components)
    errors.extend(warnings)

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [file["name"] for file in raw_files],
            "ocrDocuments": [result.get("name") for result in ocr_results if result.get("text")],
            "llmDocuments": [file["name"] for file in valid_files],
            "sessionId": (session or {}).get("request_id"),
            "donLabel": don_label,
            "portalRows": len(_portal_rows(components)),
            "classified": classified,
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "ocr_text": join_ocr_documents(ocr_results),
        "llm_output": {"group": llm_group, **{str(idx): value for idx, value in llm_types.items()}},
        "errors": errors,
    }

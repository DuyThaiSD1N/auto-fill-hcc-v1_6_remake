"""Lập kế hoạch đính kèm "Tính hoặc tính lại tiền sử dụng đất theo các điểm a, b, c và d khoản 2 Điều 12
NĐ 50/2026/NĐ-CP" tại Quảng Ngãi (1.115148).

Bước "Thành phần hồ sơ" của cổng dichvucong.quangngai.gov.vn (iGate Angular) KHÔNG cấu hình sẵn danh mục
("Không có thông tin giấy tờ") → mọi dòng phải tạo bằng nút "+ Thêm giấy tờ" (`add-document-dialog`),
theo ánh xạ của bộ phận một cửa:
  1. Đơn đề nghị tính lại tiền sử dụng đất (Bản chính) — dòng ĐÍNH KÈM CHUNG: Đơn + Bản cam kết + Bản sao
     GCN (+ CCCD, giấy ủy quyền nếu có). Hồ sơ hay quét GỘP Đơn (tr.1–2) + Bản cam kết (tr.3) + GCN (tr.4–5)
     thành MỘT PDF → đính nguyên file, không tách trang.
  2. Bản sao thông báo nộp tiền sử dụng đất (Bản sao) — mục 4.b của Đơn.
  3. Biên lai đã nộp tiền vào Ngân sách nhà nước (Bản sao) — mục 4.c của Đơn.
Dòng 2/3 chỉ tạo khi có tệp tương ứng; thiếu thì nhắc cán bộ bổ sung. Giấy tờ không rõ loại vẫn đính chung
dòng 1 (giữ tên tệp gốc), không bỏ.

Phân loại LLM-primary (một lượt gọi cho mỗi file); rule tiêu đề chỉ dự phòng khi LLM lỗi.
"""

import asyncio
import time
import unicodedata
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON = "don_de_nghi"
_CAM_KET = "ban_cam_ket"
_GCN = "giay_chung_nhan"
_THONG_BAO = "thong_bao_nop_tien"
_BIEN_LAI = "bien_lai_nop_tien"
_IDENTITY = "identity"
_UY_QUYEN = "van_ban_dai_dien"
_OTHER = "other"

# Modal "Thêm giấy tờ" của cổng Quảng Ngãi (đã crawl): ô "Giấy tờ" là input + mat-autocomplete, nút Đồng ý
# chỉ mở khi đã CHỌN một gợi ý của danh mục. FE gõ lần lượt formOptionHints (cụ thể → chung) và chọn mục
# chứa hint; hết hint thì mở cả danh mục, chọn mục trùng ≥ 60% từ với componentName hoặc mục "… khác".
# Không để hint quá chung ("Đơn đề nghị") — sẽ trúng đơn của thủ tục khác. Tên dòng thật = tên mục cổng.
_ROW_DON = {
    "order": 1,
    "componentName": "Đơn đề nghị tính lại tiền sử dụng đất",
    "loaiBan": "Bản chính",
    "formOptionHints": [
        "Đơn đề nghị tính lại tiền sử dụng đất",
        "Đơn đề nghị tính tiền sử dụng đất",
        "tính lại tiền sử dụng đất",
    ],
}
_ROW_THONG_BAO = {
    "order": 2,
    "componentName": "Bản sao thông báo nộp tiền sử dụng đất",
    "loaiBan": "Bản sao",
    "formOptionHints": ["thông báo nộp tiền sử dụng đất", "thông báo nộp tiền", "thông báo của cơ quan thuế"],
}
_ROW_BIEN_LAI = {
    "order": 3,
    "componentName": "Biên lai đã nộp tiền vào Ngân sách nhà nước",
    "loaiBan": "Bản sao",
    "formOptionHints": [
        "Biên lai đã nộp tiền",
        "nộp tiền vào ngân sách nhà nước",
        "chứng từ nộp tiền",
        "chứng từ thực hiện nghĩa vụ tài chính",
    ],
}

_ROUTES: dict[str, dict[str, Any]] = {
    _DON: {**_ROW_DON, "documentName": "Đơn đề nghị tính lại tiền sử dụng đất"},
    _CAM_KET: {**_ROW_DON, "documentName": "Bản cam kết"},
    _GCN: {**_ROW_DON, "documentName": "Bản sao Giấy chứng nhận quyền sử dụng đất"},
    _IDENTITY: {**_ROW_DON, "documentName": "Căn cước công dân"},
    _UY_QUYEN: {**_ROW_DON, "documentName": "Văn bản ủy quyền"},
    _THONG_BAO: {**_ROW_THONG_BAO, "documentName": "Bản sao thông báo nộp tiền sử dụng đất"},
    _BIEN_LAI: {**_ROW_BIEN_LAI, "documentName": "Biên lai nộp tiền vào ngân sách nhà nước"},
}
_ALLOWED = set(_ROUTES) | {_OTHER}

# Rule dự phòng: chỉ xét TIÊU ĐỀ ở phần đầu file (đơn nhắc lại "thông báo nộp tiền" ở mục 4).
_HEAD_CHARS = 1200
_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (_DON, ("don de nghi tinh lai tien su dung dat", "don de nghi tinh tien su dung dat")),
    (_CAM_KET, ("ban cam ket",)),
    # Thông báo/biên lai trước GCN: hai loại này hay nhắc số Giấy chứng nhận ngay phần đầu.
    (_THONG_BAO, ("thong bao nop tien su dung dat", "thong bao nop tien")),
    (_BIEN_LAI, ("bien lai thu", "giay nop tien vao ngan sach nha nuoc", "bien lai")),
    (_GCN, ("giay chung nhan quyen su dung dat",)),
    (_UY_QUYEN, ("giay uy quyen", "hop dong uy quyen", "van ban uy quyen")),
    (_IDENTITY, ("can cuoc cong dan", "can cuoc")),
)

# Giấy tờ nằm chung trong file Đơn — so TIÊU ĐỀ IN HOA (giữ dấu, phân biệt hoa thường) để không bắt nhầm
# câu "Bản sao giấy chứng nhận..." ở mục 4 của chính Đơn.
_BUNDLE_TITLES: tuple[tuple[str, str], ...] = (
    ("ĐƠN ĐỀ NGHỊ", "Đơn đề nghị"),
    ("BẢN CAM KẾT", "Bản cam kết"),
    ("GIẤY CHỨNG NHẬN", "Bản sao Giấy chứng nhận"),
    ("THÔNG BÁO NỘP TIỀN", "Thông báo nộp tiền sử dụng đất"),
    ("BIÊN LAI", "Biên lai nộp tiền"),
)


def _normalize_doc_type(value: Any) -> str:
    folded = _fold(str(value or ""))
    for doc_type in _ALLOWED:
        if folded == _fold(doc_type):
            return doc_type
    return _OTHER


def _rule_doc_type(text: str) -> str:
    head = _fold(text or "")[:_HEAD_CHARS]
    if not head:
        return ""
    for doc_type, markers in _RULES:
        if any(marker in head for marker in markers):
            return doc_type
    return ""


def _bundled_titles(text: str) -> list[str]:
    raw = unicodedata.normalize("NFC", text or "")
    return [label for title, label in _BUNDLE_TITLES if title in raw]


async def _classify_one_with_llm(document: dict[str, Any]) -> tuple[int, str]:
    index = int(document.get("index"))
    payload = {"index": index, "text": str(document.get("text") or "")[:12000]}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt([payload])},
    ]
    raw = await client.chat(messages, max_tokens=120, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    first = next(iter(parsed.get("documents", []) or []), {})
    return index, _normalize_doc_type(first.get("docType") or first.get("type"))


async def _classify_with_llm(documents: list[dict[str, Any]], errors: list[str]) -> dict[int, str]:
    if not documents:
        return {}
    # Một call cho mỗi file: một PDF dài hay một lỗi provider chỉ làm file đó rơi về rule dự phòng.
    outcomes = await asyncio.gather(
        *(_classify_one_with_llm(document) for document in documents),
        return_exceptions=True,
    )
    result: dict[int, str] = {}
    for document, outcome in zip(documents, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            errors.append(f"attachment_agent file {document.get('index')}: {outcome}")
            continue
        index, doc_type = outcome
        result[index] = doc_type
    return result


def _build_item(file: dict, file_index: int, route: dict, doc_type: str, document_name: str) -> dict:
    return {
        "fileIndex": file_index,
        "fileName": str(file.get("name") or f"file-{file_index + 1}"),
        "documentName": document_name,
        "componentName": route["componentName"],
        "loaiBan": route["loaiBan"],
        "formOptionHints": list(route["formOptionHints"]),
        "quantity": 1,
        "target": "add-document-dialog",
        "needsAddComponent": True,
        "detectedType": doc_type,
    }


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict] | None = None,
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    ocr_by_name = {item.get("name"): item for item in ocr_results or []}
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        text = str(ocr_by_name.get(file_name, {}).get("text") or "")
        llm_type = llm_types.get(index, "")
        rule_type = _rule_doc_type(text)
        if llm_type in _ROUTES:
            doc_type, source = llm_type, "llm"
        elif not llm_type and rule_type in _ROUTES:
            doc_type, source = rule_type, "rule"
        else:
            doc_type, source = _OTHER, "llm" if llm_type == _OTHER else "unknown"

        if doc_type in _ROUTES:
            route = _ROUTES[doc_type]
            document_name = route["documentName"]
            if doc_type == _DON:
                bundled = _bundled_titles(text)
                if len(bundled) > 1:
                    document_name = " + ".join(bundled)
                    warnings.append(
                        f'Tệp "{file_name}" gồm: {"; ".join(bundled)} — đính nguyên một file vào dòng '
                        f'"{_ROW_DON["componentName"]}" (không tách trang).'
                    )
        else:
            # Không rõ loại → vẫn đính chung dòng Đơn, giữ tên tệp gốc để cán bộ nhận ra.
            route = _ROW_DON
            document_name = file_name
            warnings.append(
                f'Chưa nhận diện chắc loại giấy tờ cho "{file_name}" — tạm đính vào dòng '
                f'"{_ROW_DON["componentName"]}"; cán bộ kiểm tra lại.'
            )

        item = _build_item(file, index, route, doc_type, document_name)
        attachments.append(item)
        classified.append({
            "fileName": file_name,
            "docType": doc_type,
            "source": source,
            "componentName": route["componentName"],
        })

    # FE tạo dòng theo thứ tự plan: Đơn → Thông báo nộp tiền → Biên lai; trong cùng dòng giữ thứ tự tải lên.
    order = {route["componentName"]: route["order"] for route in (_ROW_DON, _ROW_THONG_BAO, _ROW_BIEN_LAI)}
    attachments.sort(key=lambda item: (order[item["componentName"]], item["fileIndex"]))

    found = {item["detectedType"] for item in attachments}
    if _DON not in found:
        warnings.append(f'Chưa có "{_ROW_DON["componentName"]}" — mời bổ sung.')
    for doc_type, row, muc in ((_THONG_BAO, _ROW_THONG_BAO, "4.b"), (_BIEN_LAI, _ROW_BIEN_LAI, "4.c")):
        if doc_type not in found:
            warnings.append(
                f'Chưa có tệp "{row["componentName"]}" (mục {muc} của Đơn) — cần người dân bổ sung trước khi nộp.'
            )

    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    ocr_files = [item for item in raw_files if item.get("type") in _OCR_TYPES]
    errors: list[str] = []

    from app.services import ocr

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
    llm_types: dict[int, str] = {}
    if llm_documents:
        try:
            llm_types = await _classify_with_llm(llm_documents, errors)
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

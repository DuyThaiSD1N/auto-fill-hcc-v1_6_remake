"""Đính kèm [Lào Cai] điều chỉnh quyết định giao đất, cho thuê đất, cho phép chuyển mục đích SDĐ.

Cổng `dichvucong.laocai.gov.vn` (eForm iGate, Nth.FormBuilder). Trang `nhap-thong-tin-ho-so` có **7
`input[type=file]`** theo thứ tự DOM, mỗi ô kèm nút "Chọn tệp tin" → engine FE `fixed-slot`:

  0–2 : 3 dòng thành phần hồ sơ (`GiayToCuaHoSoOnline_{50066,50083,50067}_fileGiayTo`)
  3–5 : 3 dòng "Giấy tờ khác" (`HoSoOnline_giayToKhac_file_1..3`)
  6   : ô `HoSoOnline_fileGiayToKhac`

⚑ Giấy tờ NGOÀI danh mục KHÔNG dùng fixed-slot mà dùng `target="new"` + `needsAddComponent=True`:
trang có `input[name="HoSoOnline_giayToKhac[]"]` nên FE tự chạy `attachOneFileToOtherListFile`
(content.js) — engine này **điền cả TÊN tài liệu** vào ô rồi mới đính tệp, đúng yêu cầu nghiệp vụ là
phải ghi rõ danh mục văn bản bổ sung. Nếu chỉ đẩy vào slot 3–5 thì tệp lên nhưng ô tên để trống.
Tên đó do LLM đọc nội dung đặt (xem prompt), BE chỉ chuẩn hoá + khử trùng — tên tệp không dùng được
vì hệ thống upload đã bỏ dấu và chèn số.

Phân loại THUẦN LLM (không lưới keyword). Không bỏ sót tệp nào.
"""

import asyncio
import re
import time
from typing import Any

from app.config import settings
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_LOAI_BAN = "Bản chính"

# Cổng ghi ngay trên bảng: "Dung lượng tối đa là 6 Mb". Gán tệp quá cỡ thì cổng nuốt im lặng.
_MAX_FILE_BYTES = 6 * 1024 * 1024

# docType → (slotIndex, text NGUYÊN VĂN của dòng trên cổng, tên hiển thị).
_ROUTES: dict[str, dict[str, Any]] = {
    "don_mau_04": {
        "slotIndex": 0,
        "slotName": "Đơn theo Mẫu số 04 kèm theo Quyết định số 47/2026/QĐ-UBND",
        "display": "Đơn đề nghị điều chỉnh quyết định giao đất, cho thuê đất (Mẫu số 04)",
    },
    "quyet_dinh_bi_dieu_chinh": {
        "slotIndex": 1,
        "slotName": (
            "Một trong các giấy chứng nhận quy định tại khoản 21 Điều 3, khoản 3 Điều 256 Luật Đất đai "
            "hoặc một trong các loại giấy tờ quy định tại Điều 137 Luật Đất đai hoặc quyết định giao "
            "đất, cho thuê đất, cho phép chuyển mục đích sử dụng đất của cơ quan nhà nước có thẩm quyền"
        ),
        "display": "Quyết định giao đất, cho thuê đất đề nghị điều chỉnh",
    },
    "van_ban_thay_doi_can_cu": {
        "slotIndex": 2,
        "slotName": (
            "Văn bản của cơ quan nhà nước có thẩm quyền có nội dung làm thay đổi căn cứ quyết định giao "
            "đất, cho thuê đất, cho phép chuyển mục đích sử dụng đất"
        ),
        "display": "Văn bản làm thay đổi căn cứ quyết định giao đất, cho thuê đất",
    },
}
_ALLOWED = set(_ROUTES) | {"other"}


def _fold(value: Any) -> str:
    import unicodedata

    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _canon(value: Any) -> str:
    return re.sub(r"[_\-\s]+", "_", _fold(value)).strip("_")


def _normalize_doc_type(value: Any) -> str:
    canon = _canon(value)
    for doc_type in _ALLOWED:
        if canon == _canon(doc_type):
            return doc_type
    return "other"


_FALLBACK_DOCUMENT_NAME = "Tài liệu khác"
_MAX_DOCUMENT_NAME = 60


def _clean_document_name(raw: str) -> str:
    """Chuẩn hoá tên gõ vào ô "Tên giấy tờ".

    KHÔNG dùng `normalize_document_name` của _shared: hàm đó nhận TÊN TỆP nên chạy `Path(raw).stem`,
    cắt mất phần trước dấu "/" — "QĐ 894/QĐ-UBND phê duyệt…" thành "QĐ-UBND phê duyệt…", tức mất đúng
    số hiệu văn bản là thứ phân biệt các quyết định với nhau. Ở đây chỉ đổi "/" thành "-" (giữ số
    hiệu, tránh ký tự cổng có thể từ chối) và bỏ ký tự lạ.
    """
    import unicodedata

    text = unicodedata.normalize("NFC", str(raw or "")).replace("/", "-")
    chars = [ch if (ch.isalnum() or ch in " _-,.()") else " " for ch in text]
    text = re.sub(r"\s+", " ", "".join(chars)).strip(" -,.")
    return text[:_MAX_DOCUMENT_NAME].strip(" -,.")


def _unique_document_name(base: str, used: set[str]) -> str:
    """Hai dòng "Giấy tờ khác" trùng tên là cán bộ không phân biệt được văn bản nào."""
    value = _clean_document_name(base) or _FALLBACK_DOCUMENT_NAME
    key = _fold(value)
    if key and key not in used:
        used.add(key)
        return value
    stem = value[:52].strip() or _FALLBACK_DOCUMENT_NAME
    suffix = 2
    while True:
        candidate = f"{stem} {suffix}"[:_MAX_DOCUMENT_NAME].strip()
        if _fold(candidate) not in used:
            used.add(_fold(candidate))
            return candidate
        suffix += 1


def _file_bytes(file: dict) -> int | None:
    """Kích thước thật, suy từ độ dài base64 của dataUrl (FileItem không mang size)."""
    data_url = file.get("dataUrl")
    if not isinstance(data_url, str) or "," not in data_url:
        return None
    payload = data_url.split(",", 1)[1]
    if not payload:
        return None
    return len(payload) * 3 // 4 - payload[-2:].count("=")


async def _classify_one(document: dict[str, Any]) -> tuple[int, str, str]:
    index = int(document.get("index"))
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(
            [{"index": index, "text": str(document.get("text") or "")[:12000]}]
        )},
    ]
    # max_tokens cao hơn bản cũ vì nay LLM còn phải trả documentName.
    raw = await client.chat(messages, max_tokens=220, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    first = next(iter(parsed.get("documents", []) or []), {})
    doc_type = _normalize_doc_type(first.get("docType") or first.get("type"))
    return index, doc_type, str(first.get("documentName") or "").strip()


async def _classify_with_llm(
    documents: list[dict[str, Any]],
    errors: list[str] | None = None,
) -> dict[int, tuple[str, str]]:
    if not documents:
        return {}
    outcomes = await asyncio.gather(*(_classify_one(d) for d in documents), return_exceptions=True)
    result: dict[int, tuple[str, str]] = {}
    for document, outcome in zip(documents, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            if errors is not None:
                errors.append(f"attachment_agent file {document.get('index')}: {outcome}")
            continue
        index, doc_type, document_name = outcome
        result[index] = (doc_type, document_name)
    return result


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, tuple[str, str] | str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    unknown: list[str] = []
    qua_nang: list[str] = []
    used_names: set[str] = set()
    by_row: dict[str, list[str]] = {}

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        raw = llm_types.get(index)
        llm_type, llm_name = raw if isinstance(raw, tuple) else (raw or "", "")
        doc_type = llm_type if llm_type in _ALLOWED else "other"
        source = "llm" if llm_type else "default"

        size = _file_bytes(file)
        if size and size > _MAX_FILE_BYTES:
            qua_nang.append(f"{file_name} ({round(size / 1024 / 1024, 1)} MB)")

        if doc_type == "other":
            # Tên lấy từ LLM đọc nội dung, KHÔNG lấy tên tệp (mất dấu, dính số của hệ thống upload).
            component_name = _unique_document_name(llm_name, used_names)
            item = {
                "fileIndex": index,
                "fileName": file_name,
                "documentName": component_name,
                "componentName": component_name,
                "loaiBan": _LOAI_BAN,
                # Engine otherListFile của FE điền TÊN tài liệu rồi mới đính tệp.
                "target": "new",
                "needsAddComponent": True,
                "detectedType": doc_type,
                # Cổng iGate VNPT: bấm option "Chọn tệp tin" mở hộp thoại file của hệ điều hành
                # (chặn UI) → FE chỉ gán thẳng, hụt thì bỏ qua tệp đó.
                "noChooserClick": True,
            }
            unknown.append(f"{file_name} → \"{component_name}\"")
        else:
            route = _ROUTES[doc_type]
            item = {
                "fileIndex": index,
                "fileName": file_name,
                "documentName": route["display"],
                "componentName": route["slotName"],
                "loaiBan": _LOAI_BAN,
                "target": "fixed-slot",
                "needsAddComponent": False,
                "slotKey": f"laocai_dcgd_{doc_type}",
                "slotIndex": route["slotIndex"],
                "slotName": route["slotName"],
                "detectedType": doc_type,
            }
            by_row.setdefault(route["display"], []).append(file_name)

        attachments.append(item)
        classified.append({
            "fileName": file_name,
            "docType": doc_type,
            "documentName": item["documentName"],
            "source": source,
            "target": item["target"],
            "slotIndex": item.get("slotIndex"),
        })

    if unknown:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã thêm dòng \"Giấy tờ khác\" kèm tên tài liệu để không bỏ "
            f"sót — cán bộ kiểm tra lại: {', '.join(unknown)}."
        )
    if qua_nang:
        warnings.append(
            "Tệp vượt giới hạn 6 MB của cổng nên có thể bị nuốt im lặng, hãy nén hoặc giảm DPI rồi "
            f"tải lại: {', '.join(qua_nang)}."
        )
    # Một dòng nhận NHIỀU tệp là hợp lệ, nhưng cán bộ phải ghi rõ danh mục văn bản vào ô "Ghi chú" —
    # nêu sẵn để khỏi phải tự dò.
    for row, names in by_row.items():
        if len(names) > 1:
            warnings.append(f"Dòng \"{row}\" nhận {len(names)} tệp ({', '.join(names)}) — nên liệt kê "
                            "rõ từng văn bản vào ô \"Ghi chú\" của bước Thành phần hồ sơ.")
    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]
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

    attachments, warnings, classified = build_plan_items(raw_files, llm_types)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [raw_files[d["index"]]["name"] for d in llm_documents],
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

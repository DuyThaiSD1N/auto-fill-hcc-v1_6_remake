"""Đính kèm [Lào Cai - Cấp Sở] Đăng ký thay đổi nội dung biện pháp bảo đảm (1.011442.000.00.00.H38).

Cổng eForm iGate `dichvucong.laocai.gov.vn`, trang `nhap-thong-tin-ho-so`. Bảng thành phần hồ sơ theo
thứ tự DOM (= slotIndex):

  0 : maGiayTo 18946 — Văn bản ủy quyền … chỉ cần nộp 01 bản sao để đối chiếu  ← gồm GIẤY GIỚI THIỆU
  1 : maGiayTo 18944 — Hợp đồng thế chấp tài sản gắn liền với đất có công chứng, chứng thực …
  2 : maGiayTo 18945 — Giấy chứng nhận quyền sử dụng đất, quyền sở hữu nhà ở và tài sản khác …
  3 : maGiayTo 18943 — Đơn yêu cầu đăng ký thế chấp (*)  ← Phiếu yêu cầu đăng ký THAY ĐỔI Mẫu số 02a
  + 3 dòng "Giấy tờ khác" (`HoSoOnline_giayToKhac_file_1..3`, có ô "Tên giấy tờ" và nút "+")
  + ô `HoSoOnline_fileGiayToKhac`

Mỗi dòng cố định có checkbox ở cột đầu phải tích thì cổng mới nhận tệp → `tickRow=True`.

⚑ Dòng bắt buộc của cổng mang tên "Đơn yêu cầu đăng ký thế chấp" (danh mục dùng chung với thủ tục đăng
ký lần đầu) nhưng giấy của thủ tục này là Phiếu yêu cầu đăng ký thay đổi → đính phiếu vào dòng đó,
displayName ghi rõ là Phiếu 02a để cán bộ không tưởng nhầm giấy.

⚑ "SỐ BẢN" CỦA DÒNG GCN = SỐ TRANG GIẤY CHỨNG NHẬN (LLM đếm `gcnPages`, gửi qua `soBan`). Ảnh chụp điện
thoại từng trang GCN là nhiều tệp cùng một dòng — số bản là TỔNG số trang của các tệp đó.

⚑ slotKey cố ý KHÔNG nằm trong `FIXED_SLOT_KEYWORDS` (content.js) để FE đi thẳng theo `slotIndex`.

⚑ Giấy tờ ngoài danh mục (văn bản căn cứ thay đổi, ĐKDN/ĐKHĐ chi nhánh, CCCD, tài liệu khác) đi
`target="new"`: engine `attachOneFileToOtherListFile` của FE thêm dòng "Giấy tờ khác", gõ TÊN GIẤY TỜ rồi
mới gán tệp. Tên do LLM đọc nội dung đặt — tên tệp đã mất dấu và dính số của hệ thống upload.

Phân loại THUẦN LLM (không lưới keyword), 1 call/tệp. Tuyệt đối không bỏ sót tệp nào.
"""

import asyncio
import re
import time
import unicodedata
from typing import Any

from app.config import settings
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# Cổng ghi ngay trên bảng: "Dung lượng tối đa là 6 Mb". Gán tệp quá cỡ thì cổng nuốt im lặng.
_MAX_FILE_BYTES = 6 * 1024 * 1024

# GCN mẫu cũ 4 trang (+ trang bổ sung), mẫu 2024 2 trang; lớn hơn nhiều là LLM đếm nhầm giấy khác.
_MAX_GCN_PAGES = 10

_UY_QUYEN = "van_ban_uy_quyen"
_HOP_DONG = "hop_dong_the_chap"
_GCN = "gcn"
_PHIEU = "phieu_02a"

# docType → dòng cố định trên cổng. slotName = nguyên văn tên dòng (FE khớp substring đã fold dấu).
_ROUTES: dict[str, dict[str, Any]] = {
    _UY_QUYEN: {
        "slotIndex": 0,
        "slotName": "Văn bản ủy quyền trong trường hợp người yêu cầu đăng ký xuất trình bản chính văn bản "
                    "ủy quyền thì chỉ cần nộp 01 bản sao để đối chiếu",
        "display": "Văn bản ủy quyền, giấy giới thiệu",
    },
    _HOP_DONG: {
        "slotIndex": 1,
        "slotName": "Hợp đồng thế chấp tài sản gắn liền với đất có công chứng, chứng thực hoặc xác nhận "
                    "theo quy định của pháp luật",
        "display": "Hợp đồng thế chấp",
    },
    _GCN: {
        "slotIndex": 2,
        "slotName": "Giấy chứng nhận quyền sử dụng đất, quyền sở hữu nhà ở và tài sản khác gắn liền với đất",
        "display": "Giấy chứng nhận quyền sử dụng đất",
    },
    _PHIEU: {
        "slotIndex": 3,
        "slotName": "Đơn yêu cầu đăng ký thế chấp",
        "display": "Phiếu yêu cầu đăng ký thay đổi biện pháp bảo đảm Mẫu số 02a",
    },
}
# Loại giấy tờ không có dòng riêng → "Giấy tờ khác" với tên mặc định khi LLM không đặt được tên.
_OTHER_NAMES = {
    "van_ban_can_cu_thay_doi": "Văn bản căn cứ đăng ký thay đổi",
    "dkdn": "Giấy chứng nhận đăng ký doanh nghiệp",
    "cccd": "Căn cước công dân",
    "other": "Giấy tờ kèm theo hồ sơ",
}
_ALLOWED = set(_ROUTES) | set(_OTHER_NAMES)
# Thứ tự phủ dòng còn trống bằng tệp gộp: dòng bắt buộc trước.
_ROW_PRIORITY = (_PHIEU, _GCN, _HOP_DONG, _UY_QUYEN)

# Ô "Tên giấy tờ": ≤50 ký tự, không ngoặc, không dấu chấm.
_MAX_DOCUMENT_NAME = 50


def _fold(value: Any) -> str:
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


def _normalize_also(values: Any, primary: str) -> list[str]:
    """Các dòng cố định KHÁC mà tệp gộp này cũng chứa."""
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for value in values:
        doc_type = _normalize_doc_type(value)
        if doc_type in _ROUTES and doc_type != primary and doc_type not in out:
            out.append(doc_type)
    return out


def _gcn_pages(value: Any) -> int | None:
    try:
        pages = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return pages if 1 <= pages <= _MAX_GCN_PAGES else None


def _clean_document_name(raw: str) -> str:
    """Chuẩn hoá tên gõ vào ô "Tên giấy tờ": giữ số hiệu văn bản ("/" → "-"), bỏ ký tự lạ."""
    text = unicodedata.normalize("NFC", str(raw or "")).replace("/", "-")
    chars = [ch if (ch.isalnum() or ch in " _-,") else " " for ch in text]
    text = re.sub(r"\s+", " ", "".join(chars)).strip(" -,.")
    return text[:_MAX_DOCUMENT_NAME].strip(" -,.")


def _unique_document_name(base: str, fallback: str, used: set[str]) -> str:
    """Hai dòng "Giấy tờ khác" trùng tên thì cán bộ không phân biệt được → thêm số thứ tự."""
    value = _clean_document_name(base) or fallback
    key = _fold(value)
    if key not in used:
        used.add(key)
        return value
    stem = value[:_MAX_DOCUMENT_NAME - 3].strip()
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


def _coerce(raw: Any) -> dict[str, Any]:
    """Kết quả LLM của một tệp → dict chuẩn; chấp nhận cả dạng cũ chỉ là chuỗi docType."""
    if isinstance(raw, str):
        raw = {"docType": raw}
    if not isinstance(raw, dict):
        raw = {}
    doc_type = _normalize_doc_type(raw.get("docType") or raw.get("type"))
    return {
        "docType": doc_type,
        "alsoTypes": _normalize_also(raw.get("alsoTypes"), doc_type),
        "documentName": str(raw.get("documentName") or "").strip(),
        "gcnPages": _gcn_pages(raw.get("gcnPages")) if doc_type == _GCN else None,
    }




async def _classify_one(document: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    index = int(document.get("index"))
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt([{"index": index, "text": str(document.get("text") or "")[:12000]}])},
    ]
    raw = await client.chat(messages, max_tokens=260, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    first = next(iter(parsed.get("documents", []) or []), {})
    return index, _coerce(first)


async def _classify_with_llm(
    documents: list[dict[str, Any]],
    errors: list[str] | None = None,
) -> dict[int, dict[str, Any]]:
    if not documents:
        return {}
    # Một call cho mỗi file: PDF dài hoặc lỗi provider chỉ làm file đó rơi về other.
    outcomes = await asyncio.gather(*(_classify_one(d) for d in documents), return_exceptions=True)
    result: dict[int, dict[str, Any]] = {}
    for document, outcome in zip(documents, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            if errors is not None:
                errors.append(f"attachment_agent file {document.get('index')}: {outcome}")
            continue
        index, info = outcome
        result[index] = info
    return result


def _slot_item(index: int, file_name: str, doc_type: str) -> dict:
    route = _ROUTES[doc_type]
    return {
        "fileIndex": index,
        "fileName": file_name,
        "documentName": route["display"],
        "componentName": route["slotName"],
        "target": "fixed-slot",
        "needsAddComponent": False,
        "slotKey": f"laocai_dktdbpbd_{doc_type}",
        "slotIndex": route["slotIndex"],
        "slotName": route["slotName"],
        "detectedType": doc_type,
        "tickRow": True,
    }


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, dict[str, Any] | str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    unknown: list[str] = []
    qua_nang: list[str] = []
    used_names: set[str] = set()
    filled: dict[str, str] = {}

    resolved: list[tuple[int, str, dict[str, Any], str]] = []
    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        info = _coerce(llm_types.get(index)) if index in llm_types else _coerce(None)
        resolved.append((index, file_name, info, "llm" if index in llm_types else "default"))
        size = _file_bytes(file)
        if size and size > _MAX_FILE_BYTES:
            qua_nang.append(f"{file_name} ({round(size / 1024 / 1024, 1)} MB)")

    # Số bản dòng GCN = tổng số trang GCN của MỌI tệp GCN (ảnh chụp từng trang là nhiều tệp); thiếu số
    # trang của một tệp thì không đoán, để mặc định của cổng.
    gcn_infos = [r[2] for r in resolved if r[2]["docType"] == _GCN]
    so_trang_gcn = (
        sum(i["gcnPages"] for i in gcn_infos)
        if gcn_infos and all(i["gcnPages"] for i in gcn_infos) else None
    )

    for index, file_name, info, source in resolved:
        doc_type = info["docType"]
        entry = {
            "fileName": file_name,
            "docType": doc_type,
            "alsoTypes": info["alsoTypes"],
            "source": source,
        }
        if doc_type not in _ROUTES:
            # Dòng "Giấy tờ khác" phải có TÊN GIẤY TỜ; chỉ engine otherListFile của FE gõ được tên đó.
            document_name = _unique_document_name(info["documentName"], _OTHER_NAMES[doc_type], used_names)
            attachments.append({
                "fileIndex": index,
                "fileName": file_name,
                "documentName": document_name,
                "componentName": document_name,
                "target": "new",
                "needsAddComponent": True,
                "detectedType": doc_type,
                # Cổng iGate VNPT: bấm option "Chọn tệp tin" mở hộp thoại file của hệ điều hành → FE chỉ gán thẳng.
                "noChooserClick": True,
            })
            if doc_type == "other":
                unknown.append(f"{file_name} → \"{document_name}\"")
            classified.append({**entry, "documentName": document_name, "slotIndex": None})
            continue

        item = _slot_item(index, file_name, doc_type)
        if doc_type == _GCN and so_trang_gcn and so_trang_gcn <= _MAX_GCN_PAGES:
            item["soBan"] = so_trang_gcn
        attachments.append(item)
        filled.setdefault(doc_type, file_name)
        classified.append({**entry, "slotIndex": item["slotIndex"], "soBan": item.get("soBan")})

    # Dòng còn trống mà nội dung nằm trong một tệp scan gộp → đính lại chính tệp đó vào dòng này.
    for doc_type in _ROW_PRIORITY:
        if doc_type in filled:
            continue
        source = next((r for r in resolved if doc_type in r[2]["alsoTypes"]), None)
        if not source:
            continue
        index, file_name, _info, _src = source
        attachments.append(_slot_item(index, file_name, doc_type))
        filled[doc_type] = file_name
        warnings.append(
            f"Tệp {file_name} chứa cả \"{_ROUTES[doc_type]['display']}\" nên được đính thêm vào dòng "
            f"\"{_ROUTES[doc_type]['slotName']}\"."
        )

    if _PHIEU not in filled:
        warnings.append(
            "Chưa có Phiếu yêu cầu đăng ký thay đổi (Mẫu số 02a) — cổng bắt buộc dòng \"Đơn yêu cầu đăng ký "
            "thế chấp\" (*), cần tải lên phiếu đã ký vào dòng đó."
        )
    if _GCN not in filled:
        warnings.append("Chưa có Giấy chứng nhận quyền sử dụng đất — cần tải lên bản scan đủ các trang.")
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
    llm_types: dict[int, dict[str, Any]] = {}
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

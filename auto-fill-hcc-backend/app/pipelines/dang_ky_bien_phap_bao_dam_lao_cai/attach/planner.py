"""Đính kèm [Lào Cai - Cấp Sở] Đăng ký biện pháp bảo đảm bằng QSDĐ, TSGLVĐ (1.011441.000.00.00.H38).

Cổng eForm iGate `dichvucong.laocai.gov.vn`, bảng "Thành phần hồ sơ" — thứ tự DOM = slotIndex:

  0 (maGiayTo 14447): Hợp đồng thế chấp tài sản gắn liền với đất có công chứng, chứng thực hoặc xác nhận…
  1 (maGiayTo 13146, BẮT BUỘC): Giấy chứng nhận quyền sử dụng đất hoặc Giấy chứng nhận quyền sở hữu nhà ở…
  2 (maGiayTo 14446): Đơn yêu cầu đăng ký thế chấp  ← Phiếu yêu cầu Mẫu số 01a
  3 (maGiayTo 14448): Giấy chứng nhận quyền sử dụng đất, quyền sở hữu nhà ở và tài sản khác gắn liền với đất
  4 (maGiayTo 14449): Văn bản ủy quyền … (gồm cả giấy giới thiệu của tổ chức tín dụng)
  Sau bảng: ô "Ghi chú", 3 dòng "Giấy tờ khác" (`HoSoOnline_giayToKhac_file_1..3`, có ô "Tên giấy tờ" + nút
  "+") và ô `HoSoOnline_fileGiayToKhac`.

Mỗi dòng cố định có checkbox ở cột đầu phải tích thì cổng mới nhận tệp → `tickRow=True`.

⚑ HAI DÒNG GCN (1 và 3): tên dòng 3 là một đoạn của tên dòng 1 → khớp substring là trúng cả hai, nên
slotName ghi NGUYÊN VĂN ĐẦY ĐỦ và FE đi theo slotIndex (slotKey cố ý không nằm trong FIXED_SLOT_KEYWORDS
của content.js). Hồ sơ thế chấp nhiều thửa có nhiều GCN: số phát hành đầu tiên → dòng 1, số phát hành
KHÁC → dòng 3; LLM không đọc được số → dòng 1. Quy tắc tất định, LLM chỉ đọc `gcnSoPhatHanh`.

⚑ "SỐ BẢN" CỦA DÒNG GCN = SỐ TRANG GIẤY CHỨNG NHẬN (`gcnPages` → `soBan`).

⚑ Giấy tờ ngoài danh mục (CCCD, đăng ký doanh nghiệp, biên bản định giá tệp riêng, giấy lạ) đi
`target="new"`: engine `attachOneFileToOtherListFile` của FE thêm dòng "Giấy tờ khác", gõ TÊN GIẤY TỜ
rồi mới gán tệp. Tên do LLM đọc nội dung đặt — tên tệp đã mất dấu và dính số của hệ thống upload.

⚑ Hợp đồng thế chấp thường gộp lời chứng công chứng + biên bản định giá trong cùng tệp: tệp đó đi dòng 0,
nội dung gộp được ghi ở ô "Ghi chú" (bước process, field GhiChu_TepDinhChung).

Phân loại THUẦN LLM (không lưới keyword), 1 call/tệp. Tuyệt đối không bỏ sót tệp nào.
"""

import asyncio
import hashlib
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

# GCN mẫu cũ 4 trang, mẫu 2024 2 trang; con số lớn hơn nhiều là LLM đếm nhầm cả giấy tờ kèm theo.
_MAX_GCN_PAGES = 8

_HOP_DONG = "hop_dong_the_chap"
_GCN = "gcn"
_PHIEU = "phieu_01a"
_GCN_THU_HAI = "gcn_thu_hai"
_UY_QUYEN = "van_ban_uy_quyen"

# Dòng cố định trên cổng (key nội bộ → dòng). `gcn_thu_hai` không phải docType LLM trả, planner tự định tuyến.
_ROUTES: dict[str, dict[str, Any]] = {
    _HOP_DONG: {
        "slotIndex": 0,
        "slotName": "Hợp đồng thế chấp tài sản gắn liền với đất có công chứng, chứng thực hoặc xác nhận theo "
                    "quy định của pháp luật",
        "display": "Hợp đồng thế chấp tài sản gắn liền với đất",
    },
    _GCN: {
        "slotIndex": 1,
        "slotName": "Giấy chứng nhận quyền sử dụng đất hoặc Giấy chứng nhận quyền sở hữu nhà ở và quyền sử "
                    "dụng đất ở hoặc Giấy chứng nhận quyền sử dụng đất, quyền sở hữu nhà ở và tài sản khác "
                    "gắn liền với đất",
        "display": "Giấy chứng nhận quyền sử dụng đất",
    },
    _PHIEU: {
        "slotIndex": 2,
        "slotName": "Đơn yêu cầu đăng ký thế chấp",
        "display": "Phiếu yêu cầu đăng ký biện pháp bảo đảm (Mẫu số 01a)",
    },
    _GCN_THU_HAI: {
        "slotIndex": 3,
        "slotName": "Giấy chứng nhận quyền sử dụng đất, quyền sở hữu nhà ở và tài sản khác gắn liền với đất",
        "display": "Giấy chứng nhận quyền sử dụng đất thứ hai",
    },
    _UY_QUYEN: {
        "slotIndex": 4,
        "slotName": "Văn bản ủy quyền trong trường hợp người yêu cầu đăng ký xuất trình bản chính văn bản ủy "
                    "quyền thì chỉ cần nộp 01 bản sao để đối chiếu",
        "display": "Văn bản ủy quyền / Giấy giới thiệu",
    },
}
# docType LLM được phép trả mà có dòng cố định.
_FIXED_TYPES = (_HOP_DONG, _GCN, _PHIEU, _UY_QUYEN)
# Loại giấy tờ không có dòng riêng → "Giấy tờ khác" với tên mặc định khi LLM không đặt được tên.
_OTHER_NAMES = {
    "cccd": "Căn cước công dân",
    "dkdn": "Giấy chứng nhận đăng ký doanh nghiệp",
    "bien_ban_dinh_gia": "Biên bản định giá tài sản bảo đảm",
    "other": "Giấy tờ kèm theo hồ sơ",
}
_ALLOWED = set(_FIXED_TYPES) | set(_OTHER_NAMES)
# Thứ tự phủ dòng còn trống bằng tệp gộp: dòng bắt buộc trước.
_ROW_PRIORITY = (_GCN, _PHIEU, _HOP_DONG, _UY_QUYEN)

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
        if doc_type in _FIXED_TYPES and doc_type != primary and doc_type not in out:
            out.append(doc_type)
    return out


def _gcn_pages(value: Any) -> int | None:
    try:
        pages = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return pages if 1 <= pages <= _MAX_GCN_PAGES else None


def _serial(value: Any) -> str | None:
    """Số phát hành GCN để so trùng: bỏ khoảng trắng/ký tự lạ, viết hoa. Phải có cả chữ lẫn số."""
    text = re.sub(r"[^0-9A-Za-z]", "", _fold(value)).upper()
    return text if re.search(r"[A-Z]", text) and re.search(r"\d{5,}", text) else None


def _clean_document_name(raw: str) -> str:
    """Chuẩn hoá tên gõ vào ô "Tên giấy tờ": giữ số hiệu văn bản ("/" → "-"), bỏ ngoặc/dấu chấm/ký tự lạ."""
    text = unicodedata.normalize("NFC", str(raw or "")).replace("/", "-")
    text = re.sub(r"\.pdf$", "", text, flags=re.IGNORECASE)
    chars = [ch if (ch.isalnum() or ch in " _-,") else " " for ch in text]
    text = re.sub(r"\s+", " ", "".join(chars)).strip(" -,")
    return text[:_MAX_DOCUMENT_NAME].strip(" -,")


def _unique_document_name(base: str, fallback: str, used: set[str]) -> str:
    """Hai dòng "Giấy tờ khác" trùng tên thì cán bộ không phân biệt được → thêm số thứ tự."""
    value = _clean_document_name(base) or fallback
    key = _fold(value)
    if key not in used:
        used.add(key)
        return value
    stem = value[: _MAX_DOCUMENT_NAME - 3].strip()
    suffix = 2
    while True:
        candidate = f"{stem} {suffix}"
        if _fold(candidate) not in used:
            used.add(_fold(candidate))
            return candidate
        suffix += 1


def _payload(file: dict) -> str | None:
    data_url = file.get("dataUrl")
    if not isinstance(data_url, str) or "," not in data_url:
        return None
    return data_url.split(",", 1)[1] or None


def _file_bytes(file: dict) -> int | None:
    """Kích thước thật, suy từ độ dài base64 của dataUrl (FileItem không mang size)."""
    payload = _payload(file)
    if not payload:
        return None
    return len(payload) * 3 // 4 - payload[-2:].count("=")


def _coerce(raw: Any) -> dict[str, Any]:
    """Kết quả LLM của một tệp → dict chuẩn; chấp nhận cả dạng chỉ là chuỗi docType."""
    if isinstance(raw, str):
        raw = {"docType": raw}
    if not isinstance(raw, dict):
        raw = {}
    doc_type = _normalize_doc_type(raw.get("docType") or raw.get("type"))
    return {
        "docType": doc_type,
        "alsoTypes": _normalize_also(raw.get("alsoTypes"), doc_type),
        "documentName": str(raw.get("documentName") or "").strip(),
        "gcnSoPhatHanh": _serial(raw.get("gcnSoPhatHanh")) if doc_type == _GCN else None,
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
    # Một call cho mỗi tệp: PDF dài hoặc lỗi provider chỉ làm tệp đó rơi về other.
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


def _slot_item(index: int, file_name: str, route_key: str, doc_type: str) -> dict:
    route = _ROUTES[route_key]
    return {
        "fileIndex": index,
        "fileName": file_name,
        "documentName": route["display"],
        "componentName": route["slotName"],
        "target": "fixed-slot",
        "needsAddComponent": False,
        "slotKey": f"laocai_dkbpbd_{route_key}",
        "slotIndex": route["slotIndex"],
        "slotName": route["slotName"],
        "detectedType": doc_type,
        "tickRow": True,
    }


def _other_item(index: int, file_name: str, document_name: str, doc_type: str) -> dict:
    return {
        "fileIndex": index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": document_name,
        "target": "new",
        "needsAddComponent": True,
        "detectedType": doc_type,
        # Cổng iGate VNPT: bấm option "Chọn tệp tin" mở hộp thoại file của hệ điều hành → FE chỉ gán thẳng.
        "noChooserClick": True,
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
    trung_lap: list[str] = []
    used_names: set[str] = set()
    filled: dict[str, str] = {}
    seen_payloads: dict[str, str] = {}

    resolved: list[tuple[int, str, dict[str, Any], str]] = []
    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        info = _coerce(llm_types.get(index)) if index in llm_types else _coerce(None)
        resolved.append((index, file_name, info, "llm" if index in llm_types else "default"))
        size = _file_bytes(file)
        if size and size > _MAX_FILE_BYTES:
            qua_nang.append(f"{file_name} ({round(size / 1024 / 1024, 1)} MB)")
        payload = _payload(file)
        if payload:
            digest = hashlib.sha256(payload.encode("ascii", "ignore")).hexdigest()
            if digest in seen_payloads:
                trung_lap.append(f"{file_name} trùng {seen_payloads[digest]}")
            else:
                seen_payloads[digest] = file_name

    # Số phát hành GCN đầu tiên đọc được là "GCN chính" (dòng 1); số khác là GCN thứ hai (dòng 3).
    serial_chinh = next(
        (info["gcnSoPhatHanh"] for _i, _n, info, _s in resolved if info["docType"] == _GCN and info["gcnSoPhatHanh"]),
        None,
    )
    serial_thu_hai: str | None = None

    for index, file_name, info, source in resolved:
        doc_type = info["docType"]
        entry = {
            "fileName": file_name,
            "docType": doc_type,
            "alsoTypes": info["alsoTypes"],
            "source": source,
        }

        route_key: str | None = doc_type if doc_type in _FIXED_TYPES else None
        if doc_type == _GCN:
            serial = info["gcnSoPhatHanh"]
            if serial and serial_chinh and serial != serial_chinh:
                if serial_thu_hai in (None, serial):
                    serial_thu_hai = serial
                    route_key = _GCN_THU_HAI
                else:
                    # Dòng 3 đã có GCN khác số → không có dòng cố định cho GCN thứ ba.
                    route_key = None
            entry["gcnSoPhatHanh"] = serial

        if route_key is None:
            fallback = _OTHER_NAMES.get(doc_type) or _ROUTES[_GCN]["display"]
            document_name = _unique_document_name(info["documentName"], fallback, used_names)
            attachments.append(_other_item(index, file_name, document_name, doc_type))
            if doc_type == "other":
                unknown.append(f"{file_name} → \"{document_name}\"")
            if doc_type == _GCN:
                warnings.append(
                    f"Tệp {file_name} là Giấy chứng nhận thứ ba (số phát hành khác hai GCN đã đính) — cổng chỉ "
                    "có hai dòng Giấy chứng nhận nên đã đưa vào \"Giấy tờ khác\"."
                )
            classified.append({**entry, "documentName": document_name, "slotIndex": None})
            continue

        item = _slot_item(index, file_name, route_key, doc_type)
        if doc_type == _GCN and info["gcnPages"]:
            item["soBan"] = info["gcnPages"]
        attachments.append(item)
        filled.setdefault(route_key, file_name)
        classified.append({**entry, "slotIndex": item["slotIndex"], "soBan": item.get("soBan")})

    # Dòng còn trống mà nội dung nằm trong một tệp scan gộp → đính lại chính tệp đó vào dòng này.
    for route_key in _ROW_PRIORITY:
        if route_key in filled:
            continue
        found = next((r for r in resolved if route_key in r[2]["alsoTypes"]), None)
        if not found:
            continue
        index, file_name, _info, _src = found
        attachments.append(_slot_item(index, file_name, route_key, route_key))
        filled[route_key] = file_name
        warnings.append(
            f"Tệp {file_name} chứa cả \"{_ROUTES[route_key]['display']}\" nên được đính thêm vào dòng "
            f"\"{_ROUTES[route_key]['slotName']}\"."
        )

    if _GCN not in filled:
        warnings.append(
            "Chưa có Giấy chứng nhận quyền sử dụng đất — dòng Giấy chứng nhận là thành phần BẮT BUỘC của cổng, "
            "cần tải lên bản scan đủ các trang."
        )
    if _PHIEU not in filled:
        warnings.append(
            "Chưa nhận ra Phiếu yêu cầu đăng ký (Mẫu số 01a) cho dòng \"Đơn yêu cầu đăng ký thế chấp\" — cần "
            "tải lên phiếu đã ký."
        )
    if unknown:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã thêm dòng \"Giấy tờ khác\" kèm tên tài liệu để không bỏ "
            f"sót — cán bộ kiểm tra lại: {', '.join(unknown)}."
        )
    if trung_lap:
        warnings.append(
            "Có tệp trùng nội dung hoàn toàn với tệp khác (vẫn đính đủ để không bỏ sót) — cán bộ xem có tải "
            f"nhầm tệp không: {', '.join(trung_lap)}."
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

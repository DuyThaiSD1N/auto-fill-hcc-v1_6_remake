"""Đính kèm [Lào Cai] đăng ký, cấp GCN khi đã chuyển quyền SDĐ trước 01/8/2024 (1.115666).

Cổng `dichvucong.laocai.gov.vn` (eForm iGate). Trang `nhap-thong-tin-ho-so` có **11 `input[type=file]`**
theo thứ tự DOM, mỗi ô kèm nút "Chọn tệp tin" → engine FE `fixed-slot`:

  0 : "a) Trường hợp … chỉ có hợp đồng, văn bản về chuyển quyền …"   (tiêu đề NHÁNH a)
  1 : Đơn đăng ký biến động Mẫu số 24                                (nhánh a)
  2 : Hợp đồng, văn bản về chuyển quyền sử dụng đất đã lập theo quy định (nhánh a)
  3 : "b) Trường hợp … chỉ có Giấy chứng nhận đã cấp của bên chuyển quyền …" (tiêu đề NHÁNH b)
  4 : Đơn đăng ký biến động Mẫu số 24                                (nhánh b)
  5 : Bản gốc Giấy chứng nhận đã cấp                                 (nhánh b)
  6 : Giấy tờ về việc chuyển quyền có đủ chữ ký của hai bên          (nhánh b)
  7–9 : 3 dòng "Giấy tờ khác" (`HoSoOnline_giayToKhac_file_1..3`)
  10  : ô `HoSoOnline_fileGiayToKhac`

⚑ HAI DÒNG TRÙNG TÊN: slot 1 và slot 4 đều là "Đơn đăng ký biến động … Mẫu số 24" → KHÔNG thể khớp bằng
text, bắt buộc dùng `slotIndex`. slotKey cố ý không nằm trong `FIXED_SLOT_KEYWORDS` để FE bỏ bước
keyword.

⚑ HAI NHÁNH a) và b) LOẠI TRỪ NHAU — hồ sơ chỉ thuộc MỘT trường hợp. Quy tắc chọn nhánh (tất định, theo
đúng câu chữ của biểu mẫu): có văn bản/hợp đồng chuyển quyền → **nhánh a**; chỉ có Giấy chứng nhận của
bên chuyển quyền mà không có văn bản chuyển quyền → **nhánh b**. Planner luôn phát cảnh báo nêu rõ đã
xếp theo nhánh nào để cán bộ bỏ tick nhánh còn lại.

⚑ Giấy tờ NGOÀI danh mục dùng `target="new"` + `needsAddComponent=True`: trang có
`input[name="HoSoOnline_giayToKhac[]"]` nên FE chạy `attachOneFileToOtherListFile` — engine này **điền
cả TÊN tài liệu** rồi mới đính tệp. Đẩy vào slot 7–9 bằng fixed-slot thì tệp lên nhưng ô tên TRỐNG.

Phân loại THUẦN LLM (không lưới keyword). Không bỏ sót tệp nào.
"""

import asyncio
import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import normalize_document_name
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_LOAI_BAN = "Bản chính"

_NHANH_A = "a"
_NHANH_B = "b"

_SLOT_NAMES = {
    1: "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 24 (nhánh a)",
    2: "Hợp đồng, văn bản về chuyển quyền sử dụng đất đã lập theo quy định",
    4: "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 24 (nhánh b)",
    5: "Bản gốc Giấy chứng nhận đã cấp",
    6: "Giấy tờ về việc chuyển quyền sử dụng đất có đủ chữ ký của bên chuyển quyền và bên nhận chuyển quyền",
}

# docType → slotIndex theo từng nhánh. GCN chỉ có MỘT dòng mang tên đó (slot 5) nên dùng chung.
_ROUTES: dict[str, dict[str, int]] = {
    "don_mau_24": {_NHANH_A: 1, _NHANH_B: 4},
    "van_ban_chuyen_quyen": {_NHANH_A: 2, _NHANH_B: 6},
    "gcn_ban_goc": {_NHANH_A: 5, _NHANH_B: 5},
}
_DISPLAY = {
    "don_mau_24": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 24)",
    "van_ban_chuyen_quyen": "Văn bản về việc chuyển quyền sử dụng đất",
    "gcn_ban_goc": "Bản gốc Giấy chứng nhận đã cấp",
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


def _other_component_name(file_name: str) -> str:
    """Tên dòng 'Giấy tờ khác' — engine otherListFile điền chuỗi này vào ô tên tài liệu."""
    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", str(file_name or "")).strip()
    stem = re.sub(r"[_]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return normalize_document_name(stem, "Tài liệu khác kèm theo") if stem else "Tài liệu khác kèm theo"


def _chon_nhanh(doc_types: list[str]) -> str:
    """Hồ sơ CÓ văn bản chuyển quyền → nhánh a); chỉ có Giấy chứng nhận → nhánh b)."""
    return _NHANH_A if "van_ban_chuyen_quyen" in doc_types else _NHANH_B


async def _classify_one(document: dict[str, Any]) -> tuple[int, str]:
    index = int(document.get("index"))
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(
            [{"index": index, "text": str(document.get("text") or "")[:12000]}]
        )},
    ]
    raw = await client.chat(messages, max_tokens=120, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    first = next(iter(parsed.get("documents", []) or []), {})
    return index, _normalize_doc_type(first.get("docType") or first.get("type"))


async def _classify_with_llm(
    documents: list[dict[str, Any]],
    errors: list[str] | None = None,
) -> dict[int, str]:
    if not documents:
        return {}
    outcomes = await asyncio.gather(*(_classify_one(d) for d in documents), return_exceptions=True)
    result: dict[int, str] = {}
    for document, outcome in zip(documents, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            if errors is not None:
                errors.append(f"attachment_agent file {document.get('index')}: {outcome}")
            continue
        index, doc_type = outcome
        result[index] = doc_type
    return result


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    resolved = [
        (index, str(file.get("name") or f"file-{index + 1}"),
         llm_types.get(index) if llm_types.get(index) in _ALLOWED else "other")
        for index, file in enumerate(files)
    ]
    nhanh = _chon_nhanh([t for _, _, t in resolved])

    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    unknown: list[str] = []
    by_slot: dict[int, list[str]] = {}

    for index, file_name, doc_type in resolved:
        source = "llm" if index in llm_types else "default"
        if doc_type == "other":
            component_name = _other_component_name(file_name)
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
            }
            unknown.append(file_name)
        else:
            slot_index = _ROUTES[doc_type][nhanh]
            slot_name = _SLOT_NAMES[slot_index]
            item = {
                "fileIndex": index,
                "fileName": file_name,
                "documentName": _DISPLAY[doc_type],
                "componentName": slot_name,
                "loaiBan": _LOAI_BAN,
                "target": "fixed-slot",
                "needsAddComponent": False,
                "slotKey": f"laocai_cq2024_{doc_type}_{nhanh}",
                "slotIndex": slot_index,
                "slotName": slot_name,
                "detectedType": doc_type,
            }
            by_slot.setdefault(slot_index, []).append(file_name)

        attachments.append(item)
        classified.append({
            "fileName": file_name,
            "docType": doc_type,
            "source": source,
            "nhanh": nhanh,
            "slotIndex": item.get("slotIndex"),
        })

    if by_slot:
        warnings.append(
            f"Hồ sơ được xếp theo TRƯỜNG HỢP {nhanh.upper()}) "
            + ("(có văn bản/hợp đồng chuyển quyền)." if nhanh == _NHANH_A
               else "(chỉ có Giấy chứng nhận của bên chuyển quyền, không có văn bản chuyển quyền).")
            + " Hai trường hợp a) và b) LOẠI TRỪ NHAU — cán bộ bỏ tick các dòng của trường hợp còn lại."
        )
    if unknown:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã thêm dòng \"Giấy tờ khác\" đặt tên theo tệp để không bỏ sót — "
            f"cán bộ kiểm tra lại: {', '.join(unknown)}."
        )
    for slot_index, names in by_slot.items():
        if len(names) > 1:
            warnings.append(
                f"Dòng \"{_SLOT_NAMES[slot_index]}\" nhận {len(names)} tệp ({', '.join(names)}) — kiểm "
                "tra xem có tệp trùng nội dung không, và ghi rõ danh mục vào ô \"Ghi chú\"."
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

"""Đính kèm [Lào Cai] Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót (1.115686).

Cổng `dichvucong.laocai.gov.vn` (eForm iGate). Trang đính kèm có **8 `input[type=file]`**: 4 dòng
thành phần hồ sơ + 3 ô "Giấy tờ khác" + `HoSoOnline_fileGiayToKhac`.

  0 : Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 24 (QĐ 47/2026/QĐ-UBND)
  1 : Bản gốc Giấy chứng nhận đã cấp
  2 : Giấy tờ chứng minh sai sót thông tin của người được cấp Giấy chứng nhận
  3 : Văn bản về việc ủy quyền theo quy định của pháp luật về dân sự
  4–6 : 3 dòng "Giấy tờ khác" · 7 : `HoSoOnline_fileGiayToKhac`

⚑ CCCD CÓ DÒNG RIÊNG ở thủ tục này (dòng 2) — khác hẳn phần lớn thủ tục đất đai khác, nơi CCCD không
có chỗ nên bị đẩy sang "Giấy tờ khác". CCCD chính là thứ chứng minh thông tin đúng (tên, năm sinh) so
với thông tin sai in trên Giấy chứng nhận.

⚑ MỘT TỆP CÓ THỂ GỘP NHIỀU GIẤY CHỨNG NHẬN (hồ sơ thật: 1 tệp 10 trang = 05 GCN). Vẫn đính vào MỘT
dòng, nhưng ô "Số bản" trên bảng phải sửa thành số Giấy chứng nhận — FE không điền ô đó nên planner
phát cảnh báo.

Phân loại THUẦN LLM (không lưới keyword). Mỗi tệp chỉ đính vào MỘT dòng. Không bỏ sót tệp nào.
"""

import asyncio
import re
import time
import unicodedata
from typing import Any

from app.config import settings
from app.pipelines._shared import normalize_document_name
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_LOAI_BAN = "Bản chính"

# Giới hạn tải lên của cổng, in ngay trên bảng thành phần hồ sơ.
_GIOI_HAN_BYTE = 6 * 1024 * 1024

_T_DON = "don_mau_24"
_T_GCN = "gcn_ban_goc"
_T_CHUNG_MINH = "giay_to_chung_minh_sai_sot"
_T_UY_QUYEN = "van_ban_uy_quyen"
_T_OTHER = "other"

_SLOT_NAMES = {
    0: "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 24",
    1: "Bản gốc Giấy chứng nhận đã cấp",
    2: "Giấy tờ chứng minh sai sót thông tin của người được cấp Giấy chứng nhận",
    3: "Văn bản về việc ủy quyền theo quy định của pháp luật về dân sự",
}

_ROUTES: dict[str, int] = {
    _T_DON: 0,
    _T_GCN: 1,
    _T_CHUNG_MINH: 2,
    _T_UY_QUYEN: 3,
}
_DISPLAY = {
    _T_DON: "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 24)",
    _T_GCN: "Bản gốc Giấy chứng nhận đã cấp",
    _T_CHUNG_MINH: "Giấy tờ chứng minh sai sót thông tin của người được cấp Giấy chứng nhận",
    _T_UY_QUYEN: "Văn bản về việc ủy quyền",
}
_ALLOWED = set(_ROUTES) | {_T_OTHER}

# Thứ tự phủ dòng: Đơn là giấy tờ bắt buộc số một → tệp gộp luôn ưu tiên dòng này.
_ROW_PRIORITY = (_T_DON, _T_GCN, _T_CHUNG_MINH, _T_UY_QUYEN)


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
    return _T_OTHER


def _normalize_also(values: Any, primary: str) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for value in values:
        doc_type = _normalize_doc_type(value)
        if doc_type not in (_T_OTHER, primary) and doc_type not in out:
            out.append(doc_type)
    return out


def _kich_thuoc(file: dict) -> int | None:
    """Kích thước thật của tệp, suy từ độ dài phần base64 của dataUrl (FileItem không mang size)."""
    data_url = file.get("dataUrl")
    if not isinstance(data_url, str) or "," not in data_url:
        return None
    b64 = data_url.split(",", 1)[1]
    if not b64:
        return None
    return len(b64) * 3 // 4 - b64[-2:].count("=")


def _other_component_name(file_name: str) -> str:
    """Tên dòng 'Giấy tờ khác' — engine otherListFile điền chuỗi này vào ô tên tài liệu."""
    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", str(file_name or "")).strip()
    stem = re.sub(r"[_]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return normalize_document_name(stem, "Tài liệu khác kèm theo") if stem else "Tài liệu khác kèm theo"


async def _classify_one(document: dict[str, Any]) -> tuple[int, str, list[str]]:
    index = int(document.get("index"))
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(
            [{"index": index, "text": str(document.get("text") or "")[:14000]}]
        )},
    ]
    raw = await client.chat(messages, max_tokens=160, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    first = next(iter(parsed.get("documents", []) or []), {})
    doc_type = _normalize_doc_type(first.get("docType") or first.get("type"))
    return index, doc_type, _normalize_also(first.get("alsoTypes"), doc_type)


async def _classify_with_llm(
    documents: list[dict[str, Any]],
    errors: list[str] | None = None,
) -> dict[int, tuple[str, list[str]]]:
    if not documents:
        return {}
    outcomes = await asyncio.gather(*(_classify_one(d) for d in documents), return_exceptions=True)
    result: dict[int, tuple[str, list[str]]] = {}
    for document, outcome in zip(documents, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            if errors is not None:
                errors.append(f"attachment_agent file {document.get('index')}: {outcome}")
            continue
        index, doc_type, also = outcome
        result[index] = (doc_type, also)
    return result


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, tuple[str, list[str]] | str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}

    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    unknown: list[str] = []
    qua_nang: list[str] = []
    by_slot: dict[int, list[str]] = {}
    da_dung: set[str] = set()

    resolved: list[tuple[int, str, str, list[str], str]] = []
    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        raw = llm_types.get(index)
        doc_type, also = raw if isinstance(raw, tuple) else (raw, [])
        if doc_type not in _ALLOWED:
            doc_type = _T_OTHER
        also = _normalize_also(also, doc_type) if doc_type != _T_OTHER else []
        resolved.append((index, file_name, doc_type, also, "llm" if index in llm_types else "default"))
        size = _kich_thuoc(file)
        if size and size > _GIOI_HAN_BYTE:
            qua_nang.append(f"{file_name} ({round(size / 1024 / 1024, 1)} MB)")

    for index, file_name, doc_type, also, source in resolved:
        if doc_type == _T_OTHER:
            component_name = _other_component_name(file_name)
            attachments.append({
                "fileIndex": index,
                "fileName": file_name,
                "documentName": component_name,
                "componentName": component_name,
                "loaiBan": _LOAI_BAN,
                # Engine otherListFile của FE điền TÊN tài liệu rồi mới đính tệp.
                "target": "new",
                "needsAddComponent": True,
                "detectedType": doc_type,
            })
            unknown.append(file_name)
            classified.append({
                "fileName": file_name, "docType": doc_type, "alsoTypes": also,
                "assignedType": None, "source": source, "slotIndex": None,
            })
            continue

        # Mỗi tệp CHỈ một dòng; tệp gộp dùng để phủ dòng còn trống, ưu tiên Đơn Mẫu 24.
        ung_vien = [t for t in _ROW_PRIORITY if t in (doc_type, *also) and t not in da_dung]
        chon = ung_vien[0] if ung_vien else doc_type

        slot_index = _ROUTES[chon]
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": _DISPLAY[chon],
            "componentName": _SLOT_NAMES[slot_index],
            "loaiBan": _LOAI_BAN,
            "target": "fixed-slot",
            "needsAddComponent": False,
            # Cố ý không trùng FIXED_SLOT_KEYWORDS của extension để FE đi thẳng theo slotIndex.
            "slotKey": f"laocai_dcgcn_{chon}",
            "slotIndex": slot_index,
            "slotName": _SLOT_NAMES[slot_index],
            "detectedType": doc_type,
        })
        by_slot.setdefault(slot_index, []).append(file_name)
        da_dung.add(chon)
        classified.append({
            "fileName": file_name, "docType": doc_type, "alsoTypes": also,
            "assignedType": chon, "source": source, "slotIndex": slot_index,
        })

    if _ROUTES[_T_GCN] in by_slot:
        warnings.append(
            "Ô \"Số bản\" của dòng \"Bản gốc Giấy chứng nhận đã cấp\" phải bằng SỐ GIẤY CHỨNG NHẬN "
            "trong tệp (một tệp scan có thể gộp nhiều Giấy chứng nhận) — hệ thống chỉ đính tệp, không "
            "sửa được ô này. Ghi rõ tệp gồm mấy Giấy chứng nhận và trang của từng cái vào ô \"Ghi chú\"."
        )
    if _ROUTES[_T_CHUNG_MINH] not in by_slot:
        warnings.append(
            "Chưa có tệp ở dòng \"Giấy tờ chứng minh sai sót thông tin của người được cấp Giấy chứng "
            "nhận\" — thường là CĂN CƯỚC CÔNG DÂN của người có thông tin bị sai. Bắt buộc khi cơ quan "
            "không khai thác được Cơ sở dữ liệu quốc gia về dân cư."
        )
    if qua_nang:
        warnings.append(
            f"Tệp vượt giới hạn 6 MB của cổng, phải nén hoặc giảm DPI trước khi tải lên: "
            f"{', '.join(qua_nang)}."
        )
    if unknown:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã thêm dòng \"Giấy tờ khác\" đặt tên theo tệp để không bỏ sót "
            f"— cán bộ kiểm tra lại: {', '.join(unknown)}."
        )
    for slot_index, names in by_slot.items():
        unique = list(dict.fromkeys(names))
        if len(unique) > 1:
            warnings.append(
                f"Dòng \"{_SLOT_NAMES[slot_index]}\" nhận {len(unique)} tệp ({', '.join(unique)}) — "
                "kiểm tra lại số bản khai trên bảng thành phần hồ sơ."
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
    llm_types: dict[int, tuple[str, list[str]]] = {}
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

"""Đính kèm [Lào Cai] đăng ký biến động do chia, tách, hợp nhất, sáp nhập tổ chức (1.115670).

Cổng `dichvucong.laocai.gov.vn` (eForm iGate). Trang `nhap-thong-tin-ho-so` có **12 `input[type=file]`**
theo thứ tự DOM — 8 dòng thành phần hồ sơ rồi tới phần "Giấy tờ khác":

  0 : Quyết định phê duyệt điều chỉnh quy hoạch xây dựng chi tiết (+ bản đồ điều chỉnh, bản đồ địa chính)
  1 : Giấy chứng nhận đăng ký doanh nghiệp / văn bản về việc thành lập tổ chức SAU KHI THAY ĐỔI
  2 : Mảnh trích đo bản đồ địa chính thửa đất
  3 : Quyết định, văn bản về việc chia, tách, hợp nhất, sáp nhập, chuyển đổi mô hình tổ chức/loại hình DN
  4 : Văn bản về việc đại diện theo pháp luật dân sự (ủy quyền)
  5 : Giấy chứng nhận đã cấp
  6 : Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 24 (QĐ 47/2026/QĐ-UBND)
  7 : Bản vẽ tách thửa đất, hợp thửa đất theo Mẫu số 28
  8–10 : 3 dòng "Giấy tờ khác" (`HoSoOnline_giayToKhac_file_1..3`)
  11   : ô `HoSoOnline_fileGiayToKhac`

⚑ MỘT TỆP GỘP ĐÍNH VÀO NHIỀU DÒNG. Hồ sơ thật của cổng này hay là một bản scan liên tục (16 trang) chứa
Đơn + quyết định thành lập + quyết định giao tài sản + Giấy chứng nhận. Cán bộ phải nộp CÙNG tệp đó vào
từng dòng tương ứng, nên LLM trả thêm `alsoTypes` và planner sinh một item cho mỗi dòng (cùng
`fileIndex`, khác `slotIndex`) thay vì bắt người dùng tách tệp.

⚑ Giấy tờ NGOÀI danh mục dùng `target="new"` + `needsAddComponent=True`: trang có
`input[name="HoSoOnline_giayToKhac[]"]` nên FE chạy `attachOneFileToOtherListFile` — engine này điền cả
TÊN tài liệu rồi mới đính tệp. Đẩy vào ô 8–10 bằng fixed-slot thì tệp lên nhưng ô tên TRỐNG.

Phân loại THUẦN LLM (không lưới keyword). Không bỏ sót tệp nào.
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

# Nhãn hiển thị cho cán bộ. FE đi bằng slotIndex nên không cần khớp nguyên văn DOM — bản in trên cổng
# còn có lỗi gõ ("Giấy ch ứng nhận", "Quyết đ ịnh") nên chép nguyên si chỉ làm cảnh báo khó đọc.
_SLOT_NAMES = {
    0: "Quyết định phê duyệt điều chỉnh quy hoạch xây dựng chi tiết của cơ quan có thẩm quyền",
    1: "Giấy chứng nhận đăng ký doanh nghiệp hoặc văn bản về việc thành lập tổ chức sau khi thay đổi",
    2: "Mảnh trích đo bản đồ địa chính thửa đất",
    3: "Quyết định của cơ quan, tổ chức có thẩm quyền hoặc văn bản về việc chia, tách, hợp nhất, sáp nhập",
    4: "Văn bản về việc đại diện theo quy định của pháp luật về dân sự",
    5: "Giấy chứng nhận đã cấp",
    6: "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 24",
    7: "Bản vẽ tách thửa đất, hợp thửa đất theo Mẫu số 28",
}

# docType → slotIndex. Bảng chỉ có MỘT nhánh nên map thẳng, không phải chọn trường hợp như 1.115666.
_ROUTES: dict[str, int] = {
    "qd_dieu_chinh_quy_hoach": 0,
    "van_ban_thanh_lap_to_chuc": 1,
    "manh_trich_do": 2,
    "qd_chia_tach_sap_nhap": 3,
    "van_ban_dai_dien": 4,
    "gcn_da_cap": 5,
    "don_mau_24": 6,
    "ban_ve_tach_hop_thua": 7,
}
_DISPLAY = {
    "qd_dieu_chinh_quy_hoach": "Quyết định phê duyệt điều chỉnh quy hoạch xây dựng chi tiết",
    "van_ban_thanh_lap_to_chuc": "Văn bản về việc thành lập tổ chức sau khi thay đổi",
    "manh_trich_do": "Mảnh trích đo bản đồ địa chính thửa đất",
    "qd_chia_tach_sap_nhap": "Quyết định về việc chia, tách, hợp nhất, sáp nhập, chuyển đổi tổ chức",
    "van_ban_dai_dien": "Văn bản về việc đại diện",
    "gcn_da_cap": "Giấy chứng nhận đã cấp",
    "don_mau_24": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 24)",
    "ban_ve_tach_hop_thua": "Bản vẽ tách thửa đất, hợp thửa đất (Mẫu số 28)",
}
_ALLOWED = set(_ROUTES) | {"other"}

# Thứ tự ưu tiên PHỦ DÒNG, theo mức bắt buộc của giấy tờ trong thủ tục: Đơn → quyết định làm phát sinh
# biến động → Giấy chứng nhận đang có → tư cách tổ chức mới → nhóm chỉ dùng cho trường hợp đặc thù.
_ROW_PRIORITY = (
    "don_mau_24",
    "qd_chia_tach_sap_nhap",
    "gcn_da_cap",
    "van_ban_thanh_lap_to_chuc",
    "manh_trich_do",
    "ban_ve_tach_hop_thua",
    "qd_dieu_chinh_quy_hoach",
    "van_ban_dai_dien",
)


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
    """Các loại giấy tờ KHÁC cùng nằm trong một tệp gộp — mỗi loại sẽ thành một dòng nữa."""
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for value in values:
        doc_type = _normalize_doc_type(value)
        if doc_type != "other" and doc_type != primary and doc_type not in out:
            out.append(doc_type)
    return out


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
            [{"index": index, "text": str(document.get("text") or "")[:16000]}]
        )},
    ]
    raw = await client.chat(messages, max_tokens=220, enable_thinking=settings.agent_reasoning)
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


def _slot_item(index: int, file_name: str, doc_type: str) -> dict:
    slot_index = _ROUTES[doc_type]
    slot_name = _SLOT_NAMES[slot_index]
    return {
        "fileIndex": index,
        "fileName": file_name,
        "documentName": _DISPLAY[doc_type],
        "componentName": slot_name,
        "loaiBan": _LOAI_BAN,
        "target": "fixed-slot",
        "needsAddComponent": False,
        # Cố ý không trùng FIXED_SLOT_KEYWORDS của extension để FE đi thẳng theo slotIndex.
        "slotKey": f"laocai_bdtc_{doc_type}",
        "slotIndex": slot_index,
        "slotName": slot_name,
        "detectedType": doc_type,
    }


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, tuple[str, list[str]] | str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}

    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    unknown: list[str] = []
    con_thieu: list[str] = []
    by_slot: dict[int, list[str]] = {}
    da_dung: set[str] = set()

    resolved: list[tuple[int, str, str, list[str], str]] = []
    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        raw = llm_types.get(index)
        doc_type, also = raw if isinstance(raw, tuple) else (raw, [])
        if doc_type not in _ALLOWED:
            doc_type = "other"
        # Chuẩn hoá lại ngay tại đây: alsoTypes có thể tới thẳng từ LLM với loại lạ/trùng/"other".
        also = _normalize_also(also, doc_type) if doc_type != "other" else []
        resolved.append((index, file_name, doc_type, also, "llm" if index in llm_types else "default"))

    for index, file_name, doc_type, also, source in resolved:
        if doc_type == "other":
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
                "source": source, "slotIndex": None,
            })
            continue

        # MỖI TỆP CHỈ ĐÍNH VÀO MỘT DÒNG. Bản scan gộp chứa nhiều giấy tờ thì dùng để PHỦ dòng còn
        # trống — hồ sơ thật có hai bản scan giống hệt nhau, cán bộ nộp vào hai dòng khác nhau. Nhân
        # bản tệp ra mọi dòng nó chứa sẽ biến hồ sơ 3 tệp thành hàng chục lượt đính.
        chua_co = [t for t in _ROW_PRIORITY if t in (doc_type, *also) and t not in da_dung]
        chon = chua_co[0] if chua_co else doc_type

        attachments.append(_slot_item(index, file_name, chon))
        by_slot.setdefault(_ROUTES[chon], []).append(file_name)
        da_dung.add(chon)
        classified.append({
            "fileName": file_name,
            "docType": doc_type,
            "alsoTypes": also,
            "assignedType": chon,
            "source": source,
            "slotIndex": _ROUTES[chon],
        })

    # Dòng chưa có tệp nào nhưng nội dung nằm trong một bản scan gộp: chỉ GỢI Ý, để cán bộ tự quyết có
    # nộp lại cùng tệp vào dòng đó hay không (đúng cách hồ sơ mẫu được cán bộ xử lý).
    for doc_type in _ROW_PRIORITY:
        if doc_type in da_dung:
            continue
        nguon = [name for _, name, chinh, also, _ in resolved if doc_type in (chinh, *also)]
        if nguon:
            con_thieu.append(f'"{_SLOT_NAMES[_ROUTES[doc_type]]}" (có trong {", ".join(nguon)})')
    if con_thieu:
        warnings.append(
            "Mỗi tệp chỉ được đính vào MỘT dòng. Các dòng sau chưa có tệp nhưng nội dung nằm trong bản "
            "scan gộp — cán bộ cân nhắc nộp lại cùng tệp vào đó: " + "; ".join(con_thieu)
            + ". Ghi rõ tệp nào chứa văn bản nào (kèm số trang) vào ô \"Ghi chú\"."
        )
    if unknown:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã thêm dòng \"Giấy tờ khác\" đặt tên theo tệp để không bỏ sót — "
            f"cán bộ kiểm tra lại: {', '.join(unknown)}."
        )
    for slot_index, names in by_slot.items():
        unique = list(dict.fromkeys(names))
        if len(unique) > 1:
            warnings.append(
                f"Dòng \"{_SLOT_NAMES[slot_index]}\" nhận {len(unique)} tệp ({', '.join(unique)}) — kiểm "
                "tra xem có tệp trùng nội dung không."
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

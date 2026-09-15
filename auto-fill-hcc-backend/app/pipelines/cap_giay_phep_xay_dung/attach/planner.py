"""Đính kèm bước thành phần hồ sơ cho thủ tục cấp giấy phép xây dựng mới (cổng Bộ Xây dựng).

⚠ BẢNG THÀNH PHẦN HỒ SƠ ĐÃ ĐỔI (Nghị định 217/2026/NĐ-CP thay 175/2024): cổng không còn một danh
sách phẳng nữa mà chia **29 dòng thành 5 KHỐI theo LOẠI CÔNG TRÌNH**, mỗi khối lặp lại gần như y hệt
bộ giấy tờ (Đơn · Giấy tờ đất đai · [giấy đặc thù] · Bộ bản vẽ · dữ liệu BIM):

  dòng  1– 5  Công trình KHÔNG THEO TUYẾN (dự án)   : đơn 1,  đất 2,  bản vẽ 4
  dòng  6–11  TÍN NGƯỠNG, TÔN GIÁO                  : đơn 6,  đất 7,  bản vẽ 10
  dòng 12–16  NHÀ Ở RIÊNG LẺ                        : đơn 12, đất 13, bản vẽ 16
  dòng 17–22  TƯỢNG ĐÀI, TRANH HOÀNH TRÁNG          : đơn 17, đất 18, bản vẽ 20
  dòng 23–27  THEO GIAI ĐOẠN / DỰ ÁN                : đơn 23, đất 24, bản vẽ 26
  dòng 28     Đơn điều chỉnh/gia hạn/cấp lại (Mẫu 02)
  dòng 29     Hiệp định/thỏa thuận với Chính phủ VN

Chốt nghiệp vụ (BA, 2026-09-14): hồ sơ NHÀ Ở RIÊNG LẺ cấp III/IV phải vào **12, 13, 16**; công trình
tín ngưỡng/tôn giáo (nhà chùa…) vào **6, 7, 10**. Trước đây kế hoạch đính vào 1, 2, 27 → SAI khối.

⚑ VÌ SAO PHẢI ĐỔI slotKey (đọc kỹ trước khi sửa):
Engine FE `attachFilesByFixedSlot` tìm ô upload theo THỨ TỰ ƯU TIÊN: (1) khớp KEYWORD theo
`FIXED_SLOT_KEYWORDS[slotKey]` trong content.js, (2) mới đến `slotIndex`. Các khối trên có text đơn/
đất gần như TRÙNG KHÍT nhau nên keyword KHÔNG THỂ phân biệt khối — nó luôn bắt dòng đầu tiên khớp,
tức dòng 1 và 2. Đó chính là lý do hồ sơ thật rơi vào 1, 2 (và bản vẽ rơi xuống 27 do keyword cũ
"…nhà ở riêng lẻ" không còn trong bảng mới nên rớt về slotIndex 26).
→ Các slotKey ở đây được đặt tên MỚI, CỐ Ý KHÔNG CÓ trong `FIXED_SLOT_KEYWORDS` của extension, để FE
bỏ qua bước keyword và dùng thẳng `slotIndex`. Nhờ vậy sửa được HOÀN TOÀN Ở BACKEND, không phải phát
hành lại extension. ⚠ ĐỪNG đặt lại tên trùng các key cũ (`gpxd_application`/`gpxd_land_document`/
`gpxd_design_dossier`) — làm vậy là lỗi quay lại ngay.

slotIndex là vị trí 0-BASED trong danh sách `input[type=file]` của trang (STT − 1); FE lấy đúng theo
DOM order nên phải giữ khớp với bảng ở trên.

✔ ĐÃ ĐỐI CHIẾU SNAPSHOT THẬT `thongtin/xd/đính kèm xây dựng.html` (dvc.moc.gov.vn): đúng 29 dòng và
đúng 29 `input[type=file]`, KHÔNG có input lạ xen giữa → slotIndex = STT − 1 chuẩn. Text dòng "Đơn"
lặp y hệt ở 4 dòng (1, 6, 12, 17, 23) và "Giấy tờ đất đai" ở 5 dòng (2, 7, 13, 18, 24) — bằng chứng
trực tiếp cho việc keyword theo text KHÔNG THỂ chọn đúng khối. Riêng bản vẽ của nhà ở riêng lẻ là
loại RIÊNG ("Bộ bản vẽ thiết kế xây dựng kèm theo…") và chỉ xuất hiện đúng một lần ở dòng 16.
Cấu trúc 29 dòng được khoá trong `tests/integration/..._attachment_plan.py::_ROW_KINDS`.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold, normalize_document_name
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.cap_giay_phep_xay_dung.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DOC_APPLICATION = "building_permit_application"
_DOC_IDENTITY = "identity_document"
_DOC_SAFETY_COMMITMENT = "safety_commitment"
_DOC_LAND = "land_legal_document"
_DOC_DRAWINGS = "construction_design_drawings"
_DOC_EXPERIENCE = "design_experience_declaration"
_DOC_CAPACITY = "construction_capacity_certificate"
_DOC_ARCHITECT_CERT = "architect_practice_certificate"
_DOC_PROJECT_APPROVAL = "project_approval"
_DOC_REPAIR_APPLICATION = "repair_application"
_DOC_OLD_PERMIT = "old_construction_permit"
_DOC_OTHER = "other"
_DOC_SKIP = "skip"

_ALLOWED_DOC_TYPES = {
    _DOC_APPLICATION,
    _DOC_IDENTITY,
    _DOC_SAFETY_COMMITMENT,
    _DOC_LAND,
    _DOC_DRAWINGS,
    _DOC_EXPERIENCE,
    _DOC_CAPACITY,
    _DOC_ARCHITECT_CERT,
    _DOC_PROJECT_APPROVAL,
    _DOC_REPAIR_APPLICATION,
    _DOC_OLD_PERMIT,
    _DOC_OTHER,
    _DOC_SKIP,
}

# --- Text NGUYÊN VĂN cột "Tên giấy tờ" (rút gọn phần đầu, đủ đặc trưng để cán bộ đọc trace) ---
_C_DON = (
    "Đơn đề nghị cấp giấy phép xây dựng theo Mẫu số 1 Phụ lục số II "
    "Nghị định số 217/2026/NĐ-CP ngày 19/6/2026 của Chính phủ"
)
_C_DAT = (
    "Một trong những giấy tờ hợp pháp về đất đai chứng minh sự phù hợp mục đích sử dụng đất và "
    "sở hữu công trình để cấp phép xây dựng theo quy định tại Điều 55 của Nghị định số 217/2026/NĐ-CP"
)
_C_BANVE_NRL = (
    "Bộ bản vẽ thiết kế xây dựng kèm theo; kết quả thực hiện thủ tục hành chính theo quy định của "
    "pháp luật về phòng cháy, chữa cháy và cứu nạn, cứu hộ (nếu có yêu cầu)"
)
_C_BANVE_DUAN = (
    "Bộ bản vẽ thiết kế xây dựng trong hồ sơ thiết kế xây dựng triển khai sau khi dự án được phê duyệt"
)

_LABEL_DON = "Đơn đề nghị cấp GPXD và giấy tờ kèm theo"
_LABEL_DAT = "Giấy tờ hợp pháp về đất đai"
_LABEL_BANVE = "Hồ sơ thiết kế xây dựng"

# Nhánh loại công trình → 3 dòng của khối đó. componentIndex = STT (1-based) hiển thị trên cổng;
# slotIndex = STT − 1 (0-based, vị trí input[type=file] trong DOM) — thứ FE thực sự dùng.
_NHANH_NHA_O_RIENG_LE = "nha_o_rieng_le"
_NHANH_TIN_NGUONG_TON_GIAO = "tin_nguong_ton_giao"

def _slot(key: str, stt: int, component: str, label: str) -> dict[str, Any]:
    return {
        "slotKey": key,
        "slotIndex": stt - 1,
        "componentIndex": stt,
        "slotName": component,
        "documentName": label,
        "detectedType": label,
    }

# ⚠ slotKey CỐ Ý không trùng FIXED_SLOT_KEYWORDS của extension (xem docstring đầu file).
_SLOTS_BY_NHANH: dict[str, dict[str, dict[str, Any]]] = {
    _NHANH_NHA_O_RIENG_LE: {
        "don": _slot("gpxd_nrl_don", 12, _C_DON, _LABEL_DON),
        "dat": _slot("gpxd_nrl_dat", 13, _C_DAT, _LABEL_DAT),
        "banve": _slot("gpxd_nrl_banve", 16, _C_BANVE_NRL, _LABEL_BANVE),
    },
    _NHANH_TIN_NGUONG_TON_GIAO: {
        "don": _slot("gpxd_tg_don", 6, _C_DON, _LABEL_DON),
        "dat": _slot("gpxd_tg_dat", 7, _C_DAT, _LABEL_DAT),
        "banve": _slot("gpxd_tg_banve", 10, _C_BANVE_DUAN, _LABEL_BANVE),
    },
}

# Nhánh mặc định: cổng đặt quy trình "Cấp giấy phép xây dựng mới đối với nhà ở riêng lẻ" và gần như
# toàn bộ hồ sơ thực tế là nhà ở riêng lẻ của hộ gia đình/cá nhân.
_DEFAULT_NHANH = _NHANH_NHA_O_RIENG_LE

_GROUP_DON = "don"
_GROUP_DAT = "dat"
_GROUP_BANVE = "banve"

_TYPES_BY_GROUP = {
    _GROUP_DON: {_DOC_APPLICATION, _DOC_IDENTITY, _DOC_SAFETY_COMMITMENT},
    _GROUP_DAT: {_DOC_LAND},
    _GROUP_BANVE: {_DOC_DRAWINGS, _DOC_EXPERIENCE, _DOC_CAPACITY, _DOC_ARCHITECT_CERT},
}


def slots_for(nhanh: str) -> dict[str, dict[str, Any]]:
    return _SLOTS_BY_NHANH.get(nhanh or "", _SLOTS_BY_NHANH[_DEFAULT_NHANH])


_LABELS = {
    _DOC_APPLICATION: "Đơn đề nghị cấp giấy phép xây dựng",
    _DOC_IDENTITY: "Căn cước công dân",
    _DOC_SAFETY_COMMITMENT: "Bản cam kết xây nhà",
    _DOC_LAND: "Giấy chứng nhận quyền sử dụng đất",
    _DOC_DRAWINGS: "Bản vẽ xin cấp phép xây dựng",
    _DOC_EXPERIENCE: "Bản kê khai kinh nghiệm thiết kế",
    _DOC_CAPACITY: "Chứng chỉ năng lực hoạt động xây dựng",
    _DOC_ARCHITECT_CERT: "Chứng chỉ hành nghề kiến trúc",
    _DOC_PROJECT_APPROVAL: "Văn bản phê duyệt thẩm định dự án",
    _DOC_REPAIR_APPLICATION: "Đơn đề nghị cấp giấy phép sửa chữa cải tạo",
    _DOC_OLD_PERMIT: "Giấy phép xây dựng cũ",
    _DOC_OTHER: "Tài liệu cấp giấy phép xây dựng",
    _DOC_SKIP: "Bỏ qua",
}

_GROUP_PRIORITY = {
    _DOC_APPLICATION: 10,
    _DOC_IDENTITY: 20,
    _DOC_SAFETY_COMMITMENT: 30,
    _DOC_LAND: 10,
    _DOC_DRAWINGS: 10,
    _DOC_EXPERIENCE: 20,
    _DOC_CAPACITY: 30,
    _DOC_ARCHITECT_CERT: 40,
}


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _has_any(haystack: str, needles: tuple[str, ...]) -> bool:
    return any(needle in haystack for needle in needles)


def _normalize_doc_type(value: str) -> str:
    raw = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    if raw in _ALLOWED_DOC_TYPES:
        return raw
    text = fold(raw)
    if not text or text == "other":
        return _DOC_OTHER
    if _has_any(text, ("building_permit", "cap_giay_phep_xay_dung", "don_de_nghi", "don de nghi")):
        return _DOC_APPLICATION
    if _has_any(text, ("identity", "cccd", "can cuoc", "cmnd", "ho chieu")):
        return _DOC_IDENTITY
    if _has_any(text, ("safety", "commitment", "cam ket", "lien ke")):
        return _DOC_SAFETY_COMMITMENT
    if _has_any(text, ("land", "so do", "qsd", "quyen su dung dat", "dat dai")):
        return _DOC_LAND
    if _has_any(text, ("drawing", "design_drawing", "ban ve", "ho so thiet ke")):
        return _DOC_DRAWINGS
    if _has_any(text, ("experience", "kinh nghiem thiet ke", "ke khai")):
        return _DOC_EXPERIENCE
    if _has_any(text, ("capacity", "chung chi nang luc")):
        return _DOC_CAPACITY
    if _has_any(text, ("practice", "architect", "hanh nghe", "kien truc")):
        return _DOC_ARCHITECT_CERT
    if _has_any(text, ("project", "approval", "phe duyet", "tham dinh")):
        return _DOC_PROJECT_APPROVAL
    if _has_any(text, ("repair", "sua chua", "cai tao")):
        return _DOC_REPAIR_APPLICATION
    if _has_any(text, ("old permit", "giay phep xay dung cu")):
        return _DOC_OLD_PERMIT
    if _has_any(text, ("skip", "irrelevant", "khong ap dung")):
        return _DOC_SKIP
    return _DOC_OTHER


def _label_for_type(doc_type: str, title: str = "") -> str:
    title = normalize_document_name(title, "") if title else ""
    if title and doc_type not in {_DOC_IDENTITY, _DOC_LAND}:
        return title
    return _LABELS.get(doc_type, _LABELS[_DOC_OTHER])


def _normalize_nhanh(value: Any) -> str:
    """Nhánh loại công trình do LLM trả; giá trị lạ → nhánh mặc định (nhà ở riêng lẻ)."""
    text = fold(str(value or "")).replace(" ", "_")
    if text in _SLOTS_BY_NHANH:
        return text
    if _has_any(text, ("ton_giao", "tin_nguong", "chua", "nha_tho", "dinh", "den")):
        return _NHANH_TIN_NGUONG_TON_GIAO
    if _has_any(text, ("nha_o_rieng_le", "nha_o", "rieng_le")):
        return _NHANH_NHA_O_RIENG_LE
    return _DEFAULT_NHANH


async def _classify_with_llm(documents: list[dict[str, Any]]) -> tuple[dict[int, dict[str, str]], str]:
    if not documents:
        return {}, _DEFAULT_NHANH

    docs = [{"index": item["index"], "text": _truncate_text(item.get("text", ""))} for item in documents]
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(docs)},
    ]
    raw = await client.chat(messages, max_tokens=900, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    parsed_docs = parsed.get("documents", []) or []
    nhanh = _normalize_nhanh(parsed.get("congTrinhNhanh") or parsed.get("nhanh"))

    def _coerce(item: dict) -> dict[str, str]:
        return {
            "type": _normalize_doc_type(str(item.get("type") or item.get("docType") or "")),
            "title": str(item.get("title") or item.get("documentName") or "").strip(),
        }

    out: dict[int, dict[str, str]] = {}
    if len(parsed_docs) == len(documents):
        for pos, item in enumerate(parsed_docs):
            out[documents[pos]["index"]] = _coerce(item)
        return out, nhanh

    raw_items: list[tuple[int, dict]] = []
    for item in parsed_docs:
        try:
            raw_items.append((int(item.get("index")), item))
        except Exception:  # noqa: BLE001
            continue
    offset = 0 if any(idx == 0 for idx, _ in raw_items) else 1
    valid = {doc["index"] for doc in documents}
    for raw_idx, item in raw_items:
        idx = raw_idx - offset
        if idx in valid:
            out[idx] = _coerce(item)
    return out, nhanh


def _ordered_entries(entries: list[dict]) -> list[dict]:
    return sorted(entries, key=lambda item: (_GROUP_PRIORITY.get(item["docType"], 99), item["idx"]))


def _group_for_type(doc_type: str) -> str:
    for group, types in _TYPES_BY_GROUP.items():
        if doc_type in types:
            return group
    return ""


def _build_fixed_item(files: list[dict], entry: dict, slot: dict[str, Any]) -> dict:
    idx = entry["idx"]
    document_name = _label_for_type(entry["docType"], entry.get("title", ""))
    return {
        "fileIndex": idx,
        "fileName": str(files[idx].get("name") or f"file-{idx + 1}"),
        "documentName": document_name,
        "componentName": slot["slotName"],
        "target": "fixed-slot",
        "componentIndex": slot["componentIndex"],
        "needsAddComponent": False,
        "detectedType": document_name,
        "slotKey": slot["slotKey"],
        "slotIndex": slot["slotIndex"],
        "slotName": slot["slotName"],
    }


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, dict[str, str]] | None = None,
    nhanh: str = _DEFAULT_NHANH,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    resolved: list[dict] = []
    warnings: list[str] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        # Phân loại HOÀN TOÀN bằng LLM (prompt.py). KHÔNG dùng keyword đoán loại từ OCR: keyword dễ
        # trùng lẫn (vd "Sơ đồ thửa đất" là MỘT MỤC trong SỔ ĐỎ nhưng trùng cụm bản vẽ) và đè SAI kết
        # quả LLM. LLM đọc toàn văn + ngữ cảnh nên phân loại đúng hơn; quy tắc nghiệp vụ đặt ở prompt.
        detected = llm_types.get(idx) or {}
        llm_type = detected.get("type") or ""
        doc_type = llm_type if llm_type in _ALLOWED_DOC_TYPES else _DOC_OTHER
        resolved.append({
            "idx": idx,
            "fileName": file_name,
            "docType": doc_type,
            "title": detected.get("title", ""),
            "source": "llm" if llm_type else "default",
        })

    slots = slots_for(nhanh)
    routed = {group: [] for group in _TYPES_BY_GROUP}
    skipped_entries: list[dict] = []
    for entry in resolved:
        group = _group_for_type(entry["docType"])
        (routed[group] if group else skipped_entries).append(entry)

    attachments: list[dict] = []
    classified: list[dict] = []

    for group in (_GROUP_DON, _GROUP_DAT, _GROUP_BANVE):
        slot = slots[group]
        for entry in _ordered_entries(routed[group]):
            item = _build_fixed_item(files, entry, slot)
            attachments.append(item)
            classified.append({
                "fileName": entry["fileName"],
                "docType": entry["docType"],
                "documentName": item["documentName"],
                "target": "fixed-slot",
                "componentIndex": slot["componentIndex"],
                "slotKey": slot["slotKey"],
                "slotIndex": slot["slotIndex"],
                "source": entry["source"],
            })

    for entry in skipped_entries:
        if entry["docType"] in {_DOC_OTHER, _DOC_SKIP}:
            warnings.append(f"Không xác định được dòng thành phần hồ sơ GPXD cho file '{entry['fileName']}' — đã bỏ qua.")
        else:
            warnings.append(
                f"File '{entry['fileName']}' thuộc nhóm '{entry['docType']}' chưa có dòng tương ứng "
                f"trong khối '{nhanh}' — đã bỏ qua."
            )
        classified.append({
            "fileName": entry["fileName"],
            "docType": entry["docType"],
            "documentName": _label_for_type(entry["docType"], entry.get("title", "")),
            "target": "skip",
            "componentIndex": None,
            "source": entry["source"],
        })

    # Cả 3 dòng đều là "1 Bản chính" BẮT BUỘC. Một tệp quét gộp (vd Đơn + Sổ đỏ chung một file) chỉ
    # được xếp vào MỘT nhóm — theo thứ tự ưu tiên ở prompt thì Đơn thắng — nên nhóm còn lại sẽ trống.
    # Cảnh báo để cán bộ tự bù hoặc đề nghị người dân tách tệp, thay vì im lặng nộp thiếu thành phần.
    for group, label in ((_GROUP_DON, _LABEL_DON), (_GROUP_DAT, _LABEL_DAT), (_GROUP_BANVE, _LABEL_BANVE)):
        if not routed[group]:
            warnings.append(
                f"Chưa có tệp nào cho dòng '{label}' (STT {slots[group]['componentIndex']}). Mỗi tệp chỉ "
                "xếp được vào một dòng — nếu tệp đã nộp quét gộp cả giấy tờ của dòng này thì cán bộ đính "
                "thêm thủ công, hoặc đề nghị người dân tách tệp."
            )

    return attachments, warnings, classified


async def plan(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    _ = options or {}
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [file for file in raw_files if file.get("type") in _OCR_TYPES]

    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    ocr_by_name = {item.get("name"): item for item in ocr_results}
    llm_docs = [
        {
            "index": idx,
            "text": str(ocr_by_name.get(file.get("name"), {}).get("text") or ""),
        }
        for idx, file in enumerate(raw_files)
    ]

    t1 = time.monotonic()
    llm_types: dict[int, dict[str, str]] = {}
    nhanh = _DEFAULT_NHANH
    if llm_docs:
        try:
            llm_types, nhanh = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types, nhanh)
    errors.extend(warnings)
    skipped_ocr = [file["name"] for file in raw_files if file.get("type") not in _OCR_TYPES]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [file["name"] for file in raw_files],
            "ocrDocuments": [item.get("name") for item in ocr_results if item.get("text")],
            "llmDocuments": [file["name"] for file in raw_files],
            "sessionId": (session or {}).get("request_id"),
            "classified": classified,
            "skippedOcr": skipped_ocr,
            "congTrinhNhanh": nhanh,
            "slots": list(slots_for(nhanh).values()),
        },
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "ocr_text": join_ocr_documents(ocr_results),
        "llm_output": {str(idx): val for idx, val in llm_types.items()},
        "errors": errors,
    }

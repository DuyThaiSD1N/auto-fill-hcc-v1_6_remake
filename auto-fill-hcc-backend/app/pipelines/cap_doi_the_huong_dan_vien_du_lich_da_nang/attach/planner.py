"""Đính kèm [Đà Nẵng · Bộ VHTTDL] Thủ tục cấp đổi thẻ hướng dẫn viên du lịch quốc tế, nội địa (1.001432, QT-113).

Cổng `dichvucong.bvhttdl.gov.vn` — form và bảng thành phần hồ sơ NẰM CHUNG trang. Bảng có 4 dòng, mỗi
dòng một `<app-upload-flie-multi>` chứa input file (multiple) → engine FE `fixed-slot` (slotIndex = thứ
tự input file trên trang):

  0 : (1) Bản sao có chứng thực GCN đã qua khóa cập nhật kiến thức cho HDV du lịch   — Bản sao 1
  1 : (2) Thẻ hướng dẫn viên du lịch đã được cấp                                     — Bản chính 1
  2 : (3) Đơn đề nghị cấp đổi thẻ hướng dẫn viên du lịch (Mẫu số 05)                 — Bản chính 1
  3 : (4) 01 ảnh chân dung màu 3cm x 4cm hoặc bản điện tử ảnh màu                    — Bản chính 1

⚑ Hồ sơ hay nộp NHẦM bộ cấp mới (Đơn Mẫu 04 + chứng chỉ nghiệp vụ + văn bằng). Không bỏ tệp nào:
  - Đơn cấp mới vẫn lên dòng (3) Đơn, kèm cảnh báo SAI MẪU (Mẫu 04/06 ≠ Mẫu 05).
  - Chứng chỉ nghiệp vụ / văn bằng lên CHUNG dòng (1) (giấy tờ trình độ gần nhất), kèm cảnh báo THAY THẾ
    — không đúng loại GCN khóa cập nhật kiến thức.
  - Giấy tờ lạ (CCCD…) lên dòng (3) Đơn, giữ tên tệp.
Dòng nhận nhiều tệp hoặc tệp thay thế → planner trả sẵn nội dung ô "Mô tả" của dòng đó trong cảnh báo
(engine chưa điền được modal Mô tả). Các tệp cùng dòng dùng chung `slotKey` → engine gom vào một lần gán
input `multiple`.

⚑ ẢNH CHÂN DUNG không có chữ nên OCR rỗng → nhận tất định (tệp ảnh/PDF gần như không có chữ), không
chờ LLM. Ảnh in trên thẻ/chứng chỉ KHÔNG thay được ảnh 3x4 riêng. Phân loại THUẦN LLM cho tệp có chữ.
"""

import asyncio
import time
from typing import Any

from app.config import settings
from app.pipelines.cap_the_huong_dan_vien_du_lich_noi_dia.attach.planner import _canon, _looks_like_photo
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_BAN_CHINH = "Bản chính"
_BAN_SAO = "Bản sao"

_T_DON_DOI = "don_cap_doi"
_T_DON_MOI = "don_cap_moi"
_T_THE = "the_hdv"
_T_GCN = "gcn_cap_nhat_kien_thuc"
_T_CHUNG_CHI = "chung_chi_nghiep_vu"
_T_VAN_BANG = "van_bang"
_T_ANH = "anh_chan_dung"
_T_OTHER = "other"

_SLOT_GCN, _SLOT_THE, _SLOT_DON, _SLOT_ANH = 0, 1, 2, 3

# Tên dòng theo nhãn chuẩn hoá của bản mapping (DOM gốc bị Google Dịch) — chỉ để hiển thị, FE đi theo slotIndex.
_SLOT_NAMES = {
    _SLOT_GCN: "Bản sao có chứng thực giấy chứng nhận đã qua khóa cập nhật kiến thức cho hướng dẫn viên du "
               "lịch do Sở Du lịch/Sở Văn hóa, Thể thao và Du lịch cấp",
    _SLOT_THE: "Thẻ hướng dẫn viên du lịch đã được cấp",
    _SLOT_DON: "Đơn đề nghị cấp đổi thẻ hướng dẫn viên du lịch (theo Mẫu số 05 tại Phụ lục II Thông tư số "
               "04/2024/TT-BVHTTDL)",
    _SLOT_ANH: "01 ảnh chân dung màu 3cm x 4cm hoặc bản điện tử ảnh màu (trong trường hợp hồ sơ trực tuyến)",
}
_LOAI_BAN = {_SLOT_GCN: _BAN_SAO, _SLOT_THE: _BAN_CHINH, _SLOT_DON: _BAN_CHINH, _SLOT_ANH: _BAN_CHINH}
# slotKey theo DÒNG (không theo loại giấy tờ): tệp đính kèm chung phải chung key để engine gom vào một lần
# gán input. Cố ý không trùng FIXED_SLOT_KEYWORDS của extension để FE đi thẳng theo slotIndex.
_SLOT_KEYS = {
    _SLOT_GCN: "hdvcd_gcn_cap_nhat",
    _SLOT_THE: "hdvcd_the_da_cap",
    _SLOT_DON: "hdvcd_don_de_nghi",
    _SLOT_ANH: "hdvcd_anh_chan_dung",
}

_ROUTES: dict[str, int] = {
    _T_GCN: _SLOT_GCN,
    _T_CHUNG_CHI: _SLOT_GCN,   # thay thế — không đúng loại GCN
    _T_VAN_BANG: _SLOT_GCN,    # thay thế — không đúng loại GCN
    _T_THE: _SLOT_THE,
    _T_DON_DOI: _SLOT_DON,
    _T_DON_MOI: _SLOT_DON,     # sai mẫu — Mẫu 04/06 ≠ Mẫu 05
    _T_ANH: _SLOT_ANH,
}
# Loại giấy tờ ĐÚNG của từng dòng; tệp khác lên dòng đó là thay thế → phải ghi Mô tả.
_NATIVE = {_SLOT_GCN: _T_GCN, _SLOT_THE: _T_THE, _SLOT_DON: _T_DON_DOI, _SLOT_ANH: _T_ANH}
_DISPLAY = {
    _T_DON_DOI: "Đơn đề nghị cấp đổi thẻ hướng dẫn viên du lịch (Mẫu số 05)",
    _T_DON_MOI: "Đơn đề nghị cấp thẻ hướng dẫn viên du lịch (cấp mới — Mẫu số 04/06)",
    _T_THE: "Thẻ hướng dẫn viên du lịch đã được cấp",
    _T_GCN: "Giấy chứng nhận đã qua khóa cập nhật kiến thức cho hướng dẫn viên du lịch",
    _T_CHUNG_CHI: "Chứng chỉ nghiệp vụ hướng dẫn du lịch",
    _T_VAN_BANG: "Bằng tốt nghiệp",
    _T_ANH: "Ảnh chân dung màu 3cm x 4cm",
}
_ALLOWED = set(_ROUTES) | {_T_OTHER}

# Thứ tự chọn loại cho tệp gộp: giấy tờ của dòng còn trống trước, loại thay thế sau, ảnh sau cùng.
_ROW_PRIORITY = (_T_DON_DOI, _T_THE, _T_GCN, _T_DON_MOI, _T_CHUNG_CHI, _T_VAN_BANG, _T_ANH)


def _normalize_doc_type(value: Any) -> str:
    canon = _canon(value)
    for doc_type in _ALLOWED:
        if canon == _canon(doc_type):
            return doc_type
    return _T_OTHER


def _normalize_also(values: Any, primary: str) -> list[str]:
    """Loại giấy tờ KHÁC cùng nằm trong một tệp gộp — chỉ dùng để ghi Mô tả và chọn dòng."""
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for value in values:
        doc_type = _normalize_doc_type(value)
        if doc_type not in (_T_OTHER, primary) and doc_type not in out:
            out.append(doc_type)
    return out


async def _classify_one(document: dict[str, Any]) -> tuple[int, str, list[str]]:
    index = int(document.get("index"))
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(
            [{"index": index, "text": str(document.get("text") or "")[:14000]}]
        )},
    ]
    raw = await client.chat(messages, max_tokens=180, enable_thinking=settings.agent_reasoning)
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


def _item(index: int, file_name: str, slot_index: int, document_name: str, doc_type: str) -> dict:
    return {
        "fileIndex": index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": _SLOT_NAMES[slot_index],
        "loaiBan": _LOAI_BAN[slot_index],
        "target": "fixed-slot",
        "needsAddComponent": False,
        "slotKey": _SLOT_KEYS[slot_index],
        "slotIndex": slot_index,
        "slotName": _SLOT_NAMES[slot_index],
        "detectedType": doc_type,
    }


def _mo_ta(files_on_row: list[tuple[str, str, list[str]]], thay_the: bool) -> str:
    """Nội dung gợi ý cho ô "Mô tả" của một dòng nhận nhiều tệp hoặc tệp thay thế."""
    parts = []
    for n, (file_name, doc_type, also) in enumerate(files_on_row, start=1):
        loai = " + ".join(_DISPLAY.get(t, "") for t in (doc_type, *also) if t in _DISPLAY) or "Giấy tờ khác"
        parts.append(f"({n}) {loai} — tệp {file_name}")
    ly_do = (
        "hồ sơ chưa có giấy tờ đúng loại của dòng này, đính kèm tạm giấy tờ gần nhất để cán bộ xem xét"
        if thay_the else
        "danh mục thành phần hồ sơ trực tuyến không có dòng riêng cho các giấy tờ này"
    )
    so_tep = f"Đính kèm chung {len(files_on_row)} tệp" if len(files_on_row) > 1 else "Đính kèm 1 tệp"
    return f"{so_tep}: " + "; ".join(parts) + f". Lý do: {ly_do}."


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, tuple[str, list[str]] | str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    """`llm_types[index]` = (docType, alsoTypes). Tệp ảnh chân dung đã được planner gán sẵn `anh_chan_dung`."""
    llm_types = llm_types or {}

    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    tren_dong: dict[int, list[tuple[str, str, list[str]]]] = {s: [] for s in _SLOT_NAMES}
    chon_tren_dong: dict[int, list[str | None]] = {s: [] for s in _SLOT_NAMES}
    co_trong_ho_so: set[str] = set()

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        raw = llm_types.get(index)
        doc_type, also = raw if isinstance(raw, tuple) else (raw, [])
        if doc_type not in _ALLOWED:
            doc_type = _T_OTHER
        also = _normalize_also(also, doc_type) if doc_type != _T_OTHER else []
        source = "llm" if index in llm_types else "default"

        if doc_type == _T_OTHER:
            chon, slot, document_name = None, _SLOT_DON, file_name
        else:
            loai_trong_tep = (doc_type, *also)
            chua_co = [t for t in _ROW_PRIORITY if t in loai_trong_tep and t not in co_trong_ho_so]
            chon = chua_co[0] if chua_co else doc_type
            slot, document_name = _ROUTES[chon], _DISPLAY[chon]
            co_trong_ho_so.update(loai_trong_tep)

        attachments.append(_item(index, file_name, slot, document_name, chon or doc_type))
        tren_dong[slot].append((file_name, doc_type, also))
        chon_tren_dong[slot].append(chon)
        classified.append({
            "fileName": file_name, "docType": doc_type, "alsoTypes": also,
            "assignedType": chon, "source": source, "slotIndex": slot,
        })

    # ---- Dòng (3) Đơn ----
    so_don = sum(1 for c in chon_tren_dong[_SLOT_DON] if c in (_T_DON_DOI, _T_DON_MOI))
    if _T_DON_DOI in co_trong_ho_so:
        if so_don > 1:
            warnings.append(
                f"Có {so_don} tệp cùng nhận là Đơn đề nghị — kiểm tra lại, dòng (3) chỉ cần 01 bản chính."
            )
    elif _T_DON_MOI in co_trong_ho_so:
        warnings.append(
            "SAI MẪU ĐƠN: hồ sơ chỉ có đơn đề nghị CẤP MỚI thẻ (Mẫu số 04/06), không phải Đơn đề nghị cấp đổi "
            "thẻ theo Mẫu số 05 (tải mẫu bằng nút ở cột 'Xem mẫu đơn'). Đã đính tạm vào dòng (3); cần lập lại "
            "Đơn Mẫu 05, bổ sung số thẻ, nơi cấp, ngày cấp, loại thẻ đã được cấp và lý do đề nghị cấp đổi."
        )
    else:
        warnings.append(
            "Chưa thấy ĐƠN ĐỀ NGHỊ CẤP ĐỔI thẻ hướng dẫn viên du lịch (Mẫu số 05) — thành phần bắt buộc (3), "
            "cán bộ bổ sung trước khi nộp."
        )

    # ---- Dòng (2) Thẻ HDV đã được cấp ----
    if _T_THE not in co_trong_ho_so:
        warnings.append(
            "Chưa có tệp THẺ HƯỚNG DẪN VIÊN DU LỊCH ĐÃ ĐƯỢC CẤP — thành phần bắt buộc (2), cần bản chính thẻ "
            "đang có. Không dùng chứng chỉ nghiệp vụ thay thế; số hiệu chứng chỉ không phải số thẻ."
        )

    # ---- Dòng (1) GCN khóa cập nhật kiến thức ----
    if _T_GCN not in co_trong_ho_so:
        thay = [t for t in (_T_CHUNG_CHI, _T_VAN_BANG) if t in co_trong_ho_so]
        if thay:
            warnings.append(
                "Dòng (1) đang nhận " + " và ".join(_DISPLAY[t].lower() for t in thay) + " THAY THẾ — không "
                "đúng loại. Thủ tục cấp đổi yêu cầu bản sao có chứng thực GIẤY CHỨNG NHẬN ĐÃ QUA KHÓA CẬP NHẬT "
                "KIẾN THỨC cho hướng dẫn viên du lịch do Sở cấp; cán bộ bổ sung giấy này."
            )
        else:
            warnings.append(
                "Chưa thấy bản sao có chứng thực GIẤY CHỨNG NHẬN ĐÃ QUA KHÓA CẬP NHẬT KIẾN THỨC cho hướng dẫn "
                "viên du lịch — thành phần bắt buộc (1), cán bộ bổ sung trước khi nộp."
            )

    # ---- Dòng (4) Ảnh ----
    if not tren_dong[_SLOT_ANH]:
        warnings.append(
            "Chưa thấy ẢNH CHÂN DUNG màu 3cm x 4cm — thành phần bắt buộc (4). Ảnh in trên thẻ/chứng chỉ/CCCD "
            "không thay được; tải ảnh riêng (jpg/png hoặc PDF một trang chỉ có ảnh) rồi đính lại."
        )

    # ---- Mô tả cho dòng nhận nhiều tệp, tệp thay thế hoặc tệp scan gộp ----
    for slot, files_on_row in tren_dong.items():
        if not files_on_row or slot == _SLOT_ANH:
            continue
        native = _NATIVE[slot]
        thay_the = native not in chon_tren_dong[slot]
        gop = any(also for _n, _t, also in files_on_row)
        if len(files_on_row) > 1 or thay_the or gop:
            warnings.append(
                f"Dòng ({slot + 1}) {_SLOT_NAMES[slot].split(' (')[0]} — cán bộ bấm nút Mô tả của dòng này và "
                f"ghi: \"{_mo_ta(files_on_row, thay_the)}\""
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
    llm_types: dict[int, tuple[str, list[str]]] = {}
    llm_documents: list[dict[str, Any]] = []
    for index, file in enumerate(raw_files):
        entry = by_name.get(file.get("name"), {})
        text = str(entry.get("text") or "")
        # Ảnh chân dung không có chữ → nhận tất định. Tệp OCR lỗi thì KHÔNG coi là ảnh (có thể là đơn).
        if not entry.get("error") and file.get("type") in _OCR_TYPES and _looks_like_photo(file, text):
            llm_types[index] = (_T_ANH, [])
        elif text.strip():
            llm_documents.append({"index": index, "text": text})

    started = time.monotonic()
    if llm_documents:
        try:
            llm_types.update(await _classify_with_llm(llm_documents, errors))
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

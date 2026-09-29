"""Đính kèm [Đà Nẵng · Bộ VHTTDL] Thủ tục cấp lại thẻ hướng dẫn viên du lịch (1.004614, QT-122).

Cổng `dichvucong.bvhttdl.gov.vn` — form và bảng thành phần hồ sơ NẰM CHUNG trang. Bảng có 3 dòng, mỗi
dòng một `<app-upload-flie-multi>` chứa input file (multiple) → engine FE `fixed-slot` (slotIndex = thứ
tự input file trên trang):

  0 : Bản sao có chứng thực giấy tờ liên quan đến nội dung thay đổi (cấp lại để thay đổi thông tin) — Bản sao 1
  1 : (1) Đơn đề nghị cấp lại thẻ hướng dẫn viên du lịch (Mẫu số 05)                              — Bản chính 1
  2 : (3) 01 ảnh chân dung màu 3cm x 4cm hoặc bản điện tử ảnh màu                                 — Bản chính 1

Dòng 0 là ô DUY NHẤT nhận bản sao giấy tờ kèm theo → chứng chỉ nghiệp vụ, văn bằng, thẻ HDV cũ, GCN cập
nhật kiến thức và giấy tờ lạ đều đính CHUNG vào đây (không bỏ sót tệp), kèm nội dung ô "Mô tả" trong cảnh
báo (engine chưa điền được modal Mô tả). CCCD KHÔNG có dòng: chỉ dùng nhập eform, không đính.

⚑ Hồ sơ hay nộp NHẦM bộ cấp mới gộp trong MỘT PDF (Đơn Mẫu 04 tr.1–2 + chứng chỉ nghiệp vụ tr.3–4 + văn
bằng tr.5). OCR có header "Trang i/N" → phân loại TỪNG TRANG rồi gom các trang liền nhau cùng dòng thành một
đoạn `sourceSegments` (FE tự tách PDF con): tr.1–2 → dòng Đơn (cảnh báo SAI MẪU), tr.3–5 → dòng 0. Trang
trống / trang "Hướng dẫn ghi" in sau đơn không gọi LLM, đi theo trang liền trước. Tệp một trang hoặc OCR
không có header trang → phân loại nguyên tệp như cấp đổi (docType + alsoTypes cho bản scan gộp).

⚑ ẢNH CHÂN DUNG không có chữ nên OCR rỗng → nhận tất định (tệp ảnh/PDF một trang gần như không có chữ),
không chờ LLM. Ảnh in trên chứng chỉ/thẻ KHÔNG thay được ảnh 3x4 riêng.
"""

import asyncio
import re
import time
from typing import Any

from app.config import settings
from app.pipelines.cap_the_huong_dan_vien_du_lich_noi_dia.attach.planner import (
    _PHOTO_MAX_TEXT_CHARS,
    _canon,
    _looks_like_photo,
)
from app.pipelines.cap_the_huong_dan_vien_du_lich_noi_dia.process.mapper import _fold
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_BAN_CHINH = "Bản chính"
_BAN_SAO = "Bản sao"
# Header phân trang do OCR Tiếng Nói chèn: "Trang 2/5" (có thể kẹp giữa các gạch ngang).
_PAGE_HEADER_RE = re.compile(r"(?im)^[\s─-╿-]*(?:trang|page)\s+(\d+)\s*/\s*(\d+)[\s─-╿-]*$")

_T_DON_LAI = "don_cap_lai"
_T_DON_MOI = "don_cap_moi"
_T_THAY_DOI = "giay_to_thay_doi"
_T_THE = "the_hdv"
_T_CHUNG_CHI = "chung_chi_nghiep_vu"
_T_VAN_BANG = "van_bang"
_T_GCN = "gcn_cap_nhat_kien_thuc"
_T_CCCD = "cccd"
_T_ANH = "anh_chan_dung"
_T_OTHER = "other"

_SLOT_GIAY_TO, _SLOT_DON, _SLOT_ANH = 0, 1, 2

# Tên dòng theo nhãn trên cổng — chỉ để hiển thị, FE đi theo slotIndex.
_SLOT_NAMES = {
    _SLOT_GIAY_TO: "Bản sao có chứng thực giấy tờ liên quan đến nội dung thay đổi trong trường hợp cấp lại thẻ "
                   "để thay đổi thông tin trên thẻ hướng dẫn du lịch",
    _SLOT_DON: "(1) Đơn đề nghị cấp lại thẻ hướng dẫn viên du lịch (theo Mẫu số 05 tại Phụ lục II ban hành kèm "
               "theo Thông tư 04/2024/TT-BVHTTDL ngày 26 tháng 6 năm 2024)",
    _SLOT_ANH: "(3) 01 ảnh chân dung màu 3cm x 4cm hoặc bản điện tử ảnh màu (trong trường hợp hồ sơ trực tuyến)",
}
_SLOT_SHORT = {
    _SLOT_GIAY_TO: "Bản sao giấy tờ liên quan đến nội dung thay đổi",
    _SLOT_DON: "Đơn đề nghị cấp lại thẻ (Mẫu số 05)",
    _SLOT_ANH: "Ảnh chân dung màu 3cm x 4cm",
}
_LOAI_BAN = {_SLOT_GIAY_TO: _BAN_SAO, _SLOT_DON: _BAN_CHINH, _SLOT_ANH: _BAN_CHINH}
# slotKey theo DÒNG (không theo loại giấy tờ): tệp đính kèm chung phải chung key để engine gom vào một lần
# gán input. Cố ý không trùng FIXED_SLOT_KEYWORDS của extension để FE đi thẳng theo slotIndex.
_SLOT_KEYS = {
    _SLOT_GIAY_TO: "hdvcl_giay_to_thay_doi",
    _SLOT_DON: "hdvcl_don_de_nghi",
    _SLOT_ANH: "hdvcl_anh_chan_dung",
}

_ROUTES: dict[str, int] = {
    _T_THAY_DOI: _SLOT_GIAY_TO,
    _T_CHUNG_CHI: _SLOT_GIAY_TO,  # đính kèm chung — ô duy nhất nhận bản sao giấy tờ kèm theo
    _T_VAN_BANG: _SLOT_GIAY_TO,
    _T_THE: _SLOT_GIAY_TO,
    _T_GCN: _SLOT_GIAY_TO,
    _T_DON_LAI: _SLOT_DON,
    _T_DON_MOI: _SLOT_DON,        # sai mẫu — Mẫu 04/06 ≠ Mẫu 05
    _T_ANH: _SLOT_ANH,
}
# Loại giấy tờ ĐÚNG của từng dòng; tệp khác lên dòng đó là đính kèm chung/thay thế → phải ghi Mô tả.
_NATIVE = {_SLOT_GIAY_TO: _T_THAY_DOI, _SLOT_DON: _T_DON_LAI, _SLOT_ANH: _T_ANH}
_DISPLAY = {
    _T_DON_LAI: "Đơn đề nghị cấp lại thẻ hướng dẫn viên du lịch (Mẫu số 05)",
    _T_DON_MOI: "Đơn đề nghị cấp thẻ hướng dẫn viên du lịch (cấp mới — Mẫu số 04/06)",
    _T_THAY_DOI: "Giấy tờ liên quan đến nội dung thay đổi",
    _T_THE: "Thẻ hướng dẫn viên du lịch đã được cấp",
    _T_CHUNG_CHI: "Chứng chỉ nghiệp vụ hướng dẫn du lịch",
    _T_VAN_BANG: "Bằng tốt nghiệp",
    _T_GCN: "Giấy chứng nhận đã qua khóa cập nhật kiến thức cho hướng dẫn viên du lịch",
    _T_ANH: "Ảnh chân dung màu 3cm x 4cm",
}
_ALLOWED = set(_ROUTES) | {_T_CCCD, _T_OTHER}

# Thứ tự chọn loại cho tệp gộp: giấy tờ của dòng còn trống trước, loại thay thế sau, ảnh sau cùng.
_ROW_PRIORITY = (_T_DON_LAI, _T_THAY_DOI, _T_DON_MOI, _T_CHUNG_CHI, _T_VAN_BANG, _T_THE, _T_GCN, _T_ANH)


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


def _split_pages(text: str) -> list[str] | None:
    """Text OCR → text từng trang theo header "Trang i/N"; None khi không có header (không tách được)."""
    value = str(text or "")
    matches = list(_PAGE_HEADER_RE.finditer(value))
    if not matches:
        return None
    total = max(max(int(m.group(1)), int(m.group(2))) for m in matches)
    pages: dict[int, str] = {}
    for pos, m in enumerate(matches):
        end = matches[pos + 1].start() if pos + 1 < len(matches) else len(value)
        pages[int(m.group(1))] = value[m.end():end].strip()
    return [pages.get(p, "") for p in range(1, total + 1)]


def _page_follows_previous(text: str) -> bool:
    """Trang trống (mặt sau, ảnh mờ) hoặc trang "Hướng dẫn ghi" in sau đơn → đi theo trang liền trước."""
    if len(re.sub(r"[\W_]+", "", text or "")) < _PHOTO_MAX_TEXT_CHARS:
        return True
    folded = _fold(text)
    return "huong dan ghi" in folded and "kinh gui" not in folded


async def _classify_one(index: Any, text: str) -> tuple[Any, str, list[str]]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt([{"index": 0, "text": str(text or "")[:14000]}])},
    ]
    raw = await client.chat(messages, max_tokens=180, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    first = next(iter(parsed.get("documents", []) or []), {})
    doc_type = _normalize_doc_type(first.get("docType") or first.get("type"))
    return index, doc_type, _normalize_also(first.get("alsoTypes"), doc_type)


async def _classify_with_llm(
    units: list[tuple[Any, str]],
    errors: list[str] | None = None,
) -> dict[Any, tuple[str, list[str]]]:
    """`units` = [(khoá, text)] — khoá là fileIndex (nguyên tệp) hoặc (fileIndex, số trang)."""
    if not units:
        return {}
    outcomes = await asyncio.gather(*(_classify_one(k, t) for k, t in units), return_exceptions=True)
    result: dict[Any, tuple[str, list[str]]] = {}
    for (key, _text), outcome in zip(units, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            if errors is not None:
                errors.append(f"attachment_agent {key}: {outcome}")
            continue
        _key, doc_type, also = outcome
        result[key] = (doc_type, also)
    return result


def _resolve_pages(page_types: list[str | None]) -> list[str]:
    """Trang chưa có loại (trống / Hướng dẫn ghi / LLM lỗi) lấy loại trang liền trước, trang đầu lấy trang sau."""
    resolved = list(page_types)
    for i in range(1, len(resolved)):
        if resolved[i] is None:
            resolved[i] = resolved[i - 1]
    for i in range(len(resolved) - 2, -1, -1):
        if resolved[i] is None:
            resolved[i] = resolved[i + 1]
    return [t if t in _ALLOWED else _T_OTHER for t in resolved]


def _slot_of(doc_type: str) -> int | None:
    if doc_type == _T_CCCD:
        return None
    return _ROUTES.get(doc_type, _SLOT_GIAY_TO)


def _page_label(pages: list[int]) -> str:
    return f"trang {pages[0]}" if len(pages) == 1 else f"trang {pages[0]}–{pages[-1]}"


def _item(index: int, file_name: str, slot_index: int, document_name: str, doc_type: str,
          pages: list[int] | None) -> dict:
    item = {
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
    if pages is not None:  # đoạn con của PDF gộp → FE tách đúng các trang này thành PDF riêng.
        item["sourceSegments"] = [{"fileIndex": index, "pageIndexes": [p - 1 for p in pages]}]
    return item


def _mo_ta(pieces_on_row: list[tuple[str, list[str]]], thay_the: bool) -> str:
    """Nội dung gợi ý cho ô "Mô tả" của một dòng nhận nhiều tệp hoặc tệp không đúng loại của dòng."""
    parts = []
    for n, (label, types) in enumerate(pieces_on_row, start=1):
        loai = " + ".join(_DISPLAY[t] for t in types if t in _DISPLAY) or "Giấy tờ khác"
        parts.append(f"({n}) {loai} — {label}")
    ly_do = (
        "hồ sơ không có giấy tờ đúng loại của dòng này, đây là ô duy nhất nhận bản sao giấy tờ kèm theo nên "
        "đính kèm chung để cán bộ xem xét"
        if thay_the else
        "danh mục thành phần hồ sơ trực tuyến không có dòng riêng cho các giấy tờ này"
    )
    so_tep = f"Đính kèm chung {len(pieces_on_row)} tệp" if len(pieces_on_row) > 1 else "Đính kèm 1 tệp"
    return f"{so_tep}: " + "; ".join(parts) + f". Lý do: {ly_do}."


def _pieces(
    files: list[dict],
    llm_types: dict[int, tuple[str, list[str]] | str],
    page_types: dict[int, list[str | None]],
) -> list[dict]:
    """Mỗi phần = một tệp nguyên (pages=None) hoặc một dải trang liền nhau cùng dòng của PDF gộp."""
    pieces: list[dict] = []
    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        if index in page_types and len(page_types[index]) > 1:
            resolved = _resolve_pages(page_types[index])
            source = "llm" if any(t is not None for t in page_types[index]) else "default"
            groups: list[dict] = []
            for page_no, doc_type in enumerate(resolved, start=1):
                slot = _slot_of(doc_type)
                if groups and groups[-1]["slot"] == slot:
                    groups[-1]["pages"].append(page_no)
                    if doc_type not in groups[-1]["types"]:
                        groups[-1]["types"].append(doc_type)
                else:
                    groups.append({"slot": slot, "pages": [page_no], "types": [doc_type]})
            whole = len(groups) == 1
            for group in groups:
                pages = None if whole else group["pages"]
                label = f"tệp {file_name}" + ("" if whole else f" {_page_label(group['pages'])}")
                pieces.append({"index": index, "fileName": file_name, "pages": pages, "label": label,
                               "types": group["types"], "source": source})
            continue
        raw = llm_types.get(index)
        doc_type, also = raw if isinstance(raw, tuple) else (raw, [])
        if doc_type not in _ALLOWED:
            doc_type = _T_OTHER
        also = _normalize_also(also, doc_type) if doc_type != _T_OTHER else []
        pieces.append({"index": index, "fileName": file_name, "pages": None, "label": f"tệp {file_name}",
                       "types": [doc_type, *also], "source": "llm" if index in llm_types else "default"})
    return pieces


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, tuple[str, list[str]] | str] | None = None,
    page_types: dict[int, list[str | None]] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    """`llm_types[fileIndex]` = (docType, alsoTypes) khi phân loại nguyên tệp; `page_types[fileIndex]` = loại
    từng trang (None = đi theo trang liền trước) khi tách được trang. Ảnh chân dung đã gán sẵn `anh_chan_dung`."""
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    tren_dong: dict[int, list[tuple[str, list[str]]]] = {s: [] for s in _SLOT_NAMES}
    chon_tren_dong: dict[int, list[str | None]] = {s: [] for s in _SLOT_NAMES}
    co_trong_ho_so: set[str] = set()
    cccd_bo_qua: list[str] = []

    for piece in _pieces(files, llm_types or {}, page_types or {}):
        types = piece["types"]
        routable = [t for t in types if t in _ROUTES]
        base = {"fileName": piece["fileName"], "pages": piece["pages"], "docType": types[0],
                "alsoTypes": types[1:], "source": piece["source"]}
        if not routable and _T_CCCD in types:
            cccd_bo_qua.append(piece["label"])
            co_trong_ho_so.add(_T_CCCD)
            classified.append({**base, "assignedType": _T_CCCD, "slotIndex": None, "target": "skip"})
            continue
        if not routable:
            chon, slot = None, _SLOT_GIAY_TO
            document_name = piece["fileName"] if piece["pages"] is None else (
                f"{piece['fileName']} ({_page_label(piece['pages'])})"
            )
        else:
            chua_co = [t for t in _ROW_PRIORITY if t in routable and t not in co_trong_ho_so]
            chon = chua_co[0] if chua_co else routable[0]
            slot = _ROUTES[chon]
            cung_dong = [t for t in _ROW_PRIORITY if t in routable and _ROUTES[t] == slot]
            document_name = " + ".join(_DISPLAY[t] for t in cung_dong)
            co_trong_ho_so.update(routable)

        attachments.append(_item(piece["index"], piece["fileName"], slot, document_name, chon or types[0],
                                 piece["pages"]))
        tren_dong[slot].append((piece["label"], types))
        chon_tren_dong[slot].append(chon)
        classified.append({**base, "assignedType": chon, "slotIndex": slot})

    # ---- Dòng 2: Đơn ----
    so_don = sum(1 for c in chon_tren_dong[_SLOT_DON] if c in (_T_DON_LAI, _T_DON_MOI))
    if _T_DON_LAI in co_trong_ho_so:
        if so_don > 1:
            warnings.append(
                f"Có {so_don} tệp cùng nhận là Đơn đề nghị — kiểm tra lại, dòng Đơn chỉ cần 01 bản chính."
            )
    elif _T_DON_MOI in co_trong_ho_so:
        warnings.append(
            "SAI MẪU ĐƠN: hồ sơ chỉ có đơn đề nghị CẤP MỚI thẻ (Mẫu số 04/06), không phải Đơn đề nghị cấp lại "
            "thẻ theo Mẫu số 05 (mở mẫu bằng nút 'Xem tờ khai' của dòng Đơn). Đã đính tạm vào dòng 2; cần lập "
            "lại Đơn Mẫu 05, bổ sung số thẻ, nơi cấp, ngày cấp, loại thẻ đã được cấp và lý do đề nghị cấp lại."
        )
    else:
        warnings.append(
            "Chưa thấy ĐƠN ĐỀ NGHỊ CẤP LẠI thẻ hướng dẫn viên du lịch (Mẫu số 05) — thành phần bắt buộc, cán "
            "bộ bổ sung trước khi nộp."
        )

    # ---- Dòng 3: Ảnh ----
    if not tren_dong[_SLOT_ANH]:
        warnings.append(
            "Chưa thấy ẢNH CHÂN DUNG màu 3cm x 4cm — thành phần bắt buộc. Ảnh dán trên chứng chỉ/thẻ/CCCD "
            "không thay được; yêu cầu người đề nghị cung cấp ảnh màu 3x4 (jpg/png hoặc PDF một trang chỉ có "
            "ảnh) rồi đính lại."
        )

    # ---- CCCD: không có dòng trong bảng ----
    if cccd_bo_qua:
        warnings.append(
            "Không đính kèm CCCD (" + "; ".join(cccd_bo_qua) + ") — bảng thành phần hồ sơ không có dòng CCCD, "
            "chỉ dùng để nhập eform. Nếu cấp lại để thay đổi thông tin trên thẻ (vd đổi số định danh) thì cán "
            "bộ tự đính CCCD vào dòng 1 (giấy tờ liên quan đến nội dung thay đổi)."
        )

    # ---- Mô tả cho dòng nhận nhiều tệp, tệp không đúng loại hoặc tệp scan gộp ----
    for slot, pieces_on_row in tren_dong.items():
        if not pieces_on_row or slot == _SLOT_ANH:
            continue
        thay_the = _NATIVE[slot] not in chon_tren_dong[slot]
        gop = any(len(types) > 1 for _label, types in pieces_on_row)
        if len(pieces_on_row) > 1 or thay_the or gop:
            if slot == _SLOT_GIAY_TO and thay_the:
                warnings.append(
                    "Lưu ý dòng 1: theo quy định ô này dành cho bản sao giấy tờ chứng minh nội dung thay đổi "
                    "(cấp lại để thay đổi thông tin trên thẻ). Đính kèm chung tại đây vì là ô duy nhất nhận "
                    "bản sao giấy tờ kèm theo — tránh bỏ sót tệp; bản scan chưa thấy dấu chứng thực thì cần "
                    "bản sao có chứng thực."
                )
            warnings.append(
                f"Dòng {slot + 1} {_SLOT_SHORT[slot]} — cán bộ bấm nút Mô tả của dòng này và ghi: "
                f"\"{_mo_ta(pieces_on_row, thay_the)}\""
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
    page_types: dict[int, list[str | None]] = {}
    units: list[tuple[Any, str]] = []
    for index, file in enumerate(raw_files):
        entry = by_name.get(file.get("name"), {})
        text = str(entry.get("text") or "")
        pages = _split_pages(text) if not entry.get("error") else None
        if pages and len(pages) > 1:
            # PDF nhiều trang: phân loại TỪNG TRANG để tách bộ hồ sơ gộp ra đúng dòng.
            page_types[index] = [None] * len(pages)
            for page_no, page_text in enumerate(pages, start=1):
                if not _page_follows_previous(page_text):
                    units.append(((index, page_no), page_text))
            continue
        body = pages[0] if pages else text
        # Ảnh chân dung không có chữ → nhận tất định. Tệp OCR lỗi thì KHÔNG coi là ảnh (có thể là đơn).
        if not entry.get("error") and file.get("type") in _OCR_TYPES and _looks_like_photo(file, body):
            llm_types[index] = (_T_ANH, [])
        elif body.strip():
            units.append((index, body))

    started = time.monotonic()
    if units:
        try:
            for key, value in (await _classify_with_llm(units, errors)).items():
                if isinstance(key, tuple):
                    page_types[key[0]][key[1] - 1] = value[0]
                else:
                    llm_types[key] = value
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, llm_types, page_types)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmUnits": [
                f"{raw_files[k[0]]['name']} trang {k[1]}" if isinstance(k, tuple) else raw_files[k]["name"]
                for k, _t in units
            ],
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

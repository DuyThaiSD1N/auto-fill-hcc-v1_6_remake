"""Đính kèm bước "Thành phần hồ sơ" cho thủ tục "Cấp mới giấy phép hành nghề trong giai đoạn chuyển
tiếp..." (cổng Bộ Y tế — Angular mat-table, engine FE `attp-row`).

Bảng thành phần hồ sơ có nhiều dòng (mục a–h); ta gán vào các dòng thường dùng:
  a) "Đơn theo Mẫu 08 Phụ lục I ..."                         ← Đơn đề nghị cấp GPHN.
  b) "... Văn bằng chuyên môn (không áp dụng ..."            ← Bản sao văn bằng chuyên môn (bằng tốt nghiệp).
  d) "... giấy khám sức khỏe do cơ sở khám bệnh ..."         ← Giấy khám sức khỏe.
  e) "Sơ yếu lý lịch tự thuật của người hành nghề ..."       ← Sơ yếu lý lịch (Mẫu 09).
  g) "... giấy xác nhận hoàn thành quá trình thực hành ..."  ← Giấy xác nhận thực hành (Mẫu 07).
  h) "02 ảnh chân dung cỡ 04 cm ..."                         ← 02 ảnh chân dung 4x6.
(Mục c văn bằng chuyên khoa / đ tiếng Việt — trường hợp hiếm, chưa gán tự động.)
FE khớp dòng bằng TÊN giấy tờ (componentName, substring fold), tick checkbox + chọn loaiBan + set file.
Ta upload bản SCAN → loaiBan = "Scan tệp tin".

Phân loại **LLM-primary**: LLM đọc OCR quyết định loại; rule keyword chỉ DỰ PHÒNG. ⚠ Giấy KSK / Giấy xác
nhận thực hành đều GHI "Căn cước công dân số ..." → phải nhận theo loại đặc trưng TRƯỚC cccd. CCCD (thẻ
thật) KHÔNG có dòng riêng trên bảng → bỏ qua.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.cap_moi_giay_phep_hanh_nghe_chuyen_tiep.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_LOAI_BAN = "Scan tệp tin"

_DON = "don_de_nghi"          # mục a
_VANBANG = "van_bang"         # mục b
_SUCKHOE = "suc_khoe"         # mục d
_SYLL = "so_yeu_ly_lich"      # mục e
_THUCHANH = "thuc_hanh"       # mục g
_ANH = "anh_chan_dung"        # mục h
_CCCD = "cccd"
_OTHER = "other"

# Mỗi loại giấy tờ → 1 dòng (mục a–h). componentName = ĐOẠN TEXT ĐẶC TRƯNG DUY NHẤT của dòng (FE khớp
# substring fold vào tên dòng lấy từ DOM). loaiBan = "Scan tệp tin" (đều là file scan/PDF).
_ROWS: dict[str, dict[str, str]] = {
    _DON: {
        "componentName": "Đơn theo Mẫu 08 Phụ lục I",
        "loaiBan": _LOAI_BAN,
        "documentName": "Đơn đề nghị cấp giấy phép hành nghề (Mẫu 08 PL I NĐ 96/2023)",
    },
    _VANBANG: {
        "componentName": "Văn bằng chuyên môn",  # mục b — bản sao văn bằng chuyên môn.
        "loaiBan": _LOAI_BAN,
        "documentName": "Bản sao văn bằng chuyên môn (bằng tốt nghiệp/cử nhân)",
    },
    _SUCKHOE: {
        "componentName": "giấy khám sức khỏe do cơ sở khám bệnh",  # mục d.
        "loaiBan": _LOAI_BAN,
        "documentName": "Giấy khám sức khỏe",
    },
    _SYLL: {
        "componentName": "Sơ yếu lý lịch tự thuật của người hành nghề",
        "loaiBan": _LOAI_BAN,
        "documentName": "Sơ yếu lý lịch tự thuật của người hành nghề (Mẫu 09 PL I)",
    },
    _THUCHANH: {
        "componentName": "giấy xác nhận hoàn thành quá trình thực hành theo Mẫu 07",  # mục g.
        "loaiBan": _LOAI_BAN,
        "documentName": "Giấy xác nhận hoàn thành quá trình thực hành (Mẫu 07 PL I)",
    },
    _ANH: {
        "componentName": "02 ảnh chân dung cỡ 04 cm",  # mục h.
        "loaiBan": _LOAI_BAN,
        "documentName": "02 ảnh chân dung 4x6 nền trắng",
    },
}
# CCCD chỉ dùng ở bước thông tin, KHÔNG có dòng riêng trên bảng thành phần hồ sơ → bỏ qua.
_SKIP_DOCS = {_CCCD}
_ALLOWED_DOC_TYPES = set(_ROWS) | _SKIP_DOCS | {_OTHER}


def _is_identity_text(text: str) -> bool:
    h = _fold(text)
    return any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu", "passport"))


_IMAGE_TOKENS = {"left", "right", "image", "images", "anh", "photo", "picture", "portrait"}


def _is_image_only(text: str) -> bool:
    """True khi OCR RỖNG hoặc CHỈ có nhãn ảnh (vd 'Left image Right image') — dùng để nhận ảnh chân dung
    VÀ để BÁC BỎ khi LLM lỡ gán anh_chan_dung cho tài liệu có nội dung văn bản thật."""
    h = _fold(text)
    if not h:
        return True
    tokens = set(h.split())
    return bool(tokens) and tokens <= _IMAGE_TOKENS


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM).

    ⚠ BẪY QUAN TRỌNG — ĐƠN Mẫu 08 LIỆT KÊ danh mục hồ sơ '(1) văn bằng ... (2) giấy khám sức khỏe ...
    (3) sơ yếu lý lịch ... (4) giấy xác nhận hoàn thành quá trình thực hành ... (5) ảnh 4x6' → text của
    ĐƠN CHỨA từ khóa của MỌI loại khác. Vì vậy PHẢI nhận ĐƠN TRƯỚC (dấu hiệu RIÊNG 'NGƯỜI LÀM ĐƠN' — chỉ
    Đơn có), rồi mới tới các loại khác. Ngoài ra KSK / Xác nhận thực hành đều ghi 'Căn cước công dân số
    ...' → cccd phải chạy CUỐI CÙNG (không bắt nhầm)."""
    h = _fold(text)
    if not h:
        return ""
    # Ảnh chân dung: OCR chỉ ra nhãn ảnh (vd "Left image Right image"), không có nội dung văn bản.
    if _is_image_only(text):
        return _ANH
    # (1) ĐƠN đề nghị (mục a) — NHẬN TRƯỚC vì Đơn liệt kê mọi giấy tờ khác. Dấu hiệu RIÊNG: "NGƯỜI LÀM ĐƠN"
    # ở cuối / tiêu đề "ĐƠN ĐỀ NGHỊ ... cấp giấy phép hành nghề". Các giấy khác KHÔNG có "người làm đơn".
    if "nguoi lam don" in h \
            or ("don de nghi" in h and "cap giay phep hanh nghe" in h and "chuc danh de nghi cap" in h):
        return _DON
    # (2) Sơ yếu lý lịch tự thuật (mục e).
    if "so yeu ly lich" in h or "hoan canh gia dinh" in h or "qua trinh cong tac" in h \
            or "nguyen quan" in h:
        return _SYLL
    # (3) Giấy xác nhận HOÀN THÀNH QUÁ TRÌNH THỰC HÀNH (mục g, Mẫu 07). Nhiều dấu hiệu: tiêu đề, số hiệu
    # GXNTH/GXTTH, "theo Mẫu 07", hoặc "thời gian thực hành" + (người hướng dẫn / cơ sở thực hành).
    if "hoan thanh qua trinh thuc hanh" in h or ("xac nhan" in h and "qua trinh thuc hanh" in h) \
            or "gxnth" in h or "gxtth" in h or "mau so 07" in h or "mau 07" in h \
            or ("thoi gian thuc hanh" in h and ("nguoi huong dan" in h or "co so thuc hanh" in h or "benh vien" in h)):
        return _THUCHANH
    # (4) Giấy khám sức khỏe (mục d).
    if "giay kham suc khoe" in h or "kham suc khoe" in h or "phan loai suc khoe" in h \
            or "phan loai the luc" in h:
        return _SUCKHOE
    # (5) Văn bằng chuyên môn (mục b — bằng tốt nghiệp/cử nhân).
    if "bang tot nghiep" in h or "bang cu nhan" in h or "the degree of bachelor" in h \
            or "so vao so goc cap van bang" in h or ("hieu truong" in h and ("cu nhan" in h or "van bang" in h)):
        return _VANBANG
    # (6) CCCD/CMND (SAU CÙNG — chỉ khi là thẻ CCCD thật, sau khi đã loại KSK/thực hành/... có nhắc CCCD).
    if _is_identity_text(h):
        return _CCCD
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if "anh" in text or "chan dung" in text or "photo" in text or "image" in text:
        return _ANH
    if "thuc hanh" in text or "mau 07" in text or "07" in text:
        return _THUCHANH
    if "suc khoe" in text or "kham" in text:
        return _SUCKHOE
    if "so yeu" in text or "syll" in text or "ly lich" in text or "09" in text:
        return _SYLL
    if "van bang" in text or "bang cap" in text or "cu nhan" in text or "tot nghiep" in text:
        return _VANBANG
    if "don" in text or "de nghi" in text or "08" in text:
        return _DON
    if "cccd" in text or "can cuoc" in text or "cmnd" in text or "ho chieu" in text:
        return _CCCD
    return value if value in _ALLOWED_DOC_TYPES else _OTHER


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=500, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    out: dict[int, str] = {}
    for item in parsed.get("documents", []) or []:
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        out[idx] = _normalize_doc_type(str(item.get("docType") or item.get("type") or ""))
    return out


def _build_row_item(file: dict, file_index: int, doc_type: str) -> dict:
    row = _ROWS[doc_type]
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": row["documentName"],
        "componentName": row["componentName"],
        "loaiBan": row["loaiBan"],
        "target": "attp-row",
        "needsAddComponent": False,
        "detectedType": doc_type,
    }


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    by_name = {item.get("name"): item for item in ocr_results}
    items: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        text = str(by_name.get(file_name, {}).get("text") or "")
        llm_type = llm_types.get(idx, "")
        rule_type = _rule_doc_type(text)
        # CHỐT CHẶN: anh_chan_dung là loại "KHÔNG có text". Nếu LLM lỡ gán anh cho tài liệu CÓ nội dung
        # văn bản (vd nhầm Giấy xác nhận thực hành → ảnh) → BÁC BỎ, để rule route đúng theo nội dung.
        if llm_type == _ANH and not _is_image_only(text):
            llm_type = ""
        # LLM-primary: ưu tiên phán đoán LLM; rule keyword chỉ dự phòng khi LLM trả other/không hợp lệ.
        if llm_type in _ROWS or llm_type in _SKIP_DOCS:
            doc_type, source = llm_type, "llm"
        elif rule_type:
            doc_type, source = rule_type, "rule"
        else:
            doc_type, source = _OTHER, "unknown"

        if doc_type in _ROWS:
            items.append(_build_row_item(file, idx, doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "source": source})
            continue
        if doc_type in _SKIP_DOCS:
            classified.append({"fileName": file_name, "docType": doc_type, "source": source, "skipped": True})
            continue

        warnings.append(f"Không xác định được loại giấy tờ cho file '{file_name}' — vui lòng đính kèm thủ công.")
        classified.append({"fileName": file_name, "docType": _OTHER, "source": source})

    return items, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options or {}
    _ = session
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]

    from app.services import ocr

    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    ocr_by_name = {item.get("name"): item for item in ocr_results}
    # LLM-primary: gửi MỌI file có OCR text cho LLM phân loại.
    llm_docs: list[dict[str, Any]] = []
    for idx, file in enumerate(raw_files):
        text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        if text.strip():
            llm_docs.append({"index": idx, "text": text})

    t1 = time.monotonic()
    llm_types: dict[int, str] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types)
    errors.extend(warnings)
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [raw_files[doc["index"]]["name"] for doc in llm_docs],
            "classified": classified,
            "skippedOcr": skipped_ocr,
            "rows": [{"docType": k, **v} for k, v in _ROWS.items()],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

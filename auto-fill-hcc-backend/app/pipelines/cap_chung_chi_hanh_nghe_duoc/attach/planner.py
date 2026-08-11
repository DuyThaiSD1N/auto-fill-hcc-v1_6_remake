"""Đính kèm bước "Thành phần hồ sơ" cho thủ tục "Cấp Chứng chỉ hành nghề dược..." (cổng Bộ Y tế —
Angular mat-table, engine FE `attp-row`).

Bảng thành phần hồ sơ (mat-checkbox + rdo Bản chính/Scan tệp tin + input file), khớp dòng bằng TÊN giấy
tờ (componentName, substring fold). Ta upload bản SCAN → loaiBan = "Scan tệp tin". componentName lấy
NGUYÊN VĂN từ DOM đính kèm thật:
  1) "Đơn đề nghị cấp Chứng chỉ hành nghề dược, có ảnh chân dung ..." ← Đơn Mẫu 02 + ẢNH chân dung.
  2) "Văn bằng chuyên môn"
  3) "Giấy công nhận tương đương ..." (chỉ văn bằng nước ngoài)
  4) "Phiếu lý lịch tư pháp"
  5) "Giấy tờ do cơ quan có thẩm quyền nước ngoài cấp phải được hợp pháp hóa lãnh sự ..."
  6) "Giấy chứng nhận đủ sức khỏe để hành nghề dược ..."
  7) "Giấy xác nhận thời gian thực hành" (Mẫu 03)
  8) "Giấy xác nhận hoàn thành chương trình đào tạo, cập nhật kiến thức chuyên môn về dược" (Mẫu 08 — chỉ
     trường hợp bị THU HỒI CCHN)

Phân loại **LLM-primary**: LLM đọc OCR quyết định loại; rule keyword chỉ DỰ PHÒNG. CCCD và ẢNH chân dung
KHÔNG có dòng riêng → đính CHUNG vào dòng Đơn đề nghị (dòng ghi "có ảnh chân dung"). Ảnh scan cho OCR
rỗng/rác nên nhận bằng heuristic "không có chữ nghĩa" thay vì tin LLM/rule.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.cap_chung_chi_hanh_nghe_duoc.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_LOAI_BAN = "Scan tệp tin"

_DON = "don_de_nghi"
_ANH = "anh_chan_dung"
_VANBANG = "van_bang"
_TUONG_DUONG = "cong_nhan_tuong_duong"
_LLTP = "ly_lich_tu_phap"
_LANH_SU = "hop_phap_hoa_lanh_su"
_SUC_KHOE = "suc_khoe"
_THUC_HANH = "thoi_gian_thuc_hanh"
_CAP_NHAT = "cap_nhat_kien_thuc"
_GCN_DKKD = "gcn_du_dieu_kien_kd_duoc"
_CCCD = "cccd"
_OTHER = "other"

# Mỗi loại giấy tờ → 1 dòng. componentName = ĐOẠN TEXT ĐẶC TRƯNG DUY NHẤT của dòng (FE khớp substring fold
# vào tên dòng lấy từ DOM). ẢNH chân dung đính CHUNG dòng Đơn đề nghị (dòng ghi "có ảnh chân dung").
_ROWS: dict[str, dict[str, str]] = {
    _DON: {
        "componentName": "Đơn đề nghị cấp Chứng chỉ hành nghề dược",
        "loaiBan": _LOAI_BAN,
        "documentName": "Đơn đề nghị cấp Chứng chỉ hành nghề dược (Mẫu 02, kèm ảnh chân dung)",
    },
    _ANH: {
        "componentName": "Đơn đề nghị cấp Chứng chỉ hành nghề dược",
        "loaiBan": _LOAI_BAN,
        "documentName": "Ảnh chân dung (kèm Đơn đề nghị)",
    },
    _VANBANG: {
        "componentName": "Văn bằng chuyên môn",
        "loaiBan": _LOAI_BAN,
        "documentName": "Văn bằng chuyên môn (bằng tốt nghiệp)",
    },
    _TUONG_DUONG: {
        "componentName": "Giấy công nhận tương đương",
        "loaiBan": _LOAI_BAN,
        "documentName": "Giấy công nhận tương đương văn bằng (văn bằng nước ngoài)",
    },
    _LLTP: {
        "componentName": "Phiếu lý lịch tư pháp",
        "loaiBan": _LOAI_BAN,
        "documentName": "Phiếu lý lịch tư pháp",
    },
    _LANH_SU: {
        "componentName": "hợp pháp hóa lãnh sự",
        "loaiBan": _LOAI_BAN,
        "documentName": "Giấy tờ do cơ quan nước ngoài cấp đã hợp pháp hóa lãnh sự",
    },
    _SUC_KHOE: {
        "componentName": "Giấy chứng nhận đủ sức khỏe",
        "loaiBan": _LOAI_BAN,
        "documentName": "Giấy chứng nhận đủ sức khỏe để hành nghề dược",
    },
    _THUC_HANH: {
        "componentName": "Giấy xác nhận thời gian thực hành",
        "loaiBan": _LOAI_BAN,
        "documentName": "Giấy xác nhận thời gian thực hành (Mẫu 03)",
    },
    _CAP_NHAT: {
        "componentName": "hoàn thành chương trình đào tạo, cập nhật kiến thức",
        "loaiBan": _LOAI_BAN,
        "documentName": "Giấy xác nhận hoàn thành đào tạo, cập nhật kiến thức chuyên môn về dược (Mẫu 08)",
    },
    # CCCD không có dòng riêng → đính CHUNG dòng Đơn đề nghị (theo yêu cầu: kèm cùng ảnh chân dung).
    _CCCD: {
        "componentName": "Đơn đề nghị cấp Chứng chỉ hành nghề dược",
        "loaiBan": _LOAI_BAN,
        "documentName": "Căn cước công dân (kèm Đơn đề nghị)",
    },
    # GCN đủ điều kiện KD dược không có dòng riêng → đính CHUNG dòng Đơn đề nghị (theo yêu cầu).
    _GCN_DKKD: {
        "componentName": "Đơn đề nghị cấp Chứng chỉ hành nghề dược",
        "loaiBan": _LOAI_BAN,
        "documentName": "Giấy chứng nhận đủ điều kiện kinh doanh dược (kèm Đơn đề nghị)",
    },
}
_SKIP_DOCS: set[str] = set()
_ALLOWED_DOC_TYPES = set(_ROWS) | _SKIP_DOCS | {_OTHER}


def _is_identity_text(text: str) -> bool:
    h = _fold(text)
    return any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu", "passport"))


def _is_photo_like(text: str) -> bool:
    """File ẢNH chân dung: OCR rỗng, chỉ nhãn 'image', hoặc ra chuỗi số/rác vô nghĩa.

    Ảnh scan không có văn bản → OCR rỗng hoặc bịa ra chuỗi số dài. Giấy tờ THẬT luôn có nhiều chữ cái →
    đếm chữ cái, quá ít (< 20) coi là ảnh. Chỉ dùng làm DỰ PHÒNG khi cả LLM lẫn rule không nhận ra loại.
    """
    letters = sum(1 for c in _fold(text) if c.isalpha())
    return letters < 20


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM).

    THỨ TỰ QUAN TRỌNG: Đơn Mẫu 02 kê khai LẠI 'Văn bằng chuyên môn' (mục 7) và 'thời gian thực hành'
    (mục 8) nên chứa cả 2 cụm này → PHẢI nhận Đơn TRƯỚC (dấu hiệu 'người làm đơn' + 'đơn đề nghị') để
    khỏi bắt nhầm sang van_bang / thoi_gian_thuc_hanh.
    """
    h = _fold(text)
    if not h:
        return ""
    # Đơn đề nghị cấp CCHN dược (Mẫu 02) — nhận TRƯỚC (xem docstring).
    if "nguoi lam don" in h or ("don de nghi" in h and "chung chi hanh nghe duoc" in h):
        return _DON
    # GCN đủ điều kiện kinh doanh dược — nhận trước van_bang/suc_khoe (đều có 'duoc').
    if "du dieu kien kinh doanh duoc" in h:
        return _GCN_DKKD
    # Mẫu 08 — cập nhật kiến thức (đặt trước "thuc hanh" vì cùng là "giay xac nhan").
    if "cap nhat kien thuc" in h or ("hoan thanh" in h and "dao tao" in h and "duoc" in h):
        return _CAP_NHAT
    # Giấy xác nhận thời gian thực hành (Mẫu 03) — cần TIÊU ĐỀ "giấy xác nhận" + "thời gian thực hành"
    # (không chỉ cụm "thời gian thực hành" vì Đơn Mẫu 02 mục 8 cũng có).
    if "giay xac nhan" in h and "thoi gian thuc hanh" in h:
        return _THUC_HANH
    # Phiếu lý lịch tư pháp.
    if "ly lich tu phap" in h or "lltp" in h or "an tich" in h:
        return _LLTP
    # Giấy công nhận tương đương văn bằng.
    if "cong nhan tuong duong" in h:
        return _TUONG_DUONG
    # Hợp pháp hóa lãnh sự.
    if "hop phap hoa lanh su" in h:
        return _LANH_SU
    # Giấy khám / chứng nhận sức khỏe.
    if "suc khoe" in h or "kham suc khoe" in h:
        return _SUC_KHOE
    # Văn bằng chuyên môn / bằng tốt nghiệp.
    if "bang tot nghiep" in h or "van bang" in h or "cu nhan" in h or ("bang" in h and "duoc" in h):
        return _VANBANG
    # CCCD/CMND (bỏ qua).
    if _is_identity_text(h):
        return _CCCD
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if "du dieu kien kinh doanh" in text or "dkkd" in text:
        return _GCN_DKKD
    if "cap nhat" in text or "08" in text:
        return _CAP_NHAT
    if "thuc hanh" in text or "03" in text:
        return _THUC_HANH
    if "ly lich" in text or "lltp" in text or "tu phap" in text:
        return _LLTP
    if "tuong duong" in text:
        return _TUONG_DUONG
    if "lanh su" in text:
        return _LANH_SU
    if "suc khoe" in text:
        return _SUC_KHOE
    if "van bang" in text or "bang" in text:
        return _VANBANG
    if "anh" in text and "chan dung" in text:
        return _ANH
    if "don" in text or "de nghi" in text or "02" in text:
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
    raw = await client.chat(messages, max_tokens=600, enable_thinking=settings.agent_reasoning)
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

        # DỰ PHÒNG: file ảnh chân dung (OCR rỗng/rác) → đính vào dòng Đơn đề nghị (dòng "có ảnh chân dung").
        if _is_photo_like(text):
            items.append(_build_row_item(file, idx, _ANH))
            classified.append({"fileName": file_name, "docType": _ANH, "source": "photo-fallback"})
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

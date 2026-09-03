"""Đính kèm "Thành phần hồ sơ" cho "Đăng ký đất đai, cấp GCN QSDĐ lần đầu" (cổng DVC Đà Nẵng — engine
`attp-row`).

Bảng thành phần hồ sơ của form này có ~20 dòng theo NHIỀU TRƯỜNG HỢP. Mỗi hồ sơ chỉ dùng vài dòng. Ta chỉ
route những loại giấy tờ NHẬN DIỆN được (componentName ĐÃ verify khớp DUY NHẤT 1 nhãn DOM):
  (4)  Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu 15)         → Bản chính  (BẮT BUỘC)
  (1)  Một trong các giấy tờ Điều 137, khoản 1/5 Điều 148/149 (đất cũ) → Bản sao
  (9)  Mảnh trích đo bản đồ địa chính thửa đất                         → Bản chính
  (2)  Giấy tờ nhận thừa kế QSDĐ chưa được cấp Giấy chứng nhận         → Bản sao
  (12) Chứng từ thực hiện nghĩa vụ tài chính (tờ khai thuế/lệ phí)     → Bản sao
  (16) Văn bản về việc đại diện theo pháp luật dân sự / thỏa thuận     → Bản sao
FE khớp dòng bằng componentName (substring fold vào nhãn dòng), tick + chọn loaiBan + set file. Phân loại
**LLM-primary**; rule keyword chỉ DỰ PHÒNG. CCCD KHÔNG có dòng riêng → bỏ qua (chỉ đối chiếu).
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.dang_ky_dat_dai_lan_dau_da_nang.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON_M15 = "don_m15"
_GIAY_TO_DAT_CU = "giay_to_dat_cu"
_HO_SO_DO_DAC = "ho_so_do_dac"
_THUA_KE = "thua_ke"
_NGHIA_VU_TAI_CHINH = "nghia_vu_tai_chinh"
_VB_DAI_DIEN = "vb_dai_dien"
_CCCD = "cccd"
_OTHER = "other"

# componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng (FE khớp substring fold vào nhãn dòng lấy từ DOM).
# loaiBan theo bản chất (đơn/trích đo do người nộp lập → Bản chính; giấy tờ hỗ trợ → Bản sao).
_ROWS: dict[str, dict[str, str]] = {
    _DON_M15: {"componentName": "Đơn đăng ký đất đai", "loaiBan": "Bản chính",
               "documentName": "Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 15 + phụ lục 15a/15b)"},
    # Dòng (1): "...Điều 137, khoản 1, khoản 5 Điều 148, khoản 1, khoản 5 Điều 149..." — cụm "khoản 1,
    # khoản 5 Điều 148" phân biệt với dòng (17) "khoản 4, khoản 5 Điều 148".
    _GIAY_TO_DAT_CU: {"componentName": "khoản 1, khoản 5 Điều 148", "loaiBan": "Bản sao",
               "documentName": "Giấy tờ về quyền sử dụng đất/tài sản (Điều 137, 148, 149 Luật Đất đai) + sơ đồ nhà"},
    _HO_SO_DO_DAC: {"componentName": "Mảnh trích đo bản đồ địa chính", "loaiBan": "Bản chính",
               "documentName": "Mảnh trích đo bản đồ địa chính thửa đất"},
    _THUA_KE: {"componentName": "nhận thừa kế quyền sử dụng đất chưa được cấp", "loaiBan": "Bản sao",
               "documentName": "Giấy tờ về việc nhận thừa kế QSDĐ chưa được cấp Giấy chứng nhận"},
    _NGHIA_VU_TAI_CHINH: {"componentName": "Chứng từ thực hiện nghĩa vụ tài chính", "loaiBan": "Bản sao",
               "documentName": "Chứng từ thực hiện nghĩa vụ tài chính về đất, tài sản gắn liền với đất"},
    _VB_DAI_DIEN: {"componentName": "Văn bản về việc đại diện", "loaiBan": "Bản sao",
               "documentName": "Văn bản về việc đại diện / thỏa thuận cử người đại diện đứng tên GCN"},
}

# CCCD chỉ đối chiếu → bỏ qua.
_SKIP_DOCS = {_CCCD}
_ALLOWED_DOC_TYPES = set(_ROWS) | _SKIP_DOCS | {_OTHER}


def _is_identity_text(text: str) -> bool:
    h = _fold(text)
    return any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu", "passport"))


def _has_don_m15(text: str) -> bool:
    """File có chứa ĐƠN ĐĂNG KÝ ĐẤT ĐAI (Mẫu 15)? Marker đặc trưng của đơn (khác tờ khai thuế/giấy tờ khác)."""
    h = _fold(text)
    if not h:
        return False
    return (
        "don dang ky dat dai" in h
        or ("dang ky dat dai" in h and "tai san gan lien voi dat" in h)
        or ("mau so 15" in h and "dang ky dat dai" in h)
    )


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM). Dấu hiệu đặc trưng trước."""
    h = _fold(text)
    if not h:
        return ""
    if "don dang ky dat dai" in h or "mau so 15" in h:
        return _DON_M15
    if "manh trich do" in h or "trich do ban do dia chinh" in h or ("do dac" in h and "thua dat" in h):
        return _HO_SO_DO_DAC
    if "trich luc khai tu" in h or "giay chung tu" in h or ("thua ke" in h and "quyen su dung dat" in h):
        return _THUA_KE
    if "van ban" in h and ("cu nguoi dai dien" in h or "dai dien theo" in h or "cap chung mot giay chung nhan" in h):
        return _VB_DAI_DIEN
    if any(k in h for k in ("to khai thue", "to khai le phi truoc ba", "tien su dung dat",
                            "thue su dung dat phi nong nghiep", "cam ket han muc", "nghia vu tai chinh")):
        return _NGHIA_VU_TAI_CHINH
    if "giay chung nhan quyen su dung dat" in h or ("dieu 137" in h) or ("ban ke khai nha" in h):
        return _GIAY_TO_DAT_CU
    if _is_identity_text(h):
        return _CCCD
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if text in _ALLOWED_DOC_TYPES:
        return text
    if "15" in text or ("don" in text and "dang ky" in text):
        return _DON_M15
    if "do dac" in text or "trich do" in text:
        return _HO_SO_DO_DAC
    if "thua ke" in text or "chung tu" in text or "khai tu" in text:
        return _THUA_KE
    if "dai dien" in text or "thoa thuan" in text or "cap chung" in text:
        return _VB_DAI_DIEN
    if "tai chinh" in text or "thue" in text or "le phi" in text or "truoc ba" in text:
        return _NGHIA_VU_TAI_CHINH
    if "dat cu" in text or "137" in text or "148" in text or "149" in text or "ke khai nha" in text:
        return _GIAY_TO_DAT_CU
    if "cccd" in text or "can cuoc" in text or "cmnd" in text or "ho chieu" in text:
        return _CCCD
    return _OTHER


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
        # ƯU TIÊN ĐƠN M15: bộ hồ sơ hay được GỘP nhiều giấy tờ vào 1 file. Nếu file CÓ Đơn đăng ký đất đai
        # (Mẫu 15) thì LUÔN route vào thành phần chính "Đơn đăng ký đất đai" (bắt buộc), bất kể trang đầu là
        # tờ khai thuế / giấy tờ khác (tránh phân loại nhầm cả bộ thành 'nghĩa vụ tài chính' vì trang đầu).
        if _has_don_m15(text):
            doc_type, source = _DON_M15, "priority-don-m15"
        # LLM-PRIMARY: ưu tiên LLM; rule chỉ dùng khi LLM rỗng/không hợp lệ (lỗi 502...).
        elif llm_type in _ROWS or llm_type in _SKIP_DOCS:
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

"""Đính kèm bước "Thành phần hồ sơ" cho thủ tục "Gia hạn Chứng chỉ hành nghề thú y" (Sở Nông nghiệp và
Môi trường — Angular mat-table trên Cổng DVC quốc gia, engine FE `attp-row`).

Bảng thành phần hồ sơ có 3 dòng cố định, mỗi dòng: checkbox + radio rdo_File "1 Bản chính / 1 Bản sao"
+ nút "Scan tệp tin" / "Chọn tệp tin":
  1. "Giấy chứng nhận sức khỏe"                                  ← Giấy khám sức khỏe, Bản chính.
  2. "Giấy phép lao động hoặc giấy xác nhận không thuộc diện …   ← CHỈ người nước ngoài. Cổng TICK SẴN
     (đối với người nước ngoài)"                                   dòng này → hồ sơ không có giấy phép
                                                                   lao động thì gửi `untickRows` để FE
                                                                   BỎ TICK.
  3. "Đơn đăng ký gia hạn theo Mẫu số 02.HNTY …"                 ← Đơn, Bản chính.
Bảng KHÔNG có dòng cho văn bằng chuyên môn → dùng nút "+ Thêm giấy tờ" (`add-document-dialog`) tạo dòng
"Văn bằng, chứng chỉ chuyên môn phù hợp với từng loại hình hành nghề thú y" (1 Bản sao). Cổng không tạo
được dòng đó thì FE ĐÍNH CHUNG vào dòng Đơn (`fallbackComponentName`) và nhắc ghi chú hồ sơ.

Chứng chỉ hành nghề cũ / ảnh thẻ / giấy tờ khác không có dòng riêng → đính chung vào dòng Đơn (ô upload
nhận nhiều file). Mọi item GIỮ TÊN FILE GỐC. CCCD chỉ dùng ở bước thông tin → bỏ qua.

Phân loại **LLM-primary**: LLM đọc OCR quyết định loại; rule keyword chỉ DỰ PHÒNG.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.gia_han_chung_chi_hanh_nghe_thu_y.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON = "don_gia_han"
_GKSK = "gksk"
_VAN_BANG = "van_bang"
_GPLD = "giay_phep_lao_dong"
_CCHN_CU = "cchn_cu"
_ANH_THE = "anh_the"
_CCCD = "cccd"
_OTHER = "other"

# componentName khớp substring (fold) với nhãn dòng trên cổng — lấy đoạn đầu ĐỦ phân biệt, không chép
# cả câu dài vì nhãn thật còn kèm "Phụ lục IB … Nghị định số 32/2026/NĐ-CP …".
_ROWS: dict[str, dict[str, str]] = {
    _GKSK: {"componentName": "Giấy chứng nhận sức khỏe", "loaiBan": "Bản chính"},
    _GPLD: {
        "componentName": "Giấy phép lao động hoặc giấy xác nhận không thuộc diện cấp giấy phép lao động",
        "loaiBan": "Bản chính",
    },
    _DON: {"componentName": "Đơn đăng ký gia hạn theo Mẫu số 02.HNTY", "loaiBan": "Bản chính"},
}
# Dòng tạo qua modal "Thêm giấy tờ" — tên đúng như danh mục giấy tờ của thủ tục, 1 Bản sao chứng thực.
_VAN_BANG_ROW = {
    "componentName": "Văn bằng, chứng chỉ chuyên môn phù hợp với từng loại hình hành nghề thú y",
    "loaiBan": "Bản sao",
}
# Giấy tờ không có dòng riêng → đính chung vào dòng Đơn.
_TO_DON_ROW = {_CCHN_CU, _ANH_THE, _OTHER}
_SKIP_DOCS = {_CCCD}
_ALLOWED_DOC_TYPES = {_DON, _GKSK, _VAN_BANG, _GPLD, _CCHN_CU, _ANH_THE, _CCCD, _OTHER}


def _is_identity_text(text: str) -> bool:
    h = _fold(text)
    return any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu", "passport"))


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM)."""
    h = _fold(text)
    if not h:
        return ""
    # Đơn nhận TRƯỚC: đơn nhắc cả "chứng chỉ hành nghề" lẫn "giấy khám sức khỏe" (gửi kèm).
    if "02.hnty" in h or "02 hnty" in h or "don dang ky gia han" in h \
            or ("don dang ky" in h and "hanh nghe thu y" in h) \
            or ("hanh nghe thu y" in h and "ten toi la" in h):
        return _DON
    # Giấy khám sức khỏe — nhận TRƯỚC chứng chỉ vì mục lý do khám hay ghi "cấp chứng chỉ hành nghề".
    if "giay kham suc khoe" in h or "giay chung nhan suc khoe" in h \
            or ("kham lam sang" in h and "ket luan" in h):
        return _GKSK
    if "chung chi hanh nghe thu y" in h and ("so dang ky" in h or "co gia tri den" in h):
        return _CCHN_CU
    if "bang tot nghiep" in h or "van bang" in h or "advanced diploma" in h \
            or ("hieu truong" in h and "so hieu" in h):
        return _VAN_BANG
    if "giay phep lao dong" in h:
        return _GPLD
    if _is_identity_text(h):
        return _CCCD
    return ""


def _is_photo_only(file: dict, text: str) -> bool:
    """Ảnh chân dung: file ẢNH mà OCR ra (gần như) không có chữ."""
    return str(file.get("type") or "") in {"image/jpeg", "image/png", "image/jpg"} and len(_fold(text)) < 20


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "").replace(" ", "_")
    if text in _ALLOWED_DOC_TYPES:
        return text
    if not text or "other" in text:
        return _OTHER
    if "suc_khoe" in text or "gksk" in text:
        return _GKSK
    if "lao_dong" in text:
        return _GPLD
    if "van_bang" in text or "bang_tot_nghiep" in text:
        return _VAN_BANG
    if "cchn" in text or "chung_chi" in text:
        return _CCHN_CU
    if "don" in text or "02" in text:
        return _DON
    if "anh" in text:
        return _ANH_THE
    if any(k in text for k in ("cccd", "can_cuoc", "cmnd", "ho_chieu")):
        return _CCCD
    return _OTHER


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=400, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    out: dict[int, str] = {}
    for item in parsed.get("documents", []) or []:
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        out[idx] = _normalize_doc_type(str(item.get("docType") or item.get("type") or ""))
    return out


def _row_item(file_name: str, file_index: int, row: dict[str, str], doc_type: str) -> dict:
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        # GIỮ NGUYÊN tên file gốc — engine attp-row đặt tên file theo documentName.
        "documentName": file_name,
        "componentName": row["componentName"],
        "loaiBan": row["loaiBan"],
        "target": "attp-row",
        "needsAddComponent": False,
        "detectedType": doc_type,
    }


def _van_bang_item(file_name: str, file_index: int) -> dict:
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": file_name,
        "componentName": _VAN_BANG_ROW["componentName"],
        "loaiBan": _VAN_BANG_ROW["loaiBan"],
        "quantity": 1,
        "target": "add-document-dialog",
        "needsAddComponent": True,
        "detectedType": _VAN_BANG,
        # Modal không tạo được dòng văn bằng → đính chung vào dòng Đơn (phương án dự phòng).
        "fallbackComponentName": _ROWS[_DON]["componentName"],
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
        if llm_type in _ALLOWED_DOC_TYPES and llm_type != _OTHER:
            doc_type, source = llm_type, "llm"
        elif rule_type:
            doc_type, source = rule_type, "rule"
        elif _is_photo_only(file, text):
            doc_type, source = _ANH_THE, "rule"
        else:
            doc_type, source = _OTHER, "unknown"

        if doc_type in _SKIP_DOCS:
            classified.append({"fileName": file_name, "docType": doc_type, "source": source, "skipped": True})
            continue

        if doc_type == _VAN_BANG:
            items.append(_van_bang_item(file_name, idx))
            routed = _VAN_BANG
        elif doc_type in _ROWS:
            items.append(_row_item(file_name, idx, _ROWS[doc_type], doc_type))
            routed = doc_type
        else:
            items.append(_row_item(file_name, idx, _ROWS[_DON], doc_type))
            routed = _DON
            if doc_type == _OTHER:
                warnings.append(
                    f"Không xác định được loại giấy tờ cho file '{file_name}' — đã đính chung vào dòng "
                    "'Đơn đăng ký gia hạn', vui lòng kiểm tra lại."
                )
        classified.append({"fileName": file_name, "docType": doc_type, "source": source, "routedTo": routed})

    detected = {item["detectedType"] for item in items}
    if _DON not in detected:
        warnings.append("Không tìm thấy Đơn đăng ký gia hạn Chứng chỉ hành nghề thú y (Mẫu 02.HNTY) trong hồ sơ.")
    if _GKSK not in detected:
        warnings.append("Không tìm thấy Giấy khám sức khỏe — dòng 'Giấy chứng nhận sức khỏe' là bắt buộc.")
    # Dòng Giấy phép lao động cổng tick sẵn: công dân Việt Nam không có giấy này → nhờ FE bỏ tick. Gắn vào
    # item attp-row (FE chạy nhóm này trước modal "Thêm giấy tờ"); không có thì item bất kỳ.
    if items and _GPLD not in detected:
        carrier = next((item for item in items if item["target"] == "attp-row"), items[0])
        carrier["untickRows"] = [_ROWS[_GPLD]["componentName"]]

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
            "rows": [{"docType": k, **v} for k, v in _ROWS.items()] + [{"docType": _VAN_BANG, **_VAN_BANG_ROW}],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

"""Đính kèm "Thành phần hồ sơ" cho "Đăng ký thay đổi biện pháp bảo đảm..." (1.011442, cổng DVC Đà Nẵng — engine
`attp-row`).

Bảng thành phần hồ sơ có 12 dòng (theo ảnh ánh xạ đính kèm của thủ tục):
   1 Phiếu yêu cầu theo Mẫu số 02a (01 bản chính)                       → Bản chính  (BẮT BUỘC)
   2 Văn bản sửa đổi, bổ sung hợp đồng bảo đảm                         → Bản sao
   3 Văn bản chuyển giao quyền đòi nợ, chuyển giao nghĩa vụ            → Bản sao
   4 Văn bản khác chứng minh có căn cứ đăng ký thay đổi                → Bản sao
   5 Giấy chứng nhận (bản gốc)                                         → Bản chính  — ĐÍNH KÈM CHUNG mọi GCN
   6 GCN khi thay đổi theo điểm b khoản 1 Điều 18 NĐ 99/2022           → không tự đính (dùng lại file dòng 5)
   7 (i) văn bản về đại diện                                           → Bản sao    — ĐÍNH KÈM CHUNG giấy ủy
     quyền/giới thiệu + GCN đăng ký doanh nghiệp (chứng minh tư cách người đại diện theo pháp luật)
   8 (ii) văn bản pháp nhân giao nhiệm vụ cho chi nhánh                 → Bản sao
   9 (iii) miễn nghĩa vụ nộp phí: hợp đồng bảo đảm/hợp đồng tín dụng    → Bản sao
  10 (iv) nhiều bên bảo đảm/nhận bảo đảm                               → không tự đính
  11 (v) công ty quản lý tài sản của TCTD                              → không tự đính
  12 (vi) Danh mục văn bản Mẫu số 01đ/02đ                              → Bản sao
FE gom item theo componentName (substring fold) → nhiều file cùng dòng được set MỘT lần (ô upload multiple). Mỗi
file mang documentName RIÊNG (GCN kèm số phát hành) vì engine attp-row không tự đánh số tên trùng. Phân loại
**LLM-primary**; rule keyword chỉ DỰ PHÒNG. CCCD không có dòng riêng → bỏ qua (chỉ đối chiếu).
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.compact_agent.runner import _extract_docx_text, _is_docx
from app.pipelines.dang_ky_thay_doi_bien_phap_bao_dam_qsdd.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_PHIEU_02A = "phieu_02a"
_VB_SUA_DOI = "van_ban_sua_doi_hdbd"
_VB_CHUYEN_GIAO = "van_ban_chuyen_giao"
_VB_CAN_CU = "van_ban_can_cu_khac"
_GCN = "gcn"
_VB_DAI_DIEN = "van_ban_dai_dien"
_DKDN = "dkdn"
_VB_GIAO_NHIEM_VU = "van_ban_giao_nhiem_vu"
_HOP_DONG = "hop_dong_bao_dam"
_DANH_MUC = "danh_muc_01d"
_CCCD = "cccd"
_OTHER = "other"

# componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng (FE khớp substring fold vào nhãn dòng lấy từ DOM, lấy dòng ĐẦU
# TIÊN khớp) → mỗi chuỗi chỉ xuất hiện trong đúng một dòng.
_ROWS: dict[str, dict[str, str]] = {
    _PHIEU_02A: {"componentName": "Phiếu yêu cầu theo Mẫu số 02a", "loaiBan": "Bản chính",
                 "documentName": "Phiếu yêu cầu đăng ký thay đổi biện pháp bảo đảm (Mẫu số 02a)"},
    _VB_SUA_DOI: {"componentName": "Văn bản sửa đổi, bổ sung hợp đồng bảo đảm", "loaiBan": "Bản sao",
                  "documentName": "Văn bản sửa đổi, bổ sung hợp đồng bảo đảm"},
    _VB_CHUYEN_GIAO: {"componentName": "Văn bản chuyển giao quyền đòi nợ", "loaiBan": "Bản sao",
                      "documentName": "Văn bản chuyển giao quyền đòi nợ, chuyển giao nghĩa vụ"},
    _VB_CAN_CU: {"componentName": "Văn bản khác chứng minh có căn cứ đăng ký thay đổi", "loaiBan": "Bản sao",
                 "documentName": "Văn bản chứng minh căn cứ đăng ký thay đổi"},
    _GCN: {"componentName": "Giấy chứng nhận (bản gốc)", "loaiBan": "Bản chính",
           "documentName": "Giấy chứng nhận (bản gốc)"},
    _VB_DAI_DIEN: {"componentName": "thông qua người đại diện", "loaiBan": "Bản sao",
                   "documentName": "Văn bản ủy quyền"},
    _DKDN: {"componentName": "thông qua người đại diện", "loaiBan": "Bản sao",
            "documentName": "Giấy chứng nhận đăng ký doanh nghiệp"},
    _VB_GIAO_NHIEM_VU: {"componentName": "chi nhánh của pháp nhân", "loaiBan": "Bản sao",
                        "documentName": "Văn bản giao nhiệm vụ cho chi nhánh của pháp nhân"},
    _HOP_DONG: {"componentName": "miễn nghĩa vụ nộp phí", "loaiBan": "Bản sao",
                "documentName": "Hợp đồng bảo đảm"},
    _DANH_MUC: {"componentName": "Danh mục văn bản được kê khai", "loaiBan": "Bản sao",
                "documentName": "Danh mục văn bản (Mẫu số 01đ)"},
}

# CCCD chỉ đối chiếu → bỏ qua.
_SKIP_DOCS = {_CCCD}
_ALLOWED_DOC_TYPES = set(_ROWS) | _SKIP_DOCS | {_OTHER}

# Số phát hành GCN in ở trang bìa: 2 chữ cái + 6 chữ số ("AB 123456").
_SERIAL_RE = re.compile(r"\b([A-Z]{2})\s?(\d{6})\b")


def _is_identity_text(text: str) -> bool:
    h = _fold(text)
    return any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu", "passport"))


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM). Tiêu đề ở đầu tài liệu trước, dấu hiệu rải rác sau."""
    h = _fold(text)
    if not h:
        return ""
    head = h[:800]
    if "phieu yeu cau" in head and ("thay doi" in head or "02a" in head):
        return _PHIEU_02A
    if "danh muc" in head and ("01d" in head or "02d" in head):
        return _DANH_MUC
    if any(m in head for m in ("giay uy quyen", "hop dong uy quyen", "giay gioi thieu")):
        return _VB_DAI_DIEN
    if "chuyen giao quyen doi no" in head or "mua ban no" in head:
        return _VB_CHUYEN_GIAO
    if any(m in head for m in ("hop dong the chap", "hop dong bao dam", "hop dong tin dung")):
        if "sua doi" in head or "bo sung" in head or "phu luc" in head:
            return _VB_SUA_DOI
        return _HOP_DONG
    if "giay chung nhan dang ky doanh nghiep" in h or ("ma so doanh nghiep" in h and "dang ky lan dau" in h):
        return _DKDN
    if "giay chung nhan" in h and "quyen su dung dat" in h:
        return _GCN
    if _is_identity_text(h):
        return _CCCD
    return ""


def _normalize_doc_type(value: str) -> str:
    text = re.sub(r"[\s\-]+", "_", _fold(value or "")).strip("_")
    if not text or text == "other":
        return _OTHER
    if text in _ALLOWED_DOC_TYPES:
        return text
    if "02a" in text or ("phieu" in text and "yeu_cau" in text):
        return _PHIEU_02A
    if "danh_muc" in text or "01d" in text:
        return _DANH_MUC
    if "giao_nhiem_vu" in text or "chi_nhanh" in text:
        return _VB_GIAO_NHIEM_VU
    if "uy_quyen" in text or "dai_dien" in text or "gioi_thieu" in text:
        return _VB_DAI_DIEN
    if "chuyen_giao" in text or "doi_no" in text:
        return _VB_CHUYEN_GIAO
    if "sua_doi" in text or "bo_sung" in text:
        return _VB_SUA_DOI
    if "can_cu" in text:
        return _VB_CAN_CU
    if "hop_dong" in text:
        return _HOP_DONG
    if "dkdn" in text or "doanh_nghiep" in text:
        return _DKDN
    if "gcn" in text or "chung_nhan" in text or "so_do" in text:
        return _GCN
    if "cccd" in text or "can_cuoc" in text or "cmnd" in text or "ho_chieu" in text:
        return _CCCD
    return _OTHER


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=800, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    out: dict[int, str] = {}
    for item in parsed.get("documents", []) or []:
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        out[idx] = _normalize_doc_type(str(item.get("docType") or item.get("type") or ""))
    return out


def _gcn_serial(text: str) -> str:
    m = _SERIAL_RE.search(str(text or "").upper())
    return f"{m.group(1)} {m.group(2)}" if m else ""


def _document_name(doc_type: str, text: str) -> str:
    """GCN: kèm số phát hành để hai GCN cùng dòng 5 không trùng tên tệp trên cổng."""
    name = _ROWS[doc_type]["documentName"]
    if doc_type == _GCN:
        serial = _gcn_serial(text)
        if serial:
            return f"Giấy chứng nhận {serial} (bản gốc)"
    return name


def _build_row_item(file: dict, file_index: int, doc_type: str, text: str) -> dict:
    row = _ROWS[doc_type]
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": _document_name(doc_type, text),
        "componentName": row["componentName"],
        "loaiBan": row["loaiBan"],
        "target": "attp-row",
        "needsAddComponent": False,
        "detectedType": doc_type,
    }


def _dedupe_document_names(items: list[dict]) -> None:
    """Cùng dòng mà trùng documentName (vd 2 GCN không đọc được số phát hành) → đánh số " 2", " 3"."""
    counts: dict[tuple[str, str], int] = {}
    for item in items:
        key = (_fold(item["componentName"]), _fold(item["documentName"]))
        counts[key] = counts.get(key, 0) + 1
        if counts[key] > 1:
            item["documentName"] = f"{item['documentName']} {counts[key]}"


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
        if llm_type in _ROWS or llm_type in _SKIP_DOCS:
            doc_type, source = llm_type, "llm"
        elif rule_type:
            doc_type, source = rule_type, "rule"
        else:
            doc_type, source = _OTHER, "unknown"

        if doc_type in _ROWS:
            items.append(_build_row_item(file, idx, doc_type, text))
            classified.append({"fileName": file_name, "docType": doc_type, "source": source})
            continue
        if doc_type in _SKIP_DOCS:
            classified.append({"fileName": file_name, "docType": doc_type, "source": source, "skipped": True})
            continue

        warnings.append(f"Không xác định được loại giấy tờ cho file '{file_name}' — vui lòng đính kèm thủ công.")
        classified.append({"fileName": file_name, "docType": _OTHER, "source": source})

    _dedupe_document_names(items)

    types = {item["detectedType"] for item in items}
    if files and _PHIEU_02A not in types:
        warnings.append("Chưa có Phiếu yêu cầu đăng ký thay đổi (Mẫu số 02a) — giấy tờ BẮT BUỘC của dòng 1, vui "
                        "lòng bổ sung.")
    if _HOP_DONG in types:
        warnings.append("Hợp đồng bảo đảm/hợp đồng tín dụng được đính vào dòng (iii) miễn nghĩa vụ nộp phí — chỉ giữ "
                        "nếu hồ sơ thuộc diện miễn phí, không thì gỡ ra.")
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
    # Phiếu 02a hay nộp bằng file Word (cổng cho tải mẫu .docx) → trích text trực tiếp để phân loại.
    ocr_results.extend(_extract_docx_text(f) for f in raw_files if _is_docx(f))
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
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES and not _is_docx(f)]

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

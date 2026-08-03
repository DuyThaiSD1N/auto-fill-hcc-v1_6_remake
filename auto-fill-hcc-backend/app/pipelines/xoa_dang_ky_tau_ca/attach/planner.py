"""Lập kế hoạch đính kèm cho thủ tục xóa đăng ký tàu cá.

Trang hồ sơ là bảng Angular bốn dòng Mẫu 13/12/11/10.ĐKT; mỗi dòng cần tick checkbox, chọn Bản chính
và upload file nên dùng engine FE ``attp-row``. CCCD riêng của người nộp không có dòng cố định nên dùng
contract ``add-document-dialog`` để FE chọn đúng loại trong modal "Thêm giấy tờ", tạo dòng rồi upload.
Danh sách option thật trên cổng không có mục phù hợp cho Hợp đồng mua bán, Lời chứng và GCN đăng ký
cũ, nên các tài liệu chứng minh này được đính kèm cùng dòng Tờ khai Mẫu 10.ĐKT theo fallback đã duyệt.
PDF gộp có Mẫu 10.ĐKT vẫn được đưa nguyên file vào dòng Tờ khai.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.xoa_dang_ky_tau_ca.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_LOAI_BAN = "Bản chính"

_MAU_13 = "mau_13_xoa_dang_ky"
_MAU_12 = "mau_12_xac_nhan_tinh_trang"
_MAU_11 = "mau_11_xac_minh_tinh_trang"
_TO_KHAI_10 = "to_khai_10"
_HOP_DONG = "hop_dong_mua_ban"
_GCN_DANG_KY = "gcn_dang_ky_tau_ca"
_CCCD = "cccd"
_OTHER = "other"

_ROWS: dict[str, dict[str, str]] = {
    _MAU_13: {
        "componentName": "Giấy chứng nhận xóa đăng ký theo Mẫu số 13.ĐKT",
        "documentName": "Giấy chứng nhận xóa đăng ký tàu (Mẫu số 13.ĐKT)",
    },
    _MAU_12: {
        "componentName": "Biên bản xác nhận tình trạng của tàu theo Mẫu số 12.ĐKT",
        "documentName": "Biên bản xác nhận tình trạng của tàu (Mẫu số 12.ĐKT)",
    },
    _MAU_11: {
        "componentName": "Biên bản xác minh tình trạng của tàu theo Mẫu số 11.ĐKT",
        "documentName": "Biên bản xác minh tình trạng của tàu (Mẫu số 11.ĐKT)",
    },
    _TO_KHAI_10: {
        "componentName": "Tờ khai xóa đăng ký tàu cá theo Mẫu số 10.ĐKT",
        "documentName": "Tờ khai xóa đăng ký tàu cá (Mẫu số 10.ĐKT)",
    },
}

_SUPPORTING_DOC_NAMES: dict[str, str] = {
    _HOP_DONG: "Hợp đồng mua bán tàu cá đã công chứng",
    _GCN_DANG_KY: "Giấy chứng nhận đăng ký tàu cá cũ",
}
_CCCD_COMPONENT = (
    "Trường hợp nộp trực tiếp thì xuất trình bản chính hoặc bản sao có chứng thực giấy chứng minh nhân dân "
    "hoặc hộ chiếu còn giá trị sử dụng."
)
_ALLOWED_DOC_TYPES = set(_ROWS) | set(_SUPPORTING_DOC_NAMES) | {_CCCD, _OTHER}


def _rule_doc_type(text: str) -> str:
    """Phân loại tất định dự phòng; nhận Mẫu 10 trước để giữ đúng PDF hồ sơ gộp."""
    h = _fold(text)
    if not h:
        return ""
    if "to khai xoa dang ky" in h or ("mau so 10" in h and "xoa dang ky tau" in h):
        return _TO_KHAI_10
    if "giay chung nhan xoa dang ky" in h or ("mau so 13" in h and "xoa dang ky" in h):
        return _MAU_13
    if "bien ban xac nhan tinh trang" in h or ("mau so 12" in h and "tinh trang cua tau" in h):
        return _MAU_12
    if "bien ban xac minh tinh trang" in h or ("mau so 11" in h and "tinh trang cua tau" in h):
        return _MAU_11
    if (
        "hop dong mua ban tau" in h
        or ("ben ban" in h and "ben mua" in h and "tau ca" in h)
        or "loi chung cua cong chung vien" in h
    ):
        return _HOP_DONG
    if "giay chung nhan dang ky tau ca" in h or (
        "so dang ky" in h and "chu tau" in h and "co quan dang ky" in h
    ):
        return _GCN_DANG_KY
    if any(k in h for k in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu")):
        return _CCCD
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if "10" in text or "to khai" in text:
        return _TO_KHAI_10
    if "13" in text or "chung nhan xoa" in text:
        return _MAU_13
    if "12" in text or "xac nhan tinh trang" in text:
        return _MAU_12
    if "11" in text or "xac minh tinh trang" in text:
        return _MAU_11
    if "hop dong" in text or "mua ban" in text:
        return _HOP_DONG
    if "gcn" in text or "dang ky tau" in text:
        return _GCN_DANG_KY
    if any(k in text for k in ("cccd", "can cuoc", "cmnd", "ho chieu")):
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
            index = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        out[index] = _normalize_doc_type(str(item.get("docType") or item.get("type") or ""))
    return out


def _build_row_item(file: dict, file_index: int, doc_type: str) -> dict:
    row = _ROWS[doc_type]
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": row["documentName"],
        "componentName": row["componentName"],
        "loaiBan": _LOAI_BAN,
        "target": "attp-row",
        "needsAddComponent": False,
        "detectedType": doc_type,
    }


def _supporting_document_name(doc_type: str, text: str, file_name: str) -> str:
    if doc_type == _HOP_DONG:
        evidence = _fold(f"{file_name}\n{text}")
        if "loi chung" in evidence or ("cong chung vien" in evidence and "hop dong mua ban" not in evidence):
            return "Lời chứng của công chứng viên"
    return _SUPPORTING_DOC_NAMES[doc_type]


def _build_supporting_row_item(file: dict, file_index: int, doc_type: str, text: str) -> dict:
    """Cổng không có option riêng nên đưa tài liệu chứng minh vào cùng input multiple của Mẫu 10."""
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    row = _ROWS[_TO_KHAI_10]
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": _supporting_document_name(doc_type, text, file_name),
        "componentName": row["componentName"],
        "loaiBan": _LOAI_BAN,
        "target": "attp-row",
        "needsAddComponent": False,
        "detectedType": doc_type,
    }


def _cccd_holder_name(text: str, file_name: str) -> str:
    """Lấy tên chủ thẻ để hai CCCD cùng một thành phần vẫn có tên file phân biệt."""
    lines = [re.sub(r"\s+", " ", line).strip() for line in str(text or "").splitlines()]
    for index, line in enumerate(lines):
        folded = _fold(line)
        if not any(label in folded for label in ("ho va ten", "ho ten", "full name")):
            continue
        inline = re.sub(
            # Greedy tới nhãn cuối để dòng song ngữ "Họ và tên / Full name:" không trả
            # nhầm chính cụm "Full name" làm tên chủ thẻ.
            r"^.*(?:họ\s*(?:và\s*)?tên|full\s*name)\s*:?[\s/]*",
            "",
            line,
            flags=re.IGNORECASE,
        ).strip(" :-/")
        candidates = [inline] if inline else []
        candidates.extend(lines[index + 1:index + 3])
        for candidate in candidates:
            candidate = re.sub(r"\s+", " ", candidate).strip(" :-/")
            words = candidate.split()
            if 2 <= len(words) <= 8 and not any(char.isdigit() for char in candidate):
                return candidate.title()

    # OCR mờ vẫn cần tên riêng thay vì để nhiều file cùng tên. Filename chỉ là fallback hiển thị,
    # không dùng để xác định vai trò người nộp/chủ hồ sơ.
    stem = re.sub(r"\.[^.]+$", "", file_name).strip()
    suffix = re.sub(r"(?i)^.*?(?:cccd|cmnd|can[-_ ]?cuoc)[-_ ]*", "", stem).strip("-_ ")
    if suffix:
        suffix = re.sub(r"(?<=[a-zà-ỹ])(?=[A-ZĐ])", " ", suffix)
        return re.sub(r"[-_]+", " ", suffix).strip().title()
    return stem


def _cccd_document_name(text: str, file_name: str) -> str:
    holder = _cccd_holder_name(text, file_name)
    return f"Căn cước công dân_{holder}" if holder else "Căn cước công dân"


def _build_add_document_item(file: dict, file_index: int, text: str) -> dict:
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    document_name = _cccd_document_name(text, file_name)
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": _CCCD_COMPONENT,
        "loaiBan": _LOAI_BAN,
        "quantity": 1,
        "target": "add-document-dialog",
        "needsAddComponent": True,
        "detectedType": _CCCD,
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

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        text = str(by_name.get(file_name, {}).get("text") or "")
        llm_type = llm_types.get(index, "")
        rule_type = _rule_doc_type(text)
        if llm_type and llm_type != _OTHER:
            doc_type, source = llm_type, "llm"
        elif rule_type:
            doc_type, source = rule_type, "rule"
        else:
            doc_type, source = _OTHER, "unknown"

        if doc_type in _ROWS:
            items.append(_build_row_item(file, index, doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "source": source})
            continue
        if doc_type == _CCCD:
            document_name = _cccd_document_name(text, file_name)
            items.append(_build_add_document_item(file, index, text))
            classified.append({
                "fileName": file_name,
                "docType": doc_type,
                "source": source,
                "documentName": document_name,
            })
            continue
        if doc_type in _SUPPORTING_DOC_NAMES:
            document_name = _supporting_document_name(doc_type, text, file_name)
            items.append(_build_supporting_row_item(file, index, doc_type, text))
            classified.append({
                "fileName": file_name,
                "docType": doc_type,
                "source": source,
                "documentName": document_name,
                "fallbackComponent": _TO_KHAI_10,
            })
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
    for index, file in enumerate(raw_files):
        text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        if text.strip():
            llm_docs.append({"index": index, "text": text})

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
    manual = [item for item in classified if item.get("manualAttachment")]
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [raw_files[doc["index"]]["name"] for doc in llm_docs],
            "classified": classified,
            "manualAttachments": manual,
            "skippedOcr": skipped_ocr,
            "rows": [{"docType": key, **value} for key, value in _ROWS.items()],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

"""Lập kế hoạch đính kèm "Tính hoặc tính lại tiền sử dụng đất theo các điểm a, b, c và d khoản 2 Điều 12
NĐ 50/2026/NĐ-CP" tại Quảng Ninh (1.115148).

Cùng nền tảng với các thủ tục đất đai Quảng Ninh khác (React/Radix, modal "Danh sách tài liệu điện tử"
→ engine wallet-modal). KHÁC các thủ tục QN kia: bảng thành phần hồ sơ KHÔNG có dòng đặt tên sẵn — cổng
chỉ dựng một dòng có ô "Tên Hồ Sơ" TRỐNG, các dòng sau phải bấm "Thêm thành phần hồ sơ". Vì vậy mọi tệp
đều phát target="new" kèm componentName: FE gõ tên vào dòng trống còn lại (findReusableBlankAttachmentRow)
hoặc bấm thêm dòng rồi gõ tên. Thứ tự đính giữ Đơn trước, Giấy tờ kèm theo sau. Thủ tục chỉ đính kèm,
không điền.

Hồ sơ thực tế hay quét GỘP mọi giấy tờ kèm theo (quyết định chuyển mục đích, giấy nộp tiền, thông báo
nộp tiền, GCN, phiếu chuyển thông tin địa chính, tờ trình, biên bản, trích lục...) vào MỘT PDF. File đó
đính NGUYÊN vào hàng 2 (không tách trang); planner liệt kê các giấy tờ nằm chung và đề xuất câu trích yếu
cho ô "Ghi chú (Trích yếu nội dung hồ sơ)" để cán bộ dán vào.
"""

import asyncio
import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import sanitize_wallet_document_label as _wallet_label
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt


def _derive_component_name(file_name: str) -> str:
    """Tên thành phần hồ sơ MỚI cho giấy tờ ngoài danh mục — lấy theo tên file (bỏ đuôi, gạch dưới→cách)."""
    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", str(file_name or "")).strip()
    stem = re.sub(r"[_]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem or "Tài liệu khác kèm theo"


_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_LOAI_BAN = "Bản chính"
_AUTHORIZATION = "van_ban_dai_dien"
_EXTRA_TYPES = {_AUTHORIZATION}   # ngoài 2 thành phần chính, vẫn thêm dòng mới
_REQUIRED = ("don_de_nghi", "giay_to_kem_theo")

# 2 thành phần chính, theo thứ tự đính. "name" là chữ FE GÕ vào ô "Tên Hồ Sơ" của dòng (không có dòng sẵn
# để khớp), nên ghi đủ tên theo ánh xạ của bộ phận một cửa.
_ROUTES: dict[str, dict[str, Any]] = {
    "don_de_nghi": {
        "index": 1,
        "name": "Đơn đề nghị tính lại tiền sử dụng đất",
    },
    "giay_to_kem_theo": {
        "index": 2,
        "name": (
            "Giấy tờ kèm theo đơn (QĐ chuyển mục đích, GCN, thông báo và chứng từ nộp tiền, hồ sơ địa chính)"
        ),
    },
}
_ALLOWED = set(_ROUTES) | _EXTRA_TYPES | {"other"}

_DISPLAY = {
    "don_de_nghi": "Đơn đề nghị tính lại tiền sử dụng đất",
    "giay_to_kem_theo": "Giấy tờ kèm theo đơn",
    _AUTHORIZATION: "Văn bản đại diện hoặc ủy quyền",
}

# Tiêu đề đơn chỉ xét ở PHẦN ĐẦU file: tờ trình, biên bản trong bộ giấy tờ kèm theo hay nhắc lại "đơn đề
# nghị của ông/bà..." ở thân văn bản.
_HEAD_CHARS = 1500
_DON_MARKERS = ("don de nghi tinh lai tien su dung dat", "don de nghi tinh tien su dung dat")

# Giấy tờ hay nằm trong bộ "giấy tờ kèm theo" — dùng cho fallback rule và để liệt kê vào ghi chú.
_KEM_THEO_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("quyết định cho phép chuyển mục đích sử dụng đất", ("cho phep chuyen muc dich su dung dat",)),
    ("giấy nộp tiền vào ngân sách nhà nước", ("giay nop tien vao ngan sach nha nuoc",)),
    ("thông báo nộp tiền sử dụng đất", ("thong bao nop tien su dung dat",)),
    ("thông báo nộp lệ phí trước bạ", ("thong bao nop le phi truoc ba",)),
    ("phiếu chuyển thông tin địa chính", ("phieu chuyen thong tin dia chinh", "phieu chuyen thong tin de xac dinh")),
    ("Giấy chứng nhận quyền sử dụng đất", ("giay chung nhan quyen su dung dat",)),
    ("tờ trình", ("to trinh so", "to trinh ve viec")),
    ("biên bản kiểm tra hiện trạng", ("bien ban kiem tra",)),
    ("trích lục bản đồ địa chính", ("trich luc ban do dia chinh", "trich do ban do dia chinh")),
)


def _normalize_doc_type(value: Any) -> str:
    folded = _fold(str(value or ""))
    for doc_type in _ALLOWED:
        if folded == _fold(doc_type):
            return doc_type
    return "other"


def _rule_doc_type(text: str) -> str:
    """Fallback chỉ dùng marker đủ đặc trưng để không đính nhầm hàng."""
    folded = _fold(text or "")
    if not folded:
        return ""
    head = folded[:_HEAD_CHARS]
    if any(marker in head for marker in _DON_MARKERS):
        return "don_de_nghi"
    if any(marker in head for marker in ("giay uy quyen", "hop dong uy quyen", "van ban uy quyen")):
        return _AUTHORIZATION
    if any(marker in folded for _, markers in _KEM_THEO_MARKERS for marker in markers):
        return "giay_to_kem_theo"
    return ""


def _bundled_documents(text: str) -> list[str]:
    """Các giấy tờ nằm chung trong file kèm theo (chỉ dùng để nhắc ghi chú)."""
    folded = _fold(text or "")
    return [label for label, markers in _KEM_THEO_MARKERS if any(marker in folded for marker in markers)]


def _first(pattern: str, folded: str) -> str:
    match = re.search(pattern, folded)
    return match.group(1) if match else ""


def _suggest_note(texts: list[str]) -> str:
    """Câu trích yếu đề xuất cho ô Ghi chú, đọc từ đơn/giấy tờ kèm theo. Thiếu số thửa thì không đề xuất."""
    folded = " ".join(_fold(text) for text in texts if text)
    thua = _first(r"thua dat so\s*[:.]?\s*(\d+)", folded) or _first(r"thua so\s*[:.]?\s*(\d+)", folded)
    if not thua:
        return ""
    to = _first(r"to ban do so\s*[:.]?\s*(\d+)", folded)
    qd = re.search(r"quyet dinh so\s*[:.]?\s*(\d+)\s*/\s*(qd-[a-z]+)", folded)
    dien_tich = _first(
        r"chuyen muc dich[^.;]{0,120}?(?:dien tich)?\s*[:.]?\s*(\d+(?:[.,]\d+)?)\s*m(?:2|²)", folded
    )

    note = (
        "Đề nghị tính lại tiền sử dụng đất theo khoản 2 Điều 12 Nghị định số 50/2026/NĐ-CP - "
        f"thửa đất số {thua}"
    )
    if to:
        note += f", tờ bản đồ số {to}"
    if qd:
        number = f"{qd.group(1)}/{qd.group(2).upper().replace('QD', 'QĐ')}"
        note += "; chuyển mục đích"
        if dien_tich:
            note += f" {dien_tich} m²"
        note += f" theo Quyết định số {number}"
    return note + "."


def _llm_document(document: dict[str, Any]) -> dict[str, Any]:
    text = str(document.get("text") or "")
    return {"index": document.get("index"), "text": text[:12000]}


async def _classify_one_with_llm(document: dict[str, Any]) -> tuple[int, str]:
    index = int(document.get("index"))
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt([_llm_document(document)])},
    ]
    raw = await client.chat(messages, max_tokens=120, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    first = next(iter(parsed.get("documents", []) or []), {})
    return index, _normalize_doc_type(first.get("docType") or first.get("type"))


async def _classify_with_llm(
    documents: list[dict[str, Any]],
    errors: list[str] | None = None,
) -> dict[int, str]:
    if not documents:
        return {}

    # Một prompt/call cho mỗi file: PDF dài hoặc một lỗi provider chỉ làm file đó fallback rule.
    outcomes = await asyncio.gather(
        *(_classify_one_with_llm(document) for document in documents),
        return_exceptions=True,
    )
    result: dict[int, str] = {}
    for document, outcome in zip(documents, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            if errors is not None:
                errors.append(f"attachment_agent file {document.get('index')}: {outcome}")
            continue
        index, doc_type = outcome
        result[index] = doc_type
    return result


def _build_item(file: dict, file_index: int, doc_type: str) -> dict:
    base = {
        "fileIndex": file_index,
        "fileName": str(file.get("name") or f"file-{file_index + 1}"),
        "documentName": _wallet_label(_DISPLAY[doc_type]),
        "loaiBan": _LOAI_BAN,
        "detectedType": doc_type,
    }
    name = _ROUTES[doc_type]["name"] if doc_type in _ROUTES else _DISPLAY[doc_type]
    # Cổng không có dòng đặt tên sẵn → luôn là dòng mới, FE gõ tên rồi mới chọn tệp.
    return {
        **base,
        "componentName": name,
        "target": "new",
        "needsAddComponent": True,
    }


def _attach_order(item: dict) -> tuple[int, int]:
    """Đơn → Giấy tờ kèm theo → các dòng thêm khác; trong cùng loại giữ thứ tự tệp tải lên."""
    route = _ROUTES.get(item.get("detectedType"))
    return (route["index"] if route else len(_ROUTES) + 1, int(item.get("fileIndex") or 0))


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    ocr_by_name = {item.get("name"): item for item in ocr_results}
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    note_sources: list[str] = []
    bundle_notes: list[str] = []

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        text = str(ocr_by_name.get(file_name, {}).get("text") or "")
        llm_type = llm_types.get(index, "")
        rule_type = _rule_doc_type(text)

        if llm_type in _ROUTES or llm_type in _EXTRA_TYPES:
            doc_type, source = llm_type, "llm"
        elif rule_type in _ROUTES or rule_type in _EXTRA_TYPES:
            doc_type, source = rule_type, "rule"
        else:
            doc_type, source = "other", "llm" if llm_type == "other" else "unknown"

        if doc_type in _ROUTES:
            note_sources.append(text)
        if doc_type == "giay_to_kem_theo":
            bundled = _bundled_documents(text)
            if len(bundled) > 1:
                bundle_notes.append(f'file "{file_name}" gồm: {"; ".join(bundled)}')

        if doc_type in _ROUTES or doc_type in _EXTRA_TYPES:
            item = _build_item(file, index, doc_type)
            attachments.append(item)
            classified.append({
                "fileName": file_name,
                "docType": doc_type,
                "source": source,
                "target": item["target"],
            })
            continue

        # Giấy tờ NGOÀI danh mục → KHÔNG bỏ qua: thêm thành phần hồ sơ MỚI đặt tên theo file.
        new_name = _derive_component_name(file_name)
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": _wallet_label(new_name),
            "loaiBan": _LOAI_BAN,
            "detectedType": "other",
            "componentName": new_name,
            "target": "new",
            "needsAddComponent": True,
        })
        classified.append({"fileName": file_name, "docType": "other", "source": source, "target": "new"})

    # FE đính theo thứ tự plan: dòng trống sẵn có của cổng nhận Đơn, các dòng thêm sau mới tới giấy tờ khác.
    attachments.sort(key=_attach_order)

    found = {item["detectedType"] for item in attachments}
    for doc_type in _REQUIRED:
        if doc_type not in found:
            warnings.append(f'Chưa có "{_ROUTES[doc_type]["name"]}" — mời bổ sung.')

    note = _suggest_note(note_sources)
    if bundle_notes:
        note = (note + " " if note else "") + "Hồ sơ đính kèm: " + " | ".join(bundle_notes) + "."
    if note:
        warnings.append(f"Ghi chú (Trích yếu nội dung hồ sơ) đề xuất: {note}")

    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    ocr_files = [item for item in raw_files if item.get("type") in _OCR_TYPES]
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
    llm_types: dict[int, str] = {}
    if llm_documents:
        try:
            llm_types = await _classify_with_llm(llm_documents, errors)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [item["name"] for item in raw_files],
            "ocrDocuments": [item.get("name") for item in ocr_results if item.get("text")],
            "llmDocuments": [raw_files[item["index"]]["name"] for item in llm_documents],
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

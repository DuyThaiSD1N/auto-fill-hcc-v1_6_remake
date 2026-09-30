"""Lập kế hoạch đính kèm "Đăng ký, cấp GCN đối với toàn bộ diện tích đất đang sử dụng (khoản 2 Điều 24
NĐ 101/2024) - Miền núi, hải đảo" tại Quảng Ninh (1.115841).

Cùng nền tảng với các thủ tục đất đai Quảng Ninh khác (React/Radix, modal "Danh sách tài liệu điện tử"
→ engine wallet-modal). Bảng thành phần hồ sơ có 6 hàng cố định; componentName là khóa chính (FE khớp
substring sau khi fold dấu), componentIndex (1-based) chỉ là gợi ý thứ tự DOM.

Hồ sơ thực tế hay quét GỘP: một PDF "phiếu đo đạc" chứa luôn bản photo GCN, đơn đăng ký QSDĐ cũ và văn
bản xác nhận nhà ở. File đó đính NGUYÊN vào hàng 3 (không tách trang); planner liệt kê các giấy tờ nằm
chung để cán bộ ghi vào ô "Ghi chú", kèm một câu trích yếu đề xuất đọc từ phiếu đo đạc/đơn.
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
_ASSET = "giay_to_tai_san"
_EXTRA_TYPES = {_AUTHORIZATION, _ASSET}   # không có hàng sẵn → "Thêm thành phần hồ sơ"
_REQUIRED = ("don_mau_18", "gcn_da_cap")

# 6 hàng thành phần hồ sơ trên cổng (thứ tự DOM).
_ROUTES: dict[str, dict[str, Any]] = {
    "don_mau_18": {
        "index": 1,
        "name": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18",
    },
    "gcn_da_cap": {
        "index": 2,
        "name": "Giấy chứng nhận đã cấp",
    },
    "giay_to_dien_tich_tang_them": {
        "index": 3,
        "name": "Giấy tờ chứng minh phần diện tích tăng thêm",
    },
    "to_khai_01_lptb": {
        "index": 4,
        "name": "Tờ khai lệ phí trước bạ theo Mẫu số 01/LPTB",
    },
    "to_khai_04_sddpnn": {
        "index": 5,
        "name": "Tờ khai thuế sử dụng đất phi nông nghiệp theo Mẫu số 04/TK-SDDPNN",
    },
    "to_khai_03_bds_tncn": {
        "index": 6,
        "name": "Tờ khai thuế thu nhập cá nhân theo Mẫu số 03/BĐS-TNCN",
    },
}
_ALLOWED = set(_ROUTES) | _EXTRA_TYPES | {"other"}

_DISPLAY = {
    "don_mau_18": "Đơn đăng ký biến động đất đai Mẫu số 18",
    "gcn_da_cap": "Giấy chứng nhận quyền sử dụng đất đã cấp",
    "giay_to_dien_tich_tang_them": "Giấy tờ chứng minh phần diện tích tăng thêm",
    "to_khai_01_lptb": "Tờ khai lệ phí trước bạ Mẫu số 01/LPTB",
    "to_khai_04_sddpnn": "Tờ khai thuế sử dụng đất phi nông nghiệp Mẫu số 04/TK-SDDPNN",
    "to_khai_03_bds_tncn": "Tờ khai thuế thu nhập cá nhân Mẫu số 03/BĐS-TNCN",
    _ASSET: "Giấy tờ về tài sản gắn liền với đất",
    _AUTHORIZATION: "Văn bản đại diện hoặc ủy quyền",
}

_MEASURE_MARKERS = (
    "phieu do dac chinh ly thua dat",
    "phieu xac nhan ket qua do dac hien trang thua dat",
    "ban mo ta ranh gioi, moc gioi thua dat",
    "manh trich do ban do dia chinh thua dat",
)
_DON_18_MARKER = "don dang ky bien dong dat dai, tai san gan lien voi dat"

# Giấy tờ hay bị quét CHUNG vào file phiếu đo đạc — chỉ để nhắc cán bộ ghi chú, không đổi hàng đính.
_BUNDLED_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("phiếu xác nhận kết quả đo đạc hiện trạng", ("phieu xac nhan ket qua do dac hien trang thua dat",)),
    ("bản mô tả ranh giới, mốc giới thửa đất", ("ban mo ta ranh gioi, moc gioi thua dat",)),
    ("bản photo Giấy chứng nhận đã cấp", ("nhung thay doi sau khi cap giay chung nhan", "so do dat cap")),
    ("đơn đăng ký quyền sử dụng đất cũ (nguồn gốc đất)", ("don xin dang ky quyen su dung dat",)),
    ("văn bản xác nhận về nhà ở (tài sản gắn liền với đất)", (
        "xac nhan thong tin ve nha o", "xac nhan ve quyen so huu nha o",
    )),
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

    if "03/bds-tncn" in folded:
        return "to_khai_03_bds_tncn"
    if "04/tk-sddpnn" in folded:
        return "to_khai_04_sddpnn"
    if "01/lptb" in folded:
        return "to_khai_01_lptb"

    # Đơn Mẫu 18 liệt kê "Phiếu đo đạc chỉnh lý..." ở mục IV → xét đơn TRƯỚC phiếu đo đạc.
    if _DON_18_MARKER in folded or ("mau so 18" in folded and "dang ky bien dong" in folded):
        return "don_mau_18"
    # Phiếu đo đạc ghi "Giấy chứng nhận QSD đất số seri..." và hay kèm bản photo GCN → xét TRƯỚC GCN.
    if any(marker in folded for marker in _MEASURE_MARKERS):
        return "giay_to_dien_tich_tang_them"
    if any(marker in folded for marker in ("giay uy quyen", "hop dong uy quyen", "van ban uy quyen")) or (
        "van ban ve viec dai dien" in folded and "phap luat ve dan su" in folded
    ):
        return _AUTHORIZATION
    if "giay chung nhan" in folded and any(
        marker in folded for marker in ("quyen su dung dat", "quyen so huu tai san gan lien voi dat")
    ):
        return "gcn_da_cap"
    if any(marker in folded for marker in ("xac nhan thong tin ve nha o", "giay phep xay dung")):
        return _ASSET
    return ""


def _bundled_documents(text: str) -> list[str]:
    """Các giấy tờ phụ nằm chung trong file (chỉ dùng để nhắc ghi chú)."""
    folded = _fold(text or "")
    return [label for label, markers in _BUNDLED_MARKERS if any(marker in folded for marker in markers)]


def _decimal(raw: str) -> str:
    value = raw.strip().rstrip(".,")
    return value.replace(".", ",") if re.fullmatch(r"\d+\.\d{1,2}", value) else value


def _to_float(raw: str) -> float | None:
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        return None


def _first(pattern: str, folded: str) -> str:
    match = re.search(pattern, folded)
    return match.group(1) if match else ""


def _suggest_note(texts: list[str]) -> str:
    """Câu trích yếu đề xuất cho ô Ghi chú, đọc từ phiếu đo đạc/đơn. Thiếu số thửa thì không đề xuất."""
    folded = " ".join(_fold(text) for text in texts if text)
    thua = _first(r"thua dat so\s*[:.]?\s*(\d+)", folded)
    if not thua:
        return ""
    to = _first(r"to ban do so\s*[:.]?\s*(\d+)", folded)
    cu = _first(r"dien tich tren giay to\s*[:.]?\s*(\d+(?:[.,]\d+)?)", folded)
    moi = _first(r"dien tich sau do dac,?\s*chinh ly\s*[:.]?\s*(\d+(?:[.,]\d+)?)", folded)
    seri = _first(r"seri\s*[:.]?\s*([a-z]{1,2}\s?\d{5,})", folded).upper()

    note = f"Đăng ký, cấp GCN QSDĐ đối với thửa đất số {thua}"
    if to:
        note += f", tờ bản đồ số {to}"
    if cu and moi:
        note += f" có phần diện tích tăng thêm ({_decimal(cu)} m² → {_decimal(moi)} m²"
        old, new = _to_float(cu), _to_float(moi)
        if old is not None and new is not None and new > old:
            note += f", tăng {_decimal(f'{new - old:.1f}')} m²"
        note += ") do thay đổi ranh giới"
    note += " so với GCN đã cấp"
    if seri:
        note += f" số seri {seri}"
    if "dang ky bo sung tai san gan lien voi dat" in folded:
        note += "; đăng ký bổ sung tài sản gắn liền với đất"
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
    if doc_type in _EXTRA_TYPES:
        return {
            **base,
            "componentName": _DISPLAY[doc_type],
            "target": "new",
            "needsAddComponent": True,
        }

    route = _ROUTES[doc_type]
    return {
        **base,
        "componentName": route["name"],
        "componentIndex": route["index"],
        "target": "existing",
        "needsAddComponent": False,
    }


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

        if doc_type in ("don_mau_18", "giay_to_dien_tich_tang_them"):
            note_sources.append(text)
        if doc_type == "giay_to_dien_tich_tang_them":
            bundled = _bundled_documents(text)
            if bundled:
                bundle_notes.append(f'file "{file_name}" gồm: {"; ".join(bundled)}')

        if doc_type in _ROUTES or doc_type in _EXTRA_TYPES:
            item = _build_item(file, index, doc_type)
            attachments.append(item)
            classified_item = {
                "fileName": file_name,
                "docType": doc_type,
                "source": source,
                "target": item["target"],
            }
            if "componentIndex" in item:
                classified_item["componentIndex"] = item["componentIndex"]
            classified.append(classified_item)
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

    found = {item["detectedType"] for item in attachments}
    for doc_type in _REQUIRED:
        if doc_type not in found:
            warnings.append(f'Chưa có "{_ROUTES[doc_type]["name"]}" (hàng {_ROUTES[doc_type]["index"]}) — mời bổ sung.')

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

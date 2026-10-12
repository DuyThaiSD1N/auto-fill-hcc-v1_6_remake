"""Lập kế hoạch đính kèm "[Đặc thù] Đăng ký biến động chuyển mục đích sử dụng đất không phải xin phép cơ quan
nhà nước có thẩm quyền - Đối với cá nhân, cộng đồng dân cư, người gốc Việt Nam định cư ở nước ngoài - Miền
núi, hải đảo" tại Quảng Ninh (1.115846).

Cùng nền tảng với các thủ tục đất đai Quảng Ninh khác (React/Radix, modal "Danh sách tài liệu điện tử"
→ engine wallet-modal). Bảng thành phần hồ sơ có 4 hàng cố định; componentName là khóa chính (FE khớp
substring sau khi fold dấu), componentIndex (1-based) chỉ là gợi ý thứ tự DOM:
  [1] Mảnh trích đo bản đồ địa chính (chỉ khi có nhu cầu đo đạc lại)
  [2] Văn bản về việc đại diện (chỉ khi nộp qua người đại diện)
  [3] Giấy chứng nhận đã cấp
  [4] Đơn đăng ký biến động Mẫu số 18  ← đính kèm chung các tờ khai nghĩa vụ tài chính
Danh mục KHÔNG có dòng riêng cho tờ khai thuế sử dụng đất nông nghiệp / lệ phí trước bạ / thuế phi nông
nghiệp / TNCN, nên các tờ khai đó đính CHUNG hàng 4 sau Đơn (giữ nguyên từng tệp, không tách, không gộp).
Planner đề xuất câu trích yếu cho ô "Ghi chú", đọc từ Đơn + GCN + tờ khai. Thủ tục chỉ đính kèm, không điền.
"""

import asyncio
import re
import time
import unicodedata
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import sanitize_wallet_document_label as _wallet_label
from app.process.schemas import FileItem
from app.services.llm import client
from app.services.pdf_utils import trim_files_for_classify

from .prompt import SYSTEM_PROMPT, build_user_prompt


def _derive_component_name(file_name: str) -> str:
    """Tên thành phần hồ sơ MỚI cho giấy tờ ngoài danh mục — lấy theo tên file (bỏ đuôi, gạch dưới→cách)."""
    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", str(file_name or "")).strip()
    stem = re.sub(r"[_]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem or "Tài liệu khác kèm theo"


_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
# PDF gộp nhiều trang OCR đủ thì quá timeout 100s của extension; loại giấy tờ và số thửa/tờ/seri đều ở
# trang 1-2 → chỉ OCR 2 trang đầu; tệp đính lên cổng vẫn là bản gốc đủ trang.
_OCR_MAX_PAGES = 2
_LOAI_BAN = "Bản chính"
_REQUIRED = ("gcn_da_cap", "don_mau_18")

# 4 hàng thành phần hồ sơ trên cổng (thứ tự DOM).
_ROW_MANH_TRICH_DO = {
    "index": 1,
    "name": "Mảnh trích đo bản đồ địa chính thửa đất đối với trường hợp người sử dụng đất có nhu cầu đo đạc",
}
_ROW_DAI_DIEN = {
    "index": 2,
    "name": "Văn bản về việc đại diện theo quy định của pháp luật về dân sự",
}
_ROW_GCN = {
    "index": 3,
    "name": "Giấy chứng nhận đã cấp",
}
_ROW_DON = {
    "index": 4,
    "name": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18",
}
_ROUTES: dict[str, dict[str, Any]] = {
    "manh_trich_do": _ROW_MANH_TRICH_DO,
    "van_ban_dai_dien": _ROW_DAI_DIEN,
    "gcn_da_cap": _ROW_GCN,
    "don_mau_18": _ROW_DON,
    # Tờ khai nghĩa vụ tài chính không có dòng riêng → đính kèm chung dòng Đơn.
    "to_khai_02_sddnn": _ROW_DON,
    "to_khai_01_lptb": _ROW_DON,
    "to_khai_sddpnn": _ROW_DON,
    "to_khai_03_bds_tncn": _ROW_DON,
}
_TAX_FORMS = ("to_khai_02_sddnn", "to_khai_01_lptb", "to_khai_sddpnn", "to_khai_03_bds_tncn")
_ALLOWED = set(_ROUTES) | {"other"}
# Thứ tự trong cùng hàng 4: Đơn trước, tờ khai sau.
_ROW_ORDER = {"don_mau_18": 0, **{doc_type: order for order, doc_type in enumerate(_TAX_FORMS, start=1)}}

_DISPLAY = {
    "manh_trich_do": "Mảnh trích đo bản đồ địa chính thửa đất",
    "van_ban_dai_dien": "Văn bản đại diện hoặc ủy quyền",
    "gcn_da_cap": "Giấy chứng nhận đã cấp",
    "don_mau_18": "Đơn đăng ký biến động đất đai Mẫu số 18",
    "to_khai_02_sddnn": "Tờ khai thuế sử dụng đất nông nghiệp Mẫu 02/SDDNN",
    "to_khai_01_lptb": "Tờ khai lệ phí trước bạ Mẫu 01/LPTB",
    "to_khai_sddpnn": "Tờ khai thuế sử dụng đất phi nông nghiệp",
    "to_khai_03_bds_tncn": "Tờ khai thuế thu nhập cá nhân Mẫu 03/BĐS-TNCN",
}

_MEASURE_MARKERS = (
    "manh trich do ban do dia chinh",
    "phieu do dac chinh ly thua dat",
    "phieu xac nhan ket qua do dac hien trang thua dat",
    "ban mo ta ranh gioi, moc gioi thua dat",
)
_DON_18_MARKER = "don dang ky bien dong dat dai, tai san gan lien voi dat"
_AUTHORIZATION_MARKERS = ("giay uy quyen", "hop dong uy quyen", "van ban uy quyen", "van ban dai dien")


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

    # Tờ khai ghi số thửa, số GCN, "Đất trồng cây lâu năm"... → xét mã mẫu TRƯỚC.
    if "02/sddnn" in folded or "to khai thue su dung dat nong nghiep" in folded:
        return "to_khai_02_sddnn"
    if "03/bds-tncn" in folded:
        return "to_khai_03_bds_tncn"
    if "tk-sddpnn" in folded:
        return "to_khai_sddpnn"
    if "01/lptb" in folded or "to khai le phi truoc ba" in folded:
        return "to_khai_01_lptb"

    # Đơn Mẫu 18 nhắc "Giấy chứng nhận ... số seri" và "Bản gốc Giấy chứng nhận đã cấp" → xét TRƯỚC GCN.
    if _DON_18_MARKER in folded or ("mau so 18" in folded and "dang ky bien dong" in folded):
        return "don_mau_18"
    if any(marker in folded for marker in _MEASURE_MARKERS):
        return "manh_trich_do"
    if any(marker in folded[:400] for marker in _AUTHORIZATION_MARKERS):
        return "van_ban_dai_dien"
    if "giay chung nhan" in folded and "quyen su dung dat" in folded:
        return "gcn_da_cap"
    return ""


def _first(pattern: str, text: str, flags: int = 0) -> str:
    match = re.search(pattern, text, flags)
    return match.group(1) if match else ""


def _noi_dung_bien_dong(text: str) -> str:
    """Mục II của Đơn Mẫu 18, bỏ phần "tại Giấy chứng nhận ..." (seri ghi riêng)."""
    content = _first(
        r"N[ộo]i dung bi[ếe]n đ[ộo]ng[^:\n]{0,12}:\s*(.+?)(?:\s+t[ạa]i\s+Gi[ấa]y ch[ứu]ng nh[ậa]n|\s*III\s*\.|$)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    content = re.sub(r"\s+", " ", content).strip(" .,;:-")
    return content[:200]


def _chu_su_dung(text: str) -> str:
    """Dòng "Tên(2): Ông ..., sinh năm ...; Bà ..." của Đơn Mẫu 18 → "Ông ..., Bà ..." (viết hoa đầu chữ)."""
    raw = _first(r"\bT[êe]n\b[^:\n]{0,10}:\s*([^\n]+)", text, re.IGNORECASE)
    names = []
    for part in raw.split(";"):
        name = re.sub(r",?\s*sinh n[ăa]m.*$", "", part, flags=re.IGNORECASE).strip(" .,-")
        if name:
            names.append(name.title())
    return ", ".join(names)


def _suggest_note(don_text: str, other_texts: list[str]) -> str:
    """Câu trích yếu đề xuất cho ô Ghi chú. Không đọc được nội dung biến động lẫn số thửa thì không đề xuất."""
    don = unicodedata.normalize("NFC", don_text or "")
    folded = " ".join(_fold(text) for text in [don, *other_texts] if text)
    noi_dung = _noi_dung_bien_dong(don)
    thua = _first(r"thua dat so(?:\s*\([^)]*\))?\s*[:.]?\s*(\d+)", folded)
    if not noi_dung and not thua:
        return ""
    to = _first(r"to ban do so\s*[:.]?\s*(\d+)", folded)
    seri = _first(r"seri\s*[:.]?\s*([a-z]{1,2}\s?\d{5,})", folded).upper()

    parts = [noi_dung or "Chuyển mục đích sử dụng đất"]
    if thua:
        parts.append(f"thửa {thua}" + (f", tờ BĐ {to}" if to else ""))
    if seri:
        parts.append(f"GCN seri {seri}")
    owners = _chu_su_dung(don)
    if owners:
        parts.append(owners)
    return " – ".join(parts) + "."


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
    route = _ROUTES[doc_type]
    return {
        "fileIndex": file_index,
        "fileName": str(file.get("name") or f"file-{file_index + 1}"),
        "documentName": _wallet_label(_DISPLAY[doc_type]),
        "loaiBan": _LOAI_BAN,
        "detectedType": doc_type,
        "componentName": route["name"],
        "componentIndex": route["index"],
        "target": "existing",
        "needsAddComponent": False,
    }


def _sort_key(item: dict) -> tuple[int, int, int]:
    # Hàng theo thứ tự DOM, dòng mới cuối cùng; trong hàng 4 Đơn trước, tờ khai sau.
    return (
        int(item.get("componentIndex") or 99),
        _ROW_ORDER.get(item["detectedType"], 0),
        int(item["fileIndex"]),
    )


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
    don_text = ""
    note_sources: list[str] = []

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        text = str(ocr_by_name.get(file_name, {}).get("text") or "")
        llm_type = llm_types.get(index, "")
        rule_type = _rule_doc_type(text)

        if llm_type in _ROUTES:
            doc_type, source = llm_type, "llm"
        elif rule_type in _ROUTES:
            doc_type, source = rule_type, "rule"
        else:
            doc_type, source = "other", "llm" if llm_type == "other" else "unknown"

        if doc_type == "don_mau_18" and not don_text:
            don_text = text
        elif doc_type in ("gcn_da_cap", "manh_trich_do", *_TAX_FORMS):
            note_sources.append(text)

        if doc_type in _ROUTES:
            item = _build_item(file, index, doc_type)
            attachments.append(item)
            classified.append({
                "fileName": file_name,
                "docType": doc_type,
                "source": source,
                "target": item["target"],
                "componentIndex": item["componentIndex"],
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

    attachments.sort(key=_sort_key)

    found = {item["detectedType"] for item in attachments}
    for doc_type in _REQUIRED:
        if doc_type not in found:
            warnings.append(f'Chưa có "{_ROUTES[doc_type]["name"]}" (hàng {_ROUTES[doc_type]["index"]}) — mời bổ sung.')

    tax_files = [item for item in attachments if item["detectedType"] in _TAX_FORMS]
    if tax_files:
        listed = "; ".join(f'{item["fileName"]} ({_DISPLAY[item["detectedType"]]})' for item in tax_files)
        warnings.append(
            f"Hàng 4 đính kèm chung {len(tax_files)} tờ khai cùng Đơn Mẫu 18: {listed}. Lý do: danh mục không "
            "có dòng riêng cho tờ khai nghĩa vụ tài chính."
        )

    note = _suggest_note(don_text, note_sources)
    if note:
        warnings.append(f"Ghi chú (Trích yếu nội dung hồ sơ) đề xuất: {note}")

    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    ocr_files = trim_files_for_classify(
        [item for item in raw_files if item.get("type") in _OCR_TYPES], _OCR_MAX_PAGES
    )
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

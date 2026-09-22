"""Đính kèm [Lào Cai] tặng cho quyền sử dụng đất mở rộng đường giao thông (1.115690) — eForm iGate.

⚑ THỦ TỤC NÀY KHÔNG CÓ BẢNG "THÀNH PHẦN HỒ SƠ". Ảnh ánh xạ đính kèm của bộ phận một cửa cho thấy
khối "Thành phần hồ sơ" chỉ in đúng một dòng chữ "(Hồ sơ không yêu cầu giấy tờ kèm theo)" — không có
dòng nào để tích, không có ô upload cố định nào. Toàn bộ chỗ đính kèm nằm ở khối "Thông tin khác"
bên dưới, gồm danh sách "Giấy tờ khác": mỗi dòng là select "Mới" + ô gõ TÊN MÔ TẢ + nút "Chọn tệp
tin", kèm nút "+" để thêm dòng.

Vì vậy planner KHÔNG dùng engine `fixed-slot` (như 1.115678) mà phát `target: "new"` +
`needsAddComponent: True` — đúng nhánh `attachOneFileToOtherListFile` của content.js: FE lấy dòng
"Giấy tờ khác" còn trống (hoặc bấm "+" thêm dòng), gõ `componentName` vào ô tên rồi bơm tệp vào
input file của CHÍNH dòng đó. Mỗi tệp một dòng, nên `documentName` phải là tên giấy tờ đọc được chứ
không phải tên file thô.

`noChooserClick=True` là BẮT BUỘC với cổng iGate VNPT: bấm option "Chọn tệp tin" ở đây MỞ HỘP THOẠI
FILE CỦA HỆ ĐIỀU HÀNH và chặn UI — FE phải gán thẳng bằng DataTransfer.

⚑ KHÔNG BỎ SÓT TỆP NÀO, và KHÔNG TÁCH SANG "THÀNH PHẦN HỒ SƠ". Ảnh ánh xạ ghi rõ ba điều: cả ba tệp
đều đính vào mục "Giấy tờ khác"; không tách sang mục Thành phần hồ sơ; không được bỏ sót file đính
kèm chung. Nên ở đây KHÔNG có `SKIPPED_LABELS` — kể cả CCCD (thứ mà nhiều thủ tục khác loại ra) vẫn
được đính, chỉ kèm cảnh báo để cán bộ tự quyết.

Phân loại THUẦN LLM (không lưới keyword). Tài liệu chưa rõ loại vẫn xuống "Giấy tờ khác" với tên đọc
từ tên tệp, kèm cảnh báo.
"""

import asyncio
import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold, normalize_document_name
from app.pipelines._shared.documents import join_ocr_documents
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# Trần dung lượng MỘT tệp của cổng, ghi ngay trên trang: "Tệp tin tải lên có dung lượng không quá 6MB".
_MAX_FILE_BYTES = 6 * 1024 * 1024

# docType → TÊN MÔ TẢ gõ vào ô tên của dòng "Giấy tờ khác". Ba tên đầu lấy NGUYÊN VĂN theo ảnh ánh
# xạ đính kèm ("Tên mô tả cần nhập: Văn bản tặng cho quyền sử dụng đất, Giấy ủy quyền, Giấy chứng
# nhận quyền sử dụng đất") — đổi chữ ở đây là lệch khỏi hướng dẫn của bộ phận một cửa.
_DISPLAY: dict[str, str] = {
    "van_ban_tang_cho": "Văn bản tặng cho quyền sử dụng đất",
    "giay_uy_quyen": "Giấy ủy quyền",
    "gcn_qsdd": "Giấy chứng nhận quyền sử dụng đất",
    "giay_to_tuy_than": "Giấy tờ tùy thân",
    "so_do_trich_do": "Sơ đồ, trích đo địa chính thửa đất",
    "van_ban_ubnd": "Văn bản của cơ quan nhà nước",
}
_ALLOWED = set(_DISPLAY) | {"other"}

# Ba giấy tờ làm nên bộ hồ sơ của thủ tục này; thiếu cái nào thì cảnh báo trước khi nộp.
_CORE_TYPES: tuple[tuple[str, str], ...] = (
    ("van_ban_tang_cho", "Văn bản tặng cho quyền sử dụng đất (đơn hiến đất)"),
    ("giay_uy_quyen", "Giấy ủy quyền có công chứng"),
    ("gcn_qsdd", "Giấy chứng nhận quyền sử dụng đất"),
)

_OTHER_DISPLAY = "Tài liệu khác"


def _canon(value: Any) -> str:
    return re.sub(r"[_\-\s]+", "_", fold(value)).strip("_")


def _normalize_doc_type(value: Any) -> str:
    canon = _canon(value)
    for doc_type in _ALLOWED:
        if canon == _canon(doc_type):
            return doc_type
    return "other"


def _data_url_size(data_url: Any) -> int:
    """Kích thước thật của tệp, suy từ độ dài phần base64 (FileItem không mang size)."""
    payload = re.sub(r"\s+", "", str(data_url or "").partition(",")[2])
    if not payload:
        return 0
    padding = len(payload) - len(payload.rstrip("="))
    return max(0, (len(payload) * 3) // 4 - padding)


def _mb(size: int) -> str:
    return f"{size / 1024 / 1024:.2f} MB"


def _other_display(file_name: str) -> str:
    """Tài liệu chưa rõ loại giữ TÊN THẬT theo tệp để cán bộ biết là giấy gì."""
    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", str(file_name or "")).strip()
    stem = re.sub(r"[_]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return normalize_document_name(stem, _OTHER_DISPLAY) if stem else _OTHER_DISPLAY


def _unique_name(base: str, used: set[str]) -> str:
    """Hai tệp cùng loại thì tên dòng phải khác nhau, nếu không cán bộ không biết dòng nào là dòng nào."""
    key = fold(base)
    if key and key not in used:
        used.add(key)
        return base
    suffix = 2
    while True:
        candidate = f"{base} ({suffix})"
        if fold(candidate) not in used:
            used.add(fold(candidate))
            return candidate
        suffix += 1


async def _classify_one(document: dict[str, Any]) -> tuple[int, str]:
    index = int(document.get("index"))
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(
            [{"index": index, "text": str(document.get("text") or "")[:12000]}]
        )},
    ]
    raw = await client.chat(messages, max_tokens=120, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw) or {}
    first = next(iter(parsed.get("documents", []) or []), {})
    return index, _normalize_doc_type(first.get("docType") or first.get("type"))


async def _classify_with_llm(
    documents: list[dict[str, Any]],
    errors: list[str] | None = None,
) -> dict[int, str]:
    if not documents:
        return {}
    # Một call cho mỗi file: PDF dài hoặc lỗi provider chỉ làm file đó rơi về other, không kéo cả mẻ.
    outcomes = await asyncio.gather(*(_classify_one(d) for d in documents), return_exceptions=True)
    result: dict[int, str] = {}
    for document, outcome in zip(documents, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            if errors is not None:
                errors.append(f"attachment_agent file {document.get('index')}: {outcome}")
            continue
        index, doc_type = outcome
        result[index] = doc_type
    return result


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    unknown: list[str] = []
    used_names: set[str] = set()
    seen_types: set[str] = set()

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        llm_type = llm_types.get(index, "")
        doc_type = llm_type if llm_type in _ALLOWED else "other"
        source = "llm" if llm_type else "default"
        seen_types.add(doc_type)

        if doc_type == "other":
            document_name = _unique_name(_other_display(file_name), used_names)
            unknown.append(file_name)
        else:
            document_name = _unique_name(_DISPLAY[doc_type], used_names)

        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": document_name,
            # FE gõ componentName vào ô tên của dòng "Giấy tờ khác" → phải là TÊN GIẤY TỜ.
            "componentName": document_name,
            "target": "new",
            "needsAddComponent": True,
            "detectedType": doc_type,
            # Cổng iGate VNPT: bấm option "Chọn tệp tin" mở hộp thoại file của hệ điều hành → gán thẳng.
            "noChooserClick": True,
        })
        classified.append({
            "fileName": file_name,
            "docType": doc_type,
            "source": source,
            "documentName": document_name,
            "target": "new",
        })

    thieu = [nhan for doc_type, nhan in _CORE_TYPES if doc_type not in seen_types]
    if thieu:
        warnings.append(
            "Chưa thấy trong bộ tệp đã tải lên: " + "; ".join(thieu) + ". Đây là các giấy tờ chính của "
            "hồ sơ hiến đất — cán bộ kiểm tra lại, nếu thiếu thật thì bổ sung trước khi nộp."
        )
    if "giay_to_tuy_than" in seen_types:
        warnings.append(
            "Có tệp là giấy tờ tùy thân (CCCD/CMND). Hướng dẫn ánh xạ của thủ tục này yêu cầu KHÔNG bỏ "
            "sót tệp nào nên hệ thống vẫn đính vào \"Giấy tờ khác\" — cán bộ tự quyết có giữ lại không."
        )
    if unknown:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã đính vào \"Giấy tờ khác\" với tên lấy theo tên tệp để không "
            f"bỏ sót — cán bộ sửa lại tên mô tả nếu cần: {', '.join(unknown)}."
        )
    if attachments:
        warnings.append(
            "Thủ tục này KHÔNG có bảng \"Thành phần hồ sơ\" (cổng ghi \"Hồ sơ không yêu cầu giấy tờ kèm "
            f"theo\") nên cả {len(attachments)} tệp đều được đính vào mục \"Giấy tờ khác\", mỗi tệp một "
            "dòng kèm tên mô tả. TUYỆT ĐỐI không tách bớt tệp sang chỗ khác."
        )

    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    errors: list[str] = []

    # Trần 6 MB tính cho TỪNG TỆP (mỗi tệp một dòng riêng), khác 1.115678 nơi cả bộ dồn vào một dòng.
    valid_files: list[dict] = []
    for file in raw_files:
        size = _data_url_size(file.get("dataUrl"))
        if size > _MAX_FILE_BYTES:
            errors.append(
                f"File '{file['name']}' vượt quá 6 MB ({_mb(size)}) — cổng Lào Cai không nhận, đã bỏ "
                "qua. Hãy nén PDF hoặc quét lại ở DPI thấp hơn rồi đính bổ sung."
            )
        else:
            valid_files.append(file)

    from app.services import ocr

    ocr_files = [f for f in valid_files if f.get("type") in _OCR_TYPES]
    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    by_name = {item.get("name"): item for item in ocr_results}
    llm_documents = [
        {"index": index, "text": str(by_name.get(file.get("name"), {}).get("text") or "")}
        for index, file in enumerate(valid_files)
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

    attachments, warnings, classified = build_plan_items(valid_files, llm_types)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [valid_files[d["index"]]["name"] for d in llm_documents],
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "ocr_text": join_ocr_documents(ocr_results),
        "errors": errors,
    }

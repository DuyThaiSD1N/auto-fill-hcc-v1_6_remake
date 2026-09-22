"""Đính kèm [Lào Cai] 1.115693 — TOÀN BỘ hồ sơ đi vào mục "Giấy tờ khác" (danh sách dòng động).

⚑ KHÁC HẲN 1.115694 VÀ CÁC THỦ TỤC ĐẤT ĐAI KHÁC CỦA CÙNG CỔNG: bước "Thành phần hồ sơ" của thủ tục
này KHÔNG có bảng dòng cố định. Theo ảnh ánh xạ hồ sơ mẫu, khối "Biểu mẫu giấy tờ" chỉ ghi đúng một
dòng "(Hồ sơ không yêu cầu giấy tờ kèm theo)" — tức là không có ô upload nào được đánh sẵn tên giấy
tờ. Mọi tài liệu phải tự thêm dòng trong mục "Giấy tờ khác": mỗi dòng gồm cột "Loại" (giữ nguyên giá
trị mặc định "Mới"), ô TÊN GIẤY TỜ do người nộp tự gõ, nút "+/-" để thêm/bớt dòng và nút "Chọn tệp
tin".

Vì vậy mọi item đều là `target: "new"` + `needsAddComponent: True`; engine FE xử lý bằng
`attachOneFileToOtherListFile` (content.js): tìm dòng trống trong `#_fcgiayToKhac`, hết dòng thì bấm
nút `.act.add` để thêm dòng mới, gõ `componentName` vào ô tên rồi gán tệp vào
`input[name^="HoSoOnline_giayToKhac_file_"]`.

⚠ `componentName` CHÍNH LÀ TÊN GIẤY TỜ hiện trên hồ sơ nộp — không phải nhãn nội bộ. Hai item trùng
tên sẽ ghi đè nhau trong ô tên nên `_unique_document_name` thêm hậu tố "(2)", "(3)"…

⚠ `noChooserClick: True` (bắt buộc với cổng iGate VNPT): bấm option "Chọn tệp tin" ở đây MỞ HỘP THOẠI
FILE của hệ điều hành và chặn UI. FE gán thẳng vào input, gán hụt thì bỏ qua tệp đó chứ không bấm.

⚠ Ô "Giấy tờ khác — Chọn tệp tin" ĐỨNG RIÊNG ở cuối trang (dưới bảng) phải ĐỂ TRỐNG, đúng như ảnh ánh
xạ. Không cần xử lý gì: ô đó không nằm trong một `li` có `input[name="HoSoOnline_giayToKhac[]"]` nên
`otherListFileRows()` không bao giờ chọn tới.

⚑ MỘT TỆP ↔ MỘT DÒNG. Hồ sơ mẫu là một file scan 17 trang được tách thành 5 tệp PDF, mỗi tệp dưới 6 MB
và mỗi tệp một dòng; có tệp cố ý gộp nhiều giấy tờ cùng nhóm (phiếu đo đạc + bản mô tả ranh giới; ba
tờ khai thuế). Planner KHÔNG cắt trang bằng sourceSegments — cắt sai là mất giấy tờ — và không đính
một tệp vào hai dòng.

Phân loại THUẦN LLM (không lưới keyword), mỗi file một call để PDF dài hoặc lỗi provider chỉ làm file
đó rơi về "khac". Không rõ loại vẫn được thêm dòng với tên lấy theo tên tệp — tuyệt đối không bỏ sót.
"""

import asyncio
import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import normalize_document_name
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# Cổng ghi rõ ngay trên trang: "Tệp tin tải lên có dung lượng không quá 6MB".
_MAX_FILE_BYTES = 6 * 1024 * 1024

_OTHER = "khac"

# docType (LLM) → TÊN GIẤY TỜ gõ vào ô tên của dòng "Giấy tờ khác".
# Tên lấy nguyên theo cột "Tên giấy tờ nhập" của ảnh ánh xạ hồ sơ mẫu, có mở rộng cho các giấy tờ
# ảnh ánh xạ ghi là "CHƯA CÓ TRONG FILE SCAN" (GCN gốc, giấy ủy quyền, giấy tờ nhận chuyển quyền) —
# hồ sơ đầy đủ sẽ có chúng và cần đúng tên dòng ngay.
_ROUTES: dict[str, str] = {
    "don_bien_dong": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất",
    "gcn": "Giấy chứng nhận quyền sử dụng đất đã cấp",
    "phieu_do_dac": "Phiếu đo đạc chỉnh lý thửa đất kèm Bản mô tả ranh giới, mốc giới thửa đất",
    "bien_ban_ranh_gioi": "Biên bản làm việc xác nhận ranh giới, mốc giới và hiện trạng sử dụng đất",
    "giay_cam_ket_chu_ky": "Giấy cam kết xác nhận chữ ký",
    "van_ban_dai_dien": "Giấy ủy quyền (văn bản về việc đại diện)",
    "giay_to_chuyen_quyen": "Giấy tờ về việc nhận chuyển quyền phần diện tích tăng thêm",
    "to_khai_thue": "Tờ khai lệ phí trước bạ, Tờ khai tiền sử dụng đất, Tờ khai thuế SDĐ phi nông nghiệp",
    "giay_to_nhan_than": "Căn cước công dân của người sử dụng đất",
}
_ALLOWED = set(_ROUTES) | {_OTHER}

# THÀNH PHẦN HỒ SƠ CHÍNH theo ảnh hướng dẫn ánh xạ (cột "TP"). Thiếu thì phải nhắc cán bộ, không im
# lặng — ảnh ánh xạ ghi rõ "cần bổ sung trước khi nộp (không tự tạo tệp thay thế)".
_THANH_PHAN_CHINH: dict[str, str] = {
    "don_bien_dong": "TP 1 — Đơn đăng ký biến động đất đai, tài sản gắn liền với đất",
    "gcn": "TP 2 — Bản gốc Giấy chứng nhận đã cấp cho thửa đất gốc",
    "phieu_do_dac": "TP 3 — Mảnh trích đo/phiếu đo đạc chỉnh lý bản đồ địa chính thửa đất",
    "bien_ban_ranh_gioi": "TP 4 — Giấy tờ chứng minh phần diện tích tăng thêm (biên bản xác nhận ranh giới)",
}

# Giấy tờ chỉ bắt buộc khi hồ sơ NỘP THAY. Có giấy cam kết xác nhận chữ ký (người được ủy quyền tự
# lập) mà KHÔNG có bản ủy quyền là tình huống đã gặp trong hồ sơ mẫu → nhắc đúng chỗ đó.
_UY_QUYEN = "van_ban_dai_dien"
_CAM_KET = "giay_cam_ket_chu_ky"


def _fold(value: Any) -> str:
    import unicodedata

    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _canon(value: Any) -> str:
    return re.sub(r"[_\-\s]+", "_", _fold(value)).strip("_")


def _normalize_doc_type(value: Any) -> str:
    canon = _canon(value)
    for doc_type in _ALLOWED:
        if canon == _canon(doc_type):
            return doc_type
    return _OTHER


def _data_url_size(data_url: Any) -> int:
    """Kích thước thật của tệp, suy từ độ dài phần base64 (FileItem không mang size)."""
    payload = re.sub(r"\s+", "", str(data_url or "").partition(",")[2])
    if not payload:
        return 0
    padding = len(payload) - len(payload.rstrip("="))
    return max(0, (len(payload) * 3) // 4 - padding)


def _other_display(file_name: str) -> str:
    """Tài liệu chưa rõ loại giữ TÊN THẬT theo tệp để cán bộ biết là giấy gì."""
    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", str(file_name or "")).strip()
    stem = re.sub(r"[_]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return normalize_document_name(stem, "Tài liệu kèm theo") if stem else "Tài liệu kèm theo"


def _unique_document_name(base: str, used: set[str]) -> str:
    """documentName thành TÊN DÒNG ở "Giấy tờ khác" → hai dòng trùng tên sẽ đè nhau."""
    key = _fold(base)
    if key and key not in used:
        used.add(key)
        return base
    suffix = 2
    while True:
        candidate = f"{base} ({suffix})"
        if _fold(candidate) not in used:
            used.add(_fold(candidate))
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
    parsed = client.extract_json_block(raw)
    first = next(iter(parsed.get("documents", []) or []), {})
    return index, _normalize_doc_type(first.get("docType") or first.get("type"))


async def _classify_with_llm(
    documents: list[dict[str, Any]],
    errors: list[str] | None = None,
) -> dict[int, str]:
    if not documents:
        return {}
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

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        llm_type = llm_types.get(index, "")
        doc_type = llm_type if llm_type in _ALLOWED else _OTHER
        source = "llm" if llm_type else "default"

        if doc_type == _OTHER:
            unknown.append(file_name)
            base_name = _other_display(file_name)
        else:
            base_name = _ROUTES[doc_type]
        document_name = _unique_document_name(base_name, used_names)

        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": document_name,
            # componentName là thứ FE gõ vào ô tên của dòng → phải bằng documentName.
            "componentName": document_name,
            "target": "new",
            "needsAddComponent": True,
            "noChooserClick": True,
            "detectedType": doc_type,
        })
        classified.append({
            "fileName": file_name, "docType": doc_type, "source": source, "slotIndex": None,
        })

    if unknown:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã thêm dòng \"Giấy tờ khác\" theo tên tệp để không bỏ sót — "
            f"cán bộ sửa lại tên dòng cho đúng: {', '.join(unknown)}."
        )

    have_types = {item["detectedType"] for item in attachments}
    thieu = [mo_ta for doc_type, mo_ta in _THANH_PHAN_CHINH.items() if doc_type not in have_types]
    if thieu:
        warnings.append(
            "Chưa có tệp cho thành phần hồ sơ chính: " + "; ".join(thieu) + ". Cổng không chặn nhưng "
            "nơi tiếp nhận sẽ trả hồ sơ — cán bộ đề nghị người dân bổ sung bản scan rồi bấm \"+\" thêm "
            "dòng trong \"Giấy tờ khác\". KHÔNG tự tạo tệp thay thế."
        )

    if _CAM_KET in have_types and _UY_QUYEN not in have_types:
        warnings.append(
            "Hồ sơ có Giấy cam kết xác nhận chữ ký của người được ủy quyền nhưng KHÔNG có bản scan của "
            "chính Giấy ủy quyền. Giấy cam kết chỉ là giấy bổ trợ, không thay được văn bản về việc đại "
            "diện — cán bộ yêu cầu bổ sung bản ủy quyền công chứng trước khi nộp."
        )

    if not attachments:
        warnings.append("Không có tài liệu nào để đính kèm.")
    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]

    # Trần 6 MB tính cho TỪNG TỆP (mỗi tệp một dòng). Hồ sơ scan đất đai rất hay vượt: ảnh ánh xạ
    # khuyên giảm còn 300 dpi hoặc tách tệp. Cổng chỉ báo lỗi lúc bấm nộp nên phải nói sớm.
    valid_files: list[dict] = []
    for file in raw_files:
        size = _data_url_size(file.get("dataUrl"))
        if size > _MAX_FILE_BYTES:
            errors.append(
                f"File '{file['name']}' vượt quá 6 MB ({size / 1024 / 1024:.2f} MB) — cổng không nhận, "
                "đã bỏ qua. Nén PDF (giảm ảnh quét về 300 dpi) hoặc tách thành nhiều tệp rồi đính lại."
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
        "errors": errors,
    }

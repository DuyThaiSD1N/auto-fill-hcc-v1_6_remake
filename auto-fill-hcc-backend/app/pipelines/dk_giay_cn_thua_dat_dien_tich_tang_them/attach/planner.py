"""Đính kèm [Lào Cai] 1.115694 — bảng "Thành phần hồ sơ" bước 3 của cổng `dichvucong.laocai.gov.vn`.

Bảng PHẲNG (không chia nhánh a/b như 1.115667-1.115668), đúng 5 dòng theo thứ tự DOM; mỗi dòng có
checkbox chọn giấy tờ + ô "Số bản" + nút "Chọn tệp tin":

  0. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 24 (QĐ 47/2026/QĐ-UBND)
  1. Giấy chứng nhận đã cấp
  2. Giấy tờ về việc nhận chuyển quyền sử dụng đất đối với phần diện tích tăng thêm
  3. Mảnh trích đo bản đồ địa chính thửa đất
  4. Văn bản về việc đại diện theo quy định của pháp luật về dân sự …

Bên dưới là khối "Thành phần hồ sơ khác nếu có" → danh sách "Giấy tờ khác" (tên tự nhập + chọn tệp).

⚑ KHỚP Ô THEO `slotIndex`, KHÔNG theo keyword: bảng phẳng nên engine FE chỉ tra keyword khi slotKey có
mặt trong `FIXED_SLOT_KEYWORDS` của content.js. slotKey ở đây CỐ Ý không nằm trong bảng đó (giống
`giao_thue_dat_lao_cai`) để FE dùng thẳng thứ tự DOM — vừa khỏi phải sửa extension, vừa tránh nhầm giữa
dòng 2 ("…nhận chuyển quyền sử dụng đất…") và dòng 4 ("…thực hiện thủ tục đăng ký đất đai…") vốn dùng
chung rất nhiều từ.

`tickRow: True` vì cột "#" của mỗi dòng là checkbox chọn giấy tờ — không tích thì cổng không nhận tệp.

NHIỀU TỆP MỘT DÒNG LÀ HỢP LỆ: engine gom các item cùng `slotKey` rồi bơm cả loạt vào một ô (xem
`attachFilesByFixedSlot`). Nhờ vậy hợp đồng chuyển nhượng + chứng từ thanh toán cùng vào dòng 2 đúng
như ảnh ánh xạ. Nhưng MỘT TỆP chỉ đi ĐÚNG MỘT DÒNG: không đính một tệp vào hai dòng (số lượt đính > số
tệp làm extension báo "6/5 file"), cũng KHÔNG cắt trang bằng sourceSegments — cắt sai là mất giấy tờ.

Hệ quả đã biết của quy tắc trên (đúng như ảnh ánh xạ hồ sơ mẫu): file Đơn quét gộp cả 2 tờ khai thuế,
file Giấy ủy quyền quét gộp cả CCCD + giấy chứng nhận kết hôn. Các giấy tờ đi ghép đó nằm cùng dòng với
giấy tờ chính chứ không tách xuống "Giấy tờ khác" — planner phát cảnh báo để cán bộ tự quyết.

Phân loại THUẦN LLM (không lưới keyword), mỗi file một call để PDF dài/lỗi provider chỉ làm file đó rơi
về "khac". Không rõ loại → dòng "Giấy tờ khác", tuyệt đối không bỏ sót tệp nào.
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
# Cổng ghi rõ trên trang: "Dung lượng tối đa là 6 Mb".
_MAX_FILE_BYTES = 6 * 1024 * 1024

_OTHER = "khac"

# 5 dòng cố định của bảng; `slotIndex` là thứ tự DOM 0-based của các ô upload.
_ROWS: dict[int, str] = {
    0: "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 24 ban hành kèm theo "
       "Quyết định số 47/2026/QĐ-UBND",
    1: "Giấy chứng nhận đã cấp",
    2: "Giấy tờ về việc nhận chuyển quyền sử dụng đất đối với phần diện tích tăng thêm",
    3: "Mảnh trích đo bản đồ địa chính thửa đất",
    4: "Văn bản về việc đại diện theo quy định của pháp luật về dân sự đối với trường hợp thực hiện "
       "thủ tục đăng ký đất đai, tài sản gắn liền với đất thông qua người đại diện",
}

# docType (LLM) → (slotIndex, tên hiển thị của tài liệu).
# Hợp đồng chuyển quyền và chứng từ thanh toán CÙNG vào dòng 2: chứng từ tiền nong là một phần của hồ
# sơ chứng minh việc nhận chuyển quyền, và ô upload nhận nhiều tệp.
_ROUTES: dict[str, tuple[int, str]] = {
    "don_bien_dong": (0, "Đơn đăng ký biến động đất đai (Mẫu số 24)"),
    "gcn": (1, "Giấy chứng nhận quyền sử dụng đất đã cấp"),
    "giay_to_chuyen_quyen": (2, "Hợp đồng chuyển quyền phần diện tích tăng thêm"),
    "chung_tu_thanh_toan": (2, "Chứng từ thanh toán (hóa đơn, xác nhận số tiền đã thanh toán)"),
    "manh_trich_do": (3, "Mảnh trích đo bản đồ địa chính thửa đất"),
    "van_ban_dai_dien": (4, "Văn bản về việc đại diện (Giấy ủy quyền)"),
}

# docType KHÔNG có dòng riêng trong bảng → xuống "Giấy tờ khác" (tên dòng = documentName).
_OTHER_ROUTES: dict[str, str] = {
    "to_khai_thue": "Tờ khai thuế, lệ phí trước bạ",
    "giay_to_nhan_than": "CCCD và giấy tờ hộ tịch của người sử dụng đất",
    _OTHER: "Tài liệu kèm theo",
}

_ALLOWED = set(_ROUTES) | set(_OTHER_ROUTES)

# Dòng là thành phần hồ sơ CHÍNH của thủ tục — trống thì phải nhắc cán bộ, không im lặng.
_ROWS_CAN_NHAC = {
    0: "Đơn đăng ký biến động đất đai (Mẫu số 24)",
    1: "Giấy chứng nhận đã cấp",
    2: "Giấy tờ về việc nhận chuyển quyền sử dụng đất đối với phần diện tích tăng thêm",
    3: "Mảnh trích đo bản đồ địa chính thửa đất",
}

# Giấy tờ hay bị QUÉT GỘP vào file của dòng chính → nhắc cán bộ tự tách nếu nơi tiếp nhận yêu cầu.
# docType đi ghép → (docType của file chứa nó, mô tả).
_HAY_QUET_GOP: dict[str, tuple[str, str]] = {
    "to_khai_thue": ("don_bien_dong", "tờ khai lệ phí trước bạ / tờ khai thuế sử dụng đất phi nông nghiệp"),
    "giay_to_nhan_than": ("van_ban_dai_dien", "CCCD của người sử dụng đất và giấy chứng nhận kết hôn"),
}


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


def _data_url_size(data_url: str) -> int:
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
        {"role": "user",
         "content": build_user_prompt([{"index": index, "text": str(document.get("text") or "")[:12000]}])},
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
    used_other_names: set[str] = set()

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        llm_type = llm_types.get(index, "")
        doc_type = llm_type if llm_type in _ALLOWED else _OTHER
        source = "llm" if llm_type else "default"

        if doc_type in _ROUTES:
            slot_index, document_name = _ROUTES[doc_type]
            attachments.append({
                "fileIndex": index,
                "fileName": file_name,
                "documentName": document_name,
                "componentName": _ROWS[slot_index],
                "target": "fixed-slot",
                "needsAddComponent": False,
                # slotKey theo DÒNG (không theo docType) để hai docType cùng dòng được engine GOM vào
                # một lần bơm tệp, thay vì lần sau thấy ô đã dùng rồi báo lỗi.
                "slotKey": f"lc_115694_row_{slot_index}",
                "slotIndex": slot_index,
                "slotName": _ROWS[slot_index],
                "tickRow": True,
                "detectedType": doc_type,
            })
            classified.append({
                "fileName": file_name, "docType": doc_type, "source": source, "slotIndex": slot_index,
            })
            continue

        # Không có dòng riêng → "Giấy tờ khác" (target=new: FE thêm dòng, gõ tên rồi chọn tệp).
        base_name = _other_display(file_name) if doc_type == _OTHER else _OTHER_ROUTES[doc_type]
        document_name = _unique_document_name(base_name, used_other_names)
        if doc_type == _OTHER:
            unknown.append(file_name)
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": document_name,
            "componentName": document_name,
            "target": "new",
            "needsAddComponent": True,
            "detectedType": doc_type,
            # Cổng iGate VNPT: bấm option "Chọn tệp tin" mở hộp thoại file của hệ điều hành → FE chỉ
            # gán thẳng, không có mục "Giấy tờ khác" thì bỏ qua tệp chứ không bấm lung tung.
            "noChooserClick": True,
        })
        classified.append({"fileName": file_name, "docType": doc_type, "source": source, "slotIndex": None})

    if unknown:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã tạm đưa xuống \"Giấy tờ khác\" để không bỏ sót — cán bộ kiểm "
            f"tra lại: {', '.join(unknown)}."
        )

    filled_rows = {item["slotIndex"] for item in attachments if item.get("target") == "fixed-slot"}
    thieu = [name for slot, name in sorted(_ROWS_CAN_NHAC.items()) if slot not in filled_rows]
    if thieu:
        warnings.append(
            "Chưa có tệp nào cho dòng: " + "; ".join(thieu) + ". Cán bộ kiểm tra xem hồ sơ có thuộc "
            "trường hợp phải nộp thành phần này không — nếu có thì bổ sung rồi tích dòng, nếu không thì "
            "để trống."
        )

    # Giấy tờ quét gộp: không có file RIÊNG loại đó, nhưng có file của dòng chính hay chứa nó.
    have_types = {item.get("detectedType") for item in attachments}
    for doc_type, (host_type, mo_ta) in _HAY_QUET_GOP.items():
        if doc_type not in have_types and host_type in have_types:
            host_row = _ROWS[_ROUTES[host_type][0]]
            warnings.append(
                f"Không thấy tệp riêng cho {mo_ta}. Hồ sơ dạng này thường quét gộp chúng vào cùng file "
                f"với \"{_ROUTES[host_type][1]}\" (dòng \"{host_row[:60]}…\"). Mỗi tệp chỉ được xếp vào "
                "MỘT dòng nên chúng đi kèm ở đó; nếu nơi tiếp nhận yêu cầu tách riêng thì cán bộ đề nghị "
                "người dân tách tệp rồi đính bổ sung vào \"Giấy tờ khác\"."
            )

    if not attachments:
        warnings.append("Không có tài liệu nào để đính kèm.")
    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]

    valid_files: list[dict] = []
    for file in raw_files:
        size = _data_url_size(file.get("dataUrl", ""))
        if size > _MAX_FILE_BYTES:
            errors.append(
                f"File '{file['name']}' vượt quá 6 MB ({size / 1024 / 1024:.2f} MB) — cổng không nhận, "
                "đã bỏ qua."
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

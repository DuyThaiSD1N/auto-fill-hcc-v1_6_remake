"""Đính kèm [Lào Cai] giao đất, cho thuê đất — cổng eForm iGate `dichvucong.laocai.gov.vn`.

Trang `nhap-thong-tin-ho-so` có **14 `input[type=file]`** theo thứ tự DOM, mỗi ô kèm nút text
"Chọn tệp tin" → engine FE **`fixed-slot`** nhận diện được ngay (`isUploadSlotInput` khớp "chon tep
tin", `chooseBootstrapFileOptionForInput` mở dropdown). `slotIndex` = thứ tự DOM (0-based):

  0–9  : 10 dòng thành phần hồ sơ sẵn (`GiayToCuaHoSoOnline_<id>_fileGiayTo`)
  10–12: 3 dòng "giấy tờ khác" (`HoSoOnline_giayToKhac_file_1..3`) — MỖI DÒNG CÓ Ô "TÊN GIẤY TỜ"
  13   : ô `HoSoOnline_fileGiayToKhac`

⚑ slotKey của package CỐ Ý không nằm trong `FIXED_SLOT_KEYWORDS` (content.js) để FE bỏ bước khớp
keyword và dùng thẳng `slotIndex` — cần thiết vì 3 dòng "Phương án sử dụng đất" (slot 3/4/5) mở đầu
gần như y hệt nhau, keyword không thể phân biệt.

⚑ Tài liệu chưa rõ loại đi `target="new"` (KHÔNG phải fixed-slot): chỉ engine `attachOneFileToOtherListFile`
của FE mới THÊM DÒNG, GÕ TÊN GIẤY TỜ rồi mới gán tệp; đi fixed-slot thì tệp lên nhưng ô tên để trống.
Tên do LLM đọc nội dung đặt (xem prompt), BE chỉ chuẩn hoá + khử trùng — tên tệp không dùng được vì
hệ thống upload đã bỏ dấu và chèn số.

Phân loại THUẦN LLM (không lưới keyword). Tuyệt đối không bỏ sót tệp nào.
"""

import asyncio
import re
import time
from typing import Any

from app.config import settings
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# Cổng ghi ngay trên bảng: "Dung lượng tối đa là 6 Mb". Gán tệp quá cỡ thì cổng nuốt im lặng.
_MAX_FILE_BYTES = 6 * 1024 * 1024

# docType → (slotIndex, text NGUYÊN VĂN của dòng trên cổng, tên hiển thị).
_ROUTES: dict[str, dict[str, Any]] = {
    "don_mau_01": {
        "slotIndex": 0,
        "slotName": "Đơn theo mẫu số 01",
        "display": "Đơn đề nghị giao đất, cho thuê đất (Mẫu số 01)",
    },
    "van_ban_chu_truong_dau_tu": {
        "slotIndex": 1,
        "slotName": "Bản sao văn bản phê duyệt dự án đầu tư, quyết định chấp thuận chủ trương đầu tư",
        "display": "Văn bản chấp thuận chủ trương đầu tư",
    },
    "van_ban_dau_gia": {
        "slotIndex": 2,
        "slotName": "Bản sao văn bản của đơn vị được giao tổ chức thực hiện việc đấu giá quyền sử dụng đất",
        "display": "Văn bản của đơn vị tổ chức đấu giá quyền sử dụng đất",
    },
    "phuong_an_sdd_dieu_180": {
        "slotIndex": 3,
        "slotName": "Bản sao Phương án sử dụng đất đã được cơ quan, tổ chức có thẩm quyền phê duyệt đối "
                    "với tổ chức kinh tế, đơn vị sự nghiệp công lập",
        "display": "Phương án sử dụng đất (Điều 180)",
    },
    "phuong_an_sdd_nong_lam_181": {
        "slotIndex": 4,
        "slotName": "Bản sao Phương án sử dụng đất của công ty nông, lâm nghiệp tại địa phương",
        "display": "Phương án sử dụng đất công ty nông, lâm nghiệp (Điều 181)",
    },
    "phuong_an_sdd_dat_thu_hoi": {
        "slotIndex": 5,
        "slotName": "Bản sao Phương án sử dụng đất đã được cơ quan, tổ chức có thẩm quyền phê duyệt đối "
                    "với diện tích đất thu hồi của công ty nông, lâm nghiệp",
        "display": "Phương án sử dụng đất thu hồi của công ty nông, lâm nghiệp",
    },
    "giay_phep_khoang_san": {
        "slotIndex": 6,
        "slotName": "Bản sao Giấy phép khai thác khoáng sản trong trường hợp dự án sử dụng cho hoạt động khoáng sản",
        "display": "Giấy phép khai thác khoáng sản",
    },
    "ho_so_rung": {
        "slotIndex": 7,
        "slotName": "Đối với trường hợp giao rừng, cho thuê rừng thì phải có thêm các tài liệu sau",
        "display": "Hồ sơ giao rừng, cho thuê rừng",
    },
    "giay_to_mien_giam": {
        "slotIndex": 8,
        "slotName": "Bản sao Giấy tờ chứng minh thuộc đối tượng miễn, giảm tiền sử dụng đất theo quy định của pháp luật",
        "display": "Giấy tờ chứng minh miễn, giảm tiền sử dụng đất",
    },
    "van_ban_dieu_133": {
        "slotIndex": 9,
        "slotName": "Bản sao các văn bản theo quy định của pháp luật đối với trường hợp quy định tại "
                    "điểm i khoản 1 Điều 133 Luật Đất đai",
        "display": "Văn bản theo điểm i khoản 1 Điều 133 Luật Đất đai",
    },
}
_ALLOWED = set(_ROUTES) | {"other"}


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
    return "other"


_FALLBACK_DOCUMENT_NAME = "Tài liệu khác"
_MAX_DOCUMENT_NAME = 60


def _clean_document_name(raw: str) -> str:
    """Chuẩn hoá tên gõ vào ô "Tên giấy tờ".

    KHÔNG dùng `normalize_document_name` của _shared: hàm đó nhận TÊN TỆP nên chạy `Path(raw).stem`,
    cắt mất phần trước dấu "/" — "QĐ 1678/QĐ-UBND điều chỉnh…" thành "QĐ-UBND điều chỉnh…", tức mất
    đúng số hiệu văn bản là thứ phân biệt các quyết định với nhau. Ở đây chỉ đổi "/" thành "-" (giữ
    số hiệu, tránh ký tự cổng có thể từ chối) và bỏ ký tự lạ.
    """
    import unicodedata

    text = unicodedata.normalize("NFC", str(raw or "")).replace("/", "-")
    chars = [ch if (ch.isalnum() or ch in " _-,.()") else " " for ch in text]
    text = re.sub(r"\s+", " ", "".join(chars)).strip(" -,.")
    return text[:_MAX_DOCUMENT_NAME].strip(" -,.")


def _unique_document_name(base: str, used: set[str]) -> str:
    """Tên gõ vào ô "Tên giấy tờ" của dòng Giấy tờ khác — hai dòng trùng tên là cán bộ không phân biệt được."""
    value = _clean_document_name(base) or _FALLBACK_DOCUMENT_NAME
    key = _fold(value)
    if key and key not in used:
        used.add(key)
        return value
    stem = value[:52].strip() or _FALLBACK_DOCUMENT_NAME
    suffix = 2
    while True:
        candidate = f"{stem} {suffix}"[:_MAX_DOCUMENT_NAME].strip()
        if _fold(candidate) not in used:
            used.add(_fold(candidate))
            return candidate
        suffix += 1


def _file_bytes(file: dict) -> int | None:
    """Kích thước thật, suy từ độ dài base64 của dataUrl (FileItem không mang size)."""
    data_url = file.get("dataUrl")
    if not isinstance(data_url, str) or "," not in data_url:
        return None
    payload = data_url.split(",", 1)[1]
    if not payload:
        return None
    return len(payload) * 3 // 4 - payload[-2:].count("=")


async def _classify_one(document: dict[str, Any]) -> tuple[int, str, str]:
    index = int(document.get("index"))
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt([{"index": index, "text": str(document.get("text") or "")[:12000]}])},
    ]
    # max_tokens cao hơn bản cũ vì nay LLM còn phải trả documentName.
    raw = await client.chat(messages, max_tokens=220, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    first = next(iter(parsed.get("documents", []) or []), {})
    doc_type = _normalize_doc_type(first.get("docType") or first.get("type"))
    return index, doc_type, str(first.get("documentName") or "").strip()


async def _classify_with_llm(
    documents: list[dict[str, Any]],
    errors: list[str] | None = None,
) -> dict[int, tuple[str, str]]:
    if not documents:
        return {}
    # Một call cho mỗi file: PDF dài hoặc lỗi provider chỉ làm file đó rơi về other.
    outcomes = await asyncio.gather(*(_classify_one(d) for d in documents), return_exceptions=True)
    result: dict[int, tuple[str, str]] = {}
    for document, outcome in zip(documents, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            if errors is not None:
                errors.append(f"attachment_agent file {document.get('index')}: {outcome}")
            continue
        index, doc_type, document_name = outcome
        result[index] = (doc_type, document_name)
    return result


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, tuple[str, str] | str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    unknown: list[str] = []
    qua_nang: list[str] = []
    used_names: set[str] = set()

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        raw = llm_types.get(index)
        llm_type, llm_name = raw if isinstance(raw, tuple) else (raw or "", "")
        doc_type = llm_type if llm_type in _ALLOWED else "other"
        source = "llm" if llm_type else "default"

        size = _file_bytes(file)
        if size and size > _MAX_FILE_BYTES:
            qua_nang.append(f"{file_name} ({round(size / 1024 / 1024, 1)} MB)")

        if doc_type == "other":
            # Dòng "Giấy tờ khác" phải có TÊN GIẤY TỜ. Chỉ engine otherListFile của FE mới gõ được tên
            # đó (nó thêm dòng, điền ô tên rồi mới gán tệp) — đi fixed-slot thì tệp lên nhưng ô tên
            # TRỐNG. Tên lấy từ LLM đọc nội dung, KHÔNG lấy tên tệp (mất dấu, dính số của hệ thống).
            document_name = _unique_document_name(llm_name, used_names)
            attachments.append({
                "fileIndex": index,
                "fileName": file_name,
                "documentName": document_name,
                "componentName": document_name,
                "target": "new",
                "needsAddComponent": True,
                "detectedType": doc_type,
                # Cổng iGate VNPT: bấm option "Chọn tệp tin" mở hộp thoại file của hệ điều hành
                # (chặn UI) → FE chỉ gán thẳng, hụt thì bỏ qua tệp đó.
                "noChooserClick": True,
            })
            unknown.append(f"{file_name} → \"{document_name}\"")
            classified.append({
                "fileName": file_name,
                "docType": doc_type,
                "documentName": document_name,
                "source": source,
                "slotIndex": None,
            })
            continue

        route = _ROUTES[doc_type]
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": route["display"],
            "componentName": route["slotName"],
            "target": "fixed-slot",
            "needsAddComponent": False,
            "slotKey": f"laocai_gtd_{doc_type}",
            "slotIndex": route["slotIndex"],
            "slotName": route["slotName"],
            "detectedType": doc_type,
        })
        classified.append({
            "fileName": file_name,
            "docType": doc_type,
            "documentName": route["display"],
            "source": source,
            "slotIndex": route["slotIndex"],
        })

    if unknown:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã thêm dòng \"Giấy tờ khác\" kèm tên tài liệu để không bỏ "
            f"sót — cán bộ kiểm tra lại: {', '.join(unknown)}."
        )
    if qua_nang:
        warnings.append(
            "Tệp vượt giới hạn 6 MB của cổng nên có thể bị nuốt im lặng, hãy nén hoặc giảm DPI rồi "
            f"tải lại: {', '.join(qua_nang)}."
        )
    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]
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

    attachments, warnings, classified = build_plan_items(raw_files, llm_types)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [raw_files[d["index"]]["name"] for d in llm_documents],
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

"""Đính kèm [Lào Cai] giao đất/cho thuê đất, giao rừng/cho thuê rừng (1.115678) — eForm iGate.

Cùng cổng `dichvucong.laocai.gov.vn` và cùng engine FE **`fixed-slot`** như thủ tục 1.115650: mỗi ô
upload đi kèm nút text "Chọn tệp tin" nên `isUploadSlotInput` nhận ra, và `slotIndex` = thứ tự DOM
(0-based) của `input[type=file]` trên trang.

⚠ THỨ TỰ DÒNG KHÁC 1.115650 — KHÔNG ĐƯỢC CHÉP THẲNG BẢNG CỦA THỦ TỤC KIA. Danh mục thành phần hồ sơ
của thủ tục này (10 dòng, bóc từ ảnh chụp bước "Thành phần hồ sơ") đẩy dòng Điều 133 lên trên ba
dòng Phương án sử dụng đất, và đẩy dòng miễn/giảm tiền sử dụng đất xuống cuối:

  slot 0: Đơn theo Mẫu số 01 (ban hành kèm Quyết định số 47/2026/QĐ-UBND)
  slot 1: Văn bản phê duyệt dự án đầu tư / chấp thuận chủ trương đầu tư
  slot 2: Văn bản về kết quả đấu giá KHÔNG THÀNH (điểm b khoản 6 Điều 125)
  slot 3: Văn bản theo điểm i khoản 1 Điều 133   ← ở 1.115650 dòng này nằm CUỐI (slot 9)
  slot 4: Phương án sử dụng đất (Điều 180)
  slot 5: Phương án sử dụng đất công ty nông, lâm nghiệp (Điều 181)
  slot 6: Phương án sử dụng đất với diện tích đất thu hồi của công ty nông, lâm nghiệp
  slot 7: Giấy phép khai thác khoáng sản
  slot 8: Tài liệu giao rừng, cho thuê rừng
  slot 9: Giấy tờ chứng minh miễn, giảm tiền sử dụng đất   ← ở 1.115650 là slot 8
  slot 10–13: các dòng "giấy tờ khác" của cổng (3 dòng rời + 1 ô tổng hợp)

⚑ GỘP BỘ GIẤY TỜ TRÚNG ĐẤU GIÁ VÀO DÒNG ĐƠN (slot 0). Đây là điểm nghiệp vụ quan trọng nhất của
thủ tục: hồ sơ giao đất sau trúng đấu giá gồm quyết định công nhận kết quả, biên bản đấu giá, danh
sách người trúng, chứng từ nộp tiền, thông báo thuế, hợp đồng ủy quyền, CCCD — mà danh mục 10 dòng
của cổng KHÔNG CÓ DÒNG RIÊNG cho bất kỳ thứ nào trong số đó. Theo ảnh hướng dẫn ánh xạ, toàn bộ
chúng đi CHUNG vào dòng Đơn (ô upload nhận nhiều tệp). Vì vậy các docType nhóm này được khai riêng
để LLM nhận diện cho đúng, nhưng đều trỏ về `slotIndex` 0 — KHÔNG đẩy xuống "giấy tờ khác", vì làm
vậy là tách rời bộ hồ sơ khỏi dòng bắt buộc phải tick.

⚑ slotKey cố ý KHÔNG nằm trong `FIXED_SLOT_KEYWORDS` (content.js) để FE bỏ bước khớp keyword và
dùng thẳng `slotIndex` — bắt buộc, vì ba dòng "Phương án sử dụng đất" (slot 4/5/6) mở đầu gần như y
hệt nhau, keyword không thể phân biệt.

Phân loại THUẦN LLM (không lưới keyword). Tài liệu chưa rõ loại → dòng "giấy tờ khác", tuyệt đối
không bỏ sót tệp nào.
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

# Ô "giấy tờ khác" đầu tiên; 3 ô liền nhau (10, 11, 12) rồi tới ô tổng hợp (13).
_OTHER_SLOT_INDEX = 10
_OTHER_SLOT_COUNT = 4

# Dòng Đơn — cũng là nơi gộp cả bộ giấy tờ trúng đấu giá (xem docstring).
_DON_SLOT_INDEX = 0
_DON_SLOT_NAME = "Đơn theo Mẫu số 01 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND"

# Trần dung lượng MỘT dòng đính kèm của cổng, ghi ngay trên trang: "Dung lượng tối đa là 6 Mb".
_MAX_SLOT_BYTES = 6 * 1024 * 1024

# docType → (slotIndex, text NGUYÊN VĂN của dòng trên cổng, tên hiển thị).
_ROUTES: dict[str, dict[str, Any]] = {
    # --- Dòng Đơn và cả bộ giấy tờ trúng đấu giá gộp chung vào đó ---
    "don_mau_01": {
        "slotIndex": _DON_SLOT_INDEX,
        "slotName": _DON_SLOT_NAME,
        "display": "Đơn đề nghị giao đất, cho thuê đất (Mẫu số 01)",
    },
    "quyet_dinh_trung_dau_gia": {
        "slotIndex": _DON_SLOT_INDEX,
        "slotName": _DON_SLOT_NAME,
        "display": "Quyết định công nhận kết quả trúng đấu giá (kèm danh sách người trúng đấu giá)",
    },
    "bien_ban_dau_gia": {
        "slotIndex": _DON_SLOT_INDEX,
        "slotName": _DON_SLOT_NAME,
        "display": "Biên bản đấu giá (kèm danh sách người tham gia đấu giá và giá trả)",
    },
    "thong_bao_thue": {
        "slotIndex": _DON_SLOT_INDEX,
        "slotName": _DON_SLOT_NAME,
        "display": "Thông báo nộp tiền sử dụng đất / lệ phí trước bạ",
    },
    "chung_tu_nop_tien": {
        "slotIndex": _DON_SLOT_INDEX,
        "slotName": _DON_SLOT_NAME,
        "display": "Giấy nộp tiền vào ngân sách nhà nước",
    },
    "hop_dong_uy_quyen": {
        "slotIndex": _DON_SLOT_INDEX,
        "slotName": _DON_SLOT_NAME,
        "display": "Hợp đồng ủy quyền (có công chứng)",
    },
    "giay_to_tuy_than": {
        "slotIndex": _DON_SLOT_INDEX,
        "slotName": _DON_SLOT_NAME,
        "display": "Giấy tờ tùy thân (CCCD/CMND/hộ chiếu)",
    },
    # --- Chín dòng còn lại của danh mục, đúng thứ tự trên cổng ---
    "van_ban_chu_truong_dau_tu": {
        "slotIndex": 1,
        "slotName": "Bản sao Văn bản phê duyệt dự án đầu tư, quyết định chấp thuận chủ trương đầu tư",
        "display": "Văn bản chấp thuận chủ trương đầu tư",
    },
    "van_ban_dau_gia_khong_thanh": {
        "slotIndex": 2,
        "slotName": "Bản sao văn bản của đơn vị được giao tổ chức thực hiện việc đấu giá quyền sử dụng "
                    "đất về kết quả đấu giá quyền sử dụng đất không thành",
        "display": "Văn bản về kết quả đấu giá quyền sử dụng đất KHÔNG THÀNH",
    },
    "van_ban_dieu_133": {
        "slotIndex": 3,
        "slotName": "Bản sao các văn bản theo quy định của pháp luật đối với trường hợp quy định tại "
                    "điểm i khoản 1 Điều 133 Luật Đất đai",
        "display": "Văn bản theo điểm i khoản 1 Điều 133 Luật Đất đai",
    },
    "phuong_an_sdd_dieu_180": {
        "slotIndex": 4,
        "slotName": "Bản sao Phương án sử dụng đất đã được cơ quan, tổ chức có thẩm quyền phê duyệt đối "
                    "với tổ chức kinh tế, đơn vị sự nghiệp công lập",
        "display": "Phương án sử dụng đất (Điều 180)",
    },
    "phuong_an_sdd_nong_lam_181": {
        "slotIndex": 5,
        "slotName": "Bản sao Phương án sử dụng đất của công ty nông, lâm nghiệp tại địa phương",
        "display": "Phương án sử dụng đất công ty nông, lâm nghiệp (Điều 181)",
    },
    "phuong_an_sdd_dat_thu_hoi": {
        "slotIndex": 6,
        "slotName": "Bản sao Phương án sử dụng đất đã được cơ quan, tổ chức có thẩm quyền phê duyệt đối "
                    "với diện tích đất thu hồi của công ty nông, lâm nghiệp",
        "display": "Phương án sử dụng đất thu hồi của công ty nông, lâm nghiệp",
    },
    "giay_phep_khoang_san": {
        "slotIndex": 7,
        "slotName": "Bản sao Giấy phép khai thác khoáng sản trong trường hợp dự án sử dụng cho hoạt động "
                    "khoáng sản",
        "display": "Giấy phép khai thác khoáng sản",
    },
    "ho_so_rung": {
        "slotIndex": 8,
        "slotName": "Đối với trường hợp giao rừng, cho thuê rừng thì phải có thêm các tài liệu sau",
        "display": "Hồ sơ giao rừng, cho thuê rừng",
    },
    "giay_to_mien_giam": {
        "slotIndex": 9,
        "slotName": "Bản sao Giấy tờ chứng minh thuộc đối tượng miễn, giảm tiền sử dụng đất theo quy định "
                    "của pháp luật",
        "display": "Giấy tờ chứng minh miễn, giảm tiền sử dụng đất",
    },
}
_ALLOWED = set(_ROUTES) | {"other"}

# Các loại giấy tờ của bộ hồ sơ trúng đấu giá — không có dòng riêng nên gộp vào dòng Đơn.
_BUNDLE_TYPES = frozenset(
    doc_type
    for doc_type, route in _ROUTES.items()
    if route["slotIndex"] == _DON_SLOT_INDEX and doc_type != "don_mau_01"
)


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


def _data_url_size(data_url: Any) -> int:
    """Kích thước thật của tệp, suy từ độ dài phần base64 (FileItem không mang size)."""
    payload = re.sub(r"\s+", "", str(data_url or "").partition(",")[2])
    if not payload:
        return 0
    padding = len(payload) - len(payload.rstrip("="))
    return max(0, (len(payload) * 3) // 4 - padding)


def _mb(size: int) -> str:
    return f"{size / 1024 / 1024:.1f} MB"


def _other_display(file_name: str) -> str:
    """Tài liệu chưa rõ loại giữ TÊN THẬT theo tệp để cán bộ biết là giấy gì."""
    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", str(file_name or "")).strip()
    stem = re.sub(r"[_]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return normalize_document_name(stem, "Tài liệu khác") if stem else "Tài liệu khác"


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
    # Một call cho mỗi file: PDF dài hoặc lỗi provider chỉ làm file đó rơi về other.
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
    bundled: list[str] = []
    other_used = 0
    bytes_per_slot: dict[int, int] = {}

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        llm_type = llm_types.get(index, "")
        doc_type = llm_type if llm_type in _ALLOWED else "other"
        source = "llm" if llm_type else "default"

        if doc_type == "other":
            # Trải đều qua các ô "giấy tờ khác"; hết ô thì dồn vào ô cuối (input multiple).
            slot_index = _OTHER_SLOT_INDEX + min(other_used, _OTHER_SLOT_COUNT - 1)
            other_used += 1
            slot_key = f"laocai_ctdtr_giay_to_khac_{slot_index}"
            slot_name = "Giấy tờ khác"
            document_name = _other_display(file_name)
            unknown.append(file_name)
        else:
            route = _ROUTES[doc_type]
            slot_index = route["slotIndex"]
            slot_key = f"laocai_ctdtr_{doc_type}"
            slot_name = route["slotName"]
            document_name = route["display"]
            if doc_type in _BUNDLE_TYPES:
                bundled.append(f"{file_name} ({route['display']})")

        bytes_per_slot[slot_index] = bytes_per_slot.get(slot_index, 0) + _data_url_size(file.get("dataUrl"))

        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": document_name,
            "componentName": slot_name,
            "target": "fixed-slot",
            "needsAddComponent": False,
            "slotKey": slot_key,
            "slotIndex": slot_index,
            "slotName": slot_name,
            "detectedType": doc_type,
        })
        classified.append({
            "fileName": file_name,
            "docType": doc_type,
            "source": source,
            "slotIndex": slot_index,
        })

    if bundled:
        warnings.append(
            "Danh mục thành phần hồ sơ của thủ tục này KHÔNG có dòng riêng cho giấy tờ trúng đấu giá, "
            "nộp tiền và thông báo thuế — đã gộp chung vào dòng \"Đơn theo Mẫu số 01\" theo hướng dẫn "
            f"ánh xạ: {', '.join(bundled)}."
        )
    if unknown:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã tạm đính vào dòng \"Giấy tờ khác\" để không bỏ sót — "
            f"cán bộ kiểm tra lại: {', '.join(unknown)}."
        )

    # Trần 6 MB tính cho TỪNG DÒNG chứ không cho từng tệp: cả bộ trúng đấu giá dồn vào dòng Đơn nên
    # dòng đó là chỗ vượt trần trước tiên, mà cổng chỉ báo lỗi lúc bấm nộp — báo sớm để còn kịp nén.
    for slot_index, total in sorted(bytes_per_slot.items()):
        if total <= _MAX_SLOT_BYTES:
            continue
        ten_dong = _DON_SLOT_NAME if slot_index == _DON_SLOT_INDEX else f"thứ {slot_index + 1}"
        warnings.append(
            f"Tổng dung lượng các tệp đính vào dòng \"{ten_dong}\" là {_mb(total)}, vượt giới hạn 6 MB "
            "của cổng — cần nén PDF hoặc tách thành nhiều tệp trước khi nộp."
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

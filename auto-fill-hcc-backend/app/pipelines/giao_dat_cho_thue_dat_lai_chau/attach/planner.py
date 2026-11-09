"""Đính kèm cho [Lai Châu] Giao đất, cho thuê đất (mã 1.115577).

Bước 3 cổng dichvucong.laichau.gov.vn là BẢNG 9 DÒNG cố định, mỗi dòng có checkbox ở cột "#" + ô "Số bản" + một
``input[type=file]``; dưới bảng là khối "Giấy tờ khác" (``HoSoOnline_giayToKhac[]`` tên + tệp). Cùng khuôn bảng với
``chuyen_muc_dich_su_dung_dat_mien_nui_lai_chau``.

Định tuyến chốt theo ảnh ánh xạ của bộ hồ sơ mẫu (dự án Hồ chứa nước Giang Ma, giao đất lần 3):
  - dòng 1 "Mẫu số 01. Đơn đề nghị giao đất; cho thuê đất; ..." nhận CHUNG Đơn (tệp chính, đứng đầu) và mọi "tài liệu gửi
    kèm" mục 13 của Đơn: biên bản chỉnh lý GCN, trích đo / bản đồ khu đất, văn bản xác nhận hoàn thành bồi thường GPMB,
    biểu tổng hợp diện tích, quyết định thu hồi đất, quyết định thành lập tổ chức — form không có dòng riêng cho chúng;
  - dòng 9 "Văn bản phê duyệt dự án đầu tư, quyết định chấp thuận chủ trương đầu tư ..." nhận CHUNG quyết định chủ trương
    đầu tư và quyết định phê duyệt dự án;
  - dòng 2–8 (phương án sử dụng đất của tổ chức / công ty nông lâm nghiệp, đấu giá thuê rừng, hiện trạng rừng, đấu giá
    không thành, chia tách sáp nhập) không áp dụng cho hồ sơ mẫu → không tick;
  - CCCD / giấy ủy quyền không có dòng riêng → "Giấy tờ khác".
Thứ tự tệp trong một dòng giữ theo ảnh (Đơn → biên bản → trích đo → xác nhận GPMB → biểu tổng hợp …). Mỗi tệp đính
NGUYÊN, không tách trang. JS cổng (Nth.FormBuilder.Element.File.xhrUpload) gửi mọi tệp của một lần chọn lên máy chủ nên
extension gán cả lô vào ô của dòng một lần.

Engine ``fixed-slot`` của extension: khớp dòng theo ``slotKeywords`` (dự phòng ``slotIndex`` 0-based), tích checkbox dòng
(``tickRow``) rồi bơm tệp vào input của dòng. Mục ``target="new"`` đi khối "Giấy tờ khác".

Phân loại: LLM trước, LLM trả other/lỗi thì rule theo TIÊU ĐỀ văn bản (OCR rỗng thì theo tên tệp). Tệp không nhận ra vẫn
không bị rớt: đưa vào "Giấy tờ khác" giữ tên tệp, kèm cảnh báo. Cổng chặn tệp quá 6 MB → tệp vượt bị loại kèm cảnh báo
nén; tệp sát ngưỡng (trên 6.000.000 byte) vẫn đính nhưng cảnh báo vì cổng có thể tính 6 MB theo hệ thập phân.
"""

import re
import time
from pathlib import Path
from typing import Any

from app.config import settings
from app.pipelines._shared import fold, normalize_document_name
from app.pipelines._shared.compact_agent.runner import _extract_docx_text, _is_docx
from app.pipelines._shared.documents import join_ocr_documents
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_MAX_FILE_BYTES = 6 * 1024 * 1024
_NEAR_LIMIT_BYTES = 6_000_000
# Tiêu đề / trích yếu văn bản nằm ở đầu; phần "Căn cứ" và "Tài liệu gửi kèm" nhắc tên văn bản khác nên chỉ soi phần đầu.
_HEAD_CHARS = 800

_DON = "don_de_nghi"
_BIEN_BAN = "bien_ban_chinh_ly"
_XAC_NHAN = "xac_nhan_gpmb"
_BIEU = "bieu_tong_hop"
_TRICH_DO = "trich_do"
_THU_HOI = "quyet_dinh_thu_hoi"
_THANH_LAP = "quyet_dinh_thanh_lap"
_CHU_TRUONG = "chu_truong_dau_tu"
_PHE_DUYET = "phe_duyet_du_an"
_UY_QUYEN = "van_ban_uy_quyen"
_IDENTITY = "identity"
_OTHER = "other"

# slotName theo cột "Tên giấy tờ" trên cổng (ảnh ánh xạ); slotKeywords dạng đã fold, mỗi cụm chỉ thuộc một dòng.
SLOTS: list[dict[str, Any]] = [
    {
        "slotKey": "gddt_lc_row01", "slotIndex": 0,
        "slotName": "Mẫu số 01. Đơn đề nghị giao đất; cho thuê đất; giao đất và giao rừng; cho thuê đất và cho thuê rừng "
        "(Bản chính)",
        "slotKeywords": ["don de nghi giao dat"],
    },
    {
        "slotKey": "gddt_lc_row02", "slotIndex": 1,
        "slotName": "Bản sao Phương án sử dụng đất đã được cơ quan, tổ chức có thẩm quyền phê duyệt đối với tổ chức kinh "
        "tế, đơn vị sự nghiệp công lập đã được Nhà nước giao đất, cho thuê đất trước ngày Luật Đất đai có hiệu lực thi "
        "hành đối với trường hợp quy định tại Điều 180 Luật Đất đai (nếu có) (Bản chính hoặc bản sao)",
        "slotKeywords": ["dieu 180 luat dat dai"],
    },
    {
        "slotKey": "gddt_lc_row03", "slotIndex": 2,
        "slotName": "Bản sao Phương án sử dụng đất của công ty nông, lâm nghiệp tại địa phương đã được cơ quan, tổ chức "
        "có thẩm quyền phê duyệt đối với trường hợp quy định tại Điều 181 Luật Đất đai (nếu có) (Bản chính hoặc bản sao)",
        "slotKeywords": ["lam nghiep tai dia phuong"],
    },
    {
        "slotKey": "gddt_lc_row04", "slotIndex": 3,
        "slotName": "Kết quả đấu giá thuê rừng; biên bản đấu giá cho thuê rừng; danh sách người trúng đấu giá thuê rừng; "
        "thông báo hoàn thành nghĩa vụ tài chính đối với người trúng đấu giá thuê rừng đối với trường hợp cho thuê đất "
        "và cho thuê rừng; dự án đầu tư đối với khu rừng đề nghị thuê; báo cáo điều tra, đánh giá hiện trạng rừng và bản "
        "đồ hiện trạng rừng theo quy định của pháp luật về lâm nghiệp đối với trường hợp cho thuê đất và cho thuê rừng "
        "(Bản chính hoặc bản sao)",
        "slotKeywords": ["ket qua dau gia thue rung"],
    },
    {
        "slotKey": "gddt_lc_row05", "slotIndex": 4,
        "slotName": "Báo cáo điều tra, đánh giá hiện trạng rừng và bản đồ hiện trạng rừng theo quy định của pháp luật về "
        "lâm nghiệp đối với trường hợp giao đất và giao rừng (Bản chính hoặc bản sao)",
        "slotKeywords": ["truong hop giao dat va giao rung"],
    },
    {
        "slotKey": "gddt_lc_row06", "slotIndex": 5,
        "slotName": "Bản sao văn bản của đơn vị được giao tổ chức thực hiện việc đấu giá quyền sử dụng đất về kết quả đấu "
        "giá quyền sử dụng đất không thành quy định tại điểm b khoản 6 Điều 125 Luật Đất đai (Bản chính hoặc bản sao)",
        "slotKeywords": ["dau gia quyen su dung dat khong thanh"],
    },
    {
        "slotKey": "gddt_lc_row07", "slotIndex": 6,
        "slotName": "Bản sao các văn bản theo quy định của pháp luật đối với trường hợp quy định tại điểm i khoản 1 Điều "
        "133 Luật Đất đai mà phải thu hồi đất để giao đất, cho thuê đất cho tổ chức, cá nhân sau chia tách, sáp nhập, "
        "chuyển đổi mô hình tổ chức (Bản chính hoặc bản sao)",
        "slotKeywords": ["diem i khoan 1 dieu 133"],
    },
    {
        "slotKey": "gddt_lc_row08", "slotIndex": 7,
        "slotName": "Bản sao Phương án sử dụng đất đã được cơ quan, tổ chức có thẩm quyền phê duyệt đối với diện tích "
        "đất thu hồi của công ty nông, lâm nghiệp quản lý, sử dụng để giao đất, cho thuê đất quy định tại các điểm c, d "
        "và đ khoản 2 Điều 181 Luật Đất đai (Bản chính hoặc bản sao)",
        "slotKeywords": ["dien tich dat thu hoi cua cong ty nong"],
    },
    {
        "slotKey": "gddt_lc_row09", "slotIndex": 8,
        "slotName": "Văn bản phê duyệt dự án đầu tư, quyết định chấp thuận chủ trương đầu tư, quyết định chấp thuận chủ "
        "trương đầu tư đồng thời chấp thuận nhà đầu tư, văn bản phê duyệt kết quả lựa chọn nhà đầu tư theo quy định của "
        "pháp luật về đầu tư, pháp luật về đầu tư công, pháp luật về đầu tư theo phương thức đối tác công tư hoặc các văn "
        "bản, giấy tờ có giá trị pháp lý tương đương theo quy định của pháp luật (Bản chính)",
        "slotKeywords": ["van ban phe duyet du an dau tu"],
    },
]
_SLOT_BY_INDEX = {slot["slotIndex"]: slot for slot in SLOTS}

# docType -> (dòng, tên tài liệu hiển thị, thứ tự trong dòng). Thứ tự theo ảnh ánh xạ: tệp chính đứng đầu dòng.
_ROUTES: dict[str, tuple[int, str, int]] = {
    _DON: (0, "Đơn đề nghị giao đất, cho thuê đất (Mẫu số 01)", 0),
    _BIEN_BAN: (0, "Biên bản xác nhận công tác chỉnh lý giấy chứng nhận", 1),
    _TRICH_DO: (0, "Trích đo bản đồ địa chính khu đất", 2),
    _XAC_NHAN: (0, "Văn bản xác nhận hoàn thành bồi thường, giải phóng mặt bằng", 3),
    _BIEU: (0, "Biểu tổng hợp diện tích khu đất", 4),
    _THU_HOI: (0, "Quyết định thu hồi đất", 5),
    _THANH_LAP: (0, "Quyết định thành lập tổ chức", 6),
    _CHU_TRUONG: (8, "Quyết định chủ trương đầu tư", 0),
    _PHE_DUYET: (8, "Quyết định phê duyệt dự án đầu tư", 1),
}
# Giấy tờ nhận ra được nhưng bảng không có dòng → "Giấy tờ khác" với tên chuẩn, không cảnh báo.
_OTHER_NAMES = {_UY_QUYEN: "Văn bản ủy quyền"}
_ALLOWED = set(_ROUTES) | set(_OTHER_NAMES) | {_IDENTITY, _OTHER}

# Rule theo tiêu đề, xét THEO THỨ TỰ: văn bản đứng trước hay viện dẫn văn bản đứng sau (biên bản chỉnh lý dẫn quyết định
# phê duyệt dự án, quyết định phê duyệt dự án dẫn quyết định chủ trương đầu tư).
_HEAD_RULES: list[tuple[str, tuple[str, ...]]] = [
    (_DON, ("don de nghi giao dat", "don de nghi cho thue dat", "don xin giao dat", "don xin thue dat")),
    (_BIEN_BAN, ("chinh ly gcn", "chinh ly giay chung nhan", "ban giao, chinh ly")),
    (_XAC_NHAN, ("hoan thanh cong tac boi thuong", "hoan thanh boi thuong", "giai phong mat bang")),
    (_BIEU, ("tong hop dien tich",)),
    (_TRICH_DO, ("trich do ban do dia chinh", "trich luc ban do dia chinh", "ban do phe duyet khu dat", "manh trich do")),
    (_PHE_DUYET, ("phe duyet du an dau tu", "phe duyet ket qua lua chon nha dau tu")),
    (_CHU_TRUONG, ("chu truong dau tu",)),
    (_THANH_LAP, ("thanh lap ban quan ly",)),
    (_THU_HOI, ("thu hoi dat",)),
    (_UY_QUYEN, ("giay uy quyen", "giay gioi thieu")),
]
# OCR rỗng (ảnh quét hỏng, OCR lỗi): đoán theo tên tệp đã bỏ dấu, bỏ khoảng trắng.
_NAME_RULES: list[tuple[str, tuple[str, ...]]] = [
    (_DON, ("dondenghigiaodat", "dondenghichothuedat", "donxingiaodat")),
    (_BIEN_BAN, ("bienban", "chinhly")),
    (_BIEU, ("tonghopdientich", "bieutonghop")),
    (_TRICH_DO, ("trichdo", "trichluc", "bando")),
    (_XAC_NHAN, ("xacnhan", "boithuong", "gpmb")),
    (_PHE_DUYET, ("pheduyetduan",)),
    (_CHU_TRUONG, ("chutruongdautu",)),
    (_THU_HOI, ("thuhoidat",)),
    (_THANH_LAP, ("thanhlap",)),
    (_IDENTITY, ("cccd", "cancuoc")),
]
_IDENTITY_MARKERS = ("can cuoc", "chung minh nhan dan", "identity card", "passport")

_IDENTITY_NAME_RE = re.compile(
    r"(?:full\s*name|h[ọo],?\s*ch[ữu]\s*đ[ệe]m\s*v[àa]\s*t[êe]n(?:\s*khai\s*sinh)?|h[ọo]\s*v[àa]\s*t[êe]n)"
    r"[^\n:]*:?[ \t]*([^\n]*)(?:\n[ \t]*([^\n]*))?",
    re.IGNORECASE,
)


def _normalize_doc_type(value: Any) -> str:
    folded = fold(str(value or ""))
    for doc_type in _ALLOWED:
        if folded == fold(doc_type):
            return doc_type
    return _OTHER


def _rule_doc_type(text: str, file_name: str = "") -> str:
    haystack = fold(text)
    if not haystack.strip():
        compact = re.sub(r"[^a-z0-9]", "", fold(Path(file_name).stem))
        return next((doc for doc, marks in _NAME_RULES if any(mark in compact for mark in marks)), "")
    head = haystack[:_HEAD_CHARS]
    for doc_type, markers in _HEAD_RULES:
        if any(marker in head for marker in markers):
            return doc_type
    if any(marker in haystack for marker in _IDENTITY_MARKERS):
        return _IDENTITY
    return ""


def _identity_holder_name(text: str) -> str | None:
    """Họ tên chủ thẻ đọc từ OCR CCCD ("Họ và tên / Full name: ...") → "Nguyễn Văn A"."""
    for match in _IDENTITY_NAME_RE.finditer(text or ""):
        for candidate in match.groups():
            name = " ".join(re.sub(r"[^\w\s]", " ", candidate or "").split())
            if name and not re.search(r"\d", name) and 2 <= len(name.split()) <= 6 and "name" not in name.lower():
                return name.title()
    return None


def _data_url_size(data_url: str) -> int:
    payload = str(data_url or "").partition(",")[2]
    if not payload:
        return 0
    payload = re.sub(r"\s+", "", payload)
    padding = len(payload) - len(payload.rstrip("="))
    return max(0, (len(payload) * 3) // 4 - padding)


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=900, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    result: dict[int, str] = {}
    for item in parsed.get("documents", []) or []:
        try:
            result[int(item.get("index"))] = _normalize_doc_type(item.get("docType") or item.get("type"))
        except (TypeError, ValueError):
            continue
    return result


def _slot_item(file_index: int, file_name: str, doc_type: str) -> dict:
    slot_index, document_name, _ = _ROUTES[doc_type]
    slot = _SLOT_BY_INDEX[slot_index]
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": slot["slotName"],
        "target": "fixed-slot",
        "needsAddComponent": False,
        "detectedType": doc_type,
        "slotKey": slot["slotKey"],
        "slotIndex": slot["slotIndex"],
        "slotName": slot["slotName"],
        "slotKeywords": slot["slotKeywords"],
        "tickRow": True,
    }


def _other_item(file_index: int, file_name: str, doc_type: str, name: str) -> dict:
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": name,
        "componentName": name,
        "target": "new",
        "componentIndex": None,
        "needsAddComponent": True,
        "detectedType": doc_type,
    }


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict] | None = None,
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    text_by_name = {item.get("name"): str(item.get("text") or "") for item in ocr_results or []}
    slot_items: list[dict] = []
    other_items: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        size = _data_url_size(file.get("dataUrl", ""))
        if size > _MAX_FILE_BYTES:
            warnings.append(
                f"File '{file_name}' nặng {size / 1024 / 1024:.1f} MB, vượt giới hạn 6 MB của cổng — "
                "hãy nén PDF (giảm độ phân giải ảnh quét) cho dưới 6 MB rồi đính kèm lại."
            )
            classified.append(
                {"fileName": file_name, "docType": _OTHER, "source": "validation", "skipped": True,
                 "reason": "file_too_large"}
            )
            continue
        if size > _NEAR_LIMIT_BYTES:
            size_text = f"{size:,}".replace(",", ".")
            warnings.append(
                f"File '{file_name}' nặng {size_text} byte, sát giới hạn 6 MB — nếu cổng báo quá dung lượng thì nén nhỏ "
                "rồi đính lại."
            )

        text = text_by_name.get(file_name, "")
        rule_type = _rule_doc_type(text, file_name)
        llm_type = llm_types.get(index, "")
        if llm_type not in _ALLOWED or llm_type == _OTHER:
            doc_type, source = (rule_type, "rule") if rule_type else (_OTHER, "unknown")
        else:
            doc_type, source = llm_type, "llm"

        if doc_type in _ROUTES:
            slot_items.append(_slot_item(index, file_name, doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "source": source,
                               "slotIndex": [_ROUTES[doc_type][0]]})
            continue

        if doc_type == _IDENTITY:
            holder = _identity_holder_name(text)
            name = f"Căn cước người nộp - {holder}" if holder else "Căn cước người nộp"
            other_items.append(_other_item(index, file_name, _IDENTITY, name))
            classified.append({"fileName": file_name, "docType": _IDENTITY, "source": source})
            continue

        if doc_type in _OTHER_NAMES:
            other_items.append(_other_item(index, file_name, doc_type, _OTHER_NAMES[doc_type]))
            classified.append({"fileName": file_name, "docType": doc_type, "source": source})
            continue

        # Không rõ loại: vẫn đính vào "Giấy tờ khác" với tên tệp gốc, cảnh báo để cán bộ kiểm tra.
        name = normalize_document_name(Path(file_name).stem, "Giấy tờ khác")
        other_items.append(_other_item(index, file_name, _OTHER, name))
        warnings.append(
            f"Không xác định được loại giấy tờ của file '{file_name}' — đã đính vào \"Giấy tờ khác\"; "
            "vui lòng kiểm tra và chuyển sang đúng dòng nếu cần."
        )
        classified.append({"fileName": file_name, "docType": _OTHER, "source": source})

    # Trong một dòng: tệp chính trước, tài liệu kèm theo thứ tự ảnh ánh xạ, cùng loại thì theo thứ tự tải lên.
    slot_items.sort(key=lambda item: (item["slotIndex"], _ROUTES[item["detectedType"]][2], item["fileIndex"]))
    if slot_items and not any(item["detectedType"] == _DON for item in slot_items):
        warnings.append("Chưa thấy Đơn đề nghị giao đất (Mẫu số 01) trong các tệp — dòng 1 bắt buộc có Đơn.")
    return [*slot_items, *other_items], warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    errors: list[str] = []

    small = [item for item in raw_files if _data_url_size(item.get("dataUrl", "")) <= _MAX_FILE_BYTES]
    ocr_files = [item for item in small if item.get("type") in _OCR_TYPES]

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    # OCR không đọc DOCX → lấy chữ thẳng từ XML (Đơn soạn bằng Word).
    ocr_results.extend(_extract_docx_text(item) for item in small if _is_docx(item))
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    by_name = {item.get("name"): item for item in ocr_results}
    llm_documents = [
        {"index": index, "name": file["name"], "text": str(by_name.get(file.get("name"), {}).get("text") or "")}
        for index, file in enumerate(raw_files)
        if str(by_name.get(file.get("name"), {}).get("text") or "").strip()
    ]

    started = time.monotonic()
    llm_types: dict[int, str] = {}
    if llm_documents:
        try:
            llm_types = await _classify_with_llm(llm_documents)
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
            "llmDocuments": [item["name"] for item in llm_documents],
            "classified": classified,
            "slots": SLOTS,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "ocr_text": join_ocr_documents(ocr_results),
        "llm_output": {str(index): value for index, value in llm_types.items()},
        "errors": errors,
    }

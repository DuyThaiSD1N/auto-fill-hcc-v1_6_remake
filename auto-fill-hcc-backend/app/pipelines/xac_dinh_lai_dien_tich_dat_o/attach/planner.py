"""Đính kèm [Lào Cai] 1.115685 — bảng "Thành phần hồ sơ" của `dichvucong.laocai.gov.vn`.

Bảng PHẲNG đúng 3 dòng theo thứ tự DOM (ảnh ánh xạ hồ sơ mẫu "MẪU HỒ SƠ 2 – MAI XUÂN HẢI"); mỗi dòng
có checkbox chọn giấy tờ ở cột "#", ô "Số bản (*)", nút "Chọn tệp tin", cột "Mẫu đơn" và link "Ký số":

  0. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 24 (QĐ 47/2026/QĐ-UBND)
  1. Giấy chứng nhận đã cấp
  2. Văn bản về việc đại diện theo quy định của pháp luật về dân sự …

Bên dưới là khối "Thông tin khác": ô "Về việc (*)", ô "Ghi chú", danh sách "Giấy tờ khác" (3 dòng
dựng sẵn: select "Loại" mặc định "Mới" + ô tên + nút "Chọn tệp tin" + nút "+/-"), và một ô "Giấy tờ
khác — Chọn tệp tin" ĐỨNG RIÊNG ở cuối trang.

⚑ KHỚP Ô THEO `slotIndex`, KHÔNG theo keyword: bảng phẳng nên engine FE chỉ tra keyword khi slotKey
có mặt trong `FIXED_SLOT_KEYWORDS` của content.js. slotKey ở đây CỐ Ý không nằm trong bảng đó (giống
`dk_giay_cn_thua_dat_dien_tich_tang_them`) để FE dùng thẳng thứ tự DOM — vừa khỏi phải sửa extension,
vừa tránh nhầm giữa dòng 0 ("…đăng ký biến động đất đai, tài sản gắn liền với đất…") và dòng 2
("…thực hiện thủ tục đăng ký đất đai, tài sản gắn liền với đất thông qua người đại diện") vốn dùng
chung gần hết từ ngữ.

`tickRow: True` vì cột "#" của mỗi dòng là checkbox chọn giấy tờ — không tích thì cổng không nhận tệp.
Ảnh ánh xạ chốt: tích dòng ①; dòng ② chỉ tích khi THẬT SỰ có bản scan GCN; dòng ③ không tích khi
người sử dụng đất tự đứng đơn.

⚑ ĐÍNH KÈM CHUNG Ở DÒNG ĐƠN. Hồ sơ mẫu có HAI tệp đơn gần trùng nhau — bản đã ký số
(`donmaixuanhai0001_signed_95_…pdf`, có chữ ký nháy góc trái) và bản chưa ký
(`don_mai_xuan_hai0001_…pdf`) — ảnh ánh xạ ghi "Số bản: 1 · Gắn cả 2 tệp vào dòng này". Engine gom
các item cùng `slotKey` rồi bơm cả loạt vào một ô (xem `attachFilesByFixedSlot`) nên việc này chạy
được mà không phải bỏ tệp nào. Nhưng MỘT TỆP chỉ đi ĐÚNG MỘT DÒNG: không đính một tệp vào hai dòng
(số lượt đính > số tệp làm extension báo "4/3 file"), cũng KHÔNG cắt trang bằng sourceSegments.

⚠ Ô "Về việc (*)" cổng đã điền sẵn đúng nội dung biến động — KHÔNG ghi đè (ảnh ánh xạ: "Giữ nguyên").
Ô "Ghi chú" và 3 dòng "Giấy tờ khác" dựng sẵn để TRỐNG khi hồ sơ không có giấy tờ ngoài bảng; ô "Giấy
tờ khác — Chọn tệp tin" đứng riêng ở cuối trang cũng để trống (nó không nằm trong một `li` có
`input[name="HoSoOnline_giayToKhac[]"]` nên `otherListFileRows()` không bao giờ chọn tới).

`noChooserClick=True` là BẮT BUỘC với cổng iGate VNPT: bấm option "Chọn tệp tin" MỞ HỘP THOẠI FILE
của hệ điều hành và chặn UI — FE phải gán thẳng bằng DataTransfer.

Phân loại THUẦN LLM (không lưới keyword), mỗi file một call để PDF dài/lỗi provider chỉ làm file đó
rơi về "khac". Không rõ loại → dòng "Giấy tờ khác", tuyệt đối không bỏ sót tệp nào.
"""

import asyncio
import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold, normalize_document_name
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# Cổng ghi rõ ngay trên trang: "Dung lượng tối đa là 6 Mb".
_MAX_FILE_BYTES = 6 * 1024 * 1024

_OTHER = "khac"

# 3 dòng cố định của bảng; `slotIndex` là thứ tự DOM 0-based của các ô upload.
_ROWS: dict[int, str] = {
    0: "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 24 ban hành kèm theo "
       "Quyết định số 47/2026/QĐ-UBND",
    1: "Giấy chứng nhận đã cấp",
    2: "Văn bản về việc đại diện theo quy định của pháp luật về dân sự đối với trường hợp thực hiện "
       "thủ tục đăng ký đất đai, tài sản gắn liền với đất thông qua người đại diện",
}

# docType (LLM) → (slotIndex, tên hiển thị của tài liệu).
_ROUTES: dict[str, tuple[int, str]] = {
    "don_bien_dong": (0, "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất"),
    "gcn": (1, "Giấy chứng nhận quyền sử dụng đất đã cấp"),
    "van_ban_dai_dien": (2, "Văn bản về việc đại diện (Giấy ủy quyền)"),
}

# docType KHÔNG có dòng riêng trong bảng → xuống "Giấy tờ khác" (tên dòng = documentName).
_OTHER_ROUTES: dict[str, str] = {
    "ban_an": "Bản án, quyết định của Toà án",
    "to_khai_thue": "Tờ khai lệ phí trước bạ, tờ khai thuế",
    "giay_to_nhan_than": "Căn cước công dân của người sử dụng đất",
    _OTHER: "Tài liệu kèm theo",
}

_ALLOWED = set(_ROUTES) | set(_OTHER_ROUTES)

# Hai dòng là thành phần hồ sơ BẮT BUỘC của thủ tục (cột "Tên giấy tờ" của cổng có dấu * ở "Số bản");
# trống thì phải nhắc cán bộ, không im lặng. Dòng 2 (văn bản đại diện) chỉ cần khi nộp thay nên KHÔNG
# nằm ở đây — ảnh ánh xạ ghi "Không tick. Ông Mai Xuân Hải tự đứng đơn, không qua người đại diện."
_ROWS_BAT_BUOC = {
    0: "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất",
    1: "Giấy chứng nhận đã cấp",
}


def _canon(value: Any) -> str:
    return re.sub(r"[_\-\s]+", "_", fold(value)).strip("_")


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
        {"role": "user",
         "content": build_user_prompt([{"index": index, "text": str(document.get("text") or "")[:12000]}])},
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
                # slotKey theo DÒNG (không theo docType) để nhiều tệp cùng dòng được engine GOM vào
                # một lần bơm tệp — đúng ca "đính kèm chung" 2 bản đơn ký số/chưa ký số của hồ sơ mẫu.
                "slotKey": f"lc_115685_row_{slot_index}",
                "slotIndex": slot_index,
                "slotName": _ROWS[slot_index],
                "tickRow": True,
                "detectedType": doc_type,
            })
            classified.append({
                "fileName": file_name, "docType": doc_type, "source": source, "slotIndex": slot_index,
            })
            continue

        # Không có dòng riêng → "Giấy tờ khác" (target=new: FE lấy dòng trống hoặc bấm "+" thêm dòng,
        # gõ tên rồi gán tệp). Cột "Loại" giữ nguyên giá trị mặc định "Mới".
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
            "Chưa nhận ra loại giấy tờ, đã tạm đưa xuống \"Giấy tờ khác\" để không bỏ sót — cán bộ "
            f"kiểm tra lại tên dòng: {', '.join(unknown)}."
        )

    filled_rows = {item["slotIndex"] for item in attachments if item.get("target") == "fixed-slot"}
    thieu = [name for slot, name in sorted(_ROWS_BAT_BUOC.items()) if slot not in filled_rows]
    if thieu:
        warnings.append(
            "Thiếu thành phần hồ sơ bắt buộc, chưa có tệp cho dòng: " + "; ".join(thieu) + ". Cổng "
            "không chặn lúc nộp nhưng nơi tiếp nhận sẽ trả hồ sơ — cán bộ đề nghị người dân bổ sung "
            "bản scan rồi tích dòng. Riêng Giấy chứng nhận đã cấp có thể thử nút \"Lấy giấy tờ từ "
            "KDL\" nếu giấy của người dân đã có trong kho dữ liệu. KHÔNG tự tạo tệp thay thế."
        )

    # Nhiều tệp cùng vào một dòng là hợp lệ (engine gom theo slotKey) nhưng phải nói ra: ảnh ánh xạ
    # chốt "Số bản: 1" cho dòng Đơn dù gắn 2 tệp, nên cán bộ cần biết để soát lại ô "Số bản".
    for slot_index in sorted(filled_rows):
        cung_dong = [i for i in attachments if i.get("slotIndex") == slot_index]
        if len(cung_dong) > 1:
            ten_tep = ", ".join(i["fileName"] for i in cung_dong)
            warnings.append(
                f"Dòng \"{_ROWS[slot_index][:60]}…\" đang gắn {len(cung_dong)} tệp ({ten_tep}). Hồ sơ "
                "thủ tục này hay có cả bản ĐÃ ký số lẫn bản chưa ký của cùng một giấy tờ — gắn chung "
                "một dòng là đúng, nhưng ô \"Số bản\" vẫn để 1 và cán bộ nên bỏ bớt bản trùng nếu nơi "
                "tiếp nhận yêu cầu."
            )

    if 2 in filled_rows:
        warnings.append(
            "Hồ sơ có Văn bản về việc đại diện → đây là trường hợp NỘP THAY. Kiểm tra lại khối "
            "\"Thông tin người nộp\" ở bước trước phải là nhân thân của NGƯỜI ĐƯỢC ỦY QUYỀN, và tài "
            "khoản đang đăng nhập phải là của chính người đó."
        )

    if attachments:
        warnings.append(
            "Ô \"Về việc (*)\" ở bước Thành phần hồ sơ do cổng điền sẵn theo nội dung biến động — "
            "trợ lý KHÔNG ghi đè, cán bộ giữ nguyên. Ô \"Ghi chú\" và ô \"Giấy tờ khác — Chọn tệp "
            "tin\" đứng riêng cuối trang để TRỐNG; nếu Đơn kê giấy tờ ở mục 3.(2)/3.(3) mà chưa có "
            "tệp thì cán bộ ghi rõ vào \"Ghi chú\"."
        )

    if not attachments:
        warnings.append("Không có tài liệu nào để đính kèm.")
    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]

    # Trần 6 MB tính cho TỪNG TỆP. Bản scan GCN cũ (khổ A3, quét màu) rất hay vượt — cổng chỉ báo lỗi
    # lúc bấm nộp nên phải nói sớm.
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

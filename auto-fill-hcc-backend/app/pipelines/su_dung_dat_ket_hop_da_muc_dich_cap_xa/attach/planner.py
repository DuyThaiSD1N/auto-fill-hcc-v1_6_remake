"""Đính kèm [Lào Cai] 1.115682 — màn hình "Thông tin hồ sơ" của `dichvucong.laocai.gov.vn`.

⚑⚑ KHÁC BIỆT LỚN NHẤT SO VỚI CÁC THỦ TỤC ĐẤT ĐAI LÀO CAI KHÁC: MÀN HÌNH NÀY KHÔNG CÓ BẢNG "THÀNH
PHẦN HỒ SƠ". Theo ảnh ánh xạ hồ sơ mẫu (ông Nguyễn Đức Nhân — TTHC 1.115682), khối "Biểu mẫu giấy
tờ" của trang chỉ in đúng một dòng in nghiêng "(Hồ sơ không yêu cầu giấy tờ kèm theo)" — cổng KHÔNG
dựng sẵn dòng nào để tích và gán tệp. Vì vậy planner này KHÔNG phát `fixed-slot` / `slotIndex` /
`tickRow` nào cả; nếu bê nguyên planner của 1.115685 hay 1.115693 sang thì mọi tệp sẽ đi tìm ô không
tồn tại và không tệp nào được gắn.

Bố cục thật của trang (trái sang phải theo ảnh ánh xạ):
  ① Nút "Lấy giấy tờ từ KDL" — TUỲ CHỌN, chỉ dùng khi người dân đã lưu giấy tờ vào Kho dữ liệu; hệ
    thống không bấm, vì có bấm cũng không biết trong kho có gì.
  ② "Biểu mẫu giấy tờ" → "(Hồ sơ không yêu cầu giấy tờ kèm theo)".
  ③ Ô "Về việc (*)" — CỔNG ĐÃ ĐIỀN SẴN "Sử dụng đất kết hợp đa mục đích (cấp xã)." → KHÔNG ghi đè.
  ④ Ô "Ghi chú" — để trống, chỉ nhắc cán bộ tự ghi nếu cần.
  ⑤⑥⑦ Danh sách "Giấy tờ khác": 3 dòng dựng sẵn, mỗi dòng gồm select "Loại" (mặc định "Mới") + ô
    tên giấy tờ + nút "+/-" + nút "Chọn tệp tin". ĐÂY LÀ NƠI DUY NHẤT ĐÍNH ĐƯỢC TỆP.
  ⑧ Một ô "Giấy tờ khác — Chọn tệp tin" ĐỨNG RIÊNG ở cuối trang. Ô này KHÔNG nằm trong một `li` có
    `input[name="HoSoOnline_giayToKhac[]"]` nên `otherListFileRows()` của content.js không bao giờ
    chọn tới — tệp thứ 4 trở đi được đẩy vào một dòng MỚI của danh sách ⑤⑥⑦ (FE bấm nút "+"), kết
    quả nộp lên là tương đương.

Vì cả ba dòng ⑤⑥⑦ đều là dòng "Giấy tờ khác" tự đặt tên, thứ quyết định hồ sơ đọc được hay không là
`documentName` — nó chính là chữ FE gõ vào ô tên. `_DOC_NAMES` chép ĐÚNG tên giấy tờ theo danh mục
thành phần hồ sơ của TTHC 1.115682 (khớp ảnh ánh xạ dòng ⑤⑥⑦), không phải tên tệp người dân đặt.

`noChooserClick=True` là BẮT BUỘC với cổng iGate VNPT: bấm option "Chọn tệp tin" MỞ HỘP THOẠI FILE
của hệ điều hành và chặn UI — FE phải gán thẳng bằng DataTransfer.

Phân loại THUẦN LLM (không lưới keyword), mỗi file một call để PDF dài/lỗi provider chỉ làm file đó
rơi về "khac". Không rõ loại → vẫn tạo một dòng "Giấy tờ khác" mang tên tệp, tuyệt đối không bỏ sót.
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

# Cổng ghi rõ ngay trên trang: "Tệp tin tải lên có dung lượng không quá 6MB".
_MAX_FILE_BYTES = 6 * 1024 * 1024

_OTHER = "khac"

# docType (LLM) → tên dòng "Giấy tờ khác" sẽ gõ vào ô tên. Ba tên đầu chép đúng danh mục thành phần
# hồ sơ của TTHC 1.115682 như ảnh ánh xạ dòng ⑤⑥⑦ thể hiện.
_DOC_NAMES: dict[str, str] = {
    "gcn": "Giấy chứng nhận đã cấp hoặc một trong các loại giấy tờ về quyền sử dụng đất theo quy "
           "định của pháp luật (nếu có)",
    "don_de_nghi": "Văn bản đề nghị sử dụng đất kết hợp đa mục đích theo Mẫu số 13",
    "phuong_an": "Phương án sử dụng đất kết hợp",
    "giay_to_nhan_than": "Bản sao Căn cước công dân của chủ hộ",
    "van_ban_uy_quyen": "Giấy ủy quyền",
    "to_khai_thue": "Tờ khai lệ phí trước bạ, tờ khai thuế",
    _OTHER: "Tài liệu kèm theo",
}

_ALLOWED = set(_DOC_NAMES)

# Ba giấy tờ CỐT LÕI của bộ hồ sơ. Ảnh ánh xạ đánh dấu dòng ⑤⑥⑦ là ba thứ này; thiếu thì nơi tiếp
# nhận trả hồ sơ nên phải nhắc, không im lặng.
_GIAY_TO_COT_LOI: dict[str, str] = {
    "don_de_nghi": "Văn bản đề nghị sử dụng đất kết hợp đa mục đích theo Mẫu số 13",
    "phuong_an": "Phương án sử dụng đất kết hợp",
    "gcn": "Giấy chứng nhận đã cấp hoặc giấy tờ về quyền sử dụng đất",
}

# Mục 6 của Đơn Mẫu số 13 kê "Bản sao Căn cước công dân của chủ hộ" nhưng hồ sơ mẫu CHƯA có tệp —
# ảnh ánh xạ đánh dấu đỏ ô ⑧ "CHƯA CÓ TỆP, cần scan bổ sung". Nhắc riêng, tách khỏi 3 giấy tờ cốt lõi
# vì đây là giấy do chính Đơn tự kê chứ không phải dòng bắt buộc cổng dựng sẵn.
_CCCD_CHU_HO = "giay_to_nhan_than"


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
    """documentName thành TÊN DÒNG ở "Giấy tờ khác" → hai dòng trùng tên sẽ đè nhau.

    Hai bản của cùng một giấy tờ (bản ký số + bản chưa ký) vẫn phải ra HAI DÒNG khác tên, vì ở màn
    hình này mỗi dòng chỉ giữ được một tệp — khác hẳn bảng phẳng của 1.115685 nơi engine gom nhiều
    tệp vào một ô theo `slotKey`.
    """
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
    used_names: set[str] = set()
    seen_types: set[str] = set()

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        llm_type = llm_types.get(index, "")
        doc_type = llm_type if llm_type in _ALLOWED else _OTHER
        source = "llm" if llm_type else "default"
        seen_types.add(doc_type)

        base_name = _other_display(file_name) if doc_type == _OTHER else _DOC_NAMES[doc_type]
        document_name = _unique_document_name(base_name, used_names)
        if doc_type == _OTHER:
            unknown.append(file_name)

        # Màn hình này CHỈ có danh sách "Giấy tờ khác" → mọi tệp đều là target="new": FE lấy dòng
        # trống hoặc bấm "+" thêm dòng, gõ tên rồi gán tệp. Cột "Loại" giữ nguyên mặc định "Mới".
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": document_name,
            "componentName": document_name,
            "target": "new",
            "needsAddComponent": True,
            "detectedType": doc_type,
            # Cổng iGate VNPT: bấm option "Chọn tệp tin" mở hộp thoại file của hệ điều hành → FE chỉ
            # gán thẳng bằng DataTransfer, không bấm mở chooser.
            "noChooserClick": True,
        })
        classified.append({
            "fileName": file_name, "docType": doc_type, "source": source, "slotIndex": None,
        })

    if unknown:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã tạm đặt tên dòng theo tên tệp để không bỏ sót — cán bộ "
            f"sửa lại tên dòng cho đúng danh mục: {', '.join(unknown)}."
        )

    thieu = [ten for loai, ten in _GIAY_TO_COT_LOI.items() if loai not in seen_types]
    if attachments and thieu:
        warnings.append(
            "Thiếu giấy tờ cốt lõi của bộ hồ sơ, chưa có tệp cho: " + "; ".join(thieu) + ". Màn hình "
            "này KHÔNG có bảng thành phần hồ sơ nên cổng không chặn lúc nộp, nhưng nơi tiếp nhận sẽ "
            "trả hồ sơ — cán bộ đề nghị người dân bổ sung bản scan. Riêng Giấy chứng nhận đã cấp có "
            "thể thử nút \"Lấy giấy tờ từ KDL\" nếu giấy của người dân đã có trong Kho dữ liệu. "
            "KHÔNG tự tạo tệp thay thế."
        )

    if attachments and _CCCD_CHU_HO not in seen_types:
        warnings.append(
            "Mục 6 của Đơn Mẫu số 13 kê \"Bản sao Căn cước công dân của chủ hộ\" nhưng hồ sơ chưa có "
            "tệp CCCD nào. Cán bộ đề nghị người dân scan 2 mặt CCCD của chủ hộ rồi thêm một dòng "
            "\"Giấy tờ khác\" cho giấy này trước khi nộp."
        )

    if attachments:
        warnings.append(
            "Màn hình này KHÔNG có bảng \"Thành phần hồ sơ\" (khối Biểu mẫu giấy tờ chỉ ghi \"Hồ sơ "
            "không yêu cầu giấy tờ kèm theo\") — toàn bộ giấy tờ được đính ở danh sách \"Giấy tờ "
            "khác\", mỗi giấy tờ một dòng, cột \"Loại\" giữ nguyên mặc định \"Mới\". Cán bộ soát lại "
            "tên từng dòng trước khi bấm \"Đồng ý và tiếp tục\"."
        )
        warnings.append(
            "Ô \"Về việc (*)\" cổng đã điền sẵn theo tên thủ tục — trợ lý KHÔNG ghi đè, cán bộ giữ "
            "nguyên. Nếu nơi tiếp nhận muốn nêu rõ đề nghị thì bổ sung thêm một dòng vào ô đó (ví "
            "dụ: đề nghị sử dụng … m² đất kết hợp vào mục đích … tại thửa số …, tờ bản đồ số …) và "
            "dùng con số ở mục 5.2 của Đơn Mẫu số 13. Ô \"Ghi chú\" để trống; nếu có giấy tờ Đơn kê "
            "mà chưa nộp được thì cán bộ ghi rõ vào đó."
        )

    if not attachments:
        warnings.append("Không có tài liệu nào để đính kèm.")
    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]

    # Trần 6 MB tính cho TỪNG TỆP. Tệp Phương án sử dụng đất gộp cả bản đồ + bản vẽ (hồ sơ mẫu 21
    # trang) rất hay vượt — cổng chỉ báo lỗi lúc bấm nộp nên phải nói sớm.
    valid_files: list[dict] = []
    for file in raw_files:
        size = _data_url_size(file.get("dataUrl"))
        if size > _MAX_FILE_BYTES:
            errors.append(
                f"File '{file['name']}' vượt quá 6 MB ({size / 1024 / 1024:.2f} MB) — cổng không nhận, "
                "đã bỏ qua. Tệp Phương án sử dụng đất kèm bản đồ/bản vẽ hay vướng chỗ này: nén PDF "
                "(giảm ảnh quét về 300 dpi) hoặc tách phần thuyết minh và phần bản vẽ thành hai tệp "
                "rồi đính thành hai dòng."
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

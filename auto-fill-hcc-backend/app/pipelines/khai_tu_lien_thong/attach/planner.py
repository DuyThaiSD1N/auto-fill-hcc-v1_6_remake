"""Đính kèm bước 04 cho thủ tục liên thông khai tử.

Bảng thành phần hồ sơ trên cổng (ảnh BA "Anh_xa_giay_to_dinh_kem_Buoc4"):
  Dòng 1 (bắt buộc): Bản chụp Giấy báo tử hoặc giấy tờ thay thế Giấy báo tử.
  Dòng 2: Chứng cứ thay thế — chỉ dùng khi đăng ký cho người chết đã lâu, KHÔNG có dòng 1.
Tờ khai không có dòng riêng; BA chỉ định đính CÙNG dòng với giấy chứng minh sự kiện chết. CCCD
không có dòng nào ở bước này (chỉ xuất trình khi nhận kết quả) nên không đính.

Cổng cho đính nhiều tệp rời vào một dòng (xem khai_sinh_lien_thong.attach.planner), nên mỗi tệp là
một item `repeatUpload`; giấy báo tử đứng trước để nếu cổng chỉ giữ một tệp thì đó là giấy báo tử.
`slotKey` không có trong FIXED_SLOT_KEYWORDS của extension, extension khớp dòng theo `slotIndex`.

Phân loại: tiêu đề chuẩn (TỜ KHAI ĐĂNG KÝ KHAI TỬ, GIẤY BÁO TỬ, thẻ CCCD) quyết định tất định; chỉ
tài liệu không nhận ra theo tiêu đề mới hỏi LLM, để hồ sơ thường gặp không tốn một lượt gọi LLM.
"""
import re
import time
import unicodedata
from typing import Any

from app.config import settings
from app.pipelines.khai_tu_lien_thong.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DOC_DEATH_NOTICE = "death_notice"
_DOC_DEATH_EVENT_PROOF = "death_event_proof"
_DOC_DECLARATION = "paper_declaration"
_DOC_IDENTITY = "identity"
_DOC_OTHER = "other"
_LLM_TYPES = {_DOC_DEATH_NOTICE, _DOC_DEATH_EVENT_PROOF, _DOC_DECLARATION, _DOC_IDENTITY, _DOC_OTHER}

_DOCUMENT_LABELS = {
    _DOC_DEATH_NOTICE: "Giấy báo tử",
    _DOC_DEATH_EVENT_PROOF: "Giấy tờ chứng minh sự kiện chết",
    _DOC_DECLARATION: "Tờ khai đăng ký khai tử",
}

_DEATH_NOTICE_SLOT = {
    "slotIndex": 0,
    "slotKey": "lien_thong_khai_tu_giay_bao_tu",
    "slotName": "Bản chụp Giấy báo tử hoặc giấy tờ thay thế Giấy báo tử",
}
_DEATH_EVENT_PROOF_SLOT = {
    "slotIndex": 1,
    "slotKey": "lien_thong_khai_tu_chung_cu_thay_the",
    "slotName": "Chứng cứ thay thế Giấy báo tử (người chết đã lâu)",
}

# Một dòng chỉ gồm tiêu đề "GIẤY BÁO TỬ"/"GIẤY CHỨNG TỬ" (text đã fold, giữ xuống dòng).
_DEATH_NOTICE_TITLE_RE = re.compile(r"(?m)^[^a-z0-9\n]*giay (?:bao|chung) tu[^a-z0-9\n]*$")
# Nhãn chỉ có trong nội dung giấy báo tử thật, dùng để xác nhận khi OCR dính tiêu đề vào dòng sau.
_DEATH_NOTICE_BODY_MARKERS = ("nguoi bao tu", "ho ten nguoi chet", "da chet vao luc", "nguyen nhan chet")


def _fold(value: str) -> str:
    """Bỏ dấu, lowercase, gom khoảng trắng nhưng GIỮ xuống dòng để nhận tiêu đề theo dòng."""
    text = unicodedata.normalize("NFD", value or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d").lower()
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines())


def _is_identity_head(head: str) -> bool:
    is_identity_card = (
        ("identity card" in head or "citizen identity card" in head)
        and ("full name" in head or "personal identification number" in head or "so / no" in head)
    ) or (
        ("can cuoc cong dan" in head or re.search(r"\bcan cuoc\b", head))
        and ("ho va ten" in head or "ho, chu dem va ten khai sinh" in head or "so / no" in head)
    )
    return bool(is_identity_card or "chung minh nhan dan" in head or "passport" in head or "ho chieu" in head)


def _rule_type(text: str) -> str | None:
    """Loại tài liệu theo tiêu đề chuẩn; None khi không đủ chắc để khỏi hỏi LLM."""
    folded = _fold(text)
    if not folded.strip():
        return None
    head = folded[:1500]
    has_notice_title = bool(_DEATH_NOTICE_TITLE_RE.search(folded))
    if "to khai dang ky khai tu" in head:
        # Tờ khai có sẵn nhãn "Số Giấy báo tử/Giấy tờ thay thế..." nên chỉ tính là giấy báo tử khi cùng
        # file có trang mang đúng tiêu đề GIẤY BÁO TỬ (quét chung một PDF, vẫn vào dòng 1).
        return _DOC_DEATH_NOTICE if has_notice_title else _DOC_DECLARATION
    # Nhắc tên "giấy báo tử" thôi thì CHƯA đủ: ảnh chụp màn hình cổng, danh sách tệp hay tài liệu
    # dẫn chiếu cũng có cụm đó. Cần tiêu đề đứng riêng một dòng, hoặc kèm nhãn nội dung thật.
    nhac_ten = bool(re.search(r"giay (?:bao|chung) tu", head)) and "trich luc" not in head
    if has_notice_title or (nhac_ten and any(marker in head for marker in _DEATH_NOTICE_BODY_MARKERS)):
        return _DOC_DEATH_NOTICE
    if _is_identity_head(head):
        return _DOC_IDENTITY
    return None


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    """Trả {fileIndex: docType}. Index thiếu/sai thì bỏ để bên gọi giữ `other`, không đoán theo vị trí."""
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=400, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    valid = {doc["index"] for doc in documents}
    out: dict[int, str] = {}
    for item in parsed.get("documents", []) or []:
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        doc_type = str(item.get("docType") or "").strip().lower()
        if idx in valid:
            out[idx] = doc_type if doc_type in _LLM_TYPES else _DOC_OTHER
    return out


async def plan_khai_tu_lien_thong_attachments(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    _ = options or {}
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]

    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for result in ocr_results:
        if result.get("error"):
            errors.append(f"OCR {result.get('name')}: {result['error']}")

    # ocr_per_file trả đúng thứ tự đầu vào. Ghép theo VỊ TRÍ, không theo tên: hai file cùng tên
    # (image.pdf) là chuyện thường khi chụp từ điện thoại.
    ocr_iter = iter(ocr_results)
    texts = [
        str(next(ocr_iter, {}).get("text") or "") if f.get("type") in _OCR_TYPES else ""
        for f in raw_files
    ]

    final_types: dict[int, str] = {}
    sources: dict[int, str] = {}
    unresolved: list[int] = []
    for idx, text in enumerate(texts):
        rule_type = _rule_type(text)
        if rule_type:
            final_types[idx] = rule_type
            sources[idx] = "rule"
        else:
            unresolved.append(idx)

    t1 = time.monotonic()
    llm_types: dict[int, str] = {}
    if unresolved:
        try:
            llm_types = await _classify_with_llm([
                {"index": idx, "fileName": raw_files[idx]["name"], "text": texts[idx]}
                for idx in unresolved
            ])
        except Exception as e:  # noqa: BLE001
            errors.append(f"attachment_agent: {e}")
    llm_ms = int((time.monotonic() - t1) * 1000)
    for idx in unresolved:
        final_types[idx] = llm_types.get(idx, _DOC_OTHER)
        sources[idx] = "llm" if idx in llm_types else "default"

    indices_of = lambda doc_type: [i for i in range(len(raw_files)) if final_types[i] == doc_type]  # noqa: E731
    notices = indices_of(_DOC_DEATH_NOTICE)
    proofs = indices_of(_DOC_DEATH_EVENT_PROOF)
    declarations = indices_of(_DOC_DECLARATION)

    # Dòng 2 chỉ dùng khi không có giấy báo tử: có dòng 1 thì chứng cứ thay thế bị bỏ qua.
    if notices:
        slot, main = _DEATH_NOTICE_SLOT, notices
    elif proofs:
        slot, main = _DEATH_EVENT_PROOF_SLOT, proofs
    else:
        slot, main = None, []
        errors.append(
            "Không tìm thấy Giấy báo tử (hoặc giấy tờ thay thế/chứng cứ chứng minh sự kiện chết) "
            "trong các file đã tải lên."
        )

    attachments: list[dict] = []
    if slot:
        for idx in (*main, *declarations):
            label = _DOCUMENT_LABELS[final_types[idx]]
            attachments.append({
                "fileIndex": idx,
                "fileName": raw_files[idx]["name"],
                "documentName": label,
                "componentName": slot["slotName"],
                "target": "fixed-slot",
                **slot,
                "needsAddComponent": False,
                "repeatUpload": True,
                "detectedType": label,
            })

    attached = {item["fileIndex"] for item in attachments}
    skipped = [raw_files[i]["name"] for i in range(len(raw_files)) if i not in attached]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [raw_files[i]["name"] for i in unresolved],
            "classified": [
                {"fileName": f["name"], "docType": final_types[i], "source": sources[i]}
                for i, f in enumerate(raw_files)
            ],
            "skipped": skipped,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "errors": errors,
    }


# Entrypoint thống nhất cho registry app.pipelines.<procedure>.attach.
plan = plan_khai_tu_lien_thong_attachments

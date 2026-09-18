"""Đính kèm bước "Thành phần hồ sơ" cho "Cho thuê, cho thuê mua nhà ở xã hội…" (cổng DVC Bộ Xây dựng
dvc.moc.gov.vn — Angular mat-table, engine FE `attp-row`, CÙNG cổng #63/#76/#78/#113).

Bảng có 8 dòng (hồ sơ THUÊ chỉ dùng 4 dòng liên quan, đều "Bản chính"):
  "Đơn đăng ký thuê nhà ở xã hội theo mẫu"                             ← Tờ đơn (to_don)
  "Giấy tờ chứng minh điều kiện được hưởng chính sách…nhà ở xã hội"     ← CM ĐIỀU KIỆN (dieu_kien)
  "Giấy tờ chứng minh đối tượng theo hướng dẫn của Bộ trưởng Bộ Xây dựng, Bộ trưởng Bộ Quốc phòng,
   Bộ trưởng Bộ Công an VÀ giấy tờ chứng minh thuộc đối tượng được MIỄN, GIẢM tiền thuê nhà ở xã hội
   (nếu có)"                                                           ← CM ĐỐI TƯỢNG (doi_tuong)
  "Trường hợp thuê nhà ở xã hội"                                       ← CCCD/giấy tờ tùy thân

⚑ KHÔNG dùng componentIndex: thứ tự dòng trên cổng KHÔNG ổn định (đã quan sát 2 thứ tự khác nhau cho
cùng thủ tục). FE (`findAttachmentRowByComponent`) chỉ tin index khi nó ĐỒNG THỜI khớp text, nên bỏ hẳn
index và khớp bằng componentName là đường an toàn duy nhất.

⚑ BẢNG CÓ HAI DÒNG "chứng minh đối tượng" GẦN TRÙNG NHAU:
  (a) "…Bộ trưởng Bộ Công an VÀ giấy tờ chứng minh thuộc đối tượng được miễn, giảm tiền thuê…(nếu có)"
  (b) "…Bộ trưởng Bộ Công an."  ← ngắn hơn, là TIỀN TỐ của (a)
`componentTextMatches` so substring HAI CHIỀU, nên componentName cắt ở "…Bộ trưởng Bộ Xây dựng" khớp CẢ
HAI dòng và rơi vào dòng nào đứng trước trong DOM. Phải lấy đoạn CHỈ CÓ Ở (a) — cụm "miễn, giảm tiền
thuê nhà ở xã hội" — thì mới chốt đúng dòng (a) theo yêu cầu nghiệp vụ.

Các dòng "thuê MUA" không dùng vì hồ sơ chọn THUÊ.

Tách ĐỐI TƯỢNG ↔ ĐIỀU KIỆN theo đúng NĐ 100/2024: giấy chứng nhận ĐỐI TƯỢNG chính sách (huân/huy
chương kháng chiến, bằng khen, thương binh, người có công, quân nhân/công an, miễn-giảm tiền thuê)
đi dòng "…theo hướng dẫn của Bộ trưởng Bộ Xây dựng…"; giấy chứng minh ĐIỀU KIỆN (thu nhập, hộ
nghèo/cận nghèo, thực trạng nhà ở, hợp đồng lao động KCN) đi dòng [1].

componentName lấy đoạn text ĐẶC TRƯNG, KHÔNG lồng nhau: "thuê nhà ở xã hội theo mẫu" ≠ "thuê MUA nhà…";
"Trường hợp thuê nhà ở xã hội" ≠ "Trường hợp thuê mua…".

Phân loại **THUẦN LLM** (không còn lưới keyword quét OCR). Tài liệu không nhận ra loại KHÔNG bị bỏ qua:
mọi file đều được đính, file chưa rõ loại về dòng "chứng minh đối tượng…miễn, giảm…(nếu có)" — dòng rộng
nhất của bảng — kèm cảnh báo cho cán bộ soát. Tuyệt đối không bỏ sót file nào.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.cho_thue_thue_mua_nha_o_xa_hoi.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_TO_DON = "to_don"
_DIEU_KIEN = "dieu_kien"
_DOI_TUONG = "doi_tuong"
_CCCD = "cccd"
_OTHER = "other"

# componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng, FE khớp substring đã fold dấu (componentTextMatches).
_ROWS: dict[str, dict[str, Any]] = {
    _TO_DON: {
        "componentName": "Đơn đăng ký thuê nhà ở xã hội theo mẫu",
        "loaiBan": "Bản chính",
        "documentName": "Đơn đăng ký thuê nhà ở xã hội theo mẫu",
    },
    _DIEU_KIEN: {
        "componentName": "Giấy tờ chứng minh điều kiện được hưởng chính sách hỗ trợ về nhà ở xã hội",
        "loaiBan": "Bản chính",
        "documentName": "Giấy tờ chứng minh điều kiện được hưởng chính sách hỗ trợ về nhà ở xã hội",
    },
    # componentName PHẢI chứa cụm "miễn, giảm tiền thuê nhà ở xã hội" — đó là phần DUY NHẤT phân biệt
    # dòng này với dòng "…Bộ trưởng Bộ Công an." đứng ngay cạnh (xem khối ⚑ ở docstring).
    _DOI_TUONG: {
        "componentName": "giấy tờ chứng minh thuộc đối tượng được miễn, giảm tiền thuê nhà ở xã hội",
        "loaiBan": "Bản chính",
        # documentName TRỞ THÀNH TÊN TỆP tải lên → giữ ngắn: tên dòng đầy đủ dài ~200 ký tự, cộng hậu tố
        # đánh số và đuôi file là chạm trần 255 byte của filesystem.
        "documentName": "Giấy tờ chứng minh đối tượng được miễn, giảm tiền thuê nhà ở xã hội",
    },
    _CCCD: {
        "componentName": "Trường hợp thuê nhà ở xã hội",
        "loaiBan": "Bản chính",
        "documentName": "Giấy tờ chứng minh đối tượng - trường hợp thuê nhà ở xã hội (CCCD/tùy thân)",
    },
}
_ALLOWED_DOC_TYPES = set(_ROWS) | {_OTHER}

# Dòng nhận tài liệu chưa nhận ra loại: rộng nhất bảng ("…và giấy tờ chứng minh thuộc đối tượng được
# miễn, giảm…(nếu có)") nên nhận được mọi giấy tờ chứng minh đối tượng mà OCR đọc không rõ.
_FALLBACK_ROW = _DOI_TUONG


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if "don" in text and "thue" in text:
        return _TO_DON
    if "cccd" in text or "can cuoc" in text or "chung minh nhan dan" in text:
        return _CCCD
    if "doi tuong" in text or "huy chuong" in text or "huan chuong" in text or "co cong" in text:
        return _DOI_TUONG
    if "dieu kien" in text or "chinh sach" in text or "thu nhap" in text:
        return _DIEU_KIEN
    return value if value in _ALLOWED_DOC_TYPES else _OTHER


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=500, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    parsed_docs = parsed.get("documents", []) or []
    out: dict[int, str] = {}

    def _type_of(item: dict) -> str:
        return _normalize_doc_type(str(item.get("docType") or item.get("type") or ""))

    # Đủ số phần tử → map theo THỨ TỰ MẢNG. Field "index" do LLM tự đánh hay lệch một nhịp, nhất là khi
    # danh sách gửi đi bị khuyết index (file không có OCR text thì không được gửi cho LLM).
    if len(parsed_docs) == len(documents):
        for pos, item in enumerate(parsed_docs):
            out[int(documents[pos]["index"])] = _type_of(item)
        return out
    valid = {int(doc["index"]) for doc in documents}
    for item in parsed_docs:
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        if idx in valid:
            out[idx] = _type_of(item)
    return out


def _build_row_item(file: dict, file_index: int, row_key: str, detected_type: str) -> dict:
    row = _ROWS[row_key]
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": row["documentName"],
        "componentName": row["componentName"],
        "loaiBan": row["loaiBan"],
        "target": "attp-row",
        "needsAddComponent": False,
        "detectedType": detected_type,
    }


def _dedupe_document_names(items: list[dict]) -> None:
    """Đánh số các documentName trùng nhau trong cùng một dòng.

    Engine attp-row đặt TÊN TỆP TẢI LÊN theo documentName (`dataUrlToFile(payload, item.documentName)`)
    và chống trùng bằng chính tên đó (`attpRowHasDoc`). Nhiều file cùng một dòng mà trùng tên sẽ đè lên
    nhau ở cổng, và lần đính lại sẽ bị coi là "đã có" rồi bỏ qua hết.
    """
    seen: dict[str, int] = {}
    for item in items:
        name = item["documentName"]
        seen[name] = seen.get(name, 0) + 1
    counter: dict[str, int] = {}
    for item in items:
        name = item["documentName"]
        if seen[name] < 2:
            continue
        counter[name] = counter.get(name, 0) + 1
        item["documentName"] = f"{name} ({counter[name]})"


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    _ = ocr_results  # OCR chỉ để nuôi LLM; planner KHÔNG tự đọc text để đoán loại.
    llm_types = llm_types or {}
    items: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    unknown: list[str] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        llm_type = llm_types.get(idx, "")
        doc_type = llm_type if llm_type in _ROWS else _OTHER
        source = "llm" if llm_type in _ROWS else ("llm" if idx in llm_types else "unknown")
        row_key = doc_type if doc_type in _ROWS else _FALLBACK_ROW
        items.append(_build_row_item(file, idx, row_key, doc_type))
        classified.append({
            "fileName": file_name, "docType": doc_type, "source": source,
            "componentName": _ROWS[row_key]["componentName"],
        })
        if doc_type == _OTHER:
            unknown.append(file_name)

    _dedupe_document_names(items)
    if unknown:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã tạm đính vào dòng \"Giấy tờ chứng minh đối tượng… được "
            f"miễn, giảm tiền thuê nhà ở xã hội (nếu có)\" để không bỏ sót — cán bộ kiểm tra lại: "
            f"{', '.join(unknown)}."
        )
    return items, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options or {}
    _ = session
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]

    from app.services import ocr

    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    ocr_by_name = {item.get("name"): item for item in ocr_results}
    llm_docs: list[dict[str, Any]] = []
    for idx, file in enumerate(raw_files):
        text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        if text.strip():
            llm_docs.append({"index": idx, "text": text})

    t1 = time.monotonic()
    llm_types: dict[int, str] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types)
    errors.extend(warnings)
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [raw_files[doc["index"]]["name"] for doc in llm_docs],
            "classified": classified,
            "skippedOcr": skipped_ocr,
            "rows": [{"docType": k, **v} for k, v in _ROWS.items()],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

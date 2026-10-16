"""Đính kèm [Lào Cai] 1.012790 — bảng "Thành phần hồ sơ" của cổng `dichvucong.laocai.gov.vn`.

Bảng PHẲNG 4 dòng theo thứ tự DOM (theo ảnh ánh xạ đính kèm); mỗi dòng có checkbox + "Số bản" + nút "Chọn tệp
tin" + "Ký số":

   0. Bản gốc Giấy chứng nhận đã cấp
   1. Giấy tờ chứng minh sai sót thông tin của người được cấp Giấy chứng nhận so với thông tin tại thời điểm đề
      nghị đính chính hoặc sai sót thông tin về thửa đất, tài sản gắn liền với đất…
   2. Văn bản về việc ủy quyền theo quy định của pháp luật về dân sự (thực hiện thủ tục qua người đại diện)
   3. Đơn đề nghị đính chính Giấy chứng nhận đối với trường hợp phát hiện sai sót do lỗi của người sử dụng đất…
      — dòng BẮT BUỘC ("tệp tin và giấy").

Dòng nào không có tệp thì KHÔNG tích (ảnh ánh xạ: căn cứ sai sót nằm sẵn trong GCN thì dòng 1 để trống, không
tách/đính lại). Bên dưới: khối "Thông tin cung cấp thêm" (nhập tay — mapper gửi gợi ý), "Về việc" (*) cổng điền
sẵn — giữ nguyên, "Ghi chú" tùy chọn, danh sách "Giấy tờ khác" (CCCD, giấy kết hôn, giấy tờ lạ).

Khớp ô theo `slotIndex` + `tickRow`; mỗi file đính NGUYÊN, không tách trang. Nhiều tệp cùng loại → GOM vào MỘT
dòng (chung slotKey), "Số bản" = số tệp của dòng. Tệp trùng NỘI DUNG 100% thì không đính lại, chỉ cảnh báo.
"""

import asyncio
import time

from app.config import settings
from app.pipelines.dang_ky_bien_dong_chuyen_nhuong_thua_ke_tang_cho_dvcqg_lao_cai.attach.planner import (
    _payload_digest,
)
from app.pipelines.xac_nhan_tiep_tuc_dat_nong_nghiep.attach.planner import (
    _canon,
    _data_url_size,
    _other_display,
    _unique_document_name,
)
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
# Cổng ghi rõ trên trang: "Dung lượng tối đa là 6 Mb".
_MAX_FILE_BYTES = 6 * 1024 * 1024

_OTHER = "khac"

# 4 dòng của bảng; `slotIndex` là thứ tự DOM 0-based của các ô upload.
_ROWS: dict[int, str] = {
    0: "Bản gốc Giấy chứng nhận đã cấp",
    1: "Giấy tờ chứng minh sai sót thông tin của người được cấp Giấy chứng nhận so với thông tin tại thời điểm "
       "đề nghị đính chính hoặc sai sót thông tin về thửa đất, tài sản gắn liền với đất so với thông tin trên "
       "Giấy chứng nhận đã cấp",
    2: "Văn bản về việc ủy quyền theo quy định của pháp luật về dân sự đối với trường hợp thực hiện thủ tục "
       "thông qua người đại diện",
    3: "Đơn đề nghị đính chính Giấy chứng nhận đối với trường hợp phát hiện sai sót do lỗi của người sử dụng "
       "đất, chủ sở hữu tài sản gắn liền với đất",
}

# docType (LLM) → (slotIndex, tên hiển thị của tài liệu).
_ROUTES: dict[str, tuple[int, str]] = {
    "gcn": (0, "Giấy chứng nhận đã cấp"),
    "chung_minh_sai_sot": (1, "Giấy tờ chứng minh sai sót"),
    "uy_quyen": (2, "Văn bản ủy quyền"),
    "don_bien_dong": (3, "Đơn đề nghị đính chính Giấy chứng nhận"),
}

# docType KHÔNG có dòng riêng → "Giấy tờ khác" (tên dòng = documentName).
_OTHER_ROUTES: dict[str, str] = {
    "cccd": "Căn cước công dân",
    "ket_hon": "Giấy chứng nhận kết hôn",
    _OTHER: "Tài liệu kèm theo",
}

_ALLOWED = set(_ROUTES) | set(_OTHER_ROUTES)

_ROW_GCN = 0
_ROW_DON = 3


def _normalize_doc_type(value) -> str:
    canon = _canon(value)
    for doc_type in _ALLOWED:
        if canon == _canon(doc_type):
            return doc_type
    return _OTHER


async def _classify_one(document: dict) -> tuple[int, str]:
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


async def _classify_with_llm(documents: list[dict], errors: list[str] | None = None) -> dict[int, str]:
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
    trung_lap: list[str] = []
    used_other_names: set[str] = set()
    seen_payloads: dict[str, str] = {}

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        llm_type = llm_types.get(index, "")
        doc_type = llm_type if llm_type in _ALLOWED else _OTHER
        source = "llm" if llm_type else "default"

        digest = _payload_digest(file)
        if digest and digest in seen_payloads:
            trung_lap.append(f"{file_name} (trùng {seen_payloads[digest]})")
            classified.append({
                "fileName": file_name, "docType": doc_type, "source": source, "slotIndex": None,
                "duplicateOf": seen_payloads[digest],
            })
            continue
        if digest:
            seen_payloads[digest] = file_name

        if doc_type in _ROUTES:
            slot_index, document_name = _ROUTES[doc_type]
            attachments.append({
                "fileIndex": index,
                "fileName": file_name,
                "documentName": document_name,
                "componentName": _ROWS[slot_index],
                "target": "fixed-slot",
                "needsAddComponent": False,
                # slotKey theo DÒNG để nhiều tệp cùng dòng được GOM vào một lần bơm tệp.
                "slotKey": f"lc_012790_row_{slot_index}",
                "slotIndex": slot_index,
                "slotName": _ROWS[slot_index],
                "tickRow": True,
                "detectedType": doc_type,
            })
            classified.append({
                "fileName": file_name, "docType": doc_type, "source": source, "slotIndex": slot_index,
            })
            continue

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
            # iGate VNPT: bấm "Chọn tệp tin" mở hộp thoại file của hệ điều hành → FE chỉ gán thẳng.
            "noChooserClick": True,
        })
        classified.append({"fileName": file_name, "docType": doc_type, "source": source, "slotIndex": None})

    # "Số bản" của dòng = số tệp đính vào dòng đó (ô mặc định 1). FE đọc soBan của item đầu nhóm slotKey.
    so_tep: dict[int, int] = {}
    for item in attachments:
        if item.get("target") == "fixed-slot":
            so_tep[item["slotIndex"]] = so_tep.get(item["slotIndex"], 0) + 1
    for item in attachments:
        if item.get("target") == "fixed-slot":
            item["soBan"] = so_tep[item["slotIndex"]]

    if trung_lap:
        warnings.append(
            "Tệp trùng nội dung hoàn toàn với tệp đã có nên KHÔNG đính lại (tránh nộp hai lần cùng một giấy): "
            + ", ".join(trung_lap) + "."
        )
    if unknown:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã tạm đưa xuống \"Giấy tờ khác\" để không bỏ sót — cán bộ kiểm "
            f"tra lại: {', '.join(unknown)}."
        )
    if _ROW_DON not in so_tep:
        warnings.append(
            "Chưa có tệp nào cho dòng \"Đơn đề nghị đính chính Giấy chứng nhận\" — đây là thành phần hồ sơ BẮT "
            "BUỘC; cán bộ đề nghị người dân bổ sung Đơn (Mẫu số 24) rồi tích dòng."
        )
    if _ROW_GCN in so_tep:
        warnings.append(
            "Dòng \"Bản gốc Giấy chứng nhận đã cấp\": ngoài tệp đính kèm, người dân phải nộp BẢN GỐC Giấy chứng "
            "nhận tại Bộ phận một cửa."
        )
    else:
        warnings.append(
            "Chưa có tệp Giấy chứng nhận đã cấp — dòng \"Bản gốc Giấy chứng nhận đã cấp\" để trống, cán bộ đề "
            "nghị người dân bổ sung."
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

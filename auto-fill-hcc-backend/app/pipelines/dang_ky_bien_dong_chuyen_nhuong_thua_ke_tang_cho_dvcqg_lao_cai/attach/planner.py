"""Đính kèm [Lào Cai] 1.013831 — bảng "Thành phần hồ sơ" của cổng `dichvucong.laocai.gov.vn`.

Bảng PHẲNG 15 dòng theo thứ tự DOM (theo ảnh ánh xạ đính kèm); mỗi dòng có checkbox + "Số bản" + nút "Chọn
tệp tin" + "Ký số":

   0. Văn bản tặng cho QSDĐ hoặc biên bản họp đại diện thôn, tổ dân phố… về việc tặng cho QSDĐ
   1. Tờ khai thuế thu nhập doanh nghiệp hoặc tờ khai thuế thu nhập cá nhân
   2. Văn bản thỏa thuận về việc cấp chung một Giấy chứng nhận (nhiều người nhận chuyển quyền)
   3. Văn bản về việc cho thuê, cho thuê lại QSDĐ trong dự án xây dựng kinh doanh kết cấu hạ tầng
   4. Văn bản chấp thuận của cơ quan Nhà nước cho tổ chức kinh tế nhận chuyển nhượng, góp vốn, thuê đất NN
   5. (1) Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18 (NĐ 151/2025/NĐ-CP)
   6. Bản gốc Giấy chứng nhận đã cấp
   7. Biên bản họp giữa UBND cấp xã với người sử dụng đất về việc tặng cho QSDĐ (chỉ nộp bản gốc GCN…)
   8. Hợp đồng, văn bản về việc chuyển nhượng, tặng cho, thừa kế, góp vốn… (Hợp đồng chuyển nhượng QSDĐ)
   9. Văn bản về việc đại diện theo quy định của pháp luật về dân sự  → ánh xạ KHÔNG dùng: Giấy ủy quyền
      xuống "Giấy tờ khác" tên "Ủy quyền".
  10. Văn bản của người sử dụng đất đồng ý cho chủ sở hữu tài sản gắn liền với đất…
  11. Bản vẽ tách thửa đất, hợp thửa đất theo Mẫu số 22
  12. Mảnh trích đo bản đồ địa chính thửa đất
  13. Văn bản của bên nhận thế chấp về việc đồng ý cho bên thế chấp được chuyển nhượng, tặng cho…
  14. Tờ khai lệ phí trước bạ

Bên dưới: "Lấy giấy tờ từ KDL" (không dùng), "Về việc" (*) do cổng điền sẵn — giữ nguyên, "Ghi chú" để cán
bộ tự ghi, và danh sách "Giấy tờ khác" (Loại "Mới", tự gõ tên rồi chọn tệp).

Khớp ô theo `slotIndex` + `tickRow`; slotKey CỐ Ý không nằm trong `FIXED_SLOT_KEYWORDS` của content.js để FE
dùng thẳng thứ tự DOM. Hồ sơ nhiều thửa có NHIỀU tệp cùng loại (2 Đơn, 2 GCN, 2 tờ khai LPTB) → GOM vào MỘT
dòng (chung slotKey) và ghi "Số bản" = số tệp của dòng. Tệp trùng NỘI DUNG 100% với tệp đã có (người dân tải
hai lần) thì KHÔNG đính lại, chỉ cảnh báo. Mỗi thửa cần một bộ Đơn / tờ khai riêng → số tệp ít hơn số Giấy
chứng nhận thì nhắc bổ sung.
"""

import asyncio
import hashlib
import re
import time

from app.config import settings
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

# 15 dòng của bảng; `slotIndex` là thứ tự DOM 0-based của các ô upload.
_ROWS: dict[int, str] = {
    0: "Văn bản tặng cho quyền sử dụng đất hoặc biên bản họp giữa đại diện thôn, ấp, làng, bản, buôn, bon, "
       "phum, sóc, tổ dân phố, điểm dân cư về việc tặng cho quyền sử dụng đất",
    1: "Tờ khai thuế thu nhập doanh nghiệp hoặc tờ khai thuế thu nhập cá nhân",
    2: "Văn bản thỏa thuận về việc cấp chung một Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn "
       "liền với đất",
    3: "Văn bản về việc cho thuê, cho thuê lại quyền sử dụng đất trong dự án xây dựng kinh doanh kết cấu hạ tầng",
    4: "Văn bản chấp thuận của cơ quan Nhà nước có thẩm quyền đối với tổ chức kinh tế nhận chuyển nhượng, nhận "
       "góp vốn, thuê quyền sử dụng đất nông nghiệp để thực hiện dự án đầu tư",
    5: "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18 ban hành kèm theo Nghị định số "
       "151/2025/NĐ-CP",
    6: "Bản gốc Giấy chứng nhận đã cấp",
    7: "Biên bản họp giữa Ủy ban nhân dân cấp xã với người sử dụng đất về việc tặng cho quyền sử dụng đất",
    8: "Hợp đồng, văn bản về việc chuyển đổi, chuyển nhượng, thừa kế, tặng cho, góp vốn bằng quyền sử dụng "
       "đất, tài sản gắn liền với đất",
    9: "Văn bản về việc đại diện theo quy định của pháp luật về dân sự",
    10: "Văn bản của người sử dụng đất đồng ý cho chủ sở hữu tài sản gắn liền với đất được chuyển đổi, chuyển "
        "nhượng, tặng cho, góp vốn tài sản gắn liền với đất",
    11: "Bản vẽ tách thửa đất, hợp thửa đất theo Mẫu số 22",
    12: "Mảnh trích đo bản đồ địa chính thửa đất",
    13: "Văn bản của bên nhận thế chấp về việc đồng ý cho bên thế chấp được chuyển nhượng, tặng cho quyền sử "
        "dụng đất, quyền sở hữu tài sản gắn liền với đất",
    14: "Tờ khai lệ phí trước bạ",
}

# docType (LLM) → (slotIndex, tên hiển thị của tài liệu).
_ROUTES: dict[str, tuple[int, str]] = {
    "tang_cho_cong_dong": (0, "Văn bản tặng cho quyền sử dụng đất / biên bản họp về việc tặng cho"),
    "to_khai_tncn": (1, "Tờ khai thuế thu nhập cá nhân"),
    "thoa_thuan_cap_chung": (2, "Văn bản thỏa thuận cấp chung Giấy chứng nhận"),
    "cho_thue_ha_tang": (3, "Văn bản cho thuê, cho thuê lại quyền sử dụng đất"),
    "chap_thuan_to_chuc": (4, "Văn bản chấp thuận của cơ quan nhà nước"),
    "don_bien_dong": (5, "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất"),
    "gcn": (6, "Bản gốc Giấy chứng nhận đã cấp"),
    "hop_dong": (8, "Hợp đồng, văn bản chuyển quyền sử dụng đất"),
    "dong_y_chu_tai_san": (10, "Văn bản đồng ý của người sử dụng đất"),
    "ban_ve_tach_thua": (11, "Bản vẽ tách thửa, hợp thửa đất"),
    "manh_trich_do": (12, "Mảnh trích đo bản đồ địa chính thửa đất"),
    "dong_y_nhan_the_chap": (13, "Văn bản đồng ý của bên nhận thế chấp"),
    "to_khai_lptb": (14, "Tờ khai lệ phí trước bạ"),
}

# docType KHÔNG có dòng riêng → "Giấy tờ khác" (tên dòng = documentName, theo ảnh ánh xạ).
_OTHER_ROUTES: dict[str, str] = {
    "uy_quyen": "Ủy quyền",
    "cccd": "Photo CCCD",
    "ket_hon": "Giấy chứng nhận kết hôn",
    _OTHER: "Tài liệu kèm theo",
}

_ALLOWED = set(_ROUTES) | set(_OTHER_ROUTES)

# Dòng 5, 6 là thành phần hồ sơ BẮT BUỘC của mọi trường hợp — trống thì phải nhắc.
_ROWS_CAN_NHAC = {
    5: "Đơn đăng ký biến động đất đai (Mẫu số 18)",
    6: "Bản gốc Giấy chứng nhận đã cấp",
}

# Mỗi thửa / mỗi Giấy chứng nhận cần một bản riêng của các giấy này.
_THEO_TUNG_GCN: dict[str, str] = {
    "don_bien_dong": "Đơn đăng ký biến động",
    "to_khai_lptb": "Tờ khai lệ phí trước bạ",
    "to_khai_tncn": "Tờ khai thuế thu nhập cá nhân",
}


def _normalize_doc_type(value) -> str:
    canon = _canon(value)
    for doc_type in _ALLOWED:
        if canon == _canon(doc_type):
            return doc_type
    return _OTHER


def _payload_digest(file: dict) -> str | None:
    payload = re.sub(r"\s+", "", str(file.get("dataUrl") or "").partition(",")[2])
    return hashlib.sha256(payload.encode("ascii", "ignore")).hexdigest() if payload else None


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
                # slotKey theo DÒNG để nhiều tệp cùng dòng (hồ sơ nhiều thửa) được GOM vào một lần bơm tệp.
                "slotKey": f"lc_013831_row_{slot_index}",
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

    thieu = [name for slot, name in sorted(_ROWS_CAN_NHAC.items()) if slot not in so_tep]
    if thieu:
        warnings.append(
            "Chưa có tệp nào cho dòng: " + "; ".join(thieu) + ". Đây là thành phần hồ sơ bắt buộc của "
            "thủ tục — cán bộ đề nghị người dân bổ sung rồi tích dòng."
        )

    dem = {doc_type: 0 for doc_type in (*_THEO_TUNG_GCN, "gcn")}
    for item in attachments:
        if item.get("detectedType") in dem:
            dem[item["detectedType"]] += 1
    so_gcn = dem["gcn"]
    if so_gcn > 1:
        for doc_type, ten in _THEO_TUNG_GCN.items():
            if 0 < dem[doc_type] < so_gcn:
                warnings.append(
                    f"Hồ sơ có {so_gcn} Giấy chứng nhận (mỗi thửa một bộ) nhưng mới có {dem[doc_type]} {ten} — "
                    "cán bộ đề nghị người dân bổ sung tờ còn thiếu, chưa bổ sung được thì sửa ô \"Số bản\" "
                    "của dòng cho đúng số tệp đã đính."
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

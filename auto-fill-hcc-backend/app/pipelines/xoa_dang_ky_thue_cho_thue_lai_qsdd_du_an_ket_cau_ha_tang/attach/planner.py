"""Đính kèm bước "Thành phần hồ sơ" cho "Xóa đăng ký thuê, cho thuê lại QSDĐ trong dự án xây dựng kinh doanh kết
cấu hạ tầng" — cổng DVC Đà Nẵng (Angular mat-table, engine FE `attp-row`).

Bảng 4 dòng (thứ tự trên cổng, nhãn ghi số mục của Nghị định nên dòng 3 mang "(4)", dòng 4 mang "(3)"):
  [1] (1) Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18      Bản chính
  [2] (2) Giấy chứng nhận đã cấp                                                       Bản chính
  [3] (4) Văn bản về việc đại diện … thông qua người đại diện                          Bản sao
  [4] (3) Văn bản về việc xóa cho thuê, xóa cho thuê lại quyền sử dụng đất             Bản sao

QUY TẮC (theo ảnh ánh xạ đính kèm): KHÔNG tách trang. Mỗi file đi NGUYÊN vào đúng một dòng:
  - File có Đơn Mẫu 18 → dòng 1, kể cả khi file gộp luôn hợp đồng chấm dứt thuê / văn bản thỏa thuận (dòng 4
    coi như đã đính chung, không tải lại).
  - File không có Đơn → theo loại chính: GCN → 2, văn bản đại diện → 3, văn bản xóa thuê → 4.
  - CCCD / giấy tờ khác không có dòng riêng → đính chung dòng 1.
Ô upload mỗi dòng chỉ nhận MỘT tệp → nhiều file cùng dòng được ghép NGUYÊN VẸN thành một PDF qua
`sourceSegments` (pageIndexes=None, FE applyMergeGroups), file có Đơn đứng đầu.

Phân loại LLM-primary theo từng file (loại chính + mọi loại có trong file); rule OCR chỉ vá khi LLM lỗi.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import normalize_document_name
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.xoa_dang_ky_thue_cho_thue_lai_qsdd_du_an_ket_cau_ha_tang.attach import prompt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON = "don_bien_dong"
_GCN = "gcn_da_cap"
_DAI_DIEN = "van_ban_dai_dien"
_XOA_THUE = "van_ban_xoa_thue"
_CCCD = "cccd"
_OTHER = "other"
_ALLOWED = {_DON, _GCN, _DAI_DIEN, _XOA_THUE, _CCCD, _OTHER}

_ROW_DON = 1
_ROW_GCN = 2
_ROW_DAI_DIEN = 3
_ROW_XOA_THUE = 4

# componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng (FE khớp substring fold); componentIndex = STT dòng (1-based).
_ROWS: dict[int, dict[str, Any]] = {
    _ROW_DON: {"componentName": "Đơn đăng ký biến động đất đai", "componentIndex": 1, "loaiBan": "Bản chính",
               "documentName": "Đơn đăng ký biến động đất đai"},
    _ROW_GCN: {"componentName": "Giấy chứng nhận đã cấp", "componentIndex": 2, "loaiBan": "Bản chính",
               "documentName": "Giấy chứng nhận đã cấp"},
    _ROW_DAI_DIEN: {"componentName": "Văn bản về việc đại diện", "componentIndex": 3, "loaiBan": "Bản sao",
                    "documentName": "Văn bản về việc đại diện"},
    _ROW_XOA_THUE: {"componentName": "Văn bản về việc xóa cho thuê", "componentIndex": 4, "loaiBan": "Bản sao",
                    "documentName": "Văn bản về việc xóa cho thuê quyền sử dụng đất"},
}
_ROW_BY_TYPE = {_DON: _ROW_DON, _GCN: _ROW_GCN, _DAI_DIEN: _ROW_DAI_DIEN, _XOA_THUE: _ROW_XOA_THUE}
_TYPE_LABELS = {
    _GCN: "Giấy chứng nhận đã cấp",
    _XOA_THUE: "Văn bản về việc xóa cho thuê (hợp đồng chấm dứt hợp đồng thuê)",
}


def _normalize_type(value: Any) -> str:
    text = _fold(str(value or "")).replace("-", "_").replace(" ", "_")
    if text in _ALLOWED:
        return text
    if "xoa" in text or "cham_dut" in text or "thanh_ly" in text or "thoa_thuan" in text:
        return _XOA_THUE
    if "uy_quyen" in text or "dai_dien" in text:
        return _DAI_DIEN
    if "don" in text or "bien_dong" in text or "mau_18" in text:
        return _DON
    if "gcn" in text or "chung_nhan" in text or "so_do" in text:
        return _GCN
    if "cccd" in text or "can_cuoc" in text or "cmnd" in text or "ho_chieu" in text:
        return _CCCD
    return _OTHER


def _rule_types(text: str) -> tuple[str, set[str]]:
    """(loại chính, các loại có trong file) theo OCR — dự phòng khi LLM lỗi. Văn bản xóa thuê trước ủy quyền
    và GCN: hợp đồng chấm dứt thuê hay NHẮC 'theo Giấy ủy quyền số …' và số Giấy chứng nhận của thửa đất."""
    h = _fold(text)
    if not h.strip():
        return _OTHER, set()
    found: set[str] = set()
    if "don dang ky bien dong" in h:
        found.add(_DON)
    if any(m in h for m in ("cham dut hop dong thue", "xoa dang ky cho thue", "xoa cho thue", "thanh ly hop dong thue")):
        found.add(_XOA_THUE)
    if not found:
        if any(m in h for m in ("hop dong uy quyen", "giay uy quyen", "van ban uy quyen")):
            found.add(_DAI_DIEN)
        elif "nhung thay doi sau khi cap" in h or "so vao so cap giay chung nhan" in h:
            found.add(_GCN)
        elif "can cuoc" in h or "chung minh nhan dan" in h:
            found.add(_CCCD)
    for main in (_DON, _XOA_THUE, _DAI_DIEN, _GCN, _CCCD):
        if main in found:
            return main, found
    return _OTHER, found


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=600, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    out: dict[int, dict] = {}
    for item in parsed.get("documents", []) or []:
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        main = _normalize_type(item.get("docType") or item.get("type"))
        contains = {_normalize_type(t) for t in (item.get("containsTypes") or [])} | {main}
        out[idx] = {"docType": main, "containsTypes": contains - {_OTHER} or {main}}
    return out


def build_plan_items(
    files: list[dict],
    texts: dict[int, str],
    llm_types: dict[int, dict] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    """Gom file nguyên vẹn vào dòng. Trả (attachments, messages, classified)."""
    llm_types = llm_types or {}
    messages: list[str] = []
    classified: list[dict] = []
    by_row: dict[int, list[int]] = {}
    contains_by_file: dict[int, set[str]] = {}

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        llm = llm_types.get(idx)
        rule_main, rule_found = _rule_types(texts.get(idx, ""))
        if llm and llm["docType"] != _OTHER:
            main, contains, source = llm["docType"], set(llm["containsTypes"]), "llm"
            # Đơn là thứ quyết định dòng 1 — OCR thấy rõ tiêu đề Đơn thì tin OCR dù LLM bỏ sót.
            if _DON in rule_found:
                contains.add(_DON)
        elif rule_found:
            main, contains, source = rule_main, rule_found, "rule"
        else:
            main, contains, source = _OTHER, set(), "unknown"
        contains_by_file[idx] = contains | {main}

        row = _ROW_DON if _DON in contains else _ROW_BY_TYPE.get(main, _ROW_DON)
        by_row.setdefault(row, []).append(idx)
        classified.append({"fileIndex": idx, "fileName": file_name, "docType": main,
                           "containsTypes": sorted(contains_by_file[idx]), "source": source,
                           "componentIndex": _ROWS[row]["componentIndex"]})
        if row == _ROW_DON and _DON not in contains:
            messages.append(f"Tệp '{file_name}' không có dòng riêng trên cổng — đã đính chung ở dòng 1 (Đơn).")

    attachments: list[dict] = []
    for row in sorted(by_row):
        indexes = by_row[row]
        if row == _ROW_DON:  # file có Đơn đứng đầu PDF ghép.
            indexes = sorted(indexes, key=lambda i: (_DON not in contains_by_file[i], i))
        spec = _ROWS[row]
        first = indexes[0]
        doc_name = spec["documentName"]
        if row == _ROW_DON and any(_XOA_THUE in contains_by_file[i] for i in indexes):
            doc_name = "Đơn đăng ký biến động và văn bản chấm dứt thuê"
        item = {
            "fileIndex": first,
            "fileName": str(files[first].get("name") or f"file-{first + 1}"),
            "documentName": normalize_document_name(doc_name, spec["documentName"]),
            "componentName": spec["componentName"],
            "componentIndex": spec["componentIndex"],
            "loaiBan": spec["loaiBan"],
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": next(c["docType"] for c in classified if c["fileIndex"] == first),
        }
        if len(indexes) > 1:  # ô chỉ nhận một tệp → ghép NGUYÊN các file thành một PDF, không cắt trang.
            item["sourceSegments"] = [{"fileIndex": i, "pageIndexes": None} for i in indexes]
        attachments.append(item)

    if not files:
        return attachments, messages, classified

    all_types = set().union(*contains_by_file.values()) if contains_by_file else set()
    if _DON not in all_types:
        messages.append(
            "Không nhận ra Đơn đăng ký biến động đất đai (Mẫu số 18) trong hồ sơ — dòng 1 bắt buộc, cán bộ kiểm "
            "tra lại đã có Đơn chưa."
        )
    for row, doc_type in ((_ROW_GCN, _GCN), (_ROW_XOA_THUE, _XOA_THUE)):
        if row in by_row:
            continue
        label = _TYPE_LABELS[doc_type]
        holder = next((i for i in sorted(contains_by_file) if doc_type in contains_by_file[i]), None)
        if holder is not None:
            name = files[holder].get("name") or f"file-{holder + 1}"
            messages.append(
                f"{label} nằm chung trong tệp '{name}' đã đính ở dòng 1 — dòng {row} không đính lại. Nếu cổng "
                f"bắt buộc dòng {row} có tệp, chọn lại đúng tệp đó (không cắt trang)."
            )
        elif doc_type == _GCN:
            messages.append(
                "Hồ sơ chưa có bản scan Giấy chứng nhận đã cấp (dòng 2, bắt buộc, bản chính). Bổ sung bản scan "
                "hoặc dùng nút 'Lấy giấy tờ từ kho' trước khi nộp."
            )
        else:
            messages.append(
                "Chưa thấy văn bản về việc xóa cho thuê (hợp đồng chấm dứt hợp đồng thuê / văn bản thỏa thuận) — "
                "dòng 4 bắt buộc."
            )
    return attachments, messages, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options or {}
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_pairs = [(i, f) for i, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]

    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file([f for _, f in ocr_pairs]) if ocr_pairs else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    ocr_by_index = {ri: res for (ri, _), res in zip(ocr_pairs, ocr_results)}
    for ri, res in ocr_by_index.items():
        if res.get("error"):
            errors.append(f"OCR fileIndex={ri} {raw_files[ri].get('name')}: {res['error']}")
    texts = {ri: str(res.get("text") or "") for ri, res in ocr_by_index.items()}
    llm_docs = [{"index": i, "text": t} for i, t in sorted(texts.items()) if t.strip()]

    t1 = time.monotonic()
    llm_types: dict[int, dict] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, messages, classified = build_plan_items(raw_files, texts, llm_types)
    errors.extend(messages)

    indexed_ocr = [{**res, "name": f"fileIndex={i} · {raw_files[i].get('name')}"} for i, res in ocr_by_index.items()]
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [raw_files[i]["name"] for i, t in texts.items() if t],
            "llmDocuments": [raw_files[d["index"]]["name"] for d in llm_docs],
            "sessionId": (session or {}).get("request_id"),
            "classified": classified,
            "rows": [{"row": k, **v} for k, v in _ROWS.items()],
        },
        "ocr_text": join_ocr_documents(indexed_ocr),
        "llm_output": {"documents": [{"index": k, "docType": v["docType"], "containsTypes": sorted(v["containsTypes"])}
                                     for k, v in llm_types.items()]},
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

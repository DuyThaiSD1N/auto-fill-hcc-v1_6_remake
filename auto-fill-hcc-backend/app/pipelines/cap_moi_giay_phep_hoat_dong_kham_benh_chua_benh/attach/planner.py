"""Đính kèm bước "Thành phần hồ sơ" cho thủ tục "Cấp mới giấy phép hoạt động cơ sở khám bệnh, chữa bệnh"
(cổng Bộ Y tế — Angular mat-table, engine FE `attp-row`).

Bảng 11 dòng (theo ảnh ánh xạ):
  1  "Đơn theo Mẫu 02 Phụ lục II …"                             ← Đơn đề nghị (Bản chính)
  2  "Bản sao hợp lệ quyết định thành lập … giấy chứng nhận đăng ký doanh nghiệp …" ← GCN ĐKHKD/ĐKDN (Bản sao)
  3  "… Mẫu 11 … của người chịu trách nhiệm chuyên môn kỹ thuật …" ← CCHN/GPHN + GXN quá trình hành nghề
  4  "… Mẫu 11 … của người phụ trách bộ phận chuyên môn …"       ← cùng tệp dòng 3 (đính kèm lại)
  5  "Bản kê khai cơ sở vật chất … Mẫu 08 … và các giấy tờ chứng minh …" ← Bản kê khai + văn bằng, chứng
     chỉ đào tạo/CME, quyết định, danh hiệu, hợp đồng… (Bản chính)
  6  "Danh sách … Mẫu 01 …"                                      ← DS đăng ký hành nghề (radio Bản chính)
  7  "Văn bản … bệnh viện … Mẫu 03 …"                            ← chỉ bệnh viện
  8  "Danh mục chuyên môn kỹ thuật …"                            ← DM kỹ thuật (radio Bản chính)
  9  "Trường hợp đề nghị cấp lần đầu … nhân đạo …"               ← tài liệu nguồn tài chính nhân đạo
  10 "Đơn theo Mẫu 02 Phụ lục II …" (TRÙNG tên dòng 1, nằm trong nhóm nhân đạo) ← Đơn, CHỈ khi hồ sơ có
     tài liệu nhân đạo
  11 "Tài liệu chứng minh nguồn tài chính … nhân đạo"            ← tài liệu nguồn tài chính nhân đạo

Engine attp-row GOM item theo componentName rồi tìm dòng bằng (componentName, componentIndex). Dòng 1/10
trùng chữ → mỗi dòng một componentName KHÁC NHAU (đều là đoạn con của tên dòng) + componentIndex.

Phân loại THUẦN LLM, mỗi tệp một lượt gọi (xem prompt). Một tệp scan GỘP nhiều giấy (vd bản kê khai +
danh mục kỹ thuật + giấy chứng nhận CME) được gắn nhiều loại → đính vào mọi dòng tương ứng, mỗi dòng 1 lần.
⚑ KHÔNG BỎ SÓT TỆP: tệp không xếp được (other) hoặc lượt gọi lỗi → đính vào dòng 5 (giấy tờ chứng minh),
giữ tên tệp gốc. CCCD không có dòng riêng → bỏ qua.
"""

import asyncio
import re
import time
from pathlib import PurePath
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.cap_moi_giay_phep_hoat_dong_kham_benh_chua_benh.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_BAN_CHINH = "Bản chính"
_BAN_SAO = "Bản sao"

_DON = "don_de_nghi"
_DANGKY = "giay_dang_ky"
_GPHN = "gphn"
_XNHN = "xac_nhan_hanh_nghe"
_KEKHAI = "ban_ke_khai"
_VANBANG = "van_bang"
_CHUNGCHI = "chung_chi_dao_tao"
_CHUNGMINH = "giay_to_chung_minh"
_DSHN = "danh_sach_hanh_nghe"
_DIEULE = "dieu_le_benh_vien"
_DMKT = "danh_muc_ky_thuat"
_NHANDAO = "tai_chinh_nhan_dao"
_CCCD = "cccd"
_OTHER = "other"

_DOC_NAMES = {
    _DON: "Đơn đề nghị cấp mới giấy phép hoạt động (Mẫu 02 PL II NĐ 96/2023)",
    _DANGKY: "Bản sao giấy chứng nhận đăng ký kinh doanh - quyết định thành lập cơ sở",
    _GPHN: "Bản sao chứng chỉ hành nghề - giấy phép hành nghề",
    _XNHN: "Giấy xác nhận quá trình hành nghề (Mẫu 11 PL I)",
    _KEKHAI: "Bản kê khai cơ sở vật chất, thiết bị y tế, nhân sự (Mẫu 08 PL II)",
    _VANBANG: "Bản sao văn bằng chuyên môn",
    _CHUNGCHI: "Bản sao chứng chỉ - giấy chứng nhận đào tạo",
    _CHUNGMINH: "Giấy tờ chứng minh kê khai",
    _DSHN: "Danh sách đăng ký hành nghề (Mẫu 01 PL II)",
    _DIEULE: "Văn bản quy định chức năng nhiệm vụ - điều lệ bệnh viện (Mẫu 03 PL II)",
    _DMKT: "Danh mục chuyên môn kỹ thuật đề xuất",
    _NHANDAO: "Tài liệu chứng minh nguồn tài chính khám chữa bệnh nhân đạo",
}

# Theo THỨ TỰ dòng trên cổng. componentName = đoạn con của tên dòng, KHÁC NHAU giữa mọi dòng (engine gom
# theo nó); docTypes theo thứ tự tệp trong dòng. requiresAny: dòng chỉ nhận tệp khi hồ sơ có loại đó.
_ROWS: list[dict[str, Any]] = [
    {"componentIndex": 1, "componentName": "Đơn theo Mẫu 02 Phụ lục II ban hành kèm theo Nghị định",
     "loaiBan": _BAN_CHINH, "docTypes": [_DON]},
    {"componentIndex": 2, "componentName": "Bản sao hợp lệ quyết định thành lập hoặc văn bản có tên của cơ sở",
     "loaiBan": _BAN_SAO, "docTypes": [_DANGKY]},
    {"componentIndex": 3, "componentName": "của người chịu trách nhiệm chuyên môn kỹ thuật của cơ sở",
     "loaiBan": _BAN_SAO, "docTypes": [_GPHN, _XNHN]},
    {"componentIndex": 4, "componentName": "của người phụ trách bộ phận chuyên môn của cơ sở",
     "loaiBan": _BAN_SAO, "docTypes": [_GPHN, _XNHN]},
    {"componentIndex": 5, "componentName": "Bản kê khai cơ sở vật chất, danh mục thiết bị y tế",
     "loaiBan": _BAN_CHINH, "docTypes": [_KEKHAI, _VANBANG, _CHUNGCHI, _CHUNGMINH, _OTHER]},
    {"componentIndex": 6, "componentName": "Danh sách ghi rõ họ tên, số giấy phép hành nghề của từng người",
     "loaiBan": _BAN_CHINH, "docTypes": [_DSHN]},
    {"componentIndex": 7, "componentName": "Văn bản do cấp có thẩm quyền phê duyệt quy định về chức năng",
     "loaiBan": _BAN_CHINH, "docTypes": [_DIEULE]},
    {"componentIndex": 8, "componentName": "Danh mục chuyên môn kỹ thuật của cơ sở khám bệnh, chữa bệnh",
     "loaiBan": _BAN_CHINH, "docTypes": [_DMKT]},
    {"componentIndex": 9, "componentName": "Trường hợp đề nghị cấp lần đầu giấy phép hoạt động",
     "loaiBan": _BAN_CHINH, "docTypes": [_NHANDAO]},
    {"componentIndex": 10, "componentName": "Đơn theo Mẫu 02 Phụ lục II",
     "loaiBan": _BAN_CHINH, "docTypes": [_DON], "requiresAny": [_NHANDAO]},
    {"componentIndex": 11, "componentName": "Tài liệu chứng minh nguồn tài chính cho hoạt động",
     "loaiBan": _BAN_CHINH, "docTypes": [_NHANDAO]},
]
_SKIP_DOCS = {_CCCD}
_ALLOWED_DOC_TYPES = set(_DOC_NAMES) | _SKIP_DOCS | {_OTHER}


def _canon(value: Any) -> str:
    return re.sub(r"[\s_\-]+", "_", _fold(str(value or ""))).strip("_")


def _normalize_doc_type(value: Any) -> str:
    """Khớp ĐÚNG nhãn trong allowed_types. Nhãn lạ → other (không đoán theo chuỗi con)."""
    canon = _canon(value)
    return next((doc_type for doc_type in _ALLOWED_DOC_TYPES if _canon(doc_type) == canon), _OTHER)


def _normalize_doc_types(values: Any) -> list[str]:
    """Danh sách loại của MỘT tệp: loại đầu là loại chính. Bỏ nhãn lạ; còn loại thật thì bỏ other/cccd."""
    if not isinstance(values, (list, tuple)):
        values = [values]
    out: list[str] = []
    for value in values:
        doc_type = _normalize_doc_type(value)
        if doc_type not in out:
            out.append(doc_type)
    real = [t for t in out if t not in (_OTHER, _CCCD)]
    if real:
        return real
    return [_CCCD] if _CCCD in out else [_OTHER]


async def _classify_one(index: int, file_name: str, text: str) -> tuple[int, list[str]]:
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(file_name, text)},
    ]
    raw = await client.chat(messages, max_tokens=200, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    first = next(iter(parsed.get("documents", []) or []), None) or parsed
    values = first.get("docTypes") or first.get("docType") or first.get("type")
    return index, _normalize_doc_types(values)


async def _classify_with_llm(
    documents: list[dict[str, Any]],
    errors: list[str] | None = None,
) -> dict[int, list[str]]:
    """Một lượt gọi cho MỖI tệp — lỗi của tệp này không kéo theo tệp khác."""
    if not documents:
        return {}
    outcomes = await asyncio.gather(
        *(_classify_one(d["index"], d["name"], d["text"]) for d in documents),
        return_exceptions=True,
    )
    result: dict[int, list[str]] = {}
    for document, outcome in zip(documents, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            if errors is not None:
                errors.append(f"attachment_agent file {document['name']}: {outcome}")
            continue
        index, doc_types = outcome
        result[index] = doc_types
    return result


def _document_name(file_name: str, doc_type: str, same_type_count: int) -> str:
    # Tệp lạ giữ TÊN GỐC để cán bộ nhận ra; nhiều tệp cùng loại (vd 2 chứng chỉ đào tạo) thêm tên gốc để
    # hai tệp trong cùng dòng không mang cùng một tên.
    if doc_type == _OTHER:
        return file_name
    base = _DOC_NAMES[doc_type]
    return f"{base} ({PurePath(file_name).stem})" if same_type_count > 1 else base


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, list[str] | str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    warnings: list[str] = []
    classified: list[dict] = []
    by_type: dict[str, list[int]] = {}
    names: dict[int, str] = {}

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        names[idx] = file_name
        doc_types = _normalize_doc_types(llm_types[idx]) if idx in llm_types else [_OTHER]
        entry = {
            "fileName": file_name,
            "docType": doc_types[0],
            "docTypes": doc_types,
            "source": "llm" if idx in llm_types else "fallback",
        }
        if doc_types == [_CCCD]:
            entry["skipped"] = True
        else:
            for doc_type in doc_types:
                by_type.setdefault(doc_type, []).append(idx)
            entry["rows"] = [r["componentIndex"] for r in _ROWS if set(doc_types) & set(r["docTypes"])]
        if doc_types == [_OTHER]:
            entry["fallbackRow"] = _CHUNGMINH
        classified.append(entry)

    items: list[dict] = []
    for row in _ROWS:
        if row.get("requiresAny") and not any(by_type.get(t) for t in row["requiresAny"]):
            continue
        placed: set[int] = set()
        for doc_type in row["docTypes"]:
            indices = by_type.get(doc_type, [])
            for idx in indices:
                # Tệp gộp nhiều loại cùng rơi vào một dòng (vd văn bằng + chứng chỉ ở dòng 5) → đính 1 lần.
                if idx in placed:
                    continue
                placed.add(idx)
                items.append({
                    "fileIndex": idx,
                    "fileName": names[idx],
                    "documentName": _document_name(names[idx], doc_type, len(indices)),
                    "componentName": row["componentName"],
                    "componentIndex": row["componentIndex"],
                    "loaiBan": row["loaiBan"],
                    "target": "attp-row",
                    "needsAddComponent": False,
                    "detectedType": doc_type,
                })

    fallback = [names[idx] for idx in by_type.get(_OTHER, [])]
    if fallback:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã đính kèm chung vào dòng Bản kê khai Mẫu 08 (giấy tờ chứng minh) để "
            f"không bỏ sót — cán bộ kiểm tra lại: {', '.join(fallback)}."
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
    llm_docs = [
        {"index": idx, "name": str(file.get("name") or ""),
         "text": str(ocr_by_name.get(file.get("name"), {}).get("text") or "")}
        for idx, file in enumerate(raw_files)
        if file.get("type") in _OCR_TYPES
    ]

    t1 = time.monotonic()
    llm_types: dict[int, list[str]] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs, errors)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, llm_types)
    errors.extend(warnings)
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [doc["name"] for doc in llm_docs],
            "classified": classified,
            "skippedOcr": skipped_ocr,
            "rows": [dict(row) for row in _ROWS],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

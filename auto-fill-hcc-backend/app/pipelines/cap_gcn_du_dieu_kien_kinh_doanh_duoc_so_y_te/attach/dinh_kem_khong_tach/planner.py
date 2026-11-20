"""Đính kèm "Cấp GCN đủ điều kiện kinh doanh dược (Sở Y tế)" (1.014076) — chế độ KHÔNG tách giấy tờ.

Bảng "Thành phần hồ sơ" trên cổng Bộ Y tế (mat-table checkbox + "Loại bản" + file, engine FE ``attp-row``) theo ảnh ánh
xạ 18/11/2026, thứ tự DOM, đều "1 Bản chính":
  1. Đơn đề nghị cấp Giấy chứng nhận đủ điều kiện kinh doanh dược (Mẫu số 10)             ← don_de_nghi
  2. Tài liệu kỹ thuật quy định tại điểm b khoản 1 Điều 38 của Luật Dược                  ← tai_lieu_ky_thuat
     + Danh mục hồ sơ (không có dòng riêng — đính CHUNG một tệp với tài liệu kỹ thuật)   ← danh_muc_ho_so
  3. Giấy chứng nhận đăng ký doanh nghiệp hoặc tài liệu pháp lý chứng minh thành lập cơ sở ← giay_to_phap_ly
  4. Tài liệu thuyết minh … thuốc phải kiểm soát đặc biệt (Mẫu số 11; chỉ khi có KSĐB)    ← thuyet_minh_an_ninh
  5. Chứng chỉ hành nghề dược                                                            ← cchn_duoc
CCCD và giấy chưa rõ loại không có dòng riêng → đính chung dòng Đơn, giữ tên tệp gốc + một cảnh báo (không bỏ tệp).

Mỗi dòng = MỘT tệp: nhiều tệp cùng dòng gộp một PDF (``sourceFileIndexes``, theo thứ tự tải lên). Tệp gộp nhiều giấy
thuộc dòng của giấy CHÍNH (giấy đứng đầu tệp); dòng không có tệp riêng mà nằm trong tệp gộp thì đính nguyên tệp đó vào
dòng ấy (dòng bắt buộc của cổng không bị trống) + cảnh báo.

Phân loại: LLM đọc mọi tệp (MỘT lượt); tiêu đề đầu trang (rule) chỉ dùng cho tệp LLM lỗi / không trả, rồi mới căn
cước / other.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold
from app.pipelines._shared.compact_agent.runner import _extract_docx_text, _is_docx
from app.pipelines._shared.identity_merge import _looks_like_cccd
from app.pipelines.khai_sinh_dvc_moi.attach.dinh_kem_tach.planner import _OCR_TYPES, _pages
from app.pipelines.xac_nhan_thong_tin_ho_tich.attach.planner import _coerce_int, _unique_document_name
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

DON = "don_de_nghi"
DANH_MUC = "danh_muc_ho_so"
KY_THUAT = "tai_lieu_ky_thuat"
PHAP_LY = "giay_to_phap_ly"
THUYET_MINH = "thuyet_minh_an_ninh"
CCHN = "cchn_duoc"
CCCD = "cccd"
OTHER = "other"
ALLOWED_TYPES = {DON, DANH_MUC, KY_THUAT, PHAP_LY, THUYET_MINH, CCHN, CCCD, OTHER}

LOAI_BAN = "Bản chính"

# (STT dòng trên cổng, loại giấy vào dòng, đoạn chữ RIÊNG của dòng để extension khớp, tên tài liệu đính vào dòng).
# Tên tài liệu theo ảnh ánh xạ; dòng 2 có Danh mục hồ sơ thì mang tên "Danh mục hồ sơ_ tài liệu" (row_label).
ROWS: tuple[tuple[int, tuple[str, ...], str, str], ...] = (
    (1, (DON,), "Đơn đề nghị cấp Giấy chứng nhận đủ điều kiện kinh doanh dược", "Đơn đề nghị"),
    (2, (DANH_MUC, KY_THUAT), "Tài liệu kỹ thuật quy định tại điểm b khoản 1 Điều 38", "Tài liệu kỹ thuật"),
    (3, (PHAP_LY,), "Giấy chứng nhận đăng ký doanh nghiệp hoặc tài liệu pháp lý chứng minh việc thành lập cơ sở",
     "Đăng ký KD"),
    (4, (THUYET_MINH,), "Tài liệu thuyết minh cơ sở đáp ứng các biện pháp bảo đảm an ninh", "Tài liệu thuyết minh"),
    (5, (CCHN,), "Chứng chỉ hành nghề dược", "Chứng chỉ dược"),
)
ROW_OF_TYPE = {doc_type: row for row in ROWS for doc_type in row[1]}
# Dòng giấy tờ chưa rõ loại / CCCD đính chung.
EXTRA_ROW = ROWS[0]
DANH_MUC_LABEL = "Danh mục hồ sơ_ tài liệu"

# Câu báo thiếu theo chữ trên bảng thành phần hồ sơ. Dòng 4 chỉ bắt buộc khi kinh doanh thuốc phải kiểm soát đặc biệt.
MISSING = {
    1: "Đơn đề nghị cấp Giấy chứng nhận đủ điều kiện kinh doanh dược (Mẫu số 10)",
    2: "Tài liệu kỹ thuật theo điểm b khoản 1 Điều 38 Luật Dược",
    3: "Giấy chứng nhận đăng ký doanh nghiệp hoặc tài liệu pháp lý chứng minh việc thành lập cơ sở",
    5: "Chứng chỉ hành nghề dược",
}
_CONTROLLED = ("gay nghien", "huong than", "tien chat", "kiem soat dac biet")

# Tiêu đề giấy (fold, bỏ dấu câu) tìm ở ĐẦU từng trang. Một trang nhận cụm xuất hiện SỚM NHẤT: trang Danh mục hồ sơ có
# bảng kê tên mọi giấy ngay dưới tiêu đề, trang Đơn có dòng "Số CCHN Dược" — không bị nhận nhầm.
_TITLE_MARKERS: dict[str, tuple[str, ...]] = {
    DANH_MUC: ("danh muc ho so",),
    DON: ("don de nghi cap giay chung nhan du dieu kien kinh doanh duoc",),
    KY_THUAT: ("tai lieu ky thuat",),
    THUYET_MINH: ("tai lieu thuyet minh",),
    PHAP_LY: (
        "giay chung nhan dang ky doanh nghiep",
        "giay chung nhan dang ky ho kinh doanh",
        "giay chung nhan dang ky kinh doanh",
    ),
    CCHN: ("chung chi hanh nghe duoc",),
}
_HEAD_CHARS = 600


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", fold(text or "")).strip()


def page_type(text: str) -> str | None:
    """Loại giấy theo tiêu đề ở đầu một trang (cụm sớm nhất), không thấy tiêu đề → None."""
    head = _norm(text)[:_HEAD_CHARS]
    best: tuple[int, str] | None = None
    for doc_type, markers in _TITLE_MARKERS.items():
        for marker in markers:
            pos = head.find(marker)
            if pos >= 0 and (best is None or pos < best[0]):
                best = (pos, doc_type)
    if best:
        return best[1]
    return CCCD if _looks_like_cccd(text or "") else None


def rule_types(text: str) -> list[str]:
    """Các loại giấy có tiêu đề ở đầu trang trong tệp (theo thứ tự trang), không trùng."""
    found: list[str] = []
    for page in _pages(str(text or "")):
        doc_type = page_type(page)
        if doc_type and doc_type not in found:
            found.append(doc_type)
    return found


def canonical_type(value: Any) -> str:
    raw = re.sub(r"[\s-]+", "_", fold(str(value or "")).strip())
    if raw in ALLOWED_TYPES:
        return raw
    aliases = (
        ("thuyet_minh", THUYET_MINH), ("an_ninh", THUYET_MINH), ("danh_muc", DANH_MUC), ("ky_thuat", KY_THUAT),
        ("gdp", KY_THUAT), ("gpp", KY_THUAT), ("cchn", CCHN), ("chung_chi", CCHN), ("phap_ly", PHAP_LY),
        ("doanh_nghiep", PHAP_LY), ("kinh_doanh", PHAP_LY), ("don", DON), ("cccd", CCCD), ("can_cuoc", CCCD),
        ("cmnd", CCCD), ("ho_chieu", CCCD),
    )
    return next((doc_type for key, doc_type in aliases if key in raw), OTHER)


def row_label(row: tuple, types: set[str]) -> str:
    return DANH_MUC_LABEL if row[0] == 2 and DANH_MUC in types else row[3]


def row_item(row: tuple, label: str, doc_type: str, file_index: int, file_name: str, used_names: set[str]) -> dict:
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": _unique_document_name(label, used_names, label),
        "componentName": row[2],
        "componentIndex": row[0],
        "loaiBan": LOAI_BAN,
        "target": "attp-row",
        "needsAddComponent": False,
        "detectedType": doc_type,
    }


def extra_item(doc_type: str, file_index: int, file_name: str, base_name: str, used_names: set[str]) -> dict:
    """CCCD / giấy chưa rõ loại → dòng Đơn, giữ tên giấy (LLM) hoặc tên tệp gốc."""
    return row_item(EXTRA_ROW, base_name or file_name, doc_type, file_index, file_name, used_names)


def missing_warnings(found_rows: set[int], all_text: str) -> list[str]:
    warnings = [f"Hồ sơ đã gửi chưa có {MISSING[row]} (dòng {row}) — cần bổ sung."
                for row in sorted(MISSING) if row not in found_rows]
    if 4 not in found_rows and any(k in _norm(all_text) for k in _CONTROLLED):
        warnings.append(
            "Phạm vi kinh doanh có thuốc phải kiểm soát đặc biệt (gây nghiện / hướng thần / tiền chất) nhưng hồ sơ chưa có "
            "Tài liệu thuyết minh bảo đảm an ninh (Mẫu số 11, dòng 4) — cần bổ sung."
        )
    return warnings


def extra_warning(names: list[str]) -> list[str]:
    if not names:
        return []
    return [f"Giấy tờ không có dòng riêng hoặc chưa rõ loại đã đính chung dòng \"{EXTRA_ROW[2]}\": "
            + ", ".join(names) + "."]


def validated_classifications(raw_items: list[dict], file_count: int) -> dict[int, dict]:
    result: dict[int, dict] = {}
    for raw in raw_items or []:
        if not isinstance(raw, dict):
            continue
        file_index = _coerce_int(raw.get("fileIndex", raw.get("index")))
        if file_index is None or not 0 <= file_index < file_count or file_index in result:
            continue
        raw_types = raw.get("docTypes", raw.get("docType", raw.get("type")))
        types: list[str] = []
        for value in raw_types if isinstance(raw_types, list) else [raw_types]:
            doc_type = canonical_type(value)
            if doc_type not in types:
                types.append(doc_type)
        result[file_index] = {
            "types": types or [OTHER],
            "documentName": str(raw.get("documentName") or raw.get("title") or "").strip(),
        }
    return result


async def _classify_with_llm(documents: list[dict[str, Any]]) -> list[dict]:
    if not documents:
        return []
    raw = await client.chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(documents)},
        ],
        max_tokens=max(600, min(2000, len(documents) * 160)),
        enable_thinking=settings.agent_reasoning,
    )
    parsed = client.extract_json_block(raw)
    return parsed.get("documents", []) if isinstance(parsed, dict) else []


def build_plan_items(
    raw_files: list[dict],
    ocr_text_by_index: dict[int, str],
    llm_by_index: dict[int, dict] | None = None,
) -> tuple[list[dict], list[dict], list[str]]:
    """Dựng kế hoạch đính kèm nguyên tệp từ loại giấy đã phân (tách khỏi I/O để test)."""
    llm_by_index = llm_by_index or {}

    def file_name(index: int) -> str:
        return str(raw_files[index].get("name") or f"file-{index + 1}")

    covers: dict[int, list[str]] = {}
    source: dict[int, str] = {}
    for index in range(len(raw_files)):
        text = ocr_text_by_index.get(index, "")
        found = rule_types(text)
        if index in llm_by_index:
            covers[index], source[index] = llm_by_index[index]["types"], "llm"
        elif any(t in ROW_OF_TYPE for t in found):
            covers[index], source[index] = found, "rule"
        else:
            covers[index], source[index] = (found or [CCCD if _looks_like_cccd(text) else OTHER]), "default"

    def rows_of(index: int) -> list[int]:
        return list(dict.fromkeys(ROW_OF_TYPE[t][0] for t in covers[index] if t in ROW_OF_TYPE))

    used_names: set[str] = set()
    attachments: list[dict] = []
    rows_by_file: dict[int, list[int]] = {index: [] for index in range(len(raw_files))}
    warnings: list[str] = []
    shared_notes: list[str] = []
    for row in ROWS:
        primary = [i for i in range(len(raw_files)) if rows_of(i)[:1] == [row[0]]]
        # Không có tệp riêng → tệp gộp có chứa giấy của dòng này (đính nguyên tệp) để dòng bắt buộc không trống.
        sources = primary or [i for i in range(len(raw_files)) if row[0] in rows_of(i)]
        if not sources:
            continue
        if not primary:
            shared_notes.append(f"dòng {row[0]}: " + ", ".join(file_name(i) for i in sources))
        types = {t for i in sources for t in covers[i] if t in row[1]}
        doc_type = next(t for t in row[1][::-1] if t in types) if types else row[1][0]
        item = row_item(row, row_label(row, types), doc_type, sources[0], file_name(sources[0]), used_names)
        if len(sources) > 1:
            item["sourceFileIndexes"] = sources
        attachments.append(item)
        for index in sources:
            rows_by_file[index].append(row[0])

    extras: list[str] = []
    for index in range(len(raw_files)):
        if rows_by_file[index]:
            continue
        doc_type = CCCD if CCCD in covers[index] else OTHER
        base = (llm_by_index.get(index) or {}).get("documentName") or ""
        attachments.append(extra_item(doc_type, index, file_name(index), base, used_names))
        rows_by_file[index].append(EXTRA_ROW[0])
        extras.append(file_name(index))

    classified = [
        {
            "fileIndex": index,
            "fileName": file_name(index),
            "covers": covers[index],
            "source": source[index],
            "componentIndexes": rows_by_file[index],
        }
        for index in range(len(raw_files))
    ]
    found_rows = {item["componentIndex"] for item in attachments if item["detectedType"] in ROW_OF_TYPE}
    warnings.extend(missing_warnings(found_rows, " ".join(ocr_text_by_index.values())))
    if shared_notes:
        warnings.append("Tệp chứa nhiều giấy được đính nguyên tệp vào cả dòng không có tệp riêng — "
                        + "; ".join(shared_notes) + ". Bật cài đặt \"Tách giấy tờ\" để mỗi dòng chỉ nhận đúng trang.")
    warnings.extend(extra_warning(extras))
    return attachments, classified, warnings


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_pairs = [(i, f) for i, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file([f for _, f in ocr_pairs]) if ocr_pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    ocr_by_index = {i: result for (i, _), result in zip(ocr_pairs, ocr_results)}
    for i, result in ocr_by_index.items():
        if result.get("error"):
            errors.append(f"OCR fileIndex={i} {raw_files[i].get('name')}: {result['error']}")
    ocr_text_by_index = {i: str((ocr_by_index.get(i) or {}).get("text") or "") for i in range(len(raw_files))}
    for i, f in enumerate(raw_files):
        if _is_docx(f) and not ocr_text_by_index[i]:
            ocr_text_by_index[i] = str(_extract_docx_text(f).get("text") or "")

    # Mọi tệp có chữ đều qua LLM: cụm tiêu đề dễ khớp nhầm chữ trong bảng (cột "Chứng chỉ hành nghề dược đã cấp" của
    # bản kê nhân sự trong tài liệu kỹ thuật) nên rule chỉ dự phòng khi LLM không trả.
    llm_docs = [
        {"fileIndex": i, "ocrText": ocr_text_by_index[i][:12000]}
        for i in range(len(raw_files))
        if ocr_text_by_index[i].strip()
    ]
    started = time.monotonic()
    raw_classifications: list[dict] = []
    if llm_docs:
        try:
            raw_classifications = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001 - rule dự phòng vẫn giữ đủ tệp
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    llm_indexes = {doc["fileIndex"] for doc in llm_docs}
    llm_by_index = {
        i: item for i, item in validated_classifications(raw_classifications, len(raw_files)).items()
        if i in llm_indexes
    }
    attachments, classified, warnings = build_plan_items(raw_files, ocr_text_by_index, llm_by_index)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [raw_files[i].get("name") for i, r in ocr_by_index.items() if r.get("text")],
            "llmDocuments": [raw_files[doc["fileIndex"]]["name"] for doc in llm_docs],
            "sessionId": (session or {}).get("request_id"),
            "attachmentMode": "whole_files",
            "classified": classified,
            "rows": [{"componentIndex": r[0], "docTypes": list(r[1]), "componentName": r[2]} for r in ROWS],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

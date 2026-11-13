"""Đính kèm KHÔNG TÁCH cho "Cấp mới chứng chỉ hành nghề môi giới bất động sản" (1.012906, attp-row 6 dòng) — cài
đặt "Tách giấy tờ" tắt.

OCR từng tệp (cùng `ocr.ocr_per_file` như chế độ tách) → MỘT lượt LLM liệt kê mọi loại giấy trong từng tệp → MỖI TỆP
đính NGUYÊN, đúng MỘT lần (không `sourceSegments`), vào dòng của giấy chính trong tệp:
  Đơn đăng ký dự thi → giấy có dòng riêng (theo thứ tự xuất hiện) → giấy đi chung dòng Đơn (chứng chỉ cũ, giấy tờ tổ
  chức).
Bảng 6 dòng, ánh xạ loại → dòng, loại bản, rule vá loại theo tiêu đề và nhận ảnh rời dùng CHUNG với chế độ tách
(`dinh_kem_tach.planner`) nên hai chế độ đặt giấy cùng dòng. Tệp gộp nhiều giấy có dòng riêng → cảnh báo cán bộ. LLM
lỗi / trả other → rule OCR vá theo tiêu đề đầu tệp; vẫn không rõ (OCR rỗng) → dòng 3 (Đơn), giữ tên gốc.

Khác chế độ tách: thiếu ảnh 4x6 rời thì KHÔNG đính lại tệp Đơn vào dòng 4 (mỗi tệp chỉ một lần) — chỉ cảnh báo.
Ảnh thẻ scan thành PDF (OCR chỉ ra "Scanned with CamScanner") mà LLM trả other → rule nhận ảnh rời, vào dòng 4.

Các hàm OCR / gọi LLM / chọn giấy chính (`ocr_files`, `llm_documents`, `classify_files`, `pick_primary`,
`plan_result`) dùng chung cho chế độ không tách của các thủ tục cùng khuôn planner.
"""

import time
from collections.abc import Callable, Iterable
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.documents import join_ocr_documents, representative_excerpt
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

from ..dinh_kem_tach.planner import (
    _ANH,
    _CC_CU,
    _CCCD,
    _DON,
    _FALLBACK_ROW,
    _OCR_TYPES,
    _ORDER,
    _OTHER,
    _REQUIRED,
    _ROUTE,
    _ROW_ANH,
    _ROW_NUOC_NGOAI,
    _ROWS,
    _TO_CHUC,
    _certified,
    _is_photo,
    _normalize_type,
    _rule_type,
    _unique_name,
)
from .prompt import SYSTEM_PROMPT, build_user_prompt

# Trích đoạn OCR mỗi tệp gửi LLM (đầu từng trang, bỏ dòng lặp).
_LLM_TEXT_MAX_CHARS = 3000

# Giấy chính của tệp gộp: Đơn → giấy có dòng riêng → giấy đi chung dòng Đơn; cùng tầng thì giấy xuất hiện trước.
_TIERS: tuple[frozenset[str], ...] = (
    frozenset({_DON}),
    frozenset(_ROUTE) - {_DON},
    frozenset({_CC_CU, _TO_CHUC}),
)


# ---------------- Dùng chung cho chế độ không tách của các thủ tục cùng khuôn ----------------
async def ocr_files(raw_files: list[dict], errors: list[str]) -> tuple[dict[int, dict], int]:
    """OCR các tệp ảnh/PDF (một lần gọi `ocr.ocr_per_file` như chế độ tách) → ({fileIndex: kết quả}, ms)."""
    pairs = [(i, f) for i, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]
    started = time.monotonic()
    results = await ocr.ocr_per_file([f for _, f in pairs]) if pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    by_index = {i: res for (i, _), res in zip(pairs, results)}
    for i, res in by_index.items():
        if res.get("error"):
            errors.append(f"OCR fileIndex={i} {raw_files[i].get('name')}: {res['error']}")
    return by_index, ocr_ms


def ocr_texts(ocr_by_index: dict[int, dict]) -> dict[int, str]:
    return {i: str(res.get("text") or "") for i, res in ocr_by_index.items()}


def llm_documents(texts: dict[int, str], skip: Iterable[int] = ()) -> list[dict]:
    """Tệp có chữ → trích đoạn đại diện (đầu từng trang) cho lượt LLM duy nhất."""
    skipped = set(skip)
    return [
        {"index": i, "text": representative_excerpt(text, _LLM_TEXT_MAX_CHARS)}
        for i, text in sorted(texts.items())
        if i not in skipped and text.strip()
    ]


def parse_doc_types(parsed: dict, indexes: set[int], normalize: Callable[[str], str]) -> dict[int, list[str]]:
    """{"documents":[{"index","docTypes"}]} → {index: [loại đã chuẩn hóa, không trùng, theo thứ tự xuất hiện]}."""
    out: dict[int, list[str]] = {}
    for item in parsed.get("documents") or []:
        if not isinstance(item, dict):
            continue
        try:
            index = int(item.get("index"))
        except (TypeError, ValueError):
            continue
        if index not in indexes or index in out:
            continue
        raw = item.get("docTypes", item.get("docType", item.get("type")))
        types: list[str] = []
        for value in raw if isinstance(raw, list) else [raw]:
            doc_type = normalize(str(value or ""))
            if doc_type not in types:
                types.append(doc_type)
        out[index] = types
    return out


async def classify_files(system_prompt: str, user_prompt: str, indexes: set[int],
                         normalize: Callable[[str], str]) -> dict[int, list[str]]:
    """MỘT lượt LLM cho cả hồ sơ; exception để bên gọi ghi lỗi và đính tệp về dòng dự phòng."""
    raw = await client.chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max(600, min(2000, 200 + 80 * len(indexes))),
        enable_thinking=settings.agent_reasoning,
    )
    return parse_doc_types(client.extract_json_block(raw), indexes, normalize)


def pick_primary(doc_types: list[str], tiers: tuple[frozenset[str], ...], default: str) -> str:
    """Giấy chính của tệp: tầng ưu tiên đứng trước thắng; cùng tầng thì giấy xuất hiện trước."""
    for tier in tiers:
        for doc_type in doc_types:
            if doc_type in tier:
                return doc_type
    return default


def plan_result(raw_files: list[dict], ocr_by_index: dict[int, dict], llm_docs: list[dict],
                llm_types: dict[int, list[str]], attachments: list[dict], classified: list[dict],
                errors: list[str], session: dict | None, ocr_ms: int, llm_ms: int,
                **extracted: Any) -> dict:
    indexed_ocr = [{**res, "name": f"fileIndex={i} · {raw_files[i].get('name')}"} for i, res in ocr_by_index.items()]
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [raw_files[i]["name"] for i, r in ocr_by_index.items() if r.get("text")],
            "llmDocuments": [raw_files[d["index"]]["name"] for d in llm_docs],
            "sessionId": (session or {}).get("request_id"),
            "classified": classified,
            **extracted,
        },
        "ocr_text": join_ocr_documents(indexed_ocr),
        "llm_output": {"documents": [{"index": i, "docTypes": t} for i, t in sorted(llm_types.items())]},
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }


# ---------------- Riêng thủ tục môi giới BĐS ----------------
def _file_types(file: dict, text: str, llm: list[str] | None) -> tuple[list[str], str]:
    """Loại giấy trong tệp + nguồn. LLM là chính; LLM lỗi / chỉ trả other → rule theo tiêu đề, ảnh rời (như chế độ
    tách)."""
    types = [t for t in llm or [] if t != _OTHER]
    if types:
        return types, "llm"
    doc_type = _rule_type(text)
    if doc_type == _OTHER and _is_photo(file, text):
        doc_type = _ANH
    return ([doc_type], "rule") if doc_type != _OTHER else ([], "unknown")


def build_plan_items(
    raw_files: list[dict],
    texts: dict[int, str],
    llm_types: dict[int, list[str]] | None = None,
) -> tuple[list[dict], list[dict], list[str]]:
    """Mỗi tệp → đúng MỘT item đính nguyên tệp. Thuần tất định, không gọi OCR/LLM."""
    order = {t: i for i, t in enumerate(_ORDER)}
    used_names: set[str] = set()
    own: list[tuple[int, int, dict]] = []
    extra: list[dict] = []
    classified: list[dict] = []
    warnings: list[str] = []
    found_rows: set[int] = set()
    found_types: set[str] = set()
    extra_names: list[str] = []
    don_text = ""
    cccd_texts: list[str] = []

    for index, file in enumerate(raw_files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        text = texts.get(index, "")
        types, source = _file_types(file, text, (llm_types or {}).get(index))
        primary = pick_primary(types, _TIERS, _OTHER)
        row_idx = _ROUTE.get(primary, _FALLBACK_ROW)
        row = _ROWS[row_idx]
        found_types.update(types)
        found_rows.update(_ROUTE[t] for t in types if t in _ROUTE)
        if _DON in types:
            don_text += " " + _fold(text)[:600]
        if _CCCD in types:
            cccd_texts.append(text)
        others = sorted({_ROUTE[t] for t in types if t in _ROUTE} - {row_idx})
        mixed = len(set(types)) > 1
        # Tệp một giấy có dòng riêng mang tên giấy; tệp gộp / không có dòng riêng / không rõ giữ TÊN GỐC.
        base_name = row["documentName"] if primary in _ROUTE and not mixed else file_name
        item = {
            "fileIndex": index,
            "fileName": file_name,
            "documentName": _unique_name(base_name.replace("/", "-"), used_names, row["documentName"]),
            "componentName": row["componentName"],
            "componentIndex": row_idx,
            "loaiBan": row["loaiBan"],
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": primary,
            "includedTypes": types or [primary],
        }
        entry = {"fileIndex": index, "fileName": file_name, "type": primary, "docTypes": types, "source": source,
                 "componentIndex": row_idx}
        if primary in _ROUTE:
            own.append((row_idx, order.get(primary, 99), item))
        else:
            extra.append(item)
            extra_names.append(file_name)
            entry["routedTo"] = _FALLBACK_ROW
        classified.append(entry)
        if others:
            warnings.append(f"'{file_name}' gộp nhiều giấy tờ — đính nguyên tệp một lần vào dòng {row_idx} "
                            f"({row['documentName']}), không tách sang dòng {', '.join(map(str, others))}.")

    attachments = [item for _, _, item in sorted(own, key=lambda p: (p[0], p[1], p[2]["fileIndex"]))] + extra

    # Dòng 5 chỉ dành cho người có chứng chỉ do nước ngoài cấp — không có tệp ở dòng 5 thì bỏ tick.
    if attachments and not any(item["componentIndex"] == _ROW_NUOC_NGOAI for item in attachments):
        attachments[0]["untickRows"] = [_ROWS[_ROW_NUOC_NGOAI]["componentName"]]

    # --- Cảnh báo (cùng nội dung chế độ tách) ---
    for row_idx, label in _REQUIRED:
        if row_idx not in found_rows:
            warnings.append(f"Chưa có {label} (dòng {row_idx}) — cần bổ sung.")
    if "cap lai" in don_text:
        warnings.append("Đơn trong hồ sơ là ĐƠN XIN CẤP LẠI chứng chỉ — dòng 3 yêu cầu Đơn đăng ký dự thi sát hạch "
                        "(Phụ lục XXI NĐ 96/2024/NĐ-CP); đã đính tạm vào dòng 3, kiểm tra lại thủ tục.")
    if _ROW_ANH not in found_rows:
        if _DON in found_types:
            warnings.append(f"Hồ sơ không có ảnh 4x6 chụp rời — chế độ không tách không đính lại tệp Đơn vào dòng "
                            f"{_ROW_ANH}; còn thiếu 02 ảnh 4x6 và 02 phong bì có dán tem ghi rõ họ tên, số điện "
                            "thoại, địa chỉ người nhận.")
        else:
            warnings.append(f"Chưa có 02 ảnh 4x6 và 02 phong bì có dán tem (dòng {_ROW_ANH}) — cần bổ sung.")
    if cccd_texts and not any(_certified(t) for t in cccd_texts):
        warnings.append("Bản CCCD trong hồ sơ chưa thấy dấu chứng thực — dòng 2 yêu cầu bản sao chứng thực (hoặc bản "
                        "sao kèm bản chính để đối chiếu).")
    if _CC_CU in found_types:
        warnings.append("Hồ sơ có chứng chỉ hành nghề môi giới BĐS đã cấp — bảng thành phần không có dòng riêng, đã "
                        "đính chung dòng 3 (Đơn).")
    if extra_names:
        warnings.append(f"Giấy tờ không có dòng riêng hoặc chưa rõ loại đã đính chung dòng "
                        f"\"{_ROWS[_FALLBACK_ROW]['componentName']}\": " + "; ".join(extra_names))
    return attachments, classified, warnings


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, list[str]]:
    if not documents:
        return {}
    return await classify_files(SYSTEM_PROMPT, build_user_prompt(documents), {d["index"] for d in documents},
                                _normalize_type)


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options or {}
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_by_index, ocr_ms = await ocr_files(raw_files, errors)
    texts = ocr_texts(ocr_by_index)
    llm_docs = llm_documents(texts)

    started = time.monotonic()
    llm_types: dict[int, list[str]] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001 — LLM lỗi → rule theo tiêu đề, không rõ thì dòng Đơn, giữ tên gốc
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, classified, warnings = build_plan_items(raw_files, texts, llm_types)
    errors.extend(warnings)
    return plan_result(raw_files, ocr_by_index, llm_docs, llm_types, attachments, classified, errors, session,
                       ocr_ms, llm_ms, rows=[{"componentIndex": k, **row} for k, row in _ROWS.items()])

"""Đính kèm bước 2 "Thành phần hồ sơ" cho thủ tục "Tiếp nhận đối tượng cần bảo vệ khẩn cấp vào cơ sở trợ giúp xã
hội" (cổng Bộ Y tế — Angular table, engine FE `attp-row`).

Bảng có HAI dòng (cùng ô "Chọn/Bỏ chọn tất cả" — không tick):
  1. Tờ khai đề nghị chăm sóc, nuôi dưỡng tại cơ sở trợ giúp xã hội (Mẫu số 04 — NĐ 335/2026/NĐ-CP)
  2. Biên bản tiếp nhận có chữ ký của cá nhân hoặc đại diện cơ quan, đơn vị phát hiện ra đối tượng...
Mỗi dòng: mat-checkbox + rdo_File + ô upload multiple. Theo ánh xạ đính kèm của thủ tục:
  - CCCD và giấy tờ khác (xác nhận khuyết tật, khai sinh...) KHÔNG có dòng (QĐ 3033/QĐ-BYT đã cắt bản sao CCCD)
    → chỉ dùng để điền bước 1, KHÔNG đính.
  - Biên bản scan CHUNG tệp với tờ khai → KHÔNG tách tệp: đính chính tệp đó ở cả hai dòng.
  - Hồ sơ thiếu biên bản → cảnh báo cán bộ scan bổ sung (dòng bắt buộc trên cổng).
Planner OCR tối đa ``attach_classify_max_pages`` trang đầu nên biên bản nằm sau tờ khai 3 trang không đọc thấy —
cảnh báo thiếu biên bản nhắc luôn cách đính lại tệp chung.

Phân loại **LLM-primary**: LLM đọc OCR mọi file; rule keyword chỉ DỰ PHÒNG khi LLM trả other/không hợp lệ.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.tiep_nhan_doi_tuong_can_bao_ve_khan_cap_vao_co_so_tro_giup_xa_hoi.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_LOAI_BAN = "Scan tệp tin"

_TO_KHAI = "to_khai_mau_04"
_BIEN_BAN = "bien_ban_tiep_nhan"
_COMBINED = "to_khai_kem_bien_ban"
_CAN_CUOC = "can_cuoc"
_KHAC = "giay_to_khac"
_OTHER = "other"
_ALLOWED_DOC_TYPES = {_TO_KHAI, _BIEN_BAN, _COMBINED, _CAN_CUOC, _KHAC, _OTHER}
# Không có dòng trên cổng → chỉ dùng để điền bước 1.
_NOT_ATTACHED = {_CAN_CUOC, _KHAC}

# componentName = đoạn text đặc trưng của dòng (FE khớp substring đã fold dấu vào tên dòng lấy từ DOM).
_ROW_TO_KHAI = "Tờ khai đề nghị chăm sóc, nuôi dưỡng tại cơ sở trợ giúp xã hội"
_ROW_BIEN_BAN = "Biên bản tiếp nhận có chữ ký"

# Tên tệp tải lên (engine attp-row đổi tên theo documentName).
_DOC_TO_KHAI = "Tờ khai đề nghị chăm sóc, nuôi dưỡng (Mẫu số 04)"
_DOC_BIEN_BAN = "Biên bản tiếp nhận"

_TK_TITLE = re.compile(r"to khai de nghi cham soc,? nuoi duong|to khai .{0,60}tai co so tro giup xa hoi")
_BB_TITLE = re.compile(r"\bbien ban (?:tiep nhan|ban giao|giao nhan|phat hien)")


def _is_identity_text(h: str) -> bool:
    return any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu", "passport",
                                "citizen identity", "identity card"))


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM). Tờ khai nhắc "tiếp nhận"/"căn cước"/"khuyết tật" nên nhận
    theo TIÊU ĐỀ; biên bản bắt buộc có chữ "biên bản"."""
    h = re.sub(r"\s+", " ", _fold(text))
    if not h:
        return ""
    has_tk = bool(_TK_TITLE.search(h))
    has_bb = bool(_BB_TITLE.search(h))
    if has_tk and has_bb:
        # Biên bản hay nhắc lại tên tờ khai; chỉ coi là tệp chung khi có cả THÂN tờ khai (mục I / mục II).
        tk_body = "nguoi de nghi duoc cham soc" in h or "thong tin nguoi giam ho" in h
        return _COMBINED if tk_body else _BIEN_BAN
    if has_tk:
        return _TO_KHAI
    if has_bb:
        return _BIEN_BAN
    if _is_identity_text(h):
        return _CAN_CUOC
    if any(m in h for m in ("xac nhan khuyet tat", "giam dinh y khoa", "giay khai sinh", "trich luc khai sinh",
                            "thong tin ve cu tru", "thong bao so dinh danh", "ho can ngheo", "ho ngheo")):
        return _KHAC
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "").replace("_", " ")
    if not text or text == "other":
        return _OTHER
    if "kem bien ban" in text or ("to khai" in text and "bien ban" in text):
        return _COMBINED
    if "bien ban" in text:
        return _BIEN_BAN
    if "04" in text or "to khai" in text:
        return _TO_KHAI
    if "can cuoc" in text or "cccd" in text or "cmnd" in text or "ho chieu" in text:
        return _CAN_CUOC
    if "khac" in text or "khuyet tat" in text or "khai sinh" in text or "cu tru" in text:
        return _KHAC
    return _OTHER


async def _classify_with_llm(documents: list[dict[str, Any]], system_prompt: str | None = None) -> dict[int, str]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": system_prompt or prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=500, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    out: dict[int, str] = {}
    for item in parsed.get("documents", []) or []:
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        out[idx] = _normalize_doc_type(str(item.get("docType") or item.get("type") or ""))
    return out


def _build_row_item(file: dict, file_index: int, doc_type: str, component_name: str, document_name: str) -> dict:
    return {
        "fileIndex": file_index,
        "fileName": str(file.get("name") or f"file-{file_index + 1}"),
        "documentName": document_name,
        "componentName": component_name,
        "loaiBan": _LOAI_BAN,
        "target": "attp-row",
        "needsAddComponent": False,
        "detectedType": doc_type,
    }


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, str] | None = None,
    *,
    bien_ban_row: bool = True,
) -> tuple[list[dict], list[str], list[dict]]:
    """``bien_ban_row=False`` (1.116907): bảng chỉ có dòng Tờ khai Mẫu số 04 → biên bản không đính, tệp chung chỉ
    đính dòng tờ khai, không cảnh báo thiếu biên bản."""
    llm_types = llm_types or {}
    by_name = {item.get("name"): item for item in ocr_results}
    warnings: list[str] = []
    classified: list[dict] = []
    typed: list[tuple[int, dict, str]] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        text = str(by_name.get(file_name, {}).get("text") or "")
        llm_type = llm_types.get(idx, "")
        rule_type = _rule_doc_type(text)
        # LLM-primary: ưu tiên phán đoán của LLM; rule keyword chỉ dự phòng khi LLM trả other/không hợp lệ.
        if llm_type in _ALLOWED_DOC_TYPES and llm_type != _OTHER:
            doc_type, source = llm_type, "llm"
            # Cả hai tiêu đề cùng nằm trong OCR thì chắc chắn là tệp chung, kể cả khi LLM chỉ gọi một loại.
            if rule_type == _COMBINED and llm_type in (_TO_KHAI, _BIEN_BAN):
                doc_type, source = _COMBINED, "rule"
        elif rule_type:
            doc_type, source = rule_type, "rule"
        else:
            doc_type, source = _OTHER, "unknown" if not llm_type else "llm"
        typed.append((idx, file, doc_type))
        classified.append({"fileName": file_name, "docType": doc_type, "source": source})

    to_khai = [(idx, file) for idx, file, t in typed if t in (_TO_KHAI, _COMBINED)]
    bien_ban = [(idx, file) for idx, file, t in typed if t in (_BIEN_BAN, _COMBINED)] if bien_ban_row else []

    items: list[dict] = []
    for component, document_name, doc_type, rows in (
        (_ROW_TO_KHAI, _DOC_TO_KHAI, _TO_KHAI, to_khai),
        (_ROW_BIEN_BAN, _DOC_BIEN_BAN, _BIEN_BAN, bien_ban),
    ):
        for position, (idx, file) in enumerate(rows, start=1):
            name = document_name if position == 1 else f"{document_name} {position}"
            items.append(_build_row_item(file, idx, doc_type, component, name))

    for idx, file, doc_type in typed:
        file_name = str(file.get("name") or f"file-{idx + 1}")
        if doc_type == _COMBINED and bien_ban_row:
            warnings.append(
                f"'{file_name}' chứa cả Tờ khai Mẫu số 04 lẫn Biên bản tiếp nhận — không tách tệp, đính chính tệp "
                "đó ở cả hai dòng."
            )
        elif doc_type == _OTHER:
            warnings.append(
                f"Chưa nhận diện '{file_name}' là Tờ khai Mẫu số 04 hay Biên bản tiếp nhận — không đính; nếu là một "
                "trong hai, cán bộ đính tay vào đúng dòng."
                if bien_ban_row else
                f"Chưa nhận diện '{file_name}' là Tờ khai Mẫu số 04 — không đính; nếu là tờ khai, cán bộ đính tay "
                "vào dòng tờ khai."
            )
    if files and not to_khai:
        warnings.append(
            "Không thấy Tờ khai Mẫu số 04 trong các tệp — cán bộ bổ sung tờ khai ở dòng 'Tờ khai đề nghị chăm sóc, "
            "nuôi dưỡng tại cơ sở trợ giúp xã hội'."
        )
    if bien_ban_row and files and not bien_ban:
        warnings.append(
            "Hồ sơ chưa có Biên bản tiếp nhận — dòng này trên cổng là bắt buộc, cán bộ scan bổ sung. Nếu biên bản "
            "scan chung tệp với tờ khai thì đính lại chính tệp đó ở dòng Biên bản tiếp nhận."
        )

    return items, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options or {}
    _ = session
    return await plan_documents(files, bien_ban_row=True, system_prompt=prompt.SYSTEM_PROMPT)


async def plan_documents(files: list[FileItem], *, bien_ban_row: bool, system_prompt: str) -> dict:
    """Thân planner dùng chung với 1.116907 (bảng chỉ dòng Tờ khai Mẫu số 04 → bien_ban_row=False)."""
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
            llm_types = await _classify_with_llm(llm_docs, system_prompt)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types, bien_ban_row=bien_ban_row)
    errors.extend(warnings)
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES]
    not_attached = _NOT_ATTACHED if bien_ban_row else _NOT_ATTACHED | {_BIEN_BAN}

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [raw_files[doc["index"]]["name"] for doc in llm_docs],
            "classified": classified,
            "notAttached": [c["fileName"] for c in classified if c["docType"] in not_attached],
            "skippedOcr": skipped_ocr,
            "rows": [_ROW_TO_KHAI, _ROW_BIEN_BAN] if bien_ban_row else [_ROW_TO_KHAI],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

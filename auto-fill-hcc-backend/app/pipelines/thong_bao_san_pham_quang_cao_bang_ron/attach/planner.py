"""Đính kèm [Bộ VHTTDL] Thủ tục tiếp nhận hồ sơ thông báo sản phẩm quảng cáo trên bảng quảng cáo,
băng-rôn (1.004650).

Form và bảng thành phần hồ sơ CHUNG trang `/nop-ho-so`. Bảng `<table class="style_table">` có 7 dòng, mỗi
dòng một `<app-upload-flie-multi>` → engine FE `fixed-slot` (slotIndex = thứ tự ô upload trên trang):

  0 : (1) Giấy tờ hợp chuẩn, hợp quy / đủ điều kiện quảng cáo (Điều 20 Luật quảng cáo)
  1 : (2) Văn bản về việc tổ chức sự kiện, chính sách xã hội
  2 : (3) Ma-két sản phẩm quảng cáo
  3 : (4) Văn bản chứng minh quyền sở hữu / quyền sử dụng bảng quảng cáo, địa điểm treo băng-rôn
  4 : (5) Bản phối cảnh vị trí đặt bảng quảng cáo
  5 : (6) Giấy phép xây dựng công trình quảng cáo
  6 : (7) Thông báo sản phẩm quảng cáo (Mẫu số 01)

Giấy chứng nhận đăng ký doanh nghiệp và thông báo khuyến mại chứng minh điều kiện quảng cáo của doanh
nghiệp/chương trình → dòng (1), đính CHUNG với giấy tờ hợp quy (engine gom nhiều tệp vào một ô). Tệp
không nhận ra loại → dòng (7) kèm cảnh báo — trang không có ô "Giấy tờ khác", không tệp nào bị bỏ.

Phân loại THUẦN LLM từng tệp; định tuyến loại → dòng là tất định. Riêng ảnh phối cảnh hay bị đọc nhầm thành
ma-két hoặc không rõ loại (OCR ảnh chụp dãy phố ra chữ biển hiệu rời rạc): chưa có phoi_canh mà có ≥2 tệp maket,
hoặc có maket + tệp other, thì một tệp trong số đó gần như chắc là phối cảnh → hỏi LLM lượt 2 chọn tệp nào, chuyển
tệp đó sang dòng (5).
"""

import asyncio
import re
import time
import unicodedata
from typing import Any

from app.config import settings
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import PICK_PHOI_CANH_PROMPT, SYSTEM_PROMPT, build_pick_prompt, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_SLOT_NAMES = {
    0: "Bản sao giấy tờ chứng minh sự hợp chuẩn, hợp quy của sản phẩm, hàng hoá, dịch vụ",
    1: "Bản sao văn bản về việc tổ chức sự kiện của đơn vị tổ chức",
    2: "Ma-két sản phẩm quảng cáo in mầu",
    3: "Văn bản chứng minh quyền sở hữu hoặc quyền sử dụng bảng quảng cáo",
    4: "Bản phối cảnh vị trí đặt bảng quảng cáo",
    5: "Bản sao giấy phép xây dựng công trình quảng cáo",
    6: "Thông báo sản phẩm quảng cáo trên bảng quảng cáo, băng-rôn",
}
# Cột "Bản chính / Bản sao" theo DOM của từng dòng.
_LOAI_BAN = {0: "Bản sao", 1: "Bản sao", 2: "Bản chính", 3: "Bản chính", 4: "Bản chính", 5: "Bản sao",
             6: "Bản chính"}

# Dò ô upload THEO CHỮ của dòng, không theo thứ tự: trên trang thật số ô engine nhận ra có thể ít hơn 7
# (thứ tự lệch → đính nhầm dòng / "không tìm thấy ô"). Engine khoanh các dòng dưới tiêu đề bảng rồi khớp
# cụm chữ riêng của từng dòng (đã fold dấu).
_BANG_HEADER = "Thành phần hồ sơ"
_SLOT_KEYWORDS = {
    0: ["hop chuan"],
    1: ["to chuc su kien"],
    2: ["ket san pham quang cao"],
    3: ["quyen so huu hoac quyen su dung bang quang cao"],
    4: ["ban phoi canh"],
    5: ["giay phep xay dung cong trinh quang cao"],
    6: ["thong bao san pham quang cao tren bang quang cao"],
}

_T_OTHER = "other"
_ROUTES: dict[str, int] = {
    "hop_chuan_hop_quy": 0,
    "gcn_dang_ky_doanh_nghiep": 0,
    "thong_bao_khuyen_mai": 0,
    "van_ban_su_kien": 1,
    "maket": 2,
    "quyen_su_dung_dia_diem": 3,
    "phoi_canh": 4,
    "giay_phep_xay_dung": 5,
    "thong_bao_mau_01": 6,
}
_DISPLAY = {
    "hop_chuan_hop_quy": "Giấy tờ hợp chuẩn, hợp quy",
    "gcn_dang_ky_doanh_nghiep": "Giấy chứng nhận đăng ký doanh nghiệp",
    "thong_bao_khuyen_mai": "Thông báo thực hiện khuyến mại",
    "van_ban_su_kien": "Văn bản về việc tổ chức sự kiện",
    "maket": "Ma-két sản phẩm quảng cáo",
    "quyen_su_dung_dia_diem": "Văn bản chứng minh quyền sử dụng địa điểm quảng cáo",
    "phoi_canh": "Bản phối cảnh vị trí đặt quảng cáo",
    "giay_phep_xay_dung": "Giấy phép xây dựng công trình quảng cáo",
    "thong_bao_mau_01": "Thông báo sản phẩm quảng cáo trên bảng quảng cáo, băng-rôn",
}
_ALLOWED = set(_ROUTES) | {_T_OTHER}
_SLOT_KHONG_RO = _ROUTES["thong_bao_mau_01"]


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _canon(value: Any) -> str:
    return re.sub(r"[_\-\s]+", "_", _fold(value)).strip("_")


def _normalize_doc_type(value: Any) -> str:
    canon = _canon(value)
    return next((t for t in _ALLOWED if canon == _canon(t)), _T_OTHER)


async def _classify_one(document: dict[str, Any]) -> tuple[int, str]:
    index = int(document["index"])
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(
            [{"index": index, "text": str(document.get("text") or "")[:14000]}]
        )},
    ]
    raw = await client.chat(messages, max_tokens=220, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    first = next(iter(parsed.get("documents", []) or []), {})
    return index, _normalize_doc_type(first.get("docType") or first.get("type"))


async def _classify_with_llm(documents: list[dict[str, Any]], errors: list[str]) -> dict[int, str]:
    outcomes = await asyncio.gather(*(_classify_one(d) for d in documents), return_exceptions=True)
    result: dict[int, str] = {}
    for document, outcome in zip(documents, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            errors.append(f"attachment_agent file {document.get('index')}: {outcome}")
            continue
        result[outcome[0]] = outcome[1]
    return result


def _ung_vien_phoi_canh(llm_types: dict[int, str], file_count: int) -> list[int]:
    """Tệp maket + tệp other khi hồ sơ thiếu phối cảnh mà có ≥2 ma-két hoặc có ma-két kèm tệp chưa rõ loại.

    Ảnh phối cảnh không chỉ bị đọc thành ma-két: OCR ảnh chụp ít chữ, LLM hay trả other → rơi xuống dòng (7). Hồ
    sơ có ma-két thì gần như chắc có phối cảnh, nên tệp other cũng là ứng viên. Tệp không OCR ra chữ / LLM lỗi
    (không có trong llm_types) tính là other.
    """
    if "phoi_canh" in llm_types.values():
        return []
    maket = [i for i, t in llm_types.items() if t == "maket"]
    other = [i for i in range(file_count) if llm_types.get(i, _T_OTHER) == _T_OTHER]
    if len(maket) >= 2 or (maket and other):
        return sorted(maket + other)
    return []


async def _chon_phoi_canh(documents: list[dict[str, Any]], fallback: int, errors: list[str]) -> int:
    """LLM chọn trong các ứng viên tệp giống ảnh phối cảnh nhất. Lỗi/trả index lạ → `fallback`."""
    candidates = [int(d["index"]) for d in documents]
    try:
        messages = [
            {"role": "system", "content": PICK_PHOI_CANH_PROMPT},
            {"role": "user", "content": build_pick_prompt(
                [{"index": d["index"], "text": str(d.get("text") or "")[:6000]} for d in documents]
            )},
        ]
        raw = await client.chat(messages, max_tokens=220, enable_thinking=settings.agent_reasoning)
        chosen = int(client.extract_json_block(raw).get("index"))
        if chosen in candidates:
            return chosen
        errors.append(f"attachment_agent chọn phối cảnh: index {chosen} không thuộc {candidates}")
    except Exception as exc:  # noqa: BLE001 — lượt phụ, lỗi thì rơi về tệp đầu, không làm hỏng cả lượt đính
        errors.append(f"attachment_agent chọn phối cảnh: {exc}")
    return fallback


def build_plan_items(files: list[dict], llm_types: dict[int, str] | None = None) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    attachments: list[dict] = []
    classified: list[dict] = []
    unknown: list[str] = []

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        doc_type = llm_types.get(index, _T_OTHER)
        if doc_type not in _ALLOWED:
            doc_type = _T_OTHER
        slot = _ROUTES.get(doc_type, _SLOT_KHONG_RO)
        if doc_type == _T_OTHER:
            unknown.append(file_name)
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": _DISPLAY.get(doc_type, file_name),
            "componentName": _SLOT_NAMES[slot],
            "loaiBan": _LOAI_BAN[slot],
            "target": "fixed-slot",
            "needsAddComponent": False,
            # slotKey theo DÒNG: engine gom mọi tệp cùng slotKey vào MỘT ô upload — theo loại giấy thì 3 loại
            # của dòng (1) thành 3 nhóm tranh một ô, nhóm sau báo "không tìm thấy ô".
            "slotKey": f"spqc_row_{slot}",
            "slotIndex": slot,
            "slotName": _SLOT_NAMES[slot],
            "sectionHeader": _BANG_HEADER,
            "slotKeywords": _SLOT_KEYWORDS[slot],
            "detectedType": doc_type,
        })
        classified.append({
            "fileName": file_name, "docType": doc_type,
            "source": "llm" if index in llm_types else "default", "slotIndex": slot,
        })

    warnings: list[str] = []
    if unknown:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã đưa vào dòng \"Thông báo sản phẩm quảng cáo\" (trang không có ô "
            f"giấy tờ khác): {', '.join(unknown)} — cán bộ đối chiếu lại."
        )
    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_pairs = [(index, file) for index, file in enumerate(raw_files) if file.get("type") in _OCR_TYPES]
    errors: list[str] = []

    from app.services import ocr

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file([file for _, file in ocr_pairs]) if ocr_pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    # Kết quả OCR khớp THỨ TỰ đầu vào — hai tệp cùng tên là hai nguồn khác nhau, không map theo tên.
    text_by_index: dict[int, str] = {}
    for (index, _), result in zip(ocr_pairs, ocr_results):
        if result.get("error"):
            errors.append(f"OCR {result.get('name')}: {result['error']}")
        text_by_index[index] = str(result.get("text") or "")

    llm_documents = [{"index": i, "text": t} for i, t in text_by_index.items() if t.strip()]
    started = time.monotonic()
    llm_types = await _classify_with_llm(llm_documents, errors) if llm_documents else {}
    warnings: list[str] = []
    ung_vien = _ung_vien_phoi_canh(llm_types, len(raw_files))
    if ung_vien:
        # LLM lỗi: lấy tệp other đầu tiên (vốn đã rơi dòng 7, chuyển không mất gì); không có thì ma-két đầu.
        fallback = next((i for i in ung_vien if llm_types.get(i) != "maket"), ung_vien[0])
        chosen = await _chon_phoi_canh(
            [{"index": i, "text": text_by_index.get(i, "")} for i in ung_vien], fallback, errors,
        )
        llm_types[chosen] = "phoi_canh"
        warnings.append(
            f"Hồ sơ chưa có bản phối cảnh (chọn trong {len(ung_vien)} tệp đọc ra là ma-két/chưa rõ loại) — đã đưa "
            f"\"{raw_files[chosen]['name']}\" vào dòng \"Bản phối cảnh vị trí đặt bảng quảng cáo\", cán bộ đối chiếu lại."
        )
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, plan_warnings, classified = build_plan_items(raw_files, llm_types)
    warnings.extend(plan_warnings)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "llmDocuments": [raw_files[d["index"]]["name"] for d in llm_documents],
            "classified": classified,
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

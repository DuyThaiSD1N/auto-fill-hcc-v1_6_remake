"""Đính kèm Đăng ký tạm trú — mục "HỒ SƠ ĐÍNH KÈM" ngay trên trang kê khai của Cổng DVC Bộ Công an.

Mục này chia NHÓM theo trường hợp chỗ ở (bảng giấy tờ của nhóm chỉ nạp khi bấm vào nhóm), hồ sơ chỉ dùng
MỘT nhóm. Ba trường hợp trợ lý xử lý (prompt.py chọn, luật chữ là dự phòng khi LLM lỗi):
  owned     (0) thuộc quyền sở hữu của mình  — Tờ khai | Giấy tờ chứng minh chỗ ở hợp pháp
  consented (1) không thuộc sở hữu, được chủ hộ & chủ sở hữu đồng ý
                                             — Tờ khai | Quan hệ nhân thân | Điểm b, c khoản 2 Điều 20 | + Thêm mới GCN
  rented    (2) do thuê, mượn, ở nhờ         — Tờ khai | Hợp đồng cho thuê/mượn/ở nhờ | + Thêm mới GCN
CCCD không có dòng (cổng lấy từ CSDL dân cư) → không đính.

Plan item target "bca-row" do content/attach-core.js (attachFilesByBcaPlan) thi hành: mở nhóm theo
`groupIndex`/`groupLabel`, tìm dòng có chữ `rowKey`, hoặc bấm "+ Thêm mới" khi `newRow` rồi ghi tên dòng.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold
from app.pipelines.dang_ky_tam_tru.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

TO_KHAI = "to_khai"
HOP_DONG = "hop_dong"
GCN = "gcn"
QUAN_HE = "quan_he"
DAC_BIET = "dac_biet"
CCCD = "cccd"
OTHER = "other"
_DOC_TYPES = {TO_KHAI, HOP_DONG, GCN, QUAN_HE, DAC_BIET, CCCD, OTHER}

OWNED = "owned"
CONSENTED = "consented"
RENTED = "rented"

GROUPS = {
    OWNED: {"groupIndex": 0, "groupLabel": "Đăng ký tạm trú tại chỗ ở hợp pháp thuộc quyền sở hữu của mình"},
    CONSENTED: {
        "groupIndex": 1,
        "groupLabel": "Đăng ký tạm trú tại chỗ ở hợp pháp không thuộc quyền sở hữu của mình khi được chủ hộ "
                      "tạm trú và chủ sở hữu chỗ ở hợp pháp đó đồng ý",
    },
    RENTED: {"groupIndex": 2, "groupLabel": "Đăng ký tạm trú tại chỗ ở hợp pháp do thuê, mượn, ở nhờ"},
}

# (componentName, rowKey) — rowKey là cụm chữ (bỏ dấu, bỏ dấu câu) có trong dòng của bảng giấy tờ.
_TO_KHAI_ROW = ("Tờ khai thay đổi thông tin cư trú", "to khai thay doi thong tin cu tru")
NEW_ROW = None  # bấm "+ Thêm mới" của nhóm
# Tên ghi vào ô "Tên giấy tờ" của dòng "+ Thêm mới".
GCN_NEW_ROW_NAME = "Giấy chứng nhận quyền sử dụng đất"
ROWS: dict[str, dict[str, tuple[str, str] | None]] = {
    OWNED: {
        TO_KHAI: _TO_KHAI_ROW,
        GCN: ("Giấy tờ, tài liệu chứng minh chỗ ở hợp pháp", "chung minh cho o hop phap"),
        HOP_DONG: ("Giấy tờ, tài liệu chứng minh chỗ ở hợp pháp", "chung minh cho o hop phap"),
    },
    CONSENTED: {
        TO_KHAI: _TO_KHAI_ROW,
        QUAN_HE: ("Giấy tờ, tài liệu chứng minh quan hệ nhân thân với chủ hộ tạm trú, thành viên hộ gia đình",
                  "quan he nhan than"),
        DAC_BIET: ("Giấy tờ, tài liệu chứng minh thuộc trường hợp quy định tại điểm b, c khoản 2 Điều 20 Luật Cư trú",
                   "khoan 2 dieu 20"),
        GCN: NEW_ROW,
    },
    RENTED: {
        TO_KHAI: _TO_KHAI_ROW,
        HOP_DONG: ("Hợp đồng cho thuê, cho mượn, cho ở nhờ hoặc văn bản về việc cho mượn, cho ở nhờ chỗ ở hợp pháp",
                   "hop dong cho thue"),
        GCN: NEW_ROW,
    },
}

# documentName là TÊN TỆP khi đính (bật đổi tên tệp). Cổng từ chối tên có . , ~ " # % & * : < > ? / { | } → giữ tên
# ngắn, không dấu câu (content/attach-core.js bcaFilesForRow còn lọc lại lần nữa).
_DOCUMENT_NAMES = {
    TO_KHAI: "Tờ khai thay đổi thông tin cư trú",
    HOP_DONG: "Hợp đồng cho thuê",
    GCN: "Giấy chứng nhận quyền sử dụng đất",
    QUAN_HE: "Giấy tờ chứng minh quan hệ nhân thân",
    DAC_BIET: "Giấy tờ chứng minh trường hợp đặc biệt",
}


def doc_type(text: str) -> str:
    """Luật chữ dự phòng. Tờ khai xét TRƯỚC: mục 10 của CT01 hay nhắc cả hợp đồng thuê lẫn GCN."""
    t = fold(text)
    if "to khai thay doi thong tin cu tru" in t or "mau ct01" in t:
        return TO_KHAI
    if "hop dong" in t and any(k in t for k in ("cho thue", "hop dong thue", "cho muon", "cho o nho")):
        return HOP_DONG
    if "giay chung nhan" in t and ("quyen su dung dat" in t or "quyen so huu nha" in t):
        return GCN
    if any(k in t for k in ("giay khai sinh", "trich luc khai sinh", "chung nhan ket hon", "dang ky ket hon")):
        return QUAN_HE
    if "can cuoc" in t or "identity card" in t:
        return CCCD
    return ""


def rule_case(kinds: list[str]) -> str:
    if HOP_DONG in kinds:
        return RENTED
    if QUAN_HE in kinds or DAC_BIET in kinds:
        return CONSENTED
    if GCN in kinds:
        return OWNED
    return RENTED


def _item(file: dict, index: int, kind: str, group: dict, row: tuple[str, str] | None) -> dict:
    new_row = row is None
    return {
        "fileIndex": index,
        "fileName": str(file.get("name") or f"file-{index + 1}"),
        "documentName": _DOCUMENT_NAMES[kind],
        "componentName": GCN_NEW_ROW_NAME if new_row else row[0],
        "target": "bca-row",
        "needsAddComponent": new_row,
        "newRow": new_row,
        "rowKey": "" if new_row else row[1],
        "detectedType": _DOCUMENT_NAMES[kind],
        **group,
    }


def build_plan_items(files: list[dict], kinds: list[str], case: str) -> tuple[list[dict], list[str], list[dict]]:
    group = GROUPS[case]
    rows = ROWS[case]
    items: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    for index, (file, kind) in enumerate(zip(files, kinds)):
        name = str(file.get("name") or f"file-{index + 1}")
        classified.append({"fileName": name, "docType": kind or OTHER})
        if kind == CCCD:
            continue  # cổng không có dòng CCCD — thông tin lấy từ CSDL quốc gia về dân cư
        if kind in rows:
            items.append(_item(file, index, kind, group, rows[kind]))
        elif kind in _DOCUMENT_NAMES:
            warnings.append(f"File '{name}' ({_DOCUMENT_NAMES[kind]}) không có dòng trong nhóm "
                            f"\"{group['groupLabel']}\" — bỏ qua, vui lòng kiểm tra lại.")
        else:
            warnings.append(f"Không xác định được loại giấy tờ cho file '{name}' — bỏ qua, vui lòng đính kèm thủ công.")
    return items, warnings, classified


async def _ocr_per_file(files: list[dict]) -> list[dict]:
    from app.services import ocr

    return await ocr.ocr_per_file(files)


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict:
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=700, enable_thinking=settings.agent_reasoning)
    return client.extract_json_block(raw) or {}


def resolve(texts: list[str], llm: dict | None) -> tuple[list[str], str, str]:
    """(loại từng file, trường hợp, nguồn). LLM thiếu/sai loại ở file nào thì file đó theo luật chữ."""
    rule_kinds = [doc_type(text) for text in texts]
    llm = llm or {}
    by_index: dict[int, str] = {}
    for doc in llm.get("documents") or []:
        try:
            by_index[int(doc.get("index"))] = str(doc.get("docType") or "")
        except (TypeError, ValueError):
            continue
    kinds = []
    for i, rule in enumerate(rule_kinds):
        picked = by_index.get(i, "")
        kinds.append(picked if picked in _DOC_TYPES and picked != OTHER else (rule or picked))
    case = str(llm.get("case") or "")
    if case in GROUPS:
        return kinds, case, "llm"
    return kinds, rule_case(kinds), "rule"


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options, session
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]
    t0 = time.monotonic()
    ocr_results = await _ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    errors = [f"OCR {r.get('name')}: {r['error']}" for r in ocr_results if r.get("error")]
    by_name = {r.get("name"): str(r.get("text") or "") for r in ocr_results}
    texts = [by_name.get(f.get("name"), "") for f in raw_files]

    t1 = time.monotonic()
    llm: dict = {}
    documents = [{"index": i, "text": text} for i, text in enumerate(texts) if text.strip()]
    if documents:
        try:
            llm = await _classify_with_llm(documents)
        except Exception as exc:  # noqa: BLE001 — LLM lỗi thì luật chữ vẫn xếp được
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    kinds, case, source = resolve(texts, llm)
    attachments, warnings, classified = build_plan_items(raw_files, kinds, case)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "case": case,
            "caseSource": source,
            "caseReason": str(llm.get("reason") or "") if source == "llm" else "",
            "classified": classified,
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

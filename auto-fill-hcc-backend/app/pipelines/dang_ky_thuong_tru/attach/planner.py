"""Đính kèm Đăng ký thường trú — mục "Trường hợp và hồ sơ đính kèm" ngay trên trang kê khai (Cổng DVC Bộ Công an).

Mục chia NHÓM theo trường hợp chỗ ở (bảng giấy tờ của nhóm chỉ nạp khi bấm vào nhóm), hồ sơ chỉ dùng MỘT nhóm. Ba
trường hợp trợ lý xử lý (LLM chọn trong prompt.py; crawl 16/11/2026):
  owned     (1) thuộc quyền sở hữu của mình  — Tờ khai | Giấy tờ chứng minh chỗ ở hợp pháp | + Thêm
  consented (2) được chủ hộ & chủ sở hữu đồng ý — Tờ khai | Điểm b, c khoản 2 Điều 20 | + Thêm
  rented    (3) do thuê, mượn, ở nhờ           — Tờ khai | Đủ diện tích nhà ở | Hợp đồng cho thuê… | + Thêm
Giấy có loại rõ mà nhóm không có dòng riêng (quan hệ nhân thân, GCN…) → dòng "+ Thêm" mang tên giấy. CCCD (cổng không
có dòng) và giấy chưa rõ loại → dòng Tờ khai của nhóm (cổng nhận nhiều tệp một dòng) + cảnh báo; không bỏ tệp nào.
LLM lỗi → mọi tệp vào dòng Tờ khai của nhóm "consented" kèm cảnh báo — không đoán loại giấy bằng từ khoá.

Plan item target "bca-row" do extension (attachFilesByBcaPlan) thi hành: mở nhóm theo `groupIndex`/`groupLabel`, tìm
dòng có chữ `rowKey`, hoặc bấm "+ Thêm" khi `newRow` rồi ghi tên dòng.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines.dang_ky_thuong_tru.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

TO_KHAI = "to_khai"
HOP_DONG = "hop_dong"
GCN = "gcn"
DIEN_TICH = "dien_tich"
QUAN_HE = "quan_he"
DAC_BIET = "dac_biet"
CCCD = "cccd"
OTHER = "other"
_DOC_TYPES = {TO_KHAI, HOP_DONG, GCN, DIEN_TICH, QUAN_HE, DAC_BIET, CCCD, OTHER}

OWNED = "owned"
CONSENTED = "consented"
RENTED = "rented"
# LLM lỗi / không chọn: trường hợp hay gặp nhất của thường trú (về ở với người thân) — cảnh báo cho cán bộ soát.
DEFAULT_CASE = CONSENTED

GROUPS = {
    OWNED: {"groupIndex": 1, "groupLabel": "Đăng ký thường trú vào chỗ ở hợp pháp thuộc quyền sở hữu của mình"},
    CONSENTED: {
        "groupIndex": 2,
        "groupLabel": "Đăng ký thường trú tại chỗ ở hợp pháp không thuộc quyền sở hữu của mình khi được chủ hộ và chủ "
                      "sở hữu chỗ ở hợp pháp đó đồng ý",
    },
    RENTED: {"groupIndex": 3, "groupLabel": "Đăng ký thường trú tại chỗ ở hợp pháp do thuê, mượn, ở nhờ"},
}

# (componentName, rowKey) — rowKey là cụm chữ (bỏ dấu, bỏ dấu câu) có trong dòng của bảng giấy tờ.
_TO_KHAI_ROW = ("Tờ khai thay đổi thông tin cư trú", "to khai thay doi thong tin cu tru")
_CHO_O_ROW = ("Giấy tờ, tài liệu chứng minh chỗ ở hợp pháp", "chung minh cho o hop phap")
ROWS: dict[str, dict[str, tuple[str, str]]] = {
    OWNED: {TO_KHAI: _TO_KHAI_ROW, GCN: _CHO_O_ROW, HOP_DONG: _CHO_O_ROW},
    CONSENTED: {
        TO_KHAI: _TO_KHAI_ROW,
        DAC_BIET: ("Giấy tờ, tài liệu chứng minh thuộc trường hợp quy định tại điểm b, c khoản 2 điều 20 Luật Cư trú",
                   "khoan 2 dieu 20"),
    },
    RENTED: {
        TO_KHAI: _TO_KHAI_ROW,
        DIEN_TICH: ("Giấy tờ, tài liệu chứng minh đủ diện tích nhà ở để đăng ký thường trú theo quy định",
                    "du dien tich nha o"),
        HOP_DONG: ("Hợp đồng cho thuê, cho mượn, cho ở nhờ hoặc văn bản về việc cho mượn, cho ở nhờ chỗ ở hợp pháp",
                   "hop dong cho thue"),
    },
}
# Loại giấy rõ ràng mà nhóm không có dòng riêng → dòng "+ Thêm" với tên này (một dòng cho mọi tệp cùng loại).
NEW_ROW_NAMES = {
    QUAN_HE: "Giấy tờ chứng minh quan hệ nhân thân",
    GCN: "Giấy chứng nhận quyền sử dụng đất",
    DIEN_TICH: "Giấy tờ chứng minh đủ diện tích nhà ở",
    DAC_BIET: "Giấy tờ chứng minh trường hợp đặc biệt",
    HOP_DONG: "Hợp đồng cho thuê cho mượn cho ở nhờ",
}

# documentName là TÊN TỆP khi đính (bật đổi tên tệp). Cổng từ chối tên có . , ~ " # % & * : < > ? / { | } →
# extension lọc lại lần nữa khi đổi tên.
_DOCUMENT_NAMES = {
    TO_KHAI: "Tờ khai thay đổi thông tin cư trú",
    HOP_DONG: "Hợp đồng cho thuê",
    GCN: "Giấy chứng nhận quyền sử dụng đất",
    DIEN_TICH: "Giấy tờ chứng minh đủ diện tích nhà ở",
    QUAN_HE: "Giấy tờ chứng minh quan hệ nhân thân",
    DAC_BIET: "Giấy tờ chứng minh trường hợp đặc biệt",
}
_NAME_MAX = 50


def _clean_name(value: Any) -> str:
    text = re.sub(r"[.,~\"#%&*:<>?/\\{|}()\[\]]+", " ", str(value or ""))
    return " ".join(text.split())[:_NAME_MAX].strip()


def _item(file: dict, index: int, kind: str, name: str, group: dict, row: tuple[str, str] | None,
          new_row_name: str = "") -> dict:
    file_name = str(file.get("name") or f"file-{index + 1}")
    return {
        "fileIndex": index,
        "fileName": file_name,
        "documentName": name or file_name,
        "componentName": new_row_name if row is None else row[0],
        "target": "bca-row",
        "needsAddComponent": row is None,
        "newRow": row is None,
        "rowKey": "" if row is None else row[1],
        "detectedType": _DOCUMENT_NAMES.get(kind, kind or OTHER),
        **group,
    }


def build_plan_items(files: list[dict], kinds: list[str], names: list[str], case: str
                     ) -> tuple[list[dict], list[str], list[dict]]:
    group = GROUPS[case]
    rows = ROWS[case]
    items: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    extra_files: list[str] = []
    for index, (file, kind, llm_name) in enumerate(zip(files, kinds, names)):
        file_name = str(file.get("name") or f"file-{index + 1}")
        name = _DOCUMENT_NAMES.get(kind) or llm_name or file_name
        if kind in rows:
            items.append(_item(file, index, kind, name, group, rows[kind]))
            classified.append({"fileName": file_name, "docType": kind})
        elif kind in NEW_ROW_NAMES:
            items.append(_item(file, index, kind, llm_name or name, group, None, NEW_ROW_NAMES[kind]))
            classified.append({"fileName": file_name, "docType": kind, "routedTo": "new"})
        else:
            # CCCD (cổng không có dòng), giấy chưa rõ loại → dòng Tờ khai của nhóm.
            items.append(_item(file, index, kind, name, group, rows[TO_KHAI]))
            classified.append({"fileName": file_name, "docType": kind or OTHER, "routedTo": TO_KHAI})
            extra_files.append(file_name)
    if extra_files:
        warnings.append(
            f"Giấy tờ không có dòng riêng hoặc chưa rõ loại đã đính chung dòng \"{rows[TO_KHAI][0]}\": "
            + ", ".join(extra_files)
        )
    return items, warnings, classified


async def _ocr_per_file(files: list[dict]) -> list[dict]:
    from app.services import ocr

    return await ocr.ocr_per_file(files)


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict:
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=900, enable_thinking=settings.agent_reasoning)
    return client.extract_json_block(raw) or {}


def resolve(count: int, llm: dict | None) -> tuple[list[str], list[str], str, str]:
    """(loại từng file, tên từng file, trường hợp, nguồn). Loại ngoài danh sách / thiếu file nào → other."""
    llm = llm or {}
    kinds = [OTHER] * count
    names = [""] * count
    for doc in llm.get("documents") or []:
        try:
            index = int(doc.get("index"))
        except (TypeError, ValueError):
            continue
        if 0 <= index < count:
            kind = str(doc.get("docType") or "")
            kinds[index] = kind if kind in _DOC_TYPES else OTHER
            names[index] = _clean_name(doc.get("documentName"))
    case = str(llm.get("case") or "")
    if case in GROUPS:
        return kinds, names, case, "llm"
    return kinds, names, DEFAULT_CASE, "default"


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
        except Exception as exc:  # noqa: BLE001 — LLM lỗi thì mọi tệp vẫn được đính vào dòng Tờ khai
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    kinds, names, case, source = resolve(len(raw_files), llm)
    if source != "llm":
        errors.append(f"Chưa xác định được trường hợp chỗ ở — đã chọn nhóm \"{GROUPS[case]['groupLabel']}\", "
                      "cán bộ kiểm tra lại.")
    attachments, warnings, classified = build_plan_items(raw_files, kinds, names, case)
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

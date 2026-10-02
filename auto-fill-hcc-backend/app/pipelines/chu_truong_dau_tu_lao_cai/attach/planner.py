"""Đính kèm 3 thủ tục [Lào Cai] chấp thuận / điều chỉnh chủ trương đầu tư (cổng dichvucong.laocai.gov.vn,
eForm iGate, engine FE `fixed-slot` + "Giấy tờ khác" `otherListFile`).

Hồ sơ đầu tư gồm hàng chục văn bản trong khi bảng thành phần chia theo TRƯỜNG HỢP điều chỉnh với nhiều dòng gần
trùng nội dung. Ảnh hướng dẫn đính kèm của cơ quan tiếp nhận ĐÍNH CHUNG hồ sơ vào MỘT dòng — nhưng mỗi dòng
cổng chỉ nhận TỐI ĐA 5 TỆP ("Chỉ có thể chọn tối đa 5 tệp tin"). Vì vậy:
  - ≤ 5 tệp: tất cả vào dòng chính, tất định, không cần OCR/LLM.
  - > 5 tệp: LLM đọc từng tệp để (1) nhận ra VĂN BẢN ĐỀ NGHỊ — luôn xếp vào dòng chính trước — và (2) đặt tên
    tài liệu. Dòng chính nhận 5 tệp; phần tràn:
      · trang có "Giấy tờ khác" (1.009759, 1.009646) → mỗi tệp một dòng "Giấy tờ khác" có TÊN tài liệu
        (`target="new"`, FE tự bấm "+" thêm dòng, gõ tên rồi gán tệp);
      · trang không có "Giấy tờ khác" (1.009645) → các dòng cùng hồ sơ đề nghị (trường hợp 1, đề xuất dự án
        xây dựng, báo cáo tiền khả thi), mỗi dòng 5 tệp; hết chỗ thì cảnh báo để cán bộ đính tay.
LLM lỗi / OCR hụt → tệp giữ thứ tự tải lên, tên lấy từ tên tệp đã làm sạch. Không tệp nào bị bỏ im lặng.

slotIndex = thứ tự `input[type=file]` trên trang (đối chiếu snapshot, test khoá lại).
Cổng ghi "Dung lượng tối đa là 6 Mb" → cảnh báo tệp vượt (kích thước đo từ base64 của dataUrl).
"""

import asyncio
import re
import time
import unicodedata
from typing import Any

from app.config import settings
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_MAX_FILE_BYTES = 6 * 1024 * 1024
MAX_FILES_PER_ROW = 5
_DE_NGHI = "van_ban_de_nghi"
_MAX_DOCUMENT_NAME = 60


def _slot(key: str, index: int, name: str) -> dict:
    return {"slotKey": f"laocai_ctdt_{key}", "slotIndex": index, "slotName": name}


ROW_DIEU_CHINH_BQL = _slot("dieu_chinh_bql", 5, "Văn bản đề nghị điều chỉnh dự án đầu tư")
ROW_DIEU_CHINH_UBND = _slot("dieu_chinh_ubnd", 5, "c1) Đối với trường hợp a1, hồ sơ bao gồm")
ROW_CHAP_THUAN_UBND = _slot(
    "chap_thuan_ubnd", 0, "Hồ sơ đề nghị chấp thuận chủ trương đầu tư dự án đầu tư do nhà đầu"
)

CONFIG_DIEU_CHINH_BQL = {"rows": [ROW_DIEU_CHINH_BQL], "otherList": True}
CONFIG_DIEU_CHINH_UBND = {"rows": [ROW_DIEU_CHINH_UBND], "otherList": True}
# Trang gộp của 1.009645 không có "Giấy tờ khác" → tràn sang các dòng cùng thuộc hồ sơ đề nghị của nhà đầu tư.
# Bỏ dòng "2. … Tờ trình" (của cơ quan nhà nước) và dòng "trường hợp 2" (điều chỉnh dự án).
CONFIG_CHAP_THUAN_UBND = {
    "rows": [
        ROW_CHAP_THUAN_UBND,
        _slot("chap_thuan_ubnd_th1", 1, "Đối với trường hợp 1, hồ sơ bao gồm"),
        _slot("chap_thuan_ubnd_xay_dung", 3, "3. Đối với dự án đầu tư xây dựng, đề xuất dự án đầu tư gồm"),
        _slot("chap_thuan_ubnd_tien_kha_thi", 5,
              "4. Trường hợp pháp luật về xây dựng quy định lập báo cáo nghiên cứu tiền khả thi"),
    ],
    "otherList": False,
}


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _file_bytes(file: dict) -> int | None:
    """Kích thước thật, suy từ độ dài base64 của dataUrl (FileItem không mang size)."""
    data_url = file.get("dataUrl")
    if not isinstance(data_url, str) or "," not in data_url:
        return None
    payload = data_url.split(",", 1)[1]
    if not payload:
        return None
    return len(payload) * 3 // 4 - payload[-2:].count("=")


def _clean_document_name(raw: str) -> str:
    """Tên gõ vào ô "Tên giấy tờ": giữ số hiệu văn bản ("/" → "-"), bỏ ký tự lạ, cắt 60 ký tự."""
    text = unicodedata.normalize("NFC", str(raw or "")).replace("/", "-")
    chars = [ch if (ch.isalnum() or ch in " _-,.()") else " " for ch in text]
    text = re.sub(r"\s+", " ", "".join(chars)).strip(" -,.")
    return text[:_MAX_DOCUMENT_NAME].strip(" -,.")


def _name_from_file(file_name: str) -> str:
    """Dự phòng khi LLM không đặt được tên: tên tệp bỏ đuôi, bỏ dãy số hệ thống upload chèn vào, "_" → " "."""
    stem = re.sub(r"\.[A-Za-z0-9]{2,5}$", "", file_name)
    stem = re.sub(r"_?\d{8,}$", "", stem)
    return _clean_document_name(stem.replace("_", " "))


def _unique_name(base: str, used: set[str]) -> str:
    value = base or "Tài liệu kèm theo"
    candidate, suffix = value, 2
    while _fold(candidate) in used:
        candidate = f"{value[:52].strip()} {suffix}"
        suffix += 1
    used.add(_fold(candidate))
    return candidate


def _fixed_item(index: int, file_name: str, row: dict, detected_type: str) -> dict:
    return {
        "fileIndex": index,
        "fileName": file_name,
        "documentName": file_name,
        "componentName": row["slotName"],
        "target": "fixed-slot",
        "needsAddComponent": False,
        "detectedType": detected_type,
        "slotKey": row["slotKey"],
        "slotIndex": row["slotIndex"],
        "slotName": row["slotName"],
        "tickRow": True,
        # Cổng iGate VNPT: bấm option "Chọn tệp tin" mở hộp thoại file của hệ điều hành → chỉ gán thẳng.
        "noChooserClick": True,
    }


def _other_item(index: int, file_name: str, name: str, detected_type: str) -> dict:
    return {
        "fileIndex": index,
        "fileName": file_name,
        "documentName": name,
        "componentName": name,
        "target": "new",
        "needsAddComponent": True,
        "detectedType": detected_type,
        "noChooserClick": True,
    }


def build_plan_items(
    files: list[dict],
    config: dict,
    llm_types: dict[int, tuple[str, str]] | None = None,
) -> tuple[list[dict], list[str]]:
    llm_types = llm_types or {}
    names = [str(f.get("name") or f"file-{i + 1}") for i, f in enumerate(files)]
    doc_type = {i: (llm_types.get(i) or ("", ""))[0] or "ho_so_dau_tu" for i in range(len(files))}
    # Văn bản đề nghị luôn vào dòng chính; còn lại giữ thứ tự tải lên.
    order = [i for i in range(len(files)) if doc_type[i] == _DE_NGHI]
    order += [i for i in range(len(files)) if doc_type[i] != _DE_NGHI]

    items: list[dict] = []
    rows = config["rows"]
    stray: list[str] = []
    used_names: set[str] = set()
    for position, index in enumerate(order):
        row_no = position // MAX_FILES_PER_ROW
        if row_no < len(rows):
            items.append(_fixed_item(index, names[index], rows[row_no], doc_type[index]))
        elif config["otherList"]:
            llm_name = _clean_document_name((llm_types.get(index) or ("", ""))[1])
            name = _unique_name(llm_name or _name_from_file(names[index]), used_names)
            items.append(_other_item(index, names[index], name, doc_type[index]))
        else:
            stray.append(names[index])

    warnings: list[str] = []
    if len(files) > MAX_FILES_PER_ROW:
        spill = [i["documentName"] for i in items if i["target"] == "new"]
        if spill:
            warnings.append(
                f"Mỗi thành phần hồ sơ trên cổng chỉ nhận tối đa {MAX_FILES_PER_ROW} tệp — {len(spill)} tệp còn lại "
                "được đính vào \"Giấy tờ khác\": " + ", ".join(spill) + "."
            )
    if stray:
        warnings.append(
            f"Hết chỗ đính (mỗi dòng tối đa {MAX_FILES_PER_ROW} tệp), cán bộ đính tay các tệp: " + ", ".join(stray) + "."
        )
    qua_nang = [
        f"{names[i]} ({round(size / 1024 / 1024, 1)} MB)"
        for i, file in enumerate(files)
        if (size := _file_bytes(file)) and size > _MAX_FILE_BYTES
    ]
    if qua_nang:
        warnings.append(
            "Tệp vượt giới hạn 6 MB của cổng nên có thể bị từ chối, hãy nén hoặc tách rồi tải lại: "
            + ", ".join(qua_nang) + "."
        )
    return items, warnings


async def _classify_one(index: int, text: str) -> tuple[int, str, str]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt([{"index": index, "text": text[:12000]}])},
    ]
    raw = await client.chat(messages, max_tokens=200, enable_thinking=settings.agent_reasoning)
    first = next(iter(client.extract_json_block(raw).get("documents", []) or []), {})
    doc_type = _DE_NGHI if str(first.get("docType") or "").strip() == _DE_NGHI else "other"
    return index, doc_type, str(first.get("documentName") or "").strip()


async def _plan(files: list[FileItem], config: dict) -> dict:
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    errors: list[str] = []
    llm_types: dict[int, tuple[str, str]] = {}
    ocr_ms = llm_ms = 0
    if len(raw_files) > MAX_FILES_PER_ROW:
        from app.services import ocr

        pairs = [(i, f) for i, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]
        started = time.monotonic()
        ocr_results = await ocr.ocr_per_file([f for _, f in pairs]) if pairs else []
        ocr_ms = int((time.monotonic() - started) * 1000)
        texts = {}
        for (index, file), result in zip(pairs, ocr_results):
            if result.get("error"):
                errors.append(f"OCR {file.get('name')}: {result['error']}")
            if str(result.get("text") or "").strip():
                texts[index] = str(result["text"])
        started = time.monotonic()
        outcomes = await asyncio.gather(*(_classify_one(i, t) for i, t in texts.items()), return_exceptions=True)
        llm_ms = int((time.monotonic() - started) * 1000)
        for index, outcome in zip(texts, outcomes):
            if isinstance(outcome, BaseException):
                errors.append(f"attachment_agent file {index}: {outcome}")
                continue
            llm_types[index] = (outcome[1], outcome[2])

    attachments, warnings = build_plan_items(raw_files, config, llm_types)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "classified": [
                {"fileName": item["fileName"], "docType": item["detectedType"], "target": item["target"],
                 "slotIndex": item.get("slotIndex"), "documentName": item["documentName"]}
                for item in attachments
            ],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }


async def plan_dieu_chinh_bql(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    return await _plan(files, CONFIG_DIEU_CHINH_BQL)


async def plan_dieu_chinh_ubnd(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    return await _plan(files, CONFIG_DIEU_CHINH_UBND)


async def plan_chap_thuan_ubnd(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    return await _plan(files, CONFIG_CHAP_THUAN_UBND)

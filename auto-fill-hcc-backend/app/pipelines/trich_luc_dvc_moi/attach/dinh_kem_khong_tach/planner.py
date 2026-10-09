"""Đính kèm cấp bản sao trích lục (Cổng DVC quốc gia mới).

Bảng thành phần hồ sơ chỉ có MỘT dòng ("Văn bản ủy quyền ...") và một input file dùng chung, không
`multiple`: extension bấm nút "Tải lên file" của dòng rồi nạp từng tệp. Chỉ có một đích nên mọi tệp đều vào dòng
này để không sót tệp; LLM chỉ đọc từng tệp để đặt TÊN tệp theo giấy tờ (OCR/LLM lỗi → giữ tên tệp gốc).

Cổng chỉ nhận tệp dưới 2 MB: tệp trên 2 MB được nén bằng đúng thang của cải chính (cùng Cổng DVC quốc gia mới), trả
về ở `replaceFiles` để extension đính bản nén thay bản gốc. Tệp nhỏ hơn để nguyên. OCR vẫn đọc bản gốc.
"""

import asyncio
import os
import re
import time

from app.config import settings
from app.pipelines._shared.naming import fold, normalize_document_name
from app.pipelines.cai_chinh_dvc_moi.attach.dinh_kem_khong_tach.planner import shrink_oversized
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
ROW_NAME = "Văn bản ủy quyền theo quy định của pháp luật"


def _document_name(file_name: str, doc_name: str) -> str:
    """Tên tệp khi đính = tên giấy tờ LLM đọc từ tiêu đề; LLM lỗi/không đọc ra → giữ tên tệp gốc."""
    stem = os.path.splitext(file_name)[0] or file_name
    if not doc_name:
        return stem
    # Tên tối đa 50 ký tự: bỏ bớt CẢ CHỮ ở cuối, không để normalize cắt giữa chữ ("…bổ sung th").
    words = doc_name.split()
    while len(words) > 1 and len(" ".join(words)) > 50:
        words.pop()
    name = normalize_document_name(" ".join(words), fallback=stem)
    # Tiêu đề giấy hay in HOA ("CĂN CƯỚC CÔNG DÂN", "Bản sao GIẤY KHAI SINH") → viết thường, hoa chữ đầu, để
    # tên các tệp đồng nhất và đánh số trùng khớp nhau.
    letters = [ch for ch in name if ch.isalpha()]
    if letters and sum(ch.isupper() for ch in letters) * 2 > len(letters):
        name = name[:1].upper() + name[1:].lower()
    return name


def _llm_document_name(answer: dict) -> str:
    """Tên LLM đặt cho tệp. Thẻ CCCD/CMND → "CCCD <họ tên không dấu> [mặt trước|mặt sau]": mặt sau chỉ có tên
    không dấu ở dòng MRZ, bỏ dấu cả hai mặt để hai mặt của cùng một người trùng tên, nhận ra cùng một thẻ."""
    side_key = str(answer.get("matThe") or "").strip().lower()
    if side_key not in ("truoc", "sau", "ca_hai"):
        return str(answer.get("documentName") or "").strip()
    # Một trang chụp cả hai mặt thẻ → không ghi mặt.
    side = {"truoc": "mặt trước", "sau": "mặt sau"}.get(side_key, "")
    holder = re.sub(r"[^a-z ]+", " ", fold(str(answer.get("chuThe") or "").replace("<", " ")))
    words = [word.capitalize() for word in holder.split()]
    while words and len(" ".join(words)) > 50 - len("CCCD  ") - len(side):  # tên tệp tối đa 50 ký tự
        words.pop()
    holder = " ".join(words)
    return " ".join(part for part in ("CCCD", holder, side) if part)


def _card_side(doc: dict) -> tuple[str, str]:
    """(mặt, chủ thẻ đã bỏ dấu) khi phần tử là MỘT mặt thẻ CCCD/CMND đọc ra chủ thẻ; ngược lại ("", "")."""
    side = str(doc.get("matThe") or "").strip().lower()
    holder = " ".join(re.sub(r"[^a-z ]+", " ", fold(str(doc.get("chuThe") or "").replace("<", " "))).split())
    return (side, holder) if side in ("truoc", "sau") and holder else ("", "")


def pair_card_sides(docs: list[dict]) -> list[list[int]]:
    """Nhóm vị trí phần tử: mặt trước + mặt sau thẻ của CÙNG chủ thẻ → một nhóm [trước, sau]; còn lại đứng riêng.

    Cán bộ cần MỘT tệp CCCD cho mỗi người, không tách hai mặt. Chỉ ghép từng cặp một trước – một sau, nên hai bản
    trùng của cùng một mặt không bị dồn vào nhau; không đọc ra chủ thẻ thì không ghép (không chắc cùng người)."""
    fronts: dict[str, list[int]] = {}
    backs: dict[str, list[int]] = {}
    for index, doc in enumerate(docs):
        side, holder = _card_side(doc)
        if side:
            (fronts if side == "truoc" else backs).setdefault(holder, []).append(index)
    paired: dict[int, list[int]] = {}
    for holder, front_list in fronts.items():
        for front, back in zip(front_list, backs.get(holder, [])):
            paired[min(front, back)] = [front, back]
            paired[max(front, back)] = []
    return [paired[i] if i in paired else [i] for i in range(len(docs)) if paired.get(i, [i])]


def both_sides(doc: dict) -> dict:
    """Phần tử đại diện cho thẻ đã gộp hai mặt → tên "CCCD <chủ thẻ>" (không ghi mặt)."""
    return {**doc, "matThe": "ca_hai"}


def _merge_groups(items: list[dict], groups: list[list[int]]) -> list[dict]:
    """Mỗi nhóm tệp → một mục: mục của tệp đầu nhóm, ghép thêm các tệp còn lại qua `sourceFileIndexes`."""
    out = []
    for group in groups:
        item = dict(items[group[0]])
        if len(group) > 1:
            item["sourceFileIndexes"] = group
        out.append(item)
    return out


def build_plan_items(file_names: list[str], doc_names: dict[int, str] | None = None) -> list[dict]:
    items = []
    seen: dict[str, int] = {}
    for index, name in enumerate(file_names):
        # Hai tệp cùng loại giấy (CCCD hai người...) → đánh số để cổng và cán bộ phân biệt được.
        document_name = _document_name(name, (doc_names or {}).get(index, ""))
        seen[document_name.lower()] = seen.get(document_name.lower(), 0) + 1
        if seen[document_name.lower()] > 1:
            document_name = f"{document_name} {seen[document_name.lower()]}"
        items.append({
            "fileIndex": index,
            "fileName": name,
            "documentName": document_name,
            "componentName": ROW_NAME,
            "target": "fixed-slot",
            "needsAddComponent": False,
            "slotKey": "uy_quyen",
            "slotIndex": 0,
            "slotName": ROW_NAME,
            "noChooserClick": True,
        })
    return items


def _max_tokens(texts: dict[int, str]) -> int:
    """Trần token theo tổng số trang của hồ sơ, đúng công thức planner form cũ."""
    pages = sum(max(1, len(re.findall(r"Trang \d+/\d+", text))) for text in texts.values())
    return max(1200, min(4000, pages * 180))


async def _classify_all(texts: dict[int, str]) -> dict[int, dict]:
    """MỘT lượt LLM cho cả hồ sơ (như planner form cũ); mỗi tệp đúng một phần tử, ghép lại theo index.

    Tệp trùng nội dung (cùng tệp tải lên hai lần) chỉ gửi một bản rồi dùng chung kết quả: gửi cả hai thì LLM hay
    trả một phần tử cho cả hai, tệp kia mất tên/dòng."""
    first_of: dict[str, int] = {}
    for i, t in texts.items():
        first_of.setdefault(t, i)
    sent = {i: t for t, i in first_of.items()}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt([{"index": i, "text": t[:12000]} for i, t in sent.items()])},
    ]
    raw = await client.chat(messages, max_tokens=_max_tokens(sent), enable_thinking=settings.agent_reasoning)
    answers: dict[int, dict] = {}
    for item in client.extract_json_block(raw).get("documents", []) or []:
        try:
            index = int(item.get("index"))
        except (AttributeError, TypeError, ValueError):
            continue
        if index in sent and index not in answers:
            answers[index] = item
    for i, t in texts.items():
        if i not in answers and first_of[t] in answers:
            answers[i] = answers[first_of[t]]
    return answers


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    from app.services import ocr

    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    errors: list[str] = []
    pairs = [(i, f) for i, f in enumerate(raw_files) if f.get("type") in _OCR_TYPES]
    started = time.monotonic()
    shrink_task = asyncio.create_task(shrink_oversized(raw_files, errors))
    ocr_results = await ocr.ocr_per_file([f for _, f in pairs]) if pairs else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    texts = {}
    for (index, file), result in zip(pairs, ocr_results):
        if result.get("error"):
            errors.append(f"OCR {file.get('name')}: {result['error']}")
        if str(result.get("text") or "").strip():
            texts[index] = str(result["text"])

    started = time.monotonic()
    answers: dict[int, dict] = {}
    if texts:
        try:
            answers = await _classify_all(texts)
        except Exception as exc:  # noqa: BLE001 — LLM lỗi → mọi tệp về dòng mặc định, giữ tên gốc
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)
    doc_names = {i: _llm_document_name(a) for i, a in answers.items()}
    # Hai TỆP là hai mặt thẻ của cùng một người → một mục gộp (extension ghép thành một PDF).
    groups = pair_card_sides([answers.get(i, {}) for i in range(len(raw_files))])
    for group in groups:
        if len(group) > 1:
            doc_names[group[0]] = _llm_document_name(both_sides(answers[group[0]]))

    replace_files = await shrink_task
    names = [replace_files[str(i)]["name"] if str(i) in replace_files else f["name"] for i, f in enumerate(raw_files)]
    items = build_plan_items(names, doc_names)
    return {
        "attachments": _merge_groups(items, groups),
        "replaceFiles": replace_files or None,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "shrunk": [
                {"fileName": r["name"], "originalBytes": r["originalBytes"], "bytes": r["bytes"], "level": r["level"]}
                for r in replace_files.values()
            ],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

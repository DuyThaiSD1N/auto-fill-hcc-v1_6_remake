"""Đính kèm cấp Giấy XNTTHN (Cổng DVC quốc gia mới).

Bảng thành phần có 3 dòng cố định (giấy XNTTHN đã cấp trước đó / giấy tờ ly hôn, khai tử của vợ chồng / văn bản ủy
quyền), một dòng nhận nhiều tệp qua nút "Tải lên file", không có nút "Thêm thành phần". LLM đọc từng tệp để xếp đúng
dòng; tệp không thuộc dòng riêng nào (tờ khai, CCCD, giấy kết hôn...) đính chung dòng giấy tờ hôn nhân để không sót
tệp. LLM lỗi / OCR hụt → dòng giấy tờ hôn nhân. Xã Nghĩa Hưng không đính tờ khai; phường Đông Hà chỉ đính
văn bản ủy quyền (cờ theo tài khoản).

Cổng chỉ nhận tệp dưới 2 MB: tệp trên 2 MB được nén bằng đúng thang của cải chính (cùng Cổng DVC quốc gia mới), trả
về ở `replaceFiles` để extension đính bản nén thay bản gốc. Tệp nhỏ hơn để nguyên. OCR vẫn đọc bản gốc.
"""

import asyncio
import os
import re
import time

from app.config import settings
from app.pipelines._shared.identity_merge import ho_ten_co_dau, mat_the, so_dinh_danh_the
from app.pipelines._shared.naming import fold, normalize_document_name
from app.pipelines.cai_chinh_dvc_moi.attach.dinh_kem_khong_tach.planner import shrink_merged, shrink_oversized
from app.process.schemas import FileItem
from app.services.llm import client

from ..nghia_hung import OMITTED_DECLARATION_NOTE, keep_only_authorization, omits_paper_declaration, only_authorization
from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# slotName = đoạn đầu chữ của dòng trên cổng (extension khớp 40 ký tự đầu đã bỏ dấu).
ROW_CAP_LAI = {"slotKey": "tthn_giay_cu", "slotIndex": 0,
               "slotName": "Trường hợp cá nhân yêu cầu cấp lại Giấy xác nhận tình trạng hôn nhân"}
ROW_HON_NHAN = {"slotKey": "tthn_ly_hon_khai_tu", "slotIndex": 1,
                "slotName": "Trường hợp người yêu cầu xác nhận tình trạng hôn nhân đã có vợ"}
ROW_UY_QUYEN = {"slotKey": "tthn_uy_quyen", "slotIndex": 2,
                "slotName": "Văn bản ủy quyền theo quy định của pháp luật"}
DEFAULT_ROW = ROW_HON_NHAN
DOC_TYPES = {"declaration", "identity", "authorization", "previous_certificate", "divorce_decision",
             "death_certificate", "marriage_certificate"}
ROWS = {
    "previous_certificate": ROW_CAP_LAI,
    "divorce_decision": ROW_HON_NHAN,
    "death_certificate": ROW_HON_NHAN,
    "authorization": ROW_UY_QUYEN,
}


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
    # Tên "CCCD <Họ Tên>" đã chuẩn hoa chữ đầu mỗi tiếng ở _llm_document_name → không hạ thường.
    if letters and sum(ch.isupper() for ch in letters) * 2 > len(letters) and not name.startswith("CCCD "):
        name = name[:1].upper() + name[1:].lower()
    return name


def _ten_chu_the(answer: dict) -> str:
    """Họ tên chủ thẻ GIỮ DẤU, hoa chữ đầu mỗi tiếng; dòng MRZ ("NGUYEN<<VAN<A") đổi "<" thành khoảng trắng."""
    words = re.sub(r"[^\w ]+", " ", str(answer.get("chuThe") or "").replace("<", " ")).split()
    return " ".join(word.capitalize() for word in words if not word.isdigit())


def _llm_document_name(answer: dict) -> str:
    """Tên LLM đặt cho tệp. Thẻ CCCD/CMND → "CCCD <họ tên có dấu> [mặt trước|mặt sau]"; hai mặt đã gộp (hoặc một
    ảnh chụp cả hai mặt) không ghi mặt."""
    side_key = str(answer.get("matThe") or "").strip().lower()
    if side_key not in ("truoc", "sau", "ca_hai"):
        return str(answer.get("documentName") or "").strip()
    side = {"truoc": "mặt trước", "sau": "mặt sau"}.get(side_key, "")
    words = _ten_chu_the(answer).split()
    while words and len(" ".join(words)) > 50 - len("CCCD  ") - len(side):  # tên tệp tối đa 50 ký tự
        words.pop()
    return " ".join(part for part in ("CCCD", " ".join(words), side) if part)


def _card_side(doc: dict) -> tuple[str, str, str]:
    """(mặt, số định danh đọc từ OCR, chủ thẻ đã bỏ dấu) khi phần tử là MỘT mặt thẻ CCCD/CMND; ngược lại rỗng.
    LLM không cho biết mặt thẻ, hoặc nói "ca_hai" mà chữ OCR chỉ có dấu hiệu của MỘT mặt (không MRZ / vân tay ở ảnh
    mặt trước) → dùng mặt đọc từ OCR (`_matTheOcr`)."""
    side = str(doc.get("matThe") or "").strip().lower()
    ocr_side = str(doc.get("_matTheOcr") or "")
    if not side or (side == "ca_hai" and ocr_side):
        side = ocr_side
    if side not in ("truoc", "sau"):
        return "", "", ""
    holder = " ".join(re.sub(r"[^a-z ]+", " ", fold(str(doc.get("chuThe") or "").replace("<", " "))).split())
    return side, str(doc.get("_soThe") or ""), holder


def pair_card_sides(docs: list[dict]) -> list[list[int]]:
    """Nhóm vị trí phần tử: mặt trước + mặt sau thẻ của CÙNG một người → một nhóm [trước, sau]; còn lại đứng riêng.

    Cán bộ cần MỘT tệp CCCD cho mỗi người, không tách hai mặt. Khoá ghép là SỐ ĐỊNH DANH đọc từ OCR (`_soThe`: mặt
    trước dãy 12 số, mặt sau dòng MRZ) — họ tên LLM đọc ở mặt sau có thể lệch (mặt sau CCCD gắn chip in thêm tên
    người ký). Mặt nào không đọc ra số mới ghép theo chủ thẻ đã bỏ dấu, và không ghép hai mặt mang hai số khác nhau.
    Chỉ ghép từng cặp một trước – một sau, nên hai bản trùng của cùng một mặt không bị dồn vào nhau."""
    info = {i: _card_side(doc) for i, doc in enumerate(docs)}
    fronts = [i for i, (side, so, holder) in info.items() if side == "truoc" and (so or holder)]
    backs = [i for i, (side, so, holder) in info.items() if side == "sau" and (so or holder)]
    paired: dict[int, list[int]] = {}

    def ghep(cung_nguoi) -> None:
        for front in fronts:
            back = next((b for b in backs if b not in paired and front not in paired and cung_nguoi(front, b)), None)
            if back is not None:
                paired[min(front, back)] = [front, back]
                paired[max(front, back)] = []

    ghep(lambda f, b: bool(info[f][1]) and info[f][1] == info[b][1])
    ghep(lambda f, b: bool(info[f][2]) and info[f][2] == info[b][2]
         and not (info[f][1] and info[b][1] and info[f][1] != info[b][1]))
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


def build_plan_items(file_names: list[str], doc_types: dict[int, str],
                     doc_names: dict[int, str] | None = None) -> list[dict]:
    items = []
    seen: dict[str, int] = {}
    for index, name in enumerate(file_names):
        # Hai tệp cùng loại giấy (CCCD hai người...) → đánh số để cổng và cán bộ phân biệt được.
        document_name = _document_name(name, (doc_names or {}).get(index, ""))
        seen[document_name.lower()] = seen.get(document_name.lower(), 0) + 1
        if seen[document_name.lower()] > 1:
            document_name = f"{document_name} {seen[document_name.lower()]}"
        doc_type = doc_types.get(index) if doc_types.get(index) in DOC_TYPES else "other"
        row = ROWS.get(doc_type, DEFAULT_ROW)
        items.append({
            "fileIndex": index,
            "fileName": name,
            "documentName": document_name,
            "componentName": row["slotName"],
            "target": "fixed-slot",
            "needsAddComponent": False,
            "detectedType": doc_type,
            "noChooserClick": True,
            **row,
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
        except Exception as exc:  # noqa: BLE001 — LLM lỗi → mọi tệp về dòng giấy tờ hôn nhân, giữ tên gốc
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)
    doc_types = {i: str(a.get("docType") or "").strip() for i, a in answers.items()}
    # Số định danh đọc từ OCR của từng tệp: khoá ghép hai mặt thẻ (họ tên LLM đọc có thể lệch giữa hai mặt).
    for i, a in answers.items():
        a["_soThe"] = so_dinh_danh_the(texts.get(i, ""))
        a["_matTheOcr"] = mat_the(texts.get(i, ""))
        a["chuThe"] = ho_ten_co_dau(a.get("chuThe") or "", texts.get(i, ""))
    doc_names = {i: _llm_document_name(a) for i, a in answers.items()}
    # Hai TỆP là hai mặt thẻ của cùng một người → một mục gộp (extension ghép thành một PDF).
    groups = pair_card_sides([answers.get(i, {}) for i in range(len(raw_files))])
    for group in groups:
        if len(group) > 1:
            doc_names[group[0]] = _llm_document_name(both_sides(answers[group[0]]))

    replace_files = await shrink_task
    names = [replace_files[str(i)]["name"] if str(i) in replace_files else f["name"] for i, f in enumerate(raw_files)]
    attachments = _merge_groups(build_plan_items(names, doc_types, doc_names), groups)
    if omits_paper_declaration(options):
        for item in [a for a in attachments if a["detectedType"] == "declaration"]:
            attachments.remove(item)
            errors.append(f"{OMITTED_DECLARATION_NOTE}: {item['fileName']}")
    if only_authorization(options):
        keep_only_authorization(attachments)
    await shrink_merged(raw_files, attachments, replace_files, errors)
    return {
        "attachments": attachments,
        # Đông Hà: hồ sơ không có ủy quyền thì không đính gì — extension coi là xong, không báo lỗi.
        "nothingToAttach": (only_authorization(options) and not attachments) or None,
        "replaceFiles": replace_files or None,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "classified": [
                {"fileName": item["fileName"], "docType": item["detectedType"], "slotIndex": item["slotIndex"]}
                for item in attachments
            ],
            "shrunk": [
                {"fileName": r["name"], "originalBytes": r["originalBytes"], "bytes": r["bytes"], "level": r["level"]}
                for r in replace_files.values()
            ],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

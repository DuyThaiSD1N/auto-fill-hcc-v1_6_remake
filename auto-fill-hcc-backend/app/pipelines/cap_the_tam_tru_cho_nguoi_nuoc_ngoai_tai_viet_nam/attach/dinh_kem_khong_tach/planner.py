"""Đính kèm Cấp thẻ tạm trú cho người nước ngoài tại Việt Nam (1.003460) — chế độ KHÔNG tách: mỗi tệp đính NGUYÊN.

Bảng "Thành phần hồ sơ" của Cổng DVC Bộ Công an (eForm Nth, CÙNG trang form kê khai như thị thực 1.001194) — ảnh ánh xạ
bộ mẫu 19/11/2026:
  - dòng 1 "Giấy tờ chứng minh thuộc diện xem xét cấp thẻ tạm trú …: giấy phép lao động, giấy xác nhận …";
  - dòng 2 "Tờ khai đề nghị cấp thẻ tạm trú cho người nước ngoài (NA8)";
  - dòng 3 "Văn bản đề nghị cấp thẻ tạm trú (mẫu NA6 đối với cơ quan, tổ chức, NA7 đối với cá nhân)";
  - "Giấy tờ khác" (thêm dòng, target "new"): hộ chiếu — bảng không có dòng riêng; căn cước + giấy khác cũng vào đây.
Hồ sơ dồn cả bộ trong MỘT tệp (ảnh ánh xạ: "01 file PDF, 6 trang") → đính NGUYÊN tệp vào cả 3 dòng lẫn dòng "Giấy tờ khác"
hộ chiếu. Ảnh chân dung (``filename46``) + ảnh trang nhân thân hộ chiếu (``filenamehc``) đầu form là ô tải ảnh riêng:
bước điền (process/runner.py) và bước đính kèm (``pageFields``) đều gắn bằng ``page_fields`` ở đây; ảnh chân dung không
đính vào bảng, hộ chiếu vẫn đính "Giấy tờ khác". "Ghi chú" (trang nào là giấy gì) do pipeline điền ghi bằng
``page_types`` ở đây.

Phân loại: tệp có từ HAI loại giấy trở lên (theo tiêu đề TỪNG trang — LLM chỉ thấy 4000 ký tự đầu) là ``ho_so_gop``;
còn lại LLM trước, LLM other / lỗi thì luật tiêu đề. Cổng chặn 6 MB/tệp. ``build_items`` dùng chung với chế độ tách.
"""

import re
import time
from pathlib import Path
from typing import Any

from app.config import settings
from app.pipelines._shared import fold
from app.pipelines._shared.compact_agent.runner import _extract_docx_text, _is_docx
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.cap_thi_thuc_cho_nguoi_nuoc_ngoai_tai_viet_nam.process.mapper import parse_mrz
from app.pipelines.chuyen_muc_dich_su_dung_dat_mien_nui_lai_chau.attach.planner import _data_url_size
from app.pipelines.dieu_chinh_thong_tin_ve_cu_tru.attach.dinh_kem_khong_tach.planner import ocr_pages
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
MAX_FILE_BYTES = 6 * 1024 * 1024
_HEAD_CHARS = 700

TO_KHAI = "to_khai"
VAN_BAN = "van_ban"
HO_CHIEU = "ho_chieu"
CHUNG_MINH = "chung_minh"
IDENTITY = "identity"
BIA = "bia_ho_so"
GOP = "ho_so_gop"
OTHER = "other"
BLANK = "blank_page"
# Ảnh chân dung 4x6: đã gắn ở ô tải ảnh đầu trang (process runner) → không đính vào bảng Thành phần hồ sơ.
PORTRAIT = "anh_chan_dung"
ALLOWED = {TO_KHAI, VAN_BAN, HO_CHIEU, CHUNG_MINH, IDENTITY, BIA, GOP, OTHER, BLANK}
# Loại giấy "thật" — tệp có từ hai loại trở lên là hồ sơ gộp (bìa / danh mục không tính).
SUBSTANTIVE = (TO_KHAI, VAN_BAN, HO_CHIEU, CHUNG_MINH, IDENTITY)

# slotName = cột "Tên giấy tờ" trên cổng (rút gọn); slotKeywords dạng đã fold (khớp foldChoiceText của extension).
SLOTS: list[dict[str, Any]] = [
    {
        "slotKey": "tttnnn_row01",
        "slotIndex": 0,
        "slotName": "Giấy tờ chứng minh thuộc diện xem xét cấp thẻ tạm trú",
        "slotKeywords": ["chung minh thuoc dien xem xet cap the tam tru"],
    },
    {
        "slotKey": "tttnnn_row02",
        "slotIndex": 1,
        "slotName": "Tờ khai đề nghị cấp thẻ tạm trú cho người nước ngoài (NA8)",
        "slotKeywords": ["to khai de nghi cap the tam tru"],
    },
    {
        "slotKey": "tttnnn_row03",
        "slotIndex": 2,
        "slotName": "Văn bản đề nghị cấp thẻ tạm trú (mẫu NA6 / NA7)",
        "slotKeywords": ["van ban de nghi cap the tam tru"],
    },
]
# Loại giấy của từng dòng (tệp gộp đính vào cả ba dòng); bìa / danh mục đi kèm dòng tờ khai.
ROW_ORDERS = {
    0: (CHUNG_MINH, GOP),
    1: (BIA, TO_KHAI, GOP),
    2: (VAN_BAN, GOP),
}
ROW_DOCUMENT_NAMES = {
    0: "Giấy tờ chứng minh thuộc diện xem xét cấp thẻ tạm trú",
    1: "Tờ khai đề nghị cấp thẻ tạm trú (Mẫu NA8)",
    2: "Văn bản đề nghị cấp thẻ tạm trú",
}
PASSPORT_NAME = "Hộ chiếu (trang nhân thân, trang thị thực, dấu kiểm chứng nhập cảnh)"
OTHER_NAMES = {IDENTITY: "Thẻ căn cước", BIA: "Danh mục thành phần hồ sơ"}

_VAN_BAN_RE = re.compile(r"form\)?\s*na\s*[67]\b|mau na\s*[67]\b|v/v de nghi cap the tam tru|van ban de nghi cap the tam tru"
                         r"|de nghi quy co quan xem xet cap the tam tru")
_TO_KHAI_RE = re.compile(r"to khai de nghi cap the tam tru|information form for a temporary|form\)?\s*na\s*8\b")
_CHUNG_MINH_RE = re.compile(r"\b(giay phep lao dong|work permit|xac nhan khong thuoc dien cap giay phep lao dong"
                            r"|giay chung nhan (dang ky )?dau tu|giay chung nhan ket hon|giay khai sinh|trich luc)\b")
_MRZ_RE = re.compile(r"p<[a-z<]{3}[a-z]")  # dòng MRZ 1 trên chữ đã bỏ khoảng trắng
_VISA_STAMP_RE = re.compile(r"viet nam visa|thi thuc viet nam|nhap canh\s*/\s*arrival")
# Nhãn trang nhân thân ("Passport No.", "PASSPORT … Type P"); câu "enclosed with passport" ở trang ghi chú NA8 không tính.
_PASSPORT_LABEL_RE = re.compile(r"passport\s*(no\b|n°|number)|\bpassport\b[\s\S]{0,40}\btype\b")


def canonical_type(value: Any) -> str:
    folded = fold(str(value or "")).replace(" ", "_")
    return folded if folded in ALLOWED else OTHER


def rule_doc_type(text: str) -> str:
    """Luật theo TIÊU ĐỀ của MỘT trang / một giấy. Thứ tự quan trọng: văn bản NA6 nhắc "tờ khai … kèm theo", tờ khai NA8
    và giấy phép lao động đều in "Passport" → xét trước hộ chiếu; hộ chiếu chỉ nhận theo MRZ / trang thị thực / dấu nhập
    cảnh / chữ PASSPORT ngay đầu trang (trang ghi chú của NA8 cũng có chữ "passport")."""
    haystack = fold(text)
    if not haystack.strip():
        return ""
    head = haystack[:_HEAD_CHARS]
    if re.search(r"\b(ho so thu tuc hanh chinh|danh muc thanh phan ho so)\b", head):
        return BIA
    if _VAN_BAN_RE.search(head):
        return VAN_BAN
    if _TO_KHAI_RE.search(head):
        return TO_KHAI
    if _CHUNG_MINH_RE.search(head):
        return CHUNG_MINH
    if (_MRZ_RE.search(haystack.replace(" ", "")) or _VISA_STAMP_RE.search(haystack)
            or _PASSPORT_LABEL_RE.search(head)):
        return HO_CHIEU
    if any(marker in head for marker in ("can cuoc", "chung minh nhan dan", "identity card")):
        return IDENTITY
    return ""


def page_types(text: str) -> list[str]:
    """Loại giấy của TỪNG trang (mốc trang OCR); trang không có tiêu đề riêng (trang 2 tờ khai, mặt sau) theo trang
    liền trước; trang đầu không nhận ra → other."""
    out: list[str] = []
    for page in ocr_pages(text or ""):
        kind = rule_doc_type(page) if page.strip() else BLANK
        if kind == "":
            kind = out[-1] if out and out[-1] != BLANK else OTHER
        out.append(kind)
    return out


def file_type(text: str) -> str:
    """Tệp có từ hai loại giấy thật trở lên → ho_so_gop; một loại → loại đó; không nhận ra → ""."""
    kinds = [k for k in dict.fromkeys(page_types(text)) if k in SUBSTANTIVE]
    if len(kinds) >= 2:
        return GOP
    if kinds:
        return kinds[0]
    return rule_doc_type(text)


def _clean_name(value: Any, limit: int = 250) -> str:
    text = " ".join(str(value or "").split()).strip(" .;,")
    return text[:limit].rstrip()


def _slot_item(slot: dict, file_index: int, file_name: str, doc_type: str) -> dict:
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": ROW_DOCUMENT_NAMES[slot["slotIndex"]],
        "componentName": slot["slotName"],
        "target": "fixed-slot",
        "needsAddComponent": False,
        "detectedType": doc_type,
        "slotKey": slot["slotKey"],
        "slotIndex": slot["slotIndex"],
        "slotName": slot["slotName"],
        "slotKeywords": slot["slotKeywords"],
        "tickRow": True,
    }


def _other_item(file_index: int, file_name: str, doc_type: str, name: str) -> dict:
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": name,
        "componentName": name,
        "target": "new",
        "componentIndex": None,
        "needsAddComponent": True,
        "detectedType": doc_type,
    }


def _passport_name(text: str) -> str:
    """"Hộ chiếu của PARK JI HOON (…)" theo dòng MRZ (ảnh ánh xạ); không đọc được tên thì bỏ phần "của …"."""
    mrz = parse_mrz(text)
    holder = " ".join(filter(None, (mrz.get("ho"), mrz.get("ten"))))
    return f"Hộ chiếu của {holder} (trang nhân thân, trang thị thực, dấu kiểm chứng nhập cảnh)" if holder else PASSPORT_NAME


def _ordered(entries: list[dict], order: tuple[str, ...]) -> list[dict]:
    picked = [e for e in entries if e["docType"] in order]
    return sorted(picked, key=lambda e: order.index(e["docType"]))  # sort ổn định: giữ thứ tự tệp, trang


def build_items(names: list[str], entries: list[dict]) -> tuple[list[dict], list[str]]:
    """Đoạn đã phân loại → (mục đính kèm, cảnh báo). Tách khỏi I/O để test, dùng chung hai chế độ.

    ``entries``: [{fileIndex, pages (0-based, None = cả tệp), docType, documentName, text, contains?}] theo thứ tự tệp,
    trang (``contains`` = các loại giấy trong tệp gộp). Đoạn cùng dòng bảng gộp thành MỘT tệp: toàn tệp →
    ``sourceFileIndexes``, có đoạn cắt trang → ``sourceSegments``. Tệp gộp vào CẢ ba dòng; có trang hộ chiếu thì thêm
    dòng "Giấy tờ khác" hộ chiếu. Chỉ cảnh báo khi hồ sơ THIẾU giấy / có giấy lạ.
    """
    portraits = [e for e in entries if e.get("docType") == PORTRAIT]
    entries = [e for e in entries if e.get("docType") not in (BLANK, PORTRAIT)]
    parts_of_file: dict[int, int] = {}
    for e in entries:
        parts_of_file[e["fileIndex"]] = parts_of_file.get(e["fileIndex"], 0) + 1

    def pages_of(entry: dict):
        return None if entry["pages"] is None or parts_of_file[entry["fileIndex"]] == 1 else entry["pages"]

    has_form = any(e["docType"] in (TO_KHAI, GOP) for e in entries)
    attachments: list[dict] = []
    warnings: list[str] = [
        f"Ảnh chân dung '{names[e['fileIndex']]}' không đính vào Thành phần hồ sơ — đã gắn vào ô Ảnh chân dung đầu "
        "trang kê khai (đổi sang .jpg), kiểm tra đúng ảnh 4x6 nền trắng của người đề nghị." for e in portraits
    ]
    used: set[int] = set()
    for slot in SLOTS:
        order = ROW_ORDERS[slot["slotIndex"]]
        if slot["slotIndex"] == 1 and not has_form:
            order = (TO_KHAI, GOP)  # không có tờ khai: bìa đính ở "Giấy tờ khác", không đứng một mình dòng tờ khai
        parts = _ordered(entries, order)
        if not parts:
            continue
        first = parts[0]["fileIndex"]
        item = _slot_item(slot, first, names[first], parts[0]["docType"])
        if all(pages_of(p) is None for p in parts):
            files = list(dict.fromkeys(p["fileIndex"] for p in parts))
            if len(files) > 1:
                item["sourceFileIndexes"] = files
        else:
            item["sourceSegments"] = [{"fileIndex": p["fileIndex"], "pageIndexes": pages_of(p)} for p in parts]
        attachments.append(item)
        used.update(id(p) for p in parts)

    # "Giấy tờ khác": hộ chiếu (tệp riêng / đoạn trang / tệp gộp có trang hộ chiếu), căn cước, bìa lẻ, giấy lạ.
    has_passport = any(e["docType"] == HO_CHIEU for e in entries)
    seen_names: dict[str, int] = {}
    unknown: list[str] = []
    for e in entries:
        file_name = names[e["fileIndex"]]
        doc_type = e["docType"]
        if doc_type == GOP:
            if has_passport or HO_CHIEU not in (e.get("contains") or ()):
                continue
            name = _passport_name(e.get("text") or "")
        elif id(e) in used:
            continue
        elif doc_type == HO_CHIEU:
            name = _passport_name(e.get("text") or "")
        else:
            name = _clean_name(e.get("documentName")) if doc_type == OTHER else OTHER_NAMES.get(doc_type, "")
            if not name:
                name = _clean_name(Path(file_name).stem) or "Giấy tờ khác"
                unknown.append(file_name)
        count = seen_names[name.lower()] = seen_names.get(name.lower(), 0) + 1
        if count > 1:
            name = f"{name} ({count})"
        item = _other_item(e["fileIndex"], file_name, doc_type, name)
        pages = pages_of(e)
        if pages is not None:
            item["sourceSegments"] = [{"fileIndex": e["fileIndex"], "pageIndexes": pages}]
        attachments.append(item)

    if not has_form:
        warnings.append("Hồ sơ chưa có Tờ khai đề nghị cấp thẻ tạm trú (Mẫu NA8) — dòng Tờ khai để trống, cần tải bổ sung.")
    if not any(e["docType"] in (VAN_BAN, GOP) for e in entries):
        warnings.append("Hồ sơ chưa có Văn bản đề nghị cấp thẻ tạm trú (Mẫu NA6 / NA7) — dòng này bắt buộc, cần tải "
                        "bổ sung.")
    if not any(e["docType"] in (CHUNG_MINH, GOP) for e in entries):
        warnings.append("Hồ sơ chưa có giấy tờ chứng minh thuộc diện xem xét cấp thẻ tạm trú (giấy phép lao động …) — "
                        "dòng này bắt buộc, cần tải bổ sung.")
    if unknown:
        warnings.append(
            "Không xác định được loại giấy tờ của " + ", ".join(f"'{n}'" for n in dict.fromkeys(unknown))
            + " — đã đính vào \"Giấy tờ khác\", vui lòng kiểm tra."
        )
    return attachments, warnings


async def classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=900, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    result: dict[int, dict] = {}
    for item in parsed.get("documents", []) or []:
        try:
            result[int(item.get("index"))] = {
                "docType": canonical_type(item.get("docType") or item.get("type")),
                "documentName": _clean_name(item.get("documentName")),
            }
        except (TypeError, ValueError):
            continue
    return result


def classify_files(files: list[dict], texts: dict[str, str], llm: dict[int, dict]) -> list[dict]:
    """Mỗi tệp một đoạn (cả tệp): tệp gộp nhận theo tiêu đề từng trang; còn lại LLM, LLM other / thiếu → luật tiêu đề."""
    entries = []
    for index, file in enumerate(files):
        text = texts.get(file.get("name"), "")
        got = llm.get(index) or {}
        by_pages = file_type(text)
        doc_type = got.get("docType") or OTHER
        if by_pages == GOP:
            doc_type = GOP
        elif doc_type in (OTHER, BLANK, GOP):
            doc_type = by_pages or OTHER
        entry = {"fileIndex": index, "pages": None, "docType": doc_type,
                 "documentName": got.get("documentName") or _clean_name(Path(file.get("name") or "").stem),
                 "text": text}
        if doc_type == GOP:
            entry["contains"] = tuple(k for k in dict.fromkeys(page_types(text)) if k in SUBSTANTIVE)
        entries.append(entry)
    return entries


# ── Ảnh trang nhân thân hộ chiếu (ô tải ảnh ``filenamehc`` đầu trang kê khai, cạnh ô ảnh chân dung ``filename46``) ──
# Cổng chỉ nhận .jpg dưới 2 MB (comp ``bca-photo`` — extension gắn tệp vào input như ảnh chân dung). Lấy trang có dòng MRZ
# "P<…" (thiếu MRZ thì trang mang nhãn "Passport No."); tệp ảnh / PDF một ảnh thì lấy nguyên ảnh, PDF nhiều trang thì vẽ
# lại đúng trang đó. Bản chụp hộ chiếu trên khổ A4 gắn cả trang (không tự cắt).
PASSPORT_PAGE_FIELD = "filenamehc"
PASSPORT_PAGE_FILE_NAME = "trang_nhan_than_ho_chieu.jpg"
PASSPORT_PAGE_MAX_SIDE = 1600


def find_passport_page(files: list[dict], pages_by_index: dict[int, list[str]]) -> tuple[int, int] | None:
    """(chỉ số tệp, chỉ số trang 0-based) của trang nhân thân hộ chiếu, None khi không có. Trang phải là trang hộ chiếu
    theo luật tiêu đề (tờ khai NA8 / giấy phép lao động có chữ "Passport No." không tính); có MRZ ưu tiên hơn nhãn."""
    best: tuple[int, int, int] | None = None
    for index in range(len(files or [])):
        for number, page in enumerate(pages_by_index.get(index) or []):
            if rule_doc_type(page) != HO_CHIEU:
                continue
            haystack = fold(page)
            if _MRZ_RE.search(haystack.replace(" ", "")):
                rank = 0
            elif _PASSPORT_LABEL_RE.search(haystack[:_HEAD_CHARS]):
                rank = 1
            else:
                continue  # trang thị thực / dấu nhập cảnh
            if best is None or (rank, index, number) < best:
                best = (rank, index, number)
    return (best[1], best[2]) if best else None


def _page_image(file: dict, page_index: int) -> tuple[bytes | None, bool]:
    """(ảnh của trang, tệp có nhiều trang không). Ảnh / PDF một ảnh phủ kín trang (Auto Fill gói ảnh vào PDF lúc đính
    kèm) → ảnh gốc; PDF khác → vẽ lại trang ``page_index``."""
    import base64

    from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.process.mapper import _image_bytes

    data = _image_bytes(file)
    if data:
        return data, False
    data_url = str(file.get("dataUrl") or "")
    try:
        import fitz

        raw = base64.b64decode(data_url.split(",", 1)[1] if "," in data_url else data_url)
        with fitz.open(stream=raw, filetype="pdf") as doc:
            if not 0 <= page_index < doc.page_count:
                return None, False
            return doc[page_index].get_pixmap(dpi=150).tobytes("png"), doc.page_count > 1
    except Exception:  # noqa: BLE001 — tệp hỏng / không phải PDF
        return None, False


def passport_page_field(files: list[dict], pages_by_index: dict[int, list[str]]) -> tuple[dict | None, str | None]:
    """(ô ``filenamehc`` comp ``bca-photo`` mang ảnh JPEG trang nhân thân hộ chiếu, câu báo). Không có → (None, None)."""
    import base64

    from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.process.mapper import portrait_jpeg

    found = find_passport_page(files, pages_by_index)
    if found is None:
        return None, None
    index, page_index = found
    source_name = str(files[index].get("name") or f"file-{index + 1}")
    data, multi_page = _page_image(files[index], page_index)
    try:
        jpeg = portrait_jpeg(data or b"", max_side=PASSPORT_PAGE_MAX_SIDE)
    except Exception:  # noqa: BLE001
        return None, None
    field = {
        "name": PASSPORT_PAGE_FIELD,
        "comp": "bca-photo",
        "value": {"name": PASSPORT_PAGE_FILE_NAME, "type": "image/jpeg",
                  "dataUrl": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")},
        "sourceFileName": source_name,
    }
    where = f"trang {page_index + 1} của '{source_name}'" if multi_page else f"'{source_name}'"
    note = (f"Đã gắn {where} vào ô Trang nhân thân hộ chiếu đầu biểu mẫu (dạng .jpg) — kiểm tra đúng trang có ảnh và "
            "dòng mã MRZ của người đề nghị.")
    return field, note


def page_fields(raw_files: list[dict], pages_by_index: dict[int, list[str]]) -> list[dict]:
    """Ô tải ảnh đầu trang kê khai cho bước đính kèm (cùng khuôn hộ chiếu 1.001456): Auto Fill bấm "Đính kèm" mà không
    điền lại vẫn gắn được ảnh chân dung (``filename46``) + ảnh trang nhân thân hộ chiếu (``filenamehc``). Ảnh hỏng không
    được làm hỏng kế hoạch đính kèm → bỏ ô đó."""
    from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.process.mapper import portrait_field

    texts = {i: "\n".join(pages) for i, pages in pages_by_index.items()}
    out: list[dict] = []
    for build in (lambda: portrait_field(raw_files, texts)[0], lambda: passport_page_field(raw_files, pages_by_index)[0]):
        try:
            field = build()
        except Exception:  # noqa: BLE001
            field = None
        if field:
            out.append(field)
    return out


def mark_portrait(entries: list[dict], raw_files: list[dict], texts: dict[int, str]) -> list[dict]:
    """Tệp ảnh chân dung (luật chung với hộ chiếu 1.001456, ``find_portrait``) → loại PORTRAIT để không đính."""
    from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.process.mapper import find_portrait

    index = find_portrait(raw_files, texts)
    if index is None:
        return entries
    return [{**e, "docType": PORTRAIT} if e["fileIndex"] == index else e for e in entries]


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    names = [str(f.get("name") or f"file-{i + 1}") for i, f in enumerate(raw_files)]
    errors: list[str] = []

    keep = [i for i, f in enumerate(raw_files) if _data_url_size(f.get("dataUrl", "")) <= MAX_FILE_BYTES]
    for i in range(len(raw_files)):
        if i not in keep:
            size = _data_url_size(raw_files[i].get("dataUrl", ""))
            errors.append(
                f"File '{names[i]}' nặng {size / 1024 / 1024:.1f} MB, vượt giới hạn 6 MB của cổng — hãy tách nhỏ hoặc "
                "giảm độ phân giải (mỗi tệp dưới 6 MB) rồi đính kèm lại."
            )
    small = [raw_files[i] for i in keep]
    ocr_files = [f for f in small if f.get("type") in _OCR_TYPES]

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_results.extend(_extract_docx_text(f) for f in small if _is_docx(f))
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")
    texts = {item.get("name"): str(item.get("text") or "") for item in ocr_results}

    documents = [{"index": i, "name": names[i], "text": texts.get(names[i], "")}
                 for i in keep if texts.get(names[i], "").strip()]
    started = time.monotonic()
    llm: dict[int, dict] = {}
    if documents:
        try:
            llm = await classify_with_llm(documents)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    entries = mark_portrait([e for e in classify_files(raw_files, texts, llm) if e["fileIndex"] in keep], raw_files,
                            {i: texts.get(names[i], "") for i in range(len(names))})
    attachments, warnings = build_items(names, entries)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "pageFields": page_fields(raw_files, {i: ocr_pages(texts.get(names[i], "")) for i in keep}),
        "extracted": {
            "documents": names,
            "classified": [{"fileName": names[e["fileIndex"]], "docType": e["docType"]} for e in entries],
            "slots": SLOTS,
            "attachmentMode": "whole",
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "ocr_text": join_ocr_documents(ocr_results),
        "llm_output": {str(k): v for k, v in llm.items()},
        "errors": errors,
    }

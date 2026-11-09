"""Đính kèm cho [Lai Châu] Cấp lại Giấy chứng nhận do bị mất (mã 1.115557).

Bước 3 cổng dichvucong.laichau.gov.vn là BẢNG 3 DÒNG cố định, mỗi dòng có checkbox ở cột "#" + ô "Số bản" (cổng để
sẵn 1) + một ``input[type=file]``; dưới bảng là "Biểu mẫu giấy tờ" (e-form, không dùng), "Về việc" (cổng điền sẵn "Cấp
lại Giấy chứng nhận do bị mất", giữ nguyên), "Ghi chú" và khối "Giấy tờ khác". Cùng khuôn bảng với
``chuyen_muc_dich_su_dung_dat_mien_nui_lai_chau``.

Định tuyến chốt theo ảnh ánh xạ của bộ hồ sơ mẫu — hồ sơ là MỘT file scan chung 12 trang (Mẫu 16, Bảng 16a, CCCD của
từng người đồng sử dụng, bản sao GCN, Sổ địa chính, Mẫu 03a, Mẫu 09) nộp HAI bản giống hệt, mỗi bản đính NGUYÊN, không
tách trang:
  - dòng 1 "Mẫu số 16. Đơn đăng ký biến động..." ← bản thứ nhất;
  - dòng 2 "Giấy chứng nhận đã cấp (bản gốc)" ← bản thứ hai (GCN đã mất nên nộp bản sao + trang Sổ địa chính nằm trong
    file chung);
  - dòng 3 "Mảnh trích đo..." chỉ khi có mảnh trích đo (người dân cần đo lại) — hồ sơ mẫu không có nên không tích;
  - "Giấy tờ khác" để trống khi mọi giấy đã nằm trong file chung; "Ghi chú" đề xuất câu liệt kê nội dung file chung
    (trả trong cảnh báo — extension chưa có nhánh điền ô Ghi chú của cổng Lai Châu).

Cách làm: OCR đủ trang (bước điền đã OCR đúng các tệp này → trúng cache), tách theo dòng "Trang i/N" của OCR rồi nhận loại
TỪNG TRANG theo tiêu đề; trang không có tiêu đề nối theo trang trước. Một file chứa nhiều loại giấy thì mang mọi dòng
của các loại đó. Các tệp TRÙNG NỘI DUNG gộp một nhóm: bản thứ i nhận dòng thứ i của nhóm (hai bản file chung → dòng 1 và
dòng 2 như ảnh ánh xạ; chỉ một bản → đính cả hai dòng), bản thừa bỏ qua. Bảng 16a / Sổ địa chính đứng riêng chỉ lên
dòng 1 / dòng 2 khi dòng đó chưa có tệp nào khác, không thì vào "Giấy tờ khác". LLM chỉ gọi cho tệp mà luật không nhận
ra.

Cổng chặn 6 MB/tệp mà file scan chung 12 trang của hồ sơ mẫu nặng ~8,5 MB → tệp vượt được vẽ lại thành JPEG theo thang
nén dùng chung với ``cai_chinh_dvc_moi`` cho tới khi lọt ``_SHRINK_TARGET_BYTES``, trả ở ``replaceFiles`` để extension
đính bản nén thay bản gốc (OCR vẫn đọc bản gốc). Nén hết thang vẫn vượt thì loại tệp kèm cảnh báo tách nhỏ.
"""

import asyncio
import base64
import re
import time
from pathlib import Path
from typing import Any

from app.config import settings
from app.pipelines._shared import fold, normalize_document_name
from app.pipelines._shared.compact_agent.runner import _extract_docx_text, _is_docx
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.cai_chinh_dvc_moi.attach.dinh_kem_khong_tach.planner import shrink_file
from app.pipelines.cap_lai_giay_chung_nhan_do_bi_mat_lai_chau.process.runner import ocr_unique
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_MAX_FILE_BYTES = 6 * 1024 * 1024
# Đích nén: dưới 6 MB của cổng, chừa biên cho cả cách tính 6.000.000 lẫn 6 MiB.
_SHRINK_TARGET_BYTES = 5_800_000
# Tiêu đề nằm ở đầu trang; thân trang Mẫu 16 nhắc "Bảng 16a", Mẫu 09/03a nhắc Giấy chứng nhận → một số dấu chỉ soi đầu.
_PAGE_HEAD_CHARS = 300
# Dòng ngăn trang của OCR Tiếng Nói: "───── Trang 3/12 ─────".
_PAGE_HEADER_RE = re.compile(r"[─━-]{3,}\s*Trang\s+\d+\s*/\s*\d+\s*[─━-]{3,}", re.IGNORECASE)

_DON = "don_dang_ky_bien_dong"
_BANG_16A = "bang_16a"
_GCN = "giay_chung_nhan"
_SO_DIA_CHINH = "so_dia_chinh"
_TRICH_DO = "manh_trich_do"
_MAU_03A = "mau_03a"
_MAU_09 = "mau_09"
_UY_QUYEN = "van_ban_uy_quyen"
_IDENTITY = "identity"
_OTHER = "other"

# slotName theo cột "Tên giấy tờ" trên cổng (ảnh ánh xạ); slotKeywords dạng đã fold (khớp foldChoiceText của
# extension), mỗi cụm chỉ thuộc một dòng.
SLOTS: list[dict[str, Any]] = [
    {
        "slotKey": "clgcn_mat_lc_row01",
        "slotIndex": 0,
        "slotName": "Mẫu số 16. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Bản chính)",
        "slotKeywords": ["don dang ky bien dong dat dai"],
    },
    {
        "slotKey": "clgcn_mat_lc_row02",
        "slotIndex": 1,
        "slotName": "Giấy chứng nhận đã cấp (bản gốc) (Bản chính)",
        "slotKeywords": ["giay chung nhan da cap"],
    },
    {
        "slotKey": "clgcn_mat_lc_row03",
        "slotIndex": 2,
        "slotName": "Mảnh trích đo bản đồ địa chính thửa đất đối với trường hợp người sử dụng đất có nhu cầu đo đạc để "
        "xác định lại kích thước các cạnh, diện tích của thửa đất (Bản chính)",
        "slotKeywords": ["manh trich do ban do dia chinh"],
    },
]
_SLOT_BY_INDEX = {slot["slotIndex"]: slot for slot in SLOTS}

# Loại giấy chiếm dòng chắc chắn; loại "phụ" chỉ lên dòng khi dòng đó trống (tránh hai tệp chồng một ô 1 tệp).
_PRIMARY_ROW = {_DON: 0, _GCN: 1, _TRICH_DO: 2}
_SECONDARY_ROW = {_BANG_16A: 0, _SO_DIA_CHINH: 1}
_ROW_DOCUMENT = {
    0: "Đơn đăng ký biến động đất đai (Mẫu số 16)",
    1: "Giấy chứng nhận đã cấp",
    2: "Mảnh trích đo bản đồ địa chính thửa đất",
}
_OTHER_NAMES = {
    _BANG_16A: "Bảng 16a - Danh sách người sử dụng đất",
    _SO_DIA_CHINH: "Trang sổ địa chính",
    _MAU_03A: "Phiếu yêu cầu xóa đăng ký biện pháp bảo đảm (Mẫu số 03a)",
    _MAU_09: "Đơn xin xác nhận lại thời hạn sử dụng đất nông nghiệp (Mẫu số 09)",
    _UY_QUYEN: "Văn bản ủy quyền",
}
# Tên ngắn từng loại để ghép câu Ghi chú đề xuất.
_KIND_LABELS = {
    _DON: "Mẫu số 16",
    _BANG_16A: "Bảng 16a",
    _IDENTITY: "CCCD",
    _GCN: "bản sao Giấy chứng nhận",
    _SO_DIA_CHINH: "Sổ địa chính",
    _TRICH_DO: "mảnh trích đo",
    _MAU_03A: "Mẫu số 03a",
    _MAU_09: "Mẫu số 09",
    _UY_QUYEN: "văn bản ủy quyền",
}
_ALLOWED = set(_KIND_LABELS) | {_OTHER}

_GCN_MARKERS = (
    "noi dung thay doi va co so phap ly", "nhung thay doi sau khi cap giay chung nhan", "so vao so cap gcn",
    "so do thua dat", "quyen so huu nha o va tai san khac gan lien voi dat",
)
_SO_DIA_CHINH_MARKERS = (
    "nhung thay doi trong qua trinh su dung dat", "tiep theo trang so", "chuyen tiep trang so",
)
_TRICH_DO_MARKERS = (
    "manh trich do", "trich do ban do dia chinh", "trich luc ban do dia chinh", "phieu do dac chinh ly",
)
_IDENTITY_MARKERS = ("can cuoc", "chung minh nhan dan", "identity card", "passport")

_IDENTITY_NAME_RE = re.compile(
    r"(?:full\s*name|h[ọo],?\s*ch[ữu]\s*đ[ệe]m\s*v[àa]\s*t[êe]n(?:\s*khai\s*sinh)?|h[ọo]\s*v[àa]\s*t[êe]n)"
    r"[^\n:]*:?[ \t]*([^\n]*)(?:\n[ \t]*([^\n]*))?",
    re.IGNORECASE,
)


def split_pages(text: str) -> list[str]:
    """Tách chữ OCR theo dòng "Trang i/N"; không có dòng ngăn (ảnh, 1 trang) → cả chữ là một trang."""
    text = str(text or "")
    marks = list(_PAGE_HEADER_RE.finditer(text))
    if not marks:
        return [text] if text.strip() else []
    return [text[mark.end():(marks[i + 1].start() if i + 1 < len(marks) else len(text))]
            for i, mark in enumerate(marks)]


def page_kind(text: str) -> str:
    """Loại giấy của MỘT trang theo tiêu đề; "" = trang không có tiêu đề (trang 2 của một mẫu)."""
    haystack = fold(text)
    if not haystack.strip():
        return ""
    head = haystack[:_PAGE_HEAD_CHARS]
    # Mẫu 03a / Mẫu 09 nhắc số phát hành Giấy chứng nhận, Mẫu 16 nhắc Bảng 16a → xét các mẫu đơn trước.
    if "xoa dang ky bien phap bao dam" in haystack or "mau so 03a" in head:
        return _MAU_03A
    if "xac nhan lai thoi han su dung dat" in haystack:
        return _MAU_09
    if "don dang ky bien dong dat dai" in haystack or "huong dan ke khai don" in haystack or "mau so 16" in head:
        return _DON
    if "bang 16a" in head or "danh sach nhung nguoi su dung dat" in head:
        return _BANG_16A
    # Sổ địa chính có cột "Số vào sổ cấp GCN" → xét trước Giấy chứng nhận.
    if any(marker in haystack for marker in _SO_DIA_CHINH_MARKERS):
        return _SO_DIA_CHINH
    if any(marker in haystack for marker in _GCN_MARKERS) or ("giay chung nhan" in head and "quyen su dung dat" in head):
        return _GCN
    if any(marker in head for marker in _TRICH_DO_MARKERS):
        return _TRICH_DO
    if "giay uy quyen" in head or "hop dong uy quyen" in head:
        return _UY_QUYEN
    if any(marker in haystack for marker in _IDENTITY_MARKERS):
        return _IDENTITY
    return ""


def page_kinds(text: str) -> list[str]:
    """Loại từng trang của file; trang không tiêu đề nối theo trang trước ("" nếu trước đó chưa nhận ra gì)."""
    kinds: list[str] = []
    previous = ""
    for page in split_pages(text):
        kind = page_kind(page) or previous
        kinds.append(kind)
        previous = kind
    return kinds


def _unique(items) -> list[str]:
    return [item for index, item in enumerate(items) if item and item not in items[:index]]


def _normalize_doc_type(value: Any) -> str:
    folded = fold(str(value or ""))
    for doc_type in _ALLOWED:
        if folded == fold(doc_type):
            return doc_type
    return _OTHER


def _identity_holder_name(text: str) -> str | None:
    """Họ tên chủ thẻ đọc từ OCR CCCD ("Họ và tên / Full name: ...") → "Nguyễn Văn A"."""
    for match in _IDENTITY_NAME_RE.finditer(text or ""):
        for candidate in match.groups():
            name = " ".join(re.sub(r"[^\w\s]", " ", candidate or "").split())
            if name and not re.search(r"\d", name) and 2 <= len(name.split()) <= 6 and "name" not in name.lower():
                return name.title()
    return None


def _data_url_size(data_url: str) -> int:
    payload = str(data_url or "").partition(",")[2]
    if not payload:
        return 0
    payload = re.sub(r"\s+", "", payload)
    padding = len(payload) - len(payload.rstrip("="))
    return max(0, (len(payload) * 3) // 4 - padding)


def _shrink(raw: bytes) -> tuple[bytes, str]:
    return shrink_file(raw, _SHRINK_TARGET_BYTES)


async def shrink_oversized(raw_files: list[dict], errors: list[str]) -> dict[str, dict]:
    """Bản nén cho tệp vượt 6 MB, khoá = fileIndex (contract ``replaceFiles``). Tệp trùng nội dung chỉ nén một lần."""
    done: dict[str, tuple[bytes, str] | None] = {}
    replaced: dict[str, dict] = {}
    for index, file in enumerate(raw_files):
        data_url = str(file.get("dataUrl") or "")
        if _data_url_size(data_url) <= _MAX_FILE_BYTES:
            continue
        if data_url not in done:
            try:
                raw = base64.b64decode(data_url.split(",", 1)[1] if "," in data_url else data_url)
                done[data_url] = await asyncio.to_thread(_shrink, raw)
            except Exception as exc:  # noqa: BLE001 — nén hỏng thì coi như không nén được, tệp bị loại kèm cảnh báo
                errors.append(f"Không nén được {file.get('name')}: {exc}")
                done[data_url] = None
        result = done[data_url]
        if not result:
            continue
        out, level = result
        stem = Path(str(file.get("name") or "")).stem or "tai-lieu"
        replaced[str(index)] = {
            "name": f"{stem}.pdf",
            "type": "application/pdf",
            "dataUrl": "data:application/pdf;base64," + base64.b64encode(out).decode(),
            "originalBytes": _data_url_size(data_url),
            "bytes": len(out),
            "level": level,
        }
    return replaced


def _page_ranges(kinds: list[str]) -> str:
    """["don","don","bang_16a"] → "Mẫu số 16 (tr.1-2), Bảng 16a (tr.3)"."""
    parts: list[str] = []
    start = 0
    for index in range(1, len(kinds) + 1):
        if index < len(kinds) and kinds[index] == kinds[start]:
            continue
        label = _KIND_LABELS.get(kinds[start])
        if label:
            pages = f"tr.{start + 1}" if index - 1 == start else f"tr.{start + 1}-{index}"
            parts.append(f"{label} ({pages})")
        start = index
    return ", ".join(parts)


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=700, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    result: dict[int, str] = {}
    for item in parsed.get("documents", []) or []:
        try:
            result[int(item.get("index"))] = _normalize_doc_type(item.get("docType") or item.get("type"))
        except (TypeError, ValueError):
            continue
    return result


def _slot_item(file_index: int, file_name: str, doc_type: str, slot_index: int, document_name: str) -> dict:
    slot = _SLOT_BY_INDEX[slot_index]
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
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


def _group_files(files: list[dict], text_by_name: dict[str, str], warnings: list[str],
                 classified: list[dict], replaced: dict[str, dict]) -> list[dict]:
    """Gộp tệp TRÙNG NỘI DUNG (cùng dataUrl hoặc cùng chữ OCR) theo thứ tự xuất hiện; tệp quá 6 MB (kể cả sau khi nén)
    bị loại."""
    groups: list[dict] = []
    by_key: dict[str, dict] = {}
    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        shrunk = replaced.get(str(index))
        size = shrunk["bytes"] if shrunk else _data_url_size(file.get("dataUrl", ""))
        if size > _MAX_FILE_BYTES:
            what = "nén hết mức vẫn" if shrunk else "nặng"
            warnings.append(
                f"File '{file_name}' {what} {size / 1024 / 1024:.1f} MB, vượt giới hạn 6 MB của cổng — "
                "hãy tách nhỏ hoặc giảm độ phân giải (mỗi tệp dưới 6 MB) rồi đính kèm lại."
            )
            classified.append(
                {"fileName": file_name, "docType": _OTHER, "source": "validation", "skipped": True,
                 "reason": "file_too_large"}
            )
            continue
        text = text_by_name.get(file_name, "")
        keys = [f"data:{file.get('dataUrl')}" if file.get("dataUrl") else ""]
        normalized = " ".join(text.split())
        if len(normalized) > 50:
            keys.append(f"text:{normalized}")
        keys = [key for key in keys if key]
        group = next((by_key[key] for key in keys if key in by_key), None)
        if group is None:
            group = {"members": [], "text": text}
            groups.append(group)
        group["members"].append((index, file_name))
        for key in keys:
            by_key.setdefault(key, group)
    return groups


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict] | None = None,
    llm_types: dict[int, str] | None = None,
    replaced: dict[str, dict] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    """``replaced`` = bản nén theo fileIndex (``replaceFiles``): tệp gốc vượt 6 MB mà bản nén lọt thì vẫn đính."""
    llm_types = llm_types or {}
    text_by_name = {item.get("name"): str(item.get("text") or "") for item in ocr_results or []}
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    groups = _group_files(files, text_by_name, warnings, classified, replaced or {})
    for group in groups:
        kinds = page_kinds(group["text"])
        found = _unique(kinds)
        source = "rule"
        if not found:
            llm_type = llm_types.get(group["members"][0][0], "")
            found = [llm_type] if llm_type in _KIND_LABELS else []
            source = "llm" if found else "unknown"
        group.update(kinds=kinds, found=found, source=source,
                     primary=sorted({_PRIMARY_ROW[kind] for kind in found if kind in _PRIMARY_ROW}))

    claimed = {row for group in groups for row in group["primary"]}
    notes: list[str] = []
    for group in groups:
        found, members = group["found"], group["members"]
        rows = list(group["primary"])
        for kind in found:
            row = _SECONDARY_ROW.get(kind)
            if row is not None and row not in rows and row not in claimed:
                rows.append(row)
                claimed.add(row)
        rows.sort()
        main_kind = next((kind for kind in found if kind in _PRIMARY_ROW or kind in _SECONDARY_ROW), None)
        compound = len(found) > 1

        if rows:
            for position, row in enumerate(rows):
                index, file_name = members[min(position, len(members) - 1)]
                document_name = _ROW_DOCUMENT[row]
                if compound:
                    document_name += " (file scan chung: " + ", ".join(_KIND_LABELS[kind] for kind in found) + ")"
                kind_for_row = next(
                    (kind for kind in found if _PRIMARY_ROW.get(kind, _SECONDARY_ROW.get(kind)) == row), main_kind
                )
                attachments.append(_slot_item(index, file_name, kind_for_row, row, document_name))
            for position, (index, file_name) in enumerate(members):
                own_rows = [row for slot, row in enumerate(rows) if min(slot, len(members) - 1) == position]
                entry = {"fileName": file_name, "docType": main_kind, "source": group["source"], "kinds": found,
                         "slotIndex": own_rows}
                if not own_rows:
                    entry.update(skipped=True, reason="duplicate")
                classified.append(entry)
            if compound and len(group["kinds"]) > 1:
                note = f"File {members[0][1]} ({len(group['kinds'])} trang) gồm: {_page_ranges(group['kinds'])}."
                if len(members) > 1 and len(rows) > 1:
                    note += f" File {members[1][1]} trùng nội dung, nộp cho mục {_ROW_DOCUMENT[rows[1]]}."
                notes.append(note)
        else:
            index, file_name = members[0]
            if found:
                kind = found[0]
                if kind == _IDENTITY:
                    holder = _identity_holder_name(group["text"])
                    name = f"Căn cước công dân - {holder}" if holder else "Căn cước công dân"
                else:
                    name = _OTHER_NAMES[kind]
            else:
                kind = _OTHER
                # Không rõ loại: vẫn đính vào "Giấy tờ khác" với tên tệp gốc, cảnh báo để cán bộ kiểm tra.
                name = normalize_document_name(Path(file_name).stem, "Giấy tờ khác")
                warnings.append(
                    f"Không xác định được loại giấy tờ của file '{file_name}' — đã đính vào \"Giấy tờ khác\"; "
                    "vui lòng kiểm tra và chuyển sang đúng dòng nếu cần."
                )
            attachments.append(_other_item(index, file_name, kind, name))
            for position, (member_index, member_name) in enumerate(members):
                entry = {"fileName": member_name, "docType": kind, "source": group["source"], "kinds": found}
                if position:
                    entry.update(skipped=True, reason="duplicate")
                classified.append(entry)

        for index, file_name in members[max(len(rows), 1):]:
            warnings.append(f"File '{file_name}' trùng nội dung với '{members[0][1]}' — không đính thêm lần nữa.")

    if 0 not in claimed and groups:
        warnings.append(
            "Chưa nhận ra Đơn đăng ký biến động đất đai (Mẫu số 16) — dòng 1 bảng thành phần hồ sơ để trống, "
            "vui lòng bổ sung hoặc kiểm tra lại tệp."
        )
    if notes:
        warnings.append("Ghi chú đề xuất (ô \"Ghi chú\" bước đính kèm): " + " ".join(notes))
    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    errors: list[str] = []
    # Nén tệp vượt 6 MB song song với OCR; OCR đọc bản gốc.
    shrink_task = asyncio.create_task(shrink_oversized(raw_files, errors))

    ocr_files = [item for item in raw_files if item.get("type") in _OCR_TYPES]

    started = time.monotonic()
    # Đủ trang (cần biết file chung có trang GCN / trích đo); bước điền đã OCR đúng các tệp này nên thường trúng cache.
    ocr_results = await ocr_unique(ocr_files) if ocr_files else []
    # OCR không đọc DOCX → lấy chữ thẳng từ XML (Đơn soạn bằng Word).
    ocr_results.extend(_extract_docx_text(item) for item in raw_files if _is_docx(item))
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    # LLM chỉ cho tệp có chữ mà luật theo tiêu đề trang không nhận ra.
    by_name = {item.get("name"): item for item in ocr_results}
    llm_documents = []
    for index, file in enumerate(raw_files):
        text = str(by_name.get(file.get("name"), {}).get("text") or "")
        if text.strip() and not _unique(page_kinds(text)):
            llm_documents.append({"index": index, "name": file["name"], "text": text})

    started = time.monotonic()
    llm_types: dict[int, str] = {}
    if llm_documents:
        try:
            llm_types = await _classify_with_llm(llm_documents)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    replace_files = await shrink_task
    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types, replace_files)
    errors.extend(warnings)

    return {
        "attachments": attachments,
        "replaceFiles": replace_files or None,
        "extracted": {
            "documents": [item["name"] for item in raw_files],
            "ocrDocuments": [item.get("name") for item in ocr_results if item.get("text")],
            "llmDocuments": [item["name"] for item in llm_documents],
            "classified": classified,
            "slots": SLOTS,
            "shrunk": [
                {"fileIndex": int(index), "name": item["name"], "originalBytes": item["originalBytes"],
                 "bytes": item["bytes"], "level": item["level"]}
                for index, item in (replace_files or {}).items()
            ],
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "ocr_text": join_ocr_documents(ocr_results),
        "llm_output": {str(index): value for index, value in llm_types.items()},
        "errors": errors,
    }

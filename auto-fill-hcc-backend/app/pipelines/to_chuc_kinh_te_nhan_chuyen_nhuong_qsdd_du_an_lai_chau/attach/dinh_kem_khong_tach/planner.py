"""Đính kèm 1.115591 (Lai Châu) — chế độ ĐÍNH NGUYÊN TỆP (tắt "Tách giấy tờ"; chế độ tách gọi lại planner này trên các
PDF con, xem ../dinh_kem_tach/planner.py).

Bước 3 "Thành phần hồ sơ" cổng dichvucong.laichau.gov.vn (ảnh ánh xạ người dùng gửi 25/11/2026): BẢNG 2 DÒNG cố định,
mỗi dòng checkbox ở cột "#" + "Số bản" + "Chọn tệp tin", dưới bảng là khối "Giấy tờ khác" (``HoSoOnline_giayToKhac[]``):
   1 Trích lục vị trí khu đất mà nhà đầu tư đề xuất thực hiện dự án (Bản chính)        ← mảnh trích đo địa chính
   2 Mẫu số 30. Văn bản đề nghị chấp thuận cho tổ chức kinh tế nhận chuyển nhượng, …  ← văn bản đề nghị của công ty
Mỗi tệp khớp đúng một dòng, đính NGUYÊN, không đính chung. Căn cước người đại diện không phải thành phần hồ sơ → "Giấy
tờ khác" như các thủ tục Lai Châu khác; giấy lạ cũng vào "Giấy tờ khác" giữ tên tệp + cảnh báo, không bỏ tệp nào.
Không dùng "Lấy giấy tờ từ KDL", "Biểu mẫu giấy tờ" (e-form), "Ký số" (ảnh ánh xạ ô 1, 4, 5).

Phân loại KHÔNG gọi LLM: tiêu đề hai giấy rất rõ → cụm dấu hiệu xuất hiện SỚM NHẤT ở phần đầu chữ OCR thắng (tiêu đề
mảnh trích đo cũng có cụm "chấp thuận cho nhận chuyển nhượng quyền sử dụng đất" nên dấu hiệu văn bản đề nghị chỉ dùng
cụm riêng của nó: "Mẫu số 30", "đề nghị chấp thuận", "nhận góp vốn bằng quyền sử dụng đất"). Bản vẽ OCR méo không ra
tiêu đề → còn cụm "trích đo"/"tọa độ"/"tỷ lệ 1:" ở bất kỳ đâu thì vẫn là trích lục. OCR rỗng → đoán theo tên tệp.

Engine ``fixed-slot`` của extension: khớp dòng theo ``slotKeywords`` (dự phòng ``slotIndex`` 0-based), tích checkbox dòng
(``tickRow``) rồi bơm tệp vào input của dòng; mục ``target="new"`` đi khối "Giấy tờ khác". Cổng chặn tệp quá 6 MB.
"""

import re
import time
from pathlib import Path
from typing import Any

from app.pipelines._shared import fold, normalize_document_name
from app.pipelines._shared.compact_agent.runner import _extract_docx_text, _is_docx
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.giao_dat_cho_thue_dat_lai_chau.attach.planner import (
    _data_url_size,
    _identity_holder_name,
    _other_item,
)
from app.process.schemas import FileItem
from app.services import ocr

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_MAX_FILE_BYTES = 6 * 1024 * 1024
_NEAR_LIMIT_BYTES = 6_000_000
_HEAD_CHARS = 1500  # số ký tự (đã fold) đầu tệp dùng để dò tiêu đề

_T_TRICH_LUC, _T_VAN_BAN, _T_CCCD, _T_OTHER = "trich_luc_vi_tri", "van_ban_de_nghi", "identity", "other"

# slotName theo cột "Tên giấy tờ" trên cổng (ảnh ánh xạ); slotKeywords dạng đã fold, mỗi cụm chỉ thuộc một dòng.
SLOTS: list[dict[str, Any]] = [
    {
        "slotKey": "tckt_lc_row01", "slotIndex": 0,
        "slotName": "Trích lục vị trí khu đất mà nhà đầu tư đề xuất thực hiện dự án (Bản chính)",
        "slotKeywords": ["trich luc vi tri khu dat"],
    },
    {
        "slotKey": "tckt_lc_row02", "slotIndex": 1,
        "slotName": "Mẫu số 30. Văn bản đề nghị chấp thuận cho tổ chức kinh tế nhận chuyển nhượng, thuê quyền sử dụng "
        "đất, nhận góp vốn bằng quyền sử dụng đất để thực hiện dự án đầu tư (Bản chính)",
        "slotKeywords": ["mau so 30", "van ban de nghi chap thuan"],
    },
]
_SLOT_BY_TYPE = {_T_TRICH_LUC: SLOTS[0], _T_VAN_BAN: SLOTS[1]}
_TEN = {
    _T_TRICH_LUC: "Trích lục vị trí khu đất (mảnh trích đo địa chính)",
    _T_VAN_BAN: "Văn bản đề nghị chấp thuận (Mẫu số 30)",
}
_BAT_BUOC = {
    _T_VAN_BAN: "Văn bản đề nghị chấp thuận (Mẫu số 30)",
    _T_TRICH_LUC: "Trích lục vị trí khu đất (mảnh trích đo)",
}

# Cụm dấu hiệu tiêu đề (đã fold, chỉ chữ + số) — loại có cụm xuất hiện SỚM NHẤT ở phần đầu tệp thắng.
_DAU_HIEU: dict[str, tuple[str, ...]] = {
    _T_VAN_BAN: ("mau so 30", "de nghi chap thuan", "nhan gop von bang quyen su dung dat",
                 "to chuc de nghi thuc hien du an"),
    _T_TRICH_LUC: ("manh trich do", "trich do dia chinh", "trich do ban do", "trich luc ban do", "trich luc vi tri",
                   "ban do dia chinh", "so do vi tri", "he toa do vn"),
    _T_CCCD: ("can cuoc", "citizen identity", "identity card", "personal identification", "idvnm",
              "chung minh nhan dan"),
}
# Bản vẽ OCR méo (không ra tiêu đề) vẫn còn các cụm này ở đâu đó.
_TRICH_LUC_BAT_KY = ("trich do", "toa do", "ty le 1 ")
# OCR rỗng → tên tệp (đã fold, chỉ chữ + số, liền nhau).
_TEN_TEP: tuple[tuple[str, tuple[str, ...]], ...] = (
    (_T_CCCD, ("cccd", "cancuoc", "cmnd")),
    (_T_TRICH_LUC, ("trichdo", "trichluc", "sodo", "bando", "manhtrich", "vitrikhudat")),
    (_T_VAN_BAN, ("mau30", "denghi", "congvan", "vanban")),
)


def _chu(text: str) -> str:
    """fold + bỏ mọi ký tự ngoài chữ/số (OCR hay chèn "#", "**", xuống dòng giữa tiêu đề)."""
    return re.sub(r"[^a-z0-9]+", " ", fold(text or "")).strip()


def phan_loai(text: str, file_name: str = "") -> tuple[str, str]:
    """(docType, nguồn: "ocr" | "filename" | "default")."""
    folded = _chu(text)
    if folded:
        head = folded[:_HEAD_CHARS]
        best, best_pos = None, len(head) + 1
        for doc_type, keys in _DAU_HIEU.items():
            for key in keys:
                pos = head.find(key)
                if 0 <= pos < best_pos:
                    best, best_pos = doc_type, pos
        if best:
            return best, "ocr"
        if any(key in f" {folded} " for key in _TRICH_LUC_BAT_KY):
            return _T_TRICH_LUC, "ocr"
        return _T_OTHER, "ocr"
    name = re.sub(r"[^a-z0-9]", "", fold(Path(file_name or "").stem))
    if name.startswith("cv"):  # công văn của doanh nghiệp: "Cv66..."
        return _T_VAN_BAN, "filename"
    for doc_type, keys in _TEN_TEP:
        if any(key in name for key in keys):
            return doc_type, "filename"
    return _T_OTHER, "default"


def _slot_item(file_index: int, file_name: str, doc_type: str) -> dict:
    slot = _SLOT_BY_TYPE[doc_type]
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": _TEN[doc_type],
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


def build_plan_items(
    files: list[dict],
    texts: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    texts = texts or {}
    slot_items: list[dict] = []
    other_items: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    seen: set[str] = set()

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        size = _data_url_size(file.get("dataUrl", ""))
        if size > _MAX_FILE_BYTES:
            warnings.append(
                f"File '{file_name}' nặng {size / 1024 / 1024:.1f} MB, vượt giới hạn 6 MB của cổng — "
                "hãy nén PDF (giảm độ phân giải ảnh quét) cho dưới 6 MB rồi đính kèm lại."
            )
            classified.append({"fileName": file_name, "docType": _T_OTHER, "source": "validation", "skipped": True,
                               "reason": "file_too_large"})
            continue
        if size > _NEAR_LIMIT_BYTES:
            size_text = f"{size:,}".replace(",", ".")
            warnings.append(
                f"File '{file_name}' nặng {size_text} byte, sát giới hạn 6 MB — nếu cổng báo quá dung lượng thì nén nhỏ "
                "rồi đính lại."
            )

        text = texts.get(index, "")
        doc_type, source = phan_loai(text, file_name)
        seen.add(doc_type)
        if doc_type in _SLOT_BY_TYPE:
            slot_items.append(_slot_item(index, file_name, doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "source": source,
                               "slotIndex": [_SLOT_BY_TYPE[doc_type]["slotIndex"]]})
            continue
        if doc_type == _T_CCCD:
            holder = _identity_holder_name(text)
            name = f"Căn cước người đại diện - {holder}" if holder else "Căn cước người đại diện"
            other_items.append(_other_item(index, file_name, _T_CCCD, name))
            classified.append({"fileName": file_name, "docType": _T_CCCD, "source": source})
            continue
        # Không rõ loại: vẫn đính vào "Giấy tờ khác" với tên tệp gốc, cảnh báo để cán bộ kiểm tra.
        name = normalize_document_name(Path(file_name).stem, "Giấy tờ khác")
        other_items.append(_other_item(index, file_name, _T_OTHER, name))
        warnings.append(
            f"Không xác định được loại giấy tờ của file '{file_name}' — đã đính vào \"Giấy tờ khác\"; "
            "vui lòng kiểm tra và chuyển sang đúng dòng nếu cần."
        )
        classified.append({"fileName": file_name, "docType": _T_OTHER, "source": source})

    slot_items.sort(key=lambda item: (item["slotIndex"], item["fileIndex"]))
    thieu = [ten for loai, ten in _BAT_BUOC.items() if loai not in seen]
    if (slot_items or other_items) and thieu:
        warnings.append(
            "Chưa nhận ra thành phần hồ sơ bắt buộc: " + "; ".join(thieu) + " — kiểm tra lại tệp đã tải lên."
        )
    if not slot_items and not other_items:
        warnings.append("Không có tài liệu nào để đính kèm.")
    return [*slot_items, *other_items], warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    errors: list[str] = []

    small = [item for item in raw_files if _data_url_size(item.get("dataUrl", "")) <= _MAX_FILE_BYTES]
    ocr_files = [item for item in small if item.get("type") in _OCR_TYPES]

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    # OCR không đọc DOCX → lấy chữ thẳng từ XML (văn bản đề nghị soạn bằng Word).
    ocr_results.extend(_extract_docx_text(item) for item in small if _is_docx(item))
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    by_name = {item.get("name"): item for item in ocr_results}
    texts = {
        index: str(by_name.get(file.get("name"), {}).get("text") or "")
        for index, file in enumerate(raw_files)
        if str(by_name.get(file.get("name"), {}).get("text") or "").strip()
    }
    attachments, warnings, classified = build_plan_items(raw_files, texts)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [item["name"] for item in raw_files],
            "ocrDocuments": [item.get("name") for item in ocr_results if item.get("text")],
            "classified": classified,
            "slots": SLOTS,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": 0, "total_latency_ms": ocr_ms},
        "ocr_text": join_ocr_documents(ocr_results),
        "errors": errors,
    }

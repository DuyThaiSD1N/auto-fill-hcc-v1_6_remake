"""Đính kèm 1.115683 (Lào Cai, cổng iGate mới) — chế độ ĐÍNH NGUYÊN TỆP (tắt "Tách giấy tờ"; chế độ tách gọi lại planner
này trên các PDF con, xem ../dinh_kem_tach/planner.py).

Bước 2 "Thành phần hồ sơ hệ thống" (ảnh hướng dẫn đính kèm người dùng gửi 25/11/2026): bảng mat-table BA dòng, mỗi dòng
"1 Bản chính", mat-checkbox + "Scan tệp tin"/"Chọn tệp tin", có "Chọn/Bỏ chọn tất cả" và nút "Thêm giấy tờ", không có
dòng "giấy tờ khác":
   1 Văn bản đề nghị gia hạn phương án sử dụng đất kết hợp đa mục đích theo Mẫu số 30 (QĐ 47/2026/QĐ-UBND)
   2 Phương án sử dụng đất kết hợp
   3 Giấy chứng nhận đã cấp hoặc một trong các loại giấy tờ về quyền sử dụng đất (nếu có)
Đơn → dòng 1, Phương án (kể cả sơ đồ + bảng tọa độ nằm trong tệp phương án) → dòng 2, GCN → dòng 3. Hướng dẫn ghi
KHÔNG dùng "Thêm giấy tờ" và CCCD không phải thành phần hồ sơ → CCCD / giấy lạ đính chung dòng Đơn (vẫn là tệp riêng)
+ cảnh báo để cán bộ tự gỡ; không bỏ tệp nào.

Phân loại KHÔNG gọi LLM: tiêu đề ba giấy rất rõ → so cụm dấu hiệu xuất hiện SỚM NHẤT ở phần đầu chữ OCR (Đơn có cụm
"phương án sử dụng đất kết hợp" trong tiêu đề, Phương án có "Văn bản đề nghị gia hạn" trong chú thích ngay dưới tiêu đề
→ chỉ cụm đứng trước mới tính). Trang nối tiếp của Phương án bị tách riêng (sơ đồ, bảng tọa độ) không có tiêu đề → còn
cụm "sử dụng đất kết hợp" thì vẫn là Phương án. OCR rỗng → đoán theo tên tệp.

Engine FE "attp-row" + untickUnplannedRows dùng chung với cho_thue_dat_thue_rung_igate_lao_cai.
"""

import re
import time
from pathlib import Path

from app.pipelines._shared import fold
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.cho_thue_dat_thue_rung_igate_lao_cai.attach import planner as _igate
from app.process.schemas import FileItem
from app.services import ocr

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_GIOI_HAN_BYTE = 6 * 1024 * 1024
_DAU_TRANG = 1500  # số ký tự (đã fold) đầu tệp dùng để dò tiêu đề

_T_DON, _T_PA, _T_GCN, _T_CCCD, _T_OTHER = "don_mau_30", "phuong_an", "gcn", "cccd", "other"
_TEN = {
    _T_DON: "Văn bản đề nghị gia hạn phương án sử dụng đất kết hợp",
    _T_PA: "Phương án sử dụng đất kết hợp",
    _T_GCN: "Giấy chứng nhận quyền sử dụng đất",
    _T_CCCD: "Căn cước",
    _T_OTHER: "Giấy tờ kèm theo",
}

# Bảng 3 dòng NGUYÊN VĂN (ảnh bước 2 người dùng gửi 25/11/2026).
_DEFAULT_ROWS = [
    "Văn bản đề nghị gia hạn phương án sử dụng đất kết hợp đa mục đích theo Mẫu số 30 ban hành kèm theo Quyết định số "
    "47/2026/QĐ-UBND",
    "Phương án sử dụng đất kết hợp",
    "Giấy chứng nhận đã cấp hoặc một trong các loại giấy tờ về quyền sử dụng đất theo quy định của pháp luật (nếu có)",
]
# docType → (từ khoá dò dòng, vị trí dòng mặc định 0-based). Tên dòng 1 cũng chứa "phương án sử dụng đất kết hợp":
# _igate._find lấy dòng NGẮN nhất trong các dòng khớp → vẫn ra dòng 2.
_ROW_KEYS: dict[str, tuple[list[str], int]] = {
    _T_DON: (["mau so 30", "de nghi gia han"], 0),
    _T_PA: (["phuong an su dung dat ket hop"], 1),
    _T_GCN: (["giay chung nhan da cap", "giay chung nhan"], 2),
}
_BAT_BUOC = {_T_DON: "Văn bản đề nghị gia hạn (Mẫu số 30)", _T_PA: "Phương án sử dụng đất kết hợp"}

# Cụm dấu hiệu tiêu đề (đã fold, chỉ chữ + số) — loại có cụm xuất hiện SỚM NHẤT ở phần đầu tệp thắng.
_DAU_HIEU: dict[str, tuple[str, ...]] = {
    _T_DON: ("mau so 30", "don de nghi gia han", "van ban de nghi gia han"),
    _T_PA: ("phuong an su dung dat ket hop",),
    _T_GCN: ("giay chung nhan quyen su dung dat", "giay chung nhan quyen so huu nha o",
             "thua dat nha o va tai san khac gan lien voi dat", "nhung thay doi sau khi cap giay chung nhan",
             "noi dung thay doi va co so phap ly"),
    _T_CCCD: ("can cuoc", "citizen identity", "identity card", "personal identification", "idvnm",
              "chung minh nhan dan"),
}
# OCR rỗng → tên tệp (đã fold, "_"/"-" thành dấu cách).
_TEN_TEP: tuple[tuple[str, tuple[str, ...]], ...] = (
    (_T_PA, ("phuong an", "phuongan")),
    (_T_DON, ("mau30", "mau 30", "don de nghi", "dondenghi", "gia han")),
    (_T_GCN, ("gcn", "giay chung nhan", "so do", "so hong")),
    (_T_CCCD, ("cccd", "can cuoc", "cmnd")),
)

Row = _igate.Row


def _chu(text: str) -> str:
    """fold + bỏ mọi ký tự ngoài chữ/số (OCR hay chèn "#", "**", xuống dòng giữa tiêu đề)."""
    return re.sub(r"[^a-z0-9]+", " ", fold(text or "")).strip()


def phan_loai(text: str, file_name: str = "") -> tuple[str, str]:
    """(docType, nguồn: "ocr" | "filename" | "default")."""
    folded = _chu(text)
    if folded:
        head = folded[:_DAU_TRANG]
        best, best_pos = None, len(head) + 1
        for doc_type, keys in _DAU_HIEU.items():
            for key in keys:
                pos = head.find(key)
                if 0 <= pos < best_pos:
                    best, best_pos = doc_type, pos
        if best:
            return best, "ocr"
        # Trang nối tiếp của Phương án bị tách riêng (sơ đồ, bảng tọa độ K1–K6) không có tiêu đề.
        if "su dung dat ket hop" in folded:
            return _T_PA, "ocr"
        return _T_OTHER, "ocr"
    name = _chu(Path(file_name or "").stem)
    for doc_type, keys in _TEN_TEP:
        if any(key in name for key in keys):
            return doc_type, "filename"
    return _T_OTHER, "default"


def _kich_thuoc(file: dict) -> int:
    """Kích thước thật, suy từ độ dài base64 của dataUrl (FileItem không mang size)."""
    payload = str(file.get("dataUrl") or "").partition(",")[2]
    return len(payload) * 3 // 4 - payload[-2:].count("=") if payload else 0


def _default_rows() -> list[Row]:
    return [(i + 1, name, fold(name)) for i, name in enumerate(_DEFAULT_ROWS)]


def _row(doc_type: str, rows: list[Row]) -> Row | None:
    keys, position = _ROW_KEYS[doc_type]
    found = _igate._find(keys, rows)
    if found is None and len(rows) == len(_DEFAULT_ROWS):
        found = rows[position]
    return found


def build_plan_items(
    files: list[dict],
    texts: dict[int, str] | None = None,
    components: list[dict] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    texts = texts or {}
    rows = _igate._portal_rows(components) or _default_rows()
    don = _row(_T_DON, rows) or rows[0]
    warnings: list[str] = []

    attachments: list[dict] = []
    classified: list[dict] = []
    kem_theo: list[str] = []
    seen: set[str] = set()
    bytes_per_row: dict[int, int] = {}
    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        doc_type, source = phan_loai(texts.get(index, ""), file_name)
        seen.add(doc_type)
        row = _row(doc_type, rows) if doc_type in _ROW_KEYS else None
        if row is None:
            row = don
            kem_theo.append(f"{file_name} → \"{_TEN[doc_type]}\"")
        bytes_per_row[row[0]] = bytes_per_row.get(row[0], 0) + _kich_thuoc(file)
        attachments.append(_igate._item(index, file_name, _TEN[doc_type], row, doc_type))
        classified.append({"fileName": file_name, "docType": doc_type, "documentName": _TEN[doc_type],
                           "source": source, "componentIndex": row[0]})

    thieu = [ten for loai, ten in _BAT_BUOC.items() if loai not in seen]
    if attachments and thieu:
        warnings.append(
            "Chưa nhận ra thành phần hồ sơ bắt buộc: " + "; ".join(thieu) + ". Nơi tiếp nhận sẽ trả hồ sơ thiếu — "
            "cán bộ kiểm tra lại tệp đã tải lên."
        )
    if kem_theo:
        warnings.append(
            "Giấy tờ ngoài 3 thành phần hồ sơ (CCCD không phải thành phần hồ sơ của thủ tục) đã đính chung dòng văn "
            "bản đề nghị (vẫn là tệp riêng) vì bảng không có dòng \"giấy tờ khác\" — cán bộ gỡ ra nếu không cần nộp: "
            f"{', '.join(kem_theo)}."
        )
    for row_index, total in sorted(bytes_per_row.items()):
        if total > _GIOI_HAN_BYTE:
            warnings.append(
                f"Tổng dung lượng các tệp đính vào dòng thứ {row_index} là {total / 1024 / 1024:.1f} MB, vượt giới hạn "
                "6 MB của cổng — Phương án kèm sơ đồ hay vướng chỗ này: nén PDF hoặc giảm DPI trước khi nộp."
            )
    _igate._dedupe_document_names(attachments)
    if not attachments:
        warnings.append("Không có tài liệu nào để đính kèm.")
    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    components = ((options or {}).get("attachmentContext") or {}).get("components")
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]
    errors: list[str] = []

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
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
    attachments, warnings, classified = build_plan_items(raw_files, texts, components)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "portalRows": len(_igate._portal_rows(components)),
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": 0, "total_latency_ms": ocr_ms},
        "ocr_text": join_ocr_documents(ocr_results),
        "errors": errors,
    }

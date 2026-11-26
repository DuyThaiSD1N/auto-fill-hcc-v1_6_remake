"""Đính kèm 1.115692 (Lào Cai, cổng iGate mới) — chế độ ĐÍNH NGUYÊN TỆP (tắt "Tách giấy tờ"; chế độ tách gọi lại planner
này trên các PDF con, xem ../dinh_kem_tach/planner.py).

Bước 2 "Thành phần hồ sơ" (ảnh ánh xạ đính kèm người dùng gửi 25/11/2026): bảng mat-table NĂM dòng, mỗi dòng "1 Bản
chính", mat-checkbox + "Scan tệp tin"/"Chọn tệp tin", có "Chọn/Bỏ chọn tất cả" và nút "Thêm giấy tờ":
   1 Đơn đăng ký biến động … theo Mẫu số 24 …            ┐
   2 Giấy chứng nhận đã cấp                              ├ BỘ A — chưa có Thông báo xác nhận kết quả đăng ký đất đai
   3 Văn bản về việc đại diện … thông qua người đại diện ┘
   4 Đơn đăng ký biến động … theo theo Mẫu số 24 …       ┐ BỘ B — đã có Thông báo
   5 Thông báo xác nhận kết quả đăng ký đất đai          ┘
Chỉ nộp MỘT bộ: không tích "Chọn/Bỏ chọn tất cả", chỉ tích dòng của bộ đó (untickUnplannedRows: FE bỏ chọn hết rồi tích
dòng có tệp). Dòng 1 và 4 cùng tên (cổng ghi "theo theo") → Đơn Bộ A vào dòng Đơn ĐẦU, Bộ B vào dòng Đơn CUỐI.

Chọn bộ: có tệp Thông báo xác nhận → Bộ B; không có mà có GCN / văn bản đại diện → Bộ A; chỉ có Đơn → theo chữ Đơn
("Đã có Thông báo xác nhận…" → B, còn lại A). Giấy không thuộc bộ đã chọn, CCCD (không phải thành phần hồ sơ — thông tin
đã khai ở bước 1), giấy lạ → đính chung dòng Đơn của bộ đó (vẫn là tệp riêng) + cảnh báo để cán bộ gỡ; không bỏ tệp
nào, không dùng "Thêm giấy tờ".

Phân loại KHÔNG gọi LLM: so cụm tiêu đề xuất hiện SỚM NHẤT ở phần đầu chữ OCR (Đơn nhắc "Giấy chứng nhận", "Giấy ủy
quyền", "Thông báo xác nhận" trong thân — tiêu đề "Mẫu số 24" đứng trước nên vẫn là Đơn). Trang nối tiếp bị tách riêng
(trang 2 Đơn, trang sơ đồ/những thay đổi của GCN, trang lời chứng của Giấy ủy quyền) có cụm riêng. OCR rỗng → tên tệp.

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

_T_DON, _T_GCN, _T_DAI_DIEN, _T_THONG_BAO = "don_mau_24", "gcn", "van_ban_dai_dien", "thong_bao_xac_nhan"
_T_CCCD, _T_OTHER = "cccd", "other"
_TEN = {
    _T_DON: "Đơn đăng ký biến động đất đai Mẫu số 24",
    _T_GCN: "Giấy chứng nhận đã cấp",
    _T_DAI_DIEN: "Văn bản về việc đại diện",
    _T_THONG_BAO: "Thông báo xác nhận kết quả đăng ký đất đai",
    _T_CCCD: "Căn cước",
    _T_OTHER: "Giấy tờ kèm theo",
}

BO_A, BO_B = "A", "B"

# Bảng 5 dòng NGUYÊN VĂN (ảnh bước 2 người dùng gửi 25/11/2026; dòng 4 cổng ghi "theo theo").
_DEFAULT_ROWS = [
    "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 24 ban hành kèm theo Quyết định số "
    "47/2026/QĐ-UBND",
    "Giấy chứng nhận đã cấp",
    "Văn bản về việc đại diện theo quy định của pháp luật về dân sự đối với trường hợp thực hiện thủ tục đăng ký đất "
    "đai, tài sản gắn liền với đất thông qua người đại diện",
    "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo theo Mẫu số 24 ban hành kèm theo Quyết định số "
    "47/2026/QĐ-UBND",
    "Thông báo xác nhận kết quả đăng ký đất đai",
]
# docType → (từ khoá dò dòng, vị trí dòng mặc định 0-based khi bảng đúng 5 dòng). Đơn tìm riêng (_don_rows).
_ROW_KEYS: dict[str, tuple[list[str], int]] = {
    _T_GCN: (["giay chung nhan da cap"], 1),
    _T_DAI_DIEN: (["van ban ve viec dai dien", "thong qua nguoi dai dien", "uy quyen"], 2),
    _T_THONG_BAO: (["thong bao xac nhan ket qua dang ky dat dai", "thong bao xac nhan"], 4),
}
_DON_KEYS = ("mau so 24", "don dang ky bien dong")
# Loại giấy thuộc từng bộ (ngoài Đơn).
_THUOC_BO = {BO_A: (_T_GCN, _T_DAI_DIEN), BO_B: (_T_THONG_BAO,)}
_BAT_BUOC = {
    BO_A: {_T_DON: "Đơn đăng ký biến động (Mẫu số 24)", _T_GCN: "Giấy chứng nhận đã cấp"},
    BO_B: {_T_DON: "Đơn đăng ký biến động (Mẫu số 24)", _T_THONG_BAO: "Thông báo xác nhận kết quả đăng ký đất đai"},
}

# Cụm dấu hiệu (đã fold, chỉ chữ + số) — loại có cụm xuất hiện SỚM NHẤT ở phần đầu tệp thắng.
_DAU_HIEU: dict[str, tuple[str, ...]] = {
    _T_DON: ("mau so 24", "don dang ky bien dong", "cam doan noi dung ke khai tren don", "nguoi viet don",
             "huong dan ke khai don"),
    _T_GCN: ("giay chung nhan quyen su dung dat", "quyen so huu nha o va tai san khac",
             "thua dat nha o va tai san khac gan lien voi dat", "so do thua dat",
             "nhung thay doi sau khi cap giay chung nhan", "noi dung thay doi va co so phap ly"),
    _T_DAI_DIEN: ("giay uy quyen", "hop dong uy quyen", "van ban uy quyen", "ben uy quyen", "ben nhan uy quyen",
                  "uy quyen cho ben", "noi dung uy quyen", "thoi han uy quyen",
                  "loi chung cua nguoi thuc hien chung thuc", "van ban ve viec dai dien"),
    _T_THONG_BAO: ("thong bao xac nhan ket qua dang ky dat dai", "xac nhan ket qua dang ky dat dai"),
    _T_CCCD: ("can cuoc", "citizen identity", "identity card", "personal identification", "idvnm",
              "chung minh nhan dan"),
}
# OCR rỗng → tên tệp (đã fold, "_"/"-" thành dấu cách). Đơn xét TRƯỚC: tên kiểu "Don_Mau24_ChuaCoThongBao".
_TEN_TEP: tuple[tuple[str, tuple[str, ...]], ...] = (
    (_T_DON, ("mau24", "mau 24", "ms24", "don dang ky", "dondangky", "don bien dong")),
    (_T_DAI_DIEN, ("uy quyen", "uyquyen", "giay uq", "dai dien")),
    (_T_THONG_BAO, ("thong bao", "thongbao", "tb xnkq")),
    (_T_GCN, ("gcn", "giay chung nhan", "so do", "so hong")),
    (_T_CCCD, ("cccd", "can cuoc", "cmnd")),
)
# Đơn Bộ B ghi "Đã có Thông báo xác nhận kết quả đăng ký đất đai số …"; Bộ A ghi "Chưa có Thông báo …".
_DA_CO_THONG_BAO = re.compile(r"\b(da|nay da) co thong bao xac nhan")

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
        return (best or _T_OTHER), "ocr"
    name = _chu(Path(file_name or "").stem)
    for doc_type, keys in _TEN_TEP:
        if any(key in name for key in keys):
            return doc_type, "filename"
    return _T_OTHER, "default"


def chon_bo(doc_types: list[str], don_texts: list[str]) -> str:
    """Bộ hồ sơ (A: chưa có Thông báo / B: đã có Thông báo)."""
    if _T_THONG_BAO in doc_types:
        return BO_B
    if _T_GCN in doc_types or _T_DAI_DIEN in doc_types:
        return BO_A
    return BO_B if any(_DA_CO_THONG_BAO.search(_chu(t)) for t in don_texts) else BO_A


def _kich_thuoc(file: dict) -> int:
    """Kích thước thật, suy từ độ dài base64 của dataUrl (FileItem không mang size)."""
    payload = str(file.get("dataUrl") or "").partition(",")[2]
    return len(payload) * 3 // 4 - payload[-2:].count("=") if payload else 0


def _default_rows() -> list[Row]:
    return [(i + 1, name, fold(name)) for i, name in enumerate(_DEFAULT_ROWS)]


def _don_row(bo: str, rows: list[Row]) -> Row:
    dons = sorted((r for r in rows if any(k in r[2] for k in _DON_KEYS)), key=lambda r: r[0])
    if dons:
        return dons[0] if bo == BO_A else dons[-1]
    if len(rows) == len(_DEFAULT_ROWS):
        return rows[0] if bo == BO_A else rows[3]
    return rows[0]


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
    warnings: list[str] = []

    names = [str(file.get("name") or f"file-{index + 1}") for index, file in enumerate(files)]
    loai = [phan_loai(texts.get(index, ""), names[index]) for index in range(len(files))]
    doc_types = [t for t, _ in loai]
    bo = chon_bo(doc_types, [texts.get(i, "") for i, t in enumerate(doc_types) if t == _T_DON])
    don = _don_row(bo, rows)

    attachments: list[dict] = []
    classified: list[dict] = []
    kem_theo: list[str] = []
    bytes_per_row: dict[int, int] = {}
    for index, file in enumerate(files):
        file_name, (doc_type, source) = names[index], loai[index]
        row = None
        if doc_type == _T_DON:
            row = don
        elif doc_type in _THUOC_BO[bo]:
            row = _row(doc_type, rows)
        if row is None:
            row = don
            kem_theo.append(f"{file_name} → \"{_TEN[doc_type]}\"")
        bytes_per_row[row[0]] = bytes_per_row.get(row[0], 0) + _kich_thuoc(file)
        attachments.append(_igate._item(index, file_name, _TEN[doc_type], row, doc_type))
        classified.append({"fileName": file_name, "docType": doc_type, "documentName": _TEN[doc_type],
                           "source": source, "componentIndex": row[0], "bo": bo})

    thieu = [ten for t, ten in _BAT_BUOC[bo].items() if t not in doc_types]
    if attachments and thieu:
        warnings.append(
            f"Hồ sơ {'đã' if bo == BO_B else 'chưa'} có Thông báo xác nhận kết quả đăng ký đất đai (bộ "
            f"{'dòng 4–5' if bo == BO_B else 'dòng 1–3'}) nhưng chưa nhận ra: " + "; ".join(thieu)
            + ". Nơi tiếp nhận sẽ trả hồ sơ thiếu — cán bộ kiểm tra lại tệp đã tải lên."
        )
    if kem_theo:
        warnings.append(
            "Giấy tờ không thuộc thành phần hồ sơ của trường hợp đã chọn (CCCD không phải thành phần hồ sơ) đã đính "
            "chung dòng Đơn (vẫn là tệp riêng) — cán bộ gỡ ra nếu không cần nộp: " + ", ".join(kem_theo) + "."
        )
    for row_index, total in sorted(bytes_per_row.items()):
        if total > _GIOI_HAN_BYTE:
            warnings.append(
                f"Tổng dung lượng các tệp đính vào dòng thứ {row_index} là {total / 1024 / 1024:.1f} MB, vượt giới hạn "
                "6 MB của cổng — nén PDF hoặc giảm DPI trước khi nộp."
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

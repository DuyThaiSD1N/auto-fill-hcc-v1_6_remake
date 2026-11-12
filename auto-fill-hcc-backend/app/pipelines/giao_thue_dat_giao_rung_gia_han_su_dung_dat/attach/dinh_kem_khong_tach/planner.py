"""Đính kèm KHÔNG TÁCH cho bảng thành phần hồ sơ 26 dòng trên cổng Lâm Đồng (1.116366) — cài đặt tách tắt.

Bảng lấy VERBATIM từ crawl 'crawl-dinh-kem-1.116366.json' (12/11/2026): mỗi dòng là mat-checkbox + input[type=file]
multiple, loại bản ghi cứng sẵn ("1 Bản chính"/"1 Bản sao", không có radio để chọn) → engine FE `attp-row`, KHÔNG gửi
loaiBan. componentIndex là STT đếm từ 1 (FE thử rows[componentIndex - 1] trước rồi mới dò tên); componentName là tên
dòng nguyên văn — đã kiểm bằng thuật toán khớp hai chiều của FE: mỗi tên chỉ khớp đúng dòng của nó.

Ánh xạ hồ sơ (bảng KHÔNG có dòng Giấy chứng nhận / mảnh trích đo / CCCD / giấy ủy quyền):
  Đơn Mẫu số 01                         → dòng 13 "Đơn đề nghị giao đất, Mẫu số 01 Phụ lục VI…"
  Giấy ủy quyền, CCCD                   → dòng 13 cùng Đơn (tệp riêng, không gộp PDF)
  Giấy chứng nhận, mảnh trích đo, giấy lạ → dòng 24 "Giấy tờ khác có liên quan (nếu có)"
  giấy tờ thuế / miễn giảm / dự án / rừng → dòng riêng của nó (_ROUTES)
Dòng 12 ("…phê duyệt về thực hiện dự án") không có loại riêng: văn bản về thực hiện dự án đi dòng 9, văn bản phê duyệt
dự án đầu tư đi dòng 14.

Bảng có thể đổi theo trường hợp → có attachmentContext thì dò dòng THẬT trên trang theo từ khóa (_KEYS), gửi đúng index
+ tên nguyên văn của dòng; dòng không có trên trang → về dòng "Giấy tờ khác" (không có thì dòng Đơn) + cảnh báo.

MỖI FILE ĐÍNH NGUYÊN KHỐI, MỘT LẦN, vào dòng của giấy chính trong file theo _PRIORITY (có Đơn thì luôn là dòng Đơn); LLM
liệt kê mọi loại giấy trong file để chọn dòng và báo cán bộ những giấy có dòng riêng mà nằm chung file. OCR phân loại
dùng lại cách của đăng ký đất đai lần đầu Khánh Hòa (chữ đủ trang từ cache bước điền), gửi LLM trích đoạn đầu từng trang.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.documents import representative_excerpt
from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.attach.planner import _LLM_TEXT_MAX_CHARS, _ocr_for_classify
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON_DE_NGHI = "don_de_nghi"
_AUTHORIZATION = "authorization"
_IDENTITY = "identity"
_GCN = "gcn"
_TRICH_DO = "trich_do"
_OTHER = "other"

_DON_ROW = 13
_KHAC_ROW = 24

# STT -> tên dòng NGUYÊN VĂN (cột "Tên giấy tờ" của crawl).
_ROWS: dict[int, str] = {
    1: "Tờ khai lệ phí trước bạ",
    2: "Tờ khai thuế sử dụng đất phi nông nghiệp tương ứng với từng trường hợp theo quy định của pháp luật về quản lý "
       "thuế",
    3: "Giấy tờ có liên quan chứng minh thuộc diện được miễn, giảm tiền sử dụng đất theo quy định của pháp luật về người "
       "có công với cách mạng",
    4: "Quyết định hoặc văn bản theo quy định của pháp luật về miễn, giảm tiền sử dụng đất của Ủy ban nhân dân cấp tỉnh "
       "hoặc của cơ quan được Ủy ban nhân dân cấp tỉnh ủy quyền, phân cấp",
    5: "Giấy chứng nhận đầu tư hoặc Giấy phép đầu tư hoặc Giấy chứng nhận đăng ký đầu tư",
    6: "Xác nhận thông tin về cư trú hoặc Thông báo số định danh cá nhân và thông tin công dân trong Cơ sở dữ liệu quốc "
       "gia về dân cư",
    7: "Xác nhận của cơ quan có thẩm quyền về hộ nghèo",
    8: "Quyết định giao đất của cơ quan nhà nước có thẩm quyền",
    9: "Văn bản của cơ quan nhà nước có thẩm quyền về thực hiện dự án",
    10: "Văn bản đề nghị theo mẫu số 01/MGTH tại Phụ lục I ban hành kèm theo Thông tư số 80/2021/TT-BTC ngày 29/9/2021 "
        "của Bộ Tài chính",
    11: "Quyết định giao đất ở để bố trí tái định cư của cơ quan nhà nước có thẩm quyền",
    12: "Văn bản của cơ quan nhà nước có thẩm quyền phê duyệt về thực hiện dự án",
    13: "Đơn đề nghị giao đất, Mẫu số 01 Phụ lục VI ban hành kèm theo Quyết định số 40/2026/QĐ-UBND",
    14: "Văn bản phê duyệt dự án đầu tư, quyết định chấp thuận chủ trương đầu tư, quyết định chấp thuận chủ trương đầu tư "
        "đồng thời chấp thuận nhà đầu tư, quyết định chấp thuận nhà đầu tư, văn bản phê duyệt kết quả lựa chọn nhà đầu "
        "tư theo quy định của pháp luật về đầu tư, pháp luật về đầu tư công, pháp luật về đầu tư theo phương thức đối "
        "tác công tư hoặc các văn bản, giấy tờ có giá trị pháp lý tương đương theo quy định của pháp luật",
    15: "Tài liệu chứng minh năng lực tài chính",
    16: "Bản sao văn bản của đơn vị được giao tổ chức thực hiện việc đấu giá quyền sử dụng đất về kết quả đấu giá quyền "
        "sử dụng đất không thành quy định tại điểm b khoản 6 Điều 125 của Luật Đất đai",
    17: "Bản sao các văn bản theo quy định của pháp luật đối với trường hợp quy định tại điểm i khoản 1 Điều 133 của Luật "
        "Đất đai mà phải thu hồi đất để giao đất, cho thuê đất cho tổ chức, cá nhân sau chia tách, sáp nhập, chuyển "
        "đổi mô hình tổ chức",
    18: "Bản sao Phương án sử dụng đất đã được cơ quan, tổ chức có thẩm quyền phê duyệt đối với tổ chức kinh tế, đơn vị "
        "sự nghiệp công lập đã được Nhà nước giao đất, cho thuê đất trước ngày Luật Đất đai có hiệu lực thi hành đối "
        "với trường hợp quy định tại Điều 180 của Luật Đất đai (nếu có)",
    19: "Bản sao Phương án sử dụng đất của công ty nông, lâm nghiệp tại địa phương đã được cơ quan, tổ chức có thẩm quyền "
        "phê duyệt đối với trường hợp quy định tại Điều 181 của Luật Đất đai (nếu có)",
    20: "Bản sao Phương án sử dụng đất đã được cơ quan, tổ chức có thẩm quyền phê duyệt đối với diện tích đất thu hồi "
        "của công ty nông, lâm nghiệp quản lý, sử dụng để giao đất, cho thuê đất quy định tại các điểm c, d và đ khoản "
        "2 Điều 181 của Luật Đất đai (nếu có)",
    21: "Bản sao dự án đầu tư lấn biển hoặc hạng mục lấn biển của dự án đầu tư đã được cơ quan nhà nước có thẩm quyền "
        "phê duyệt đối với trường hợp quy định tại Điều 190 của Luật Đất đai",
    22: "Bản sao văn bản về kết quả thực hiện việc nhận chuyển nhượng dự án bất động sản theo quy định của pháp luật về "
        "kinh doanh bất động sản đối với trường hợp quy định tại khoản 7 Điều 124 Luật Đất đai",
    23: "Các giấy tờ đề nghị miễn, giảm tiền sử dụng đất, tiền thuê đất tại Phụ lục V ban hành kèm theo Quyết định số "
        "40/2026/QĐ-UBND (nếu có)",
    24: "Giấy tờ khác có liên quan (nếu có)",
    25: "Báo cáo điều tra, đánh giá hiện trạng rừng và bản đồ hiện trạng rừng theo quy định của pháp luật về lâm nghiệp "
        "đối với trường hợp giao đất và giao rừng",
    26: "Kết quả đấu giá thuê rừng; biên bản đấu giá cho thuê rừng; danh sách người trúng đấu giá thuê rừng; thông báo "
        "hoàn thành nghĩa vụ tài chính đối với người trúng đấu giá thuê rừng đối với trường hợp cho thuê đất và cho thuê "
        "rừng; dự án đầu tư đối với khu rừng đề nghị thuê của tổ chức, cá nhân trúng đấu giá thuê rừng; báo cáo điều "
        "tra, đánh giá hiện trạng rừng và bản đồ hiện trạng rừng theo quy định của pháp luật về lâm nghiệp đối với "
        "trường hợp cho thuê đất và cho thuê rừng",
}

# Từ khóa (đã fold) dò dòng thật khi extension gửi attachmentContext: tên đầy đủ trước, rồi cụm đặc trưng / 60 ký tự đầu
# (dòng 18 và 20 trùng 60 ký tự đầu nên có cụm riêng). Nhiều dòng cùng chứa → lấy dòng NGẮN nhất.
_KEYS: dict[int, tuple[str, ...]] = {
    row: (_fold(name), _fold(name)[:60]) for row, name in _ROWS.items()
}
_KEYS[_DON_ROW] = (_fold(_ROWS[_DON_ROW]), "don de nghi giao dat", "mau so 01 phu luc vi", "don theo mau so 01")
_KEYS[18] = (_fold(_ROWS[18]), "doi voi to chuc kinh te, don vi su nghiep cong lap")
_KEYS[20] = (_fold(_ROWS[20]), "dien tich dat thu hoi cua cong ty nong")
_KEYS[_KHAC_ROW] = (_fold(_ROWS[_KHAC_ROW]), "giay to khac co lien quan", "giay to khac")

# Loại giấy -> (dòng, tên tài liệu khi đính). None = dòng Đơn.
_ROUTES: dict[str, tuple[int | None, str]] = {
    _DON_DE_NGHI: (_DON_ROW, "Đơn đề nghị giao đất, cho thuê đất, chuyển mục đích sử dụng đất (Mẫu số 01)"),
    _AUTHORIZATION: (None, "Giấy ủy quyền"),
    _IDENTITY: (None, "Căn cước công dân"),
    _GCN: (_KHAC_ROW, "Giấy chứng nhận quyền sử dụng đất"),
    _TRICH_DO: (_KHAC_ROW, "Mảnh trích đo bản đồ địa chính"),
    "to_khai_le_phi_truoc_ba": (1, "Tờ khai lệ phí trước bạ"),
    "to_khai_thue_phi_nong_nghiep": (2, "Tờ khai thuế sử dụng đất phi nông nghiệp"),
    "giay_to_nguoi_co_cong": (3, "Giấy tờ chứng minh người có công với cách mạng"),
    "quyet_dinh_mien_giam": (4, "Quyết định miễn, giảm tiền sử dụng đất"),
    "giay_chung_nhan_dau_tu": (5, "Giấy chứng nhận đăng ký đầu tư"),
    "xac_nhan_cu_tru": (6, "Xác nhận thông tin về cư trú"),
    "xac_nhan_ho_ngheo": (7, "Xác nhận hộ nghèo"),
    "quyet_dinh_giao_dat": (8, "Quyết định giao đất"),
    "van_ban_thuc_hien_du_an": (9, "Văn bản về thực hiện dự án"),
    "van_ban_de_nghi_mgth": (10, "Văn bản đề nghị miễn, giảm (Mẫu số 01/MGTH)"),
    "quyet_dinh_tai_dinh_cu": (11, "Quyết định giao đất ở tái định cư"),
    "phe_duyet_du_an_dau_tu": (14, "Văn bản phê duyệt dự án đầu tư, chấp thuận chủ trương đầu tư"),
    "nang_luc_tai_chinh": (15, "Tài liệu chứng minh năng lực tài chính"),
    "dau_gia_khong_thanh": (16, "Văn bản kết quả đấu giá quyền sử dụng đất không thành"),
    "thu_hoi_dieu_133": (17, "Văn bản thu hồi đất (điểm i khoản 1 Điều 133)"),
    "phuong_an_to_chuc_kinh_te": (18, "Phương án sử dụng đất của tổ chức kinh tế, đơn vị sự nghiệp công lập"),
    "phuong_an_cong_ty_nong_lam": (19, "Phương án sử dụng đất của công ty nông, lâm nghiệp"),
    "phuong_an_dat_thu_hoi": (20, "Phương án sử dụng diện tích đất thu hồi của công ty nông, lâm nghiệp"),
    "du_an_lan_bien": (21, "Dự án đầu tư lấn biển"),
    "chuyen_nhuong_du_an_bds": (22, "Văn bản kết quả nhận chuyển nhượng dự án bất động sản"),
    "giay_to_mien_giam": (23, "Giấy tờ đề nghị miễn, giảm tiền sử dụng đất, tiền thuê đất"),
    "bao_cao_hien_trang_rung": (25, "Báo cáo điều tra, đánh giá hiện trạng rừng"),
    "dau_gia_thue_rung": (26, "Kết quả đấu giá thuê rừng"),
}
# File gộp nhiều giấy: dòng của giấy ĐỨNG TRƯỚC nhận nguyên file. Đơn luôn thắng; giấy có dòng riêng thắng giấy đi dòng
# "Giấy tờ khác"; ủy quyền / CCCD đứng cuối (đi theo dòng Đơn).
_PRIORITY: tuple[str, ...] = (
    _DON_DE_NGHI,
    *(doc_type for doc_type, (row, _name) in _ROUTES.items() if row not in (None, _DON_ROW, _KHAC_ROW)),
    _GCN, _TRICH_DO, _AUTHORIZATION, _IDENTITY,
)
_ALLOWED = set(_ROUTES) | {_OTHER}


def portal_rows(options: dict | None) -> list[tuple[int, str, str]]:
    """(STT, tên nguyên văn, tên fold) các dòng extension đọc trên trang (attachmentContext); [] nếu không gửi."""
    components = ((options or {}).get("attachmentContext") or {}).get("components")
    rows: list[tuple[int, str, str]] = []
    for component in components or []:
        if not isinstance(component, dict):
            continue
        try:
            index = int(component.get("index"))
        except (TypeError, ValueError):
            continue
        name = str(component.get("componentName") or "").strip()
        if index > 0 and name:
            rows.append((index, name, _fold(name)))
    return rows


def _find_on_page(row: int, rows: list[tuple[int, str, str]]) -> tuple[int, str] | None:
    for key in _KEYS[row]:
        hits = [item for item in rows if key in item[2]]
        if hits:
            index, name, _ = min(hits, key=lambda item: (len(item[2]), item[0]))
            return index, name
    return None


def resolve_row(row: int, rows: list[tuple[int, str, str]]) -> tuple[int, str, str | None]:
    """(STT, tên dòng gửi FE, cảnh báo). Không có attachmentContext → bảng 26 dòng cố định."""
    if not rows:
        return row, _ROWS[row], None
    hit = _find_on_page(row, rows)
    if hit:
        return hit[0], hit[1], None
    fallback = _find_on_page(_KHAC_ROW, rows) or _find_on_page(_DON_ROW, rows) or (rows[0][0], rows[0][1])
    note = f"Trang không có dòng '{_ROWS[row][:80]}' — đính vào dòng '{fallback[1][:80]}'; cán bộ kiểm tra lại."
    return fallback[0], fallback[1], note


def route_row(doc_type: str) -> int:
    """Dòng nhận giấy trong bảng 26 dòng; ủy quyền / CCCD đi dòng Đơn, giấy lạ đi dòng "Giấy tờ khác"."""
    if doc_type == _OTHER:
        return _KHAC_ROW
    row = _ROUTES[doc_type][0] if doc_type in _ROUTES else _KHAC_ROW
    return _DON_ROW if row is None else row


def document_name(doc_type: str) -> str:
    return _ROUTES[doc_type][1] if doc_type in _ROUTES else ""


def primary(doc_types: list[str] | set[str]) -> str:
    return next((doc_type for doc_type in _PRIORITY if doc_type in doc_types), _OTHER)


def normalize_doc_type(value: Any) -> str:
    folded = _fold(str(value or ""))
    for doc_type in _ALLOWED:
        if folded == _fold(doc_type):
            return doc_type
    return _OTHER


def _doc_types(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        raw = [raw]
    out: list[str] = []
    for value in raw:
        doc_type = normalize_doc_type(value)
        if doc_type not in out:
            out.append(doc_type)
    return out


def attachment(file_index: int, file_name: str, row: int, row_name: str, name: str, doc_type: str) -> dict:
    # KHÔNG gửi loaiBan: mỗi dòng của cổng ghi cứng loại bản. Nhiều item cùng dòng → FE bơm cả loạt vào một ô multiple.
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": name,
        "componentName": row_name,
        "componentIndex": row,
        "target": "attp-row",
        "needsAddComponent": False,
        "detectedType": doc_type,
    }


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, list[str]]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=900, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    result: dict[int, list[str]] = {}
    for item in parsed.get("documents", []) or []:
        try:
            result[int(item.get("index"))] = _doc_types(item.get("docTypes", item.get("docType")))
        except (TypeError, ValueError, AttributeError):
            continue
    return result


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict] | None = None,
    llm_types: dict[int, list[str] | str] | None = None,
    rows: list[tuple[int, str, str]] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    del ocr_results  # LLM-first: không suy luận rule từ OCR text ở đây.
    rows = rows or []
    types_by_file = {index: _doc_types(raw) for index, raw in (llm_types or {}).items() if raw}
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    def warn(message: str | None) -> None:
        if message and message not in warnings:
            warnings.append(message)

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        doc_types = types_by_file.get(index, [])
        doc_type = primary(doc_types)
        row, row_name, note = resolve_row(route_row(doc_type), rows)
        warn(note)
        others = sorted({route_row(item) for item in doc_types if item in _ROUTES} - {route_row(doc_type)})
        # File gộp hoặc không rõ loại giữ TÊN GỐC để cán bộ nhận ra; file một giấy mang tên giấy.
        name = file_name if others or doc_type == _OTHER else document_name(doc_type)
        attachments.append(attachment(index, file_name, row, row_name, name, doc_type))
        classified.append({"fileName": file_name, "docType": doc_type, "docTypes": doc_types,
                           "source": "llm" if index in types_by_file else "unknown", "rows": [row]})
        if doc_type == _OTHER:
            warnings.append(f"Chưa nhận diện chắc loại giấy tờ cho '{file_name}' — tạm đính vào dòng {row} (Giấy tờ "
                            f"khác có liên quan); cán bộ kiểm tra lại.")
        elif others:
            warnings.append(f"'{file_name}' gộp nhiều giấy tờ — đính nguyên file một lần vào dòng {row} "
                            f"({document_name(doc_type)}), không tách sang dòng {', '.join(map(str, others))}.")

    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    rows = portal_rows(options)
    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    ocr_files = [item for item in raw_files if item.get("type") in _OCR_TYPES]
    errors: list[str] = []

    started = time.monotonic()
    ocr_results = await _ocr_for_classify(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    by_name = {item.get("name"): item for item in ocr_results}
    llm_documents = [
        {"index": index, "text": representative_excerpt(str(by_name[file.get("name")].get("text")),
                                                        _LLM_TEXT_MAX_CHARS)}
        for index, file in enumerate(raw_files)
        if str(by_name.get(file.get("name"), {}).get("text") or "").strip()
    ]
    started = time.monotonic()
    llm_types: dict[int, list[str]] = {}
    if llm_documents:
        try:
            llm_types = await _classify_with_llm(llm_documents)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types, rows)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [item["name"] for item in raw_files],
            "ocrDocuments": [item.get("name") for item in ocr_results if item.get("text")],
            "llmDocuments": [raw_files[item["index"]]["name"] for item in llm_documents],
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

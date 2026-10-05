"""Lập kế hoạch đính kèm cho [Lâm Đồng] "Chuyển mục đích sử dụng đất; chuyển hình thức sử dụng đất;
gia hạn sử dụng đất khi hết thời hạn sử dụng đất; điều chỉnh thời hạn sử dụng đất của dự án đầu tư"
(mã 1.116365, cổng dichvucong.lamdong.gov.vn).

Bảng thành phần hồ sơ có sẵn 24 dòng (đã đối chiếu VERBATIM với 'chuyển mục đích đính kèm.html' —
mỗi dòng là mat-checkbox + input[type=file] multiple) → engine "attp-row": FE tick checkbox rồi bơm
file vào ô upload của đúng dòng. componentIndex là STT 1-BASED; componentName là đoạn text đặc trưng
trong cột "Tên giấy tờ" (FE khớp substring hai chiều sau khi fold dấu).

⚠ Bẫy đã kiểm: FE coi là khớp cả khi componentName CHỨA text của dòng (`want.includes(rowText)`).
Dòng 6 là TIỀN TỐ của dòng 22, và dòng 7 gần trùng đuôi dòng 22 → mọi chuỗi componentName dưới đây đã
được kiểm lại với đúng thuật toán của FE trên cả 24 dòng: mỗi chuỗi chỉ khớp DUY NHẤT dòng của nó.

QUY TẮC ĐÍNH KÈM — 3 MỤC (theo ảnh ánh xạ Anh-xa-thanh-phan-ho-so_1.116365.png):
  MỤC 1 — ĐƠN      → Đơn + Giấy ủy quyền + CCCD vào CÙNG MỘT DÒNG (dòng của mẫu đơn tương ứng).
                     Mẫu 02 (chuyển mục đích) → STT 21; Mẫu 03 (chuyển hình thức) → STT 4;
                     Mẫu 4a (gia hạn) → STT 5; Mẫu 4b (điều chỉnh thời hạn) → STT 1.
  MỤC 2 — BẢN VẼ   → STT 23 "Bản trích lục bản đồ địa chính hoặc trích đo bản đồ địa chính".
  MỤC 3 — GCN      → STT 22 (dòng "khoản 21 Điều 3 ... hoặc ... Điều 137 ..."). Ảnh ánh xạ ghi rõ GCN
                     nộp ở MỤC 3, kể cả hồ sơ nhánh "chuyển hình thức" (dòng 3) và "gia hạn" (dòng 6).
Các dòng còn lại chỉ dùng khi hồ sơ thực sự có giấy đó (xem _ROUTES).

⚠ BẢNG ĐỔI THEO TRƯỜNG HỢP: cổng chỉ hiện các dòng của trường hợp đang làm, không phải lúc nào cũng đủ
24 dòng. Hồ sơ "điều chỉnh thời hạn" chỉ có 17 dòng (Đơn 4b, VB thay đổi thời hạn, GCN "Một trong các
giấy chứng nhận: …", rồi các dòng chung), KHÔNG có Mẫu 02/03/4a, dòng khoản 21 Điều 3/Điều 137, dòng gia
hạn dự án, và thứ tự dòng cũng khác. Vì vậy index/tên cố định ở dưới CHỈ dùng khi extension không gửi
attachmentContext. Có attachmentContext thì mỗi route dò dòng THẬT theo "keys" (thử lần lượt; nhiều dòng
cùng chứa thì lấy dòng NGẮN nhất = cụ thể nhất) rồi gửi đúng index + tên NGUYÊN VĂN của dòng đó. Dòng
không có trên trang → tệp về dòng Đơn neo + cảnh báo (Đơn không có dòng riêng → mượn dòng Đơn khác).

⚠ CÙNG DÒNG ≠ GỘP PDF: ô upload của mỗi dòng là input[type=file] MULTIPLE, FE (attachFilesByAttpRow)
gom mọi item cùng componentName rồi set CẢ LOẠT vào một ô → mỗi giấy tờ vẫn là MỘT TỆP RIÊNG, cán bộ
mở/tải từng cái được. KHÔNG dùng sourceFileIndexes (gộp PDF) ở thủ tục này. Thứ tự item giữ đúng thứ
tự đọc của ảnh ánh xạ: Đơn → Giấy ủy quyền → CCCD.

Phân loại LLM-FIRST tuyệt đối: docType CHỈ lấy từ LLM, KHÔNG có nhánh rule keyword (giòn, dễ sai).
File không nhận ra loại → vẫn đính vào dòng ĐƠN, giữ TÊN FILE GỐC làm documentName + cảnh báo để cán
bộ soát. KHÔNG set Bản chính/Bản sao: mỗi dòng của cổng đã ghi cứng loại bản, không có radio để chọn.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# --- docType LLM ---
_DON_CHUYEN_MUC_DICH = "don_chuyen_muc_dich"
_DON_CHUYEN_HINH_THUC = "don_chuyen_hinh_thuc"
_DON_GIA_HAN = "don_gia_han"
_DON_DIEU_CHINH_THOI_HAN = "don_dieu_chinh_thoi_han"
_UY_QUYEN = "uy_quyen"
_CCCD = "cccd"
_GIAY_CHUNG_NHAN = "giay_chung_nhan"
_TRICH_LUC_BAN_DO = "trich_luc_ban_do"
_XAC_NHAN_CU_TRU = "xac_nhan_cu_tru"
_TO_KHAI_LE_PHI_TRUOC_BA = "to_khai_le_phi_truoc_ba"
_TO_KHAI_THUE_PHI_NONG_NGHIEP = "to_khai_thue_phi_nong_nghiep"
_VAN_BAN_THAY_DOI_THOI_HAN_DU_AN = "van_ban_thay_doi_thoi_han_du_an"
_VAN_BAN_GIA_HAN_DU_AN = "van_ban_gia_han_du_an"
_QUYET_DINH_DAT_QUA_CAC_THOI_KY = "quyet_dinh_dat_qua_cac_thoi_ky"
_GIAY_CHUNG_NHAN_DAU_TU = "giay_chung_nhan_dau_tu"
_GIAY_TO_MIEN_GIAM = "giay_to_mien_giam"
_OTHER = "other"

# Bốn loại ĐƠN — mỗi loại một dòng riêng; loại đơn nào có mặt sẽ neo MỤC 1 (gộp Đơn + ủy quyền + CCCD).
# index/name: bảng 24 dòng (extension không gửi attachmentContext). keys: từ khóa đã fold để dò dòng thật.
_DON_ROUTES: dict[str, dict[str, Any]] = {
    _DON_CHUYEN_MUC_DICH: {
        "index": 21,
        "name": "Đơn, Mẫu số 02 Phụ lục VI",
        "keys": ["mau so 02 phu luc vi"],
        "documentName": "Đơn đề nghị chuyển mục đích sử dụng đất",
    },
    _DON_CHUYEN_HINH_THUC: {
        "index": 4,
        "name": "Đơn, Mẫu số 03 Phụ lục VI",
        "keys": ["mau so 03 phu luc vi"],
        "documentName": "Đơn đề nghị chuyển hình thức sử dụng đất",
    },
    _DON_GIA_HAN: {
        "index": 5,
        "name": "Đơn theo Mẫu số 4a Phụ lục VI",
        "keys": ["mau so 4a phu luc vi"],
        "documentName": "Đơn đề nghị gia hạn sử dụng đất",
    },
    _DON_DIEU_CHINH_THOI_HAN: {
        "index": 1,
        "name": "Đơn, Mẫu số 4b Phụ lục VI",
        "keys": ["mau so 4b phu luc vi"],
        "documentName": "Đơn đề nghị điều chỉnh thời hạn sử dụng đất của dự án đầu tư",
    },
}

# Hồ sơ không đọc được loại đơn nào → dùng dòng Đơn CHÍNH của thủ tục (Mẫu 02, dòng duy nhất có mã
# thành phần TP-H36.000013 trên cổng) + cảnh báo cho cán bộ.
_DEFAULT_DON = _DON_ROUTES[_DON_CHUYEN_MUC_DICH]

# Các giấy tờ có dòng riêng (không gộp vào MỤC 1).
_ROUTES: dict[str, dict[str, Any]] = {
    _GIAY_CHUNG_NHAN: {
        "index": 22,
        "name": "hoặc một trong các loại giấy tờ quy định tại Điều 137 Luật Đất đai",
        "keys": ["dieu 137 luat dat dai", "khoan 21 dieu 3", "mot trong cac giay chung nhan"],
        "documentName": "Giấy chứng nhận quyền sử dụng đất",
    },
    _TRICH_LUC_BAN_DO: {
        "index": 23,
        "name": "Bản trích lục bản đồ địa chính hoặc trích đo bản đồ địa chính",
        "keys": ["trich luc ban do dia chinh"],
        "documentName": "Bản trích lục bản đồ địa chính",
    },
    _XAC_NHAN_CU_TRU: {
        "index": 14,
        "name": "Xác nhận thông tin về cư trú hoặc Thông báo số định danh cá nhân",
        "keys": ["xac nhan thong tin ve cu tru"],
        "documentName": "Xác nhận thông tin về cư trú",
    },
    _TO_KHAI_LE_PHI_TRUOC_BA: {
        "index": 9,
        "name": "Tờ khai lệ phí trước bạ",
        "keys": ["to khai le phi truoc ba"],
        "documentName": "Tờ khai lệ phí trước bạ",
    },
    _TO_KHAI_THUE_PHI_NONG_NGHIEP: {
        "index": 10,
        "name": "Tờ khai thuế sử dụng đất phi nông nghiệp",
        "keys": ["to khai thue su dung dat phi nong nghiep"],
        "documentName": "Tờ khai thuế sử dụng đất phi nông nghiệp",
    },
    _VAN_BAN_THAY_DOI_THOI_HAN_DU_AN: {
        "index": 2,
        "name": "cho phép thay đổi thời hạn hoạt động của dự án đầu tư",
        "keys": ["cho phep thay doi thoi han hoat dong"],
        "documentName": "Văn bản cho phép thay đổi thời hạn hoạt động của dự án đầu tư",
    },
    _VAN_BAN_GIA_HAN_DU_AN: {
        "index": 8,
        "name": "cho phép gia hạn thời hạn hoạt động của dự án đầu tư",
        "keys": ["cho phep gia han thoi han hoat dong"],
        "documentName": "Văn bản cho phép gia hạn thời hạn hoạt động của dự án đầu tư",
    },
    _QUYET_DINH_DAT_QUA_CAC_THOI_KY: {
        "index": 7,
        "name": (
            "Quyết định giao đất, quyết định cho thuê đất, quyết định cho phép chuyển mục đích sử "
            "dụng đất của cơ quan nhà nước có thẩm quyền theo quy định của pháp luật đất đai qua "
            "các thời kỳ"
        ),
        "keys": ["quyet dinh giao dat, quyet dinh cho thue dat", "quyet dinh giao dat cua co quan nha nuoc"],
        "documentName": "Quyết định giao đất/cho thuê đất/cho phép chuyển mục đích sử dụng đất",
    },
    _GIAY_CHUNG_NHAN_DAU_TU: {
        "index": 13,
        "name": "Giấy chứng nhận đầu tư hoặc Giấy phép đầu tư hoặc Giấy chứng nhận đăng ký đầu tư",
        "keys": ["giay chung nhan dau tu hoac giay phep dau tu"],
        "documentName": "Giấy chứng nhận đăng ký đầu tư",
    },
    _GIAY_TO_MIEN_GIAM: {
        "index": 24,
        "name": "Các giấy tờ đề nghị miễn, giảm tiền sử dụng đất, tiền thuê đất tại Phụ lục V",
        "keys": ["giay to de nghi mien, giam tien su dung dat"],
        "documentName": "Giấy tờ đề nghị miễn, giảm tiền sử dụng đất, tiền thuê đất",
    },
}

_ALLOWED = set(_DON_ROUTES) | set(_ROUTES) | {_UY_QUYEN, _CCCD, _OTHER}

# Ủy quyền và CCCD KHÔNG có dòng riêng trong bảng 24 dòng → đính chung ô với Đơn, nhưng vẫn là tệp
# riêng nên cần documentName riêng để cán bộ phân biệt trong danh sách file của ô đó.
_LABELS = {
    _UY_QUYEN: "Giấy ủy quyền",
    _CCCD: "Căn cước công dân",
}

# Nhãn cho tài liệu KHÔNG nhận ra loại. Bảng không có dòng "giấy tờ khác" → đính vào dòng Đơn.
_LABEL_OTHER = "Tài liệu khác"


def _normalize_doc_type(value: Any) -> str:
    folded = _fold(str(value or ""))
    for doc_type in _ALLOWED:
        if folded == _fold(doc_type):
            return doc_type
    return _OTHER


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


def _item(file_index: int, file_name: str, document_name: str, route: dict, doc_type: str) -> dict:
    # KHÔNG set sourceFileIndexes: mỗi giấy tờ giữ nguyên là MỘT TỆP, không gộp PDF. Nhiều item cùng
    # componentName sẽ được FE gom rồi bơm cả loạt vào cùng một ô upload (input multiple).
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": route["name"],
        "componentIndex": route["index"],
        "target": "attp-row",
        "needsAddComponent": False,
        "detectedType": doc_type,
    }


def _dedupe_document_names(attachments: list[dict]) -> None:
    """documentName trở thành TÊN TỆP khi FE dựng file → hai tệp cùng tên trong một ô (vd CCCD của
    hai người) sẽ chồng nhau và bị bộ chống-trùng của FE bỏ qua. Đánh số từ bản thứ hai trở đi."""
    counts: dict[tuple[int, str], int] = {}
    for item in attachments:
        key = (item["componentIndex"], item["documentName"])
        counts[key] = counts.get(key, 0) + 1
    used: dict[tuple[int, str], int] = {}
    for item in attachments:
        key = (item["componentIndex"], item["documentName"])
        if counts[key] < 2:
            continue
        used[key] = used.get(key, 0) + 1
        item["documentName"] = f"{item['documentName']} ({used[key]})"


def _portal_rows(components: list[dict] | None) -> list[tuple[int, str, str]]:
    """(index, tên nguyên văn, tên fold) các dòng extension đọc được trên trang (attachmentContext)."""
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


def _on_page(route: dict, rows: list[tuple[int, str, str]]) -> dict | None:
    """Dòng thật của route trên trang; None nếu trường hợp đang làm không hiện dòng đó.

    Không có attachmentContext (extension cũ) → giữ index/tên cố định của bảng 24 dòng. Có thì gửi
    đúng index + tên NGUYÊN VĂN của dòng: FE so rows[index-1] khớp tuyệt đối, không lo trùng tiền tố.
    """
    if not rows:
        return route
    for key in route["keys"]:
        hits = [row for row in rows if key in row[2]]
        if hits:
            # Nhiều dòng cùng chứa từ khóa (vd dòng 7 và đuôi dòng 22) → dòng ngắn nhất là dòng riêng.
            index, name, _ = min(hits, key=lambda row: (len(row[2]), row[0]))
            return {**route, "index": index, "name": name}
    return None


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict] | None = None,
    llm_types: dict[int, str] | None = None,
    components: list[dict] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    del ocr_results  # LLM-first: không dùng OCR text để suy luận rule ở đây.
    llm_types = llm_types or {}
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    rows = _portal_rows(components)

    def warn(message: str) -> None:
        if message not in warnings:
            warnings.append(message)

    def don_on_page(doc_type: str) -> tuple[dict, str | None]:
        """Dòng của mẫu đơn; trang không có dòng đó → mượn dòng Đơn khác đang hiện (giữ tên giấy)."""
        route = _DON_ROUTES[doc_type]
        own = _on_page(route, rows)
        if own:
            return own, None
        borrowed = next(
            (hit for hit in (_on_page(other, rows) for other in _DON_ROUTES.values()) if hit),
            {"index": rows[0][0], "name": rows[0][1]},
        )
        note = (
            f"Trang không có dòng '{route['documentName']}' — đính vào dòng '{borrowed['name']}'; "
            "cán bộ kiểm tra lại."
        )
        return {**route, "index": borrowed["index"], "name": borrowed["name"]}, note

    def name_of(index: int) -> str:
        return str(files[index].get("name") or f"file-{index + 1}")

    resolved: list[str] = []
    for index in range(len(files)):
        llm_type = llm_types.get(index, "")
        resolved.append(llm_type if llm_type in _ALLOWED else _OTHER)

    don_indexes = [i for i, t in enumerate(resolved) if t in _DON_ROUTES]
    uy_quyen_indexes = [i for i, t in enumerate(resolved) if t == _UY_QUYEN]
    cccd_indexes = [i for i, t in enumerate(resolved) if t == _CCCD]

    # ---- MỤC 1: dòng ĐƠN. KHÔNG gộp PDF — ô upload của cổng là input[type=file] MULTIPLE, FE gom mọi
    # item cùng componentName rồi set cả loạt vào một ô → mỗi giấy tờ vẫn là MỘT TỆP RIÊNG, cán bộ mở
    # ra xem/tách được từng cái. Đơn ĐẦU TIÊN quyết định dòng neo cho ủy quyền + CCCD (bảng không có
    # dòng riêng cho hai loại này); đơn thứ hai trở đi đi dòng của chính nó.
    don_route, don_note = don_on_page(resolved[don_indexes[0]] if don_indexes else _DON_CHUYEN_MUC_DICH)
    if not don_indexes and (uy_quyen_indexes or cccd_indexes):
        warnings.append(
            "Không nhận ra Đơn đề nghị trong hồ sơ — giấy ủy quyền/CCCD tạm đính vào dòng "
            f"'{_DEFAULT_DON['documentName']}'; cán bộ kiểm tra lại."
        )

    def anchor() -> dict:
        # Cảnh báo "mượn dòng Đơn" chỉ hiện khi thật sự có tệp đi vào dòng neo.
        if don_note:
            warn(don_note)
        return don_route

    # Thứ tự đính trong cùng một ô giữ đúng thứ tự đọc của ảnh ánh xạ: Đơn → Giấy ủy quyền → CCCD.
    muc1: list[tuple[int, dict]] = []
    for i in don_indexes:
        route, note = don_on_page(resolved[i])
        if note:
            warn(note)
        muc1.append((i, route))
    muc1 += [(i, anchor()) for i in uy_quyen_indexes + cccd_indexes]
    for index, route in muc1:
        doc_type = resolved[index]
        document_name = route["documentName"] if doc_type in _DON_ROUTES else _LABELS[doc_type]
        attachments.append(_item(index, name_of(index), document_name, route, doc_type))
        classified.append({
            "fileName": name_of(index), "docType": doc_type, "source": "llm",
            "componentIndexes": [route["index"]],
        })

    # ---- MỤC 2, MỤC 3 và các dòng phụ.
    for index, doc_type in enumerate(resolved):
        if doc_type not in _ROUTES:
            continue
        document_name = _ROUTES[doc_type]["documentName"]
        route = _on_page(_ROUTES[doc_type], rows)
        if route is None:
            route = anchor()
            warnings.append(
                f"Trang không có dòng '{document_name}' — '{name_of(index)}' đính vào dòng "
                f"'{route['name']}'; cán bộ kiểm tra lại."
            )
        attachments.append(_item(index, name_of(index), document_name, route, doc_type))
        classified.append({
            "fileName": name_of(index), "docType": doc_type, "source": "llm",
            "componentIndexes": [route["index"]],
        })

    # ---- KHÔNG RÕ LOẠI → "Tài liệu khác", đính vào dòng ĐƠN. TUYỆT ĐỐI KHÔNG bỏ file nào: mọi
    # nhánh hỏng (OCR rỗng, file không phải ảnh/PDF, LLM lỗi/trả loại lạ) đều rơi về đây, nên mỗi file
    # tải lên luôn có ít nhất MỘT plan item. Giữ TÊN FILE GỐC trong documentName để cán bộ soát lại.
    for index, doc_type in enumerate(resolved):
        if doc_type != _OTHER:
            continue
        file_name = name_of(index)
        attachments.append(_item(index, file_name, f"{_LABEL_OTHER} - {file_name}", anchor(), _OTHER))
        warnings.append(
            f"Chưa nhận diện chắc loại giấy tờ cho '{file_name}' — xếp '{_LABEL_OTHER}' và đính vào "
            f"dòng '{don_route['documentName']}'; cán bộ kiểm tra lại."
        )
        classified.append({
            "fileName": file_name, "docType": _OTHER,
            "source": "llm" if llm_types.get(index) else "unknown",
            "componentIndexes": [don_route["index"]],
        })

    if not attachments:
        warnings.append("Không có tài liệu nào để đính kèm.")
    _dedupe_document_names(attachments)
    # CHỐT AN TOÀN: mọi file tải lên PHẢI có mặt trong kế hoạch. Nếu một nhánh nào đó về sau làm rơi
    # file, vớt lại vào dòng Đơn ngay tại đây thay vì để file biến mất im lặng.
    planned = {item["fileIndex"] for item in attachments}
    for index in range(len(files)):
        if index in planned:
            continue
        file_name = name_of(index)
        attachments.append(_item(index, file_name, f"{_LABEL_OTHER} - {file_name}", anchor(), _OTHER))
        warnings.append(
            f"'{file_name}' chưa được xếp vào dòng nào — đính bổ sung vào dòng "
            f"'{don_route['documentName']}'; cán bộ kiểm tra lại."
        )
    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    # Danh sách dòng extension đọc trên trang — bảng đổi theo trường hợp nên phải dò dòng thật.
    components = ((options or {}).get("attachmentContext") or {}).get("components")
    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    ocr_files = [item for item in raw_files if item.get("type") in _OCR_TYPES]
    errors: list[str] = []

    from app.services import ocr

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    by_name = {item.get("name"): item for item in ocr_results}
    llm_documents = [
        {"index": index, "text": str(by_name.get(file.get("name"), {}).get("text") or "")}
        for index, file in enumerate(raw_files)
        if str(by_name.get(file.get("name"), {}).get("text") or "").strip()
    ]
    started = time.monotonic()
    llm_types: dict[int, str] = {}
    if llm_documents:
        try:
            llm_types = await _classify_with_llm(llm_documents)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types, components)
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

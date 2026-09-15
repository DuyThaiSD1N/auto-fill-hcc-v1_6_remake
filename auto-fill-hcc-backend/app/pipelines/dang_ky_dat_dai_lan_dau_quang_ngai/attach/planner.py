"""Lập kế hoạch đính kèm vào đúng 20 dòng hồ sơ trên cổng DVC Quảng Ngãi.

Thủ tục "Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận ... lần đầu": bảng thành phần
hồ sơ có sẵn 20 dòng (đã đối chiếu VERBATIM với 'đki dâtd đai đính kèm.html' + ảnh ánh xạ 03 cho các
dòng 15-20 và khu "+ Thêm giấy tờ"). componentIndex là vị trí DOM 0-based của dòng (STT − 1);
componentName là đoạn text đặc trưng trong cột "Tên giấy tờ" của dòng đó (FE khớp substring sau khi
fold dấu, đã soát để mỗi chuỗi chỉ trúng ĐÚNG dòng mong muốn).

  index 0  (STT1) : Đơn đăng ký đất đai, tài sản gắn liền với đất          -> don_dang_ky (ĐƠN CHÍNH)
  index 1  (STT2) : Văn bản về việc đại diện theo pháp luật dân sự         -> authorization
  index 2  (STT3) : Giấy tờ Điều 137, khoản 1/khoản 5 Điều 148, 149        -> giay_to_dieu_137
  index 3  (STT4) : Thừa kế QSDĐ chưa được cấp Giấy chứng nhận             -> thua_ke
  index 4  (STT5) : Thừa kế + chuyển quyền theo khoản 4 Điều 45            -> thua_ke_chuyen_quyen
  index 5  (STT6) : Giao đất không đúng thẩm quyền/mua, thanh lý, hóa giá  -> giao_dat_khong_dung_tham_quyen
  index 6  (STT7) : Giấy tờ liên quan đến xử phạt vi phạm hành chính       -> xu_phat_hanh_chinh
  index 7  (STT8) : Xác lập quyền đối với thửa đất liền kề                 -> thua_dat_lien_ke
  index 8  (STT9) : Văn bản xác định thành viên chung QSDĐ của hộ gia đình -> van_ban_thanh_vien_ho_gia_dinh
  index 9  (STT10): Mảnh trích đo bản đồ địa chính thửa đất                -> manh_trich_do
  index 10 (STT11): Hồ sơ thiết kế xây dựng công trình                     -> ho_so_thiet_ke_xay_dung
  index 11 (STT12): Quyết định xử phạt VPHC + chứng từ nộp phạt            -> quyet_dinh_xu_phat
  index 12 (STT13): Chứng từ thực hiện nghĩa vụ tài chính                  -> chung_tu_tai_chinh, to_khai_thue
  index 13 (STT14): Giấy tờ chuyển quyền có chữ ký hai bên                 -> giay_to_chuyen_quyen
  index 14 (STT15): Giấy xác nhận của cơ quan quản lý xây dựng cấp huyện   -> giay_xac_nhan_xay_dung
  index 15 (STT16): Văn bản thỏa thuận cấp chung một Giấy chứng nhận       -> thoa_thuan_cap_chung
  index 16 (STT17): TRÙNG NHÓM dòng STT3 (chỉ khác "khoản 4" vs "khoản 1") -> BỎ, xem ghi chú dưới
  index 17 (STT18): TRÙNG nội dung dòng STT4 (bản rút gọn, không hậu tố)   -> BỎ
  index 18 (STT19): TRÙNG HOÀN TOÀN dòng STT16 (chỉ thừa dấu chấm cuối)    -> BỎ
  index 19 (STT20): Thông báo xác nhận kết quả đăng ký đất đai             -> KHÔNG route (xem dưới)

DÒNG TRÙNG TEXT — chỉ route DÒNG CHÍNH, đúng như ảnh ánh xạ 03 hướng dẫn cán bộ:
  - STT17 ≡ STT3  ("Trùng nhóm nội dung với dòng 3 — chỉ tích một dòng")   -> chỉ index 2.
  - STT18 ≡ STT4  ("Không tích. Trùng nội dung với dòng 4")                -> chỉ index 3.
  - STT19 ≡ STT16 ("Chỉ tích và tải file ở dòng 16 HOẶC dòng 19, không tích cả hai") -> chỉ index 15.
FE gom nhóm theo componentName nên hai item cùng tên sẽ nhập một nhóm và chỉ một dòng được đính ->
nhân đôi là vô nghĩa và gây hiểu nhầm. Riêng cặp STT16/STT19 text chỉ khác dấu chấm cuối nên
componentName của thoa_thuan_cap_chung khớp cả hai dòng; FE lấy dòng khớp ĐẦU TIÊN = STT16 (dòng
chính), đúng ý đồ. Cán bộ tự đính thêm dòng trùng nếu cổng bắt buộc.

DÒNG 20 "Thông báo xác nhận kết quả đăng ký đất đai" KHÔNG có docType: ảnh ánh xạ ghi rõ đây là giấy
do cơ quan đăng ký đất đai phát hành SAU khi giải quyết hồ sơ, không phải giấy tờ người dân nộp vào.

Bảng KHÔNG có dòng riêng cho CCCD/căn cước và giấy xác nhận số định danh (CMND 9 số ↔ CCCD là cùng
một người) -> gom CHUNG vào dòng ĐƠN ĐĂNG KÝ (index 0), giữ documentName mô tả để cán bộ soát; đây
chính là cách xử lý (2) mà ảnh ánh xạ 03 khuyến nghị khi các giấy tờ đó nằm chung một file PDF với
Đơn. data[note] của process đã nêu rõ chỗ này. Tờ khai thuế/lệ phí trước bạ đi dòng CHỨNG TỪ NGHĨA VỤ
TÀI CHÍNH (index 12) — cũng theo ánh xạ ảnh 03 (file tờ khai thuế -> Dòng 13).

Phân loại LLM-FIRST tuyệt đối: doc_type CHỈ lấy từ LLM, KHÔNG có nhánh rule keyword (giòn, dễ sai).
Không rõ/không hợp lệ -> đính CHUNG vào dòng Đơn đăng ký, KHÔNG bỏ file, giữ TÊN FILE GỐC + cảnh báo.
KHÔNG set Bản chính/Bản sao (loaiBan): cán bộ tự chọn.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON_DANG_KY = "don_dang_ky"
_AUTHORIZATION = "authorization"
_GIAY_TO_DIEU_137 = "giay_to_dieu_137"
_THUA_KE = "thua_ke"
_THUA_KE_CHUYEN_QUYEN = "thua_ke_chuyen_quyen"
_GIAO_DAT_KHONG_DUNG_THAM_QUYEN = "giao_dat_khong_dung_tham_quyen"
_XU_PHAT_HANH_CHINH = "xu_phat_hanh_chinh"
_THUA_DAT_LIEN_KE = "thua_dat_lien_ke"
_VAN_BAN_THANH_VIEN_HO_GIA_DINH = "van_ban_thanh_vien_ho_gia_dinh"
_MANH_TRICH_DO = "manh_trich_do"
_HO_SO_THIET_KE_XAY_DUNG = "ho_so_thiet_ke_xay_dung"
_QUYET_DINH_XU_PHAT = "quyet_dinh_xu_phat"
_CHUNG_TU_TAI_CHINH = "chung_tu_tai_chinh"
_TO_KHAI_THUE = "to_khai_thue"
_GIAY_TO_CHUYEN_QUYEN = "giay_to_chuyen_quyen"
_GIAY_XAC_NHAN_XAY_DUNG = "giay_xac_nhan_xay_dung"
_THOA_THUAN_CAP_CHUNG = "thoa_thuan_cap_chung"
_IDENTITY = "identity"
_XAC_NHAN_CMND_CCCD = "xac_nhan_cmnd_cccd"
_OTHER = "other"

# componentName lấy VERBATIM từ cột "Tên giấy tờ" của 'đki dâtd đai đính kèm.html'; mỗi chuỗi đã được
# soát chéo trên cả 20 dòng để chỉ khớp (hoặc khớp ĐẦU TIÊN) đúng dòng mong muốn.
_DON_DANG_KY_NAME = "Đơn đăng ký đất đai, tài sản gắn liền với đất"
_DON_DANG_KY_INDEX = 0
_CHUNG_TU_TAI_CHINH_NAME = "Chứng từ thực hiện nghĩa vụ tài chính"
_CHUNG_TU_TAI_CHINH_INDEX = 12

_ROUTES: dict[str, dict[str, Any]] = {
    _DON_DANG_KY: {
        "index": _DON_DANG_KY_INDEX,
        "name": _DON_DANG_KY_NAME,
        "documentName": "Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 15)",
    },
    _AUTHORIZATION: {
        "index": 1,
        "name": "Văn bản về việc đại diện theo quy định của pháp luật về dân sự",
        "documentName": "Văn bản đại diện/ủy quyền",
    },
    _GIAY_TO_DIEU_137: {
        # STT3 và STT17 trùng nhóm nội dung -> chỉ dòng chính STT3 (index 2).
        "index": 2,
        "name": "Điều 137, khoản 1, khoản 5 Điều 148",
        "documentName": "Giấy tờ về quyền sử dụng đất theo Điều 137",
    },
    _THUA_KE: {
        # STT4 và STT18 trùng nội dung -> chỉ dòng chính STT4 (index 3).
        "index": 3,
        "name": "nhận thừa kế quyền sử dụng đất chưa được cấp Giấy chứng nhận",
        "documentName": "Giấy tờ nhận thừa kế quyền sử dụng đất",
    },
    _THUA_KE_CHUYEN_QUYEN: {
        "index": 4,
        "name": "khoản 4 Điều 45 Luật Đất đai",
        "documentName": "Giấy tờ thừa kế kèm chuyển quyền (khoản 4 Điều 45)",
    },
    _GIAO_DAT_KHONG_DUNG_THAM_QUYEN: {
        "index": 5,
        "name": "Giấy tờ về giao đất không đúng thẩm quyền",
        "documentName": "Giấy tờ giao đất không đúng thẩm quyền/mua, thanh lý, hóa giá nhà ở",
    },
    _XU_PHAT_HANH_CHINH: {
        "index": 6,
        "name": "Giấy tờ liên quan đến xử phạt vi phạm hành chính",
        "documentName": "Giấy tờ liên quan xử phạt vi phạm hành chính về đất đai",
    },
    _THUA_DAT_LIEN_KE: {
        "index": 7,
        "name": "xác lập quyền đối với thửa đất liền kề",
        "documentName": "Giấy tờ xác lập quyền đối với thửa đất liền kề",
    },
    _VAN_BAN_THANH_VIEN_HO_GIA_DINH: {
        "index": 8,
        "name": "Văn bản xác định các thành viên có chung quyền sử dụng đất của hộ gia đình",
        "documentName": "Văn bản xác định thành viên hộ gia đình có chung QSDĐ",
    },
    _MANH_TRICH_DO: {
        "index": 9,
        "name": "Mảnh trích đo bản đồ địa chính thửa đất",
        "documentName": "Mảnh trích đo bản đồ địa chính thửa đất",
    },
    _HO_SO_THIET_KE_XAY_DUNG: {
        "index": 10,
        "name": "Hồ sơ thiết kế xây dựng công trình",
        "documentName": "Hồ sơ thiết kế xây dựng/nghiệm thu công trình",
    },
    _QUYET_DINH_XU_PHAT: {
        "index": 11,
        "name": "Quyết định xử phạt vi phạm hành chính trong lĩnh vực đất đai; chứng từ nộp phạt",
        "documentName": "Quyết định xử phạt VPHC và chứng từ nộp phạt",
    },
    _CHUNG_TU_TAI_CHINH: {
        "index": _CHUNG_TU_TAI_CHINH_INDEX,
        "name": _CHUNG_TU_TAI_CHINH_NAME,
        "documentName": "Chứng từ thực hiện nghĩa vụ tài chính",
    },
    # Tờ khai thuế/lệ phí trước bạ KHÔNG có dòng riêng; ảnh ánh xạ 03 xếp file tờ khai thuế vào Dòng
    # 13 (chứng từ nghĩa vụ tài chính) -> theo đúng ánh xạ đó, giữ documentName riêng để cán bộ soát.
    _TO_KHAI_THUE: {
        "index": _CHUNG_TU_TAI_CHINH_INDEX,
        "name": _CHUNG_TU_TAI_CHINH_NAME,
        "documentName": "Tờ khai thuế/lệ phí trước bạ",
    },
    _GIAY_TO_CHUYEN_QUYEN: {
        "index": 13,
        "name": "có chữ ký của bên chuyển quyền và bên nhận chuyển quyền",
        "documentName": "Giấy tờ chuyển quyền có chữ ký hai bên",
    },
    _GIAY_XAC_NHAN_XAY_DUNG: {
        "index": 14,
        "name": "Giấy xác nhận của cơ quan có chức năng quản lý về xây dựng cấp huyện",
        "documentName": "Giấy xác nhận đủ điều kiện tồn tại nhà ở, công trình xây dựng",
    },
    _THOA_THUAN_CAP_CHUNG: {
        # STT16 và STT19 trùng text (chỉ khác dấu chấm cuối) -> chỉ dòng chính STT16 (index 15).
        "index": 15,
        "name": "Văn bản thỏa thuận về việc cấp chung một Giấy chứng nhận",
        "documentName": "Văn bản thỏa thuận cấp chung một Giấy chứng nhận",
    },
    # Hai loại dưới KHÔNG có dòng riêng trong bảng 20 dòng -> gom CHUNG vào dòng ĐƠN ĐĂNG KÝ,
    # giữ documentName mô tả để cán bộ phân biệt trong cùng ô upload.
    _IDENTITY: {
        "index": _DON_DANG_KY_INDEX,
        "name": _DON_DANG_KY_NAME,
        "documentName": "Căn cước công dân",
    },
    _XAC_NHAN_CMND_CCCD: {
        "index": _DON_DANG_KY_INDEX,
        "name": _DON_DANG_KY_NAME,
        "documentName": "Giấy xác nhận số định danh cá nhân/số CMND 9 số",
    },
}
_ALLOWED = set(_ROUTES) | {_OTHER}


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


def _build_item(file: dict, file_index: int, doc_type: str) -> dict:
    route = _ROUTES[doc_type]
    return {
        "fileIndex": file_index,
        "fileName": str(file.get("name") or f"file-{file_index + 1}"),
        "documentName": route["documentName"],
        "componentName": route["name"],
        "componentIndex": route["index"],
        "target": "attp-row",
        "needsAddComponent": False,
        "detectedType": doc_type,
    }


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict] | None = None,
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    del ocr_results  # LLM-first: không dùng OCR text để suy luận rule ở đây.
    llm_types = llm_types or {}
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        llm_type = llm_types.get(index, "")
        # doc_type CHỈ lấy từ LLM; không có rule keyword fallback.
        doc_type = llm_type if llm_type in _ROUTES else _OTHER

        if doc_type in _ROUTES:
            item = _build_item(file, index, doc_type)
            attachments.append(item)
            classified.append({
                "fileName": file_name,
                "docType": doc_type,
                "source": "llm",
                "componentIndex": item["componentIndex"],
            })
            continue

        # Bảng KHÔNG có dòng "Giấy tờ khác" -> KHÔNG bỏ file (sẽ rớt), mà đính CHUNG vào dòng ĐƠN
        # ĐĂNG KÝ (index 0). Giữ TÊN FILE GỐC làm documentName để cán bộ nhận ra và soát lại.
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": file_name,
            "componentName": _DON_DANG_KY_NAME,
            "componentIndex": _DON_DANG_KY_INDEX,
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": _OTHER,
        })
        warnings.append(
            f"Chưa nhận diện chắc loại giấy tờ cho '{file_name}' — tạm đính vào dòng Đơn đăng ký "
            f"đất đai, tài sản gắn liền với đất; cán bộ kiểm tra lại."
        )
        source = "llm" if llm_type == _OTHER else "unknown"
        classified.append({
            "fileName": file_name,
            "docType": _OTHER,
            "source": source,
            "routedTo": _DON_DANG_KY_INDEX,
        })

    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
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

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types)
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

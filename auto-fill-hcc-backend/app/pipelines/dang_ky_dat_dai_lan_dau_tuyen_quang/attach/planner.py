"""Lập kế hoạch đính kèm vào 20 dòng thành phần hồ sơ trên cổng iGate Tuyên Quang (1.013978) — chung cho ba form.

Bảng có sẵn 20 dòng (mat-checkbox + radio Bản chính/Bản sao + "Chọn tệp tin", engine FE `attp-row`), tên dòng lấy
nguyên văn từ file mapping Mapping_Cap_GCN_lan_dau (ba sheet cùng một bảng). Thứ tự KHÁC bản Khánh Hòa cùng mã thủ tục
— Đơn đăng ký nằm ở dòng 16. componentIndex = STT (đếm từ 1): FE tìm `rows[componentIndex - 1]` trước rồi mới so tên,
nên dòng lặp danh mục (13 / 20) vẫn giữ file ở đúng dòng chính. componentName là đoạn chữ đặc trưng của dòng:

  dòng 1 : Chứng từ thực hiện nghĩa vụ tài chính                    -> chung_tu_tai_chinh, to_khai_thue
  dòng 2 : Giấy tờ liên quan đến xử phạt vi phạm hành chính         -> xu_phat_hanh_chinh
  dòng 3 : Giao đất không đúng thẩm quyền / mua, thanh lý, hóa giá  -> giao_dat_khong_dung_tham_quyen
  dòng 4 : Giấy tờ chuyển quyền có chữ ký hai bên                   -> giay_to_chuyen_quyen
  dòng 5 : Thừa kế + chuyển quyền theo khoản 4 Điều 45              -> thua_ke_chuyen_quyen
  dòng 6 : Thừa kế QSDĐ chưa được cấp Giấy chứng nhận               -> thua_ke
  dòng 7 : Giấy xác nhận của cơ quan quản lý xây dựng cấp huyện     -> giay_xac_nhan_xay_dung
  dòng 8 : Hồ sơ thiết kế xây dựng công trình                       -> ho_so_thiet_ke_xay_dung
  dòng 9 : Xác lập quyền đối với thửa đất liền kề                   -> thua_dat_lien_ke
  dòng 10: Mảnh trích đo bản đồ địa chính thửa đất                  -> manh_trich_do
  dòng 11: Giấy tờ Điều 137, khoản 1/khoản 5 Điều 148, 149          -> giay_to_dieu_137
  dòng 12: Quyết định xử phạt VPHC + chứng từ nộp phạt              -> quyet_dinh_xu_phat
  dòng 13: Văn bản thỏa thuận cấp chung một Giấy chứng nhận         -> thoa_thuan_cap_chung
  dòng 14: Văn bản về việc đại diện theo pháp luật dân sự           -> authorization
  dòng 15: Văn bản xác định thành viên chung QSDĐ của hộ gia đình   -> van_ban_thanh_vien_ho_gia_dinh
  dòng 16: Đơn đăng ký đất đai, tài sản gắn liền với đất            -> don_dang_ky (+ CCCD, giấy khai sinh)
  dòng 17: Thông báo xác nhận kết quả đăng ký đất đai               -> KHÔNG route (cơ quan phát hành sau)
  dòng 18: TRÙNG dòng 6 (bản rút gọn)                               -> BỎ
  dòng 19: TRÙNG NHÓM dòng 11 (khoản 4 thay khoản 1)                -> BỎ
  dòng 20: TRÙNG dòng 13 (chỉ thêm dấu chấm cuối)                   -> BỎ

MỖI FILE ĐÍNH NGUYÊN KHỐI, MỘT LẦN, KHÔNG TÁCH TRANG (ánh xạ hồ sơ của thủ tục): file Đơn gộp tờ khai lệ phí trước bạ
+ tờ khai thuế TNCN đính nguyên ở dòng 16; file gộp giấy chuyển nhượng + đơn xin làm nhà cũ + giấy khai sinh đính
nguyên ở dòng 4; file phiếu đo đạc + bản mô tả ranh giới + mảnh trích đo ở dòng 10. LLM liệt kê MỌI loại giấy trong
file, planner chọn dòng theo _PRIORITY (tất định) rồi cảnh báo những giấy có dòng riêng mà nằm chung file. Bản chưa ký
số đã có bản ký số cùng tên ("DON.pdf" + "DON.signed.pdf") không đính lại. KHÔNG set Bản chính/Bản sao: cổng để sẵn
Bản chính, cán bộ tự đổi.

OCR phân loại như đăng ký đất đai lần đầu Khánh Hòa: chữ đủ trang từ cache bước điền, chưa có cache thì vài trang
đầu; chữ gửi LLM là trích đoạn đầu TỪNG trang để file gộp 10+ trang vẫn lộ đủ các giấy ở trang sau.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.documents import representative_excerpt
from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.attach.planner import _LLM_TEXT_MAX_CHARS, _ocr_for_classify
from app.process.schemas import FileItem
from app.services.llm import client

from ..process.runner import unsigned_copies
from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON_DANG_KY = "don_dang_ky"
_AUTHORIZATION = "authorization"
_GIAY_TO_CHUYEN_QUYEN = "giay_to_chuyen_quyen"
_THUA_KE = "thua_ke"
_THUA_KE_CHUYEN_QUYEN = "thua_ke_chuyen_quyen"
_GIAO_DAT_KHONG_DUNG_THAM_QUYEN = "giao_dat_khong_dung_tham_quyen"
_GIAY_TO_DIEU_137 = "giay_to_dieu_137"
_THUA_DAT_LIEN_KE = "thua_dat_lien_ke"
_VAN_BAN_THANH_VIEN_HO_GIA_DINH = "van_ban_thanh_vien_ho_gia_dinh"
_THOA_THUAN_CAP_CHUNG = "thoa_thuan_cap_chung"
_MANH_TRICH_DO = "manh_trich_do"
_HO_SO_THIET_KE_XAY_DUNG = "ho_so_thiet_ke_xay_dung"
_GIAY_XAC_NHAN_XAY_DUNG = "giay_xac_nhan_xay_dung"
_XU_PHAT_HANH_CHINH = "xu_phat_hanh_chinh"
_QUYET_DINH_XU_PHAT = "quyet_dinh_xu_phat"
_CHUNG_TU_TAI_CHINH = "chung_tu_tai_chinh"
_TO_KHAI_THUE = "to_khai_thue"
_IDENTITY = "identity"
_XAC_NHAN_CMND_CCCD = "xac_nhan_cmnd_cccd"
_OTHER = "other"

_DON_ROW = 16

# STT -> đoạn chữ đặc trưng của cột "Tên giấy tờ" (FE khớp substring sau khi fold dấu). Dòng 17-20 không khai.
_ROW_NAMES: dict[int, str] = {
    1: "Chứng từ thực hiện nghĩa vụ tài chính, giấy tờ liên quan đến việc miễn, giảm nghĩa vụ tài chính",
    2: "Giấy tờ liên quan đến xử phạt vi phạm hành chính trong lĩnh vực đất đai",
    3: "Giấy tờ về giao đất không đúng thẩm quyền",
    4: "có chữ ký của bên chuyển quyền và bên nhận chuyển quyền",
    5: "khoản 4 Điều 45 Luật Đất đai",
    6: "nhận thừa kế quyền sử dụng đất chưa được cấp Giấy chứng nhận",
    7: "Giấy xác nhận của cơ quan có chức năng quản lý về xây dựng cấp huyện",
    8: "Hồ sơ thiết kế xây dựng công trình",
    9: "xác lập quyền đối với thửa đất liền kề",
    10: "Mảnh trích đo bản đồ địa chính thửa đất",
    11: "Điều 137, khoản 1, khoản 5 Điều 148",
    12: "Quyết định xử phạt vi phạm hành chính trong lĩnh vực đất đai; chứng từ nộp phạt",
    13: "Văn bản thỏa thuận về việc cấp chung một Giấy chứng nhận",
    14: "Văn bản về việc đại diện theo quy định của pháp luật về dân sự",
    15: "Văn bản xác định các thành viên có chung quyền sử dụng đất của hộ gia đình",
    _DON_ROW: "Đơn đăng ký đất đai, tài sản gắn liền với đất",
}

# Loại giấy -> (dòng, tên tài liệu hiện trên cổng).
_ROUTES: dict[str, tuple[int, str]] = {
    _CHUNG_TU_TAI_CHINH: (1, "Chứng từ thực hiện nghĩa vụ tài chính"),
    _TO_KHAI_THUE: (1, "Tờ khai lệ phí trước bạ/thuế thu nhập cá nhân"),
    _XU_PHAT_HANH_CHINH: (2, "Giấy tờ liên quan xử phạt vi phạm hành chính về đất đai"),
    _GIAO_DAT_KHONG_DUNG_THAM_QUYEN: (3, "Giấy tờ giao đất không đúng thẩm quyền/mua, thanh lý, hóa giá nhà ở"),
    _GIAY_TO_CHUYEN_QUYEN: (4, "Giấy tờ chuyển quyền có chữ ký hai bên"),
    _THUA_KE_CHUYEN_QUYEN: (5, "Giấy tờ thừa kế kèm chuyển quyền (khoản 4 Điều 45)"),
    _THUA_KE: (6, "Giấy tờ nhận thừa kế quyền sử dụng đất"),
    _GIAY_XAC_NHAN_XAY_DUNG: (7, "Giấy xác nhận đủ điều kiện tồn tại nhà ở, công trình xây dựng"),
    _HO_SO_THIET_KE_XAY_DUNG: (8, "Hồ sơ thiết kế xây dựng/nghiệm thu công trình"),
    _THUA_DAT_LIEN_KE: (9, "Giấy tờ xác lập quyền đối với thửa đất liền kề"),
    _MANH_TRICH_DO: (10, "Mảnh trích đo/phiếu đo đạc, bản mô tả ranh giới thửa đất"),
    _GIAY_TO_DIEU_137: (11, "Giấy tờ về quyền sử dụng đất theo Điều 137"),
    _QUYET_DINH_XU_PHAT: (12, "Quyết định xử phạt VPHC và chứng từ nộp phạt"),
    _THOA_THUAN_CAP_CHUNG: (13, "Văn bản thỏa thuận cấp chung một Giấy chứng nhận"),
    _AUTHORIZATION: (14, "Văn bản đại diện/ủy quyền"),
    _VAN_BAN_THANH_VIEN_HO_GIA_DINH: (15, "Văn bản xác định thành viên hộ gia đình có chung QSDĐ"),
    _DON_DANG_KY: (_DON_ROW, "Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 19)"),
    # Bảng không có dòng riêng cho giấy tờ nhân thân -> đính chung dòng Đơn, documentName để cán bộ phân biệt.
    _IDENTITY: (_DON_ROW, "Giấy tờ nhân thân (CCCD/giấy khai sinh)"),
    _XAC_NHAN_CMND_CCCD: (_DON_ROW, "Giấy xác nhận số định danh cá nhân/số CMND 9 số"),
}

# File gộp nhiều giấy: dòng của giấy ĐỨNG TRƯỚC trong danh sách này nhận nguyên file. Đơn luôn thắng (tờ khai đi kèm
# đơn ở lại dòng Đơn); giấy tờ nguồn gốc đất (chuyển quyền, thừa kế, Điều 137) đứng trước giấy đo đạc và giấy nhân thân.
_PRIORITY: tuple[str, ...] = (
    _DON_DANG_KY,
    _GIAY_TO_CHUYEN_QUYEN,
    _THUA_KE_CHUYEN_QUYEN,
    _THUA_KE,
    _GIAO_DAT_KHONG_DUNG_THAM_QUYEN,
    _GIAY_TO_DIEU_137,
    _THOA_THUAN_CAP_CHUNG,
    _VAN_BAN_THANH_VIEN_HO_GIA_DINH,
    _THUA_DAT_LIEN_KE,
    _AUTHORIZATION,
    _MANH_TRICH_DO,
    _GIAY_XAC_NHAN_XAY_DUNG,
    _HO_SO_THIET_KE_XAY_DUNG,
    _QUYET_DINH_XU_PHAT,
    _XU_PHAT_HANH_CHINH,
    _CHUNG_TU_TAI_CHINH,
    _TO_KHAI_THUE,
    _IDENTITY,
    _XAC_NHAN_CMND_CCCD,
)
_ALLOWED = set(_ROUTES) | {_OTHER}


def _normalize_doc_type(value: Any) -> str:
    folded = _fold(str(value or ""))
    for doc_type in _ALLOWED:
        if folded == _fold(doc_type):
            return doc_type
    return _OTHER


def _doc_types(item: dict) -> list[str]:
    raw = item.get("docTypes")
    if raw is None:
        raw = item.get("docType") or item.get("type")
    if not isinstance(raw, list):
        raw = [raw]
    out: list[str] = []
    for value in raw:
        doc_type = _normalize_doc_type(value)
        if doc_type not in out:
            out.append(doc_type)
    return out


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
            result[int(item.get("index"))] = _doc_types(item)
        except (TypeError, ValueError, AttributeError):
            continue
    return result


def _item(file_index: int, file_name: str, row: int, document_name: str, doc_type: str) -> dict:
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": _ROW_NAMES[row],
        "componentIndex": row,
        "target": "attp-row",
        "needsAddComponent": False,
        "detectedType": doc_type,
    }


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict] | None = None,
    llm_types: dict[int, list[str] | str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    del ocr_results  # LLM-first: không suy luận rule từ OCR text ở đây.
    llm_types = llm_types or {}
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    twins = unsigned_copies(files)

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        if index in twins:
            signed_name = str(files[twins[index]].get("name") or "")
            warnings.append(f"'{file_name}' trùng bản ký số '{signed_name}' — không đính lại, chỉ đính bản ký số.")
            classified.append({"fileName": file_name, "docType": "duplicate", "docTypes": [], "source": "name",
                               "duplicateOf": signed_name})
            continue
        raw_types = llm_types.get(index)
        doc_types = _doc_types({"docTypes": raw_types}) if raw_types else []
        doc_type = next((item for item in _PRIORITY if item in doc_types), _OTHER)

        if doc_type == _OTHER:
            # Không nhận diện được: không bỏ file mà đính chung dòng Đơn, giữ TÊN FILE GỐC để cán bộ soát lại.
            attachments.append(_item(index, file_name, _DON_ROW, file_name, _OTHER))
            warnings.append(
                f"Chưa nhận diện chắc loại giấy tờ cho '{file_name}' — tạm đính vào dòng {_DON_ROW} (Đơn đăng ký "
                f"đất đai, tài sản gắn liền với đất); cán bộ kiểm tra lại."
            )
            classified.append({"fileName": file_name, "docType": _OTHER, "docTypes": doc_types,
                               "source": "llm" if raw_types else "unknown", "rows": [_DON_ROW]})
            continue

        row, document_name = _ROUTES[doc_type]
        attachments.append(_item(index, file_name, row, document_name, doc_type))
        classified.append({"fileName": file_name, "docType": doc_type, "docTypes": doc_types, "source": "llm",
                           "rows": [row]})
        # Giấy có dòng RIÊNG nhưng nằm chung file với giấy chính: đính nguyên file một lần, báo cán bộ đừng đính lại
        # ở dòng kia. Giấy nhân thân không có dòng riêng (về dòng Đơn) nên không cần báo.
        bundled = {_ROUTES[other][0]: _ROUTES[other][1] for other in doc_types
                   if other in _ROUTES and _ROUTES[other][0] not in (row, _DON_ROW)}
        if bundled:
            rows = "; ".join(f"{name} (dòng {stt})" for stt, name in sorted(bundled.items()))
            warnings.append(
                f"'{file_name}' gộp nhiều giấy tờ — đính nguyên file ở dòng {row} ({document_name}), không tách "
                f"sang: {rows}."
            )

    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    twins = unsigned_copies(raw_files)
    # Bản chưa ký số không đính nên không OCR / phân loại.
    ocr_files = [item for index, item in enumerate(raw_files) if item.get("type") in _OCR_TYPES and index not in twins]
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
        if index not in twins and str(by_name.get(file.get("name"), {}).get("text") or "").strip()
    ]
    started = time.monotonic()
    llm_types: dict[int, list[str]] = {}
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

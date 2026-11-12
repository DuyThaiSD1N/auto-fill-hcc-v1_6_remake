"""Lập kế hoạch đính kèm vào 20 dòng thành phần hồ sơ trên cổng iGate Khánh Hòa (1.013978).

Bảng có sẵn 20 dòng (mat-checkbox + radio Bản chính/Bản sao + "Chọn tệp tin", engine FE `attp-row`), thứ tự KHÁC
Quảng Ngãi cùng mã thủ tục — Đơn đăng ký nằm ở dòng 19, không phải dòng 1. componentIndex = STT − 1;
componentName là đoạn chữ đặc trưng của cột "Tên giấy tờ" (FE khớp substring sau khi fold dấu):

  index 0  (STT1) : Giấy tờ chuyển quyền có chữ ký hai bên                -> giay_to_chuyen_quyen
  index 1  (STT2) : Chứng từ thực hiện nghĩa vụ tài chính                  -> chung_tu_tai_chinh, to_khai_thue
  index 2  (STT3) : Xác lập quyền đối với thửa đất liền kề                 -> thua_dat_lien_ke
  index 3  (STT4) : Giấy tờ liên quan đến xử phạt vi phạm hành chính       -> xu_phat_hanh_chinh
  index 4  (STT5) : Văn bản xác định thành viên chung QSDĐ của hộ gia đình -> van_ban_thanh_vien_ho_gia_dinh
  index 5  (STT6) : Thừa kế + chuyển quyền theo khoản 4 Điều 45            -> thua_ke_chuyen_quyen
  index 6  (STT7) : Giấy tờ Điều 137, khoản 1/khoản 5 Điều 148, 149        -> giay_to_dieu_137
  index 7  (STT8) : Mảnh trích đo bản đồ địa chính thửa đất                -> manh_trich_do
  index 8  (STT9) : Hồ sơ thiết kế xây dựng công trình                     -> ho_so_thiet_ke_xay_dung
  index 9  (STT10): Giao đất không đúng thẩm quyền/mua, thanh lý, hóa giá  -> giao_dat_khong_dung_tham_quyen
  index 10 (STT11): Thừa kế QSDĐ chưa được cấp Giấy chứng nhận             -> thua_ke
  index 11 (STT12): Quyết định xử phạt VPHC + chứng từ nộp phạt            -> quyet_dinh_xu_phat
  index 12 (STT13): Giấy xác nhận của cơ quan quản lý xây dựng cấp huyện   -> giay_xac_nhan_xay_dung
  index 13 (STT14): Văn bản thỏa thuận cấp chung một Giấy chứng nhận       -> thoa_thuan_cap_chung
  index 14 (STT15): TRÙNG dòng STT14 (chỉ thừa dấu chấm cuối)              -> BỎ
  index 15 (STT16): TRÙNG NHÓM dòng STT7 (khoản 4 thay khoản 1)            -> BỎ
  index 16 (STT17): TRÙNG dòng STT11 (bản rút gọn)                         -> BỎ
  index 17 (STT18): Văn bản về việc đại diện theo pháp luật dân sự         -> authorization
  index 18 (STT19): Đơn đăng ký đất đai, tài sản gắn liền với đất          -> don_dang_ky (+ CCCD, giấy khai sinh)
  index 19 (STT20): Thông báo xác nhận kết quả đăng ký đất đai             -> KHÔNG route (cơ quan phát hành sau)

MẶC ĐỊNH MỖI FILE ĐÍNH NGUYÊN KHỐI, KHÔNG TÁCH TRANG (theo ánh xạ hồ sơ của thủ tục; bật "Có tách hồ sơ khi đính
kèm" thì tách — xem plan_theo_cai_dat_tach): file Đơn gộp kèm tờ khai lệ phí trước
bạ + tờ khai thuế TNCN đính nguyên ở dòng Đơn; file gộp hợp đồng chuyển nhượng + đơn xin làm nhà cũ + giấy khai
sinh đính nguyên ở dòng giấy tờ chuyển quyền. LLM liệt kê MỌI loại giấy có trong file, planner chọn dòng theo
_PRIORITY (tất định) rồi cảnh báo những giấy có dòng riêng mà nằm chung file, để cán bộ biết không đính lại.

OCR phân loại: lấy chữ ĐỦ TRANG từ cache OCR của bước điền (khóa theo nội dung file); file chưa có cache mới OCR
_OCR_MAX_PAGES trang đầu (PDF scan gộp 10-25 trang OCR đủ sẽ quá timeout 100s của extension).
KHÔNG set Bản chính/Bản sao: cán bộ tự chọn.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.kinh_doanh_tach_giay_to import split_requested
from app.pipelines._shared.khanh_hoa_tach_giay_to import plan_with_split
from app.process.schemas import FileItem
from app.services.llm import client
from app.services.pdf_utils import trim_files_for_classify

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_OCR_MAX_PAGES = 2
_LLM_TEXT_MAX_CHARS = 12000

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

_DON_DANG_KY_NAME = "Đơn đăng ký đất đai, tài sản gắn liền với đất"
_DON_DANG_KY_INDEX = 18
_CHUNG_TU_TAI_CHINH_NAME = "Chứng từ thực hiện nghĩa vụ tài chính"
_CHUNG_TU_TAI_CHINH_INDEX = 1

_ROUTES: dict[str, dict[str, Any]] = {
    _GIAY_TO_CHUYEN_QUYEN: {
        "index": 0,
        "name": "có chữ ký của bên chuyển quyền và bên nhận chuyển quyền",
        "documentName": "Giấy tờ chuyển quyền có chữ ký hai bên",
    },
    _CHUNG_TU_TAI_CHINH: {
        "index": _CHUNG_TU_TAI_CHINH_INDEX,
        "name": _CHUNG_TU_TAI_CHINH_NAME,
        "documentName": "Chứng từ thực hiện nghĩa vụ tài chính",
    },
    _TO_KHAI_THUE: {
        "index": _CHUNG_TU_TAI_CHINH_INDEX,
        "name": _CHUNG_TU_TAI_CHINH_NAME,
        "documentName": "Tờ khai lệ phí trước bạ/thuế thu nhập cá nhân",
    },
    _THUA_DAT_LIEN_KE: {
        "index": 2,
        "name": "xác lập quyền đối với thửa đất liền kề",
        "documentName": "Giấy tờ xác lập quyền đối với thửa đất liền kề",
    },
    _XU_PHAT_HANH_CHINH: {
        "index": 3,
        "name": "Giấy tờ liên quan đến xử phạt vi phạm hành chính",
        "documentName": "Giấy tờ liên quan xử phạt vi phạm hành chính về đất đai",
    },
    _VAN_BAN_THANH_VIEN_HO_GIA_DINH: {
        "index": 4,
        "name": "Văn bản xác định các thành viên có chung quyền sử dụng đất của hộ gia đình",
        "documentName": "Văn bản xác định thành viên hộ gia đình có chung QSDĐ",
    },
    _THUA_KE_CHUYEN_QUYEN: {
        "index": 5,
        "name": "khoản 4 Điều 45 Luật Đất đai",
        "documentName": "Giấy tờ thừa kế kèm chuyển quyền (khoản 4 Điều 45)",
    },
    _GIAY_TO_DIEU_137: {
        # STT7 và STT16 cùng nhóm Điều 137 (khoản 1 vs khoản 4) -> chỉ dòng chính STT7.
        "index": 6,
        "name": "Điều 137, khoản 1, khoản 5 Điều 148",
        "documentName": "Giấy tờ về quyền sử dụng đất theo Điều 137",
    },
    _MANH_TRICH_DO: {
        "index": 7,
        "name": "Mảnh trích đo bản đồ địa chính thửa đất",
        "documentName": "Mảnh trích đo/phiếu đo đạc, bản mô tả ranh giới thửa đất",
    },
    _HO_SO_THIET_KE_XAY_DUNG: {
        "index": 8,
        "name": "Hồ sơ thiết kế xây dựng công trình",
        "documentName": "Hồ sơ thiết kế xây dựng/nghiệm thu công trình",
    },
    _GIAO_DAT_KHONG_DUNG_THAM_QUYEN: {
        "index": 9,
        "name": "Giấy tờ về giao đất không đúng thẩm quyền",
        "documentName": "Giấy tờ giao đất không đúng thẩm quyền/mua, thanh lý, hóa giá nhà ở",
    },
    _THUA_KE: {
        # STT11 và STT17 trùng nội dung -> chỉ dòng chính STT11.
        "index": 10,
        "name": "nhận thừa kế quyền sử dụng đất chưa được cấp Giấy chứng nhận",
        "documentName": "Giấy tờ nhận thừa kế quyền sử dụng đất",
    },
    _QUYET_DINH_XU_PHAT: {
        "index": 11,
        "name": "Quyết định xử phạt vi phạm hành chính trong lĩnh vực đất đai; chứng từ nộp phạt",
        "documentName": "Quyết định xử phạt VPHC và chứng từ nộp phạt",
    },
    _GIAY_XAC_NHAN_XAY_DUNG: {
        "index": 12,
        "name": "Giấy xác nhận của cơ quan có chức năng quản lý về xây dựng cấp huyện",
        "documentName": "Giấy xác nhận đủ điều kiện tồn tại nhà ở, công trình xây dựng",
    },
    _THOA_THUAN_CAP_CHUNG: {
        # STT14 và STT15 chỉ khác dấu chấm cuối; FE lấy dòng khớp ĐẦU TIÊN = STT14.
        "index": 13,
        "name": "Văn bản thỏa thuận về việc cấp chung một Giấy chứng nhận",
        "documentName": "Văn bản thỏa thuận cấp chung một Giấy chứng nhận",
    },
    _AUTHORIZATION: {
        "index": 17,
        "name": "Văn bản về việc đại diện theo quy định của pháp luật về dân sự",
        "documentName": "Văn bản đại diện/ủy quyền",
    },
    _DON_DANG_KY: {
        "index": _DON_DANG_KY_INDEX,
        "name": _DON_DANG_KY_NAME,
        "documentName": "Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 19)",
    },
    # Bảng không có dòng riêng cho giấy tờ nhân thân -> đính chung dòng Đơn, documentName để cán bộ phân biệt.
    _IDENTITY: {
        "index": _DON_DANG_KY_INDEX,
        "name": _DON_DANG_KY_NAME,
        "documentName": "Giấy tờ nhân thân (CCCD/giấy khai sinh)",
    },
    _XAC_NHAN_CMND_CCCD: {
        "index": _DON_DANG_KY_INDEX,
        "name": _DON_DANG_KY_NAME,
        "documentName": "Giấy xác nhận số định danh cá nhân/số CMND 9 số",
    },
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


def _primary(doc_types: list[str]) -> str:
    for doc_type in _PRIORITY:
        if doc_type in doc_types:
            return doc_type
    return _OTHER


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

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        raw_types = llm_types.get(index)
        doc_types = _doc_types({"docTypes": raw_types}) if raw_types else []
        doc_type = _primary(doc_types)

        if doc_type in _ROUTES:
            route = _ROUTES[doc_type]
            attachments.append({
                "fileIndex": index,
                "fileName": file_name,
                "documentName": route["documentName"],
                "componentName": route["name"],
                "componentIndex": route["index"],
                "target": "attp-row",
                "needsAddComponent": False,
                "detectedType": doc_type,
            })
            classified.append({
                "fileName": file_name,
                "docType": doc_type,
                "docTypes": doc_types,
                "source": "llm",
                "componentIndex": route["index"],
            })
            # Giấy có dòng RIÊNG nhưng nằm chung file với giấy chính: đính nguyên file một lần, báo cán bộ đừng
            # đính lại ở dòng kia. Giấy nhân thân không có dòng riêng nên không cần báo.
            bundled = [
                _ROUTES[other] for other in doc_types
                if other in _ROUTES and _ROUTES[other]["index"] not in (route["index"], _DON_DANG_KY_INDEX)
            ]
            if bundled:
                rows = "; ".join(
                    f"{item['documentName']} (dòng {item['index'] + 1})"
                    for item in {item["index"]: item for item in bundled}.values()
                )
                warnings.append(
                    f"'{file_name}' gộp nhiều giấy tờ — đính nguyên file ở dòng {route['index'] + 1} "
                    f"({route['documentName']}), không tách sang: {rows}."
                )
            continue

        # Không nhận diện được: không bỏ file mà đính chung dòng Đơn, giữ TÊN FILE GỐC để cán bộ soát lại.
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
            f"Chưa nhận diện chắc loại giấy tờ cho '{file_name}' — tạm đính vào dòng {_DON_DANG_KY_INDEX + 1} "
            f"(Đơn đăng ký đất đai, tài sản gắn liền với đất); cán bộ kiểm tra lại."
        )
        classified.append({
            "fileName": file_name,
            "docType": _OTHER,
            "docTypes": doc_types,
            "source": "llm" if raw_types else "unknown",
            "routedTo": _DON_DANG_KY_INDEX,
        })

    return attachments, warnings, classified


async def _ocr_for_classify(files: list[dict]) -> list[dict]:
    """Chữ OCR để phân loại: đủ trang nếu bước điền đã OCR đúng file đó (cache), không thì vài trang đầu.

    Đoạn trang do bộ tách giấy tờ cắt ra đã có chữ nạp sẵn (ocr.preset_texts) → dùng luôn, không OCR lần hai."""
    from app.services import ocr, ocr_cache

    keys = [ocr_cache.content_key(item.get("dataUrl") or "") for item in files]
    cached = await ocr_cache.get_many([key for key in keys if key])
    results: list[dict | None] = []
    misses: list[dict] = []
    for item, key in zip(files, keys):
        preset = ocr.preset_text(item.get("dataUrl") or "")
        if preset and preset.strip():
            results.append({"name": item.get("name"), "type": item.get("type"), "text": preset, "provider": "tiengnoi"})
            continue
        hit = cached.get(key) if key else None
        text = str((hit or {}).get("text") or "")
        if hit and hit.get("provider") == "tiengnoi" and text.strip():
            results.append({"name": item.get("name"), "type": item.get("type"), "text": text, "provider": "tiengnoi"})
        else:
            results.append(None)
            misses.append(item)
    fresh = iter(await ocr.ocr_per_file(trim_files_for_classify(misses, _OCR_MAX_PAGES)) if misses else [])
    return [item if item is not None else next(fresh) for item in results]


async def plan_theo_cai_dat_tach(plan_fn, files: list[FileItem], options: dict | None = None,
                                 session: dict | None = None) -> dict:
    """Chung cho 7 thủ tục đất đai iGate Khánh Hòa.

    Cài đặt "Có tách hồ sơ khi đính kèm" (``options.splitDocuments`` là boolean true, engine cắt được trang) → OCR
    tệp gốc, LLM chỉ ra trang mở giấy mới, cắt PDF gộp thành từng giấy rồi chạy ``plan_fn`` trên các giấy đã cắt
    (mỗi giấy vào dòng của nó, extension cắt trang theo ``sourceSegments``). Không bật → đính nguyên tệp như cũ.
    """
    if split_requested(options):
        return await plan_with_split(plan_fn, files, options, session)
    return await plan_fn(files, options, session)


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    return await plan_theo_cai_dat_tach(_plan_theo_tep, files, options, session)


async def _plan_theo_tep(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
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
        {"index": index, "text": str(by_name.get(file.get("name"), {}).get("text") or "")[:_LLM_TEXT_MAX_CHARS]}
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

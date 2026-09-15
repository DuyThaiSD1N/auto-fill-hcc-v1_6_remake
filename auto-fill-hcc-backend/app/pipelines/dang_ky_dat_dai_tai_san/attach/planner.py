"""Đính kèm cho [Lai Châu] Đăng ký đất đai, tài sản gắn liền với đất, cấp GCN lần đầu (1.013978).

Cổng dichvucong.laichau.gov.vn — eForm Lai Châu, bước 3 "Thông tin hồ sơ" là BẢNG 20 DÒNG cố định,
mỗi dòng một loại giấy tờ kèm sẵn một ``input[type=file]``. Đây là cùng khuôn với thủ tục
``dinh_chinh_sai_sot`` (Lai Châu) nên dùng ĐÚNG engine đó: ``target="fixed-slot"`` + ``slotIndex``.

``slotIndex`` là vị trí 0-BASED trong danh sách ô upload của trang (extension lấy
``fixedSlotUploadInputs()[item.slotIndex]``), tức dòng STT n trên giao diện -> slotIndex n-1. Đã đếm
trên 'đính kèm lai châu.html': đúng 20 input file nằm trong bảng theo đúng thứ tự dòng, 4 input
"giấy tờ khác" nằm SAU nên không làm lệch index. ``componentName`` lấy VERBATIM cột "Tên giấy tờ".

Phân loại LLM-FIRST tuyệt đối: docType CHỈ lấy từ LLM, KHÔNG có nhánh rule keyword (tên giấy tờ đất
đai quá dài/trùng lặp nên keyword sai nhiều hơn đúng). File không nhận diện được -> "other" nhưng
KHÔNG bị rớt: đính vào dòng 1 (Đơn đăng ký) kèm cảnh báo để cán bộ tự chuyển dòng.

Định tuyến chốt theo ẢNH ÁNH XẠ 'Anh_xa_thanh_phan_ho_so_HS1_HS2.png' (2 bộ hồ sơ mẫu thật):
  - Đơn Mẫu 13/Mẫu 15 + danh sách người sử dụng chung Mẫu 13a -> DÒNG 1 (13a là phụ lục của Đơn,
    KHÔNG phải văn bản thỏa thuận cấp chung ở dòng 17);
  - sơ đồ/bản trích lục/mảnh trích đo + bản mô tả ranh giới mốc giới + GCN của THỬA LIỀN KỀ (nộp để
    đối chiếu ranh giới) -> DÒNG 5, cả ba không có dòng riêng trên cổng;
  - giấy tờ chuyển quyền + bản cam kết nguồn gốc đất -> DÒNG 8;
  - GCN cấp cho phần diện tích tăng thêm -> DÒNG 12 (dự phòng, chỉ khi hồ sơ có diện tích tăng thêm).

RÀNG BUỘC CỔNG: "Tệp tin tải lên có dung lượng không quá 6MB". Planner KHÔNG tự tách file được nên
file vượt ngưỡng bị loại khỏi kế hoạch kèm cảnh báo nêu rõ phải tách nhỏ (hồ sơ mẫu HS2 có 1 file
11,2 MB đã phải tách thành 4 file theo từng giấy tờ).

Cột "Số bản (*)": ảnh ánh xạ chốt = 1 cho mọi dòng được tích. Engine fixed-slot của extension KHÔNG
điền ô số bản (cổng đã để sẵn 1) nên planner cũng không phát khóa nào cho nó.
"""

import re
import time
from pathlib import Path
from typing import Any

from app.config import settings
from app.pipelines._shared import fold, normalize_document_name
from app.pipelines._shared.documents import join_ocr_documents
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_MAX_FILE_BYTES = 6 * 1024 * 1024

_OTHER = "other"

# 20 dòng thành phần hồ sơ — slotName lấy VERBATIM cột "Tên giấy tờ" của 'đính kèm lai châu.html'.
_ROW_NAMES: list[str] = [
    "Mẫu số 13. Đơn đăng ký đất đai, tài sản gắn liền với đất (Bản chính)",
    "Thông báo xác nhận kết quả đăng ký đất đai (Bản chính)",
    "Hợp đồng hoặc văn bản thỏa thuận hoặc quyết định của Tòa án nhân dân về việc xác lập quyền đối "
    "với thửa đất liền kề kèm theo sơ đồ thể hiện vị trí, kích thước phần diện tích thửa đất liền kề "
    "được quyền sử dụng hạn chế đối với trường hợp có đăng ký quyền đối với thửa đất liền kề (Bản chính)",
    "Văn bản xác định các thành viên có chung quyền sử dụng đất của hộ gia đình đang sử dụng đất đối "
    "với trường hợp hộ gia đình đang sử dụng đất (Bản chính)",
    "Sơ đồ hoặc bản trích lục bản đồ địa chính hoặc mảnh trích đo bản đồ địa chính thửa đất (nếu có) "
    "(Bản chính)",
    "Quyết định xử phạt vi phạm hành chính trong lĩnh vực đất đai; chứng từ nộp phạt của người sử "
    "dụng đất đối với trường hợp quy định tại điểm a khoản 6 Điều 25 Nghị định số 101/2024/NĐ-CP "
    "(Bản chính)",
    "Chứng từ thực hiện nghĩa vụ tài chính, giấy tờ liên quan đến việc miễn, giảm nghĩa vụ tài chính "
    "về đất đai, tài sản gắn liền với đất (nếu có) (Bản chính)",
    "Giấy tờ về việc chuyển quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất có chữ ký của "
    "bên chuyển quyền và bên nhận chuyển quyền đối với trường hợp nhận chuyển quyền sử dụng đất, "
    "quyền sở hữu nhà ở, công trình xây dựng mà chưa thực hiện thủ tục chuyển quyền theo quy định "
    "của pháp luật (Bản chính)",
    "Giấy xác nhận của cơ quan có chức năng quản lý về xây dựng cấp huyện trước ngày 01 tháng 7 năm "
    "2025 về đủ điều kiện tồn tại nhà ở, công trình xây dựng đó theo quy định của pháp luật về xây "
    "dựng đối với trường hợp hộ gia đình, cá nhân có nhu cầu cấp Giấy chứng nhận quyền sử dụng đất, "
    "quyền sở hữu tài sản gắn liền với đất đối với nhà ở, công trình xây dựng thuộc trường hợp phải "
    "xin phép xây dựng quy định tại khoản 3 Điều 148, khoản 3 Điều 149 Luật Đất đai (nếu có) (Bản chính)",
    "Giấy tờ về việc nhận thừa kế quyền sử dụng đất theo quy định của pháp luật về dân sự (Bản sao "
    "công chứng)",
    "Một trong các loại giấy tờ quy định tại Điều 137, khoản 1, khoản 5 Điều 148, khoản 1, khoản 5 "
    "Điều 149 Luật Đất đai, sơ đồ nhà ở, công trình xây dựng (nếu có) (Bản chính)",
    "Giấy tờ về việc chuyển quyền sử dụng đất và Giấy chứng nhận đã cấp cho phần diện tích tăng thêm "
    "(Bản chính)",
    "Giấy tờ về việc nhận thừa kế quyền sử dụng đất theo quy định của pháp luật về dân sự đối với "
    "trường hợp nhận thừa kế quyền sử dụng đất chưa được cấp Giấy chứng nhận theo quy định pháp luật "
    "về đất đai (Bản chính)",
    "Giấy tờ về giao đất không đúng thẩm quyền hoặc giấy tờ về việc mua, nhận thanh lý, hóa giá, "
    "phân phối nhà ở, công trình xây dựng gắn liền với đất theo quy định tại Điều 140 Luật Đất đai "
    "(nếu có) (Bản chính)",
    "Giấy tờ liên quan đến xử phạt vi phạm hành chính trong lĩnh vực đất đai đối với trường hợp có "
    "vi phạm hành chính trong lĩnh vực đất đai (Bản chính)",
    "Hồ sơ thiết kế xây dựng công trình đã được cơ quan chuyên môn về xây dựng thẩm định hoặc đã có "
    "văn bản chấp thuận kết quả nghiệm thu hoàn thành hạng mục công trình, công trình xây dựng theo "
    "quy định của pháp luật về xây dựng đối với trường hợp chứng nhận quyền sở hữu công trình xây "
    "dựng trên đất nông nghiệp mà chủ sở hữu công trình không có một trong các loại giấy tờ quy định "
    "tại Điều 149 của Luật Đất đai hoặc công trình được miễn giấy phép xây dựng theo quy định của "
    "pháp luật về xây dựng (Bản chính)",
    "Văn bản thỏa thuận về việc cấp chung một Giấy chứng nhận đối với trường hợp có nhiều người "
    "chung quyền sử dụng đất, chung quyền sở hữu tài sản gắn liền với đất (Bản chính)",
    "Văn bản về việc đại diện theo quy định của pháp luật về dân sự đối với trường hợp thực hiện thủ "
    "tục đăng ký đất đai, tài sản gắn liền với đất thông qua người đại diện (Bản chính)",
    "Một trong các loại giấy tờ quy định tại Điều 137, khoản 4, khoản 5 Điều 148, khoản 4, khoản 5 "
    "Điều 149 Luật Đất đai (nếu có) (Bản chính)",
    "Giấy tờ về việc nhận thừa kế quyền sử dụng đất theo quy định của pháp luật về dân sự và giấy tờ "
    "về việc chuyển quyền sử dụng đất đối với trường hợp quy định tại khoản 4 Điều 45 Luật Đất đai "
    "(Bản chính)",
]

# slotKey phải DUY NHẤT theo dòng: extension gom các file cùng slotKey vào chung một ô upload.
SLOTS: list[dict[str, Any]] = [
    {"slotKey": f"dkdd_lc_row{index + 1:02d}", "slotIndex": index, "slotName": name}
    for index, name in enumerate(_ROW_NAMES)
]
_SLOT_BY_INDEX = {slot["slotIndex"]: slot for slot in SLOTS}

# docType -> (slotIndex 0-based, tên tài liệu hiển thị cho cán bộ).
_ROUTES: dict[str, dict[str, Any]] = {
    # --- Dòng 1: Đơn và phụ lục của Đơn.
    "don_dang_ky": {"index": 0, "documentName": "Đơn đăng ký đất đai, tài sản gắn liền với đất"},
    "danh_sach_su_dung_chung": {"index": 0, "documentName": "Danh sách người sử dụng chung (Mẫu số 13a)"},
    # Cổng KHÔNG có dòng giấy tờ tùy thân -> CCCD đi chung dòng Đơn (giống các thủ tục đất khác).
    "identity": {"index": 0, "documentName": "Căn cước công dân"},
    # --- Các dòng route theo đúng tên dòng.
    "thong_bao_ket_qua_dang_ky": {"index": 1, "documentName": "Thông báo xác nhận kết quả đăng ký đất đai"},
    "thoa_thuan_thua_lien_ke": {"index": 2, "documentName": "Văn bản xác lập quyền đối với thửa đất liền kề"},
    "van_ban_thanh_vien_ho_gia_dinh": {
        "index": 3,
        "documentName": "Văn bản xác định thành viên hộ gia đình sử dụng đất",
    },
    # --- Dòng 5: trích đo + bản mô tả ranh giới + GCN thửa liền kề (ảnh ánh xạ: không có dòng riêng).
    "so_do_trich_luc_trich_do": {"index": 4, "documentName": "Mảnh trích đo/trích lục bản đồ địa chính thửa đất"},
    "ban_mo_ta_ranh_gioi": {"index": 4, "documentName": "Bản mô tả ranh giới, mốc giới thửa đất"},
    "gcn_thua_lien_ke": {"index": 4, "documentName": "Giấy chứng nhận thửa đất liền kề (đối chiếu ranh giới)"},
    "quyet_dinh_xu_phat": {"index": 5, "documentName": "Quyết định xử phạt vi phạm hành chính về đất đai"},
    "chung_tu_tai_chinh": {"index": 6, "documentName": "Chứng từ thực hiện nghĩa vụ tài chính"},
    # --- Dòng 8: giấy tờ chuyển quyền + bản cam kết nguồn gốc đất (ảnh ánh xạ HS2).
    "giay_to_chuyen_quyen": {"index": 7, "documentName": "Giấy tờ chuyển quyền sử dụng đất"},
    "cam_ket_nguon_goc_dat": {"index": 7, "documentName": "Bản cam kết nguồn gốc đất"},
    "xac_nhan_xay_dung": {"index": 8, "documentName": "Giấy xác nhận điều kiện tồn tại công trình xây dựng"},
    "thua_ke_cong_chung": {"index": 9, "documentName": "Giấy tờ nhận thừa kế QSDĐ (bản sao công chứng)"},
    "giay_to_dieu_137_khoan1": {"index": 10, "documentName": "Giấy tờ về quyền sử dụng đất theo Điều 137"},
    "gcn_dien_tich_tang_them": {"index": 11, "documentName": "Giấy chứng nhận phần diện tích tăng thêm"},
    "thua_ke_chua_cap_gcn": {"index": 12, "documentName": "Giấy tờ thừa kế QSDĐ chưa được cấp Giấy chứng nhận"},
    "giao_dat_khong_dung_tham_quyen": {"index": 13, "documentName": "Giấy tờ giao đất không đúng thẩm quyền"},
    "giay_to_xu_phat_lien_quan": {"index": 14, "documentName": "Giấy tờ liên quan xử phạt vi phạm về đất đai"},
    "ho_so_thiet_ke_xay_dung": {"index": 15, "documentName": "Hồ sơ thiết kế xây dựng công trình"},
    "thoa_thuan_cap_chung_gcn": {"index": 16, "documentName": "Văn bản thỏa thuận cấp chung một Giấy chứng nhận"},
    "van_ban_dai_dien": {"index": 17, "documentName": "Văn bản về việc đại diện/ủy quyền"},
    "giay_to_dieu_137_khoan4": {"index": 18, "documentName": "Giấy tờ về quyền sử dụng đất theo khoản 4"},
    "thua_ke_va_chuyen_quyen": {"index": 19, "documentName": "Giấy tờ thừa kế kèm chuyển quyền sử dụng đất"},
}

# File chưa nhận diện KHÔNG được rớt: đính tạm vào dòng Đơn rồi cảnh báo cho cán bộ chuyển dòng.
_OTHER_SLOT_INDEX = 0
_ALLOWED = set(_ROUTES) | {_OTHER}


def _normalize_doc_type(value: Any) -> str:
    """Chuẩn hóa docType LLM trả về; không khớp allowed_types thì coi như other."""
    folded = fold(str(value or ""))
    for doc_type in _ALLOWED:
        if folded == fold(doc_type):
            return doc_type
    return _OTHER


def _data_url_size(data_url: str) -> int:
    """Ước lượng kích thước payload base64 mà không giải mã file lớn."""
    payload = str(data_url or "").partition(",")[2]
    if not payload:
        return 0
    payload = re.sub(r"\s+", "", payload)
    padding = len(payload) - len(payload.rstrip("="))
    return max(0, (len(payload) * 3) // 4 - padding)


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=900, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    result: dict[int, str] = {}
    for item in parsed.get("documents", []) or []:
        try:
            result[int(item.get("index"))] = _normalize_doc_type(item.get("docType") or item.get("type"))
        except (TypeError, ValueError):
            continue
    return result


def _build_item(file: dict, file_index: int, file_name: str, doc_type: str, slot_index: int, document_name: str) -> dict:
    del file  # chỉ cần index + tên; nội dung file do FE gửi kèm theo fileIndex.
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
    }


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict] | None = None,
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    del ocr_results  # LLM-first: không suy luận rule từ OCR text ở đây.
    llm_types = llm_types or {}
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")

        # Cổng chặn cứng 6 MB/tệp. Planner không tách file được nên phải báo cho cán bộ tự tách.
        size = _data_url_size(file.get("dataUrl", ""))
        if size > _MAX_FILE_BYTES:
            warnings.append(
                f"File '{file_name}' nặng {size / 1024 / 1024:.1f} MB, vượt giới hạn 6 MB của cổng — "
                "hãy tách thành nhiều tệp nhỏ theo từng giấy tờ (mỗi tệp dưới 6 MB) rồi đính kèm lại."
            )
            classified.append(
                {"fileName": file_name, "docType": _OTHER, "source": "validation", "skipped": True,
                 "reason": "file_too_large"}
            )
            continue

        doc_type = llm_types.get(index) or _OTHER
        if doc_type not in _ALLOWED:
            doc_type = _OTHER

        if doc_type in _ROUTES:
            route = _ROUTES[doc_type]
            item = _build_item(file, index, file_name, doc_type, route["index"], route["documentName"])
            attachments.append(item)
            classified.append(
                {"fileName": file_name, "docType": doc_type, "source": "llm", "slotIndex": item["slotIndex"]}
            )
            continue

        # other: vẫn đính vào dòng Đơn để không bỏ sót giấy tờ, kèm cảnh báo rõ ràng.
        document_name = normalize_document_name(Path(file_name).stem, "Tài liệu chưa xác định")
        item = _build_item(file, index, file_name, _OTHER, _OTHER_SLOT_INDEX, document_name)
        attachments.append(item)
        warnings.append(
            f"Không xác định được loại giấy tờ của file '{file_name}' — đã đính tạm vào dòng 1 "
            "(Đơn đăng ký đất đai); vui lòng kiểm tra và chuyển sang đúng dòng nếu cần."
        )
        classified.append(
            {"fileName": file_name, "docType": _OTHER,
             "source": "llm" if index in llm_types else "unknown",
             "slotIndex": _OTHER_SLOT_INDEX, "fallback": True}
        )

    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": item.name, "type": item.type, "dataUrl": item.dataUrl} for item in files]
    errors: list[str] = []

    # File quá khổ bị cổng từ chối -> không tốn OCR/LLM cho chúng; build_plan_items tự phát cảnh báo.
    ocr_files = [
        item
        for item in raw_files
        if item.get("type") in _OCR_TYPES and _data_url_size(item.get("dataUrl", "")) <= _MAX_FILE_BYTES
    ]

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    by_name = {item.get("name"): item for item in ocr_results}
    llm_documents = [
        {"index": index, "name": file["name"], "text": str(by_name.get(file.get("name"), {}).get("text") or "")}
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
            "llmDocuments": [item["name"] for item in llm_documents],
            "classified": classified,
            "slots": SLOTS,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "ocr_text": join_ocr_documents(ocr_results),
        "llm_output": {str(index): value for index, value in llm_types.items()},
        "errors": errors,
    }

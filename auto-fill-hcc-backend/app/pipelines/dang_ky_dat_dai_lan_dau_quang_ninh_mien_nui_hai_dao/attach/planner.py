"""Lập kế hoạch đính kèm vào bảng 22 hàng trên cổng DVC Quảng Ninh.

Hàng 2 và 18 trong HTML thật chỉ là tiêu đề phân nhóm nên không có route nghiệp vụ. Mỗi file chỉ
sinh một plan item; đặc biệt Đơn Mẫu số 15 có Mẫu 15a đi kèm không được nhân sang hàng 12.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import sanitize_wallet_document_label as _wallet_label
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_LOAI_BAN = "Bản chính"

# componentIndex theo chỉ số 0-based đã dùng trong các planner attp-row hiện có. componentName là
# khóa chính vì FE khớp substring sau khi fold dấu; index chỉ giúp định vị nhanh khi thứ tự còn nguyên.
_ROUTES: dict[str, dict[str, Any]] = {
    "ho_so_thiet_ke_xay_dung": {
        "index": 0,
        "name": "Hồ sơ thiết kế xây dựng công trình đã được cơ quan chuyên môn về xây dựng thẩm định",
    },
    "don_mau_15": {
        "index": 2,
        "name": "Đơn đăng ký đất đai, tài sản gắn liền với đất theo Mẫu số 15",
    },
    "to_khai_01_sddpnn": {
        "index": 2,
        "name": "Đơn đăng ký đất đai, tài sản gắn liền với đất theo Mẫu số 15",
    },
    "giay_to_dieu_137_148_149": {
        "index": 3,
        "name": "Một trong các loại giấy tờ quy định tại Điều 137, khoản 1, khoản 5 Điều 148",
    },
    "dien_tich_tang_them": {
        "index": 4,
        "name": "Trường hợp thửa đất gốc có giấy tờ về quyền sử dụng đất",
    },
    "cam_ket_thua_ke_chua_gcn": {
        "index": 5,
        "name": "Văn bản cam kết của người nhận thừa kế hoặc văn bản thỏa thuận của những người nhận thừa kế đối với trường hợp nhận thừa kế",
    },
    "cam_ket_thua_ke_khong_cong_chung": {
        "index": 6,
        "name": "Văn bản cam kết của người nhận thừa kế hoặc văn bản thỏa thuận của những người nhận thừa kế không phải thực hiện công chứng",
    },
    "giay_to_thua_ke_chuyen_quyen": {
        "index": 7,
        "name": "Giấy tờ về việc nhận thừa kế quyền sử dụng đất",
    },
    "giao_dat_khong_dung_tham_quyen": {
        "index": 8,
        "name": "Giấy tờ về giao đất không đúng thẩm quyền",
    },
    "xu_phat_vi_pham_dat_dai": {
        "index": 9,
        "name": "Quyết định xử phạt vi phạm hành chính trong lĩnh vực đất đai đối với trường hợp có vi phạm",
    },
    "quyen_thua_dat_lien_ke": {
        "index": 10,
        "name": "Hợp đồng hoặc văn bản thỏa thuận hoặc quyết định của Tòa án nhân dân về việc xác lập quyền đối với thửa đất liền kề",
    },
    "thanh_vien_chung_qsdd": {
        "index": 11,
        "name": "Văn bản xác định các thành viên có chung quyền sử dụng đất",
    },
    "manh_trich_do": {
        "index": 12,
        "name": "Mảnh trích đo bản đồ địa chính thửa đất",
    },
    "xu_phat_dieu_25": {
        "index": 13,
        "name": "Trường hợp quy định tại điểm a khoản 6 Điều 25 Nghị định số 101/2024/NĐ-CP",
    },
    "nghia_vu_tai_chinh": {
        "index": 14,
        "name": "Chứng từ đã thực hiện nghĩa vụ tài chính",
    },
    "chuyen_quyen_chua_thu_tuc": {
        "index": 15,
        "name": "Trường hợp nhận chuyển quyền sử dụng đất, quyền sở hữu nhà ở, công trình xây dựng mà chưa thực hiện thủ tục chuyển quyền",
    },
    "xac_nhan_ton_tai_cong_trinh": {
        "index": 16,
        "name": "giấy xác nhận của cơ quan có chức năng quản lý về xây dựng cấp huyện",
    },
    "thong_bao_ket_qua_dang_ky": {
        "index": 18,
        "name": "Thông báo xác nhận kết quả đăng ký đất đai",
    },
    "to_khai_01_lptb": {
        "index": 19,
        "name": "Tờ khai lệ phí trước bạ theo Mẫu số 01/LPTB",
    },
    "to_khai_04_sddpnn": {
        "index": 20,
        "name": "Tờ khai thuế sử dụng đất phi nông nghiệp theo Mẫu số 04/TK-SDDPNN",
    },
    "to_khai_03_bds_tncn": {
        "index": 21,
        "name": "Tờ khai thuế thu nhập cá nhân theo Mẫu số 03/BĐS-TNCN",
    },
}
_ALLOWED = set(_ROUTES) | {"other"}

_DISPLAY = {
    "ho_so_thiet_ke_xay_dung": "Hồ sơ thiết kế xây dựng công trình",
    "don_mau_15": "Đơn đăng ký đất đai Mẫu số 15",
    "to_khai_01_sddpnn": "Tờ khai thuế sử dụng đất phi nông nghiệp Mẫu 01/TK-SDDPNN",
    "giay_to_dieu_137_148_149": "Giấy tờ về quyền sử dụng đất, tài sản gắn liền với đất",
    "dien_tich_tang_them": "Giấy tờ đối với phần diện tích đất tăng thêm",
    "cam_ket_thua_ke_chua_gcn": "Văn bản cam kết hoặc thỏa thuận thừa kế",
    "cam_ket_thua_ke_khong_cong_chung": "Văn bản cam kết hoặc thỏa thuận thừa kế không công chứng",
    "giay_to_thua_ke_chuyen_quyen": "Giấy tờ thừa kế và chuyển quyền sử dụng đất",
    "giao_dat_khong_dung_tham_quyen": "Giấy tờ giao đất không đúng thẩm quyền",
    "xu_phat_vi_pham_dat_dai": "Quyết định xử phạt vi phạm hành chính về đất đai",
    "quyen_thua_dat_lien_ke": "Văn bản xác lập quyền đối với thửa đất liền kề",
    "thanh_vien_chung_qsdd": "Văn bản xác định thành viên có chung quyền sử dụng đất",
    "manh_trich_do": "Hồ sơ đo đạc, trích đo địa chính thửa đất",
    "xu_phat_dieu_25": "Quyết định xử phạt theo Điều 25 Nghị định 101/2024/NĐ-CP",
    "nghia_vu_tai_chinh": "Chứng từ thực hiện nghĩa vụ tài chính",
    "chuyen_quyen_chua_thu_tuc": "Giấy tờ chuyển quyền chưa thực hiện thủ tục",
    "xac_nhan_ton_tai_cong_trinh": "Giấy xác nhận đủ điều kiện tồn tại nhà ở, công trình",
    "thong_bao_ket_qua_dang_ky": "Thông báo xác nhận kết quả đăng ký đất đai",
    "to_khai_01_lptb": "Tờ khai lệ phí trước bạ Mẫu 01/LPTB",
    "to_khai_04_sddpnn": "Tờ khai thuế sử dụng đất phi nông nghiệp Mẫu 04/TK-SDDPNN",
    "to_khai_03_bds_tncn": "Tờ khai thuế thu nhập cá nhân Mẫu 03/BĐS-TNCN",
}


def _normalize_doc_type(value: Any) -> str:
    folded = _fold(str(value or ""))
    for doc_type in _ALLOWED:
        if folded == _fold(doc_type):
            return doc_type
    return "other"


def _rule_doc_type(text: str) -> str:
    """Fallback chỉ dùng marker đủ đặc trưng để không đính nhầm hàng."""
    folded = _fold(text or "")
    if not folded:
        return ""

    # Mã biểu mẫu phải kiểm tra trước các cụm mô tả chung về thuế/đất đai.
    if "03/bds-tncn" in folded:
        return "to_khai_03_bds_tncn"
    if "04/tk-sddpnn" in folded:
        return "to_khai_04_sddpnn"
    if "01/lptb" in folded:
        return "to_khai_01_lptb"
    if "01/tk-sddpnn" in folded:
        return "to_khai_01_sddpnn"

    # Đơn là tài liệu chính dù phần kê khai có liệt kê Phiếu đo đạc hay Mẫu 15a đi kèm.
    if "don dang ky dat dai, tai san gan lien voi dat" in folded or (
        "mau so 15" in folded and "de nghi dang ky dat dai" in folded
    ):
        return "don_mau_15"

    if any(
        marker in folded
        for marker in (
            "phieu do dac chinh ly thua dat",
            "phieu xac nhan ket qua do dac hien trang thua dat",
            "ban mo ta ranh gioi, moc gioi thua dat",
            "manh trich do ban do dia chinh thua dat",
        )
    ):
        return "manh_trich_do"
    if "van ban xac dinh cac thanh vien co chung quyen su dung dat" in folded:
        return "thanh_vien_chung_qsdd"
    if "thong bao xac nhan ket qua dang ky dat dai" in folded:
        return "thong_bao_ket_qua_dang_ky"
    if "diem a khoan 6 dieu 25" in folded and "101/2024/nd-cp" in folded:
        return "xu_phat_dieu_25"
    if "quyet dinh xu phat vi pham hanh chinh" in folded and "dat dai" in folded:
        return "xu_phat_vi_pham_dat_dai"
    if "giay to ve giao dat khong dung tham quyen" in folded:
        return "giao_dat_khong_dung_tham_quyen"
    if "quyen doi voi thua dat lien ke" in folded and any(
        marker in folded for marker in ("hop dong", "van ban thoa thuan", "quyet dinh cua toa an")
    ):
        return "quyen_thua_dat_lien_ke"
    if "chung tu da thuc hien nghia vu tai chinh" in folded:
        return "nghia_vu_tai_chinh"
    if "khong phai thuc hien cong chung, chung thuc" in folded and "nhan thua ke" in folded:
        return "cam_ket_thua_ke_khong_cong_chung"
    if "nhan thua ke quyen su dung dat chua duoc cap giay chung nhan" in folded:
        return "cam_ket_thua_ke_chua_gcn"
    if "giay xac nhan" in folded and "du dieu kien ton tai" in folded and "cong trinh xay dung" in folded:
        return "xac_nhan_ton_tai_cong_trinh"
    return ""


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


def _build_item(file: dict, file_index: int, doc_type: str) -> dict:
    route = _ROUTES[doc_type]
    return {
        "fileIndex": file_index,
        "fileName": str(file.get("name") or f"file-{file_index + 1}"),
        "documentName": _wallet_label(_DISPLAY[doc_type]),
        "componentName": route["name"],
        "componentIndex": route["index"],
        "loaiBan": _LOAI_BAN,
        # Cổng Quảng Ninh (React/Radix) đính qua modal "Danh sách tài liệu điện tử" (ví tài liệu) như cổng
        # Bộ Tư pháp → target "existing" để dùng engine wallet-modal (rowForPlanItem + attachOneFileVia
        # DocumentWallet), KHÔNG phải bảng mat-radio attp-row.
        "target": "existing",
        "needsAddComponent": False,
        "detectedType": doc_type,
    }


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    ocr_by_name = {item.get("name"): item for item in ocr_results}
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        text = str(ocr_by_name.get(file_name, {}).get("text") or "")
        llm_type = llm_types.get(index, "")
        rule_type = _rule_doc_type(text)

        if llm_type in _ROUTES:
            doc_type, source = llm_type, "llm"
        elif rule_type in _ROUTES:
            doc_type, source = rule_type, "rule"
        else:
            doc_type, source = "other", "llm" if llm_type == "other" else "unknown"

        if doc_type in _ROUTES:
            item = _build_item(file, index, doc_type)
            attachments.append(item)
            classified.append(
                {
                    "fileName": file_name,
                    "docType": doc_type,
                    "source": source,
                    "componentIndex": item["componentIndex"],
                }
            )
            continue

        warnings.append(f"Không xác định được loại giấy tờ cho file '{file_name}' — vui lòng đính kèm thủ công.")
        classified.append({"fileName": file_name, "docType": "other", "source": source, "skipped": True})

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

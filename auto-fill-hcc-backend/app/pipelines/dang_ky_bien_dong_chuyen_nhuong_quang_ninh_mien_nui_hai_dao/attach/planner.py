"""Lập kế hoạch đính kèm đăng ký biến động đất đai trên cổng DVC Quảng Ninh.

Hàng 8 trong HTML thật chỉ là tiêu đề phân nhóm nên cố ý không có route. Mỗi file chỉ sinh một plan
item; nhiều Giấy chứng nhận độc lập được phép cùng đi vào hàng "Giấy chứng nhận đã cấp".
"""

import asyncio
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
_AGRICULTURAL_TAX = "to_khai_thue_su_dung_dat_nong_nghiep"

# componentIndex là 0-based theo đúng 15 hàng trong HTML. componentName là khóa chính vì FE khớp
# substring sau khi fold dấu; index chỉ là dự phòng khi thứ tự bảng không đổi.
_ROUTES: dict[str, dict[str, Any]] = {
    "manh_trich_do": {
        "index": 0,
        "name": "Mảnh trích đo bản đồ địa chính thửa đất đối với trường hợp người sử dụng đất có nhu cầu đo đạc",
    },
    "ban_ve_tach_hop_thua": {
        "index": 1,
        "name": "Bản vẽ tách thửa đất, hợp thửa đất theo Mẫu số 27",
    },
    "to_khai_01_lptb": {
        "index": 2,
        "name": "Tờ khai lệ phí trước bạ theo Mẫu số 01/LPTB",
    },
    "to_khai_04_sddpnn": {
        "index": 3,
        "name": "Tờ khai thuế sử dụng đất phi nông nghiệp theo Mẫu số 04/TK-SDDPNN",
    },
    "to_khai_03_bds_tncn": {
        "index": 4,
        "name": "Tờ khai thuế thu nhập cá nhân theo Mẫu số 03/BĐS-TNCN",
    },
    "gcn_da_cap": {
        "index": 5,
        "name": "Giấy chứng nhận đã cấp",
    },
    "don_mau_18": {
        "index": 6,
        "name": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18",
    },
    # index 7 là tiêu đề nhóm "Đối với trường hợp chuyển đổi, chuyển nhượng...", không nhận file.
    "hop_dong_chuyen_quyen": {
        "index": 8,
        "name": "Hợp đồng hoặc văn bản về việc chuyển quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất",
    },
    "hop_dong_tai_san_dat_thue_hang_nam": {
        "index": 9,
        "name": "Hợp đồng hoặc văn bản về việc bán hoặc tặng cho hoặc để thừa kế hoặc góp vốn bằng tài sản gắn liền với đất",
    },
    "van_ban_cho_thue_lai": {
        "index": 10,
        "name": "Văn bản về việc cho thuê, cho thuê lại quyền sử dụng đất đối với trường hợp cho thuê, cho thuê lại quyền sử dụng đất trong dự án xây dựng kinh doanh kết cấu hạ tầng",
    },
    "thoa_thuan_cap_chung_gcn": {
        "index": 11,
        "name": "Văn bản thỏa thuận về việc cấp chung một Giấy chứng nhận",
    },
    "dong_y_chu_so_huu_tai_san": {
        "index": 12,
        "name": "Văn bản của người sử dụng đất đồng ý cho chủ sở hữu tài sản gắn liền với đất được chuyển nhượng",
    },
    "dong_y_ben_nhan_the_chap": {
        "index": 13,
        "name": "Văn bản của bên nhận thế chấp về việc đồng ý cho bên thế chấp được chuyển nhượng",
    },
    "van_ban_dai_dien": {
        "index": 14,
        "name": "Văn bản về việc đại diện theo quy định của pháp luật về dân sự",
    },
}
_ALLOWED = set(_ROUTES) | {_AGRICULTURAL_TAX, "other"}

_DISPLAY = {
    "manh_trich_do": "Phiếu đo đạc chỉnh lý, mảnh trích đo địa chính",
    "ban_ve_tach_hop_thua": "Bản vẽ tách thửa đất, hợp thửa đất Mẫu số 27",
    "to_khai_01_lptb": "Tờ khai lệ phí trước bạ Mẫu số 01/LPTB",
    "to_khai_04_sddpnn": "Tờ khai thuế sử dụng đất phi nông nghiệp Mẫu số 04/TK-SDDPNN",
    "to_khai_03_bds_tncn": "Tờ khai thuế thu nhập cá nhân Mẫu số 03/BĐS-TNCN",
    "gcn_da_cap": "Giấy chứng nhận quyền sử dụng đất đã cấp",
    "don_mau_18": "Đơn đăng ký biến động đất đai Mẫu số 18",
    "hop_dong_chuyen_quyen": "Hợp đồng hoặc văn bản chuyển quyền sử dụng đất",
    "hop_dong_tai_san_dat_thue_hang_nam": "Văn bản chuyển quyền tài sản gắn liền với đất thuê trả tiền hằng năm",
    "van_ban_cho_thue_lai": "Văn bản cho thuê, cho thuê lại quyền sử dụng đất",
    "thoa_thuan_cap_chung_gcn": "Văn bản thỏa thuận cấp chung một Giấy chứng nhận",
    "dong_y_chu_so_huu_tai_san": "Văn bản đồng ý của người sử dụng đất",
    "dong_y_ben_nhan_the_chap": "Văn bản đồng ý của bên nhận thế chấp",
    "van_ban_dai_dien": "Văn bản đại diện hoặc ủy quyền",
    _AGRICULTURAL_TAX: "Tờ khai thuế sử dụng đất nông nghiệp",
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

    # Mã biểu mẫu phải đứng trước các cụm mô tả chung trong hợp đồng/đơn.
    if "03/bds-tncn" in folded:
        return "to_khai_03_bds_tncn"
    if "04/tk-sddpnn" in folded:
        return "to_khai_04_sddpnn"
    if "01/lptb" in folded:
        return "to_khai_01_lptb"
    if "to khai thue su dung dat nong nghiep" in folded and "phi nong nghiep" not in folded:
        return _AGRICULTURAL_TAX

    # Tài liệu chính phải được nhận diện trước các GCN/tài liệu kèm nằm ở trang sau.
    if "don dang ky bien dong dat dai, tai san gan lien voi dat" in folded or (
        "mau so 18" in folded and "dang ky bien dong" in folded
    ):
        return "don_mau_18"
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
    if "ban ve tach thua dat" in folded or "ban ve hop thua dat" in folded or (
        "mau so 27" in folded and any(marker in folded for marker in ("tach thua", "hop thua"))
    ):
        return "ban_ve_tach_hop_thua"

    # Các nhánh hợp đồng/văn bản đặc thù phải được xét trước hợp đồng chuyển quyền phổ thông.
    if "dat thue cua nha nuoc" in folded and "tra tien thue dat hang nam" in folded and any(
        marker in folded for marker in ("ban", "tang cho", "thua ke", "gop von")
    ):
        return "hop_dong_tai_san_dat_thue_hang_nam"
    if "cho thue lai quyen su dung dat" in folded and "kinh doanh ket cau ha tang" in folded:
        return "van_ban_cho_thue_lai"
    if "cap chung mot giay chung nhan" in folded and "nhieu nguoi nhan chuyen quyen" in folded:
        return "thoa_thuan_cap_chung_gcn"
    if "ben nhan the chap" in folded and "dong y" in folded and any(
        marker in folded for marker in ("chuyen nhuong", "tang cho", "gop von")
    ):
        return "dong_y_ben_nhan_the_chap"
    if "nguoi su dung dat dong y" in folded and "chu so huu tai san gan lien voi dat" in folded:
        return "dong_y_chu_so_huu_tai_san"
    if any(marker in folded for marker in ("giay uy quyen", "hop dong uy quyen", "van ban uy quyen")) or (
        "van ban ve viec dai dien" in folded and "phap luat ve dan su" in folded
    ):
        return "van_ban_dai_dien"
    if any(
        marker in folded
        for marker in (
            "hop dong chuyen nhuong quyen su dung dat",
            "hop dong tang cho quyen su dung dat",
            "van ban khai nhan di san",
            "van ban thoa thuan phan chia di san",
            "hop dong gop von bang quyen su dung dat",
            "hop dong chuyen doi quyen su dung dat nong nghiep",
        )
    ):
        return "hop_dong_chuyen_quyen"
    if "giay chung nhan" in folded and any(
        marker in folded for marker in ("quyen su dung dat", "quyen so huu tai san gan lien voi dat")
    ):
        return "gcn_da_cap"
    return ""


def _llm_document(document: dict[str, Any]) -> dict[str, Any]:
    # File hợp đồng/đo đạc có thể rất dài. Tài liệu chính luôn nằm ở đầu PDF nên giữ phần đầu vừa đủ
    # để một file không tự vượt context và cũng không để giấy tờ kèm ở cuối lấn át loại chính.
    text = str(document.get("text") or "")
    return {"index": document.get("index"), "text": text[:12000]}


async def _classify_one_with_llm(document: dict[str, Any]) -> tuple[int, str]:
    index = int(document.get("index"))
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt([_llm_document(document)])},
    ]
    raw = await client.chat(messages, max_tokens=120, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    first = next(iter(parsed.get("documents", []) or []), {})
    return index, _normalize_doc_type(first.get("docType") or first.get("type"))


async def _classify_with_llm(
    documents: list[dict[str, Any]],
    errors: list[str] | None = None,
) -> dict[int, str]:
    if not documents:
        return {}

    # Một prompt/call cho mỗi file: PDF dài hoặc một lỗi provider chỉ làm file đó fallback rule,
    # không làm mất kết quả phân loại của toàn bộ hồ sơ.
    outcomes = await asyncio.gather(
        *(_classify_one_with_llm(document) for document in documents),
        return_exceptions=True,
    )
    result: dict[int, str] = {}
    for document, outcome in zip(documents, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            if errors is not None:
                errors.append(f"attachment_agent file {document.get('index')}: {outcome}")
            continue
        index, doc_type = outcome
        result[index] = doc_type
    return result


def _build_item(file: dict, file_index: int, doc_type: str) -> dict:
    base = {
        "fileIndex": file_index,
        "fileName": str(file.get("name") or f"file-{file_index + 1}"),
        "documentName": _wallet_label(_DISPLAY[doc_type]),
        "loaiBan": _LOAI_BAN,
        "detectedType": doc_type,
    }
    if doc_type == _AGRICULTURAL_TAX:
        return {
            **base,
            "componentName": _DISPLAY[doc_type],
            "target": "new",
            "needsAddComponent": True,
        }

    route = _ROUTES[doc_type]
    return {
        **base,
        "componentName": route["name"],
        "componentIndex": route["index"],
        # Quảng Ninh (React/Radix) đính qua modal "Danh sách tài liệu điện tử" như Bộ Tư pháp → engine
        # wallet-modal (target "existing"), không phải bảng mat-radio attp-row.
        "target": "existing",
        "needsAddComponent": False,
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

        if llm_type in _ROUTES or llm_type == _AGRICULTURAL_TAX:
            doc_type, source = llm_type, "llm"
        elif rule_type in _ROUTES or rule_type == _AGRICULTURAL_TAX:
            doc_type, source = rule_type, "rule"
        else:
            doc_type, source = "other", "llm" if llm_type == "other" else "unknown"

        if doc_type in _ROUTES or doc_type == _AGRICULTURAL_TAX:
            item = _build_item(file, index, doc_type)
            attachments.append(item)
            classified_item = {
                "fileName": file_name,
                "docType": doc_type,
                "source": source,
                "target": item["target"],
            }
            if "componentIndex" in item:
                classified_item["componentIndex"] = item["componentIndex"]
            classified.append(classified_item)
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
            llm_types = await _classify_with_llm(llm_documents, errors)
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

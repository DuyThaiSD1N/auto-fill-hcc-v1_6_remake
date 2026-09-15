"""Lập kế hoạch đính kèm cho [Lâm Đồng] "Đăng ký, cấp Giấy chứng nhận đối với thửa đất có DIỆN TÍCH
TĂNG THÊM do thay đổi ranh giới so với Giấy chứng nhận đã cấp; đăng ký, cấp Giấy chứng nhận đối với
toàn bộ diện tích đất đang sử dụng" (mã 1.116356, cổng dichvucong.lamdong.gov.vn).

Bảng thành phần hồ sơ có sẵn 6 dòng (đã đối chiếu VERBATIM với 'đính kèm.html'; mỗi dòng là
mat-checkbox + input[type=file] MULTIPLE) → engine "attp-row". componentIndex là STT 1-BASED;
componentName là đoạn text đặc trưng trong cột "Tên giấy tờ" (FE khớp substring HAI CHIỀU sau khi
fold dấu — đã soát cả 6 dòng, mỗi chuỗi chỉ trúng ĐÚNG dòng của nó).

  STT 1: Đơn đăng ký biến động đất đai... Mẫu số 18    ← don_bien_dong · cccd · other
  STT 2: Giấy chứng nhận đã cấp, trừ trường hợp...     ← giay_chung_nhan
  STT 3: Giấy tờ chứng minh phần diện tích tăng thêm   ← chung_minh_tang_them
  STT 4: Mảnh trích đo bản đồ địa chính thửa đất       ← manh_do_dac
  STT 5: Tờ khai thuế theo quy định của pháp luật...   ← to_khai_thue
  STT 6: Văn bản về việc đại diện theo pháp luật dân sự ← van_ban_dai_dien

⚑ MỘT TỆP = MỘT LOẠI GIẤY TỜ = MỘT DÒNG (quy tắc chốt 2026-09-14). `_ROUTES` là map 1-1, tuyệt đối
không docType nào trỏ hai dòng. Lý do: đính một tệp vào nhiều dòng làm số lượt đính > số tệp, extension
báo "4/3 file" gây hiểu nhầm là sai/thừa file; và nghiệp vụ cũng chỉ cần mỗi tệp nằm đúng một chỗ.
⚠ Đánh đổi đã biết: ảnh ánh xạ `anh_xa_thanh_phan_ho_so_1.116356.png` mô tả hồ sơ mẫu có MỘT tệp quét
gộp (trang 1 = Mảnh đo đạc chỉnh lý → dòng 4; trang 2-6 = Bản mô tả ranh giới + công văn → dòng 3) và
khuyên tải tệp đó ở CẢ hai dòng. Với quy tắc 1-tệp-1-dòng thì dòng còn lại sẽ TRỐNG → `_SCAN_GOP_PAIR`
phát cảnh báo để cán bộ tự bù hoặc đề nghị người dân tách tệp, KHÔNG im lặng bỏ qua. Cũng KHÔNG cắt
trang bằng `sourceSegments`: cắt sai là mất giấy tờ.

CCCD ĐI CHUNG DÒNG ĐƠN (STT 1): ảnh ánh xạ khuyên bấm "+ Thêm giấy tờ" để khai riêng một dòng CCCD,
nhưng nút `a.btn_addNewFile` nằm NGOÀI <table> nên engine attp-row không bấm được, và extension không
được sửa trong phạm vi thêm thủ tục. Đính CCCD vào dòng Đơn là an toàn: trong hồ sơ mẫu, CCCD vốn
nằm CÙNG FILE với Đơn Mẫu 18. Đây là điểm CỐ Ý khác khuyến nghị thao tác tay trong ảnh.

KHÔNG gộp PDF (không dùng sourceFileIndexes): ô upload là input MULTIPLE, FE gom mọi item cùng
componentName rồi set cả loạt → mỗi giấy tờ vẫn là MỘT TỆP RIÊNG.

Phân loại LLM-FIRST tuyệt đối: docType CHỈ lấy từ LLM, KHÔNG có nhánh rule keyword (giòn, dễ sai).
Không rõ loại → "Tài liệu khác", đính vào dòng Đơn + cảnh báo; TUYỆT ĐỐI không bỏ sót file nào.
KHÔNG set Bản chính/Bản sao: cả 6 dòng của cổng đã ghi cứng "1 Bản chính", không có radio để chọn.
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
_DON_BIEN_DONG = "don_bien_dong"
_GIAY_CHUNG_NHAN = "giay_chung_nhan"
_CHUNG_MINH_TANG_THEM = "chung_minh_tang_them"
_MANH_DO_DAC = "manh_do_dac"
_TO_KHAI_THUE = "to_khai_thue"
_VAN_BAN_DAI_DIEN = "van_ban_dai_dien"
_CCCD = "cccd"
_OTHER = "other"

# --- 6 dòng của bảng (STT 1-based) ---
_ROW_DON = {
    "index": 1,
    "name": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất, Mẫu số 18 Phụ lục VI",
}
_ROW_GCN = {
    "index": 2,
    "name": "Giấy chứng nhận đã cấp, trừ trường hợp thực hiện quyết định hoặc bản án của Tòa án nhân dân",
}
_ROW_CHUNG_MINH = {"index": 3, "name": "Giấy tờ chứng minh phần diện tích tăng thêm"}
_ROW_DO_DAC = {"index": 4, "name": "Mảnh trích đo bản đồ địa chính thửa đất"}
_ROW_THUE = {"index": 5, "name": "Tờ khai thuế theo quy định của pháp luật thuế hiện hành"}
_ROW_DAI_DIEN = {"index": 6, "name": "Văn bản về việc đại diện theo quy định của pháp luật về dân sự"}

# docType → (dòng, nhãn hiển thị). MỘT FILE CHỈ ĐI ĐÚNG MỘT DÒNG — xem quy tắc 1-file-1-loại ở
# docstring đầu file; vì vậy map là 1-1, không có docType nào trỏ hai dòng.
_ROUTES: dict[str, tuple[dict, str]] = {
    _DON_BIEN_DONG: (_ROW_DON, "Đơn đăng ký biến động đất đai (Mẫu số 18)"),
    _GIAY_CHUNG_NHAN: (_ROW_GCN, "Giấy chứng nhận quyền sử dụng đất đã cấp"),
    _CHUNG_MINH_TANG_THEM: (_ROW_CHUNG_MINH, "Giấy tờ chứng minh phần diện tích tăng thêm"),
    _MANH_DO_DAC: (_ROW_DO_DAC, "Mảnh trích đo bản đồ địa chính thửa đất"),
    _TO_KHAI_THUE: (_ROW_THUE, "Tờ khai thuế"),
    _VAN_BAN_DAI_DIEN: (_ROW_DAI_DIEN, "Văn bản về việc đại diện"),
    # Bảng KHÔNG có dòng riêng cho CCCD (phải bấm "+ Thêm giấy tờ" — engine không bấm được) → dòng Đơn.
    _CCCD: (_ROW_DON, "Căn cước công dân của người sử dụng đất"),
}
_ALLOWED = set(_ROUTES) | {_OTHER}

# Hai dòng hay bị NGƯỜI DÂN QUÉT GỘP vào một tệp (mảnh đo đạc ở trang đầu, bản mô tả ranh giới +
# công văn ở các trang sau). Một tệp giờ chỉ đi ĐÚNG một dòng, nên dòng còn lại sẽ trống → phát cảnh
# báo để cán bộ biết mà tự bù, thay vì im lặng để hồ sơ thiếu thành phần.
_SCAN_GOP_PAIR = {
    _CHUNG_MINH_TANG_THEM: (_ROW_DO_DAC, "Mảnh trích đo bản đồ địa chính thửa đất"),
    _MANH_DO_DAC: (_ROW_CHUNG_MINH, "Giấy tờ chứng minh phần diện tích tăng thêm"),
}

# Nhãn cho tài liệu KHÔNG nhận ra loại; đính vào dòng Đơn để không rớt file.
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

    def name_of(index: int) -> str:
        return str(files[index].get("name") or f"file-{index + 1}")

    for index in range(len(files)):
        llm_type = llm_types.get(index, "")
        doc_type = llm_type if llm_type in _ROUTES else _OTHER
        file_name = name_of(index)

        if doc_type == _OTHER:
            # Không rõ loại → "Tài liệu khác" vào dòng Đơn. Mọi nhánh hỏng (OCR rỗng, file không phải
            # ảnh/PDF nên không tới LLM, LLM lỗi/trả loại lạ/lệch index) đều rơi về đây → không mất file.
            attachments.append(_item(index, file_name, f"{_LABEL_OTHER} - {file_name}", _ROW_DON, _OTHER))
            warnings.append(
                f"Chưa nhận diện chắc loại giấy tờ cho '{file_name}' — xếp '{_LABEL_OTHER}' và đính vào "
                "dòng Đơn đăng ký biến động (Mẫu số 18); cán bộ kiểm tra lại."
            )
            classified.append({
                "fileName": file_name, "docType": _OTHER,
                "source": "llm" if llm_types.get(index) else "unknown",
                "componentIndexes": [_ROW_DON["index"]],
            })
            continue

        route, document_name = _ROUTES[doc_type]
        attachments.append(_item(index, file_name, document_name, route, doc_type))
        classified.append({
            "fileName": file_name, "docType": doc_type, "source": "llm",
            "componentIndexes": [route["index"]],
        })

    # Mảnh đo đạc và giấy tờ chứng minh diện tích tăng thêm hay bị QUÉT GỘP chung một tệp, mà một tệp
    # chỉ được xếp vào MỘT dòng → dòng còn lại sẽ trống. Nhắc cán bộ thay vì im lặng để hồ sơ thiếu
    # thành phần (cả hai dòng đều là "1 Bản chính" bắt buộc).
    filled_rows = {item["componentIndex"] for item in attachments}
    for doc_type, (missing_row, missing_label) in _SCAN_GOP_PAIR.items():
        has_this = _ROUTES[doc_type][0]["index"] in filled_rows
        if has_this and missing_row["index"] not in filled_rows:
            warnings.append(
                f"Chưa có tệp nào cho dòng '{missing_label}'. Mỗi tệp chỉ được xếp vào MỘT dòng — nếu "
                "tệp đã nộp quét gộp cả giấy tờ của dòng này thì cán bộ đính thêm thủ công, hoặc đề "
                "nghị người dân tách tệp."
            )

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
        attachments.append(_item(index, file_name, f"{_LABEL_OTHER} - {file_name}", _ROW_DON, _OTHER))
        warnings.append(
            f"'{file_name}' chưa được xếp vào dòng nào — đính bổ sung vào dòng Đơn đăng ký biến động "
            "(Mẫu số 18); cán bộ kiểm tra lại."
        )
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

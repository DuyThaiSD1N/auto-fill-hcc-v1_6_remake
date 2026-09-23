"""Đính kèm [Lào Cai] tổ chức kinh tế nhận chuyển nhượng QSDĐ dự án (1.115681) — eForm iGate.

⚑ MÀN HÌNH NÀY KHÔNG CÓ BẢNG "THÀNH PHẦN HỒ SƠ NỘP". Ảnh ánh xạ đính kèm của bộ phận một cửa ghi rõ:
ảnh hướng dẫn của thủ tục có bảng 2 dòng tích chọn, nhưng màn hình thật thì khối "Biểu mẫu giấy tờ"
chỉ in "(Hồ sơ không yêu cầu giấy tờ kèm theo)" — không có dòng nào để tích, không có ô upload cố
định nào. Toàn bộ chỗ đính kèm nằm ở khối "Thông tin khác" bên dưới: danh sách "Giấy tờ khác", mỗi
dòng là select "Mới" + ô gõ TÊN MÔ TẢ + nút "Chọn tệp tin", kèm nút "+" để thêm dòng.

Vì vậy planner KHÔNG dùng engine `fixed-slot` mà phát `target: "new"` + `needsAddComponent: True` —
đúng nhánh `attachOneFileToOtherListFile` của content.js: FE lấy dòng "Giấy tờ khác" còn trống (hoặc
bấm "+" thêm dòng), gõ `componentName` vào ô tên rồi bơm tệp vào input file của CHÍNH dòng đó.

⚑ HAI TẦNG TÊN GỌI, LẤY THẲNG TỪ ẢNH ÁNH XẠ:
  • Hai giấy tờ vốn là "thành phần hồ sơ" theo ảnh hướng dẫn được giữ NGUYÊN VĂN tên thành phần và
    xếp LÊN ĐẦU danh sách (dòng ① và ②): "Trích lục vị trí khu đất mà nhà đầu tư đề xuất thực hiện
    dự án" và "Văn bản đề nghị chấp thuận cho tổ chức kinh tế nhận chuyển nhượng, thuê quyền sử dụng
    đất, nhận góp vốn bằng quyền sử dụng đất để thực hiện dự án đầu tư". Ảnh ánh xạ ghi: "2 tệp của
    2 thành phần đó được chuyển xuống Giấy tờ khác dòng ① và ②, GIỮ NGUYÊN TÊN THÀNH PHẦN" — đổi chữ
    ở đây là lệch khỏi hướng dẫn của bộ phận một cửa.
  • Năm tệp còn lại là ĐÍNH KÈM CHUNG, giữ đúng thứ tự tải lên của ảnh ánh xạ và mang tên gọi thật
    của từng giấy tờ. Engine của cổng chỉ nhận MỘT tệp mỗi dòng nên chúng được rải thành các dòng
    "Giấy tờ khác" kế tiếp thay vì dồn vào một ô — kết quả nộp lên là như nhau, và cán bộ còn đọc
    được tên từng giấy.

⚑ CHỖ ẢNH ÁNH XẠ TỰ GHI NHẬN LÀ CHƯA CHẮC: dòng ② mang tên "Văn bản đề nghị chấp thuận…" nhưng tệp
được gắn vào đó là QUYẾT ĐỊNH CHẤP THUẬN CHỦ TRƯƠNG ĐẦU TƯ, trong khi văn bản đề nghị THẬT (đơn của
doanh nghiệp) lại nằm trong nhóm đính kèm chung. Planner đi theo đúng ảnh ánh xạ và phát cảnh báo
để cán bộ tự quyết có đổi chỗ hai tệp hay không — không tự ý sửa hướng dẫn một cửa.

`noChooserClick=True` là BẮT BUỘC với cổng iGate VNPT: bấm option "Chọn tệp tin" ở đây MỞ HỘP THOẠI
FILE CỦA HỆ ĐIỀU HÀNH và chặn UI — FE phải gán thẳng bằng DataTransfer.

⚑ KHÔNG BỎ SÓT TỆP NÀO. Ảnh ánh xạ chốt "TỔNG HỢP: 7/7 tệp trong hồ sơ đã được gắn" nên ở đây KHÔNG
có `SKIPPED_LABELS` — kể cả giấy tờ tùy thân (thứ nhiều thủ tục khác loại ra) vẫn được đính, chỉ kèm
cảnh báo để cán bộ tự quyết.

Phân loại THUẦN LLM (không lưới keyword). Tài liệu chưa rõ loại vẫn xuống "Giấy tờ khác" với tên đọc
từ tên tệp, kèm cảnh báo.
"""

import asyncio
import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold, normalize_document_name
from app.pipelines._shared.documents import join_ocr_documents
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# Trần dung lượng MỘT tệp của cổng, in ngay trên trang: "Tệp tin tải lên có dung lượng không quá 6MB".
# Ảnh ánh xạ cảnh báo tệp quyết định cho thuê đất của hồ sơ mẫu ~5,9 MB — SÁT trần, nên giữ nguyên
# ngưỡng 6 MB tính trên từng tệp chứ không cộng gộp.
_MAX_FILE_BYTES = 6 * 1024 * 1024

# docType → TÊN MÔ TẢ gõ vào ô tên của dòng "Giấy tờ khác".
# Hai tên đầu lấy NGUYÊN VĂN tên thành phần hồ sơ theo ảnh ánh xạ (xem docstring); các tên còn lại là
# tên gọi thật của giấy tờ để cán bộ tiếp nhận đối chiếu nhanh.
_DISPLAY: dict[str, str] = {
    "so_do_khu_dat": "Trích lục vị trí khu đất mà nhà đầu tư đề xuất thực hiện dự án",
    "qd_chap_thuan_chu_truong": (
        "Văn bản đề nghị chấp thuận cho tổ chức kinh tế nhận chuyển nhượng, thuê quyền sử dụng đất, "
        "nhận góp vốn bằng quyền sử dụng đất để thực hiện dự án đầu tư"
    ),
    "don_de_nghi": "Văn bản đề nghị của tổ chức kinh tế",
    "gcn_dkdn": "Giấy chứng nhận đăng ký doanh nghiệp",
    "giay_uy_quyen": "Giấy ủy quyền",
    "qd_giao_thue_dat": "Quyết định thu hồi đất, chuyển mục đích sử dụng đất và cho thuê đất",
    "so_hoa_mat_bang": "Sơ họa mặt bằng xây dựng dự án",
    "gcn_qsdd": "Giấy chứng nhận quyền sử dụng đất",
    "giay_to_tuy_than": "Giấy tờ tùy thân",
}
_ALLOWED = set(_DISPLAY) | {"other"}

# Hai giấy tờ vốn là "thành phần hồ sơ" của ảnh hướng dẫn → phải nằm ở dòng ① và ② của danh sách
# "Giấy tờ khác", theo đúng thứ tự này. Engine lấy dòng trống theo thứ tự nên chỉ cần xếp chúng lên
# đầu mảng attachments là ra đúng vị trí.
_THANH_PHAN_ORDER: tuple[str, ...] = ("so_do_khu_dat", "qd_chap_thuan_chu_truong")

# Thứ tự tải lên của nhóm đính kèm chung, giữ đúng như ảnh ánh xạ liệt kê.
_CHUNG_ORDER: tuple[str, ...] = (
    "don_de_nghi",
    "gcn_dkdn",
    "giay_uy_quyen",
    "qd_giao_thue_dat",
    "so_hoa_mat_bang",
    "gcn_qsdd",
    "giay_to_tuy_than",
)

# Giấy tờ làm nên bộ hồ sơ của thủ tục này; thiếu cái nào thì cảnh báo trước khi nộp.
_CORE_TYPES: tuple[tuple[str, str], ...] = (
    ("don_de_nghi", "Văn bản đề nghị của tổ chức kinh tế (đơn theo mẫu)"),
    ("so_do_khu_dat", "Trích lục vị trí khu đất nhà đầu tư đề xuất thực hiện dự án"),
    ("qd_chap_thuan_chu_truong", "Quyết định chấp thuận chủ trương đầu tư đồng thời chấp thuận nhà đầu tư"),
    ("gcn_dkdn", "Giấy chứng nhận đăng ký doanh nghiệp của tổ chức đứng đơn"),
)

_OTHER_DISPLAY = "Tài liệu khác"


def _canon(value: Any) -> str:
    return re.sub(r"[_\-\s]+", "_", fold(value)).strip("_")


def _normalize_doc_type(value: Any) -> str:
    canon = _canon(value)
    for doc_type in _ALLOWED:
        if canon == _canon(doc_type):
            return doc_type
    return "other"


def _data_url_size(data_url: Any) -> int:
    """Kích thước thật của tệp, suy từ độ dài phần base64 (FileItem không mang size)."""
    payload = re.sub(r"\s+", "", str(data_url or "").partition(",")[2])
    if not payload:
        return 0
    padding = len(payload) - len(payload.rstrip("="))
    return max(0, (len(payload) * 3) // 4 - padding)


def _mb(size: int) -> str:
    return f"{size / 1024 / 1024:.2f} MB"


def _other_display(file_name: str) -> str:
    """Tài liệu chưa rõ loại giữ TÊN THẬT theo tệp để cán bộ biết là giấy gì."""
    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", str(file_name or "")).strip()
    stem = re.sub(r"[_]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return normalize_document_name(stem, _OTHER_DISPLAY) if stem else _OTHER_DISPLAY


def _unique_name(base: str, used: set[str]) -> str:
    """Hai tệp cùng loại thì tên dòng phải khác nhau, nếu không cán bộ không biết dòng nào là dòng nào."""
    key = fold(base)
    if key and key not in used:
        used.add(key)
        return base
    suffix = 2
    while True:
        candidate = f"{base} ({suffix})"
        if fold(candidate) not in used:
            used.add(fold(candidate))
            return candidate
        suffix += 1


def _sort_key(doc_type: str, index: int) -> tuple[int, int, int]:
    """Thứ tự dòng "Giấy tờ khác": 2 thành phần hồ sơ trước, rồi đính kèm chung, rồi tài liệu lạ.

    Trong mỗi nhóm giữ thứ tự của ảnh ánh xạ; cùng loại thì giữ thứ tự tải lên (`index`) để hai bản
    của cùng một giấy tờ không bị đảo.
    """
    if doc_type in _THANH_PHAN_ORDER:
        return (0, _THANH_PHAN_ORDER.index(doc_type), index)
    if doc_type in _CHUNG_ORDER:
        return (1, _CHUNG_ORDER.index(doc_type), index)
    return (2, 0, index)


async def _classify_one(document: dict[str, Any]) -> tuple[int, str]:
    index = int(document.get("index"))
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(
            [{"index": index, "text": str(document.get("text") or "")[:12000]}]
        )},
    ]
    raw = await client.chat(messages, max_tokens=120, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw) or {}
    first = next(iter(parsed.get("documents", []) or []), {})
    return index, _normalize_doc_type(first.get("docType") or first.get("type"))


async def _classify_with_llm(
    documents: list[dict[str, Any]],
    errors: list[str] | None = None,
) -> dict[int, str]:
    if not documents:
        return {}
    # Một call cho mỗi file: PDF dài hoặc lỗi provider chỉ làm file đó rơi về other, không kéo cả mẻ.
    outcomes = await asyncio.gather(*(_classify_one(d) for d in documents), return_exceptions=True)
    result: dict[int, str] = {}
    for document, outcome in zip(documents, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            if errors is not None:
                errors.append(f"attachment_agent file {document.get('index')}: {outcome}")
            continue
        index, doc_type = outcome
        result[index] = doc_type
    return result


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    warnings: list[str] = []
    unknown: list[str] = []
    used_names: set[str] = set()
    seen_types: set[str] = set()

    # Gắn loại cho từng tệp trước, rồi mới xếp thứ tự dòng — tên dòng phải được đánh số theo thứ tự
    # ĐÃ SẮP, nếu không "(2)" sẽ rơi vào tệp đứng trước trên màn hình.
    typed: list[tuple[int, str, str]] = []  # (fileIndex, fileName, docType)
    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        llm_type = llm_types.get(index, "")
        doc_type = llm_type if llm_type in _ALLOWED else "other"
        seen_types.add(doc_type)
        typed.append((index, file_name, doc_type))

    attachments: list[dict] = []
    classified: list[dict] = []
    for index, file_name, doc_type in sorted(typed, key=lambda t: _sort_key(t[2], t[0])):
        source = "llm" if llm_types.get(index) in _ALLOWED else "default"
        if doc_type == "other":
            document_name = _unique_name(_other_display(file_name), used_names)
            unknown.append(file_name)
        else:
            document_name = _unique_name(_DISPLAY[doc_type], used_names)

        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": document_name,
            # FE gõ componentName vào ô tên của dòng "Giấy tờ khác" → phải là TÊN GIẤY TỜ.
            "componentName": document_name,
            "target": "new",
            "needsAddComponent": True,
            "detectedType": doc_type,
            # Cổng iGate VNPT: bấm option "Chọn tệp tin" mở hộp thoại file của hệ điều hành → gán thẳng.
            "noChooserClick": True,
        })
        classified.append({
            "fileName": file_name,
            "docType": doc_type,
            "source": source,
            "documentName": document_name,
            "target": "new",
        })

    thieu = [nhan for doc_type, nhan in _CORE_TYPES if doc_type not in seen_types]
    if thieu:
        warnings.append(
            "Chưa thấy trong bộ tệp đã tải lên: " + "; ".join(thieu) + ". Đây là các giấy tờ chính "
            "của hồ sơ tổ chức kinh tế nhận chuyển nhượng quyền sử dụng đất — cán bộ kiểm tra lại, "
            "nếu thiếu thật thì bổ sung trước khi nộp."
        )
    # Điểm ảnh ánh xạ tự đánh dấu là chưa chắc — nói thẳng ra thay vì âm thầm chọn hộ cán bộ.
    if {"qd_chap_thuan_chu_truong", "don_de_nghi"} <= seen_types:
        warnings.append(
            "Dòng \"Văn bản đề nghị chấp thuận cho tổ chức kinh tế nhận chuyển nhượng…\" đang gắn "
            "QUYẾT ĐỊNH CHẤP THUẬN CHỦ TRƯƠNG ĐẦU TƯ, đúng như ảnh ánh xạ đính kèm của bộ phận một "
            "cửa. Nhưng văn bản đề nghị THẬT (đơn của doanh nghiệp) lại đang nằm ở nhóm đính kèm "
            "chung — cán bộ tiếp nhận xác nhận giúp có cần đổi chỗ hai tệp này không. Hệ thống cố ý "
            "làm theo ảnh ánh xạ, không tự đổi."
        )
    if "giay_to_tuy_than" in seen_types:
        warnings.append(
            "Có tệp là giấy tờ tùy thân (CCCD/CMND). Ảnh ánh xạ của thủ tục này chốt \"7/7 tệp trong "
            "hồ sơ đã được gắn\" nên hệ thống vẫn đính vào \"Giấy tờ khác\" — cán bộ tự quyết có giữ "
            "lại không."
        )
    if unknown:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã đính vào \"Giấy tờ khác\" với tên lấy theo tên tệp để "
            f"không bỏ sót — cán bộ sửa lại tên mô tả nếu cần: {', '.join(unknown)}."
        )
    if attachments:
        warnings.append(
            "Màn hình này KHÔNG có bảng \"Thành phần hồ sơ nộp\" (cổng ghi \"Hồ sơ không yêu cầu giấy "
            f"tờ kèm theo\") nên cả {len(attachments)} tệp đều được đính vào mục \"Giấy tờ khác\", "
            "mỗi tệp một dòng kèm tên mô tả; hai dòng đầu giữ NGUYÊN VĂN tên thành phần hồ sơ theo "
            "ảnh hướng dẫn. TUYỆT ĐỐI không tách bớt tệp sang chỗ khác. Ô \"Về việc (*)\" đã được "
            "cổng điền sẵn đúng tên thủ tục — giữ nguyên, không sửa."
        )

    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    errors: list[str] = []

    # Trần 6 MB tính cho TỪNG TỆP (mỗi tệp một dòng riêng).
    valid_files: list[dict] = []
    for file in raw_files:
        size = _data_url_size(file.get("dataUrl"))
        if size > _MAX_FILE_BYTES:
            errors.append(
                f"File '{file['name']}' vượt quá 6 MB ({_mb(size)}) — cổng Lào Cai không nhận, đã bỏ "
                "qua. Hãy nén PDF hoặc quét lại ở DPI thấp hơn rồi đính bổ sung."
            )
        else:
            valid_files.append(file)

    from app.services import ocr

    ocr_files = [f for f in valid_files if f.get("type") in _OCR_TYPES]
    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    by_name = {item.get("name"): item for item in ocr_results}
    llm_documents = [
        {"index": index, "text": str(by_name.get(file.get("name"), {}).get("text") or "")}
        for index, file in enumerate(valid_files)
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

    attachments, warnings, classified = build_plan_items(valid_files, llm_types)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [valid_files[d["index"]]["name"] for d in llm_documents],
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "ocr_text": join_ocr_documents(ocr_results),
        "errors": errors,
    }

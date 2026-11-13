"""Đính kèm KHÔNG TÁCH cho "Đăng ký đất đai lần đầu ... Nhà nước giao đất để quản lý" (1.012756, cổng DVC Đà Nẵng,
engine FE `attp-row`) — cài đặt "Tách giấy tờ" tắt.

OCR từng tệp như chế độ tách → MỘT lượt LLM liệt kê mọi loại giấy trong từng tệp → MỖI TỆP ĐÍNH NGUYÊN, MỘT LẦN (không
`sourceSegments`) vào dòng của giấy chính. Bảng 2 dòng + ánh xạ dùng chung với chế độ tách (`_ROWS`, `_ROW_OF_TYPE`):
  [1] Đơn Mẫu 15 + giấy kèm theo mục 5 của Đơn (quyết định, hợp đồng thuê đất, biên bản giao đất, GCN ĐKDN, phiếu đo
      đạc, giấy tờ thuế, tờ khai LPTB, ủy quyền, giấy tờ khác)
  [2] Báo cáo rà soát hiện trạng Mẫu 15đ + trích lục / mảnh trích đo
Giấy chính: Đơn trước, Báo cáo rà soát sau, rồi giấy đính kèm chung (theo thứ tự `types` của dòng), CCCD cuối. Tệp gộp
giấy của cả hai dòng → đính dòng của giấy chính + cảnh báo. CCCD / chưa rõ loại / OCR rỗng / LLM lỗi → dòng 1. Tên tệp
đánh số D1-01, D2-01 … như chế độ tách (FE chống đính trùng theo tên); tệp gộp hai dòng / chưa rõ loại giữ tên gốc sau
tiền tố. Không bỏ tệp nào.
"""

from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.attach.dinh_kem_khong_tach.planner import (  # noqa: E501
    merged_file_warning,
    plan_whole_files,
    primary,
    shared_row_warning,
)
from app.process.schemas import FileItem

from ..dinh_kem_tach.planner import (
    _BAO_CAO,
    _CCCD,
    _DON15,
    _KHAC,
    _OTHER,
    _ROW_OF_TYPE,
    _ROWS,
    _TRICH_LUC,
    _TYPE_NAMES,
    _file_name,
    _normalize_type,
)
from .prompt import SYSTEM_PROMPT, build_user_prompt

_FALLBACK_ROW = 1
_PRIORITY: tuple[str, ...] = tuple(dict.fromkeys((
    _DON15,
    _BAO_CAO,
    *(doc_type for doc_type in _ROWS[1]["types"] if doc_type != _KHAC),
    *_ROWS[2]["types"],
    _KHAC,
    _CCCD,
)))


def build_plan_items(
    raw_files: list[dict], types_by_file: dict[int, list[str]],
) -> tuple[list[dict], list[dict], list[str]]:
    """Mỗi tệp → đúng một mục attp-row (không sourceSegments). Thuần tất định, không gọi OCR/LLM."""
    entries = []
    for index, file in enumerate(raw_files):
        doc_types = types_by_file.get(index, [])
        doc_type = primary(doc_types, _PRIORITY, _OTHER)
        row_idx = _ROW_OF_TYPE.get(doc_type, _FALLBACK_ROW)
        others = sorted({_ROW_OF_TYPE[item] for item in doc_types if item in _ROW_OF_TYPE} - {row_idx})
        entries.append((index, str(file.get("name") or f"file-{index + 1}"), doc_type, doc_types, row_idx, others))

    attachments: list[dict] = []
    classified: list[dict] = []
    warnings: list[str] = []
    shared: list[str] = []
    for row_idx in sorted(_ROWS):
        row = _ROWS[row_idx]
        order = {doc_type: i for i, doc_type in enumerate(row["types"])}
        parts = sorted((e for e in entries if e[4] == row_idx), key=lambda e: (order.get(e[2], 99), e[0]))
        for position, (index, file_name, doc_type, doc_types, _, others) in enumerate(parts, start=1):
            base = file_name if others or doc_type not in _TYPE_NAMES else _TYPE_NAMES[doc_type]
            attachments.append({
                "fileIndex": index,
                "fileName": file_name,
                "documentName": _file_name(row_idx, position, base, file_name),
                "componentName": row["componentName"],
                "componentIndex": row_idx,
                "loaiBan": row["loaiBan"],
                "target": "attp-row",
                "needsAddComponent": False,
                "detectedType": doc_type,
                "includedTypes": doc_types or [doc_type],
            })
            classified.append({"fileIndex": index, "fileName": file_name, "docType": doc_type, "docTypes": doc_types,
                               "source": "llm" if index in types_by_file else "unknown", "componentIndex": row_idx})
            if others:
                warnings.append(merged_file_warning(file_name, row_idx, row["documentName"], others))
            elif doc_type not in _ROW_OF_TYPE:
                shared.append(file_name)

    if shared:
        warnings.append(shared_row_warning(_ROWS[_FALLBACK_ROW]["componentName"], shared))
    found = {item for doc_types in types_by_file.values() for item in doc_types}
    if types_by_file and _DON15 not in found:
        warnings.append("Không tìm thấy Đơn đăng ký đất đai, tài sản gắn liền với đất Mẫu số 15 (dòng 1, bắt buộc) "
                        "— vui lòng đính tay.")
    if types_by_file and _BAO_CAO not in found:
        warnings.append("Không tìm thấy Báo cáo kết quả rà soát hiện trạng sử dụng đất Mẫu số 15đ (dòng 2, bắt "
                        "buộc) — vui lòng đính tay.")
    elif types_by_file and _TRICH_LUC not in found:
        warnings.append("Chưa thấy trích lục bản đồ địa chính / mảnh trích đo thửa đất kèm Báo cáo rà soát (dòng 2) "
                        "— kiểm tra, bổ sung nếu có.")
    return attachments, classified, warnings


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options  # chế độ không tách không cần cài đặt nào khác.
    result = await plan_whole_files(
        files, session, system_prompt=SYSTEM_PROMPT, user_prompt=build_user_prompt, normalize=_normalize_type,
        build_items=build_plan_items,
    )
    result["extracted"]["rows"] = [{"componentIndex": k, **{n: v for n, v in row.items() if n != "types"}}
                                   for k, row in _ROWS.items()]
    return result

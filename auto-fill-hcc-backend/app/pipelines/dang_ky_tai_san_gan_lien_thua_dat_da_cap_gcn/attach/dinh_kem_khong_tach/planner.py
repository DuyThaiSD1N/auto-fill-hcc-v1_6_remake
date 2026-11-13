"""Đính kèm KHÔNG TÁCH cho "Đăng ký tài sản gắn liền với thửa đất đã được cấp GCN..." (1.013995, cổng DVC Đà Nẵng,
engine FE `attp-row`) — cài đặt "Tách giấy tờ" tắt.

OCR từng tệp như chế độ tách → MỘT lượt LLM liệt kê mọi loại giấy trong từng tệp → MỖI TỆP ĐÍNH NGUYÊN, MỘT LẦN (không
`sourceSegments`) vào dòng của giấy chính. Bảng 8 dòng dùng chung với chế độ tách (`_ROWS` của dinh_kem_tach):
  Đơn Mẫu 18 → 1 · GCN đã cấp → 2 · giấy tờ Điều 148, 149 → 3 · sơ đồ công trình → 4 · hồ sơ thiết kế đã thẩm định →
  5 · văn bản gia hạn sở hữu nhà ở → 6 · mảnh trích đo → 7 · văn bản đại diện → 8.
Giấy chính: Đơn trước, rồi các giấy có dòng riêng theo thứ tự dòng, CCCD cuối. Tệp gộp giấy của nhiều dòng → cảnh báo.
CCCD / chưa rõ loại / OCR rỗng / LLM lỗi → dòng 1 (Đơn) như chế độ tách, giữ tên gốc. Không bỏ tệp nào.
"""

from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.attach.dinh_kem_khong_tach.planner import (  # noqa: E501
    merged_file_warning,
    plan_whole_files,
    primary,
    shared_row_warning,
)
from app.process.schemas import FileItem

from ..dinh_kem_tach.planner import (
    _CCCD,
    _DON18,
    _GCN,
    _GIAY_TO_148,
    _OTHER,
    _ROWS,
    _SO_DO,
    _normalize_type,
    _unique_name,
)
from .prompt import SYSTEM_PROMPT, build_user_prompt

_FALLBACK = _DON18
# _ROWS xếp theo thứ tự dòng, Đơn đứng đầu.
_PRIORITY: tuple[str, ...] = (*_ROWS, _CCCD)


def build_plan_items(
    raw_files: list[dict], types_by_file: dict[int, list[str]],
) -> tuple[list[dict], list[dict], list[str]]:
    """Mỗi tệp → đúng một mục attp-row (không sourceSegments). Thuần tất định, không gọi OCR/LLM."""
    attachments: list[dict] = []
    classified: list[dict] = []
    warnings: list[str] = []
    shared: list[str] = []
    used_names: set[str] = set()
    for index, file in enumerate(raw_files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        doc_types = types_by_file.get(index, [])
        doc_type = primary(doc_types, _PRIORITY, _OTHER)
        row = _ROWS.get(doc_type, _ROWS[_FALLBACK])
        others = sorted({_ROWS[item]["componentIndex"] for item in doc_types if item in _ROWS}
                        - {row["componentIndex"]})
        base = row["documentName"] if doc_type in _ROWS and not others else file_name
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": _unique_name(base, used_names, file_name),
            "componentName": row["componentName"],
            "componentIndex": row["componentIndex"],
            "loaiBan": row["loaiBan"],
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": doc_type,
        })
        classified.append({"fileIndex": index, "fileName": file_name, "docType": doc_type, "docTypes": doc_types,
                           "source": "llm" if index in types_by_file else "unknown",
                           "componentIndex": row["componentIndex"]})
        if others:
            warnings.append(merged_file_warning(file_name, row["componentIndex"], row["documentName"], others))
        elif doc_type not in _ROWS:
            shared.append(file_name)

    if shared:
        warnings.append(shared_row_warning(_ROWS[_FALLBACK]["componentName"], shared))
    found = {item for doc_types in types_by_file.values() for item in doc_types}
    if types_by_file and _DON18 not in found:
        warnings.append("Không tìm thấy Đơn đăng ký biến động Mẫu số 18 (dòng 1, bắt buộc) — vui lòng đính tay.")
    if types_by_file and _GCN not in found:
        warnings.append("Không tìm thấy Giấy chứng nhận đã cấp (dòng 2, bắt buộc) — vui lòng đính tay.")
    if types_by_file and not found & {_GIAY_TO_148, _SO_DO}:
        warnings.append(
            "Hồ sơ chưa có Sơ đồ nhà ở, công trình xây dựng (dòng 4) hay giấy tờ theo Điều 148, 149 Luật Đất đai "
            "(dòng 3) — kiểm tra, bổ sung sơ đồ công trình nếu tài sản đăng ký chưa có trong GCN."
        )
    return attachments, classified, warnings


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options  # chế độ không tách không cần cài đặt nào khác.
    result = await plan_whole_files(
        files, session, system_prompt=SYSTEM_PROMPT, user_prompt=build_user_prompt, normalize=_normalize_type,
        build_items=build_plan_items,
    )
    result["extracted"]["rows"] = [{"docType": k, **v} for k, v in _ROWS.items()]
    return result

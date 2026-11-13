"""Đính kèm KHÔNG TÁCH cho "Xác định lại diện tích đất ở (GCN cấp trước 01/7/2004)" (cổng DVC Đà Nẵng, engine FE
`attp-row`) — cài đặt "Tách giấy tờ" tắt.

OCR từng tệp như chế độ tách → MỘT lượt LLM liệt kê mọi loại giấy trong từng tệp → MỖI TỆP ĐÍNH NGUYÊN, MỘT LẦN (không
`sourceSegments`) vào dòng của giấy chính. Bảng 3 dòng + ánh xạ dùng chung với chế độ tách (`_ROWS`, `_ROW_BY_TYPE`):
  GCN đã cấp → 1 · văn bản đại diện → 2 · Đơn và mọi giấy khác (bản mô tả ranh giới, công văn, phiếu đo đạc, CCCD…) → 3.
Giấy chính: Đơn trước, rồi GCN, văn bản đại diện, rồi giấy đính chung dòng 3. Tệp gộp giấy của nhiều dòng (vd Đơn + GCN)
→ đính dòng của Đơn + cảnh báo. Chưa rõ loại / OCR rỗng / LLM lỗi → dòng 3, giữ tên gốc. Không bỏ tệp nào.
"""

from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.attach.dinh_kem_khong_tach.planner import (  # noqa: E501
    merged_file_warning,
    plan_whole_files,
    primary,
)
from app.process.schemas import FileItem

from ..dinh_kem_tach.planner import (
    _BLANK,
    _CCCD,
    _CO_QUAN,
    _DAI_DIEN,
    _DO_DAC,
    _DON,
    _GCN,
    _MO_TA,
    _OTHER,
    _ROW_BY_TYPE,
    _ROW_DON,
    _ROWS,
    _don_group_name,
    _normalize_type,
    _unique_name,
)
from .prompt import SYSTEM_PROMPT, build_user_prompt

_PRIORITY: tuple[str, ...] = (_DON, _GCN, _DAI_DIEN, _MO_TA, _CO_QUAN, _DO_DAC, _CCCD)


def build_plan_items(
    raw_files: list[dict], types_by_file: dict[int, list[str]],
) -> tuple[list[dict], list[dict], list[str]]:
    """Mỗi tệp → đúng một mục attp-row (không sourceSegments). Thuần tất định, không gọi OCR/LLM."""
    attachments: list[dict] = []
    classified: list[dict] = []
    warnings: list[str] = []
    unknown: list[str] = []
    used_names: set[str] = set()
    for index, file in enumerate(raw_files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        doc_types = [item for item in types_by_file.get(index, []) if item != _BLANK]
        doc_type = primary(doc_types, _PRIORITY, _OTHER)
        row_idx = _ROW_BY_TYPE.get(doc_type, _ROW_DON)
        spec = _ROWS[row_idx]
        others = sorted({_ROW_BY_TYPE.get(item, _ROW_DON) for item in doc_types if item != _OTHER} - {row_idx})
        if others or doc_type == _OTHER:
            base = file_name
        elif row_idx == _ROW_DON:
            base = _don_group_name([{"type": item, "documentName": ""} for item in doc_types if item != _OTHER])
        else:
            base = spec["documentName"]
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": _unique_name(base, used_names, spec["documentName"]),
            "componentName": spec["componentName"],
            "componentIndex": spec["componentIndex"],
            "loaiBan": "Bản chính",
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": doc_type,
        })
        classified.append({"fileIndex": index, "fileName": file_name, "docType": doc_type, "docTypes": doc_types,
                           "source": "llm" if index in types_by_file else "unknown",
                           "componentIndex": spec["componentIndex"]})
        if others:
            warnings.append(merged_file_warning(file_name, row_idx, spec["documentName"], others))
        elif doc_type == _OTHER:
            unknown.append(file_name)

    if unknown:
        warnings.append(f"Chưa nhận diện chắc loại giấy tờ, đã đính chung dòng {_ROW_DON} "
                        f"\"{_ROWS[_ROW_DON]['componentName']}\": " + "; ".join(unknown) + ".")
    found = {item for doc_types in types_by_file.values() for item in doc_types}
    if types_by_file and _GCN not in found:
        warnings.append(
            "Hồ sơ chưa có bản scan Giấy chứng nhận đã cấp (dòng 1 'Bản gốc Giấy chứng nhận đã cấp'). Bổ "
            "sung bản scan hoặc dùng nút 'Lấy giấy tờ từ kho' trước khi nộp."
        )
    if types_by_file and _DON not in found:
        warnings.append(
            "Không nhận ra Đơn đăng ký biến động đất đai trong hồ sơ — các giấy tờ vẫn được đính chung ở dòng "
            "3, cán bộ kiểm tra lại đã có Đơn chưa."
        )
    return attachments, classified, warnings


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options  # chế độ không tách không cần cài đặt nào khác.
    return await plan_whole_files(
        files, session, system_prompt=SYSTEM_PROMPT, user_prompt=build_user_prompt, normalize=_normalize_type,
        build_items=build_plan_items,
    )

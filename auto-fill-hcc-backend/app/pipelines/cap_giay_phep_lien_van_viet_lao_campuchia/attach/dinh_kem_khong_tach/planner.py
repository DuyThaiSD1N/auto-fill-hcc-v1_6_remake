"""Đính kèm "Cấp, cấp lại Giấy phép liên vận giữa Việt Nam, Lào và Campuchia" (1.002877, attp-row 7 dòng) — chế độ KHÔNG
tách giấy tờ.

Cài đặt "Tách giấy tờ" tắt (hoặc client cũ): OCR từng tệp, MỘT lượt LLM liệt kê mọi loại giấy có trong từng tệp
(docTypes), rồi MỖI TỆP đính NGUYÊN, MỘT lần (không `sourceSegments`), vào dòng của giấy chính theo _PRIORITY: Giấy đề nghị
trước, rồi đăng ký xe, tài liệu quyền sử dụng xe, hợp đồng dự án; CCCD, giấy chưa rõ cuối (về dòng Giấy đề nghị). Bảng
dòng, nhóm thương mại / phi thương mại, dòng bỏ tick lấy từ chế độ tách nên hai chế độ đặt cùng dòng. Tệp gộp nhiều giấy
có dòng riêng → cảnh báo. OCR rỗng / LLM lỗi → tệp về dòng Giấy đề nghị, giữ tên gốc + cảnh báo. Không bỏ tệp nào.
"""

from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.attach.dinh_kem_khong_tach.planner import (
    gop_warning,
    run_plan,
)
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.attach.dinh_kem_tach.planner import (
    _unique_name,
)
from app.process.schemas import FileItem

from ..dinh_kem_tach.planner import (
    _CCCD,
    _DANG_KY_XE,
    _DE_NGHI,
    _EXTRA_NAMES,
    _HOP_DONG,
    _OTHER,
    _QUYEN_SU_DUNG,
    ROWS,
    _normalize_type,
    _rule_type,
    has_own_row,
    is_thuong_mai,
    missing_warnings,
    route,
    untick_rows,
)
from .prompt import SYSTEM_PROMPT, build_user_prompt

# Tệp gộp nhiều giấy: dòng của giấy ĐỨNG TRƯỚC nhận nguyên tệp.
_PRIORITY = (_DE_NGHI, _DANG_KY_XE, _QUYEN_SU_DUNG, _HOP_DONG, _CCCD, _OTHER)


def primary(types: list[str]) -> str:
    return next((t for t in _PRIORITY if t in types), _OTHER)


def build_plan_items(
    raw_files: list[dict],
    types_by_file: dict[int, list[str]],
    texts: dict[int, str] | None = None,
) -> tuple[list[dict], list[dict], list[str]]:
    """{fileIndex: docTypes} → (attachments, classified, warnings). Thuần tất định, không gọi OCR/LLM."""
    texts = texts or {}
    # Nhóm theo tiêu đề Giấy đề nghị: chỉ đọc tệp có Giấy đề nghị (giấy xe / hợp đồng không quyết định nhóm).
    thuong_mai = is_thuong_mai(texts.get(i, "") for i, types in types_by_file.items() if _DE_NGHI in types)
    attachments: list[dict] = []
    classified: list[dict] = []
    warnings: list[str] = []
    shared: list[str] = []
    used_names: set[str] = set()
    found: set[str] = set()

    for index, file in enumerate(raw_files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        types = types_by_file.get(index) or [_OTHER]
        found.update(types)
        doc_type = primary(types)
        row_idx = route(doc_type, thuong_mai)
        other_rows = sorted({route(t, thuong_mai) for t in types if has_own_row(t, thuong_mai)} - {row_idx})
        row = ROWS[row_idx]
        own = has_own_row(doc_type, thuong_mai)
        # Tệp gộp / chưa rõ loại giữ TÊN GỐC để cán bộ nhận ra; tệp một giấy mang tên giấy.
        if other_rows or not own:
            base_name = file_name
        else:
            base_name = _EXTRA_NAMES.get(doc_type, row["documentName"])
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": _unique_name(base_name.replace("/", "-"), used_names, row["documentName"]),
            "loaiBan": row["loaiBan"],
            "detectedType": doc_type,
            "includedTypes": types,
            "componentName": row["componentName"],
            "componentIndex": row_idx,
            "target": "attp-row",
            "needsAddComponent": False,
        })
        classified.append({"fileIndex": index, "fileName": file_name, "type": doc_type, "docTypes": types,
                           "source": "llm" if index in types_by_file else "unknown", "componentIndex": row_idx})
        if not own:
            shared.append(file_name)
        if other_rows:
            warnings.append(gop_warning(file_name, row_idx, row["componentName"], other_rows))

    order = {t: i for i, t in enumerate(_PRIORITY)}
    attachments.sort(key=lambda a: (a["componentIndex"], order.get(a["detectedType"], 99), a["fileIndex"]))
    # Tệp gộp có hợp đồng dự án nhưng đính nguyên ở dòng Giấy đề nghị: dòng 4 không có tệp → vẫn bỏ tick theo dòng thực đính.
    planned_rows = {a["componentIndex"] for a in attachments}
    if attachments and (untick := untick_rows(planned_rows, thuong_mai)):
        attachments[0]["untickRows"] = untick
    if types_by_file:
        warnings.extend(w for w in missing_warnings(found, thuong_mai)
                        if not (w.startswith("Không có hợp đồng") and _HOP_DONG in found))
    if shared:
        warnings.append("Giấy tờ không có dòng riêng (CCCD, giấy chưa rõ loại) đã đính chung dòng "
                        f"{route(_DE_NGHI, thuong_mai)} Giấy đề nghị: " + ", ".join(shared))
    return attachments, classified, warnings


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    result = await run_plan(
        files, session,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=build_user_prompt,
        normalize=_normalize_type,
        rule_type=_rule_type,
        build_items=build_plan_items,
        rows=[{"componentIndex": k, **row} for k, row in ROWS.items()],
    )
    result["extracted"]["thuongMai"] = any(a["componentIndex"] in (2, 6) for a in result["attachments"])
    return result

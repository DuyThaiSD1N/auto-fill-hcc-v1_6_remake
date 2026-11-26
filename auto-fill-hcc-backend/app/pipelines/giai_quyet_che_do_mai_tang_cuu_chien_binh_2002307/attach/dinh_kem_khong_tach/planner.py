"""Đính kèm "Giải quyết chế độ mai táng phí đối với cựu chiến binh" (2.002307, attp-row 3 dòng) — chế độ KHÔNG tách giấy
tờ.

Cài đặt "Tách giấy tờ" tắt (hoặc client cũ): OCR từng tệp, MỘT lượt LLM liệt kê mọi loại giấy có trong từng tệp
(docTypes), rồi MỖI TỆP đính NGUYÊN, MỘT lần (không `sourceSegments`), vào dòng của giấy chính theo _PRIORITY: Bản khai
trước, rồi trích lục khai tử, giấy xác nhận cựu chiến binh; CCCD, giấy chưa rõ cuối (về dòng 1). Bảng dòng, loại bản lấy
từ chế độ tách nên hai chế độ đặt cùng dòng. Tệp gộp nhiều giấy có dòng riêng → cảnh báo. Tệp trùng nội dung các tệp
khác (bộ hồ sơ gộp tải lên cùng các tệp lẻ) → không đính thêm. OCR rỗng / LLM lỗi → tệp về dòng 1, giữ tên gốc + cảnh
báo.
"""

from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.attach.dinh_kem_khong_tach.planner import (
    gop_warning,
    run_plan,
)
from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.attach.dinh_kem_tach.planner import _split_ocr_pages
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.attach.dinh_kem_tach.planner import (
    _unique_name,
)
from app.process.schemas import FileItem

from ..dinh_kem_tach.planner import (
    _BAN_KHAI,
    _CCCD,
    _EXTRA_NAMES,
    _OTHER,
    _ROUTE,
    _ROWS,
    _TRICH_LUC,
    _XAC_NHAN_CCB,
    _normalize_type,
    _rule_type,
    duplicate_files,
    duplicate_warnings,
    missing_warnings,
)
from .prompt import SYSTEM_PROMPT, build_user_prompt

_FALLBACK_ROW = 1
# Tệp gộp nhiều giấy: dòng của giấy ĐỨNG TRƯỚC nhận nguyên tệp.
_PRIORITY = (_BAN_KHAI, _TRICH_LUC, _XAC_NHAN_CCB, _CCCD, _OTHER)
_NAMES = {
    _BAN_KHAI: _ROWS[1]["documentName"],
    _TRICH_LUC: _ROWS[2]["documentName"],
    _XAC_NHAN_CCB: _ROWS[3]["documentName"],
    **_EXTRA_NAMES,
}


def primary(types: list[str]) -> str:
    return next((t for t in _PRIORITY if t in types), _OTHER)


def build_plan_items(
    raw_files: list[dict],
    types_by_file: dict[int, list[str]],
    texts: dict[int, str] | None = None,
) -> tuple[list[dict], list[dict], list[str]]:
    """{fileIndex: docTypes} → (attachments, classified, warnings). Thuần tất định, không gọi OCR/LLM."""
    dropped = duplicate_files({i: _split_ocr_pages(t, 1)[0] for i, t in (texts or {}).items()})
    attachments: list[dict] = []
    classified: list[dict] = []
    warnings: list[str] = []
    shared: list[str] = []
    used_names: set[str] = set()
    found_rows: set[int] = set()

    for index, file in enumerate(raw_files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        types = types_by_file.get(index) or [_OTHER]
        doc_type = primary(types)
        row_idx = _ROUTE.get(doc_type, _FALLBACK_ROW)
        entry = {"fileIndex": index, "fileName": file_name, "type": doc_type, "docTypes": types,
                 "source": "llm" if index in types_by_file else "unknown", "componentIndex": row_idx}
        if index in dropped:
            classified.append({**entry, "duplicateOf": dropped[index]})
            continue
        other_rows = sorted({_ROUTE[t] for t in types if t in _ROUTE} - {row_idx})
        # Giấy trong tệp gộp vẫn tính là có (không báo thiếu dòng của nó).
        found_rows.update(_ROUTE[t] for t in types if t in _ROUTE)
        found_rows.add(row_idx)
        row = _ROWS[row_idx]
        # Tệp gộp / chưa rõ loại giữ TÊN GỐC để cán bộ nhận ra; tệp một giấy mang tên giấy.
        base_name = _NAMES[doc_type] if doc_type in _NAMES and not other_rows else file_name
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
        classified.append(entry)
        if doc_type not in _ROUTE:
            shared.append(file_name)
        if other_rows:
            warnings.append(gop_warning(file_name, row_idx, row["componentName"], other_rows))

    order = {t: i for i, t in enumerate(_PRIORITY)}
    attachments.sort(key=lambda a: (a["componentIndex"], order.get(a["detectedType"], 99), a["fileIndex"]))
    if types_by_file:
        warnings.extend(missing_warnings(found_rows))
    warnings.extend(duplicate_warnings(raw_files, dropped))
    if shared:
        warnings.append("Giấy tờ không có dòng riêng (CCCD, giấy chưa rõ loại) đã đính chung dòng 1 Bản khai: "
                        + ", ".join(shared))
    return attachments, classified, warnings


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    del options
    return await run_plan(
        files, session,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=build_user_prompt,
        normalize=_normalize_type,
        rule_type=_rule_type,
        build_items=build_plan_items,
        rows=[{"componentIndex": k, **row} for k, row in _ROWS.items()],
    )

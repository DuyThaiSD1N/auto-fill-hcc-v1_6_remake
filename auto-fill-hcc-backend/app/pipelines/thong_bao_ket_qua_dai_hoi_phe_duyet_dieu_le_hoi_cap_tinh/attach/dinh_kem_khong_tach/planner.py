"""Đính kèm "Thông báo kết quả đại hội và phê duyệt đổi tên hội, phê duyệt điều lệ hội (cấp tỉnh)" (1.012943, attp-row)
— chế độ KHÔNG tách giấy tờ.

Cài đặt "Tách giấy tờ" tắt (hoặc client cũ): OCR từng tệp như chế độ tách, MỘT lượt LLM liệt kê mọi loại giấy có trong
từng tệp (docTypes), rồi MỖI TỆP đính NGUYÊN, MỘT lần (không `sourceSegments`), vào dòng của giấy chính theo _PRIORITY:
Tờ trình / văn bản báo cáo kết quả đại hội và Đơn đổi tên trước; biên bản, nghị quyết, điều lệ, chương trình hoạt động,
sơ yếu lý lịch / LLTP sau; danh sách nhân sự, Báo cáo tổng kết (đính tạm dòng 6), CCCD, giấy chưa rõ cuối. Bảng 7 dòng,
ánh xạ loại → dòng (_ROUTE, danh sách "kèm theo tờ trình" về dòng 1) và `untickRows` của dòng điều kiện lấy từ chế độ
tách nên hai chế độ đặt cùng dòng. Tệp gộp nhiều giấy có dòng riêng → cảnh báo.

OCR rỗng / LLM lỗi → tệp về dòng 1 (văn bản báo cáo kết quả đại hội), giữ tên gốc + cảnh báo. Không bỏ tệp nào.
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
    _BAO_CAO,
    _BIEN_BAN,
    _CCCD,
    _CONDITIONAL_ROWS,
    _CT_HD,
    _DANH_SACH,
    _DIEU_LE,
    _DOI_TEN,
    _LLTP,
    _NQ,
    _OTHER,
    _REQUIRED,
    _ROUTE,
    _ROWS,
    _SYLL,
    _TONG_KET,
    _attached_to_report,
    _normalize_type,
    _rule_type,
)
from .prompt import SYSTEM_PROMPT, build_user_prompt

# Dòng dự phòng của chế độ tách cho CCCD / giấy chưa rõ loại.
_FALLBACK_ROW = 1
# Tệp gộp nhiều giấy: dòng của giấy ĐỨNG TRƯỚC nhận nguyên tệp.
_PRIORITY = (_BAO_CAO, _DOI_TEN, _BIEN_BAN, _NQ, _DIEU_LE, _CT_HD, _SYLL, _LLTP, _DANH_SACH, _TONG_KET, _CCCD, _OTHER)
_NAMES = {
    _BAO_CAO: "Văn bản báo cáo kết quả đại hội",
    _DOI_TEN: "Đơn đề nghị đổi tên hội",
    _BIEN_BAN: "Biên bản đại hội",
    _DANH_SACH: "Danh sách Ban chấp hành",
    _DIEU_LE: "Dự thảo điều lệ",
    _NQ: "Nghị quyết đại hội",
    _CT_HD: "Chương trình hoạt động của hội",
    _TONG_KET: "Báo cáo tổng kết nhiệm kỳ",
    _SYLL: "Sơ yếu lý lịch",
    _LLTP: "Phiếu lý lịch tư pháp số 1",
}


def primary(types: list[str]) -> str:
    return next((t for t in _PRIORITY if t in types), _OTHER)


def build_plan_items(
    raw_files: list[dict],
    types_by_file: dict[int, list[str]],
    texts: dict[int, str] | None = None,
) -> tuple[list[dict], list[dict], list[str]]:
    """{fileIndex: docTypes} → (attachments, classified, warnings). Thuần tất định, không gọi OCR/LLM."""
    texts = texts or {}
    found = {t for types in types_by_file.values() for t in types}
    has_report = _BAO_CAO in found
    attachments: list[dict] = []
    classified: list[dict] = []
    warnings: list[str] = []
    shared: list[str] = []
    used_names: set[str] = set()

    for index, file in enumerate(raw_files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        types = types_by_file.get(index) or [_OTHER]
        doc_type = primary(types)
        # Danh sách ghi "(Kèm theo tờ trình …)" đi chung dòng văn bản báo cáo (như chế độ tách).
        to_report = has_report and _attached_to_report(texts.get(index, ""))

        def route(t: str) -> int | None:
            return 1 if t == _DANH_SACH and to_report else _ROUTE.get(t)

        own_row = route(doc_type)
        row_idx = own_row or _FALLBACK_ROW
        row = _ROWS[row_idx]
        other_rows = sorted({r for r in map(route, types) if r} - {row_idx})
        # Tệp gộp hoặc chưa rõ loại giữ TÊN GỐC để cán bộ nhận ra; tệp một giấy mang tên giấy.
        base_name = file_name if other_rows or own_row is None else _NAMES.get(doc_type, row["documentName"])
        attachments.append({
            "fileIndex": index,
            "fileName": file_name,
            "documentName": _unique_name(base_name.replace("/", "-"), used_names, row["documentName"]),
            "loaiBan": "Bản chính",
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": doc_type,
            "includedTypes": types,
            "componentName": row["componentName"],
            "componentIndex": row_idx,
        })
        classified.append({"fileIndex": index, "fileName": file_name, "type": doc_type, "docTypes": types,
                           "componentIndex": row_idx, "source": "llm" if index in types_by_file else "unknown",
                           **({} if own_row else {"routedTo": row_idx})})
        if own_row is None:
            shared.append(file_name)
        if other_rows:
            warnings.append(gop_warning(file_name, row_idx, row["componentName"], other_rows))

    order = {t: i for i, t in enumerate(_PRIORITY)}
    attachments.sort(key=lambda a: (a["componentIndex"], order.get(a["detectedType"], 99), a["fileIndex"]))
    used_rows = {a["componentIndex"] for a in attachments}
    # Dòng điều kiện cổng có thể tick sẵn (dòng 7) mà không có tệp nào → bỏ tick (như chế độ tách).
    untick = [_ROWS[idx]["componentName"] for idx in _CONDITIONAL_ROWS if idx not in used_rows]
    if attachments and untick:
        attachments[0]["untickRows"] = untick

    # --- Cảnh báo ---
    if shared:
        warnings.append("Giấy tờ không có dòng riêng hoặc chưa rõ loại đã đính chung dòng "
                        f"\"{_ROWS[_FALLBACK_ROW]['componentName']}\" (dòng {_FALLBACK_ROW}): " + ", ".join(shared))
    if types_by_file:
        found_rows = {_ROUTE[t] for t in found if t in _ROUTE}
        for row_idx, label in _REQUIRED:
            if row_idx not in found_rows:
                warnings.append(f"Chưa có {label} (dòng {row_idx}) — cần bổ sung.")
        if 6 in used_rows and _CT_HD not in found:
            warnings.append("Hồ sơ không có Chương trình hoạt động riêng — dòng 6 đính tạm Báo cáo tổng kết (phần "
                            "phương hướng nhiệm vụ); nên bổ sung Chương trình hoạt động của hội.")
        if 7 not in used_rows and (_SYLL in found or _LLTP in found):
            warnings.append("Sơ yếu lý lịch / phiếu lý lịch tư pháp nằm trong tệp gộp đã đính ở dòng khác — dòng 7 "
                            "không có tệp nên đã bỏ tick; bật \"Tách giấy tờ\" nếu cần nộp riêng ở dòng 7.")
        elif 7 not in used_rows:
            warnings.append("Không có sơ yếu lý lịch, phiếu lý lịch tư pháp số 1 của Chủ tịch — đã bỏ tick dòng 7; "
                            "chỉ cần nộp khi Chủ tịch không phải nhân sự dự kiến đã báo cáo cơ quan nhà nước.")
        if _SYLL in found and _LLTP not in found:
            warnings.append("Chưa có Phiếu lý lịch tư pháp số 1 của Chủ tịch hội (dòng 7) — cần bổ sung, trừ khi người "
                            "đó là cán bộ, công chức, viên chức (kể cả đã nghỉ hưu) được cơ quan có thẩm quyền đồng ý.")
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

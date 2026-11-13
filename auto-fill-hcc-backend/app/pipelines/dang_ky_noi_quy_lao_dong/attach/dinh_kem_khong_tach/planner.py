"""Đính kèm "Đăng ký nội quy lao động của doanh nghiệp" (2.001955, attp-row + modal "Thêm giấy tờ") — chế độ KHÔNG tách
giấy tờ.

Cài đặt "Tách giấy tờ" tắt (hoặc client cũ): OCR từng tệp như chế độ tách, MỘT lượt LLM liệt kê mọi loại giấy có trong
từng tệp (docTypes), rồi MỖI TỆP đính NGUYÊN, MỘT lần (không `sourceSegments`), vào dòng của giấy chính theo _PRIORITY:
Văn bản đề nghị trước; Quyết định ban hành, Nội quy, góp ý, quy định kỷ luật, Giấy ủy quyền (dòng tạo qua "+ Thêm giấy
tờ") sau; GCN đăng ký doanh nghiệp, CCCD, giấy chưa rõ cuối. Bảng 4 dòng, ánh xạ loại → dòng (_ROUTE) và item modal Giấy
ủy quyền (`add-document-dialog`, `fallbackComponentName` = dòng 4) lấy từ chế độ tách nên hai chế độ đặt cùng dòng. Mỗi
tệp Giấy ủy quyền là một item modal riêng (FE chỉ tạo dòng một lần theo componentName). Tệp gộp nhiều giấy có dòng
riêng → cảnh báo.

OCR rỗng / LLM lỗi → tệp về dòng 1 (Nội quy lao động), giữ tên gốc + cảnh báo. Không bỏ tệp nào.
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
    _DE_NGHI,
    _DKDN,
    _EXTRA_NAMES,
    _GOP_Y,
    _KY_LUAT,
    _NOI_QUY,
    _OTHER,
    _QUYET_DINH,
    _ROUTE,
    _ROW_UY_QUYEN,
    _ROWS,
    _UY_QUYEN,
    _normalize_type,
    _rule_type,
)
from .prompt import SYSTEM_PROMPT, build_user_prompt

# Dòng dự phòng của chế độ tách cho GCN ĐKDN / CCCD / giấy chưa rõ loại; dòng nhận Giấy ủy quyền khi modal hỏng.
_FALLBACK_ROW = 1
_UY_QUYEN_FALLBACK_ROW = 4
# Tệp gộp nhiều giấy: dòng của giấy ĐỨNG TRƯỚC nhận nguyên tệp.
_PRIORITY = (_DE_NGHI, _QUYET_DINH, _NOI_QUY, _GOP_Y, _KY_LUAT, _UY_QUYEN, _DKDN, _CCCD, _OTHER)
_NAMES = {
    _DE_NGHI: "Văn bản đề nghị đăng ký nội quy lao động",
    _QUYET_DINH: "Quyết định ban hành Nội quy lao động",
    _NOI_QUY: "Nội quy lao động",
    _GOP_Y: "Văn bản góp ý của tổ chức đại diện NLĐ",
    _KY_LUAT: "Văn bản về kỷ luật lao động, trách nhiệm vật chất",
    _UY_QUYEN: _ROW_UY_QUYEN["documentName"],
    **_EXTRA_NAMES,
}
_DIALOG = "Giấy ủy quyền (+ Thêm giấy tờ)"


def primary(types: list[str]) -> str:
    return next((t for t in _PRIORITY if t in types), _OTHER)


def _slot(doc_type: str) -> int | str | None:
    """Dòng riêng của loại giấy: STT dòng cố định, "Thêm giấy tờ" cho Giấy ủy quyền, None nếu không có dòng."""
    return _DIALOG if doc_type == _UY_QUYEN else _ROUTE.get(doc_type)


def build_plan_items(
    raw_files: list[dict],
    types_by_file: dict[int, list[str]],
    texts: dict[int, str] | None = None,
) -> tuple[list[dict], list[dict], list[str]]:
    """{fileIndex: docTypes} → (attachments, classified, warnings). Thuần tất định, không gọi OCR/LLM."""
    del texts
    found = {t for types in types_by_file.values() for t in types}
    rows: list[dict] = []
    dialogs: list[dict] = []
    classified: list[dict] = []
    warnings: list[str] = []
    shared: list[str] = []
    used_names: set[str] = set()

    for index, file in enumerate(raw_files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        types = types_by_file.get(index) or [_OTHER]
        doc_type = primary(types)
        slot = _slot(doc_type)
        other_slots = {s for s in map(_slot, types) if s is not None} - {slot}
        # Tệp gộp hoặc chưa rõ loại giữ TÊN GỐC để cán bộ nhận ra; tệp một giấy mang tên giấy.
        base_name = _NAMES[doc_type] if doc_type in _NAMES and not other_slots else file_name
        base = {"fileIndex": index, "fileName": file_name, "type": doc_type, "docTypes": types,
                "source": "llm" if index in types_by_file else "unknown"}
        if slot == _DIALOG:
            dialogs.append({
                "fileIndex": index,
                "fileName": file_name,
                "documentName": _unique_name(base_name.replace("/", "-"), used_names, _ROW_UY_QUYEN["documentName"]),
                "loaiBan": _ROW_UY_QUYEN["loaiBan"],
                "detectedType": doc_type,
                "includedTypes": types,
                "componentName": _ROW_UY_QUYEN["componentName"],
                "quantity": 1,
                "target": "add-document-dialog",
                "needsAddComponent": True,
                # Modal không tạo được dòng → đính chung vào dòng Văn bản đề nghị.
                "fallbackComponentName": _ROWS[_UY_QUYEN_FALLBACK_ROW]["componentName"],
            })
            classified.append({**base, "target": "add-document-dialog"})
            row_label, row_name = _ROW_UY_QUYEN["componentName"], "tạo qua + Thêm giấy tờ"
        else:
            row_idx = slot or _FALLBACK_ROW
            row = _ROWS[row_idx]
            default_name = row["documentName"] if doc_type in _ROUTE else _EXTRA_NAMES.get(doc_type, "Giấy tờ kèm theo")
            rows.append({
                "fileIndex": index,
                "fileName": file_name,
                "documentName": _unique_name(base_name.replace("/", "-"), used_names, default_name),
                "loaiBan": "Bản chính",
                "detectedType": doc_type,
                "includedTypes": types,
                "componentName": row["componentName"],
                "componentIndex": row_idx,
                "target": "attp-row",
                "needsAddComponent": False,
            })
            classified.append({**base, "componentIndex": row_idx, **({} if slot else {"routedTo": row_idx})})
            if slot is None:
                shared.append(file_name)
            row_label, row_name = row_idx, row["componentName"]
        if other_slots:
            labels = sorted(other_slots, key=lambda s: (isinstance(s, str), str(s)))
            warnings.append(gop_warning(file_name, row_label, row_name, labels))

    order = {t: i for i, t in enumerate(_PRIORITY)}
    rows.sort(key=lambda a: (a["componentIndex"], order.get(a["detectedType"], 99), a["fileIndex"]))
    attachments = rows + dialogs

    # --- Cảnh báo ---
    if types_by_file:
        if _DE_NGHI not in found:
            warnings.append("Chưa có Văn bản đề nghị đăng ký nội quy lao động (dòng 4) — cần bổ sung.")
        if _NOI_QUY not in found:
            warnings.append("Chưa có toàn văn Nội quy lao động (dòng 1) — cần bổ sung.")
        if _QUYET_DINH not in found:
            warnings.append("Không thấy Quyết định ban hành Nội quy lao động — dòng 1 chỉ có toàn văn Nội quy, kiểm tra "
                            "lại.")
        if _GOP_Y not in found:
            warnings.append("Chưa có văn bản góp ý / biên bản đối thoại của tổ chức đại diện người lao động (dòng 2) — "
                            "bắt buộc với nơi có tổ chức đại diện người lao động tại cơ sở.")
    if shared:
        warnings.append("Giấy tờ không có dòng riêng (GCN đăng ký doanh nghiệp, CCCD, giấy chưa rõ loại) đã đính chung "
                        "dòng 1 Nội quy lao động: " + ", ".join(shared))
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

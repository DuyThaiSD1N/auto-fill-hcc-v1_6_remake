"""Compact agent pipeline cho "[Bắc Ninh] Đăng ký biến động do đổi tên / thay đổi thông tin người sử dụng đất".

TÁCH theo purpose (chọn TRƯỚC khi gọi LLM để mỗi lần trích gọn, không lẫn người):
- "registration_form" (mặc định): Đơn Mẫu 18 / Mẫu 24 (tối đa hai người đứng đơn) + Văn bản cam kết thành viên hộ +
  người nhận kết quả.
- "authorized_person": nhân thân MỘT người = chủ hồ sơ (bên ủy quyền) → khối doiTuongKhac*; trả kèm
  ``authorizedSubject`` "Người cao tuổi" khi chủ hồ sơ từ 60 tuổi.

OCR fallback dùng chung với 1.115465 (cùng Đơn Mẫu 18 cổng Bắc Ninh): vá Kính gửi, Địa chỉ một dòng, Nội dung biến
động, mục V khi LLM bỏ sót.
"""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_lai_giay_chung_nhan_do_bi_mat_bac_ninh.process.fallback import (
    apply_authorized_fallback,
    apply_ocr_fallback,
)
from app.pipelines.dang_ky_bien_dong_doi_ten_nguoi_su_dung_dat_bac_ninh.process import mapper
from app.pipelines.dang_ky_bien_dong_doi_ten_nguoi_su_dung_dat_bac_ninh.process.prompt import (
    EXTRA_RULES,
    RULES_UYQUYEN,
)
from app.pipelines.dang_ky_bien_dong_doi_ten_nguoi_su_dung_dat_bac_ninh.process.schema import (
    ALIASES,
    ALLOWED,
    ALLOWED_UYQUYEN,
    COMPACT_COMP_BY_NAME,
    COMPACT_COMP_UYQUYEN,
    FIELDS,
    FIELDS_UYQUYEN,
)


_MUC_V_FROM_VBCK = {"Don_ThanhVienHo": "Vbck_ThanhVien", "Don_TranhChap": "Vbck_TranhChap"}


def ocr_fallback(raw_fields, documents: list[dict]) -> dict:
    """Fallback OCR của 1.115465, nhưng mục V do regex vá thêm bị bỏ khi LLM đã đọc Văn bản cam kết thành viên hộ: Đơn
    Mẫu 24 không có mục V, regex dễ bắt nhầm câu "… thành viên hộ gia đình …:" trong chính văn bản cam kết."""
    llm =raw_fields if isinstance(raw_fields, dict) else {
        f.get("name"): f.get("value") for f in (raw_fields or []) if isinstance(f, dict)}
    fields = apply_ocr_fallback(raw_fields, documents)
    for don_name, vbck_name in _MUC_V_FROM_VBCK.items():
        if llm.get(vbck_name) and not llm.get(don_name):
            fields.pop(don_name, None)
    return fields


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    if str((options or {}).get("purpose") or "registration_form") == "authorized_person":
        res = await runner.run(
            files_by_role,
            fields=FIELDS_UYQUYEN,
            allowed=ALLOWED_UYQUYEN,
            comp_by_name=COMPACT_COMP_UYQUYEN,
            aliases=ALIASES,
            extra_rules=RULES_UYQUYEN,
            compact_field_fallback=apply_authorized_fallback,
        )
        raw = res["fields"]
        res["fields"], warnings = mapper.enrich_authorized(raw)
        subject = mapper.authorized_subject(raw)
        if subject and res["fields"]:
            res["authorizedSubject"] = subject
        if warnings:
            res.setdefault("errors", []).extend(warnings)
        return res

    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        compact_field_fallback=ocr_fallback,
    )
    res["fields"] = mapper.enrich(res["fields"])
    return res

"""Compact agent process pipeline cho "Cấp giấy phép thi công công trình trên đường bộ đang khai thác" (1.013061).

Form chỉ có Phần I người nộp. NGƯỜI ĐỀ NGHỊ (chủ đầu tư đứng đơn) thường chính là tài khoản đăng nhập; nộp thay thì
context_builder (dùng chung với 1.012906) neo NGƯỜI NỘP vào đúng thẻ CCCD của họ."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_giay_phep_thi_cong_cong_trinh_tren_duong_bo_dang_khai_thac.process import mapper
from app.pipelines.cap_giay_phep_thi_cong_cong_trinh_tren_duong_bo_dang_khai_thac.process.prompt import EXTRA_RULES
from app.pipelines.cap_giay_phep_thi_cong_cong_trinh_tren_duong_bo_dang_khai_thac.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)
from app.pipelines.cap_moi_chung_chi_hanh_nghe_moi_gioi_bat_dong_san.process.runner import _submitter_context


async def _context(documents: list[dict], options: dict) -> str:
    if str((options or {}).get("submitterMode") or "") == mapper.OWNER_AS_SUBMITTER:
        # Cài đặt "Lấy người nộp theo tờ khai": không neo tài khoản, người nộp = người đứng đơn.
        return ('\n\n<nguoi_nop_context result="theo_to_khai">\nNgười nộp lấy theo tờ khai = NGƯỜI ĐỨNG ĐƠN. Chỉ trả '
                "NguoiDeNghi_* (và ToChuc_* nếu tổ chức đứng đơn), KHÔNG trả NguoiNop_*.\n</nguoi_nop_context>")
    return await _submitter_context(documents, options)


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        context_builder=_context,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res

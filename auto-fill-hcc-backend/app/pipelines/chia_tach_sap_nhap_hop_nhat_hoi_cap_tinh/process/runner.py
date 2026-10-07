"""Compact agent process pipeline cho "Thủ tục chia, tách; sáp nhập; hợp nhất hội (cấp tỉnh)" (1.012945).

BA vai: NGƯỜI NỘP (tài khoản đăng nhập, người được BCH giao làm thủ tục), CHỦ HỒ SƠ (Chủ tịch dự kiến — người có
Phiếu LLTP số 1) và NGƯỜI LIÊN HỆ ở cuối mẫu đơn. context_builder neo NGƯỜI NỘP vào đúng thẻ CCCD của họ để LLM
không lấy nhân thân trên Phiếu LLTP của chủ hồ sơ."""

import re

from app.pipelines._shared.compact_agent import runner
from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.process import mapper
from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.process.prompt import EXTRA_RULES
from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.process.runner import (
    _norm_text,
    find_submitter_card,
)


async def _submitter_context(documents: list[dict], options: dict) -> str:
    """Neo NGƯỜI NỘP (tên + CCCD cổng tự đổ từ tài khoản) để LLM tách khỏi CHỦ HỒ SƠ trên Phiếu LLTP."""
    context = (options or {}).get("formContext") or {}
    raw_name = context.get("applicantFullname") or context.get("fullname") or ""
    name = _norm_text(raw_name)
    identity = re.sub(
        r"\D+", "", str(context.get("applicantIdentityNumber") or context.get("identityNumber") or "")
    )[:20]
    if not name and not identity:
        return ""

    anchor = f'tên "{raw_name}"' + (f', số định danh "{identity}"' if identity else "")
    matched = find_submitter_card(documents, name, identity)
    if matched:
        idx, scope = matched
        return (
            "\n\n<nguoi_nop_context result=\"co_giay_to\">\n"
            f"NGƯỜI NỘP HỒ SƠ (tài khoản đăng nhập) là: {anchor}. Tài liệu #{idx} CÓ thẻ CCCD của người này "
            "(trích đoạn bên dưới) → trích NguoiNop_* TỪ CHÍNH thẻ này. ChuHoSo_* vẫn lấy theo Chủ tịch dự kiến "
            "(Phiếu LLTP / CCCD của người đó) — KHÔNG lấy từ thẻ này, trừ khi hai người trùng nhau.\n"
            f"<cccd_nguoi_nop tai_lieu=\"{idx}\">\n{scope}\n</cccd_nguoi_nop>\n"
            "</nguoi_nop_context>"
        )
    return (
        "\n\n<nguoi_nop_context result=\"khong_co_giay_to\">\n"
        f"NGƯỜI NỘP HỒ SƠ (tài khoản đăng nhập) là: {anchor}, NHƯNG hồ sơ KHÔNG có thẻ CCCD của người này → BỎ "
        "TRỐNG toàn bộ NguoiNop_*. Các field khác trích bình thường.\n"
        "</nguoi_nop_context>"
    )


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    # Chế độ người nộp theo tờ khai: bỏ mốc tài khoản (người nộp = chủ hồ sơ, không cần neo CCCD người nộp).
    owner_mode = str((options or {}).get("submitterMode") or "") == "owner_as_submitter"
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        context_builder=None if owner_mode else _submitter_context,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res

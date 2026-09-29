"""Compact agent process pipeline cho "Đăng ký thay đổi biện pháp bảo đảm bằng QSDĐ, tài sản gắn liền với đất"
(1.011442, cổng DVC Đà Nẵng).

BỐN vai: CHỦ HỒ SƠ (người yêu cầu đăng ký thay đổi — Phiếu 02a mục 1, thường là tổ chức), NGƯỜI ĐẠI DIỆN THEO
PHÁP LUẬT (GCN đăng ký doanh nghiệp), BÊN ĐƯỢC ỦY QUYỀN và NGƯỜI NỘP (tài khoản đăng nhập). context_builder neo
NGƯỜI NỘP vào đúng thẻ CCCD của họ. Mapper ghép tài sản bảo đảm (thửa + số GCN) vào nội dung yêu cầu."""

import re

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.process.runner import (
    _norm_text,
    find_submitter_card,
)
from app.pipelines.dang_ky_thay_doi_bien_phap_bao_dam_qsdd.process import mapper
from app.pipelines.dang_ky_thay_doi_bien_phap_bao_dam_qsdd.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_thay_doi_bien_phap_bao_dam_qsdd.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


async def _submitter_context(documents: list[dict], options: dict) -> str:
    """Neo NGƯỜI NỘP (tên + CCCD cổng tự đổ từ tài khoản) để LLM tách khỏi CHỦ HỒ SƠ / người đại diện."""
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
            "(trích đoạn bên dưới) → trích NguoiNop_* TỪ CHÍNH thẻ này. ChuHoSo_* vẫn lấy theo người yêu cầu đăng "
            "ký ở Phiếu 02a / tổ chức trên GCN đăng ký doanh nghiệp, DaiDien_* theo GCN đăng ký doanh nghiệp.\n"
            f"<cccd_nguoi_nop tai_lieu=\"{idx}\">\n{scope}\n</cccd_nguoi_nop>\n"
            "</nguoi_nop_context>"
        )
    return (
        "\n\n<nguoi_nop_context result=\"khong_co_giay_to\">\n"
        f"NGƯỜI NỘP HỒ SƠ (tài khoản đăng nhập) là: {anchor}, NHƯNG hồ sơ KHÔNG có thẻ CCCD của người này → BỎ "
        "TRỐNG toàn bộ NguoiNop_*. ChuHoSo_*, DaiDien_*, UyQuyen_* trích bình thường.\n"
        "</nguoi_nop_context>"
    )


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        context_builder=_submitter_context,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res

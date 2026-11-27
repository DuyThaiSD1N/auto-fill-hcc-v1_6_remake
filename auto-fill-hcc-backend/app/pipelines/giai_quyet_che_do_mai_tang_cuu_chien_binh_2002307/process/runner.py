"""Compact-agent pipeline cho "Giải quyết chế độ mai táng phí đối với cựu chiến binh" (2.002307).

context_builder khoanh Mục 1 (cựu chiến binh đã chết) và Mục 2 (cá nhân / tổ chức nhận trợ cấp = chủ hồ sơ) của Bản khai
Mẫu số 01 rồi neo NGƯỜI NỘP theo tài khoản đăng nhập (cổng tự đổ họ tên + CCCD ở khối Người nộp): khớp Mục 2 → người nộp
là chủ hồ sơ; có thẻ CCCD khớp → trích NguoiNop_* từ thẻ đó; không thì bỏ NguoiNop_*. Cài đặt "Lấy người nộp theo tờ
khai" (options.submitterMode) bỏ neo tài khoản: người nộp = người nhận trợ cấp ở Mục 2a.
"""

import re

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.process.runner import (
    _matches_anchor,
    _norm_text,
    find_submitter_card,
)
from app.pipelines.giai_quyet_che_do_khang_chien.process.runner import _bounded_section
from app.pipelines.giai_quyet_che_do_mai_tang_cuu_chien_binh_2002307.process import mapper
from app.pipelines.giai_quyet_che_do_mai_tang_cuu_chien_binh_2002307.process.prompt import EXTRA_RULES
from app.pipelines.giai_quyet_che_do_mai_tang_cuu_chien_binh_2002307.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


def ban_khai_muc_1(text: str) -> str:
    """Mục 1 Bản khai: cựu chiến binh đã chết (tới Mục 2 người nhận trợ cấp)."""
    return _bounded_section(
        text,
        (r"^\s*1\s*[.)]\s*Họ và tên cựu chiến binh", r"Họ và tên cựu chiến binh"),
        (r"^\s*2\s*[.)]\s*Cá nhân hoặc tổ chức nhận", r"Cá nhân hoặc tổ chức nhận trợ cấp"),
    )


def ban_khai_muc_2(text: str) -> str:
    """Mục 2 Bản khai: cá nhân (2a) / tổ chức (2b) nhận trợ cấp mai táng (tới phần ký, xác nhận UBND)."""
    return _bounded_section(
        text,
        (r"^\s*2\s*[.)]\s*Cá nhân hoặc tổ chức nhận", r"Cá nhân hoặc tổ chức nhận trợ cấp mai táng"),
        (r"Xác nhận của UBND", r"Xác nhận của Ủy ban", r"^\s*[^\n]*,\s*ngày\s+\d+\s+tháng"),
    )


async def _context(documents: list[dict], options: dict) -> str:
    form = (options or {}).get("formContext") or {}
    raw_name = form.get("applicantFullname") or form.get("fullname") or ""
    name = _norm_text(raw_name)
    identity = re.sub(r"\D+", "", str(form.get("applicantIdentityNumber") or form.get("identityNumber") or ""))[:20]

    parts: list[str] = []
    recipients: list[str] = []
    for index, document in enumerate(documents, start=1):
        text = str(document.get("text") or "")
        if muc_1 := ban_khai_muc_1(text):
            parts.append(f'<cuu_chien_binh_ocr document="{index}">\nMục 1 Bản khai — CỰU CHIẾN BINH ĐÃ CHẾT, nguồn của '
                         f"CCB_* (không phải người nhận trợ cấp).\n{muc_1}\n</cuu_chien_binh_ocr>")
        if muc_2 := ban_khai_muc_2(text):
            recipients.append(muc_2)
            parts.append(f'<nguoi_nhan_tro_cap_ocr document="{index}">\nMục 2 Bản khai — CÁ NHÂN NHẬN TRỢ CẤP MAI TÁNG '
                         f"= chủ hồ sơ, nguồn chính của ChuHoSo_*.\n{muc_2}\n</nguoi_nhan_tro_cap_ocr>")

    if str((options or {}).get("submitterMode") or "") == mapper.OWNER_AS_SUBMITTER:
        # Cài đặt "Lấy người nộp theo tờ khai": không neo tài khoản, người nộp = người nhận trợ cấp ở Mục 2a.
        parts.insert(0, '<nguoi_nop_context result="owner_match">\nNgười nộp lấy theo tờ khai = người nhận trợ cấp ở Mục '
                        "2a. Chỉ trả ChuHoSo_*, không trả NguoiNop_*.\n</nguoi_nop_context>")
    elif not name and not identity:
        parts.insert(0, '<nguoi_nop_context result="khong_giay_to">\nForm không có mốc người nộp. Không trả '
                        "NguoiNop_*.\n</nguoi_nop_context>")
    elif any(_matches_anchor(scope, name, identity) for scope in recipients):
        parts.insert(0, '<nguoi_nop_context result="owner_match">\nNgười nộp chính là người nhận trợ cấp ở Mục 2a. Chỉ '
                        "trả ChuHoSo_*, không lặp NguoiNop_*.\n</nguoi_nop_context>")
    elif matched := find_submitter_card(documents, name, identity):
        index, card = matched
        parts.insert(0, f'<nguoi_nop_context result="co_giay_to">\nNgười nộp (tài khoản) là "{raw_name}". Tài liệu '
                        f"#{index} là thẻ CCCD của người này → trích NguoiNop_* từ ĐÚNG thẻ dưới đây, không lấy cho "
                        f'ChuHoSo_*.\n<cccd_nguoi_nop tai_lieu="{index}">\n{card}\n</cccd_nguoi_nop>\n'
                        "</nguoi_nop_context>")
    else:
        parts.insert(0, '<nguoi_nop_context result="khong_giay_to">\nKhông giấy tờ nào khớp người nộp. Không trả '
                        "NguoiNop_*.\n</nguoi_nop_context>")
    return "\n\n" + "\n".join(parts)


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

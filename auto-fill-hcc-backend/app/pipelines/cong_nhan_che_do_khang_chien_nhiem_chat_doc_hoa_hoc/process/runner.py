"""Compact-agent pipeline cho "Công nhận và giải quyết chế độ ưu đãi người HĐKC bị nhiễm chất độc hóa học" (1.010816).

context_builder khoanh Mục 1 Bản khai Mẫu 09 (người hoạt động kháng chiến = chủ hồ sơ) và neo NGƯỜI NỘP theo tài khoản
đăng nhập (cổng tự đổ họ tên + CCCD ở khối Người nộp): khớp Mục 1 → người nộp là chủ hồ sơ; có thẻ CCCD khớp → trích
NguoiNop_* từ thẻ đó; không thì bỏ NguoiNop_*. Cài đặt "Lấy người nộp theo tờ khai" (options.submitterMode) bỏ neo tài
khoản: người nộp = người khai Mục 1.
"""

import re

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cong_nhan_che_do_khang_chien_nhiem_chat_doc_hoa_hoc.process import mapper
from app.pipelines.cong_nhan_che_do_khang_chien_nhiem_chat_doc_hoa_hoc.process.prompt import EXTRA_RULES
from app.pipelines.cong_nhan_che_do_khang_chien_nhiem_chat_doc_hoa_hoc.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.process.runner import (
    _matches_anchor,
    _norm_text,
    find_submitter_card,
)
from app.pipelines.giai_quyet_che_do_khang_chien.process.runner import _bounded_section


def ban_khai_muc_1(text: str) -> str:
    """Mục 1 "Phần khai về người hoạt động kháng chiến bị nhiễm chất độc hóa học" (tới Mục 2 con đẻ)."""
    return _bounded_section(
        text,
        (r"^\s*1\s*[.)]\s*Phần khai về người hoạt động kháng chiến",
         r"Phần khai về người hoạt động kháng chiến bị nhiễm"),
        (r"^\s*2\s*[.)]\s*Phần khai về con", r"Phần khai về con đẻ", r"Xác nhận của UBND"),
    )


async def _context(documents: list[dict], options: dict) -> str:
    form = (options or {}).get("formContext") or {}
    raw_name = form.get("applicantFullname") or form.get("fullname") or ""
    name = _norm_text(raw_name)
    identity = re.sub(r"\D+", "", str(form.get("applicantIdentityNumber") or form.get("identityNumber") or ""))[:20]

    scopes = [(i, s) for i, d in enumerate(documents, start=1) if (s := ban_khai_muc_1(str(d.get("text") or "")))]
    parts = [
        f'<chu_ho_so_ocr document="{i}">\nMục 1 Bản khai Mẫu 09 — nguồn chính của ChuHoSo_*, HDKC_QuaTrinh, '
        f"HDKC_TinhTrangSucKhoe.\n{scope}\n</chu_ho_so_ocr>"
        for i, scope in scopes
    ]
    if str((options or {}).get("submitterMode") or "") == mapper.OWNER_AS_SUBMITTER:
        # Cài đặt "Lấy người nộp theo tờ khai": không neo tài khoản, người nộp = người khai Mục 1.
        parts.insert(0, '<nguoi_nop_context result="owner_match">\nNgười nộp lấy theo tờ khai = người hoạt động kháng '
                        "chiến ở Mục 1. Chỉ trả ChuHoSo_*, không trả NguoiNop_*.\n</nguoi_nop_context>")
    elif not name and not identity:
        parts.insert(0, '<nguoi_nop_context result="khong_giay_to">\nForm không có mốc người nộp. Không trả '
                        "NguoiNop_*.\n</nguoi_nop_context>")
    elif any(_matches_anchor(scope, name, identity) for _, scope in scopes):
        parts.insert(0, '<nguoi_nop_context result="owner_match">\nNgười nộp chính là người hoạt động kháng chiến ở '
                        "Mục 1. Chỉ trả ChuHoSo_*, không lặp NguoiNop_*.\n</nguoi_nop_context>")
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

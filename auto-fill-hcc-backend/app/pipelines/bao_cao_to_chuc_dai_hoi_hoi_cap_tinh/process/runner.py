"""Compact agent process pipeline cho "Thủ tục báo cáo tổ chức đại hội thành lập, đại hội nhiệm kỳ, đại hội bất
thường của hội (cấp tỉnh)" (1.012942).

HAI vai: NGƯỜI NỘP (tài khoản đăng nhập) và CHỦ HỒ SƠ (nhân sự dự kiến làm Chủ tịch — người có Sơ yếu lý lịch /
Phiếu LLTP số 1). context_builder neo NGƯỜI NỘP vào đúng thẻ CCCD của họ. Hồ sơ hay là 2 PDF scan ~50 trang, phần
lớn là các dự thảo báo cáo / Điều lệ / Nghị quyết đại hội không có dữ liệu cho form → document_filter bỏ các khối
trang đó trước khi gửi LLM."""

import re

from app.pipelines._shared.compact_agent import runner
from app.pipelines.bao_cao_to_chuc_dai_hoi_hoi_cap_tinh.process import mapper
from app.pipelines.bao_cao_to_chuc_dai_hoi_hoi_cap_tinh.process.prompt import EXTRA_RULES
from app.pipelines.bao_cao_to_chuc_dai_hoi_hoi_cap_tinh.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.process.runner import (
    _PAGE_SPLIT_RE,
    _norm_text,
    find_submitter_card,
)

# Tiêu đề các văn bản dài không có dữ liệu cho bước điền (so trên phần ĐẦU trang đã bỏ dấu).
_BULKY_MARKERS = (
    "bao cao tong ket",
    "bao cao chinh tri",
    "bao cao kiem diem",
    "kiem diem hoat dong",
    "bao cao tai chinh",
    "nghi quyet dai hoi",
    "dieu le hoi",
    "du thao dieu le",
    "dieu le sua doi",
)
# Tiêu đề văn bản CẦN giữ (mở đầu giấy tờ mới, kết thúc khối bỏ).
_KEEP_MARKERS = (
    "cong hoa xa hoi chu nghia",
    "so yeu ly lich",
    "ly lich tu phap",
    "danh sach",
    "de an",
    "can cuoc",
    "chung minh nhan dan",
)


_BODY_START_RE = re.compile(r"\b(?:can cu|kinh gui)\b")


def _page_state(head: str) -> str | None:
    """"drop" / "keep" nếu trang mở đầu một giấy tờ, None nếu là trang nối tiếp. Tiêu đề văn bản dài chỉ xét phần
    TRƯỚC "Căn cứ" / "Kính gửi" — công văn hay viện dẫn "Căn cứ Điều lệ Hội ..." ngay đầu trang."""
    body = _BODY_START_RE.search(head)
    title = head[:body.start()] if body else head
    if any(m in title for m in _BULKY_MARKERS):
        return "drop"
    if any(m in head for m in _KEEP_MARKERS):
        return "keep"
    return None


def trim_bulky_pages(documents: list[dict]) -> list[dict]:
    """Bỏ các khối trang dự thảo báo cáo / Điều lệ / Nghị quyết đại hội trước khi gửi LLM; trang nối tiếp theo trạng
    thái của trang mở đầu đứng trước. Không có header trang thì giữ nguyên."""
    out: list[dict] = []
    for document in documents:
        text = str(document.get("text") or "")
        headers = list(_PAGE_SPLIT_RE.finditer(text))
        if not headers:
            out.append(document)
            continue
        kept = [text[:headers[0].start()]]
        dropping = False
        for pos, header in enumerate(headers):
            end = headers[pos + 1].start() if pos + 1 < len(headers) else len(text)
            state = _page_state(_norm_text(text[header.end():end][:500]))
            if state:
                dropping = state == "drop"
            if not dropping:
                kept.append(text[header.start():end])
        trimmed = "".join(kept).strip()
        out.append({**document, "text": trimmed} if trimmed else document)
    return out


async def _submitter_context(documents: list[dict], options: dict) -> str:
    """Neo NGƯỜI NỘP (tên + CCCD cổng tự đổ từ tài khoản) để LLM tách khỏi CHỦ HỒ SƠ trên Phiếu LLTP / SYLL."""
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
            "(trích đoạn bên dưới) → trích NguoiNop_* TỪ CHÍNH thẻ này. ChuHoSo_* vẫn lấy theo nhân sự dự kiến "
            "Chủ tịch (Sơ yếu lý lịch / Phiếu LLTP) — KHÔNG lấy từ thẻ này, trừ khi hai người trùng nhau.\n"
            f"<cccd_nguoi_nop tai_lieu=\"{idx}\">\n{scope}\n</cccd_nguoi_nop>\n"
            "</nguoi_nop_context>"
        )
    return (
        "\n\n<nguoi_nop_context result=\"khong_co_giay_to\">\n"
        f"NGƯỜI NỘP HỒ SƠ (tài khoản đăng nhập) là: {anchor}, NHƯNG hồ sơ KHÔNG có thẻ CCCD của người này → BỎ "
        "TRỐNG NguoiNop_* (trừ NguoiNop_DienThoai nếu hồ sơ ghi cạnh đúng tên người này). Các field khác trích bình "
        "thường.\n"
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
        document_filter=trim_bulky_pages,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res

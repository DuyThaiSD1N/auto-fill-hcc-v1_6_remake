"""Compact agent process pipeline cho "Đăng ký đất đai lần đầu ... Nhà nước giao đất để quản lý" (1.012756).

BỐN vai: CHỦ HỒ SƠ (tổ chức đứng tên Đơn Mẫu 15), NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT (GCN đăng ký doanh nghiệp), BÊN
ĐƯỢC ỦY QUYỀN và NGƯỜI NỘP (tài khoản đăng nhập). context_builder neo NGƯỜI NỘP vào đúng thẻ CCCD của họ; hồ sơ
hay là một PDF gộp vài chục trang nên bỏ bớt khối quyết định / hợp đồng thuê đất / biên bản giao đất (nhiều trang,
chỉ ghi địa chỉ CŨ, không có dữ liệu cho bước điền) trước khi gửi LLM."""

import re

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.process.runner import (
    _PAGE_SPLIT_RE,
    _norm_text,
    find_submitter_card,
)
from app.pipelines.dang_ky_dat_dai_lan_dau_nha_nuoc_giao_quan_ly.process import mapper
from app.pipelines.dang_ky_dat_dai_lan_dau_nha_nuoc_giao_quan_ly.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_dat_dai_lan_dau_nha_nuoc_giao_quan_ly.process.schema import (
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
            "(trích đoạn bên dưới) → trích NguoiNop_* TỪ CHÍNH thẻ này. ChuHoSo_* vẫn lấy theo tổ chức đứng "
            "tên Đơn Mẫu 15, DaiDien_* theo GCN đăng ký doanh nghiệp.\n"
            f"<cccd_nguoi_nop tai_lieu=\"{idx}\">\n{scope}\n</cccd_nguoi_nop>\n"
            "</nguoi_nop_context>"
        )
    return (
        "\n\n<nguoi_nop_context result=\"khong_co_giay_to\">\n"
        f"NGƯỜI NỘP HỒ SƠ (tài khoản đăng nhập) là: {anchor}, NHƯNG hồ sơ KHÔNG có thẻ CCCD của người này → BỎ "
        "TRỐNG toàn bộ NguoiNop_*. ChuHoSo_*, DaiDien_*, UyQuyen_* trích bình thường.\n"
        "</nguoi_nop_context>"
    )


_KEEP_MARKERS = ("don dang ky", "bao cao", "to khai", "phieu do dac", "trich luc", "dang ky doanh nghiep",
                 "uy quyen", "can cuoc")


def _is_document_start(head: str) -> bool:
    """Trang mở đầu một giấy tờ mới (quốc hiệu / 'Mẫu số' ở đầu trang); trang nối tiếp thì không có."""
    return "cong hoa xa hoi chu nghia" in head or "mau so" in head or "can cuoc" in head


def _is_bulky_document(head: str) -> bool:
    """Quyết định của UBND (giao đất, cho thuê đất, chủ trương đầu tư, điều chỉnh), hợp đồng thuê đất + phụ lục,
    biên bản giao đất trên thực địa — mỗi thứ vài trang, chỉ ghi địa chỉ CŨ, không có ô nào trên form lấy từ đó."""
    if any(m in head for m in _KEEP_MARKERS):
        return False
    if "hop dong thue dat" in head:
        return True
    if "bien ban" in head and "giao dat" in head:
        return True
    return "quyet dinh" in head and ("ubnd" in head or "uy ban nhan dan" in head)


def trim_bulky_pages(documents: list[dict]) -> list[dict]:
    """Bỏ các khối trang quyết định / hợp đồng thuê đất / biên bản giao đất trước khi gửi LLM. Trang nối tiếp theo
    trạng thái của trang mở đầu giấy tờ đứng trước. Không có header trang thì giữ nguyên."""
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
            page = text[header.start():end]
            head = _norm_text(text[header.end():end][:600])
            if _is_document_start(head):
                dropping = _is_bulky_document(head)
            if not dropping:
                kept.append(page)
        trimmed = "".join(kept).strip()
        out.append({**document, "text": trimmed} if trimmed else document)
    return out


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

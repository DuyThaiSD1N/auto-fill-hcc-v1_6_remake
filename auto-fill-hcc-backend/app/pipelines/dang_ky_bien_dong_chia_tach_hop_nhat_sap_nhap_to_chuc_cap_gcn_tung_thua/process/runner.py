"""Compact agent process pipeline cho "Đăng ký biến động ... do chia, tách, hợp nhất, sáp nhập tổ chức..." (1.013977).

BA vai: CHỦ HỒ SƠ (tổ chức theo tên mới, đứng tên Đơn Mẫu 18), BÊN ĐƯỢC ỦY QUYỀN (giấy ủy quyền) và NGƯỜI NỘP
(tài khoản đăng nhập). context_builder neo NGƯỜI NỘP vào đúng thẻ CCCD của họ; dò theo TỪNG TRANG vì hồ sơ hay là
một PDF gộp nhiều chục trang."""

import re
import unicodedata

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.process import mapper
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

_PAGE_SPLIT_RE = re.compile(r"(?im)^[\t ─-╿-]*(?:trang|page)\s+\d+\s*/\s*\d+[\t ─-╿-]*$")
_ID_CARD_MARKERS = (
    "can cuoc",
    "chung minh nhan dan",
    "identity card",
    "personal identification",
    "citizen identity",
)


def _norm_text(value: str) -> str:
    text = str(value or "").replace("Đ", "D").replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^0-9a-zA-Z]+", " ", text).strip().lower()
    return re.sub(r"\s+", " ", text)


def _identity_occurs(identity: str, text: str) -> bool:
    if not identity:
        return False
    for cand in re.findall(r"(?:\d[ \t.\-]*){9,12}", str(text or "")):
        if re.sub(r"\D+", "", cand) == identity:
            return True
    return False


def _matches_anchor(text: str, name: str, identity: str) -> bool:
    name_matches = bool(name and name in _norm_text(text))
    identity_matches = _identity_occurs(identity, text)
    if name and identity:
        return name_matches and identity_matches
    return name_matches if name else identity_matches


def _looks_like_id_card(text: str) -> bool:
    folded = _norm_text(text)
    return any(marker in folded for marker in _ID_CARD_MARKERS)


def find_submitter_card(documents: list[dict], name: str, identity: str) -> tuple[int, str] | None:
    """(số thứ tự tài liệu 1-based, đoạn văn bản thẻ CCCD) của người nộp, hoặc None."""
    for index, document in enumerate(documents, start=1):
        text = str(document.get("text") or "")
        chunks = [c for c in _PAGE_SPLIT_RE.split(text) if c.strip()] or [text]
        for chunk in chunks:
            if _looks_like_id_card(chunk) and _matches_anchor(chunk, name, identity):
                return index, chunk[:4000]
    return None


async def _submitter_context(documents: list[dict], options: dict) -> str:
    """Neo NGƯỜI NỘP (tên + CCCD cổng tự đổ từ tài khoản) để LLM tách khỏi CHỦ HỒ SƠ / người ký đơn."""
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
            "tên Đơn Mẫu 18 (tên MỚI) — KHÔNG lấy từ thẻ này.\n"
            f"<cccd_nguoi_nop tai_lieu=\"{idx}\">\n{scope}\n</cccd_nguoi_nop>\n"
            "</nguoi_nop_context>"
        )
    return (
        "\n\n<nguoi_nop_context result=\"khong_co_giay_to\">\n"
        f"NGƯỜI NỘP HỒ SƠ (tài khoản đăng nhập) là: {anchor}, NHƯNG hồ sơ KHÔNG có thẻ CCCD của người này → BỎ "
        "TRỐNG toàn bộ NguoiNop_*. ChuHoSo_* và UyQuyen_* trích bình thường theo Đơn Mẫu 18 / giấy ủy quyền.\n"
        "</nguoi_nop_context>"
    )


def _is_document_start(head: str) -> bool:
    """Trang mở đầu một giấy tờ mới (quốc hiệu / 'Mẫu số' ở đầu trang); trang nối tiếp thì không có."""
    return "cong hoa xa hoi chu nghia" in head or "mau so" in head or "can cuoc" in head


def _is_bulky_document(head: str) -> bool:
    """Giấy tờ dài không có dữ liệu cho bước điền: giấy phép xây dựng / thẩm định của Sở Xây dựng (hàng chục
    trang) và quyết định / biên bản họp Hội đồng thành viên."""
    if "so xay dung" in head and ("giay phep xay dung" in head or "tham dinh" in head or "cpxd" in head
                                  or "gpxd" in head):
        return True
    return "hdtv" in head or "hoi dong thanh vien" in head


def trim_bulky_pages(documents: list[dict]) -> list[dict]:
    """Bỏ các khối trang giấy phép xây dựng / thẩm định / QĐ-biên bản HĐTV trước khi gửi LLM. Hồ sơ mẫu 59 trang
    có ~2/3 văn bản là các khối này → prompt vượt ngữ cảnh model chính. Trang nối tiếp theo trạng thái của trang
    mở đầu giấy tờ đứng trước. Không có header trang thì giữ nguyên."""
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

"""Compact agent process pipeline cho "Đăng ký nội quy lao động của doanh nghiệp" (2.001955).

BA vai: DOANH NGHIỆP (chủ hồ sơ), NGƯỜI ĐẠI DIỆN theo pháp luật (Bên A Giấy ủy quyền) và NGƯỜI NỘP (tài khoản đăng
nhập, thường là Bên B). context_builder neo NGƯỜI NỘP theo tài khoản để LLM tách khỏi người đại diện. Toàn văn Nội quy
lao động dài vài chục trang mà không có dữ liệu cho form → document_filter bỏ khối trang đó trước khi gửi LLM."""

import re
import unicodedata

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.process.runner import (
    _PAGE_SPLIT_RE,
    _norm_text,
    find_submitter_card,
)
from app.pipelines.dang_ky_noi_quy_lao_dong.process import mapper
from app.pipelines.dang_ky_noi_quy_lao_dong.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_noi_quy_lao_dong.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

# Phần tiêu đề đứng trước thân văn bản ("Căn cứ ..." / "Kính gửi ...").
_BODY_START_RE = re.compile(r"\b(?:can cu|kinh gui)\b")
# Trang mở đầu một giấy tờ cần giữ — chỉ xét ĐẦU trang: thân Nội quy hay viết "lập biên bản", "quyết định kỷ luật"
# nên không dùng các cụm đó làm mốc (mọi văn bản hành chính khác đều mở bằng quốc hiệu).
_KEEP_MARKERS = (
    "cong hoa xa hoi chu nghia",
    "can cuoc cong dan",
    "the can cuoc",
    "chung minh nhan dan",
    "giay chung nhan dang ky doanh nghiep",
)
_KEEP_HEAD_CHARS = 250


def _page_state(head: str) -> str | None:
    """"drop" nếu trang mở đầu TOÀN VĂN Nội quy lao động, "keep" nếu mở đầu giấy tờ khác, None nếu trang nối tiếp.

    Quyết định ban hành ("Về việc ban hành Nội quy lao động") và công văn ("V/v đăng ký Nội quy lao động") cũng chứa
    cụm "nội quy lao động" → chỉ coi là toàn văn khi trang ghi "Ban hành kèm theo Quyết định" hoặc mở Chương I."""
    body = _BODY_START_RE.search(head)
    title = head[:body.start()] if body else head
    if "noi quy lao dong" in title and "ve viec ban hanh" not in title and "v v " not in title and (
        "kem theo quyet dinh" in head or "chuong i " in head or "nhung quy dinh chung" in head
    ):
        return "drop"
    if any(m in head[:_KEEP_HEAD_CHARS] for m in _KEEP_MARKERS):
        return "keep"
    return None


def trim_rule_pages(documents: list[dict]) -> list[dict]:
    """Bỏ thân toàn văn Nội quy lao động (giữ trang tiêu đề) trước khi gửi LLM; trang nối tiếp theo trạng thái của trang mở đầu
    đứng trước. Không có header trang thì giữ nguyên."""
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
            state = _page_state(_norm_text(text[header.end():end][:600]))
            if state:
                dropping = state == "drop"
            # Giữ trang ĐẦU của Nội quy (tiêu đề "NỘI QUY LAO ĐỘNG") để LLM còn biết hồ sơ có Nội quy khi lập
            # DanhMucHoSo; chỉ bỏ các trang thân văn bản phía sau.
            if not dropping or state == "drop":
                kept.append(text[header.start():end])
        trimmed = "".join(kept).strip()
        out.append({**document, "text": trimmed} if trimmed else document)
    return out


async def _submitter_context(documents: list[dict], options: dict) -> str:
    """Neo NGƯỜI NỘP (tên + CCCD cổng tự đổ từ tài khoản) để LLM tách khỏi người đại diện của doanh nghiệp."""
    context = (options or {}).get("formContext") or {}
    raw_name = context.get("applicantFullname") or context.get("fullname") or ""
    name = _norm_text(raw_name)
    identity = re.sub(
        r"\D+", "", str(context.get("applicantIdentityNumber") or context.get("identityNumber") or "")
    )[:20]
    if not name and not identity:
        return ""

    anchor = f'tên "{raw_name}"' + (f', số định danh "{identity}"' if identity else "")
    lines = [
        f"NGƯỜI NỘP HỒ SƠ (tài khoản đăng nhập) là: {anchor}. Nếu người này cũng là người đại diện theo pháp luật "
        "(Bên A / người ký công văn) thì NguoiNop_* chép đúng nhân thân người đại diện.",
    ]
    matched = find_submitter_card(documents, name, identity)
    mention = None if matched else find_submitter_mention(documents, raw_name, identity)
    if matched:
        idx, scope = matched
        lines.append(f"Tài liệu #{idx} CÓ thẻ CCCD của người này (trích đoạn bên dưới) → BẮT BUỘC trích NguoiNop_* "
                     "(họ tên, số định danh, ngày cấp, nơi cấp, giới tính, nơi cư trú) từ thẻ này.")
        lines.append(f"<cccd_nguoi_nop tai_lieu=\"{idx}\">\n{scope}\n</cccd_nguoi_nop>")
    elif mention:
        idx, scope = mention
        lines.append(f"Tài liệu #{idx} CÓ đoạn ghi nhân thân người này (thường là Bên được ủy quyền — Bên B của Giấy "
                     "ủy quyền, trích bên dưới) → BẮT BUỘC trích NguoiNop_HoTen, NguoiNop_SoDinhDanh, NguoiNop_NgayCap, "
                     "NguoiNop_NoiCap (và giới tính theo danh xưng Ông/Bà) từ ĐÚNG đoạn này, không lấy của Bên A.")
        lines.append(f"<doan_nguoi_nop tai_lieu=\"{idx}\">\n{scope}\n</doan_nguoi_nop>")
    else:
        lines.append("Không giấy tờ nào ghi nhân thân người này → BỎ TRỐNG NguoiNop_*.")
    return "\n\n<nguoi_nop_context>\n" + "\n".join(lines) + "\n</nguoi_nop_context>"


def find_submitter_mention(documents: list[dict], raw_name: str, identity: str) -> tuple[int, str] | None:
    """(số thứ tự tài liệu 1-based, đoạn văn bản quanh số định danh / họ tên người nộp), hoặc None.

    Giấy ủy quyền ghi nhân thân Bên B ngay trong thân văn bản ("Họ và tên: Ông ..., CCCD số: ..., Ngày cấp ...,
    Nơi cấp ..."), không phải thẻ CCCD nên find_submitter_card không bắt được. Ưu tiên số định danh (không trùng ai),
    sau đó mới tới họ tên (so không phân biệt hoa thường)."""
    patterns = []
    if len(identity) >= 9:
        patterns.append(re.compile(r"[\s.]?".join(identity)))
    name = " ".join(unicodedata.normalize("NFC", str(raw_name or "")).split())
    if name:
        patterns.append(re.compile(r"\s+".join(map(re.escape, name.split())), re.IGNORECASE))
    for pattern in patterns:
        for index, document in enumerate(documents, start=1):
            text = unicodedata.normalize("NFC", str(document.get("text") or ""))
            m = pattern.search(text)
            if m:
                return index, text[max(0, m.start() - 150):m.end() + 400].strip()
    return None


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
        document_filter=trim_rule_pages,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res

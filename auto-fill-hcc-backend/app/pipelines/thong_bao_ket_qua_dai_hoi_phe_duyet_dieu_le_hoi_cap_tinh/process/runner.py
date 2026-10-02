"""Compact agent process pipeline cho "Thông báo kết quả đại hội và phê duyệt đổi tên hội, phê duyệt điều lệ hội
(cấp tỉnh)" (1.012943).

HAI vai: NGƯỜI NỘP (tài khoản đăng nhập) và CHỦ HỒ SƠ (người ký TM. Ban chấp hành — chỉ khi có CCCD của người đó).
context_builder neo NGƯỜI NỘP vào đúng thẻ CCCD của họ. Hồ sơ hay là một PDF scan ~30 trang, phần lớn là Báo cáo tổng
kết / báo cáo kinh phí / phụ lục thi đua không có dữ liệu cho form → document_filter chỉ giữ ĐẦU trang tiêu đề của
các văn bản đó (để vẫn liệt kê được vào danh mục hồ sơ), bỏ các trang nối tiếp. Nghị quyết đại hội GIỮ ĐỦ vì ô "Nội
dung" chép nguyên văn phần quyết nghị."""

import re

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.process.runner import (
    _PAGE_SPLIT_RE,
    _norm_text,
    find_submitter_card,
)
from app.pipelines.thong_bao_ket_qua_dai_hoi_phe_duyet_dieu_le_hoi_cap_tinh.process import mapper
from app.pipelines.thong_bao_ket_qua_dai_hoi_phe_duyet_dieu_le_hoi_cap_tinh.process.prompt import EXTRA_RULES
from app.pipelines.thong_bao_ket_qua_dai_hoi_phe_duyet_dieu_le_hoi_cap_tinh.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

# Ô "Nội dung" chép toàn văn phần quyết nghị (vài nghìn ký tự) → cần nhiều token hơn mức mặc định.
_MAX_TOKENS = 4500
# Đầu trang tiêu đề giữ lại cho văn bản bị lược (đủ tên loại + trích yếu).
_TITLE_KEEP_CHARS = 600

# Tiêu đề các văn bản dài không có dữ liệu cho bước điền (so trên phần ĐẦU trang đã bỏ dấu).
_BULKY_MARKERS = (
    "bao cao tong ket",
    "bao cao chinh tri",
    "bao cao kiem diem",
    "bao cao kinh phi",
    "bao cao tai chinh",
    "thong ke ket qua thi dua",
    "chuong trinh hoat dong",
    "dieu le hoi",
    "du thao dieu le",
    "dieu le sua doi",
)
# Tiêu đề văn bản CẦN giữ (mở đầu giấy tờ mới, kết thúc khối lược).
_KEEP_MARKERS = (
    "cong hoa xa hoi chu nghia",
    "to trinh",
    "nghi quyet",
    "bien ban",
    "danh sach",
    "so yeu ly lich",
    "ly lich tu phap",
    "can cuoc",
    "chung minh nhan dan",
)

_BODY_START_RE = re.compile(r"\b(?:can cu|kinh gui)\b")


def _page_state(head: str) -> str | None:
    """"drop" / "keep" nếu trang mở đầu một giấy tờ, None nếu là trang nối tiếp. Chỉ xét vùng tiêu đề (đầu trang,
    trước "Căn cứ" / "Kính gửi") — thân Nghị quyết hay nhắc "Báo cáo tổng kết", "danh sách" ở giữa trang."""
    body = _BODY_START_RE.search(head)
    title = head[:body.start()] if body else head
    if any(m in title[:350] for m in _BULKY_MARKERS):
        return "drop"
    if any(m in head[:250] for m in _KEEP_MARKERS):
        return "keep"
    return None


def trim_bulky_pages(documents: list[dict]) -> list[dict]:
    """Lược các khối trang Báo cáo tổng kết / kinh phí / thi đua / Điều lệ trước khi gửi LLM: giữ phần đầu trang
    tiêu đề, bỏ các trang nối tiếp (theo trạng thái của trang mở đầu đứng trước). Không có header trang thì giữ
    nguyên."""
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
            body = text[header.end():end]
            state = _page_state(_norm_text(body[:600]))
            if state == "drop":
                dropping = True
                kept.append(text[header.start():header.end()] + body[:_TITLE_KEEP_CHARS].rstrip()
                            + "\n[... lược bớt phần còn lại của văn bản ...]\n")
                continue
            if state == "keep":
                dropping = False
            if not dropping:
                kept.append(text[header.start():end])
        trimmed = "".join(kept).strip()
        out.append({**document, "text": trimmed} if trimmed else document)
    return out


_QUYET_NGHI_RE = re.compile(r"(?im)^[\t ]*quyết[\t ]+nghị[\t ]*:?[\t ]*$")
# Tiêu đề văn bản "NGHỊ QUYẾT" (viết hoa, đầu dòng) — khác câu "Căn cứ Nghị quyết số ..." trong thân bài.
_TITLE_RE = re.compile(r"(?m)^[\t ]*NGHỊ[\t ]+QUYẾT\b")
# Khối chữ ký / nơi nhận kết thúc phần quyết nghị.
_SIGNATURE_RE = re.compile(r"(?im)^[\t ]*(?:t/?m[\t .]|tm\.|thay mặt|nơi nhận|(?:phó[\t ]+)?chủ[\t ]+tịch\b)")
_SKIP_LINE_RE = re.compile(r"^\s*(?:\d{1,3}|={3,}.*={3,}|-{3,})\s*$")
_MIN_QUYET_NGHI_CHARS = 200


def extract_quyet_nghi(ocr_text: str) -> str | None:
    """Toàn văn phần quyết nghị của Nghị quyết đại hội, cắt thẳng từ OCR (LLM hay bỏ đoạn cuối "Nghị quyết này đã
    được ... thông qua"). Từ dòng "QUYẾT NGHỊ" — có tiêu đề "Nghị quyết ... Đại hội" đứng trước — tới khối chữ ký;
    bỏ header "Trang n/m", số trang đứng riêng. Không tìm thấy / quá ngắn → None (dùng giá trị LLM)."""
    text = str(ocr_text or "")
    for match in _QUYET_NGHI_RE.finditer(text):
        titles = list(_TITLE_RE.finditer(text, max(0, match.start() - 3000), match.start()))
        if not titles or "dai hoi" not in _norm_text(text[titles[-1].end():titles[-1].end() + 300]):
            continue
        rest = text[match.end():]
        end = _SIGNATURE_RE.search(rest)
        body = rest[:end.start()] if end else rest[:8000]
        lines = []
        for line in body.splitlines():
            if _PAGE_SPLIT_RE.match(line) or _SKIP_LINE_RE.match(line):
                continue
            line = " ".join(line.split())
            if line:
                lines.append(line)
        result = "\n".join(lines).strip()
        if len(result) >= _MIN_QUYET_NGHI_CHARS:
            return result
    return None


async def _submitter_context(documents: list[dict], options: dict) -> str:
    """Neo NGƯỜI NỘP (tên + CCCD cổng tự đổ từ tài khoản) để LLM không lấy nhân thân người khác cho NguoiNop_*."""
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
            "(trích đoạn bên dưới) → trích NguoiNop_* TỪ CHÍNH thẻ này. ChuHoSo_* chỉ lấy từ CCCD của người ký TM. "
            "Ban chấp hành — KHÔNG lấy từ thẻ này, trừ khi hai người trùng nhau.\n"
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
        max_tokens=_MAX_TOKENS,
    )
    quyet_nghi = extract_quyet_nghi(res.get("ocr_text") or "")
    if quyet_nghi:
        res["fields"] = [f for f in res.get("fields") or [] if f.get("name") != "NoiDung"]
        res["fields"].append({"name": "NoiDung", "value": quyet_nghi})
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res

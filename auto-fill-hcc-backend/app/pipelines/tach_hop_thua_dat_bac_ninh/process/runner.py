"""Compact agent pipeline "[Bắc Ninh] Tách thửa đất/hợp thửa đất".

Neo ĐƠN TÁCH THỬA (Mẫu 22) + BẢN VẼ (Mẫu 22a) theo TIÊU ĐỀ IN HOA trong OCR: người dùng hay tải lẫn hồ
sơ của thủ tục khác (vd đơn xin cấp giấy phép xây dựng + hồ sơ thiết kế có thửa, chủ, địa chỉ riêng).
document_filter bỏ tài liệu lạc thủ tục trước khi gửi LLM; context_builder chỉ rõ tài liệu nào là đơn/
bản vẽ. Không neo thì LLM vơ dữ liệu của tài liệu đứng trước.
"""

import re

from app.pipelines._shared.compact_agent import runner
from app.pipelines.tach_hop_thua_dat_bac_ninh.process import mapper
from app.pipelines.tach_hop_thua_dat_bac_ninh.process.fallback import apply_ocr_fallback
from app.pipelines.tach_hop_thua_dat_bac_ninh.process.prompt import EXTRA_RULES
from app.pipelines.tach_hop_thua_dat_bac_ninh.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

# Chỉ khớp tiêu đề IN HOA (không IGNORECASE): bản vẽ có dòng thường "(Kèm theo Đơn đề nghị tách thửa
# đất…)" không được tính là đơn. OCR hay chèn ** (markdown đậm) giữa hai dòng tiêu đề và đọc "THỬA"
# thành "THỪA".
_DON_RE = re.compile(r"ĐƠN\s*ĐỀ\s*NGHỊ[\s*_]*TÁCH\s*TH[ỬỪ]A")
_BAN_VE_RE = re.compile(r"BẢN\s*VẼ[\s*_]*TÁCH\s*TH[ỬỪ]A")
_THUA_RE = re.compile(
    r"Tách\s*thửa\s*đất\s*số\s*:?\s*([\w\-/]+)[\s,;]*tờ\s*bản\s*đồ\s*số\s*:?\s*([\w\-/]+)", re.IGNORECASE
)


_ID_RE = re.compile(r"(?<!\d)\d{12}(?!\d)")


def _parcel_re(so: str, to: str) -> re.Pattern:
    return re.compile(
        rf"th[ửừ]a\s*(?:đất\s*)?số\s*:?\s*{re.escape(so)}(?![\w-])[\s\S]{{0,40}}?"
        rf"tờ\s*bản\s*đồ\s*(?:số\s*)?:?\s*{re.escape(to)}(?![\w-])",
        re.IGNORECASE,
    )


def _keep_tach_thua_documents(documents: list[dict]) -> list[dict]:
    """Bỏ tài liệu của thủ tục khác khi đã thấy ĐƠN TÁCH THỬA.

    Giữ: đơn, bản vẽ, và tài liệu nhắc CÙNG thửa (số thửa + tờ bản đồ, vd GCN) hoặc CÙNG số định danh
    của người đứng đơn (CCCD, giấy ủy quyền). Hồ sơ lẫn nhiều bộ còn làm tràn ngữ cảnh model chính
    (~32k token) → rơi sang model dự phòng, trích lệch sang bộ đứng trước. Không thấy đơn → giữ đủ.
    """
    dons = [str(d.get("text") or "") for d in documents if _DON_RE.search(str(d.get("text") or ""))]
    if not dons:
        return documents
    ids = {i for text in dons for i in _ID_RE.findall(text)}
    parcel = None
    for text in dons:
        m = _THUA_RE.search(text)
        if m:
            parcel = _parcel_re(m.group(1), m.group(2))
            break
    kept = []
    for d in documents:
        text = str(d.get("text") or "")
        if (
            _DON_RE.search(text)
            or _BAN_VE_RE.search(text)
            or (parcel and parcel.search(text))
            or any(i in text for i in ids)
        ):
            kept.append(d)
    return kept


def _doc_refs(documents: list[dict], pattern: re.Pattern) -> list[str]:
    return [
        f'#{i} ("{d.get("name") or ""}")'
        for i, d in enumerate(documents, 1)
        if pattern.search(str(d.get("text") or ""))
    ]


async def _focus_context(documents: list[dict], options: dict) -> str:
    """Chỉ ra tài liệu nào là đơn/bản vẽ tách thửa để LLM bỏ qua tài liệu của thủ tục khác."""
    don = _doc_refs(documents, _DON_RE)
    if not don:
        return ""
    ban_ve = _doc_refs(documents, _BAN_VE_RE)
    thua = ""
    for d in documents:
        text = str(d.get("text") or "")
        if _DON_RE.search(text):
            m = _THUA_RE.search(text)
            if m:
                thua = f" (thửa đất số {m.group(1)}, tờ bản đồ số {m.group(2)})"
                break
    lines = [
        "\n\n<tai_lieu_tach_thua>",
        "Hồ sơ có thể LẪN tài liệu của thủ tục khác (đơn xin cấp giấy phép xây dựng, hồ sơ thiết kế, "
        "cam kết an toàn công trình…) với chủ, thửa, địa chỉ RIÊNG. Chỉ trích từ bộ tách thửa sau:",
        f"- ĐƠN ĐỀ NGHỊ TÁCH THỬA: tài liệu {', '.join(don)}.",
    ]
    if ban_ve:
        lines.append(f"- BẢN VẼ TÁCH THỬA: tài liệu {', '.join(ban_ve)}.")
    lines += [
        "- Chủ đất, địa chỉ, điện thoại, Kính gửi, thửa gốc, các thửa mới, lý do, giấy tờ kèm, đề nghị cấp "
        "GCN: lấy từ ĐƠN TÁCH THỬA (đối chiếu bản vẽ).",
        f"- GCN: chỉ dùng Giấy chứng nhận của CÙNG thửa ghi trong đơn tách thửa{thua}.",
        "- TUYỆT ĐỐI không lấy dữ liệu từ tài liệu ngoài bộ này, kể cả khi nó đứng trước.",
        "</tai_lieu_tach_thua>",
    ]
    return "\n".join(lines)


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        compact_field_fallback=apply_ocr_fallback,
        options=options,
        context_builder=_focus_context,
        document_filter=_keep_tach_thua_documents,
    )
    res["fields"] = mapper.enrich(res["fields"])
    return res

"""Đính kèm "Thành phần hồ sơ" cho "Giao đất, cho thuê đất, chuyển mục đích SDĐ; giao/cho thuê rừng; gia
hạn SDĐ" (cổng DVC Đà Nẵng — engine `attp-row`).

Bảng thành phần hồ sơ (crawl 29/10/2026, UBND Phường Hải Châu) có 12 dòng theo NHIỀU NHÁNH, mỗi dòng đều có radio
Bản chính/Bản sao:
   1 Đơn theo Mẫu số 01                                         → Bản chính
   2 Phương án sử dụng tầng đất mặt Mẫu số 26 (đất chuyên trồng lúa) → Bản chính
   3 Dự án đầu tư đối với khu rừng + hiện trạng rừng (giao rừng)  → Bản chính
   4 Kết quả đấu giá thuê rừng (cho thuê rừng)                    → Bản sao
   5 Một trong các loại giấy tờ: VB phê duyệt dự án/chủ trương đầu tư, chấp thuận nhà đầu tư (khoản 5 Điều 124),
     đấu giá QSDĐ không thành, nhận chuyển nhượng dự án BĐS, điểm i khoản 1 Điều 133 (giao đất/cho thuê đất)
   6 VB phê duyệt kết quả lựa chọn nhà đầu tư (khoản 2 Điều 116)
   7 VB phê duyệt dự án/chủ trương đầu tư (chuyển mục đích)
   8 Giấy chứng nhận (khoản 21 Điều 3...) / quyết định giao, cho thuê, chuyển mục đích
   9 PA SDĐ tổ chức kinh tế, đơn vị sự nghiệp công lập · 10 PA SDĐ công ty nông, lâm nghiệp tại địa phương
  11 PA SDĐ diện tích đất thu hồi của công ty nông, lâm nghiệp
  12 Một trong các giấy tờ: GCN / quyết định giao-thuê-chuyển MĐ / VB cho phép gia hạn dự án (gia hạn SDĐ)
Dòng 5 và 7 cùng nói "văn bản phê duyệt dự án đầu tư", dòng 8 và 12 cùng nhận GCN → chọn theo NHÁNH đọc từ tiêu đề
Đơn (chuyển mục đích → 7; gia hạn → 12; còn lại → 5 và 8).

FE khớp dòng bằng componentIndex + componentName (tên NGUYÊN VĂN dò trong attachmentContext theo từ khoá; extension
không gửi thì dùng bảng 12 dòng dưới đây), tick + chọn loaiBan + set file. Phân loại **LLM-primary**: LLM đã trả
loại (kể cả other) thì giữ, rule keyword chỉ dùng cho tệp LLM không trả (lỗi 502...). Tệp không có dòng riêng
(CCCD, ủy quyền, tờ khai thuế, công văn, phiếu đo đạc...) → đính CHUNG vào dòng Đơn, giữ tên thật của tệp, kèm cảnh
báo để cán bộ kiểm tra — không bỏ tệp nào.
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.naming import normalize_document_name
from app.pipelines.giao_thue_chuyen_muc_dich_dat_da_nang.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON_M01 = "don_m01"
_GCN = "gcn"
_PHUONG_AN_DAT_MAT = "phuong_an_dat_mat"
_DU_AN_GIAO_RUNG = "du_an_giao_rung"
_DAU_GIA_THUE_RUNG = "dau_gia_thue_rung"
_VAN_BAN_GIAO_THUE = "van_ban_giao_thue"
_CHU_TRUONG_DAU_TU = "chu_truong_dau_tu"
_LUA_CHON_NHA_DAU_TU = "lua_chon_nha_dau_tu"
_PHUONG_AN_SDD = "phuong_an_sdd"
_GIA_HAN_DU_AN = "van_ban_gia_han_du_an"
_CCCD = "cccd"
_OTHER = "other"

# Nhánh hồ sơ đọc từ tiêu đề Đơn.
_NHANH_GIAO_THUE = "giao_thue"
_NHANH_CHUYEN_MD = "chuyen_muc_dich"
_NHANH_GIA_HAN = "gia_han"

# Bảng 12 dòng NGUYÊN VĂN (crawl 29/10/2026) — chỉ dùng khi extension không gửi attachmentContext.
_DEFAULT_ROWS = [
    "Đơn theo Mẫu số 01",
    "Phương án sử dụng tầng đất mặt theo Mẫu số 26 ban hành kèm theo Nghị định số 151/2025/NĐ-CP (đối với trường "
    "hợp chuyển mục đích sử dụng đất chuyên trồng lúa).",
    "Dự án đầu tư đối với khu rừng đề nghị giao; báo cáo điều tra, đánh giá hiện trạng rừng và bản đồ hiện trạng "
    "rừng theo quy định của pháp luật về lâm nghiệp (đối với trường hợp đề nghị giao đất và giao rừng);",
    "Kết quả đấu giá thuê rừng; biên bản đấu giá cho thuê rừng; danh sách người trúng đấu giá thuê rừng; thông báo "
    "hoàn thành nghĩa vụ tài chính đối với người trúng đấu giá thuê rừng (đối với trường hợp cho thuê đất và cho "
    "thuê rừng).",
    "Một trong các loại giấy tờ sau: + Bản sao văn bản phê duyệt dự án đầu tư, quyết định chấp thuận chủ trương đầu "
    "tư, quyết định chấp thuận chủ trương đầu tư đồng thời chấp thuận nhà đầu tư theo quy định của pháp luật về đầu "
    "tư công, pháp luật về đầu tư; văn bản phê duyệt kết quả lựa chọn nhà đầu tư đối với dự án đầu tư theo phương "
    "thức đối tác công tư (nếu có); + Bản sao văn bản của cơ quan nhà nước có thẩm quyền chấp thuận nhà đầu tư theo "
    "quy định của pháp luật về đầu tư đối với trường hợp quy định tại khoản 5 Điều 124 Luật Đất đai; + Bản sao văn "
    "bản của đơn vị được giao tổ chức thực hiện việc đấu giá quyền sử dụng đất về kết quả đấu giá quyền sử dụng đất "
    "không thành quy định tại điểm b khoản 6 Điều 125 Luật Đất đai; + Bản sao văn bản về kết quả thực hiện việc nhận "
    "chuyển nhượng dự án bất động sản theo quy định của pháp luật về kinh doanh bất động sản đối với trường hợp quy "
    "định tại khoản 7 Điều 124 Luật Đất đai; + Bản sao các văn bản theo quy định của pháp luật đối với trường hợp "
    "quy định tại điểm i khoản 1 Điều 133 Luật Đất đai mà phải thu hồi đất.",
    "Bản sao văn bản phê duyệt kết quả lựa chọn nhà đầu tư của cơ quan nhà nước có thẩm quyền đối với trường hợp quy "
    "định tại khoản 2 Điều 116 Luật Đất đai.",
    "Bản sao văn bản phê duyệt dự án đầu tư, quyết định chấp thuận chủ trương đầu tư, quyết định chấp thuận chủ "
    "trương đầu tư đồng thời chấp thuận nhà đầu tư theo quy định của pháp luật về đầu tư công, pháp luật về đầu tư; "
    "văn bản phê duyệt kết quả lựa chọn nhà đầu tư đối với dự án đầu tư theo phương thức đối tác công tư (nếu có).",
    "Một trong các giấy chứng nhận quy định tại khoản 21 Điều 3, khoản 3 Điều 256 Luật Đất đai hoặc một trong các "
    "loại giấy tờ quy định tại Điều 137 Luật Đất đai hoặc quyết định giao đất, quyết định cho thuê đất, quyết định "
    "cho phép chuyển mục đích sử dụng đất của cơ quan nhà nước có thẩm quyền theo quy định của pháp luật về đất đai "
    "qua các thời kỳ.",
    "Bản sao Phương án sử dụng đất đã được cơ quan, tổ chức có thẩm quyền phê duyệt đối với tổ chức kinh tế, đơn vị "
    "sự nghiệp công lập đã được Nhà nước giao đất, cho thuê đất trước ngày Luật Đất đai có hiệu lực thi hành;",
    "Bản sao Phương án sử dụng đất của công ty nông, lâm nghiệp tại địa phương đã được cơ quan, tổ chức có thẩm "
    "quyền phê duyệt",
    "Bản sao Phương án sử dụng đất đã được cơ quan, tổ chức có thẩm quyền phê duyệt đối với diện tích đất thu hồi của "
    "công ty nông, lâm nghiệp quản lý, sử dụng để giao đất, cho thuê đất quy định tại các điểm c, d và đ khoản 2 "
    "Điều 181 Luật Đất đai;",
    "Một trong các giấy tờ sau: + Bản sao một trong các giấy chứng nhận: Giấy chứng nhận quyền sử dụng đất, quyền "
    "sở hữu tài sản gắn liền với đất, Giấy chứng nhận quyền sử dụng đất, Giấy chứng nhận quyền sở hữu nhà ở và quyền "
    "sử dụng đất ở, Giấy chứng nhận quyền sở hữu nhà ở, Giấy chứng nhận quyền sở hữu công trình xây dựng, Giấy chứng "
    "nhận quyền sử dụng đất, quyền sở hữu nhà ở và tài sản khác gắn liền với đất đã được cấp theo quy định của pháp "
    "luật về đất đai, pháp luật về nhà ở, pháp luật về xây dựng trước ngày Luật này có hiệu lực thi hành vẫn có giá "
    "trị pháp lý và không phải cấp đổi sang Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất. "
    "+ Quyết định giao đất, quyết định cho thuê đất, quyết định cho phép chuyển mục đích sử dụng đất của cơ quan nhà "
    "nước có thẩm quyền theo quy định của pháp luật về đất đai qua các thời kỳ. + Văn bản của cơ quan có thẩm quyền cho phép gia hạn thời hạn hoạt động của dự án đầu tư hoặc thể hiện "
    "thời hạn hoạt động của dự án đầu tư theo quy định của pháp luật về đầu tư đối với trường hợp sử dụng đất để "
    "thực hiện dự án đầu tư.",
]

# Khoá dòng → (từ khoá fold, loại bản). Mỗi từ khoá khớp ĐÚNG MỘT dòng, trừ "phe duyet du an dau tu" (dòng 5 và
# 7): _find lấy dòng NGẮN nhất → dòng 7; dòng 5 dò bằng "khoan 5 dieu 124".
_ROW_SPECS: dict[str, tuple[str, str]] = {
    "don": ("mau so 01", "Bản chính"),
    "dat_mat": ("tang dat mat", "Bản chính"),
    "giao_rung": ("du an dau tu doi voi khu rung", "Bản chính"),
    "dau_gia_rung": ("ket qua dau gia thue rung", "Bản sao"),
    "giao_thue": ("khoan 5 dieu 124", "Bản sao"),
    "lua_chon_ndt": ("khoan 2 dieu 116", "Bản sao"),
    "chuyen_md": ("phe duyet du an dau tu", "Bản sao"),
    "gcn": ("khoan 21 dieu 3", "Bản sao"),
    "pa_to_chuc": ("to chuc kinh te, don vi su nghiep cong lap", "Bản sao"),
    "pa_nong_lam": ("cong ty nong, lam nghiep tai dia phuong", "Bản sao"),
    "pa_thu_hoi": ("dien tich dat thu hoi", "Bản sao"),
    "gia_han": ("gia han thoi han hoat dong cua du an dau tu", "Bản sao"),
}

# Tên tài liệu (thành tên tệp khi FE dựng file) theo docType.
_DOC_NAMES: dict[str, str] = {
    _DON_M01: "Đơn đề nghị theo Mẫu số 01",
    _GCN: "Giấy chứng nhận quyền sử dụng đất hoặc quyết định giao đất, cho thuê đất, chuyển mục đích",
    _PHUONG_AN_DAT_MAT: "Phương án sử dụng tầng đất mặt theo Mẫu số 26",
    _DU_AN_GIAO_RUNG: "Dự án đầu tư, báo cáo và bản đồ hiện trạng rừng",
    _DAU_GIA_THUE_RUNG: "Kết quả đấu giá cho thuê rừng",
    _VAN_BAN_GIAO_THUE: "Văn bản chấp thuận nhà đầu tư hoặc kết quả đấu giá, nhận chuyển nhượng dự án",
    _CHU_TRUONG_DAU_TU: "Văn bản phê duyệt dự án hoặc chấp thuận chủ trương đầu tư",
    _LUA_CHON_NHA_DAU_TU: "Văn bản phê duyệt kết quả lựa chọn nhà đầu tư",
    _PHUONG_AN_SDD: "Phương án sử dụng đất đã được phê duyệt",
    _GIA_HAN_DU_AN: "Văn bản cho phép gia hạn thời hạn hoạt động của dự án đầu tư",
}

# CCCD không có dòng riêng → đính chung vào dòng Đơn như giấy tờ khác.
_CCCD_NAME = "Căn cước công dân"
_ALLOWED_DOC_TYPES = set(_DOC_NAMES) | {_CCCD, _OTHER}

Row = tuple[int, str, str]  # (index 1-based, tên nguyên văn, tên fold)


def _is_identity_text(text: str) -> bool:
    h = _fold(text)
    return any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu", "passport"))


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM). Dấu hiệu đặc trưng trước, GCN sau."""
    h = _fold(text)
    if not h:
        return ""
    if "mau so 01" in h and ("don" in h or "de nghi" in h):
        return _DON_M01
    if "phuong an su dung tang dat mat" in h or "mau so 26" in h:
        return _PHUONG_AN_DAT_MAT
    # "khu rung" chứ không "rung" trần: "chu truong" cũng chứa "rung".
    if "hien trang rung" in h or ("du an dau tu" in h and "khu rung" in h):
        return _DU_AN_GIAO_RUNG
    if "dau gia" in h and "thue rung" in h:
        return _DAU_GIA_THUE_RUNG
    if "gia han thoi han hoat dong" in h:
        return _GIA_HAN_DU_AN
    if "ket qua lua chon nha dau tu" in h:
        return _LUA_CHON_NHA_DAU_TU
    if "chap thuan chu truong dau tu" in h or "phe duyet du an dau tu" in h:
        return _CHU_TRUONG_DAU_TU
    if "dau gia quyen su dung dat khong thanh" in h or "chuyen nhuong du an bat dong san" in h:
        return _VAN_BAN_GIAO_THUE
    if "phuong an su dung dat" in h:
        return _PHUONG_AN_SDD
    if "giay chung nhan quyen su dung dat" in h or ("giay chung nhan" in h and "quyen su dung dat" in h):
        return _GCN
    if "quyet dinh giao dat" in h or "quyet dinh cho thue dat" in h or "quyet dinh cho phep chuyen muc dich" in h:
        return _GCN
    if _is_identity_text(h):
        return _CCCD
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if text in _ALLOWED_DOC_TYPES:
        return text
    if "gia han" in text:
        return _GIA_HAN_DU_AN
    if "lua chon" in text:
        return _LUA_CHON_NHA_DAU_TU
    if "chu truong" in text:
        return _CHU_TRUONG_DAU_TU
    if "01" in text or ("don" in text and "de nghi" in text):
        return _DON_M01
    if "dat mat" in text or "26" in text:
        return _PHUONG_AN_DAT_MAT
    if "giao rung" in text or ("du an" in text and "rung" in text):
        return _DU_AN_GIAO_RUNG
    if "dau gia" in text and "rung" in text:
        return _DAU_GIA_THUE_RUNG
    if "phuong an" in text:
        return _PHUONG_AN_SDD
    if "gcn" in text or "chung nhan" in text or "so do" in text or "quyet dinh" in text:
        return _GCN
    if "cccd" in text or "can cuoc" in text or "cmnd" in text or "ho chieu" in text:
        return _CCCD
    return _OTHER


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=500, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    out: dict[int, str] = {}
    for item in parsed.get("documents", []) or []:
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        out[idx] = _normalize_doc_type(str(item.get("docType") or item.get("type") or ""))
    return out


def _portal_rows(components: list[dict] | None) -> list[Row]:
    rows: list[Row] = []
    for component in components or []:
        if not isinstance(component, dict):
            continue
        try:
            index = int(component.get("index"))
        except (TypeError, ValueError):
            continue
        name = str(component.get("componentName") or "").strip()
        if index > 0 and name:
            rows.append((index, name, _fold(name)))
    return rows


def _default_rows() -> list[Row]:
    return [(i + 1, name, _fold(name)) for i, name in enumerate(_DEFAULT_ROWS)]


def _find(key: str, rows: list[Row]) -> Row | None:
    hits = [row for row in rows if key in row[2]]
    return min(hits, key=lambda row: (len(row[2]), row[0])) if hits else None


def _nhanh(files: list[dict], texts: dict[int, str], types: dict[int, str]) -> str:
    """Nhánh hồ sơ theo TIÊU ĐỀ Đơn (phần trước "Kính gửi"). Thân Mẫu 01 liệt kê cả giao/thuê/chuyển MĐ nên chỉ
    đọc tiêu đề."""
    for idx in range(len(files)):
        if types.get(idx) != _DON_M01:
            continue
        h = _fold(texts.get(idx, ""))
        head = h.split("kinh gui", 1)[0] if "kinh gui" in h else h[:400]
        if "gia han" in head:
            return _NHANH_GIA_HAN
        if "chuyen muc dich" in head and "giao dat" not in head and "cho thue" not in head:
            return _NHANH_CHUYEN_MD
    return _NHANH_GIAO_THUE


def _row_key(doc_type: str, text: str, nhanh: str) -> str:
    if doc_type == _DON_M01:
        return "don"
    if doc_type == _PHUONG_AN_DAT_MAT:
        return "dat_mat"
    if doc_type == _DU_AN_GIAO_RUNG:
        return "giao_rung"
    if doc_type == _DAU_GIA_THUE_RUNG:
        return "dau_gia_rung"
    if doc_type == _VAN_BAN_GIAO_THUE:
        return "giao_thue"
    if doc_type == _CHU_TRUONG_DAU_TU:
        return "chuyen_md" if nhanh == _NHANH_CHUYEN_MD else "giao_thue"
    if doc_type == _LUA_CHON_NHA_DAU_TU:
        return "lua_chon_ndt"
    if doc_type == _GCN:
        return "gia_han" if nhanh == _NHANH_GIA_HAN else "gcn"
    if doc_type == _GIA_HAN_DU_AN:
        return "gia_han"
    # Phương án SDĐ: 3 dòng theo đối tượng.
    h = _fold(text)
    if "thu hoi" in h and "nong, lam nghiep" in h:
        return "pa_thu_hoi"
    if "cong ty nong" in h or "nong, lam nghiep" in h or "nong lam nghiep" in h:
        return "pa_nong_lam"
    return "pa_to_chuc"


def _other_display(file_name: str) -> str:
    """Tệp không có dòng riêng giữ TÊN THẬT (bỏ đuôi, "_" → cách) để cán bộ biết là giấy gì."""
    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", str(file_name or "")).strip()
    stem = re.sub(r"\s+", " ", stem.replace("_", " ")).strip()
    return normalize_document_name(stem, "Tài liệu khác") if stem else "Tài liệu khác"


def _dedupe_document_names(attachments: list[dict]) -> None:
    """documentName thành TÊN TỆP khi FE dựng file → nhiều tệp cùng tên trong một ô thì đánh số để phân biệt."""
    counts: dict[tuple, int] = {}
    for item in attachments:
        key = (item["componentIndex"], item["documentName"])
        counts[key] = counts.get(key, 0) + 1
    used: dict[tuple, int] = {}
    for item in attachments:
        key = (item["componentIndex"], item["documentName"])
        if counts[key] < 2:
            continue
        used[key] = used.get(key, 0) + 1
        item["documentName"] = f"{item['documentName']} ({used[key]})"


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, str] | None = None,
    components: list[dict] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    rows = _portal_rows(components) or _default_rows()
    by_name = {item.get("name"): item for item in ocr_results}
    texts = {idx: str(by_name.get(str(f.get("name") or ""), {}).get("text") or "") for idx, f in enumerate(files)}

    types: dict[int, tuple[str, str]] = {}
    for idx in range(len(files)):
        # LLM-PRIMARY: LLM đã trả loại (kể cả other) thì giữ; rule chỉ cho tệp LLM không trả.
        if idx in llm_types:
            types[idx] = (llm_types[idx], "llm")
        elif rule_type := _rule_doc_type(texts[idx]):
            types[idx] = (rule_type, "rule")
        else:
            types[idx] = (_OTHER, "unknown")
    nhanh = _nhanh(files, texts, {idx: t for idx, (t, _) in types.items()})

    don_key, don_loai_ban = _ROW_SPECS["don"]
    don = _find(don_key, rows) or rows[0]

    items: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    bundled: list[str] = []
    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        doc_type, source = types[idx]

        row = None
        if doc_type in _DOC_NAMES:
            key, loai_ban = _ROW_SPECS[_row_key(doc_type, texts[idx], nhanh)]
            row = _find(key, rows)
            document_name = _DOC_NAMES[doc_type]
        if row is None:
            # Không có dòng riêng (CCCD, ủy quyền, tờ khai thuế, công văn...) hoặc trang thiếu dòng → đính chung vào
            # dòng Đơn để không sót tệp; giữ tên thật của tệp để cán bộ biết là giấy gì.
            row, loai_ban = don, don_loai_ban
            document_name = _CCCD_NAME if doc_type == _CCCD else _other_display(file_name)
            bundled.append(file_name)
        items.append({
            "fileIndex": idx,
            "fileName": file_name,
            "documentName": document_name,
            "componentName": row[1],
            "componentIndex": row[0],
            "loaiBan": loai_ban,
            "target": "attp-row",
            "needsAddComponent": False,
            "detectedType": doc_type,
        })
        classified.append({"fileName": file_name, "docType": doc_type, "source": source, "componentIndex": row[0]})

    if bundled:
        warnings.append(
            f"Bảng thành phần hồ sơ không có dòng riêng cho các tệp sau, đã đính chung vào dòng \"{don[1][:60]}\" — "
            f"cán bộ kiểm tra lại: {', '.join(bundled)}."
        )
    _dedupe_document_names(items)
    return items, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    components = ((options or {}).get("attachmentContext") or {}).get("components")
    _ = session
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]

    from app.services import ocr

    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    ocr_by_name = {item.get("name"): item for item in ocr_results}
    llm_docs: list[dict[str, Any]] = []
    for idx, file in enumerate(raw_files):
        text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        if text.strip():
            llm_docs.append({"index": idx, "text": text})

    t1 = time.monotonic()
    llm_types: dict[int, str] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types, components)
    errors.extend(warnings)
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [raw_files[doc["index"]]["name"] for doc in llm_docs],
            "classified": classified,
            "skippedOcr": skipped_ocr,
            "portalRows": len(_portal_rows(components)),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }

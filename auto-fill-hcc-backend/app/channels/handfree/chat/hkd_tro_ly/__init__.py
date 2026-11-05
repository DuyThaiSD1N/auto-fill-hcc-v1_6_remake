"""Trợ lý hộ kinh doanh: thành lập hộ kinh doanh bằng hỏi đáp, đi lần lượt TỪNG KHỐI trên cổng HkdOnline.

Mỗi khối: mở khối (extension bấm menu) → điền sẵn ô đã biết → trỏ từng ô còn thiếu, hỏi, điền ngay ô đó → đọc lại
và chờ công dân xác nhận "Lưu khối này" (khối không phải hỏi gì thì tự lưu) → extension chạy máy điền HkdOnline cho
đúng MỘT trang (pageOrder 1 trang: thêm mã ngành, chọn địa chỉ tỉnh → xã, sao chép tài khoản, tạo thành viên… như
luồng có tờ khai) và báo business_report → sang khối kế. Cổng reload toàn trang sau mỗi postback nên BE giữ trạng thái
(khối nào, ô nào); extension chỉ làm từng thao tác nhỏ và báo trang đang đứng qua page_status (businessPageKey).

Hai mức, cùng một vòng:
- Không có giấy tờ (nút trên thẻ đồng ý): hỏi mọi ô, kể cả ô không bắt buộc (bỏ qua được).
- Có giấy tờ: pipeline đọc như cũ; mỗi khối điền sẵn từ giấy, chỉ hỏi ô bắt buộc còn thiếu; ngành chỉ có tên → agent
  tra mã. Tệp đính kèm chạy cùng lần lưu khối cuối.

Chỉ bật khi extension khai supportsHkdTroLy và không ở chế độ tiếng Mông (câu thoại mới chưa có bản dịch). Bản extension
cũ trên chợ không khai cờ → luồng tải tờ khai như trước.
"""
import json
import logging
import re
import time

from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.hkd_tro_ly import hoi_dap, nganh_nghe
from app.channels.handfree.chat.intents import Intent
from app.pipelines.dang_ky_kinh_doanh.process import mapper

logger = logging.getLogger(__name__)

CAPABILITY = "supportsHkdTroLy"
MEMBERS_PAGE = "thong-tin-ve-thanh-vien"
AUTH_PAGE = "thong-tin-uy-quyen"
_OWNER_PAGE = "chu-ho-kinh-doanh"
_NGANH_PAGE = "nganh-nghe-kinh-doanh"
_CONFIRM = "__xac_nhan__"
_ACTIONS = {"hkd_no_docs", "hkd_answer", "hkd_value", "hkd_pick", "hkd_skip", "hkd_save", "hkd_resume"}
_OPEN_RETRY_SECONDS = 8
_OPEN_MAX_TRIES = 3

# Thứ tự khối = menu "Khối dữ liệu" của cổng. Khối thành viên chỉ có khi chủ thể là các thành viên hộ gia đình; khối
# ủy quyền chỉ có khi người nộp là người được ủy quyền (extension báo "missing" thì bỏ qua).
_BLOCKS = [
    ("hinh-thuc-dang-ky", []),
    ("dia-chi", ["dia_chi_kd", "dien_thoai", "email", "fax", "website", "khong_kd_tru_so"]),
    (_NGANH_PAGE, []),
    ("ten-ho-kinh-doanh", ["ten_ho", "ten_nuoc_ngoai", "ten_viet_tat"]),
    (_OWNER_PAGE, ["chu_ho_la_ban", "chu_ho_ho_ten", "chu_ho_gioi_tinh", "chu_ho_ngay_sinh", "chu_ho_so_dinh_danh",
                   "chu_the", "noi_o"]),
    (MEMBERS_PAGE, []),
    ("thong-tin-ve-von", ["von"]),
    ("thong-tin-ve-thue", ["dia_chi_thue", "dia_chi_thue_khac", "ngay_bat_dau", "so_lao_dong"]),
    ("nguoi-nop-ho-so", []),
    (AUTH_PAGE, []),
]

# Mục hỏi: loại giá trị (hoi_dap.check), "skip" = ô không bắt buộc (bỏ qua được), "optional" = chỉ hỏi khi không có
# giấy tờ (có tờ khai mà ô trống nghĩa là không kê khai), "same" = nhận "giống …".
_SLOTS = {
    "dia_chi_kd": {"kind": "address"},
    "dien_thoai": {"kind": "phone"},
    "email": {"kind": "email", "skip": True},
    "fax": {"kind": "text", "skip": True, "optional": True},
    "website": {"kind": "text", "skip": True, "optional": True},
    "khong_kd_tru_so": {"kind": "yesno", "skip": True, "optional": True},
    "ten_ho": {"kind": "text"},
    "ten_nuoc_ngoai": {"kind": "text", "skip": True, "optional": True},
    "ten_viet_tat": {"kind": "text", "skip": True, "optional": True},
    "chu_ho_la_ban": {"kind": "yesno"},
    "chu_ho_ho_ten": {"kind": "text"},
    "chu_ho_gioi_tinh": {"kind": "gender"},
    "chu_ho_ngay_sinh": {"kind": "date"},
    "chu_ho_so_dinh_danh": {"kind": "id12"},
    "chu_the": {"kind": "chu_the"},
    "noi_o": {"kind": "address", "same": True},
    "von": {"kind": "money"},
    "dia_chi_thue": {"kind": "yesno"},
    "dia_chi_thue_khac": {"kind": "address"},
    "ngay_bat_dau": {"kind": "date", "skip": True},
    "so_lao_dong": {"kind": "int", "skip": True},
}
_MEMBER_SLOTS = {
    "tv_ho_ten": {"kind": "text"},
    "tv_gioi_tinh": {"kind": "gender"},
    "tv_ngay_sinh": {"kind": "date"},
    "tv_so_dinh_danh": {"kind": "id12"},
    "tv_noi_o": {"kind": "address", "same": True},
    "tv_them": {"kind": "yesno"},
}
# Mục → field tờ khai (schema pipeline): có giấy tờ mà field đã có thì không hỏi.
_FROM_DOCS = {
    "dia_chi_kd": ("TruSo_DiaChi",),
    "dien_thoai": ("TruSo_DienThoai", "ChuHo_DienThoai"),
    "email": ("ChuHo_Email", "TruSo_Email"),
    "ten_ho": ("HoKinhDoanh_Ten",),
    "von": ("Von_SoTien",),
    "ngay_bat_dau": ("Thue_NgayBatDau",),
    "so_lao_dong": ("Thue_SoLaoDong",),
    "noi_o": ("ChuHo_DiaChi",),
}
_P = "ctl00$C$"
_OWN = _P + "OWN_PCtl$PERSCtl$"
_TAX = _P + "UC_DW_TAXEditCtl$"
# Ô trên cổng của từng mục: trỏ (tô sáng) khi hỏi; mục không có _FILL_RE thì cũng là field điền ngay khi có câu trả lời.
_DOM = {
    "dia_chi_kd": [_P + "ADDRCtl$CITY_IDFld", _P + "ADDRCtl$WARD_IDFld", _P + "ADDRCtl$STREET_NUMBERFld"],
    "dien_thoai": [_P + "DCONTClt$HO_PHONEFld"],
    "email": [_P + "DCONTClt$HO_EMAILFld"],
    "fax": [_P + "DCONTClt$HO_FAXFld"],
    "website": [_P + "DCONTClt$HO_URLFld"],
    "khong_kd_tru_so": [_P + "NO_BUSINESS_HEADOFFICEld"],
    "ten_ho": [_P + "NAMEFld"],
    "ten_nuoc_ngoai": [_P + "NAME_FFld"],
    "ten_viet_tat": [_P + "SHORT_NAMEFld"],
    "chu_ho_la_ban": [_P + "OWN_PCtl$btnIS_SIGNER"],
    "chu_ho_ho_ten": [_OWN + "FULL_NAMEFld"],
    "chu_ho_gioi_tinh": [_OWN + "GENDER_IDFld"],
    "chu_ho_ngay_sinh": [_OWN + "DATE_OF_BIRTHFld"],
    "chu_ho_so_dinh_danh": [_OWN + "PERS_DOC_NOFld"],
    "chu_the": [_P + "OWNER_TYPE_RbBox"],
    "noi_o": [_OWN + "ADDRCCtl$CITY_IDFld", _OWN + "ADDRCCtl$WARD_IDFld", _OWN + "ADDRCCtl$STREET_NUMBERFld"],
    "von": [_P + "CPT_CHARTER_AMOUNTFld"],
    "dia_chi_thue": [_TAX + "REP_RECV_ADDR_TYPEFld"],
    "dia_chi_thue_khac": [_TAX + "ADDRCtl$CITY_IDFld", _TAX + "ADDRCtl$WARD_IDFld", _TAX + "ADDRCtl$STREET_NUMBERFld"],
    "ngay_bat_dau": [_TAX + "BUSINESS_START_DATEFld"],
    "so_lao_dong": [_TAX + "TOTAL_OF_LABORSFld"],
}
# Mục gồm nhiều field (khối địa chỉ: quốc gia, tỉnh, xã, số nhà; nút sao chép tài khoản).
_FILL_RE = {
    "dia_chi_kd": re.compile(r"^ctl00\$C\$ADDRCtl\$"),
    "noi_o": re.compile(r"OWN_PCtl\$PERSCtl\$ADDRCCtl\$"),
    "dia_chi_thue": re.compile(r"UC_DW_TAXEditCtl\$(REP_RECV_ADDR_TYPEFld|ADDRCtl\$)"),
    "dia_chi_thue_khac": re.compile(r"UC_DW_TAXEditCtl\$(REP_RECV_ADDR_TYPEFld|ADDRCtl\$)"),
    "ten_ho": re.compile(r"\$(NAMEFld|DROP_NAME_TYPE)$"),
    "chu_ho_la_ban": re.compile(r"^__copyAccount$"),
}


def _slot_of(name: str, key: str) -> bool:
    rx = _FILL_RE.get(key)
    return bool(rx.search(name)) if rx else name in _DOM.get(key, [])


# ── Bật / trạng thái ──

def active(conv: dict, proc: dict | None) -> bool:
    return bool(proc and proc.get("businessWorkflow") == "create"
                and (conv.get("client_capabilities") or {}).get(CAPABILITY)
                and (conv.get("lang") or "vi") != "hmong")


def asking(conv: dict) -> bool:
    st = conv.get("hkd") or {}
    return st.get("phase") in ("ask", "confirm") and not st.get("paused")


def consent_card_extra(conv: dict, proc: dict | None) -> dict:
    """Nút "không có giấy tờ" trên thẻ đồng ý — extension cũ không biết khoá này nên không vẽ."""
    return {"no_docs_label": vi.HKD_NO_DOCS_LABEL} if active(conv, proc) else {}


def no_docs_chip(conv: dict, proc: dict | None) -> dict | None:
    if not active(conv, proc) or conv.get("hkd"):
        return None
    return {"label": vi.HKD_NO_DOCS_LABEL, "send": "__action:hkd_no_docs"}


def needs_review(conv: dict, proc: dict | None) -> bool:
    """Pipeline đọc giấy tờ xong (business_ready) mà chưa vào vòng đi từng khối."""
    return (active(conv, proc) and conv.get("pipeline_status") == "business_ready"
            and not conv.get("hkd_checked") and not conv.get("business_action_started"))


def _say(tpl: dict, **kw) -> tuple[str, str]:
    return tpl["md"].format(**kw), tpl["tts"].format(**kw)


def _join(*parts: tuple[str, str]) -> tuple[str, str]:
    return "".join(p[0] for p in parts), "".join(p[1] for p in parts)


def _reply(text: tuple[str, str], chips: list | None = None, actions: list | None = None):
    from app.channels.handfree.chat.flow import Reply
    r = Reply(text[0], text[1])
    r.actions = list(actions or [])
    r.chips = list(chips or [])
    return r


def _json(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def _location(conv: dict) -> str:
    loc = conv.get("location") or {}
    return ", ".join(x for x in (loc.get("ward"), loc.get("province")) if x)


def _has(value) -> bool:
    if isinstance(value, dict):
        return bool(value.get("xa") or value.get("tinh"))
    return value not in (None, "", [])


def _spec(key: str) -> dict:
    return _SLOTS.get(key) or _MEMBER_SLOTS.get(key) or {}


def _blocks(st: dict) -> list[str]:
    return [page for page, _ in _BLOCKS
            if page != MEMBERS_PAGE or st["values"].get("chu_the") == "ho_gia_dinh"]


def _page(st: dict) -> str:
    return _blocks(st)[st["block"]]


def _label(page: str) -> str:
    return vi.HKD_BLOCK_LABELS.get(page, page)


# ── Mục còn phải hỏi trong khối ──

def _needed(st: dict, key: str) -> bool:
    values, skipped = st["values"], set(st.get("skipped") or [])
    if key in skipped or _has(values.get(key)) or values.get(key) is False:
        return False
    if _SLOTS[key].get("optional") and st["mode"] != "khong_giay":
        return False
    if key == "dia_chi_thue_khac":
        return values.get("dia_chi_thue") is False
    if key.startswith("chu_ho_") and key != "chu_ho_la_ban":
        return values.get("chu_ho_la_ban") is False
    if key == "chu_ho_la_ban":
        return st["mode"] == "khong_giay" or not st.get("owner_from_docs")
    if key == "chu_the":
        return st["mode"] == "khong_giay"
    if key == "ngay_bat_dau" and st.get("skip_start_date"):
        return False
    return True


def _nganh_step(st: dict) -> str:
    rows = st.get("nganh") or []
    if st.get("from_docs_codes"):
        return ""
    if not rows:
        return "nganh"
    if any(r.get("ma") and not r.get("chac") for r in rows):
        return "nganh_chon"
    if any(not r.get("ma") for r in rows):
        # Cổng chỉ nhận ngành theo mã (ghi chữ chỉ khi KHÔNG có mã nào) → dòng chưa có mã phải rõ mã hoặc bỏ.
        return "nganh_ro"
    if len(rows) > 1 and not st.get("chinh"):
        return "nganh_chinh"
    return ""


def _member_step(st: dict) -> str:
    if st.get("members_done"):
        return ""
    member = st.get("member") or {}
    for key in ("tv_ho_ten", "tv_gioi_tinh", "tv_ngay_sinh", "tv_so_dinh_danh", "tv_noi_o"):
        if not _has(member.get(key)):
            return key
    return "tv_them"


def _next_field(st: dict) -> str:
    page = _page(st)
    if page == _NGANH_PAGE:
        return _nganh_step(st)
    if page == MEMBERS_PAGE:
        return _member_step(st)
    return next((k for k in dict(_BLOCKS)[page] if _needed(st, k)), "")


# ── Câu hỏi + nút ──

def _question(st: dict, key: str) -> tuple[str, str]:
    if key == "nganh_chon":
        row = next(r for r in st["nganh"] if r.get("ma") and not r.get("chac"))
        return _say(vi.HKD_QUESTIONS[key], hoat_dong=row.get("hoatDong") or "")
    if key == "nganh_ro":
        row = next(r for r in st["nganh"] if not r.get("ma"))
        return _say(vi.HKD_QUESTIONS[key], hoat_dong=row.get("hoatDong") or "")
    if key == "nganh_chinh":
        return _say(vi.HKD_QUESTIONS[key], n=len(st["nganh"]))
    if key.startswith("tv_"):
        name = (st.get("member") or {}).get("tv_ho_ten") or ""
        return _say(vi.HKD_QUESTIONS[key], i=len(st.get("members") or []) + 1, name=name)
    return _say(vi.HKD_QUESTIONS[key])


def _chips(st: dict, key: str) -> list:
    def value(label, v):
        return {"label": label, "send": f'__action:hkd_value:{{"v":{_json(v)}}}'}

    if key == "nganh_chon":
        i, row = next((i, r) for i, r in enumerate(st["nganh"]) if r.get("ma") and not r.get("chac"))
        return [{"label": f"{ma} · {nganh_nghe.ten(ma)}", "send": f'__action:hkd_pick:{{"row":{i},"ma":"{ma}"}}'}
                for ma in row["ma"]]
    if key == "nganh_ro":
        i = next(i for i, r in enumerate(st["nganh"]) if not r.get("ma"))
        return [{"label": vi.HKD_DROP_ACTIVITY_LABEL, "send": f'__action:hkd_pick:{{"row":{i},"drop":true}}'}]
    if key == "nganh_chinh":
        return [{"label": f"{r['ma'][0]} · {nganh_nghe.ten(r['ma'][0])}",
                 "send": f'__action:hkd_pick:{{"chinh":"{r["ma"][0]}"}}'} for r in st["nganh"] if r.get("chac")]
    spec = _spec(key)
    chips = []
    if spec.get("kind") == "yesno":
        chips = [value(vi.HKD_YES_LABEL, True), value(vi.HKD_NO_LABEL, False)]
    elif spec.get("kind") == "gender":
        chips = [value(vi.HKD_MALE_LABEL, "Nam"), value(vi.HKD_FEMALE_LABEL, "Nữ")]
    elif spec.get("kind") == "chu_the":
        chips = [value(vi.HKD_INDIVIDUAL_LABEL, "ca_nhan"), value(vi.HKD_HOUSEHOLD_LABEL, "ho_gia_dinh")]
    elif key == "noi_o":
        chips = [value(vi.HKD_SAME_HEAD_OFFICE_LABEL, "giong")]
    elif key == "tv_noi_o":
        chips = [value(vi.HKD_SAME_OWNER_LABEL, "giong")]
    if spec.get("skip"):
        chips.append({"label": vi.HKD_SKIP_LABEL, "send": "__action:hkd_skip"})
    return chips


# ── Hiển thị giá trị ──

def _addr_text(value, key: str = "") -> str:
    if value == "giong":
        return vi.HKD_VALUE_TEXT["same_owner" if key == "tv_noi_o" else "same_head_office"]
    if not isinstance(value, dict):
        return ""
    return ", ".join(v for v in (value.get("diaChi"), value.get("xa"), value.get("tinh")) if v)


def _show(key: str, value) -> tuple[str, str]:
    """(chữ hiển thị, chữ đọc) của một giá trị đã ghi."""
    kind = _spec(key).get("kind")
    if kind == "address":
        text = _addr_text(value, key)
        return text, text
    if kind in ("phone", "id12"):
        return str(value), " ".join(str(value))  # đọc từng chữ số để công dân soát
    if kind == "money":
        text = f"{int(value):,}".replace(",", ".") + " đồng"
        return text, text
    if kind == "yesno":
        if key == "chu_ho_la_ban":
            text = vi.HKD_VALUE_TEXT["account_owner" if value else "other_person"]
        elif key == "dia_chi_thue":
            text = vi.HKD_VALUE_TEXT["same_head_office" if value else "other_address"]
        else:
            text = vi.HKD_YES_LABEL if value else vi.HKD_NO_LABEL
        return text, text
    if kind == "chu_the":
        text = vi.HKD_VALUE_TEXT["individual" if value == "ca_nhan" else "household"]
        return text, text
    return str(value), str(value)


def _noted(key: str, value) -> tuple[str, str]:
    shown, spoken = _show(key, value)
    return _say(vi.HKD_NOTED, label=vi.HKD_LABELS.get(key, key), value=shown, value_tts=spoken)


def _nganh_lines(st: dict) -> list[str]:
    out = []
    for r in st.get("nganh") or []:
        if not r.get("chac"):
            continue
        ma = r["ma"][0]
        main = vi.HKD_VALUE_TEXT["main"] if ma == st.get("chinh") or len(st["nganh"]) == 1 else ""
        detail = f" — {vi.HKD_LABELS['chi_tiet']}: {r['chiTiet']}" if r.get("chiTiet") else ""
        out.append(f"{ma} · {nganh_nghe.ten(ma)}{main}{detail}")
    return out


def _noted_nganh(st: dict) -> tuple[str, str]:
    sure = [r for r in st.get("nganh") or [] if r.get("chac")]
    if not sure:
        return "", ""
    return _say(vi.HKD_NOTED, label=vi.HKD_LABELS["nganh"], value="; ".join(_nganh_lines(st)),
                value_tts="; ".join(r.get("chiTiet") or nganh_nghe.ten(r["ma"][0]) for r in sure))


def _block_rows(st: dict, page: str) -> list[str]:
    if page == _NGANH_PAGE:
        return [f"- {line}" for line in _nganh_lines(st)]
    if page == MEMBERS_PAGE:
        return [f"- **{vi.HKD_LABELS['thanh_vien']} {i}:** " + ", ".join(
            p for p in (m.get("tv_ho_ten"), m.get("tv_gioi_tinh"), m.get("tv_ngay_sinh"), m.get("tv_so_dinh_danh"),
                        _addr_text(m.get("tv_noi_o"), "tv_noi_o")) if p)
                for i, m in enumerate(st.get("members") or [], 1)]
    rows = []
    values, skipped = st["values"], set(st.get("skipped") or [])
    for key in dict(_BLOCKS)[page]:
        if key == "dia_chi_thue_khac":
            continue
        if key in skipped:
            rows.append(f"- **{vi.HKD_LABELS[key]}:** _{vi.HKD_VALUE_TEXT['skipped']}_")
        elif values.get(key) not in (None, "__docs__") and (_has(values.get(key)) or values.get(key) is False):
            shown, _ = _show(key, values[key])
            if key == "dia_chi_thue" and values[key] is False:
                shown = _addr_text(values.get("dia_chi_thue_khac"))
            rows.append(f"- **{vi.HKD_LABELS.get(key, key)}:** {shown}")
    if st["mode"] == "bo_sung":
        rows.append(f"- _{vi.HKD_VALUE_TEXT['from_docs']}_")
    return rows


# ── Dựng field cho trang ──

def _schema_facts(st: dict) -> dict:
    facts = {k: v for k, v in (st.get("base") or {}).items() if v not in (None, "", [], {})}
    f = {k: v for k, v in st["values"].items() if v != "__docs__"}

    def put(name, value, *, only_if_empty=False):
        if value in (None, "", {}) or (only_if_empty and _has(facts.get(name))):
            return
        facts[name] = value

    put("HoKinhDoanh_Ten", f.get("ten_ho"))
    put("HoKinhDoanh_TenNuocNgoai", f.get("ten_nuoc_ngoai"))
    put("HoKinhDoanh_TenVietTat", f.get("ten_viet_tat"))
    put("TruSo_DiaChi", f.get("dia_chi_kd"))
    put("TruSo_DienThoai", f.get("dien_thoai"))
    put("ChuHo_DienThoai", f.get("dien_thoai"), only_if_empty=True)
    put("Thue_DienThoai", f.get("dien_thoai"), only_if_empty=True)
    put("TruSo_Email", f.get("email"))
    put("ChuHo_Email", f.get("email"), only_if_empty=True)
    put("Thue_Email", f.get("email"), only_if_empty=True)
    put("TruSo_Fax", f.get("fax"))
    put("TruSo_Website", f.get("website"))
    if f.get("von"):
        put("Von_SoTien", str(f["von"]))
    put("Thue_NgayBatDau", f.get("ngay_bat_dau"))
    if f.get("so_lao_dong") is not None:
        put("Thue_SoLaoDong", str(f["so_lao_dong"]))
    if f.get("dia_chi_thue") is True:
        facts.pop("Thue_DiaChiNhanThongBao", None)  # trống = giống trụ sở (mapper)
    elif f.get("dia_chi_thue") is False:
        put("Thue_DiaChiNhanThongBao", f.get("dia_chi_thue_khac"))
    put("ChuHo_HoTen", f.get("chu_ho_ho_ten"))
    put("ChuHo_GioiTinh", f.get("chu_ho_gioi_tinh"))
    put("ChuHo_NgaySinh", f.get("chu_ho_ngay_sinh"))
    put("ChuHo_SoDinhDanh", f.get("chu_ho_so_dinh_danh"))
    put("ChuHo_DiaChi", facts.get("TruSo_DiaChi") if f.get("noi_o") == "giong" else f.get("noi_o"))
    rows = [r for r in st.get("nganh") or [] if r.get("chac")]
    if rows and not st.get("from_docs_codes"):
        chinh = st.get("chinh") or (rows[0]["ma"][0] if len(rows) == 1 else "")
        # Tên gửi cho mapper = chữ ghi vào ô chi tiết của dòng ngành (extension ghi khi khác tên chuẩn của mã).
        facts["NganhNghe_DanhSach"] = [{"ma": r["ma"][0], "ten": r.get("chiTiet") or nganh_nghe.ten(r["ma"][0]),
                                        "chinh": r["ma"][0] == chinh} for r in rows]
        facts["NganhNghe_MaChinh"] = chinh
        facts.pop("NganhNghe_TenChinh", None)
    return facts


def _member_fields(member: dict, owner_address) -> list[dict]:
    prefix = "ctl00$C$MEM_PCtl$PERSCtl$"
    out = [
        {"name": f"{prefix}FULL_NAMEFld", "comp": "dom-input", "value": mapper._proper_name(member.get("tv_ho_ten"))},
        {"name": f"{prefix}GENDER_IDFld", "comp": "dom-radio", "value": mapper._gender_code(member.get("tv_gioi_tinh"))},
        {"name": f"{prefix}DATE_OF_BIRTHFld", "comp": "dom-date", "value": member.get("tv_ngay_sinh") or ""},
        {"name": f"{prefix}PERS_DOC_NOFld", "comp": "dom-input", "value": member.get("tv_so_dinh_danh") or ""},
    ]
    address = mapper._addr(owner_address if member.get("tv_noi_o") == "giong" else member.get("tv_noi_o"))
    if address:
        out += [
            {"name": f"{prefix}ADDRCCtl$COUNTRY_IDFld", "comp": "dom-select", "value": address.get("quocGia") or "Việt Nam"},
            {"name": f"{prefix}ADDRCCtl$CITY_IDFld", "comp": "dom-select", "value": address.get("tinh")},
            {"name": f"{prefix}ADDRCCtl$WARD_IDFld", "comp": "dom-select", "value": address.get("xa")},
            {"name": f"{prefix}ADDRCCtl$STREET_NUMBERFld", "comp": "dom-input", "value": address.get("diaChi")},
        ]
    return [f for f in out if f["value"]]


def page_fields(st: dict, page: str) -> list[dict]:
    """Field của một khối từ mọi giá trị đã có (mapper của pipeline + phần riêng của luồng hỏi đáp)."""
    if page == MEMBERS_PAGE:
        owner_address = _schema_facts(st).get("ChuHo_DiaChi")
        return [{"name": "__members", "comp": "raw",
                 "value": [_member_fields(m, owner_address) for m in st.get("members") or []]}]
    if page == AUTH_PAGE:
        return []
    facts = _schema_facts(st)
    fields = mapper.enrich([{"name": k, "value": v} for k, v in facts.items()], page=page,
                           skip_start_date=bool(st.get("skip_start_date")))
    values = st["values"]
    if page == "dia-chi" and values.get("khong_kd_tru_so") is False:
        fields.append({"name": _P + "NO_BUSINESS_HEADOFFICEld", "comp": "dom-checkbox", "value": True})
    if page == _OWNER_PAGE:
        if values.get("chu_ho_la_ban") is True:
            # Chủ hộ là người đang đăng nhập: nhân thân lấy bằng nút "Sao chép thông tin đăng ký tài khoản" (khớp CSDL
            # dân cư) thay vì hỏi bằng lời; nơi ở / điện thoại / email đã hỏi vẫn điền đè sau đó.
            fields.insert(0, {"name": "__copyAccount", "comp": "raw", "value": True})
        if values.get("chu_the") == "ho_gia_dinh":
            for f in fields:
                if f["name"] == _P + "OWNER_TYPE_RbBox":
                    f["value"] = "M"
    return fields


def _fill_now(st: dict, keys: list[str]) -> list[dict]:
    """Lệnh điền NGAY các mục vừa có câu trả lời (chỉ mục thuộc khối đang mở; mục khối khác điền khi tới khối đó)."""
    page = _page(st)
    own = dict(_BLOCKS).get(page) or []
    keys = [k for k in keys if k in own]
    fields = [f for f in page_fields(st, page) if any(_slot_of(f["name"], k) for k in keys)] if keys else []
    return [{"type": "hkd_fill", "page": page, "fields": fields}] if fields else []


def _prefill_fields(st: dict, page: str) -> list[dict]:
    """Điền sẵn lúc vào khối: mọi field đã có giá trị, trừ ô của mục còn phải hỏi (hỏi tới đâu điền tới đó)."""
    pending = [k for k in dict(_BLOCKS).get(page) or [] if _needed(st, k)]
    return [f for f in page_fields(st, page)
            if not f["name"].startswith("__") and not any(_slot_of(f["name"], k) for k in pending)]


# ── Chuyển khối ──

def _open_action(page: str) -> dict:
    return {"type": "hkd_open_block", "page": page, "label": _label(page)}


def _go_block(conv: dict, index: int, lead: tuple[str, str] = ("", "")):
    st = conv["hkd"]
    blocks = _blocks(st)
    if index >= len(blocks):
        return _finish(conv, lead)
    st.update(block=index, phase="open", field="", asked=False, open_tries=1, opened_at=time.time(),
              open_failed_said=False)
    return _reply(lead, actions=[_open_action(blocks[index])])


def _arrive(conv: dict):
    """Extension báo đã đứng đúng khối: điền sẵn ô đã biết, rồi hỏi ô đầu tiên còn thiếu (hoặc tự lưu)."""
    st = conv["hkd"]
    page = _page(st)
    st["phase"] = "ask"
    prefill = _prefill_fields(st, page)
    actions = [{"type": "hkd_fill", "page": page, "fields": prefill}] if prefill else []
    return _ask_next(conv, _say(vi.HKD_BLOCK_OPEN, label=_label(page)), actions)


def _ask_next(conv: dict, lead: tuple[str, str] = ("", ""), actions: list | None = None):
    st = conv["hkd"]
    page = _page(st)
    key = _next_field(st)
    actions = list(actions or [])
    if key:
        st.update(phase="ask", field=key, asked=True)
        if key in _DOM:
            actions.append({"type": "hkd_focus", "page": page, "names": _DOM[key]})
        return _reply(_join(lead, _question(st, key)), _chips(st, key), actions)
    if not st.get("asked"):
        return _save(conv, lead, actions)  # khối không phải hỏi gì → tự lưu
    st.update(phase="confirm", field=_CONFIRM)
    actions.append({"type": "hkd_focus", "page": page, "names": []})
    text = _say(vi.HKD_BLOCK_CONFIRM, label=_label(page), rows="\n".join(_block_rows(st, page)))
    return _reply(_join(lead, text), [{"label": vi.HKD_BLOCK_SAVE_LABEL, "send": "__action:hkd_save", "solid": True}],
                  actions)


def _save(conv: dict, lead: tuple[str, str] = ("", ""), actions: list | None = None):
    """Lưu khối = máy điền HkdOnline chạy đúng một trang (điền lại toàn khối rồi bấm Lưu), báo business_report."""
    from app.channels.handfree.chat import flow
    st = conv["hkd"]
    page = _page(st)
    st.update(phase="saving", field="", saving_at=time.time())
    last = st["block"] == len(_blocks(st)) - 1
    action = {
        "type": "start_business_registration",
        "pages": {page: page_fields(st, page)},
        # Tệp đính kèm (có giấy tờ) chạy cùng lần lưu khối cuối — máy điền đính sau khi xong trang cuối.
        "attachments": (conv.get("attach_plan") or []) if last else [],
        "session_id": (conv.get("upload_session_id") or "") if last else "",
        "businessDefaults": flow._business_defaults(conv),
        "workflow": "create",
        "businessFlow": {"pageOrder": [page]},
    }
    return _reply(_join(lead, _say(vi.HKD_BLOCK_SAVING, label=_label(page))), actions=[*(actions or []), action])


def _finish(conv: dict, lead: tuple[str, str]):
    st = conv["hkd"]
    st.update(phase="done", field="")
    conv["state"] = "done"
    conv["attach_done"] = True
    conv["pipeline_status"] = "business_done"
    attached = int(st.get("attached") or 0)
    text = _say(vi.HKD_DONE, attached=vi.HKD_DONE_ATTACHED.format(n=attached) if attached else "")
    return _reply(_join(lead, text))


async def _on_report(conv: dict, payload: dict):
    st = conv["hkd"]
    page = _page(st)
    if payload.get("ok") is True:
        st["attached"] = int(st.get("attached") or 0) + max(0, int(payload.get("attached") or 0))
        return _go_block(conv, st["block"] + 1, _say(vi.HKD_BLOCK_SAVED, label=_label(page)))
    st["phase"] = "confirm"
    errors = [str(e) for e in payload.get("errors") or [] if e]
    text = _say(vi.HKD_BLOCK_SAVE_FAILED, label=_label(page), error=errors[0] if errors else "cổng chưa nhận")
    return _reply(text, [{"label": vi.HKD_BLOCK_RETRY_LABEL, "send": "__action:hkd_save", "solid": True}])


def _on_page(conv: dict, here: str):
    """page_status trong lúc chờ mở khối: đúng khối → vào khối; sai khối quá lâu → mở lại (có trần)."""
    st = conv["hkd"]
    page = _page(st)
    if here == page:
        return _arrive(conv)
    if time.time() - float(st.get("opened_at") or 0) < _OPEN_RETRY_SECONDS:
        return _reply(("", ""))
    if int(st.get("open_tries") or 0) >= _OPEN_MAX_TRIES:
        if not st.get("open_failed_said"):
            st["open_failed_said"] = True
            return _reply(_say(vi.HKD_BLOCK_OPEN_FAILED, label=_label(page)))
        return _reply(("", ""))
    st["open_tries"] = int(st.get("open_tries") or 0) + 1
    st["opened_at"] = time.time()
    return _reply(("", ""), actions=[_open_action(page)])


# ── Trả lời ──

def _open_slots(st: dict) -> list[dict]:
    def label(k):
        return vi.HKD_PROMPT_LABELS.get(k) or vi.HKD_LABELS.get(k, k)

    if _page(st) == MEMBERS_PAGE:
        # Khối thành viên: chỉ mục của thành viên — "ở cùng chủ hộ" không được rơi vào nơi ở của chủ hộ.
        return [{"key": k, "label": label(k), **spec} for k, spec in _MEMBER_SLOTS.items()]
    # Chỉ mục của khối đang mở: câu "giống địa chỉ kinh doanh" ở ô nơi ở không được rơi sang mục địa chỉ thuế của
    # khối sau. Câu nhiều ý trong cùng khối (địa chỉ kèm điện thoại) vẫn ghi đủ; ý của khối khác tới khối đó mới hỏi.
    keys = [k for k in dict(_BLOCKS).get(_page(st)) or [] if k != "chu_the" or st["mode"] == "khong_giay"]
    return [{"key": k, "label": label(k), **_SLOTS[k]} for k in keys]


def _apply(st: dict, key: str, value) -> None:
    if key.startswith("tv_"):
        if key == "tv_them":
            # Chốt thành viên đang nhập; "còn nữa" → thành viên mới, "hết" → xong vòng thành viên.
            if st.get("member"):
                st.setdefault("members", []).append(dict(st["member"]))
            st["member"] = {}
            st["members_done"] = not value
            return
        st.setdefault("member", {})[key] = value
        return
    st["values"][key] = value
    if key in (st.get("skipped") or []):
        st["skipped"].remove(key)


async def _lookup(st: dict, text: str) -> tuple[str, str]:
    """Agent tra mã cập nhật danh sách ngành. Trả câu hỏi lại của agent / báo lỗi (nếu có)."""
    res = await nganh_nghe.tra_cuu(text, st.get("nganh") or [])
    st.setdefault("trace", []).append({"text": text[:300], "steps": res.steps[-6:], "error": res.error})
    if res.error:
        return _say(vi.HKD_NGANH_FAILED)
    st["nganh"] = [n.to_dict() for n in res.nganh]
    st.pop("from_docs_codes", None)
    sure = [r["ma"][0] for r in st["nganh"] if r.get("chac")]
    if res.chinh:
        st["chinh"] = res.chinh
    elif st.get("chinh") not in sure:
        st["chinh"] = sure[0] if len(st["nganh"]) == 1 and sure else ""
    if res.hoi_lai and not st["nganh"]:
        return res.hoi_lai, res.hoi_lai
    return "", ""


def _skip(conv: dict, lead: tuple[str, str] = ("", ""), actions: list | None = None):
    st = conv["hkd"]
    key = st.get("field") or ""
    if not _spec(key).get("skip"):
        return _ask_next(conv, _join(lead, _say(vi.HKD_REQUIRED)), actions)
    if key not in st.setdefault("skipped", []):
        st["skipped"].append(key)
    return _ask_next(conv, lead, actions)


async def _answer(conv: dict, text: str):
    st = conv["hkd"]
    key = st["field"]
    if key in ("nganh", "nganh_chon", "nganh_ro", "nganh_chinh") or (key == _CONFIRM and _page(st) == _NGANH_PAGE):
        failed = _say(vi.HKD_NGANH_FAILED)
        lead = await _lookup(st, text)
        if lead == failed or (lead[0] and not st.get("nganh")):
            return _reply(lead)  # agent lỗi / lời kể còn quá chung → hỏi lại, vẫn đứng ở mục ngành
        return _ask_next(conv, _noted_nganh(st))
    question = _question(st, key)[0] if key != _CONFIRM else ""
    parsed = await hoi_dap.interpret(text, key if key != _CONFIRM else "tom_tat", question, _open_slots(st),
                                     {**st["values"], **(st.get("member") or {})}, _location(conv))
    if parsed.action == "dong_y" and key == _CONFIRM and not parsed.values:
        return _save(conv)
    if parsed.action == "tam_dung":
        st["paused"] = True
        return _reply(_say(vi.HKD_PAUSED), [{"label": vi.HKD_RESUME_LABEL, "send": "__action:hkd_resume", "solid": True}])
    lead = ("", "")
    for k, v in parsed.values.items():
        _apply(st, k, v)
        lead = _join(lead, _noted(k, v))
    actions = _fill_now(st, list(parsed.values))
    if parsed.action == "bo_qua" and key not in parsed.values and key != _CONFIRM:
        return _skip(conv, lead, actions)  # "không có email, vốn 50 triệu" → ghi vốn rồi bỏ qua email
    if key in parsed.bad_digits:
        digits = parsed.bad_digits[key]
        lead = _join(lead, _say(vi.HKD_DIGITS_WRONG, n=len(digits), digits=digits,
                                what=vi.HKD_DIGITS_WHAT[_spec(key)["kind"]]))
    elif not parsed.values and parsed.action != "nhac_lai":
        lead = _join(lead, _say(vi.HKD_UNCLEAR))
    return _ask_next(conv, lead, actions)


# ── Bắt đầu ──

async def _base_state(conv: dict, mode: str) -> dict:
    from app.channels.handfree.chat import pipeline_runner
    user = await pipeline_runner._load_owner_user(conv, None)
    return {"mode": mode, "values": {}, "nganh": [], "chinh": "", "skipped": [], "members": [], "member": {},
            "block": 0, "phase": "", "field": "", "skip_start_date": mapper.is_bac_ninh_phuong_lieu(user)}


def _begin(conv: dict) -> None:
    conv["hkd_checked"] = True
    conv["state"] = "filling"
    conv["pipeline_status"] = "hkd_hoi"  # chặn nhánh điền cả 8 trang một lượt của luồng tờ khai
    conv["business_action_started"] = False


async def start_no_docs(conv: dict):
    """Công dân không có tờ khai/giấy tờ: đi từng khối, hỏi mọi ô (sau khi đã đồng ý xử lý dữ liệu)."""
    conv["hkd"] = await _base_state(conv, "khong_giay")
    conv["attach_plan"] = []
    _begin(conv)
    return _go_block(conv, 0, _say(vi.HKD_START))


async def start_review(conv: dict):
    """Pipeline đọc giấy tờ xong: đi từng khối, điền sẵn từ giấy, chỉ hỏi ô còn thiếu."""
    base = {f.get("name"): f.get("value") for f in conv.get("business_facts") or [] if f.get("name")}
    st = await _base_state(conv, "bo_sung")
    st["base"] = base
    st["owner_from_docs"] = bool(base.get("ChuHo_HoTen") and base.get("ChuHo_SoDinhDanh"))
    for key, names in _FROM_DOCS.items():
        if any(_has(base.get(n)) for n in names):
            st["values"][key] = "__docs__"
    st["values"]["dia_chi_thue"] = "__docs__"  # tờ khai không ghi địa chỉ thuế riêng = giống trụ sở (mapper)
    rows = [r for r in base.get("NganhNghe_DanhSach") or [] if isinstance(r, dict)]
    coded = [r for r in rows if mapper._clean_business_code(r.get("ma")) in nganh_nghe.catalog()]
    conv["hkd"] = st
    _begin(conv)
    if coded:
        st["from_docs_codes"] = True
    elif rows:
        await _lookup(st, "; ".join(str(r.get("ten") or "") for r in rows if r.get("ten")))
    return _go_block(conv, 0, _say(vi.HKD_REVIEW_START))


# ── Lượt hội thoại ──

async def handle(conv: dict, proc: dict | None, intent: Intent):
    """Lệnh / câu trả lời / sự kiện trang của luồng đi từng khối. None = không thuộc luồng này."""
    if not active(conv, proc):
        return None
    st = conv.get("hkd")
    if intent.kind == "action" and intent.value == "hkd_no_docs":
        if st or not (conv.get("consent") or {}).get("accepted"):
            return None
        return await start_no_docs(conv)
    if not st or st.get("phase") in ("", "done"):
        return None
    phase = st["phase"]
    # Sự kiện trang: chỉ luồng này điều khiển — không để nhánh tờ khai phát lệnh điền cả 8 trang.
    if intent.kind == "event" and intent.value in ("page_status", "hkd_arrived"):
        result = intent.payload.get("businessResult")
        # Extension giữ kết quả lần chạy gần nhất ~30 phút và gửi kèm mọi page_status → chỉ nhận kết quả sinh SAU lúc
        # bắt đầu lưu khối này, không thì khối mới bị coi là đã lưu theo kết quả của khối trước.
        if (phase == "saving" and isinstance(result, dict) and result
                and float(result.get("createdAt") or 0) / 1000 >= float(st.get("saving_at") or 0) - 1):
            return await _on_report(conv, result)
        if phase == "open":
            if intent.value == "hkd_arrived":
                if intent.payload.get("page") != _page(st):
                    return _reply(("", ""))
                if intent.payload.get("missing") is True:
                    if _page(st) == AUTH_PAGE:
                        return _go_block(conv, st["block"] + 1)  # không có khối ủy quyền = chủ hộ tự nộp
                    # Khối khác vắng trong menu là bất thường (vd khối thành viên khi lưu chủ hộ chưa nhận) → nhờ bấm tay.
                    st["open_failed_said"] = True
                    return _reply(_say(vi.HKD_BLOCK_OPEN_FAILED, label=_label(_page(st))))
                return _arrive(conv)
            return _on_page(conv, str(intent.payload.get("businessPageKey") or ""))
        return _reply(("", ""))
    if intent.kind == "action" and intent.value == "business_report":
        if phase != "saving":
            return _reply(("", ""))  # báo trùng (watcher + sidebar) của khối đã chuyển
        return await _on_report(conv, intent.payload)
    if intent.kind != "action" or intent.value not in _ACTIONS:
        return None
    if intent.value == "hkd_resume":
        st["paused"] = False
        return _ask_next(conv)
    if intent.value == "hkd_save":
        return _save(conv) if phase == "confirm" else _reply(("", ""))
    if phase not in ("ask", "confirm"):
        return _reply(("", ""))
    if intent.value == "hkd_skip":
        return _skip(conv)
    if intent.value == "hkd_value":
        key = st["field"]
        spec = _spec(key)
        value, _ = hoi_dap.check(spec["kind"], intent.payload.get("v"), "", False, bool(spec.get("same"))) \
            if spec else (None, "")
        if value is None:
            return _ask_next(conv)
        _apply(st, key, value)
        return _ask_next(conv, _noted(key, value), _fill_now(st, [key]))
    if intent.value == "hkd_pick":
        chinh = str(intent.payload.get("chinh") or "")
        if chinh:
            st["chinh"] = chinh
            return _ask_next(conv, _noted_nganh(st))
        try:
            row = st["nganh"][int(intent.payload.get("row"))]
        except (TypeError, ValueError, IndexError):
            return _ask_next(conv)
        if intent.payload.get("drop") is True and not row.get("ma"):
            st["nganh"].remove(row)
        else:
            ma = str(intent.payload.get("ma") or "")
            if ma in row.get("ma") or []:
                row.update({"ma": [ma], "chac": True})
        if len(st["nganh"]) == 1 and st["nganh"][0].get("chac"):
            st["chinh"] = st["nganh"][0]["ma"][0]
        return _ask_next(conv, _noted_nganh(st))
    text = str(intent.payload.get("text") or "").strip()
    if not text:
        return _ask_next(conv)
    return await _answer(conv, text)
